#!/usr/bin/env pwsh
param(
    [Parameter(Mandatory=$true)]
    [string]$OldLabel,
    
    [Parameter(Mandatory=$true)]
    [string]$NewLabel,
    
    [string]$Filter = "*"
)

$data = Get-Content .\metrics_data\fmea_test_results.json | ConvertFrom-Json

# Handle multiple entries with same label - take the most recent
$old = $data | Where-Object { $_.label -eq $OldLabel } | Select-Object -Last 1
$new = $data | Where-Object { $_.label -eq $NewLabel } | Select-Object -Last 1

if (-not $old -or -not $new) {
    Write-Host "[ERROR] Label not found!" -ForegroundColor Red
    Write-Host "Available labels:"
    $data | ForEach-Object { 
        Write-Host ("  - {0,-30} {1}" -f $_.label, $_.timestamp.Substring(0,19))
    }
    exit
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DETAILED TEST COMPARISON" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ("Old: {0} ({1})" -f $OldLabel, $old.commit_hash.Substring(0,8))
Write-Host ("New: {0} ({1})" -f $NewLabel, $new.commit_hash.Substring(0,8))

# Get all test names (filter out array properties)
$oldTestNames = $old.test_results.PSObject.Properties | 
                Where-Object { $_.MemberType -eq 'NoteProperty' } | 
                Select-Object -ExpandProperty Name

$newTestNames = $new.test_results.PSObject.Properties | 
                Where-Object { $_.MemberType -eq 'NoteProperty' } | 
                Select-Object -ExpandProperty Name

$allTests = ($oldTestNames + $newTestNames) | 
            Select-Object -Unique | 
            Where-Object { $_ -like $Filter } | 
            Sort-Object

# Header
$headerLine = "{0,-50} {1,-10} {2,-10} {3}" -f "Test Name", "Old", "New", "Status"
Write-Host "`n$headerLine"
$separatorLine = "{0,-50} {1,-10} {2,-10} {3}" -f ("-" * 50), ("-" * 10), ("-" * 10), ("-" * 10)
Write-Host $separatorLine

$fixed = @()
$regressed = @()
$stable = @()
$stillFailing = @()

foreach ($testName in $allTests) {
    $oldTest = $old.test_results.$testName
    $newTest = $new.test_results.$testName
    
    $oldOutcome = if ($oldTest) { $oldTest.outcome } else { "missing" }
    $newOutcome = if ($newTest) { $newTest.outcome } else { "missing" }
    
    $oldStatus = if ($oldOutcome -eq "passed") { "PASS" } else { "FAIL" }
    $newStatus = if ($newOutcome -eq "passed") { "PASS" } else { "FAIL" }
    
    # Determine color and status
    if ($oldOutcome -ne "passed" -and $newOutcome -eq "passed") {
        $color = "Green"
        $status = "[FIXED]"
        $fixed += $testName
    }
    elseif ($oldOutcome -eq "passed" -and $newOutcome -ne "passed") {
        $color = "Red"
        $status = "[REGRESSED]"
        $regressed += $testName
    }
    elseif ($oldOutcome -eq "passed" -and $newOutcome -eq "passed") {
        $color = "Gray"
        $status = "[Stable]"
        $stable += $testName
    }
    else {
        $color = "DarkGray"
        $status = "[Still failing]"
        $stillFailing += $testName
    }
    
    $shortName = if ($testName.Length -gt 49) { $testName.Substring(0, 46) + "..." } else { $testName }
    $line = "{0,-50} {1,-10} {2,-10} {3}" -f $shortName, $oldStatus, $newStatus, $status
    Write-Host $line -ForegroundColor $color
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($fixed.Count -gt 0) {
    Write-Host "`n[FIXED] ($($fixed.Count) tests):" -ForegroundColor Green
    $fixed | ForEach-Object { Write-Host "   + $_" }
}

if ($regressed.Count -gt 0) {
    Write-Host "`n[REGRESSED] ($($regressed.Count) tests):" -ForegroundColor Red
    $regressed | ForEach-Object { Write-Host "   - $_" }
}

if ($stillFailing.Count -gt 0) {
    Write-Host "`n[Still Failing] ($($stillFailing.Count) tests):" -ForegroundColor Yellow
    $stillFailing | ForEach-Object { Write-Host "   ~ $_" }
}

Write-Host "`n[Stable] $($stable.Count) tests" -ForegroundColor Gray

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RELIABILITY SCORES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Safely handle reliability scores
$oldScore = [double]$old.reliability_score
$newScore = [double]$new.reliability_score
$improvement = $newScore - $oldScore

Write-Host ("Old: {0:F1}% ({1}/{2})" -f $oldScore, $old.passed, $old.total_tests)
Write-Host ("New: {0:F1}% ({1}/{2})" -f $newScore, $new.passed, $new.total_tests)

# Show improvement with proper sign
$sign = if ($improvement -ge 0) { "+" } else { "" }
$color = if ($improvement -ge 0) { "Green" } else { "Red" }
Write-Host ("Improvement: {0}{1:F1}%" -f $sign, $improvement) -ForegroundColor $color

# Footer
Write-Host "`nTo see error details for a specific test:" -ForegroundColor Yellow
Write-Host "  .\get_test_details.ps1 -Label '$OldLabel' -TestName 'test_name_here'" -ForegroundColor Gray