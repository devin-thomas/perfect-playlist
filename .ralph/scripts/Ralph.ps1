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
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $repositoryRoot
. (Join-Path $repositoryRoot ".ralph/Ralph.Core.ps1")

exit (Invoke-RalphBounded -Iterations $Iterations -Model $Model -ReasoningEffort $ReasoningEffort)
