#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$Model = "gpt-5.6-luna",

    [ValidateSet("minimal", "low", "medium", "high", "xhigh")]
    [string]$ReasoningEffort = "medium",

    [switch]$Retry
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
. "$PSScriptRoot/.ralph/Ralph.Core.ps1"

exit (Invoke-RalphOnce -Model $Model -ReasoningEffort $ReasoningEffort -Retry:$Retry)
