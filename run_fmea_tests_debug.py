#!/usr/bin/env python3
"""Debug version that writes to file instead of console"""

import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path

# FORCE output to file
DEBUG_LOG = Path("fmea_debug.log")
def log(msg):
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")
    # Also try print
    print(msg, flush=True)

log("=" * 70)
log("SCRIPT STARTED")
log(f"Python version: {sys.version}")
log(f"Current directory: {Path.cwd()}")
log("=" * 70)

PROJECT_ROOT = Path(__file__).parent
METRICS_DIR = PROJECT_ROOT / "metrics_data"
FMEA_METRICS_FILE = METRICS_DIR / "fmea_test_results.json"

log(f"Project root: {PROJECT_ROOT}")
log(f"Metrics dir: {METRICS_DIR}")
log(f"Metrics file: {FMEA_METRICS_FILE}")

METRICS_DIR.mkdir(exist_ok=True)
log("Metrics directory created/verified")

# Try importing requests
try:
    import requests
    log("SUCCESS: requests imported")
except Exception as e:
    log(f"FAILED: requests import - {e}")

# Check services
log("\nChecking services...")
services = {
    "artist_service": "http://localhost:8001/health",
    "album_service": "http://localhost:8002/health",
}

for service, url in services.items():
    try:
        import requests
        response = requests.get(url, timeout=5)
        log(f"  {service}: {response.status_code}")
    except Exception as e:
        log(f"  {service}: FAILED - {e}")

# Try running pytest
log("\nRunning pytest...")
result = subprocess.run(
    ["pytest", "tests/fmea/", "-v", "--json-report", 
     f"--json-report-file={METRICS_DIR}/fmea_report.json"],
    capture_output=True,
    text=True,
    cwd=PROJECT_ROOT
)

log(f"Pytest return code: {result.returncode}")
log(f"Stdout length: {len(result.stdout)}")
log(f"Stderr length: {len(result.stderr)}")

if result.stdout:
    log("Pytest stdout:")
    log(result.stdout[-1000:]) # Last 1000 chars

if result.stderr:
    log("Pytest stderr (THE ERROR):")
    log(result.stderr)  

report_file = METRICS_DIR / "fmea_report.json"
log(f"\nChecking for report file: {report_file}")
log(f"File exists: {report_file.exists()}")

if report_file.exists():
    log("SUCCESS: Report file created!")
    with open(report_file) as f:
        report = json.load(f)
    
    summary = report.get("summary", {})
    log(f"Total tests: {summary.get('total', 0)}")
    log(f"Passed: {summary.get('passed', 0)}")
    log(f"Failed: {summary.get('failed', 0)}")
    
    # Save to metrics
    metrics = {
        "label": "debug_test",
        "timestamp": datetime.now().isoformat(),
        "total_tests": summary.get('total', 0),
        "passed": summary.get('passed', 0),
        "failed": summary.get('failed', 0),
    }
    
    with open(FMEA_METRICS_FILE, 'w') as f:
        json.dump([metrics], f, indent=2)
    
    log(f"Metrics saved to: {FMEA_METRICS_FILE}")
else:
    log("FAILED: No report file created")

log("\nSCRIPT COMPLETED")