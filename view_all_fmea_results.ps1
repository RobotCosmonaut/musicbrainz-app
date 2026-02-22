#!/usr/bin/env pwsh
<#
.SYNOPSIS
    View all FMEA test results across all commits in a single dashboard
#>

$data = Get-Content .\metrics_data\fmea_test_results.json | ConvertFrom-Json

if ($data.Count -eq 0) {
    Write-Host "[ERROR] No test results found!" -ForegroundColor Red
    exit
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "FMEA RESULTS DASHBOARD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total test runs: $($data.Count)"
Write-Host ""

# Summary Table
Write-Host "SUMMARY TABLE" -ForegroundColor Yellow
Write-Host ("{0,-25} {1,-12} {2,-20} {3,-12} {4,-8} {5,-8}" -f "Label", "Commit", "Date", "Reliability", "Passed", "Total")
Write-Host ("{0,-25} {1,-12} {2,-20} {3,-12} {4,-8} {5,-8}" -f ("-" * 25), ("-" * 12), ("-" * 20), ("-" * 12), ("-" * 8), ("-" * 8))

# Sort by timestamp
$sortedData = $data | Sort-Object timestamp

foreach ($entry in $sortedData) {
    $label = $entry.label
    $commit = $entry.commit_hash.Substring(0, 8)
    $date = $entry.timestamp.Substring(0, 19)
    $reliability = "{0:F1}%" -f $entry.reliability_score
    $passed = $entry.passed
    $total = $entry.total_tests
    
    # Color code based on reliability
    $color = if ($entry.reliability_score -ge 90) { "Green" }
             elseif ($entry.reliability_score -ge 75) { "Yellow" }
             else { "Red" }
    
    $line = "{0,-25} {1,-12} {2,-20} {3,-12} {4,-8} {5,-8}" -f $label, $commit, $date, $reliability, $passed, $total
    Write-Host $line -ForegroundColor $color
}

# Trend Analysis
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TREND ANALYSIS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($sortedData.Count -ge 2) {
    $first = $sortedData[0]
    $latest = $sortedData[-1]
    
    $reliabilityChange = $latest.reliability_score - $first.reliability_score
    $testsChange = $latest.passed - $first.passed
    
    Write-Host "`nFirst Run:  $($first.label)"
    Write-Host "  Date:        $($first.timestamp.Substring(0, 19))"
    Write-Host "  Reliability: $($first.reliability_score.ToString('F1'))%"
    Write-Host "  Passed:      $($first.passed)/$($first.total_tests)"
    
    Write-Host "`nLatest Run: $($latest.label)"
    Write-Host "  Date:        $($latest.timestamp.Substring(0, 19))"
    Write-Host "  Reliability: $($latest.reliability_score.ToString('F1'))%"
    Write-Host "  Passed:      $($latest.passed)/$($latest.total_tests)"
    
    $sign = if ($reliabilityChange -ge 0) { "+" } else { "" }
    $color = if ($reliabilityChange -ge 0) { "Green" } else { "Red" }
    Write-Host "`nOverall Change:" -ForegroundColor Yellow
    Write-Host ("  Reliability: {0}{1:F1}%" -f $sign, $reliabilityChange) -ForegroundColor $color
    Write-Host ("  Tests Fixed: {0}{1}" -f $sign, $testsChange) -ForegroundColor $color
}

# Test-by-Test Comparison (All Commits)
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TEST PROGRESSION ACROSS COMMITS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Get all unique test names
$allTestNames = @{}
foreach ($entry in $sortedData) {
    $entry.test_results.PSObject.Properties | 
        Where-Object { $_.MemberType -eq 'NoteProperty' } | 
        ForEach-Object {
            $allTestNames[$_.Name] = $true
        }
}

# Build header with commit labels
$header = "{0,-45}" -f "Test Name"
foreach ($entry in $sortedData) {
    $shortLabel = if ($entry.label.Length -gt 12) { $entry.label.Substring(0, 9) + "..." } else { $entry.label }
    $header += " {0,-13}" -f $shortLabel
}
Write-Host "`n$header"

$separator = "{0,-45}" -f ("-" * 45)
foreach ($entry in $sortedData) {
    $separator += " {0,-13}" -f ("-" * 13)
}
Write-Host $separator

# Show each test across all commits
foreach ($testName in ($allTestNames.Keys | Sort-Object)) {
    $shortName = if ($testName.Length -gt 44) { $testName.Substring(0, 41) + "..." } else { $testName }
    $line = "{0,-45}" -f $shortName
    
    $hasImprovement = $false
    $outcomes = @()
    
    foreach ($entry in $sortedData) {
        $test = $entry.test_results.$testName
        if ($test) {
            $outcome = if ($test.outcome -eq "passed") { "PASS" } else { "FAIL" }
            $outcomes += $outcome
            $line += " {0,-13}" -f $outcome
        } else {
            $outcomes += "---"
            $line += " {0,-13}" -f "---"
        }
    }
    
    # Check if test improved (FAIL -> PASS)
    if ($outcomes.Count -ge 2) {
        for ($i = 0; $i -lt $outcomes.Count - 1; $i++) {
            if ($outcomes[$i] -eq "FAIL" -and $outcomes[$i + 1] -eq "PASS") {
                $hasImprovement = $true
                break
            }
        }
    }
    
    # Color code: Green if improved, Gray if stable pass, Red if currently failing
    $color = if ($hasImprovement) { "Green" }
             elseif ($outcomes[-1] -eq "PASS") { "Gray" }
             else { "Red" }
    
    Write-Host $line -ForegroundColor $color
}

# Export Option
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "EXPORT OPTIONS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "To export to CSV:" -ForegroundColor Yellow
Write-Host "  .\export_fmea_results.ps1" -ForegroundColor Gray
Write-Host "`nTo compare specific commits:" -ForegroundColor Yellow
Write-Host "  python run_fmea_tests.py --compare <label1> <label2>" -ForegroundColor Gray
Write-Host "`nTo view detailed test comparison:" -ForegroundColor Yellow
Write-Host "  .\analyze_tests.ps1 -OldLabel '<label>' -NewLabel '<label>'" -ForegroundColor Gray