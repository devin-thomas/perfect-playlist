#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$Model = "gpt-5.6-luna",

    [switch]$SkipOpenAIOAuth,

    [switch]$SkipLinearSecret,

    [switch]$ForceBootstrap
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
. "$PSScriptRoot/.ralph/Ralph.Core.ps1"

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
    Write-Host "Paste the scoped Linear API key. Docker currently stores custom proxy secrets globally, domain-scoped to mcp.linear.app."
    Write-Host "The value is not written to the repository or to Ralph logs."

    $secureValue = Read-Host "Linear API key" -AsSecureString
    $plainValue = [System.Net.NetworkCredential]::new("", $secureValue).Password

    try
    {
        if ([string]::IsNullOrWhiteSpace($plainValue))
        {
            throw "No Linear API key was supplied."
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
        $secureValue = $null
    }
}

$code = Initialize-RalphEnvironment -Model $Model -ForceBootstrap:$ForceBootstrap
if ($code -ne 0)
{
    exit $code
}

Write-Host ""
Write-Host "Ralph setup is ready."
Write-Host "Try: pwsh .\RalphOnce.ps1"
exit 0
