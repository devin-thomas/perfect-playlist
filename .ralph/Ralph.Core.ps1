#requires -Version 7.0
Set-StrictMode -Version Latest

$script:RalphDirectory = $PSScriptRoot
$script:RalphRepositoryRoot = Split-Path -Parent $PSScriptRoot
$script:RalphConfig = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "config.json") | ConvertFrom-Json
$script:RalphStateDirectory = Join-Path $PSScriptRoot "state"
$script:RalphLogDirectory = Join-Path $PSScriptRoot "logs"
$script:RalphDisabledHooksDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "perfect-playlist-ralph-disabled-hooks-$PID"
$script:RalphPromptPath = Join-Path $PSScriptRoot "TASK-EXECUTION-PROMPT.md"
$script:RalphLockPath = Join-Path $script:RalphStateDirectory "ralph.lock.json"
$script:RalphLatestStatePath = Join-Path $script:RalphStateDirectory "latest-run.json"
$script:RalphBootstrapStatePath = Join-Path $script:RalphStateDirectory "bootstrap.json"
$script:RalphSecretPath = Join-Path $script:RalphRepositoryRoot $script:RalphConfig.secretFile

function Assert-RalphHost
{
    if ($PSVersionTable.PSVersion.Major -lt 7)
    {
        throw "Ralph requires PowerShell 7 or newer. Run it with pwsh, not Windows PowerShell."
    }

    foreach ($command in @("git", "sbx"))
    {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue))
        {
            throw "Required command '$command' was not found in PATH."
        }
    }
}

function Invoke-RalphGit
{
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [switch]$AllowFailure
    )

    $output = @(& git `
        -c "core.hooksPath=$script:RalphDisabledHooksDirectory" `
        -c "core.fsmonitor=false" `
        -C $script:RalphRepositoryRoot `
        @Arguments 2>&1)
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0 -and -not $AllowFailure)
    {
        $message = ($output -join [Environment]::NewLine).Trim()
        throw "git $($Arguments -join ' ') failed with exit code $exitCode.`n$message"
    }

    [pscustomobject]@{
        ExitCode = $exitCode
        Output = $output
        Text = ($output -join [Environment]::NewLine).Trim()
    }
}

function Invoke-RalphGitBytes
{
    param([Parameter(Mandatory)][string[]]$Arguments)

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = "git"
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true

    foreach ($argument in @(
        "-c", "core.hooksPath=$script:RalphDisabledHooksDirectory",
        "-c", "core.fsmonitor=false",
        "-C", $script:RalphRepositoryRoot
    ) + $Arguments)
    {
        [void]$startInfo.ArgumentList.Add($argument)
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $memory = [System.IO.MemoryStream]::new()
    try
    {
        [void]$process.Start()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.StandardOutput.BaseStream.CopyTo($memory)
        $process.WaitForExit()
        $stderr = $stderrTask.GetAwaiter().GetResult().Trim()
        if ($process.ExitCode -ne 0)
        {
            throw "git $($Arguments -join ' ') failed with exit code $($process.ExitCode).`n$stderr"
        }

        return [pscustomobject]@{ Bytes = $memory.ToArray() }
    }
    finally
    {
        $memory.Dispose()
        $process.Dispose()
    }
}

function Assert-RalphRepository
{
    $rootResult = Invoke-RalphGit -Arguments @("rev-parse", "--show-toplevel")
    $actualRoot = [System.IO.Path]::GetFullPath($rootResult.Text)
    $expectedRoot = [System.IO.Path]::GetFullPath($script:RalphRepositoryRoot)

    if ($actualRoot.TrimEnd([char[]]@('\', '/')) -ne $expectedRoot.TrimEnd([char[]]@('\', '/')))
    {
        throw "Run Ralph from the repository containing these scripts. Expected '$expectedRoot', got '$actualRoot'."
    }

    foreach ($path in @($script:RalphPromptPath))
    {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf))
        {
            throw "Required Ralph file is missing: $path"
        }
    }

    $remote = Invoke-RalphGit -Arguments @("remote", "get-url", "origin") -AllowFailure
    if ($remote.ExitCode -ne 0)
    {
        throw "The repository must have an 'origin' remote so successful tasks can be pushed."
    }
}

function Initialize-RalphDirectories
{
    [void](New-Item -ItemType Directory -Force -Path $script:RalphStateDirectory)
    [void](New-Item -ItemType Directory -Force -Path $script:RalphLogDirectory)
    [void](New-Item -ItemType Directory -Force -Path $script:RalphDisabledHooksDirectory)
}

function Assert-RalphSecretFileSafety
{
    if (-not (Test-Path -LiteralPath $script:RalphSecretPath -PathType Leaf))
    {
        Write-Warning "Spotify secret file not found at '$($script:RalphConfig.secretFile)'. Tasks needing live Spotify credentials will be unable to run."
        return
    }

    $ignore = Invoke-RalphGit -Arguments @("check-ignore", "-q", "--", $script:RalphConfig.secretFile) -AllowFailure
    if ($ignore.ExitCode -ne 0)
    {
        throw "'$($script:RalphConfig.secretFile)' is not ignored by Git. Add it to .gitignore before running Ralph."
    }

    $text = Get-Content -Raw -LiteralPath $script:RalphSecretPath
    if ($text -match '\\_')
    {
        throw "The Spotify secret file contains escaped underscores (for example SPOTIPY\_CLIENT\_ID). Remove the backslashes."
    }
}

function Enter-RalphLock
{
    Initialize-RalphDirectories

    for ($attempt = 1; $attempt -le 2; $attempt++)
    {
        $payload = [pscustomobject]@{
            pid = $PID
            startedAt = [DateTimeOffset]::Now.ToString("o")
            repository = $script:RalphRepositoryRoot
        } | ConvertTo-Json

        try
        {
            $stream = [System.IO.File]::Open(
                $script:RalphLockPath,
                [System.IO.FileMode]::CreateNew,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::None
            )
            try
            {
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
                $stream.Write($bytes, 0, $bytes.Length)
                $stream.Flush($true)
            }
            finally
            {
                $stream.Dispose()
            }
            return
        }
        catch [System.IO.IOException]
        {
            $existingPid = $null
            try
            {
                $existing = Get-Content -Raw -LiteralPath $script:RalphLockPath | ConvertFrom-Json
                $existingPid = [int]$existing.pid
            }
            catch
            {
                # An unreadable lock is treated as stale only after no live PID can be established.
            }

            if ($null -ne $existingPid)
            {
                $running = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
                if ($null -ne $running)
                {
                    throw "Another Ralph process is already running (PID $existingPid)."
                }
            }

            Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $script:RalphLockPath
            if ($attempt -eq 2)
            {
                throw "Unable to acquire the Ralph lock."
            }
        }
    }
}

function Exit-RalphLock
{
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $script:RalphLockPath
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $script:RalphDisabledHooksDirectory
}

function Get-RalphGitStatusEntries
{
    $result = Invoke-RalphGit -Arguments @("-c", "core.quotepath=false", "status", "--porcelain=v1", "--untracked-files=all")
    $entries = @()

    foreach ($line in $result.Output)
    {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.Length -lt 4)
        {
            continue
        }

        $path = $line.Substring(3)
        if ($path.Contains(" -> "))
        {
            $path = ($path -split " -> ")[-1]
        }

        $entries += [pscustomobject]@{
            Index = $line.Substring(0, 1)
            WorkTree = $line.Substring(1, 1)
            Path = $path.Trim('"')
            Raw = $line
        }
    }

    return $entries
}

function Assert-RalphIndexClean
{
    $result = Invoke-RalphGit -Arguments @("diff", "--cached", "--quiet", "--exit-code") -AllowFailure
    if ($result.ExitCode -eq 1)
    {
        throw "The Git index already contains staged changes. Unstage or commit them before running Ralph."
    }
    if ($result.ExitCode -ne 0)
    {
        throw "Unable to inspect the Git index."
    }
}

function Get-RalphCurrentBranch
{
    $branch = (Invoke-RalphGit -Arguments @("branch", "--show-current")).Text
    if ([string]::IsNullOrWhiteSpace($branch))
    {
        throw "Ralph does not support running from a detached HEAD."
    }
    return $branch
}

function Get-RalphPathState
{
    param([Parameter(Mandatory)][string]$RelativePath)

    $normalized = ConvertTo-RalphGitPath -RelativePath $RelativePath
    $fullPath = Join-Path $script:RalphRepositoryRoot $normalized
    if (-not (Test-Path -LiteralPath $fullPath))
    {
        return "MISSING"
    }

    $item = Get-Item -Force -LiteralPath $fullPath
    if ($item.PSIsContainer)
    {
        return "DIRECTORY|$($item.LastWriteTimeUtc.Ticks)"
    }

    try
    {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $fullPath).Hash
        return "FILE|$($item.Length)|$hash"
    }
    catch
    {
        return "FILE|$($item.Length)|$($item.LastWriteTimeUtc.Ticks)"
    }
}

function Get-RalphPreexistingPathStates
{
    $states = @{}
    foreach ($entry in Get-RalphGitStatusEntries)
    {
        $states[$entry.Path] = Get-RalphPathState -RelativePath $entry.Path
    }
    return $states
}

