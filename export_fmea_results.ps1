#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Export all FMEA results to CSV for analysis in Excel
#>

$data = Get-Content .\metrics_data\fmea_test_results.json | ConvertFrom-Json

# DEDUPLICATE: Keep only the most recent entry for each unique label
Write-Host "Deduplicating entries..." -ForegroundColor Yellow
$uniqueData = @{}
foreach ($entry in $data) {
    $label = $entry.label
    if (-not $uniqueData.ContainsKey($label)) {
        $uniqueData[$label] = $entry
    } else {
        # Keep the more recent one
        if ($entry.timestamp -gt $uniqueData[$label].timestamp) {
            $uniqueData[$label] = $entry
        }
    }
}

$sortedData = $uniqueData.Values | Sort-Object timestamp

Write-Host "Found $($data.Count) total entries, $($sortedData.Count) unique labels" -ForegroundColor Cyan

# Export 1: Summary CSV
$summaryData = $sortedData | Select-Object `
    label,
    @{N="Commit";E={$_.commit_hash.Substring(0,8)}},
    @{N="Date";E={$_.timestamp.Substring(0,19)}},
    @{N="Reliability_Score";E={$_.reliability_score}},
    @{N="Tests_Passed";E={$_.passed}},
    @{N="Tests_Total";E={$_.total_tests}},
    @{N="Tests_Failed";E={$_.failed}},
    commit_message

$summaryData | Export-Csv -Path "fmea_summary.csv" -NoTypeInformation
Write-Host "[OK] Exported summary to: fmea_summary.csv" -ForegroundColor Green

# Export 2: Detailed Test Results CSV
$detailedResults = @()

foreach ($entry in $sortedData) {
    $entry.test_results.PSObject.Properties | 
        Where-Object { $_.MemberType -eq 'NoteProperty' } |
        ForEach-Object {
            $detailedResults += [PSCustomObject]@{
                Label = $entry.label
                Commit = $entry.commit_hash.Substring(0,8)
                Date = $entry.timestamp.Substring(0,19)
                TestName = $_.Name
                Outcome = $_.Value.outcome
                Duration = $_.Value.duration
            }
        }
}

$detailedResults | Export-Csv -Path "fmea_detailed.csv" -NoTypeInformation
Write-Host "[OK] Exported detailed results to: fmea_detailed.csv" -ForegroundColor Green

# Export 3: Test Progression Matrix (FIXED - handles duplicates)
$allTestNames = @{}
foreach ($entry in $sortedData) {
    $entry.test_results.PSObject.Properties | 
        Where-Object { $_.MemberType -eq 'NoteProperty' } | 
        ForEach-Object { $allTestNames[$_.Name] = $true }
}

$matrixData = @()
foreach ($testName in ($allTestNames.Keys | Sort-Object)) {
    $row = [PSCustomObject]@{ TestName = $testName }
    
    foreach ($entry in $sortedData) {
        $test = $entry.test_results.$testName
        $outcome = if ($test) { $test.outcome } else { "missing" }
        
        # Use unique column name with timestamp to avoid duplicates
        $columnName = "{0}_{1}" -f $entry.label, $entry.timestamp.Substring(0,10)
        $row | Add-Member -NotePropertyName $columnName -NotePropertyValue $outcome -Force
    }
    
    $matrixData += $row
}

$matrixData | Export-Csv -Path "fmea_progression.csv" -NoTypeInformation
Write-Host "[OK] Exported test progression to: fmea_progression.csv" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "All exports complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Files created:"
Write-Host "  1. fmea_summary.csv      - High-level metrics per commit"
Write-Host "  2. fmea_detailed.csv     - Individual test results"
Write-Host "  3. fmea_progression.csv  - Test outcomes across all commits"