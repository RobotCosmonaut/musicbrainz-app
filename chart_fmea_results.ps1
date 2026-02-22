#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate ASCII chart of reliability improvement over time
#>

$data = Get-Content .\metrics_data\fmea_test_results.json | ConvertFrom-Json
$sortedData = $data | Sort-Object timestamp

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RELIABILITY TREND CHART" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$maxScore = 100

# Draw chart
for ($y = $maxScore; $y -ge 0; $y -= 5) {
    $line = "{0,3}% |" -f $y
    
    foreach ($entry in $sortedData) {
        $score = [int]$entry.reliability_score
        if ($score -ge $y) {
            $line += "*"  # Changed from █ to *
        } else {
            $line += " "
        }
    }
    
    Write-Host $line
}

# X-axis
$line = "     +"
foreach ($entry in $sortedData) {
    $line += "-"
}
Write-Host $line

# Labels
$line = "      "
for ($i = 0; $i -lt $sortedData.Count; $i++) {
    $line += ($i + 1).ToString()
}
Write-Host $line

# Legend
Write-Host "`nLegend:"
for ($i = 0; $i -lt $sortedData.Count; $i++) {
    $entry = $sortedData[$i]
    $color = if ($entry.reliability_score -ge 90) { "Green" }
             elseif ($entry.reliability_score -ge 75) { "Yellow" }
             else { "Red" }
    
    Write-Host ("  {0}. {1,-25} {2,5:F1}% ({3})" -f ($i + 1), $entry.label, $entry.reliability_score, $entry.commit_hash.Substring(0,8)) -ForegroundColor $color
}