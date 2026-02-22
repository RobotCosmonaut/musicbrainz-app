#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Backup current FMEA results and start fresh
#>

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "FMEA FRESH START" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$metricsFile = ".\metrics_data\fmea_test_results.json"

if (Test-Path $metricsFile) {
    # Show current data
    $data = Get-Content $metricsFile | ConvertFrom-Json
    Write-Host "`nCurrent file contains:" -ForegroundColor Yellow
    Write-Host "  Total entries: $($data.Count)"
    Write-Host "  Unique labels: $(($data | Select-Object -ExpandProperty label -Unique).Count)"
    Write-Host "`nLabels:"
    $data | ForEach-Object {
        Write-Host ("    - {0,-30} {1}" -f $_.label, $_.timestamp.Substring(0,19))
    }
    
    # Confirm
    Write-Host "`nThis will backup and clear the current results." -ForegroundColor Yellow
    $confirm = Read-Host "Continue? (y/n)"
    
    if ($confirm -eq 'y') {
        # Backup
        $timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
        $backupFile = ".\metrics_data\fmea_test_results_backup_$timestamp.json"
        
        Copy-Item $metricsFile $backupFile
        Remove-Item $metricsFile
        
        Write-Host "`n✅ Backed up to: fmea_test_results_backup_$timestamp.json" -ForegroundColor Green
        Write-Host "✅ Original file removed" -ForegroundColor Green
        Write-Host "`nReady for fresh start!" -ForegroundColor Cyan
        Write-Host "`nNext steps:" -ForegroundColor Yellow
        Write-Host "  1. Run: .\run_retrospective_fmea.ps1 -OldCommit <hash> -OldLabel 'Initial_Commit'" -ForegroundColor Gray
        Write-Host "  2. This will create a clean fmea_test_results.json with just 2 entries" -ForegroundColor Gray
    } else {
        Write-Host "`nCancelled. No changes made." -ForegroundColor Yellow
    }
} else {
    Write-Host "`n✅ No existing file found. Ready for fresh start!" -ForegroundColor Green
}