#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Runs FMEA tests against an older commit WITHOUT touching current files.

.DESCRIPTION
    Uses git worktree to check out the old commit into a SEPARATE directory.
    Your current project files, git history, and future commits are
    completely unaffected.

.PARAMETER OldCommit
    The commit hash to test against (can be partial, e.g. "a1b2c3d")

.EXAMPLE
    .\run_retrospective_fmea.ps1 -OldCommit "a1b2c3d"
    .\run_retrospective_fmea.ps1 -OldCommit "a1b2c3d" -OldLabel "before_recommendations"
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
$FmeaTestsDir = "$CurrentDir\tests\fmea"
$MetricsDir   = "$CurrentDir\metrics_data"

if ($OldLabel -eq "") {
    $OldLabel = "old_$($OldCommit.Substring(0, [Math]::Min(8, $OldCommit.Length)))"
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  Retrospective FMEA Test Runner (Safe Mode)" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "  Current project : $CurrentDir"    -ForegroundColor Gray
Write-Host "  Old commit      : $OldCommit"     -ForegroundColor Gray
Write-Host "  Worktree folder : $WorktreeDir"   -ForegroundColor Gray
Write-Host "  Old label       : $OldLabel"      -ForegroundColor Gray
Write-Host "  New label       : $NewLabel"      -ForegroundColor Gray
Write-Host ""
Write-Host "  ✅ Your current files will NOT be modified" -ForegroundColor Green
Write-Host "  ✅ Your git history will NOT be affected"   -ForegroundColor Green
Write-Host "  ✅ Your future commits will NOT be affected" -ForegroundColor Green
Write-Host ""

# ─────────────────────────────────────────────────────────────────────
# STEP 1: VERIFY OLD COMMIT EXISTS
# ─────────────────────────────────────────────────────────────────────

Write-Host "[1/7] Verifying old commit exists..." -ForegroundColor Yellow

$CommitExists = git cat-file -t $OldCommit 2>&1
if ($CommitExists -ne "commit") {
    Write-Host "❌ Commit '$OldCommit' not found in git history" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Recent commits:" -ForegroundColor Gray
    git log --oneline | Select-Object -First 10
    exit 1
}

$FullOldHash = git rev-parse $OldCommit
Write-Host "   ✅ Found commit: $($FullOldHash.Substring(0,8))" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────
# STEP 2: CREATE WORKTREE (separate folder, no current dir changes)
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[2/7] Creating isolated worktree for old commit..." -ForegroundColor Yellow

$WorktreeDir = "..\musicbrainz-app_old_$($OldCommit.Substring(0,8))"
Write-Host "      Location: $WorktreeDir" -ForegroundColor Gray

# Remove existing worktree if it exists from a previous run
if (Test-Path $WorktreeDir) {
    Write-Host "      Removing existing worktree from prior run..." -ForegroundColor Gray
    git worktree remove $WorktreeDir --force 2>&1 | Out-Null
    Remove-Item -Path $WorktreeDir -Recurse -Force -ErrorAction SilentlyContinue
}

# Create the worktree
git worktree add $WorktreeDir $OldCommit

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Failed to create worktree" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Worktree created" -ForegroundColor Green

# CAPTURE COMMIT HASH IMMEDIATELY (worktree exists now!)
Push-Location $WorktreeDir
$OldCommitHash = git rev-parse HEAD
Pop-Location

Write-Host "   Old commit hash: $OldCommitHash" -ForegroundColor Cyan

# ─────────────────────────────────────────────────────────────────────
# STEP 3: START OLD SERVICES (NO FILE COPYING!)
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/7] Starting OLD commit services..." -ForegroundColor Yellow
Write-Host "      (Tests will run from current directory)" -ForegroundColor Gray

# Stop current services first
Write-Host "   Stopping current services to free ports..." -ForegroundColor Gray
Set-Location $CurrentDir
docker-compose down 2>&1 | Out-Null
Start-Sleep -Seconds 5

