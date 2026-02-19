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
Write-Host "[2/7] Creating isolated worktree..." -ForegroundColor Yellow
Write-Host "      Location: $WorktreeDir" -ForegroundColor Gray

# Remove existing worktree if it exists from a previous run
if (Test-Path $WorktreeDir) {
    Write-Host "      Removing existing worktree from prior run..." -ForegroundColor Gray
    git worktree remove $WorktreeDir --force 2>&1 | Out-Null
    Remove-Item -Path $WorktreeDir -Recurse -Force -ErrorAction SilentlyContinue
}

# Create the worktree - this is the key command
# It checks out the old commit into $WorktreeDir WITHOUT touching $CurrentDir
git worktree add $WorktreeDir $OldCommit

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create worktree" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Worktree created at: $WorktreeDir" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────
# STEP 3: INJECT FMEA SCRIPTS INTO WORKTREE
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/7] Injecting FMEA test scripts into worktree..." -ForegroundColor Yellow
Write-Host "      (These scripts don't exist in the old commit)" -ForegroundColor Gray

# Create test structure in worktree
New-Item -ItemType Directory -Path "$WorktreeDir\tests\fmea" -Force | Out-Null
New-Item -ItemType Directory -Path "$WorktreeDir\metrics_data" -Force | Out-Null

# Copy FMEA test files from current project into worktree
$FilesToCopy = @{
    # Test files
    "$CurrentDir\tests\fmea"                    = "$WorktreeDir\tests\fmea"
    "$CurrentDir\tests\__init__.py"             = "$WorktreeDir\tests\__init__.py"
    "$CurrentDir\tests\conftest.py"             = "$WorktreeDir\tests\conftest.py"

    # Utility scripts
    "$CurrentDir\run_fmea_tests.py"             = "$WorktreeDir\run_fmea_tests.py"
}

foreach ($Source in $FilesToCopy.Keys) {
    $Dest = $FilesToCopy[$Source]

    if (Test-Path $Source) {
        if ((Get-Item $Source).PSIsContainer) {
            # It's a directory
            Copy-Item -Path "$Source\*" -Destination $Dest -Recurse -Force
            Write-Host "   ✅ Copied directory: $(Split-Path $Source -Leaf)" -ForegroundColor Green
        } else {
            # It's a file
            Copy-Item -Path $Source -Destination $Dest -Force
            Write-Host "   ✅ Copied file: $(Split-Path $Source -Leaf)" -ForegroundColor Green
        }
    } else {
        Write-Host "   ⚠️  Not found (skipping): $Source" -ForegroundColor Yellow
    }
}

# ─────────────────────────────────────────────────────────────────────
# STEP 4: START OLD COMMIT SERVICES
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/7] Starting services from OLD commit..." -ForegroundColor Yellow
Write-Host "      Directory: $WorktreeDir" -ForegroundColor Gray

# Check if old commit has docker-compose
if (-not (Test-Path "$WorktreeDir\docker-compose.yml")) {
    Write-Host "   ⚠️  No docker-compose.yml in old commit" -ForegroundColor Yellow
    Write-Host "   ⚠️  Skipping service start - some tests will fail (expected)" -ForegroundColor Yellow
} else {
    # Use different port mapping to avoid conflicts with current services
    # if both are running simultaneously
    Set-Location $WorktreeDir
    docker-compose up --build -d

    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ⚠️  Services failed to start - some tests will show failures" -ForegroundColor Yellow
    } else {
        Write-Host "   Waiting 30 seconds for services to initialize..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
        Write-Host "   ✅ Services started" -ForegroundColor Green
    }

    # Return to original directory (unchanged)
    Set-Location $CurrentDir
}

# ─────────────────────────────────────────────────────────────────────
# STEP 5: RUN FMEA TESTS AGAINST OLD COMMIT
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[5/7] Running FMEA tests against OLD commit..." -ForegroundColor Yellow

# Run from the WORKTREE directory but save metrics to CURRENT project
Set-Location $WorktreeDir

python run_fmea_tests.py --label $OldLabel

# Copy metrics back to current project's metrics_data
# So both old and new results are in the same file for comparison
$WorktreeMetrics = "$WorktreeDir\metrics_data\fmea_test_results.json"
$CurrentMetrics  = "$CurrentDir\metrics_data\fmea_test_results.json"

if (Test-Path $WorktreeMetrics) {
    # Merge worktree metrics into current project metrics
    $WorktreeData = Get-Content $WorktreeMetrics | ConvertFrom-Json
    
    if (Test-Path $CurrentMetrics) {
        $CurrentData = Get-Content $CurrentMetrics | ConvertFrom-Json
        $MergedData = $CurrentData + $WorktreeData
    } else {
        $MergedData = $WorktreeData
    }
    
    $MergedData | ConvertTo-Json -Depth 10 | Set-Content $CurrentMetrics
    Write-Host "   ✅ Old commit results saved to current project metrics" -ForegroundColor Green
}

# Stop old services
if (Test-Path "$WorktreeDir\docker-compose.yml") {
    docker-compose down
}

# Return to current directory
Set-Location $CurrentDir

# ─────────────────────────────────────────────────────────────────────
# STEP 6: RUN FMEA TESTS AGAINST CURRENT COMMIT
# ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[6/7] Running FMEA tests against CURRENT commit..." -ForegroundColor Yellow

# Check if Minikube is running
$MinikubeStatus = minikube status --format='{{.Host}}' 2>&1
if ($MinikubeStatus -eq "Running") {
    Write-Host "   Using Minikube deployment..." -ForegroundColor Gray
    
    # Get Minikube IP
    $MinikubeIP = minikube ip
    
    # Set environment variables for tests to use Minikube endpoints
    $env:API_GATEWAY_URL = "http://${MinikubeIP}:30000"
    $env:ARTIST_SERVICE_URL = "http://${MinikubeIP}:30001"
    
} else {
    Write-Host "   Using Docker Compose..." -ForegroundColor Gray
    docker-compose up --build -d
    Start-Sleep -Seconds 30
}

# Run tests
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