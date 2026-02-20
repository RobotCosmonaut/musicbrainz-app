#!/usr/bin/env python3
"""
Complete Reliability Test Runner
Runs both FMEA tests AND general reliability tests
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
METRICS_DIR = PROJECT_ROOT / "metrics_data"
COMPLETE_METRICS_FILE = METRICS_DIR / "complete_reliability_results.json"

def run_all_tests(label=None):
    """Run both FMEA and reliability tests"""
    
    print("=" * 70)
    print("COMPLETE RELIABILITY TEST SUITE")
    print("=" * 70)
    
    METRICS_DIR.mkdir(exist_ok=True)
    
    # Run FMEA tests
    print("\n[1/2] Running FMEA Tests...")
    fmea_result = subprocess.run(
        [
            "pytest",
            "tests/fmea/",
            "-v",
            "-k", "not database",
            "--json-report",
            f"--json-report-file={METRICS_DIR}/fmea_report.json"
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    
    # Run general reliability tests
    print("\n[2/2] Running General Reliability Tests...")
    reliability_result = subprocess.run(
        [
            "pytest",
            "tests/",
            "-v",
            "-m", "reliability",
            "-k", "not fmea and not database",
            "--json-report",
            f"--json-report-file={METRICS_DIR}/reliability_report.json"
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    
    # Parse both reports
    fmea_report_file = METRICS_DIR / "fmea_report.json"
    reliability_report_file = METRICS_DIR / "reliability_report.json"
    
    fmea_data = None
    reliability_data = None
    
    if fmea_report_file.exists():
        with open(fmea_report_file) as f:
            fmea_report = json.load(f)
        fmea_summary = fmea_report.get("summary", {})
        fmea_data = {
            "total": fmea_summary.get("total", 0),
            "passed": fmea_summary.get("passed", 0),
            "failed": fmea_summary.get("failed", 0),
            "reliability_score": (fmea_summary.get("passed", 0) / fmea_summary.get("total", 1) * 100)
        }
        print(f"   FMEA: {fmea_data['passed']}/{fmea_data['total']} passed ({fmea_data['reliability_score']:.1f}%)")
    
    if reliability_report_file.exists():
        with open(reliability_report_file) as f:
            reliability_report = json.load(f)
        reliability_summary = reliability_report.get("summary", {})
        reliability_data = {
            "total": reliability_summary.get("total", 0),
            "passed": reliability_summary.get("passed", 0),
            "failed": reliability_summary.get("failed", 0),
            "reliability_score": (reliability_summary.get("passed", 0) / reliability_summary.get("total", 1) * 100)
        }
        print(f"   Reliability: {reliability_data['passed']}/{reliability_data['total']} passed ({reliability_data['reliability_score']:.1f}%)")
    
    # Combined metrics
    total_tests = (fmea_data['total'] if fmea_data else 0) + (reliability_data['total'] if reliability_data else 0)
    total_passed = (fmea_data['passed'] if fmea_data else 0) + (reliability_data['passed'] if reliability_data else 0)
    combined_score = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n   COMBINED: {total_passed}/{total_tests} passed ({combined_score:.1f}%)")
    
    # Get git info
    try:
        commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT).decode().strip()
        commit_msg = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], cwd=PROJECT_ROOT).decode().strip()
    except:
        commit_hash = "unknown"
        commit_msg = "unknown"
    
    # Save combined results
    metrics = {
        "label": label or f"commit_{commit_hash[:8]}",
        "timestamp": datetime.now().isoformat(),
        "commit_hash": commit_hash,
        "commit_message": commit_msg,
        "fmea_tests": fmea_data,
        "reliability_tests": reliability_data,
        "combined": {
            "total": total_tests,
            "passed": total_passed,
            "failed": (fmea_data['failed'] if fmea_data else 0) + (reliability_data['failed'] if reliability_data else 0),
            "reliability_score": combined_score
        }
    }
    
    # Save to history
    history = []
    if COMPLETE_METRICS_FILE.exists():
        with open(COMPLETE_METRICS_FILE) as f:
            history = json.load(f)
    
    history = [h for h in history if h.get("label") != metrics["label"]]
    history.append(metrics)
    
    with open(COMPLETE_METRICS_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"\n[SUCCESS] Complete results saved: {COMPLETE_METRICS_FILE}")
    return metrics

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=str, help="Label for this test run")
    args = parser.parse_args()
    
    run_all_tests(label=args.label)