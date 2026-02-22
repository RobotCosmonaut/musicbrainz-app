# cleanup_duplicates.ps1
$data = Get-Content .\metrics_data\fmea_test_results.json | ConvertFrom-Json

Write-Host "Original entries: $($data.Count)" -ForegroundColor Yellow

# Keep only most recent entry for each label
$uniqueData = @{}
foreach ($entry in $data) {
    $label = $entry.label
    if (-not $uniqueData.ContainsKey($label)) {
        $uniqueData[$label] = $entry
    } else {
        # Keep the more recent one
        if ($entry.timestamp -gt $uniqueData[$label].timestamp) {
            Write-Host "  Replacing duplicate: $label (keeping newer entry)" -ForegroundColor Cyan
            $uniqueData[$label] = $entry
        } else {
            Write-Host "  Skipping duplicate: $label (keeping existing entry)" -ForegroundColor Gray
        }
    }
}

$cleanData = $uniqueData.Values | Sort-Object timestamp

Write-Host "`nCleaned entries: $($cleanData.Count)" -ForegroundColor Yellow
Write-Host "Removed: $($data.Count - $cleanData.Count) duplicates" -ForegroundColor Green

# Backup original
Copy-Item .\metrics_data\fmea_test_results.json .\metrics_data\fmea_test_results.json.backup
Write-Host "`nBackup created: fmea_test_results.json.backup" -ForegroundColor Cyan

# Save cleaned data
$cleanData | ConvertTo-Json -Depth 10 | Set-Content .\metrics_data\fmea_test_results.json

Write-Host "Cleaned file saved!" -ForegroundColor Green
Write-Host "`nUnique labels remaining:"
$cleanData | ForEach-Object {
    Write-Host ("  - {0,-30} {1}" -f $_.label, $_.timestamp.Substring(0,19))
}