function Get-RalphWorkspaceFingerprint
{
    $skipDirectoryNames = [System.Collections.Generic.HashSet[string]]::new(
        [string[]]@(".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
    )
    $records = [System.Collections.Generic.List[string]]::new()
    $pending = [System.Collections.Generic.Stack[System.IO.DirectoryInfo]]::new()
    $pending.Push((Get-Item -LiteralPath $script:RalphRepositoryRoot))

    while ($pending.Count -gt 0)
    {
        $directory = $pending.Pop()
        foreach ($childDirectory in Get-ChildItem -Force -Directory -LiteralPath $directory.FullName -ErrorAction SilentlyContinue)
        {
            $relativeDirectory = [System.IO.Path]::GetRelativePath($script:RalphRepositoryRoot, $childDirectory.FullName).Replace('\', '/')
            if ($skipDirectoryNames.Contains($childDirectory.Name))
            {
                continue
            }
            if ($relativeDirectory -eq ".ralph/logs" -or $relativeDirectory -eq ".ralph/state")
            {
                continue
            }
            $pending.Push($childDirectory)
        }

        foreach ($file in Get-ChildItem -Force -File -LiteralPath $directory.FullName -ErrorAction SilentlyContinue)
        {
            $relative = [System.IO.Path]::GetRelativePath($script:RalphRepositoryRoot, $file.FullName).Replace('\', '/')
            $records.Add("$relative|$($file.Length)|$($file.LastWriteTimeUtc.Ticks)")
        }
    }

    $joined = ($records | Sort-Object) -join "`n"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
    $hashBytes = [System.Security.Cryptography.SHA256]::HashData($bytes)
    return [Convert]::ToHexString($hashBytes)
}

function Get-RalphGitControlFingerprint
{
    $gitDirectoryResult = Invoke-RalphGit -Arguments @("rev-parse", "--git-dir")
    $gitDirectory = $gitDirectoryResult.Text
    if (-not [System.IO.Path]::IsPathRooted($gitDirectory))
    {
        $gitDirectory = Join-Path $script:RalphRepositoryRoot $gitDirectory
    }
    $gitDirectory = [System.IO.Path]::GetFullPath($gitDirectory)

    $records = [System.Collections.Generic.List[string]]::new()
    $config = Invoke-RalphGit -Arguments @("config", "--local", "--list", "--show-origin", "--null") -AllowFailure
    $records.Add("config|$($config.ExitCode)|$($config.Text)")

    foreach ($relativePath in @("config", "config.worktree", "info/attributes"))
    {
        $path = Join-Path $gitDirectory $relativePath
        if (Test-Path -LiteralPath $path -PathType Leaf)
        {
            $records.Add("$relativePath|$((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash)")
        }
        else
        {
            $records.Add("$relativePath|MISSING")
        }
    }

    $hooksDirectory = Join-Path $gitDirectory "hooks"
    if (Test-Path -LiteralPath $hooksDirectory -PathType Container)
    {
        foreach ($hook in Get-ChildItem -Force -File -Recurse -LiteralPath $hooksDirectory | Sort-Object FullName)
        {
            $relativeHook = [System.IO.Path]::GetRelativePath($hooksDirectory, $hook.FullName).Replace('\', '/')
            $records.Add("hooks/$relativeHook|$((Get-FileHash -Algorithm SHA256 -LiteralPath $hook.FullName).Hash)")
        }
    }
    else
    {
        $records.Add("hooks|MISSING")
    }

    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($records -join "`n"))
    return [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes))
}

function Get-RalphSecretSnapshot
{
    if (Test-Path -LiteralPath $script:RalphSecretPath -PathType Leaf)
    {
        $bytes = [System.IO.File]::ReadAllBytes($script:RalphSecretPath)
        return [pscustomobject]@{ Exists = $true; Bytes = $bytes }
    }

    return [pscustomobject]@{ Exists = $false; Bytes = $null }
}

function Restore-RalphSecretIfChanged
{
    param([Parameter(Mandatory)]$Snapshot)

    $existsNow = Test-Path -LiteralPath $script:RalphSecretPath -PathType Leaf
    $changed = $false

    if ($Snapshot.Exists)
    {
        if (-not $existsNow)
        {
            $changed = $true
        }
        else
        {
            $currentBytes = [System.IO.File]::ReadAllBytes($script:RalphSecretPath)
            if ($currentBytes.Length -ne $Snapshot.Bytes.Length)
            {
                $changed = $true
            }
            else
            {
                for ($index = 0; $index -lt $currentBytes.Length; $index++)
                {
                    if ($currentBytes[$index] -ne $Snapshot.Bytes[$index])
                    {
                        $changed = $true
                        break
                    }
                }
            }
        }

        if ($changed)
        {
            [System.IO.Directory]::CreateDirectory((Split-Path -Parent $script:RalphSecretPath)) | Out-Null
            [System.IO.File]::WriteAllBytes($script:RalphSecretPath, $Snapshot.Bytes)
        }
    }
    elseif ($existsNow)
    {
        $changed = $true
        Remove-Item -Force -LiteralPath $script:RalphSecretPath
    }

    return $changed
}

function New-RalphAttemptSnapshot
{
    [pscustomobject]@{
        Head = (Invoke-RalphGit -Arguments @("rev-parse", "HEAD")).Text
        Branch = Get-RalphCurrentBranch
        OriginUrl = (Invoke-RalphGit -Arguments @("remote", "get-url", "origin")).Text
        Status = ((Get-RalphGitStatusEntries | ForEach-Object Raw) -join "`n")
        WorkspaceFingerprint = Get-RalphWorkspaceFingerprint
        GitControlFingerprint = Get-RalphGitControlFingerprint
        PreexistingPaths = Get-RalphPreexistingPathStates
        Secret = Get-RalphSecretSnapshot
    }
}

function Get-RalphAttemptChangeReasons
{
    param([Parameter(Mandatory)]$Snapshot)

    $reasons = [System.Collections.Generic.List[string]]::new()
    $head = (Invoke-RalphGit -Arguments @("rev-parse", "HEAD")).Text
    if ($head -ne $Snapshot.Head)
    {
        $reasons.Add("HEAD changed")
    }

    $branch = Get-RalphCurrentBranch
    if ($branch -ne $Snapshot.Branch)
    {
        $reasons.Add("current branch changed")
    }

    $originUrl = (Invoke-RalphGit -Arguments @("remote", "get-url", "origin")).Text
    if ($originUrl -ne $Snapshot.OriginUrl)
    {
        $reasons.Add("origin remote changed")
    }

    $status = ((Get-RalphGitStatusEntries | ForEach-Object Raw) -join "`n")
    if ($status -ne $Snapshot.Status)
    {
        $reasons.Add("Git status changed")
    }

    if ((Get-RalphWorkspaceFingerprint) -ne $Snapshot.WorkspaceFingerprint)
    {
        $reasons.Add("workspace files changed")
    }

    if ((Get-RalphGitControlFingerprint) -ne $Snapshot.GitControlFingerprint)
    {
        $reasons.Add("Git configuration or hooks changed")
    }

    return $reasons
}

function Get-RalphKnownSecretValues
{
    $values = [System.Collections.Generic.List[string]]::new()
    foreach ($path in @($script:RalphSecretPath, (Join-Path $script:RalphRepositoryRoot ".env")))
    {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf))
        {
            continue
        }

        foreach ($line in Get-Content -LiteralPath $path -ErrorAction SilentlyContinue)
        {
            if ($line -match '^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*(.+?)\s*$')
            {
                $value = $Matches[1].Trim().Trim('"').Trim("'")
                if ($value.Length -ge 7)
                {
                    $values.Add($value)
                }
            }
        }
    }
    return $values | Sort-Object -Unique
}

function Protect-RalphText
{
    param([AllowNull()][string]$Text)

    if ($null -eq $Text)
    {
        return ""
    }

    $protected = $Text
    foreach ($value in Get-RalphKnownSecretValues)
    {
        $protected = $protected.Replace($value, "[REDACTED]")
    }

    $protected = [regex]::Replace($protected, '(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+\-/=]+', '$1[REDACTED]')
    return $protected
}

function ConvertTo-RalphSafeName
{
    param([Parameter(Mandatory)][string]$Value)
    return (($Value.ToLowerInvariant() -replace '[^a-z0-9.-]', '-') -replace '-+', '-').Trim('-')
}

