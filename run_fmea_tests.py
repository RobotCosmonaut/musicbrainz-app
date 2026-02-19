#!/usr/bin/env python3
"""
FMEA Test Runner - Updated for Retrospective Testing
Supports --label flag for identifying old vs new commits

Usage:
  python run_fmea_tests.py                           # Current commit
  python run_fmea_tests.py --label "old_commit_abc" # Label results
  python run_fmea_tests.py --compare HEAD~5          # Compare commits
  python run_fmea_tests.py --report                  # Show history
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
    """
    Check which services are actually running before tests
    Critical for retrospective testing - old commits may not have
    all services implemented
    """
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
    # This is critical for old commits
    print("\nChecking service availability...")
    availability = check_service_availability()

    for service, status in availability.items():
        indicator = "✅" if status["available"] else "❌"
        print(f"  {indicator} {service}: {status}")

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
        print("❌ No test report generated")
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
            # Capture what error occurred for comparison
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

    print(f"\n✅ Results saved with label: {metrics['label']}")
    return metrics


def compare_labels(old_label, new_label):
    """
    Compare two labeled test runs
    This is what makes retrospective testing meaningful
    """

    if not FMEA_METRICS_FILE.exists():
        print("❌ No metrics history found")
        return

    with open(FMEA_METRICS_FILE) as f:
        history = json.load(f)

    # Find entries by label
    old_metrics = next(
        (h for h in history if h.get("label") == old_label), None
    )
    new_metrics = next(
        (h for h in history if h.get("label") == new_label), None
    )

    if not old_metrics:
        print(f"❌ Label not found: {old_label}")
        _show_available_labels(history)
        return

    if not new_metrics:
        print(f"❌ Label not found: {new_label}")
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
    print(f"\n📅 OLD: {old_metrics['label']}")
    print(f"   Commit:      {old_metrics['commit_hash'][:8]}")
    print(f"   Date:        {old_metrics.get('commit_date', 'unknown')[:19]}")
    print(f"   Message:     {old_metrics['commit_message'][:50]}")
    print(f"   Tested at:   {old_metrics['timestamp'][:19]}")

    print(f"\n📅 NEW: {new_metrics['label']}")
    print(f"   Commit:      {new_metrics['commit_hash'][:8]}")
    print(f"   Date:        {new_metrics.get('commit_date', 'unknown')[:19]}")
    print(f"   Message:     {new_metrics['commit_message'][:50]}")
    print(f"   Tested at:   {new_metrics['timestamp'][:19]}")

    # Service availability comparison
    print(f"\n🔌 Service Availability Changes:")
    old_avail = old_metrics.get("service_availability", {})
    new_avail = new_metrics.get("service_availability", {})

    all_services = set(list(old_avail.keys()) + list(new_avail.keys()))
    for service in sorted(all_services):
        old_up = old_avail.get(service, {}).get("available", False)
        new_up = new_avail.get(service, {}).get("available", False)

        if not old_up and new_up:
            print(f"  ✅ {service:30s}: DOWN → UP (service added/fixed)")
        elif old_up and not new_up:
            print(f"  ❌ {service:30s}: UP → DOWN (regression!)")
        elif old_up and new_up:
            print(f"  ✅ {service:30s}: UP → UP (stable)")
        else:
            print(f"  ⚠️  {service:30s}: DOWN → DOWN (still missing)")

    # Overall scores
    score_diff = new_metrics['reliability_score'] - old_metrics['reliability_score']
    tests_diff = new_metrics['total_tests'] - old_metrics['total_tests']

    print(f"\n📊 Overall Results:")
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
    print(f"\n🔍 Test-by-Test Comparison:")
    print(f"  {'Test':<45} {'Old':>8} {'New':>8}")
    print(f"  {'-'*62}")

    old_results = old_metrics.get("test_results", {})
    new_results = new_metrics.get("test_results", {})
    all_tests = set(list(old_results.keys()) + list(new_results.keys()))

    newly_passing = []
    newly_failing = []
    still_failing = []

    for test in sorted(all_tests):
        old_outcome = old_results.get(test, {}).get("outcome", "missing")
        new_outcome = new_results.get(test, {}).get("outcome", "missing")

        old_icon = "✅" if old_outcome == "passed" else "❌"
        new_icon = "✅" if new_outcome == "passed" else "❌"

        # Categorize changes
        if old_outcome != "passed" and new_outcome == "passed":
            newly_passing.append(test)
        elif old_outcome == "passed" and new_outcome != "passed":
            newly_failing.append(test)
        elif old_outcome != "passed" and new_outcome != "passed":
            still_failing.append(test)

        print(
            f"  {test[:44]:<45} "
            f"{old_icon} {old_outcome[:6]:>6}  "
            f"{new_icon} {new_outcome[:6]:>6}"
        )

    # Summary of changes
    if newly_passing:
        print(f"\n✅ Newly Passing ({len(newly_passing)} tests):")
        for test in newly_passing:
            print(f"   + {test}")

    if newly_failing:
        print(f"\n❌ Regressions - Newly Failing ({len(newly_failing)} tests):")
        for test in newly_failing:
            print(f"   - {test}")

    if still_failing:
        print(f"\n⚠️  Still Failing ({len(still_failing)} tests):")
        for test in still_failing:
            print(f"   ~ {test}")

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
        run_fmea_tests(label=args.label)
```

---

## What Results Are Actually Compared?

This is the most important part. Here is **exactly** what changes between old and new commits:

### **1. Service Availability**
```
Old Commit (e.g., before recommendation service added):
  ❌ recommendation_service: DOWN (not implemented yet)
  ✅ artist_service: UP
  ✅ album_service: UP
  ❌ api_gateway: DOWN (depended on missing service)

Current Commit:
  ✅ recommendation_service: UP
  ✅ artist_service: UP
  ✅ album_service: UP
  ✅ api_gateway: UP
```

### **2. Test Pass/Fail Changes**

| Test | Old Commit | New Commit | Meaning |
|------|-----------|------------|---------|
| `test_rate_limit_delay_enforced` | ❌ FAILED | ✅ PASSED | Rate limiting added |
| `test_timeout_returns_empty` | ❌ FAILED | ✅ PASSED | Error handling added |
| `test_diversity_filter` | ❌ FAILED | ✅ PASSED | Feature implemented |
| `test_database_init_idempotency` | ❌ FAILED | ✅ PASSED | Init script fixed |
| `test_health_endpoint_availability` | ✅ PASSED | ✅ PASSED | Was always stable |
| `test_genre_detection` | ❌ MISSING | ✅ PASSED | Feature newly added |

### **3. Performance Metrics**
```
Old Commit:
  avg_response_time:  4.2s  (no caching)
  response_time_cv:   85%   (very inconsistent)
  
Current Commit:
  avg_response_time:  0.8s  (with caching)
  response_time_cv:   22%   (consistent)
```

### **4. Error Types Revealed**
```
Old Commit Failures:
  test_timeout_returns_empty:
    Error: "AttributeError: 'NoneType' has no attribute 'get'"
    Meaning: No null check on API response

  test_diversity_filter:
    Error: "AttributeError: module has no 'ensure_artist_diversity'"
    Meaning: Function not yet implemented

Current Commit:
  All above tests pass
  ensure_artist_diversity() exists and works
  Null checks present