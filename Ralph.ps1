#requires -Version 7.0
[CmdletBinding()]
param(
    [ValidateRange(1, 100)]
    [int]$Iterations = 5,

    [string]$Model = "gpt-5.6-luna",

    [ValidateSet("minimal", "low", "medium", "high", "xhigh")]
    [string]$ReasoningEffort = "medium"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
. "$PSScriptRoot/.ralph/Ralph.Core.ps1"

exit (Invoke-RalphBounded -Iterations $Iterations -Model $Model -ReasoningEffort $ReasoningEffort)
