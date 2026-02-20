#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Runs COMPLETE reliability tests (FMEA + Reliability) against old and current commits

.PARAMETER OldCommit
    The commit hash to test against (can be partial)

.PARAMETER OldLabel
    Custom label for old commit results

.PARAMETER NewLabel
    Custom label for current commit results (default: "current")
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$OldCommit,

    [string]$OldLabel = "",
    [string]$NewLabel = "current"
)

# ─────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────

$CurrentDir   = Get-Location
$ProjectName  = Split-Path $CurrentDir -Leaf
$WorktreeDir  = "$($CurrentDir.Path)_old_$($OldCommit.Substring(0, [Math]::Min(8, $OldCommit.Length)))"

if ($OldLabel -eq "") {
    $OldLabel = "old_$($OldCommit.Substring(0, [Math]::Min(8, $OldCommit.Length)))"
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  Complete Retrospective Test Runner" -ForegroundColor Cyan
Write-Host "  (FMEA + Reliability Tests)" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "  Current project : $CurrentDir"    -ForegroundColor Gray
Write-Host "  Old commit      : $OldCommit"     -ForegroundColor Gray
Write-Host "  Worktree folder : $WorktreeDir"   -ForegroundColor Gray
Write-Host "  Old label       : $OldLabel"      -ForegroundColor Gray
Write-Host "  New label       : $NewLabel"      -ForegroundColor Gray
Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# STEP 1: VERIFY OLD COMMIT EXISTS
# ─────────────────────────────────────────────────────────────────────

Write-Host "[1/7] Verifying old commit exists..." -ForegroundColor Yellow

$CommitExists = git cat-file -t $OldCommit 2>&1
if ($CommitExists -ne "commit") {
    Write-Host "❌ Commit '$OldCommit' not found" -ForegroundColor Red
    exit 1
}

$FullOldHash = git rev-parse $OldCommit
Write-Host "   ✅ Found commit: $($FullOldHash.Substring(0,8))" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────
# STEP 2: CREATE WORKTREE
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[2/7] Creating isolated worktree..." -ForegroundColor Yellow

if (Test-Path $WorktreeDir) {
    Write-Host "      Removing existing worktree..." -ForegroundColor Gray
    git worktree remove $WorktreeDir --force 2>&1 | Out-Null
    Remove-Item -Path $WorktreeDir -Recurse -Force -ErrorAction SilentlyContinue
}

git worktree add $WorktreeDir $OldCommit

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create worktree" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Worktree created" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────
# STEP 3: INJECT TEST SCRIPTS INTO WORKTREE
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/7] Injecting test scripts into worktree..." -ForegroundColor Yellow

# Create test structure
New-Item -ItemType Directory -Path "$WorktreeDir\tests\fmea" -Force | Out-Null
New-Item -ItemType Directory -Path "$WorktreeDir\metrics_data" -Force | Out-Null

# Copy ALL test files (FMEA + Reliability)
$TestFilesToCopy = @{
    # FMEA tests
    "$CurrentDir\tests\fmea"                           = "$WorktreeDir\tests\fmea"
    
    # General reliability tests
    "$CurrentDir\tests\test_artist_service_reliability.py"         = "$WorktreeDir\tests\test_artist_service_reliability.py"
    "$CurrentDir\tests\test_album_service_reliability.py"          = "$WorktreeDir\tests\test_album_service_reliability.py"
    "$CurrentDir\tests\test_recommendation_service_reliability.py" = "$WorktreeDir\tests\test_recommendation_service_reliability.py"
    "$CurrentDir\tests\test_gateway_reliability.py"                = "$WorktreeDir\tests\test_gateway_reliability.py"
    "$CurrentDir\tests\test_database_reliability.py"               = "$WorktreeDir\tests\test_database_reliability.py"
    "$CurrentDir\tests\test_e2e_reliability.py"                    = "$WorktreeDir\tests\test_e2e_reliability.py"
    
    # Test infrastructure
    "$CurrentDir\tests\__init__.py"                    = "$WorktreeDir\tests\__init__.py"
    "$CurrentDir\tests\conftest.py"                    = "$WorktreeDir\tests\conftest.py"

    # Test runner script
    "$CurrentDir\run_all_reliability_tests.py"         = "$WorktreeDir\run_all_reliability_tests.py"
}

