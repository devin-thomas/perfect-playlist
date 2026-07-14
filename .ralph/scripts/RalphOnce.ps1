#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$Model = "gpt-5.6-luna",

    [ValidateSet("minimal", "low", "medium", "high", "xhigh")]
    [string]$ReasoningEffort = "medium",

    [switch]$Retry
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $repositoryRoot
. (Join-Path $repositoryRoot ".ralph/Ralph.Core.ps1")

exit (Invoke-RalphOnce -Model $Model -ReasoningEffort $ReasoningEffort -Retry:$Retry)
