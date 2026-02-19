#!/usr/bin/env python3
"""
FMEA Test Runner - Fixed Version (No Emoji Syntax Errors)
Supports --label flag for identifying old vs new commits
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

def get_commit_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT
        ).decode().strip()
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

def run_fmea_tests(label=None):
    """Run FMEA tests and save with optional label"""

    print("=" * 70)
    print("Running FMEA Tests")
    print("=" * 70)

    METRICS_DIR.mkdir(exist_ok=True)

    # Check which services are available
    print("\nChecking service availability...")
    availability = check_service_availability()

    for service, status in availability.items():
        if status["available"]:
            print(f"  [OK] {service}: {status}")
        else:
            print(f"  [FAIL] {service}: {status}")

    # Run pytest
    result = subprocess.run(
        [
            "pytest",
            "tests/fmea/",
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file={METRICS_DIR}/fmea_report.json"
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )

    print(result.stdout[-3000:])  # Show last 3000 chars

    report_file = METRICS_DIR / "fmea_report.json"
    if not report_file.exists():
        print("[ERROR] No test report generated")
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
        "label": label or f"commit_{get_commit_hash()[:8]}",
        "timestamp": datetime.now().isoformat(),
        "commit_hash": get_commit_hash(),
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
    print(f"   Message:     {old_metrics['commit_message'][:50]}")
    print(f"   Tested at:   {old_metrics['timestamp'][:19]}")

    print(f"\n[NEW] {new_metrics['label']}")
    print(f"   Commit:      {new_metrics['commit_hash'][:8]}")
    print(f"   Date:        {new_metrics.get('commit_date', 'unknown')[:19]}")
    print(f"   Message:     {new_metrics['commit_message'][:50]}")
    print(f"   Tested at:   {new_metrics['timestamp'][:19]}")

    # Service availability comparison
    print(f"\n[SERVICE AVAILABILITY CHANGES]")
    old_avail = old_metrics.get("service_availability", {})
    new_avail = new_metrics.get("service_availability", {})

    all_services = set(list(old_avail.keys()) + list(new_avail.keys()))
    for service in sorted(all_services):
        old_up = old_avail.get(service, {}).get("available", False)
        new_up = new_avail.get(service, {}).get("available", False)

        if not old_up and new_up:
            print(f"  [+] {service:30s}: DOWN -> UP (service added/fixed)")
        elif old_up and not new_up:
            print(f"  [-] {service:30s}: UP -> DOWN (regression!)")
        elif old_up and new_up:
            print(f"  [=] {service:30s}: UP -> UP (stable)")
        else:
            print(f"  [!] {service:30s}: DOWN -> DOWN (still missing)")

    # Overall scores
    score_diff = new_metrics['reliability_score'] - old_metrics['reliability_score']
    tests_diff = new_metrics['total_tests'] - old_metrics['total_tests']

    print(f"\n[OVERALL RESULTS]")
    print(f"  {'Metric':<30} {'Old':>10} {'New':>10} {'Change':>10}")
    print(f"  {'-'*62}")
    print(
        f"  {'Reliability Score':<30} "
        f"{old_metrics['reliability_score']:>9.1f}% "
        f"{new_metrics['reliability_score']:>9.1f}% "
        f"{score_diff:>+9.1f}%"
    )
    print(
        f"  {'Tests Passed':<30} "
        f"{old_metrics['passed']:>10} "
        f"{new_metrics['passed']:>10} "
        f"{new_metrics['passed'] - old_metrics['passed']:>+10}"
    )
    print(
        f"  {'Total Tests':<30} "
        f"{old_metrics['total_tests']:>10} "
        f"{new_metrics['total_tests']:>10} "
        f"{tests_diff:>+10}"
    )

    # Test-by-test comparison
    print(f"\n[TEST-BY-TEST COMPARISON]")
    print(f"  {'Test':<45} {'Old':>8} {'New':>8}")
    print(f"  {'-'*62}")

    old_results = old_metrics.get("test_results", {})
    new_results = new_metrics.get("test_results", {})
    all_tests = set(list(old_results.keys()) + list(new_results.keys()))

    newly_passing = []
    newly_failing = []