function Invoke-RalphProcess
{
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$InputText,
        [Parameter(Mandatory)][int]$TimeoutSeconds,
        [Parameter(Mandatory)][string]$LogPath
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.WorkingDirectory = $script:RalphRepositoryRoot
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true

    foreach ($argument in $Arguments)
    {
        [void]$startInfo.ArgumentList.Add($argument)
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $startedAt = [DateTimeOffset]::Now
    [void]$process.Start()

    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.StandardInput.Write($InputText)
    $process.StandardInput.Close()

    $timedOut = -not $process.WaitForExit($TimeoutSeconds * 1000)
    if ($timedOut)
    {
        try
        {
            $process.Kill($true)
        }
        catch
        {
            Write-Warning "Unable to terminate timed-out process cleanly: $($_.Exception.Message)"
        }
        [void]$process.WaitForExit(10000)
    }

    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $exitCode = if ($timedOut) { -1 } else { $process.ExitCode }
    $finishedAt = [DateTimeOffset]::Now

    $safeStdout = Protect-RalphText -Text $stdout
    $safeStderr = Protect-RalphText -Text $stderr
    $logText = @(
        "Started: $($startedAt.ToString('o'))"
        "Finished: $($finishedAt.ToString('o'))"
        "Timed out: $timedOut"
        "Exit code: $exitCode"
        ""
        "===== STDOUT ====="
        $safeStdout
        ""
        "===== STDERR ====="
        $safeStderr
    ) -join [Environment]::NewLine

    Set-Content -LiteralPath $LogPath -Value $logText -Encoding utf8

    if (-not [string]::IsNullOrWhiteSpace($safeStdout))
    {
        Write-Host $safeStdout
    }
    if (-not [string]::IsNullOrWhiteSpace($safeStderr))
    {
        Write-Host $safeStderr -ForegroundColor DarkYellow
    }

    [pscustomobject]@{
        ExitCode = $exitCode
        TimedOut = $timedOut
        Stdout = $safeStdout
        Stderr = $safeStderr
        LogPath = $LogPath
        StartedAt = $startedAt
        FinishedAt = $finishedAt
    }
}

function Invoke-RalphCodexAttempt
{
    param(
        [Parameter(Mandatory)][string]$Prompt,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$ReasoningEffort,
        [Parameter(Mandatory)][int]$TimeoutMinutes,
        [Parameter(Mandatory)][string]$Label
    )

    Initialize-RalphDirectories
    $timestamp = [DateTimeOffset]::Now.ToString("yyyyMMdd-HHmmss")
    $safeModel = ConvertTo-RalphSafeName -Value $Model
    $safeLabel = ConvertTo-RalphSafeName -Value $Label
    $logPath = Join-Path $script:RalphLogDirectory "$timestamp-$safeLabel-$safeModel-$ReasoningEffort.log"
    $lastMessageRelative = ".ralph/state/last-message-$timestamp-$safeLabel.txt"
    $lastMessagePath = Join-Path $script:RalphRepositoryRoot $lastMessageRelative
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $lastMessagePath

    $arguments = @(
        "run",
        "codex",
        "--name", [string]$script:RalphConfig.sandboxName,
        $script:RalphRepositoryRoot,
        "--",
        "--dangerously-bypass-approvals-and-sandbox",
        "exec",
        "--ephemeral",
        "--color", "never",
        "--model", $Model,
        "--config", "model_reasoning_effort=`"$ReasoningEffort`"",
        "--config", "mcp_servers.linear.url=`"https://mcp.linear.app/mcp`"",
        "--config", "mcp_servers.linear.bearer_token_env_var=`"LINEAR_API_KEY`"",
        "--config", "mcp_servers.linear.required=true",
        "--config", "mcp_servers.linear.startup_timeout_sec=20",
        "--config", "mcp_servers.linear.tool_timeout_sec=90",
        "--config", "mcp_servers.linear.default_tools_approval_mode=`"approve`"",
        "--output-last-message", $lastMessageRelative,
        "-"
    )

    Write-Host ""
    Write-Host "Starting $Label with $Model / $ReasoningEffort (timeout: $TimeoutMinutes minute(s))..."
    $processResult = Invoke-RalphProcess `
        -FilePath "sbx" `
        -Arguments $arguments `
        -InputText $Prompt `
        -TimeoutSeconds ($TimeoutMinutes * 60) `
        -LogPath $logPath

    $finalMessage = ""
    if (Test-Path -LiteralPath $lastMessagePath -PathType Leaf)
    {
        $finalMessage = Protect-RalphText -Text (Get-Content -Raw -LiteralPath $lastMessagePath)
        Set-Content -LiteralPath $lastMessagePath -Value $finalMessage -Encoding utf8
    }

    [pscustomobject]@{
        ExitCode = $processResult.ExitCode
        TimedOut = $processResult.TimedOut
        FinalMessage = $finalMessage
        LogPath = $logPath
        StartedAt = $processResult.StartedAt
        FinishedAt = $processResult.FinishedAt
    }
}

function Get-RalphCanonicalPrompt
{
    $text = Get-Content -Raw -LiteralPath $script:RalphPromptPath
    $match = [regex]::Match($text, '(?s)```text\s*(.*?)\s*```')
    if (-not $match.Success)
    {
        throw "Could not extract the text block from $script:RalphPromptPath."
    }
    return $match.Groups[1].Value.Trim()
}

function Get-RalphBoundedPrompt
{
    $canonical = Get-RalphCanonicalPrompt
    $markerInstructions = @'

Bounded Ralph controller requirement:
After the canonical RALPH_CHANGED_PATHS line, output exactly one additional line containing exactly one of these markers:
<RALPH_STATUS>READY_TO_COMMIT</RALPH_STATUS>
<RALPH_STATUS>INCOMPLETE</RALPH_STATUS>
<RALPH_STATUS>BLOCKED</RALPH_STATUS>
<RALPH_STATUS>REVIEW_REQUIRED</RALPH_STATUS>

Use READY_TO_COMMIT only when the selected implementation child passes the readiness gate and its human-readable status is Ready to Commit.
Use INCOMPLETE when implementation or verification is incomplete.
Use BLOCKED when a blocker or inconsistent state prevents work.
Use REVIEW_REQUIRED only when all authorized implementation children are Done and M-27 is the next remaining work.
Do not output more than one RALPH_STATUS marker.
'@
    return $canonical + $markerInstructions
}

function Get-RalphBoundedStatus
{
    param([Parameter(Mandatory)][string]$FinalMessage)

    $matches = [regex]::Matches($FinalMessage, '<RALPH_STATUS>(READY_TO_COMMIT|INCOMPLETE|BLOCKED|REVIEW_REQUIRED)</RALPH_STATUS>')
    if ($matches.Count -ne 1)
    {
        return "MALFORMED"
    }
    return $matches[0].Groups[1].Value
}

function Get-RalphOnceStatus
{
    param([Parameter(Mandatory)][string]$FinalMessage)

    $matches = [regex]::Matches($FinalMessage, '(?m)^Status:\s*(Ready to Commit|Incomplete|Blocked|Review Required)\s*$')
    if ($matches.Count -ne 1)
    {
        return "MALFORMED"
    }

    $value = $matches[0].Groups[1].Value
    if ($value -eq "Ready to Commit") { return "READY_TO_COMMIT" }
    if ($value -eq "Incomplete") { return "INCOMPLETE" }
    if ($value -eq "Blocked") { return "BLOCKED" }
    if ($value -eq "Review Required") { return "REVIEW_REQUIRED" }
    return "MALFORMED"
}

function Get-RalphTaskIdentity
{
    param([Parameter(Mandatory)][string]$FinalMessage)

    $matches = [regex]::Matches($FinalMessage, '(?m)^Task:\s*(M-\d+)\s*(?:—|-)\s*(.+?)\s*$')
    if ($matches.Count -ne 1)
    {
        return $null
    }

    $match = $matches[0]

    [pscustomobject]@{
        Id = $match.Groups[1].Value
        Title = $match.Groups[2].Value.Trim()
    }
}

function Get-RalphReportedChangedPaths
{
    param([Parameter(Mandatory)][string]$FinalMessage)

    $matches = [regex]::Matches($FinalMessage, '(?m)^<RALPH_CHANGED_PATHS>(\[.*\])</RALPH_CHANGED_PATHS>\s*$')
    if ($matches.Count -ne 1)
    {
        throw "Ready-to-commit output must contain exactly one RALPH_CHANGED_PATHS JSON marker."
    }

    try
    {
        $decoded = @($matches[0].Groups[1].Value | ConvertFrom-Json -ErrorAction Stop)
    }
    catch
    {
        throw "RALPH_CHANGED_PATHS must contain a valid JSON array."
    }

    $paths = [System.Collections.Generic.List[string]]::new()
    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($item in $decoded)
    {
        if ($item -isnot [string])
        {
            throw "Every RALPH_CHANGED_PATHS item must be a string."
        }

        $path = ConvertTo-RalphGitPath -RelativePath ([string]$item)
        if (-not $seen.Add($path))
        {
            throw "RALPH_CHANGED_PATHS contains duplicate path '$path'."
        }
        $paths.Add($path)
    }

    return $paths.ToArray()
}

function ConvertTo-RalphGitPath
{
    param([Parameter(Mandatory)][string]$RelativePath)

    $normalized = $RelativePath.Replace('\', '/')
    while ($normalized.StartsWith("./", [StringComparison]::Ordinal))
    {
        $normalized = $normalized.Substring(2)
    }
    $wasRooted = [System.IO.Path]::IsPathRooted($normalized)
    $normalized = $normalized.TrimStart('/')

    if (
        [string]::IsNullOrWhiteSpace($normalized) -or
        $wasRooted -or
        $normalized -match '(^|/)\.\.($|/)'
    )
    {
        throw "Unsafe repository-relative Git path '$RelativePath'."
    }

    return $normalized
}

function Test-RalphSensitiveCommitPath
{
    param([Parameter(Mandatory)][string]$RelativePath)

    $normalized = ConvertTo-RalphGitPath -RelativePath $RelativePath
    $leaf = [System.IO.Path]::GetFileName($normalized)
    $lower = $normalized.ToLowerInvariant()
    $leafLower = $leaf.ToLowerInvariant()

    if ($lower -eq "resources/spotify-secrets.env") { return $true }
    if ($leafLower -eq ".env") { return $true }
    if ($leafLower.StartsWith(".env.") -and -not $leafLower.EndsWith(".example")) { return $true }
    if ($leafLower.EndsWith(".pem") -or $leafLower.EndsWith(".key")) { return $true }
    if ($leafLower.Contains("token-cache")) { return $true }
    return $false
}

function Get-RalphSafeIterationPaths
{
    param(
        [Parameter(Mandatory)]$Snapshot,
        [Parameter(Mandatory)][string[]]$ReportedPaths
    )

    $currentHead = (Invoke-RalphGit -Arguments @("rev-parse", "HEAD")).Text
    if ($currentHead -ne $Snapshot.Head)
    {
        throw "Codex changed Git HEAD or created a commit. Ralph will not rewrite that history automatically."
    }

    if ((Get-RalphCurrentBranch) -ne $Snapshot.Branch)
    {
        throw "Codex changed the current Git branch. Ralph will not commit or push from an unexpected branch."
    }

    $originUrl = (Invoke-RalphGit -Arguments @("remote", "get-url", "origin")).Text
    if ($originUrl -ne $Snapshot.OriginUrl)
    {
        throw "Codex changed the origin remote. Ralph will not use the modified remote."
    }

    if ((Get-RalphGitControlFingerprint) -ne $Snapshot.GitControlFingerprint)
    {
        throw "Codex changed repository-local Git configuration, attributes, or hooks."
    }

    $index = Invoke-RalphGit -Arguments @("diff", "--cached", "--quiet", "--exit-code") -AllowFailure
    if ($index.ExitCode -eq 1)
    {
        throw "Codex staged files even though the prompt forbids staging. Ralph stopped without committing."
    }
    if ($index.ExitCode -ne 0)
    {
        throw "Unable to verify the Git index after the Codex attempt."
    }

    foreach ($path in $Snapshot.PreexistingPaths.Keys)
    {
        $before = $Snapshot.PreexistingPaths[$path]
        $after = Get-RalphPathState -RelativePath $path
        if ($before -ne $after)
        {
            throw "Codex touched pre-existing dirty path '$path'. Ralph will not stage or commit overlapping work."
        }
    }

    $preexistingSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($path in $Snapshot.PreexistingPaths.Keys)
    {
        [void]$preexistingSet.Add([string]$path)
    }

    $paths = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in Get-RalphGitStatusEntries)
    {
        if ($preexistingSet.Contains($entry.Path))
        {
            continue
        }
        if (Test-RalphSensitiveCommitPath -RelativePath $entry.Path)
        {
            throw "Ralph refused to stage sensitive path '$($entry.Path)'."
        }
        if (-not $paths.Contains($entry.Path))
        {
            $paths.Add($entry.Path)
        }
    }

    $safePaths = $paths.ToArray()
    Assert-RalphPathSetMatches -ExpectedPaths $ReportedPaths -ActualPaths $safePaths -Context "Reported task manifest"
    return $safePaths
}

function Assert-RalphPathSetMatches
{
    param(
        [Parameter(Mandatory)][string[]]$ExpectedPaths,
        [Parameter(Mandatory)][string[]]$ActualPaths,
        [Parameter(Mandatory)][string]$Context
    )

    $expected = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($path in $ExpectedPaths)
    {
        [void]$expected.Add((ConvertTo-RalphGitPath -RelativePath $path))
    }

    $actual = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($path in $ActualPaths)
    {
        [void]$actual.Add((ConvertTo-RalphGitPath -RelativePath $path))
    }

    $matches = $expected.Count -eq $actual.Count
    if ($matches)
    {
        foreach ($path in $expected)
        {
            if (-not $actual.Contains($path))
            {
                $matches = $false
                break
            }
        }
    }

    if (-not $matches)
    {
        $expectedText = (@($expected) | Sort-Object) -join ", "
        $actualText = (@($actual) | Sort-Object) -join ", "
        throw "$Context path mismatch. Expected [$expectedText]; actual [$actualText]."
    }
}

function Assert-RalphStagedCommitCandidate
{
    param(
        [Parameter(Mandatory)][string[]]$ExpectedPaths,
        [Parameter(Mandatory)]$Snapshot
    )

    $staged = Invoke-RalphGit -Arguments @("-c", "core.quotepath=false", "diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB")
    $stagedPaths = @($staged.Output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($stagedPaths.Count -eq 0)
    {
        throw "No changes were staged for the completed task."
    }

    Assert-RalphPathSetMatches -ExpectedPaths $ExpectedPaths -ActualPaths $stagedPaths -Context "Staged commit"

    foreach ($stagedPath in $stagedPaths)
    {
        if (Test-RalphSensitiveCommitPath -RelativePath $stagedPath)
        {
            throw "A sensitive path reached the staging area: '$stagedPath'."
        }
    }

    $diffCheck = Invoke-RalphGit -Arguments @("diff", "--cached", "--check") -AllowFailure
    if ($diffCheck.ExitCode -ne 0)
    {
        throw "The staged diff failed git diff --cached --check.`n$($diffCheck.Text)"
    }

    $preexisting = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($path in $Snapshot.PreexistingPaths.Keys)
    {
        [void]$preexisting.Add((ConvertTo-RalphGitPath -RelativePath ([string]$path)))
    }

    foreach ($entry in Get-RalphGitStatusEntries)
    {
        $path = ConvertTo-RalphGitPath -RelativePath $entry.Path
        if ($entry.WorkTree -ne ' ' -and -not $preexisting.Contains($path))
        {
            throw "Task-owned path '$($entry.Path)' still has unstaged changes after exact-path staging."
        }
    }
}

