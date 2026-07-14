#requires -Version 7.0

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $repositoryRoot ".ralph/Ralph.Core.ps1")

function Assert-Equal
{
    param(
        [Parameter(Mandatory)]$Expected,
        [Parameter(Mandatory)]$Actual,
        [Parameter(Mandatory)][string]$Message
    )

    if ($Expected -ne $Actual)
    {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Assert-Throws
{
    param(
        [Parameter(Mandatory)][scriptblock]$Action,
        [Parameter(Mandatory)][string]$Message
    )

    try
    {
        & $Action
    }
    catch
    {
        return
    }

    throw $Message
}

$readyMessage = @'
Task: M-123 - Harden commit handling
Status: Ready to Commit
<RALPH_CHANGED_PATHS>["docs/file.md",".env.example"]</RALPH_CHANGED_PATHS>
'@

Assert-Equal "READY_TO_COMMIT" (Get-RalphOnceStatus -FinalMessage $readyMessage) "Once status parsing failed."
Assert-Equal "READY_TO_COMMIT" (Get-RalphBoundedStatus -FinalMessage "<RALPH_STATUS>READY_TO_COMMIT</RALPH_STATUS>") "Bounded status parsing failed."
Assert-Equal "MALFORMED" (Get-RalphOnceStatus -FinalMessage "Status: Complete") "Legacy completion must not trigger a host commit."

$task = Get-RalphTaskIdentity -FinalMessage $readyMessage
Assert-Equal "M-123" $task.Id "Task ID parsing failed."
Assert-Equal "Harden commit handling" $task.Title "Task title parsing failed."
if ($null -ne (Get-RalphTaskIdentity -FinalMessage "$readyMessage`nTask: M-124 - Duplicate"))
{
    throw "Duplicate task lines must be rejected."
}

$paths = @(Get-RalphReportedChangedPaths -FinalMessage $readyMessage)
Assert-Equal 2 $paths.Count "Changed-path manifest parsing failed."
Assert-Equal "docs/file.md" $paths[0] "The first manifest path was not normalized."
Assert-Equal ".env.example" $paths[1] "A leading dot was removed from a manifest path."

Assert-RalphPathSetMatches -ExpectedPaths @("./docs/file.md", ".env.example") -ActualPaths @(".env.example", "docs/file.md") -Context "Smoke test"
Assert-Throws { Assert-RalphPathSetMatches -ExpectedPaths @("docs/file.md") -ActualPaths @("docs/other.md") -Context "Smoke test" } "Mismatched path sets must be rejected."
Assert-Throws { ConvertTo-RalphGitPath -RelativePath "../outside.txt" } "Parent traversal must be rejected."
Assert-Throws { ConvertTo-RalphGitPath -RelativePath "C:/outside.txt" } "Absolute paths must be rejected."
Assert-Equal "docs/file.md" (ConvertTo-RalphGitPath -RelativePath ".\docs\file.md") "Safe relative path normalization failed."

if (-not (Test-RalphSensitiveCommitPath -RelativePath ".env"))
{
    throw ".env must be treated as sensitive."
}
if (-not (Test-RalphSensitiveCommitPath -RelativePath ".env.local"))
{
    throw ".env.local must be treated as sensitive."
}
if (Test-RalphSensitiveCommitPath -RelativePath ".env.example")
{
    throw ".env.example must remain eligible for commits."
}

$textBytes = [System.Text.Encoding]::UTF8.GetBytes("safe text`r`n")
Assert-Equal "safe text`r`n" (ConvertFrom-RalphStagedTextBlob -Bytes $textBytes -RelativePath "docs/file.md") "Strict staged-text decoding failed."
Assert-Throws { ConvertFrom-RalphStagedTextBlob -Bytes ([byte[]]@(0x89, 0x50, 0x4E, 0x47, 0x00)) -RelativePath "image.bin" } "Binary staged bytes must be rejected independently of Git diff attributes."
Assert-Throws { ConvertFrom-RalphStagedTextBlob -Bytes ([byte[]]@(0xC3, 0x28)) -RelativePath "invalid-utf8.txt" } "Invalid UTF-8 staged bytes must be rejected."

$trackedBlob = Get-RalphStagedBlob -RelativePath ".ralph/config.json"
if (-not $trackedBlob.Exists)
{
    throw "A tracked stage-zero blob could not be read from the index."
}
$trackedText = ConvertFrom-RalphStagedTextBlob -Bytes $trackedBlob.Bytes -RelativePath ".ralph/config.json"
if (-not $trackedText.Contains('"sandboxName"'))
{
    throw "The direct staged-blob read returned unexpected content."
}

$firstFingerprint = Get-RalphGitControlFingerprint
$secondFingerprint = Get-RalphGitControlFingerprint
Assert-Equal $firstFingerprint $secondFingerprint "The Git-control fingerprint is not stable."

Push-Location (Join-Path $repositoryRoot "docs")
try
{
    $reportedRoot = (Invoke-RalphGit -Arguments @("rev-parse", "--show-toplevel")).Text
}
finally
{
    Pop-Location
}
Assert-Equal ([System.IO.Path]::GetFullPath($repositoryRoot)) ([System.IO.Path]::GetFullPath($reportedRoot)) "Git commands were not pinned to the repository root."

$finalizerPrompt = Get-RalphLinearFinalizationPrompt -Task $task -Commit "0123456789abcdef"
if (-not $finalizerPrompt.Contains('Ralph commit: 0123456789abcdef'))
{
    throw "The Linear finalizer prompt did not include the verified commit."
}

$verificationPrompt = Get-RalphLinearVerificationPrompt -Task $task -Commit "0123456789abcdef"
if (-not $verificationPrompt.Contains('Ralph commit: 0123456789abcdef'))
{
    throw "The Linear verification prompt did not include the verified commit."
}

Write-Host "Ralph.Core smoke tests passed."