foreach ($Source in $TestFilesToCopy.Keys) {
    $Dest = $TestFilesToCopy[$Source]

    if (Test-Path $Source) {
        if ((Get-Item $Source).PSIsContainer) {
            # Directory
            Copy-Item -Path "$Source\*" -Destination $Dest -Recurse -Force
            Write-Host "   ✅ Copied: $(Split-Path $Source -Leaf)/" -ForegroundColor Green
        } else {
            # File
            Copy-Item -Path $Source -Destination $Dest -Force
            Write-Host "   ✅ Copied: $(Split-Path $Source -Leaf)" -ForegroundColor Green
        }
    } else {
        Write-Host "   ⚠️  Not found (skipping): $(Split-Path $Source -Leaf)" -ForegroundColor Yellow
    }
}

# ─────────────────────────────────────────────────────────────────────
# STEP 4: START OLD COMMIT SERVICES
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/7] Starting services from OLD commit..." -ForegroundColor Yellow

if (-not (Test-Path "$WorktreeDir\docker-compose.yml")) {
    Write-Host "   ⚠️  No docker-compose.yml in old commit" -ForegroundColor Yellow
} else {
    Set-Location $WorktreeDir
    docker-compose up --build -d

    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ⚠️  Services failed to start" -ForegroundColor Yellow
    } else {
        Write-Host "   Waiting 30 seconds for services..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
        Write-Host "   ✅ Services started" -ForegroundColor Green
    }

    Set-Location $CurrentDir
}

# ─────────────────────────────────────────────────────────────────────
# STEP 5: RUN COMPLETE TESTS AGAINST OLD COMMIT
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[5/7] Running COMPLETE tests against OLD commit..." -ForegroundColor Yellow
Write-Host "      (FMEA + Reliability tests)" -ForegroundColor Gray

Set-Location $WorktreeDir

python run_all_reliability_tests.py --label $OldLabel

# Copy metrics back to current project
$WorktreeMetrics = "$WorktreeDir\metrics_data\complete_reliability_results.json"
$CurrentMetrics  = "$CurrentDir\metrics_data\complete_reliability_results.json"

if (Test-Path $WorktreeMetrics) {
    $WorktreeData = Get-Content $WorktreeMetrics | ConvertFrom-Json
    
    if (Test-Path $CurrentMetrics) {
        $CurrentData = Get-Content $CurrentMetrics | ConvertFrom-Json
        $MergedData = $CurrentData + $WorktreeData
    } else {
        $MergedData = $WorktreeData
    }
    
    $MergedData | ConvertTo-Json -Depth 10 | Set-Content $CurrentMetrics
    Write-Host "   ✅ Old commit results saved" -ForegroundColor Green
}

# Stop old services
if (Test-Path "$WorktreeDir\docker-compose.yml") {
    docker-compose down
}

Set-Location $CurrentDir

# ─────────────────────────────────────────────────────────────────────
# STEP 6: RUN COMPLETE TESTS AGAINST CURRENT COMMIT
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[6/7] Running COMPLETE tests against CURRENT commit..." -ForegroundColor Yellow

# Start current services if not running
$GatewayRunning = $false
try {
    $Response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 3
    $GatewayRunning = $Response.StatusCode -eq 200
} catch {
    $GatewayRunning = $false
}

if (-not $GatewayRunning) {
    Write-Host "   Starting current project services..." -ForegroundColor Gray
    docker-compose up --build -d
    Start-Sleep -Seconds 30
}

# Run complete tests
python run_all_reliability_tests.py --label $NewLabel

# ─────────────────────────────────────────────────────────────────────
# STEP 7: COMPARE AND CLEAN UP
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[7/7] Comparing results and cleaning up..." -ForegroundColor Yellow

# Show comparison
python compare_complete_reliability.py $OldLabel $NewLabel

# Remove worktree
git worktree remove $WorktreeDir --force
Remove-Item -Path $WorktreeDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "  ✅ Complete retrospective test finished!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
Write-Host ""
Write-Host "  Results saved to:" -ForegroundColor Gray
Write-Host "  $CurrentDir\metrics_data\complete_reliability_results.json" -ForegroundColor Gray
Write-Host ""
Write-Host "  To view comparison again:" -ForegroundColor Gray
Write-Host "  python compare_complete_reliability.py $OldLabel $NewLabel" -ForegroundColor Gray
Write-Host ""