function Assert-RalphNoActiveContentFilters
{
    param([Parameter(Mandatory)][string[]]$Paths)

    $attributes = Invoke-RalphGit -Arguments (@("check-attr", "filter", "--") + $Paths)
    foreach ($line in $attributes.Output)
    {
        if ($line -notmatch ': filter: (?:unspecified|unset)\s*$')
        {
            throw "Ralph refused to stage a path with an active Git content filter."
        }
    }
}

function Get-RalphStagedBlob
{
    param([Parameter(Mandatory)][string]$RelativePath)

    $path = ConvertTo-RalphGitPath -RelativePath $RelativePath
    $entry = Invoke-RalphGit -Arguments @("ls-files", "--stage", "--", $path)
    $lines = @($entry.Output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -eq 0)
    {
        return [pscustomobject]@{ Exists = $false; Bytes = [byte[]]@() }
    }
    if ($lines.Count -ne 1 -or $lines[0] -notmatch '^([0-9]{6}) ([0-9a-fA-F]{40,64}) 0\s')
    {
        throw "Unable to resolve one stage-zero Git blob for '$path'."
    }

    $mode = $Matches[1]
    $objectId = $Matches[2]
    if ($mode -notin @("100644", "100755"))
    {
        throw "Ralph refuses automatic commits containing non-regular Git entry '$path' (mode $mode)."
    }

    $blob = Invoke-RalphGitBytes -Arguments @("cat-file", "blob", $objectId)
    return [pscustomobject]@{ Exists = $true; Bytes = [byte[]]$blob.Bytes }
}

function ConvertFrom-RalphStagedTextBlob
{
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][byte[]]$Bytes,
        [Parameter(Mandatory)][string]$RelativePath
    )

    foreach ($value in $Bytes)
    {
        if (($value -lt 0x20 -and $value -notin @(0x09, 0x0A, 0x0D)) -or $value -eq 0x7F)
        {
            throw "Ralph refuses automatic commits containing non-text bytes in '$RelativePath'."
        }
    }

    try
    {
        $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
        return $strictUtf8.GetString($Bytes)
    }
    catch [System.Text.DecoderFallbackException]
    {
        throw "Ralph refuses automatic commits containing non-UTF-8 bytes in '$RelativePath'."
    }
}

function Assert-RalphStagedContentSafe
{
    param([Parameter(Mandatory)][string[]]$Paths)

    $numstat = Invoke-RalphGit -Arguments @("diff", "--cached", "--numstat", "--no-ext-diff")
    foreach ($line in $numstat.Output)
    {
        if ($line -match '^-\s+-\s+')
        {
            throw "Ralph refuses automatic commits containing binary file changes."
        }
    }

    foreach ($path in $Paths)
    {
        $blob = Get-RalphStagedBlob -RelativePath $path
        if (-not $blob.Exists)
        {
            continue
        }

        $blobText = ConvertFrom-RalphStagedTextBlob -Bytes $blob.Bytes -RelativePath $path
        foreach ($secret in Get-RalphKnownSecretValues)
        {
            if ($blobText.Contains($secret, [StringComparison]::Ordinal))
            {
                throw "Ralph detected a known secret value in staged file '$path'. The value was not logged."
            }
        }
    }

    $diff = Invoke-RalphGit -Arguments @("diff", "--cached", "--no-ext-diff", "--no-color", "--unified=0")
    $text = $diff.Text

    foreach ($secret in Get-RalphKnownSecretValues)
    {
        if ($text.Contains($secret, [StringComparison]::Ordinal))
        {
            throw "Ralph detected a known secret value in the staged diff. The value was not logged."
        }
    }

    foreach ($line in $diff.Output)
    {
        if (-not $line.StartsWith('+') -or $line.StartsWith('+++'))
        {
            continue
        }

        if ($line -match '-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----')
        {
            throw "Ralph detected private-key material in the staged diff."
        }

        if ($line -match '(?i)(?:SPOTIPY_CLIENT_SECRET|SPOTIFY_REFRESH_TOKEN|LINEAR_API_KEY|ACCESS_TOKEN|CLIENT_SECRET)\s*[:=]\s*["'']?([^"''\s#]+)')
        {
            $candidate = $Matches[1]
            if (
                $candidate.Length -ge 8 -and
                $candidate -notmatch '^(?:your_|example|placeholder|<|\$\{)'
            )
            {
                throw "Ralph detected credential-shaped content in the staged diff."
            }
        }

        if ($line -match '(?i)Bearer\s+[A-Za-z0-9._~+/-]{20,}')
        {
            throw "Ralph detected bearer-token-shaped content in the staged diff."
        }
    }
}

