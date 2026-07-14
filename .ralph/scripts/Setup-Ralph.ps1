#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$Model = "gpt-5.6-luna",

    [switch]$SkipOpenAIOAuth,

    [switch]$SkipLinearSecret,

    [switch]$ForceBootstrap
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $repositoryRoot
. (Join-Path $repositoryRoot ".ralph/Ralph.Core.ps1")

Assert-RalphHost
Assert-RalphRepository
Initialize-RalphDirectories
Assert-RalphSecretFileSafety

if (-not $SkipOpenAIOAuth)
{
    Write-Host "Starting Docker's host-side OpenAI OAuth flow..."
    & sbx secret set -g openai --oauth
    if ($LASTEXITCODE -ne 0)
    {
        throw "OpenAI OAuth setup failed."
    }
}

if (-not $SkipLinearSecret)
{
    Write-Host ""
    Write-Host "Registering the scoped Linear API key from resources/spotify-secrets.env."
    Write-Host "Docker stores it as a custom proxy secret domain-scoped to mcp.linear.app; the agent receives only a placeholder."

    $plainValue = $null
    foreach ($line in Get-Content -LiteralPath $script:RalphSecretPath)
    {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#"))
        {
            continue
        }

        $parts = $line -split "=", 2
        if ($parts.Count -eq 2 -and $parts[0].Trim() -ceq "LINEAR_API_KEY")
        {
            $plainValue = $parts[1].Trim().Trim('"').Trim("'")
            break
        }
    }

    try
    {
        if ([string]::IsNullOrWhiteSpace($plainValue) -or $plainValue -ceq "value")
        {
            throw "LINEAR_API_KEY is missing or still uses the example placeholder in resources/spotify-secrets.env."
        }

        & sbx secret set-custom -g `
            --host mcp.linear.app `
            --env LINEAR_API_KEY `
            --value $plainValue

        if ($LASTEXITCODE -ne 0)
        {
            throw "Docker failed to store the Linear custom secret."
        }
    }
    finally
    {
        $plainValue = $null
    }
}

$code = Initialize-RalphEnvironment -Model $Model -ForceBootstrap:$ForceBootstrap
if ($code -ne 0)
{
    exit $code
}

Write-Host ""
Write-Host "Ralph setup is ready."
Write-Host "Try: pwsh .\.ralph\scripts\RalphOnce.ps1"
exit 0
