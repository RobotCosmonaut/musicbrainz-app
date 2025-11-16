# Automated Daily Flake8 Metrics Collection Script
# For Windows systems using PowerShell
#
# Setup for automated daily execution:
# 1. Open Task Scheduler
# 2. Create Basic Task
# 3. Name: "Orchestr8r Daily Metrics"
# 4. Trigger: Daily at desired time (e.g., 9:00 AM)
# 5. Action: Start a program
#    - Program: powershell.exe
#    - Arguments: -ExecutionPolicy Bypass -File "C:\path\to\run_daily_metrics.ps1"
# 6. Finish

# Configuration
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $ProjectDir "metrics_data\logs"
$LogFile = Join-Path $LogDir "metrics_$(Get-Date -Format 'yyyy-MM-dd').log"

# Create log directory if it doesn't exist
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Start logging
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$separator = "=" * 60

"$separator" | Tee-Object -FilePath $LogFile -Append
"Metrics Collection Started" | Tee-Object -FilePath $LogFile -Append
"Date: $timestamp" | Tee-Object -FilePath $LogFile -Append
"$separator" | Tee-Object -FilePath $LogFile -Append

# Navigate to project directory
Set-Location $ProjectDir

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    "Activating virtual environment..." | Tee-Object -FilePath $LogFile -Append
    & "venv\Scripts\Activate.ps1"
}
elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    "Activating virtual environment..." | Tee-Object -FilePath $LogFile -Append
    & ".venv\Scripts\Activate.ps1"
}

# Check if Flake8 is installed
$flake8Installed = Get-Command flake8 -ErrorAction SilentlyContinue
if (-not $flake8Installed) {
    "ERROR: Flake8 not found. Installing..." | Tee-Object -FilePath $LogFile -Append
    pip install -r requirements-metrics.txt 2>&1 | Tee-Object -FilePath $LogFile -Append
}

# Run metrics collection
"Running metrics collection..." | Tee-Object -FilePath $LogFile -Append
python collect_metrics.py 2>&1 | Tee-Object -FilePath $LogFile -Append

# Check if collection was successful
if ($LASTEXITCODE -eq 0) {
    "SUCCESS: Metrics collection completed" | Tee-Object -FilePath $LogFile -Append
    
    # Generate visualizations
    "Generating visualizations..." | Tee-Object -FilePath $LogFile -Append
    python visualize_metrics.py 2>&1 | Tee-Object -FilePath $LogFile -Append
    
    if ($LASTEXITCODE -eq 0) {
        "SUCCESS: Visualizations generated" | Tee-Object -FilePath $LogFile -Append
    }
    else {
        "WARNING: Visualization generation failed" | Tee-Object -FilePath $LogFile -Append
    }
}
else {
    "ERROR: Metrics collection failed" | Tee-Object -FilePath $LogFile -Append
    exit 1
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"$separator" | Tee-Object -FilePath $LogFile -Append
"Metrics Collection Finished" | Tee-Object -FilePath $LogFile -Append
"Date: $timestamp" | Tee-Object -FilePath $LogFile -Append
"$separator" | Tee-Object -FilePath $LogFile -Append

# Optional: Commit results to git
# Uncomment the following lines to automatically commit metrics to git
# git add metrics_data/
# git commit -m "Daily metrics update: $(Get-Date -Format 'yyyy-MM-dd')"
# git push

exit 0