function Assert-RalphPostCommitState
{
    param(
        [Parameter(Mandatory)]$Snapshot,
        [Parameter(Mandatory)][string[]]$ExpectedPaths,
        [Parameter(Mandatory)][string]$PreviousHead,
        [Parameter(Mandatory)][string]$Commit,
        [Parameter(Mandatory)][string]$CommitMessage,
        [Parameter(Mandatory)][string]$StagedTree
    )

    if ($Commit -eq $PreviousHead)
    {
        throw "git commit did not advance HEAD."
    }

    $parent = (Invoke-RalphGit -Arguments @("rev-parse", "$Commit^" )).Text
    if ($parent -ne $PreviousHead)
    {
        throw "The automatic commit is not a single direct child of the validated task snapshot."
    }

    $subject = (Invoke-RalphGit -Arguments @("show", "-s", "--format=%s", $Commit)).Text
    if ($subject -ne $CommitMessage)
    {
        throw "The automatic commit subject does not match '$CommitMessage'."
    }

    $commitTree = (Invoke-RalphGit -Arguments @("rev-parse", "$Commit^{tree}")).Text
    if ($commitTree -ne $StagedTree)
    {
        throw "The committed tree does not match the tree validated before git commit."
    }

    $committed = Invoke-RalphGit -Arguments @("-c", "core.quotepath=false", "diff", "--no-ext-diff", "--name-only", "--diff-filter=ACDMRTUXB", $PreviousHead, $Commit)
    $committedPaths = @($committed.Output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    Assert-RalphPathSetMatches -ExpectedPaths $ExpectedPaths -ActualPaths $committedPaths -Context "Created commit"

    $index = Invoke-RalphGit -Arguments @("diff", "--cached", "--quiet", "--exit-code") -AllowFailure
    if ($index.ExitCode -ne 0)
    {
        throw "The Git index is not clean after the automatic commit."
    }

    $preexisting = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($path in $Snapshot.PreexistingPaths.Keys)
    {
        $before = $Snapshot.PreexistingPaths[$path]
        $after = Get-RalphPathState -RelativePath $path
        if ($before -ne $after)
        {
            throw "The commit workflow changed pre-existing dirty path '$path'."
        }
        [void]$preexisting.Add((ConvertTo-RalphGitPath -RelativePath ([string]$path)))
    }

    foreach ($entry in Get-RalphGitStatusEntries)
    {
        $path = ConvertTo-RalphGitPath -RelativePath $entry.Path
        if (-not $preexisting.Contains($path))
        {
            throw "The automatic commit left unexpected task-owned path '$($entry.Path)' dirty."
        }
    }
}

function Invoke-RalphCommit
{
    param(
        [Parameter(Mandatory)][string[]]$Paths,
        [Parameter(Mandatory)]$Task,
        [Parameter(Mandatory)]$Snapshot,
        [Parameter(Mandatory)]$CandidateStates
    )

    if ($Paths.Count -eq 0)
    {
        throw "The task reported Ready to Commit but produced no safe Git changes. Ralph will not create an empty commit."
    }

    $committed = $false
    $previousHead = $Snapshot.Head
    $commitMessage = "$($Task.Id): $($Task.Title)"
    try
    {
        $currentHead = (Invoke-RalphGit -Arguments @("rev-parse", "HEAD")).Text
        if ($currentHead -ne $previousHead)
        {
            throw "HEAD changed between task validation and the automatic commit transaction."
        }
        if ((Get-RalphCurrentBranch) -ne $Snapshot.Branch)
        {
            throw "The current branch changed before the automatic commit transaction."
        }
        if ((Invoke-RalphGit -Arguments @("remote", "get-url", "origin")).Text -ne $Snapshot.OriginUrl)
        {
            throw "The origin remote changed before the automatic commit transaction."
        }
        if ((Get-RalphGitControlFingerprint) -ne $Snapshot.GitControlFingerprint)
        {
            throw "Git configuration, attributes, or hooks changed before staging."
        }

        foreach ($path in $Paths)
        {
            if ((Get-RalphPathState -RelativePath $path) -ne $CandidateStates[$path])
            {
                throw "Task-owned path '$path' changed after the manifest was validated."
            }
        }

        Assert-RalphNoActiveContentFilters -Paths $Paths
        [void](Invoke-RalphGit -Arguments (@("add", "--") + $Paths))
        Assert-RalphStagedCommitCandidate -ExpectedPaths $Paths -Snapshot $Snapshot
        Assert-RalphStagedContentSafe -Paths $Paths
        $stagedTree = (Invoke-RalphGit -Arguments @("write-tree")).Text
        [void](Invoke-RalphGit -Arguments @("-c", "commit.gpgSign=false", "commit", "-m", $commitMessage))
        $committed = $true
        $commit = (Invoke-RalphGit -Arguments @("rev-parse", "HEAD")).Text
        Assert-RalphPostCommitState -Snapshot $Snapshot -ExpectedPaths $Paths -PreviousHead $previousHead -Commit $commit -CommitMessage $commitMessage -StagedTree $stagedTree
    }
    catch
    {
        if (-not $committed)
        {
            [void](Invoke-RalphGit -Arguments (@("reset", "--") + $Paths) -AllowFailure)
        }
        throw
    }

    return [pscustomobject]@{ Commit = $commit; Error = "" }
}

function Invoke-RalphPush
{
    param([Parameter(Mandatory)][string]$Branch)

    $delays = @(2, 5, 10)
    $lastPushError = ""
    for ($attempt = 1; $attempt -le [int]$script:RalphConfig.pushAttempts; $attempt++)
    {
        $push = Invoke-RalphGit -Arguments @("push", "-u", "origin", $Branch) -AllowFailure
        if ($push.ExitCode -eq 0)
        {
            return [pscustomobject]@{ Pushed = $true; Error = "" }
        }

        $lastPushError = $push.Text
        if ($attempt -lt [int]$script:RalphConfig.pushAttempts)
        {
            Start-Sleep -Seconds $delays[[Math]::Min($attempt - 1, $delays.Count - 1)]
        }
    }

    return [pscustomobject]@{
        Pushed = $false
        Error = $lastPushError
    }
}

function Invoke-RalphCompletionGitTransaction
{
    param(
        [Parameter(Mandatory)]$Result,
        [Parameter(Mandatory)]$Task,
        [Parameter(Mandatory)][string[]]$ReportedPaths
    )

    try
    {
        $paths = Get-RalphSafeIterationPaths -Snapshot $Result.Snapshot -ReportedPaths $ReportedPaths
        $candidateStates = @{}
        foreach ($path in $paths)
        {
            $candidateStates[$path] = Get-RalphPathState -RelativePath $path
        }
        $gitResult = Invoke-RalphCommit -Paths $paths -Task $Task -Snapshot $Result.Snapshot -CandidateStates $candidateStates
        return [pscustomobject]@{
            Success = $true
            Commit = $gitResult.Commit
            Error = $gitResult.Error
        }
    }
    catch
    {
        $head = Invoke-RalphGit -Arguments @("rev-parse", "HEAD") -AllowFailure
        $commit = if ($head.ExitCode -eq 0 -and $head.Text -ne $Result.Snapshot.Head) { $head.Text } else { $null }
        return [pscustomobject]@{
            Success = $false
            Commit = $commit
            Error = $_.Exception.Message
        }
    }
}

function Get-RalphLinearFinalizationPrompt
{
    param(
        [Parameter(Mandatory)]$Task,
        [Parameter(Mandatory)][string]$Commit
    )

    return @"
This is a narrow Linear-only finalization step for the Perfect Playlist Ralph runner.

Task ID: $($Task.Id)
Expected title: $($Task.Title)
Verified local commit: $Commit

Rules:
1. Do not modify repository files, Git state, GitHub, branches, pull requests, or any issue other than the task and its organizational parent.
2. Use only the configured Linear MCP server. Read the task and verify that its ID and title match exactly.
3. The task must be In Progress or already Done. If it is another state, make no changes and report failure.
4. Ensure the task has one comment containing the exact line "Ralph commit: $Commit". If that exact line already exists, do not add a duplicate.
5. Mark the task Done if it is still In Progress.
6. Read the task's parent and every child. Mark the parent Done only if every child is Done and the parent's acceptance criteria are satisfied; otherwise leave it In Progress.
7. Never modify or mark M-27 Done. Never implement another issue.
8. This operation must be idempotent so a retry after an uncertain response is safe.

After a concise report, output exactly one line:
<RALPH_LINEAR_FINALIZATION>COMPLETE</RALPH_LINEAR_FINALIZATION>

If any rule cannot be satisfied, make no further changes and output exactly one line:
<RALPH_LINEAR_FINALIZATION>FAILED</RALPH_LINEAR_FINALIZATION>
"@
}

function Get-RalphLinearVerificationPrompt
{
    param(
        [Parameter(Mandatory)]$Task,
        [Parameter(Mandatory)][string]$Commit
    )

    return @"
This is a read-only Linear reconciliation check for the Perfect Playlist Ralph runner.

Task ID: $($Task.Id)
Expected title: $($Task.Title)
Verified local commit: $Commit

Do not modify Linear, repository files, Git state, GitHub, branches, pull requests, or any other external state.

Use the configured Linear MCP server to read the task, its comments, its organizational parent, and every child of that parent. Then output exactly one marker:

- <RALPH_LINEAR_VERIFICATION>VERIFIED</RALPH_LINEAR_VERIFICATION> only when the task ID and title match, the task is Done, exactly one comment contains "Ralph commit: $Commit", and the parent state is correct for the current child states and parent acceptance criteria.
- <RALPH_LINEAR_VERIFICATION>IN_PROGRESS</RALPH_LINEAR_VERIFICATION> only when the task ID and title match and the task is still In Progress.
- <RALPH_LINEAR_VERIFICATION>INCONSISTENT</RALPH_LINEAR_VERIFICATION> for every other observed state.

Never modify or mark M-27 Done. Output exactly one verification marker.
"@
}

function Invoke-RalphLinearVerification
{
    param(
        [Parameter(Mandatory)]$Task,
        [Parameter(Mandatory)][string]$Commit,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$Mode,
        [Parameter(Mandatory)][int]$Iteration
    )

    $prompt = Get-RalphLinearVerificationPrompt -Task $Task -Commit $Commit
    $delays = @(2, 5, 10)
    $lastLogPath = $null

    for ($attemptNumber = 1; $attemptNumber -le [int]$script:RalphConfig.linearAttempts; $attemptNumber++)
    {
        $snapshot = New-RalphAttemptSnapshot
        $attempt = Invoke-RalphCodexAttempt `
            -Prompt $prompt `
            -Model $Model `
            -ReasoningEffort "medium" `
            -TimeoutMinutes ([int]$script:RalphConfig.bootstrapTimeoutMinutes) `
            -Label "$Mode-iteration-$Iteration-linear-verify-$attemptNumber"
        $lastLogPath = $attempt.LogPath

        if (Restore-RalphSecretIfChanged -Snapshot $snapshot.Secret)
        {
            return [pscustomobject]@{ Status = "UNKNOWN"; Error = "Spotify secret file changed during Linear verification; original bytes restored."; LogPath = $attempt.LogPath }
        }

        $changes = Get-RalphAttemptChangeReasons -Snapshot $snapshot
        if ($changes.Count -gt 0)
        {
            return [pscustomobject]@{ Status = "UNKNOWN"; Error = "Linear verification changed repository state: $($changes -join ', ')."; LogPath = $attempt.LogPath }
        }

        $markers = [regex]::Matches($attempt.FinalMessage, '<RALPH_LINEAR_VERIFICATION>(VERIFIED|IN_PROGRESS|INCONSISTENT)</RALPH_LINEAR_VERIFICATION>')
        if ($attempt.ExitCode -eq 0 -and -not $attempt.TimedOut -and $markers.Count -eq 1)
        {
            $value = $markers[0].Groups[1].Value
            if ($value -eq "VERIFIED")
            {
                return [pscustomobject]@{ Status = "VERIFIED"; Error = ""; LogPath = $attempt.LogPath }
            }
            if ($value -eq "IN_PROGRESS")
            {
                return [pscustomobject]@{ Status = "IN_PROGRESS"; Error = "Linear authoritatively remains In Progress."; LogPath = $attempt.LogPath }
            }
            return [pscustomobject]@{ Status = "UNKNOWN"; Error = "Linear reconciliation found an inconsistent task, comment, or parent state."; LogPath = $attempt.LogPath }
        }

        if ($attemptNumber -lt [int]$script:RalphConfig.linearAttempts)
        {
            Start-Sleep -Seconds $delays[[Math]::Min($attemptNumber - 1, $delays.Count - 1)]
        }
    }

    return [pscustomobject]@{ Status = "UNKNOWN"; Error = "Linear reconciliation could not obtain an authoritative read."; LogPath = $lastLogPath }
}

function Invoke-RalphLinearFinalization
{
    param(
        [Parameter(Mandatory)]$Task,
        [Parameter(Mandatory)][string]$Commit,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$Mode,
        [Parameter(Mandatory)][int]$Iteration
    )

    $prompt = Get-RalphLinearFinalizationPrompt -Task $Task -Commit $Commit
    $delays = @(2, 5, 10)
    $lastError = "Linear finalization failed, timed out, or returned an invalid marker."
    $safetyError = ""

    for ($attemptNumber = 1; $attemptNumber -le [int]$script:RalphConfig.linearAttempts; $attemptNumber++)
    {
        $snapshot = New-RalphAttemptSnapshot
        $attempt = Invoke-RalphCodexAttempt `
            -Prompt $prompt `
            -Model $Model `
            -ReasoningEffort "medium" `
            -TimeoutMinutes ([int]$script:RalphConfig.bootstrapTimeoutMinutes) `
            -Label "$Mode-iteration-$Iteration-linear-finalize-$attemptNumber"

        if (Restore-RalphSecretIfChanged -Snapshot $snapshot.Secret)
        {
            $safetyError = "Spotify secret file changed during Linear finalization; original bytes restored."
            break
        }

        $changes = Get-RalphAttemptChangeReasons -Snapshot $snapshot
        if ($changes.Count -gt 0)
        {
            $safetyError = "Linear finalization changed repository state: $($changes -join ', ')."
            break
        }

        $markers = [regex]::Matches($attempt.FinalMessage, '<RALPH_LINEAR_FINALIZATION>(COMPLETE|FAILED)</RALPH_LINEAR_FINALIZATION>')
        if (
            $attempt.ExitCode -eq 0 -and
            -not $attempt.TimedOut -and
            $markers.Count -eq 1 -and
            $markers[0].Groups[1].Value -eq "COMPLETE"
        )
        {
            break
        }

        if ($attemptNumber -lt [int]$script:RalphConfig.linearAttempts)
        {
            Start-Sleep -Seconds $delays[[Math]::Min($attemptNumber - 1, $delays.Count - 1)]
        }
    }

    $verification = Invoke-RalphLinearVerification -Task $Task -Commit $Commit -Model $Model -Mode $Mode -Iteration $Iteration
    if ($safetyError)
    {
        $verificationDetail = if ($verification.Error) { $verification.Error } else { "Independent Linear state: $($verification.Status)." }
        return [pscustomobject]@{
            Success = $false
            LinearState = $verification.Status
            Error = "$safetyError $verificationDetail"
            LogPath = $verification.LogPath
        }
    }

    if ($verification.Status -eq "VERIFIED")
    {
        return [pscustomobject]@{ Success = $true; LinearState = "VERIFIED"; Error = ""; LogPath = $verification.LogPath }
    }

    $error = if ($verification.Error) { $verification.Error } else { $lastError }
    return [pscustomobject]@{ Success = $false; LinearState = $verification.Status; Error = $error; LogPath = $verification.LogPath }
}

function Write-RalphLatestState
{
    param(
        [Parameter(Mandatory)][int]$Iteration,
        [AllowNull()][string]$Task,
        [Parameter(Mandatory)][string]$Status,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$ReasoningEffort,
        [AllowNull()][string]$Commit,
        [Parameter(Mandatory)][bool]$Pushed,
        [AllowNull()][string]$LogPath,
        [AllowNull()][string]$Message
    )

    [pscustomobject]@{
        iteration = $Iteration
        task = $Task
        status = $Status
        model = $Model
        reasoningEffort = $ReasoningEffort
        commit = $Commit
        pushed = $Pushed
        log = if ($LogPath) { [System.IO.Path]::GetRelativePath($script:RalphRepositoryRoot, $LogPath).Replace('\', '/') } else { $null }
        message = $Message
        updatedAt = [DateTimeOffset]::Now.ToString("o")
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $script:RalphLatestStatePath -Encoding utf8
}

function Invoke-RalphReadyTaskCompletion
{
    param(
        [Parameter(Mandatory)]$Result,
        [Parameter(Mandatory)]$Task,
        [Parameter(Mandatory)][string[]]$ReportedPaths,
        [Parameter(Mandatory)][string]$Branch,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$Mode,
        [Parameter(Mandatory)][int]$Iteration
    )

    $gitResult = Invoke-RalphCompletionGitTransaction -Result $Result -Task $Task -ReportedPaths $ReportedPaths
    if (-not $gitResult.Success)
    {
        Write-RalphLatestState -Iteration $Iteration -Task $Task.Id -Status "COMMIT_FAILED" -Model $Model -ReasoningEffort $Result.Effort -Commit $gitResult.Commit -Pushed $false -LogPath $Result.Attempt.LogPath -Message $gitResult.Error
        return [pscustomobject]@{ Status = "COMMIT_FAILED"; Commit = $gitResult.Commit; Error = $gitResult.Error }
    }

    Write-RalphLatestState -Iteration $Iteration -Task $Task.Id -Status "COMMITTED_PENDING_LINEAR" -Model $Model -ReasoningEffort $Result.Effort -Commit $gitResult.Commit -Pushed $false -LogPath $Result.Attempt.LogPath -Message "The verified local commit exists; Linear finalization and push are pending."

    $linearResult = Invoke-RalphLinearFinalization -Task $Task -Commit $gitResult.Commit -Model $Model -Mode $Mode -Iteration $Iteration
    if (-not $linearResult.Success)
    {
        $status = if ($linearResult.LinearState -eq "IN_PROGRESS") { "LINEAR_FINALIZE_FAILED" } else { "LINEAR_FINALIZE_UNKNOWN" }
        Write-RalphLatestState -Iteration $Iteration -Task $Task.Id -Status $status -Model $Model -ReasoningEffort $Result.Effort -Commit $gitResult.Commit -Pushed $false -LogPath $linearResult.LogPath -Message $linearResult.Error
        return [pscustomobject]@{ Status = $status; Commit = $gitResult.Commit; Error = $linearResult.Error }
    }

    $pushResult = Invoke-RalphPush -Branch $Branch
    if (-not $pushResult.Pushed)
    {
        Write-RalphLatestState -Iteration $Iteration -Task $Task.Id -Status "PUSH_FAILED" -Model $Model -ReasoningEffort $Result.Effort -Commit $gitResult.Commit -Pushed $false -LogPath $linearResult.LogPath -Message $pushResult.Error
        return [pscustomobject]@{ Status = "PUSH_FAILED"; Commit = $gitResult.Commit; Error = $pushResult.Error }
    }

    Write-RalphLatestState -Iteration $Iteration -Task $Task.Id -Status "COMPLETE" -Model $Model -ReasoningEffort $Result.Effort -Commit $gitResult.Commit -Pushed $true -LogPath $linearResult.LogPath -Message ""
    return [pscustomobject]@{ Status = "COMPLETE"; Commit = $gitResult.Commit; Error = "" }
}

function Test-RalphSandboxExists
{
    $output = @(& sbx ls 2>&1)
    if ($LASTEXITCODE -ne 0)
    {
        return $false
    }

    $text = $output -join "`n"
    $escapedName = [regex]::Escape([string]$script:RalphConfig.sandboxName)
    return $text -match "(?m)^\s*$escapedName(?:\s|$)"
}

function Invoke-RalphBootstrap
{
    param([Parameter(Mandatory)][string]$Model)

    Write-Host "Running one-time sandbox, dependency, Codex, and Linear MCP bootstrap check..."
    $snapshot = New-RalphAttemptSnapshot
    $prompt = @'
This is a read-only Ralph bootstrap check. Do not modify repository files, Git state, GitHub, or any Linear issue.

1. Verify Python is available.
2. Ensure this project and its development dependencies are usable. If needed, run: python -m pip install -e ".[dev,yaml]"
3. Verify pytest, ruff, mypy, and the perfect_playlist package can be imported or invoked.
4. Use the Linear MCP server to read issue M-115 without changing it.
5. If every check succeeds, reply with exactly RALPH_BOOTSTRAP_OK and nothing else.
'@

    $attempt = Invoke-RalphCodexAttempt `
        -Prompt $prompt `
        -Model $Model `
        -ReasoningEffort "medium" `
        -TimeoutMinutes ([int]$script:RalphConfig.bootstrapTimeoutMinutes) `
        -Label "bootstrap"

    $secretChanged = Restore-RalphSecretIfChanged -Snapshot $snapshot.Secret
    if ($secretChanged)
    {
        throw "The Spotify secret file changed during bootstrap. Its original bytes were restored."
    }

    $changes = Get-RalphAttemptChangeReasons -Snapshot $snapshot
    if ($changes.Count -gt 0)
    {
        throw "Bootstrap changed the repository ($($changes -join ', ')). Review and clean the worktree before retrying."
    }

    if ($attempt.ExitCode -ne 0 -or $attempt.TimedOut -or $attempt.FinalMessage.Trim() -ne "RALPH_BOOTSTRAP_OK")
    {
        throw "Ralph bootstrap failed. Review '$($attempt.LogPath)' and verify OpenAI OAuth, the Linear Docker secret, model name, and Balanced network access."
    }

    [pscustomobject]@{
        sandbox = [string]$script:RalphConfig.sandboxName
        model = $Model
        completedAt = [DateTimeOffset]::Now.ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $script:RalphBootstrapStatePath -Encoding utf8
}

function Initialize-RalphEnvironment
{
    param(
        [Parameter(Mandatory)][string]$Model,
        [switch]$ForceBootstrap
    )

    Assert-RalphHost
    Assert-RalphRepository
    Initialize-RalphDirectories
    Assert-RalphSecretFileSafety

    $sandboxExists = Test-RalphSandboxExists
    $bootstrapExists = Test-Path -LiteralPath $script:RalphBootstrapStatePath -PathType Leaf
    if ($ForceBootstrap -or -not $sandboxExists -or -not $bootstrapExists)
    {
        Invoke-RalphBootstrap -Model $Model
    }

    return 0
}

function Test-RalphLocalBranchExists
{
    param([Parameter(Mandatory)][string]$Branch)
    $result = Invoke-RalphGit -Arguments @("show-ref", "--verify", "--quiet", "refs/heads/$Branch") -AllowFailure
    return $result.ExitCode -eq 0
}

function Test-RalphRemoteBranchExists
{
    param([Parameter(Mandatory)][string]$Branch)
    $result = Invoke-RalphGit -Arguments @("show-ref", "--verify", "--quiet", "refs/remotes/origin/$Branch") -AllowFailure
    return $result.ExitCode -eq 0
}

function Initialize-RalphBoundedBranch
{
    $branch = [string]$script:RalphConfig.boundedBranch
    [void](Invoke-RalphGit -Arguments @("fetch", "origin", "--prune"))
    $current = Get-RalphCurrentBranch
    $dirty = (Get-RalphGitStatusEntries).Count -gt 0

    if (-not (Test-RalphLocalBranchExists -Branch $branch))
    {
        if ($dirty)
        {
            throw "The '$branch' branch does not exist locally and the current branch is dirty. Commit/stash the work or create/switch branches manually."
        }

        if (Test-RalphRemoteBranchExists -Branch $branch)
        {
            [void](Invoke-RalphGit -Arguments @("switch", "-c", $branch, "--track", "origin/$branch"))
        }
        else
        {
            [void](Invoke-RalphGit -Arguments @("switch", "-c", $branch))
        }
    }
    elseif ($current -ne $branch)
    {
        if ($dirty)
        {
            throw "Bounded Ralph is not on '$branch' and the worktree is dirty. Switch manually after preserving your work."
        }
        [void](Invoke-RalphGit -Arguments @("switch", $branch))
    }

    if (Test-RalphRemoteBranchExists -Branch $branch)
    {
        $local = (Invoke-RalphGit -Arguments @("rev-parse", "HEAD")).Text
        $remote = (Invoke-RalphGit -Arguments @("rev-parse", "origin/$branch")).Text
        if ($local -ne $remote)
        {
            $localIsAncestor = Invoke-RalphGit -Arguments @("merge-base", "--is-ancestor", $local, $remote) -AllowFailure
            $remoteIsAncestor = Invoke-RalphGit -Arguments @("merge-base", "--is-ancestor", $remote, $local) -AllowFailure

            if ($localIsAncestor.ExitCode -eq 0)
            {
                if ((Get-RalphGitStatusEntries).Count -gt 0)
                {
                    throw "origin/$branch is ahead, but the worktree is dirty. Fast-forward manually before running Ralph."
                }
                [void](Invoke-RalphGit -Arguments @("merge", "--ff-only", "origin/$branch"))
            }
            elseif ($remoteIsAncestor.ExitCode -eq 0)
            {
                throw "Local '$branch' is ahead of origin. Push or reconcile it manually before bounded Ralph."
            }
            else
            {
                throw "Local and remote '$branch' have diverged. Resolve the branch manually."
            }
        }
        return (Invoke-RalphGit -Arguments @("rev-parse", "origin/$branch")).Text
    }

    return $null
}

function Confirm-RalphRemoteStable
{
    param([AllowNull()][string]$ExpectedRemoteSha)

    $branch = [string]$script:RalphConfig.boundedBranch
    [void](Invoke-RalphGit -Arguments @("fetch", "origin", "--prune"))
    $remoteExists = Test-RalphRemoteBranchExists -Branch $branch

    if ($null -eq $ExpectedRemoteSha)
    {
        if ($remoteExists)
        {
            throw "origin/$branch appeared after this bounded run started. Stop and inspect the remote change."
        }
        return
    }

    if (-not $remoteExists)
    {
        throw "origin/$branch disappeared during the bounded run."
    }

    $actual = (Invoke-RalphGit -Arguments @("rev-parse", "origin/$branch")).Text
    if ($actual -ne $ExpectedRemoteSha)
    {
        throw "origin/$branch changed during the bounded run. Expected $ExpectedRemoteSha, found $actual."
    }
}

function Invoke-RalphTaskAttemptWithOptionalRetry
{
    param(
        [Parameter(Mandatory)][string]$Prompt,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$InitialEffort,
        [Parameter(Mandatory)][string]$Mode,
        [Parameter(Mandatory)][int]$Iteration,
        [Parameter(Mandatory)][bool]$AllowRetry
    )

    $effort = $InitialEffort
    $timeout = if ($effort -eq "high" -or $effort -eq "xhigh") {
        [int]$script:RalphConfig.highTimeoutMinutes
    } else {
        [int]$script:RalphConfig.mediumTimeoutMinutes
    }

    $snapshot = New-RalphAttemptSnapshot
    $attempt = Invoke-RalphCodexAttempt `
        -Prompt $Prompt `
        -Model $Model `
        -ReasoningEffort $effort `
        -TimeoutMinutes $timeout `
        -Label "$Mode-iteration-$Iteration"

    $secretChanged = Restore-RalphSecretIfChanged -Snapshot $snapshot.Secret
    if ($secretChanged)
    {
        return [pscustomobject]@{
            Status = "SAFETY_STOP"
            Attempt = $attempt
            Snapshot = $snapshot
            Effort = $effort
            Message = "Spotify secret file changed; original bytes restored."
        }
    }

    $status = if ($Mode -eq "bounded") {
        Get-RalphBoundedStatus -FinalMessage $attempt.FinalMessage
    } else {
        Get-RalphOnceStatus -FinalMessage $attempt.FinalMessage
    }

    $attemptHealthy = $attempt.ExitCode -eq 0 -and -not $attempt.TimedOut
    $statusRecognized = $status -in @("READY_TO_COMMIT", "INCOMPLETE", "BLOCKED", "REVIEW_REQUIRED")

    if ($attemptHealthy -and $statusRecognized)
    {
        return [pscustomobject]@{
            Status = $status
            Attempt = $attempt
            Snapshot = $snapshot
            Effort = $effort
            Message = ""
        }
    }

    if (-not $AllowRetry)
    {
        $failureStatus = if ($attemptHealthy) { "MALFORMED" } else { "EXECUTION_FAILED" }
        return [pscustomobject]@{
            Status = $failureStatus
            Attempt = $attempt
            Snapshot = $snapshot
            Effort = $effort
            Message = "Codex exited unsuccessfully, timed out, or did not produce a valid final status."
        }
    }

    $changes = Get-RalphAttemptChangeReasons -Snapshot $snapshot
    if ($changes.Count -gt 0)
    {
        return [pscustomobject]@{
            Status = "SAFETY_STOP"
            Attempt = $attempt
            Snapshot = $snapshot
            Effort = $effort
            Message = "The failed attempt changed the repository: $($changes -join ', ')."
        }
    }

    Write-Warning "The initial attempt failed without changing the repository. Retrying once with high reasoning and a 40-minute timeout."
    $retrySnapshot = New-RalphAttemptSnapshot
    $retryAttempt = Invoke-RalphCodexAttempt `
        -Prompt $Prompt `
        -Model $Model `
        -ReasoningEffort "high" `
        -TimeoutMinutes ([int]$script:RalphConfig.highTimeoutMinutes) `
        -Label "$Mode-iteration-$Iteration-retry"

    $retrySecretChanged = Restore-RalphSecretIfChanged -Snapshot $retrySnapshot.Secret
    if ($retrySecretChanged)
    {
        return [pscustomobject]@{
            Status = "SAFETY_STOP"
            Attempt = $retryAttempt
            Snapshot = $retrySnapshot
            Effort = "high"
            Message = "Spotify secret file changed during retry; original bytes restored."
        }
    }

    $retryStatus = if ($Mode -eq "bounded") {
        Get-RalphBoundedStatus -FinalMessage $retryAttempt.FinalMessage
    } else {
        Get-RalphOnceStatus -FinalMessage $retryAttempt.FinalMessage
    }

    $retryHealthy = $retryAttempt.ExitCode -eq 0 -and -not $retryAttempt.TimedOut
    $retryRecognized = $retryStatus -in @("READY_TO_COMMIT", "INCOMPLETE", "BLOCKED", "REVIEW_REQUIRED")
    $finalRetryStatus = if ($retryHealthy -and $retryRecognized) { $retryStatus } elseif ($retryHealthy) { "MALFORMED" } else { "EXECUTION_FAILED" }
    $retryMessage = if ($finalRetryStatus -in @("MALFORMED", "EXECUTION_FAILED")) {
        "The Luna High recovery attempt failed or did not produce a valid final status."
    } else {
        ""
    }

    return [pscustomobject]@{
        Status = $finalRetryStatus
        Attempt = $retryAttempt
        Snapshot = $retrySnapshot
        Effort = "high"
        Message = $retryMessage
    }
}

function Invoke-RalphOnce
{
    param(
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$ReasoningEffort,
        [switch]$Retry
    )

    Enter-RalphLock
    try
    {
        Assert-RalphIndexClean
        [void](Initialize-RalphEnvironment -Model $Model)
        $branch = Get-RalphCurrentBranch
        $prompt = Get-RalphCanonicalPrompt

        $result = Invoke-RalphTaskAttemptWithOptionalRetry `
            -Prompt $prompt `
            -Model $Model `
            -InitialEffort $ReasoningEffort `
            -Mode "once" `
            -Iteration 1 `
            -AllowRetry $Retry.IsPresent

        if ($result.Status -eq "REVIEW_REQUIRED")
        {
            $reviewChanges = Get-RalphAttemptChangeReasons -Snapshot $result.Snapshot
            if ($reviewChanges.Count -gt 0)
            {
                Write-RalphLatestState -Iteration 1 -Task $null -Status "SAFETY_STOP" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message "Review Required result changed the repository: $($reviewChanges -join ', ')."
                Write-Warning "Ralph reported Review Required but changed repository state. Review the worktree manually."
                return 2
            }
            Write-RalphLatestState -Iteration 1 -Task $null -Status "REVIEW_REQUIRED" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message "M-27 requires independent review."
            Write-Host "Implementation is complete. M-27 requires independent review; Ralph did not run it."
            return 0
        }

        if ($result.Status -ne "READY_TO_COMMIT")
        {
            Write-RalphLatestState -Iteration 1 -Task $null -Status $result.Status -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message $result.Message
            Write-Warning "RalphOnce stopped with status $($result.Status). No commit or push was performed."
            return 2
        }

        $task = Get-RalphTaskIdentity -FinalMessage $result.Attempt.FinalMessage
        if ($null -eq $task)
        {
            Write-RalphLatestState -Iteration 1 -Task $null -Status "MALFORMED" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message "Missing Task line."
            Write-Host "The result was Ready to Commit but its Task line could not be parsed." -ForegroundColor Red
            return 2
        }

        try
        {
            $reportedPaths = @(Get-RalphReportedChangedPaths -FinalMessage $result.Attempt.FinalMessage)
            if ($reportedPaths.Count -eq 0)
            {
                throw "Ready-to-commit output reported an empty changed-path manifest."
            }
        }
        catch
        {
            Write-RalphLatestState -Iteration 1 -Task $task.Id -Status "MALFORMED" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message $_.Exception.Message
            Write-Host $_.Exception.Message -ForegroundColor Red
            return 2
        }

        $completion = Invoke-RalphReadyTaskCompletion -Result $result -Task $task -ReportedPaths $reportedPaths -Branch $branch -Model $Model -Mode "once" -Iteration 1
        if ($completion.Status -eq "COMMIT_FAILED")
        {
            Write-Host "Automatic commit-on-ready failed. Ralph stopped before Linear finalization and push. $($completion.Error)" -ForegroundColor Red
            return 4
        }
        if ($completion.Status -eq "LINEAR_FINALIZE_FAILED")
        {
            Write-Host "The verified local commit exists, but Linear finalization failed. Linear remains In Progress and no push was attempted. $($completion.Error)" -ForegroundColor Red
            return 5
        }
        if ($completion.Status -eq "LINEAR_FINALIZE_UNKNOWN")
        {
            Write-Host "The verified local commit exists, but Linear reconciliation could not determine the authoritative state. No push was attempted. $($completion.Error)" -ForegroundColor Red
            return 6
        }
        if ($completion.Status -eq "PUSH_FAILED")
        {
            Write-Host "The local commit was created and Linear was finalized, but push failed after three attempts. Push the commit manually." -ForegroundColor Red
            return 3
        }

        Write-Host "RalphOnce completed, committed, and pushed $($task.Id) on '$branch'."
        return 0
    }
    catch
    {
        Write-Host $_.Exception.Message -ForegroundColor Red
        return 1
    }
    finally
    {
        Exit-RalphLock
    }
}

function Invoke-RalphBounded
{
    param(
        [Parameter(Mandatory)][int]$Iterations,
        [Parameter(Mandatory)][string]$Model,
        [Parameter(Mandatory)][string]$ReasoningEffort
    )

    Enter-RalphLock
    try
    {
        Assert-RalphIndexClean
        [void](Initialize-RalphEnvironment -Model $Model)
        $expectedRemoteSha = Initialize-RalphBoundedBranch
        $prompt = Get-RalphBoundedPrompt

        for ($iteration = 1; $iteration -le $Iterations; $iteration++)
        {
            Write-Host ""
            Write-Host "================ Ralph $iteration / $Iterations ================"
            Assert-RalphIndexClean
            Confirm-RalphRemoteStable -ExpectedRemoteSha $expectedRemoteSha

            $result = Invoke-RalphTaskAttemptWithOptionalRetry `
                -Prompt $prompt `
                -Model $Model `
                -InitialEffort $ReasoningEffort `
                -Mode "bounded" `
                -Iteration $iteration `
                -AllowRetry $true

            if ($result.Status -eq "REVIEW_REQUIRED")
            {
                $reviewChanges = Get-RalphAttemptChangeReasons -Snapshot $result.Snapshot
                if ($reviewChanges.Count -gt 0)
                {
                    Write-RalphLatestState -Iteration $iteration -Task $null -Status "SAFETY_STOP" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message "Review Required result changed the repository: $($reviewChanges -join ', ')."
                    Write-Warning "Ralph reported Review Required but changed repository state. Review the worktree manually."
                    return 2
                }
                Write-RalphLatestState -Iteration $iteration -Task $null -Status "REVIEW_REQUIRED" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message "M-27 requires independent review."
                Write-Host "All authorized implementation work is complete. M-27 requires independent review."
                return 0
            }

            if ($result.Status -ne "READY_TO_COMMIT")
            {
                Write-RalphLatestState -Iteration $iteration -Task $null -Status $result.Status -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message $result.Message
                Write-Warning "Bounded Ralph stopped with status $($result.Status). No new iteration will start."
                return 2
            }

            $task = Get-RalphTaskIdentity -FinalMessage $result.Attempt.FinalMessage
            if ($null -eq $task)
            {
                Write-RalphLatestState -Iteration $iteration -Task $null -Status "MALFORMED" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message "Missing Task line."
                Write-Host "The result was Ready to Commit but its Task line could not be parsed." -ForegroundColor Red
                return 2
            }

            try
            {
                $reportedPaths = @(Get-RalphReportedChangedPaths -FinalMessage $result.Attempt.FinalMessage)
                if ($reportedPaths.Count -eq 0)
                {
                    throw "Ready-to-commit output reported an empty changed-path manifest."
                }
            }
            catch
            {
                Write-RalphLatestState -Iteration $iteration -Task $task.Id -Status "MALFORMED" -Model $Model -ReasoningEffort $result.Effort -Commit $null -Pushed $false -LogPath $result.Attempt.LogPath -Message $_.Exception.Message
                Write-Host $_.Exception.Message -ForegroundColor Red
                return 2
            }

            $branch = [string]$script:RalphConfig.boundedBranch
            $completion = Invoke-RalphReadyTaskCompletion -Result $result -Task $task -ReportedPaths $reportedPaths -Branch $branch -Model $Model -Mode "bounded" -Iteration $iteration
            if ($completion.Status -eq "COMMIT_FAILED")
            {
                Write-Host "Automatic commit-on-ready failed. Bounded Ralph stopped before Linear finalization and push. $($completion.Error)" -ForegroundColor Red
                return 4
            }
            if ($completion.Status -eq "LINEAR_FINALIZE_FAILED")
            {
                Write-Host "The verified local commit exists, but Linear finalization failed. Linear remains In Progress and no push was attempted. $($completion.Error)" -ForegroundColor Red
                return 5
            }
            if ($completion.Status -eq "LINEAR_FINALIZE_UNKNOWN")
            {
                Write-Host "The verified local commit exists, but Linear reconciliation could not determine the authoritative state. No push was attempted. $($completion.Error)" -ForegroundColor Red
                return 6
            }
            if ($completion.Status -eq "PUSH_FAILED")
            {
                Write-Host "The local commit was created and Linear was finalized, but push failed after three attempts. Push the commit manually." -ForegroundColor Red
                return 3
            }

            $expectedRemoteSha = $completion.Commit
            Write-Host "Completed, committed, and pushed $($task.Id)."
        }

        Write-Host "Reached the configured maximum of $Iterations successful iteration(s). More implementation work may remain."
        return 0
    }
    catch
    {
        Write-Host $_.Exception.Message -ForegroundColor Red
        return 1
    }
    finally
    {
        Exit-RalphLock
    }
}
