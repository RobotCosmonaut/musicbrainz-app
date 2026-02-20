#!/usr/bin/env pwsh
param(
    [Parameter(Mandatory=$true)]
    [string]$Label,
    
    [Parameter(Mandatory=$true)]
    [string]$TestName
)

$data = Get-Content .\metrics_data\fmea_test_results.json | ConvertFrom-Json
$entry = $data | Where-Object { $_.label -eq $Label }

if (-not $entry) {
    Write-Host "[ERROR] Label '$Label' not found!" -ForegroundColor Red
    exit
}

$test = $entry.test_results.$TestName

if (-not $test) {
    Write-Host "[ERROR] Test '$TestName' not found!" -ForegroundColor Red
    Write-Host "`nAvailable tests:" -ForegroundColor Yellow
    $entry.test_results.PSObject.Properties.Name | Sort-Object | ForEach-Object {
        Write-Host "  - $_"
    }
    exit
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TEST DETAILS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Label:    $Label"
Write-Host "Test:     $TestName"
Write-Host "Outcome:  $($test.outcome)"
Write-Host "Duration: $($test.duration.ToString('F3'))s"

if ($test.error) {
    Write-Host "`nERROR DETAILS:" -ForegroundColor Red
    Write-Host $test.error
}