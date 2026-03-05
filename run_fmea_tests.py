#!/usr/bin/env python3
"""
FMEA Test Runner - Working Version
Runs FMEA tests and saves metrics with labels for retrospective comparison
"""

import subprocess
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
METRICS_DIR = PROJECT_ROOT / "metrics_data"
FMEA_METRICS_FILE = METRICS_DIR / "fmea_test_results.json"

def get_commit_hash(override_hash=None):
    """Get commit hash - use override if provided, otherwise detect from git"""
    if override_hash:
        print(f"Using provided commit hash: {override_hash}")
        return override_hash
    
    try:
        hash_value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT
        ).decode().strip()
        print(f"Detected commit hash: {hash_value}")
        return hash_value
    except:
        return "unknown"

def get_commit_message():
    try:
        return subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"],
            cwd=PROJECT_ROOT
        ).decode().strip()
    except:
        return "unknown"

def get_commit_date():
    try:
        return subprocess.check_output(
            ["git", "log", "-1", "--pretty=%ci"],
            cwd=PROJECT_ROOT
        ).decode().strip()
    except:
        return "unknown"

def check_service_availability():
    """Check which services are running"""
    import requests

    services = {
        "artist_service": "http://localhost:8001/health",
        "album_service": "http://localhost:8002/health",
        "recommendation_service": "http://localhost:8003/health",
        "api_gateway": "http://localhost:8000/health",
    }

    availability = {}
    for service, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            availability[service] = {
                "available": response.status_code == 200,
                "status_code": response.status_code
            }
        except Exception as e:
            availability[service] = {
                "available": False,
                "error": str(e)
            }

    return availability

def run_fmea_tests(label=None, commit_hash=None):
    """Run FMEA tests and save with optional label"""

    commit_hash_value = get_commit_hash(commit_hash)

    print("=" * 70)
    print("Running FMEA Tests")
    print("=" * 70)

    METRICS_DIR.mkdir(exist_ok=True)

    # Check which services are available
    print("\nChecking service availability...")
    availability = check_service_availability()

    for service, status in availability.items():
        if status["available"]:
            print(f"  [OK] {service}")
        else:
            print(f"  [FAIL] {service}")

    # Run pytest (skip database tests to avoid timeouts)
    print("\nRunning pytest...")
    result = subprocess.run(
        [
            "pytest",
            "tests/fmea/",
            "-v",
            "-k", "not database",  # Skip database tests
            "--tb=short",
            "--json-report",
            f"--json-report-file={METRICS_DIR}/fmea_report.json"
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )

    print(f"Pytest completed with return code: {result.returncode}")

    report_file = METRICS_DIR / "fmea_report.json"
    if not report_file.exists():
        print("[ERROR] No test report generated")
        if result.stderr:
            print("Stderr:", result.stderr[:500])
        return None

    with open(report_file) as f:
        report = json.load(f)

    # Process results
    test_results = {}
    for test in report.get("tests", []):
        test_name = test["nodeid"].split("::")[-1]
        test_results[test_name] = {
            "outcome": test["outcome"],
            "duration": test.get("call", {}).get("duration", 0),
            "error": test.get("call", {}).get("longrepr", "") 
                     if test["outcome"] == "failed" else None
        }

    summary = report.get("summary", {})
    total_tests = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("error", 0)

    reliability_score = (passed / total_tests * 100) if total_tests > 0 else 0

    metrics = {
        "label": label or f"commit_{commit_hash_value[:8]}",  # Use stored value
        "timestamp": datetime.now().isoformat(),
        "commit_hash": commit_hash_value,  # Use stored value
        "commit_message": get_commit_message(),
        "commit_date": get_commit_date(),
        "service_availability": availability,
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "reliability_score": reliability_score,
        "test_results": test_results
    }
    

    # Save to history
    history = []
    if FMEA_METRICS_FILE.exists():
        with open(FMEA_METRICS_FILE) as f:
            history = json.load(f)

    # Replace existing entry with same label if exists
    history = [h for h in history if h.get("label") != metrics["label"]]
    history.append(metrics)

    with open(FMEA_METRICS_FILE, 'w') as f:
        json.dump(history, f, indent=2)

    print(f"\n[SUCCESS] Results saved with label: {metrics['label']}")
    print(f"Reliability Score: {reliability_score:.1f}%")
    print(f"Tests Passed: {passed}/{total_tests}")
    print(f"File: {FMEA_METRICS_FILE}")
    
    return metrics


def compare_labels(old_label, new_label):
    """Compare two labeled test runs"""

    if not FMEA_METRICS_FILE.exists():
        print("[ERROR] No metrics history found")
        return

    with open(FMEA_METRICS_FILE) as f:
        history = json.load(f)

    old_metrics = next(
        (h for h in history if h.get("label") == old_label), None
    )
    new_metrics = next(
        (h for h in history if h.get("label") == new_label), None
    )

    if not old_metrics:
        print(f"[ERROR] Label not found: {old_label}")
        _show_available_labels(history)
        return

    if not new_metrics:
        print(f"[ERROR] Label not found: {new_label}")
        _show_available_labels(history)
        return

    _print_comparison(old_metrics, new_metrics)


def _show_available_labels(history):
    print("\nAvailable labels:")
    for entry in history:
        print(
            f"  {entry.get('label', 'unlabeled'):35s} "
            f"{entry['commit_hash'][:8]}  "
            f"{entry['timestamp'][:19]}  "
            f"{entry['reliability_score']:.1f}%"
        )


def _print_comparison(old_metrics, new_metrics):
    """Print detailed comparison between two test runs"""

    print("\n" + "=" * 70)
    print("FMEA RETROSPECTIVE COMPARISON")
    print("=" * 70)

    # Header info
    print(f"\n[OLD] {old_metrics['label']}")
    print(f"   Commit:      {old_metrics['commit_hash'][:8]}")
    print(f"   Date:        {old_metrics.get('commit_date', 'unknown')[:19]}")
    print(f"   Reliability: {old_metrics['reliability_score']:.1f}%")
    print(f"   Passed:      {old_metrics['passed']}/{old_metrics['total_tests']}")

    print(f"\n[NEW] {new_metrics['label']}")
    print(f"   Commit:      {new_metrics['commit_hash'][:8]}")
    print(f"   Date:        {new_metrics.get('commit_date', 'unknown')[:19]}")
    print(f"   Reliability: {new_metrics['reliability_score']:.1f}%")
    print(f"   Passed:      {new_metrics['passed']}/{new_metrics['total_tests']}")

    # Overall change
    score_diff = new_metrics['reliability_score'] - old_metrics['reliability_score']
    print(f"\n[CHANGE] Reliability: {score_diff:+.1f}%")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FMEA Test Runner with Retrospective Support"
    )
    parser.add_argument(
        "--label",
        type=str,
        help="Label for this test run (e.g. 'old_v1' or 'current')"
    )
    parser.add_argument(
        "--commit-hash",
        type=str,
        default=None,
        help="Commit hash to record (overrides git detection)"
    )  # ← ADD THIS
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("OLD_LABEL", "NEW_LABEL"),
        help="Compare two labeled runs"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show all historical results"
    )

    args = parser.parse_args()

    if args.compare:
        compare_labels(args.compare[0], args.compare[1])
    elif args.report:
        if FMEA_METRICS_FILE.exists():
            with open(FMEA_METRICS_FILE) as f:
                history = json.load(f)
            _show_available_labels(history)
    else:
        run_fmea_tests(label=args.label, commit_hash=args.commit_hash)