if (-not (Test-Path "$WorktreeDir\docker-compose.yml")) {
    Write-Host "   ⚠️  No docker-compose.yml in old commit" -ForegroundColor Yellow
} else {
    # Build and start in worktree (NO test files copied, so Docker builds cleanly)
    Set-Location $WorktreeDir
    
    Write-Host "   Building old commit services..." -ForegroundColor Gray
    docker-compose build 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ❌ Build failed" -ForegroundColor Red
    } else {
        Write-Host "   Starting old commit services..." -ForegroundColor Gray
        docker-compose up -d 2>&1 | Out-Null
        
        Write-Host "   Waiting 30 seconds..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
        
        # Verify
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "   ✅ Old commit services running on localhost:8000-8003" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  Services not responding (tests will fail)" -ForegroundColor Yellow
        }
    }
    
    Set-Location $CurrentDir
}

# ─────────────────────────────────────────────────────────────────────
# STEP 4: RUN TESTS FROM CURRENT DIR AGAINST OLD SERVICES
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/7] Running FMEA tests against OLD commit services..." -ForegroundColor Yellow
Write-Host "      Testing commit: $OldCommitHash" -ForegroundColor Gray

# CRITICAL: Stay in current directory where test files exist
Set-Location $CurrentDir

# Run tests with the hash we captured in Step 2
python run_fmea_tests.py --label $OldLabel --commit-hash $OldCommitHash

Write-Host "   Old commit test results saved" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────
# STEP 5: STOP OLD SERVICES, START CURRENT SERVICES
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[5/7] Switching to current commit services..." -ForegroundColor Yellow

# Stop old services
if (Test-Path "$WorktreeDir\docker-compose.yml") {
    Write-Host "   Stopping old commit services..." -ForegroundColor Gray
    Set-Location $WorktreeDir
    docker-compose down 2>&1 | Out-Null
    Set-Location $CurrentDir
}

Start-Sleep -Seconds 5

# Start current services
Write-Host "   Starting current commit services..." -ForegroundColor Gray
docker-compose up -d 2>&1 | Out-Null
Start-Sleep -Seconds 30

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Current services running" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Services not responding" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────────────
# STEP 6: STOP OLD SERVICES, START CURRENT SERVICES, RUN TESTS
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[6/7] Stopping old services and running tests against CURRENT commit..." -ForegroundColor Yellow

# Stop old services if they're running
if (Test-Path "$WorktreeDir\docker-compose.yml") {
    Write-Host "   Stopping old commit services..." -ForegroundColor Gray
    Set-Location $WorktreeDir
    docker-compose down
    Set-Location $CurrentDir
    Start-Sleep -Seconds 5
}

# Start current project services
Write-Host "   Starting current project services..." -ForegroundColor Gray
docker-compose up --build -d
Start-Sleep -Seconds 30
Write-Host "   ✅ Current services started" -ForegroundColor Green

# Get current commit hash
$CurrentCommitHash = git rev-parse HEAD
Write-Host "      Testing commit: $CurrentCommitHash" -ForegroundColor Gray

# Run FMEA tests against current commit
python run_fmea_tests.py --label $NewLabel

# ─────────────────────────────────────────────────────────────────────
# STEP 7: COMPARE AND CLEAN UP
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[7/7] Comparing results and cleaning up..." -ForegroundColor Yellow

# Run comparison
python run_fmea_tests.py --compare $OldLabel $NewLabel

# Remove worktree (cleans up the separate folder)
git worktree remove $WorktreeDir --force
Remove-Item -Path $WorktreeDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "  ✅ Retrospective test complete!" -ForegroundColor Green
Write-Host "  ✅ Worktree cleaned up"          -ForegroundColor Green
Write-Host "  ✅ Current directory unchanged"  -ForegroundColor Green
Write-Host "  ✅ Git history unaffected"       -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
Write-Host ""
Write-Host "  Results saved to:" -ForegroundColor Gray
Write-Host "  $CurrentDir\metrics_data\fmea_test_results.json" -ForegroundColor Gray
Write-Host ""
Write-Host "  To view comparison again later:" -ForegroundColor Gray
Write-Host "  python run_fmea_tests.py --compare $OldLabel $NewLabel" -ForegroundColor Gray
Write-Host ""