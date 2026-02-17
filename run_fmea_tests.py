#!/usr/bin/env python3
"""
FMEA Test Runner and Comparison Framework
Runs all FMEA tests and saves results for commit comparison

Usage:
  python run_fmea_tests.py                      # Run and save current
  python run_fmea_tests.py --compare HEAD~5     # Compare to prior commit
  python run_fmea_tests.py --report             # Show history
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

FMEA_ITEMS = {
    "test_rate_limit_delay_enforced":     {"severity": 7,  "component": "MusicBrainz API"},
    "test_rate_limit_429_handling":       {"severity": 7,  "component": "MusicBrainz API"},
    "test_timeout_returns_empty":         {"severity": 8,  "component": "MusicBrainz API"},
    "test_recommendation_timeout":        {"severity": 8,  "component": "MusicBrainz API"},
    "test_wait_for_database_retry":       {"severity": 9,  "component": "PostgreSQL"},
    "test_connection_pool_exhaustion":    {"severity": 8,  "component": "PostgreSQL"},
    "test_disk_space_monitoring":         {"severity": 10, "component": "PostgreSQL"},
    "test_transaction_rollback":          {"severity": 8,  "component": "PostgreSQL"},
    "test_database_init_idempotency":     {"severity": 10, "component": "PostgreSQL"},
    "test_routing_reliability":           {"severity": 8,  "component": "API Gateway"},
    "test_concurrent_routing":            {"severity": 8,  "component": "API Gateway"},
    "test_genre_detection_known_genres":  {"severity": 7,  "component": "Recommendation"},
    "test_diversity_filter":              {"severity": 5,  "component": "Recommendation"},
    "test_empty_results_graceful":        {"severity": 7,  "component": "Recommendation"},
    "test_profile_save_and_retrieve":     {"severity": 7,  "component": "User Profile"},
    "test_listening_history_saved":       {"severity": 6,  "component": "User Profile"},
    "test_history_without_profile":       {"severity": 6,  "component": "User Profile"},
}

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

def run_fmea_tests():
    """Run all FMEA tests and collect results"""

    print("="*70)
    print("Running FMEA Tests")
    print("="*70)

    METRICS_DIR.mkdir(exist_ok=True)

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

    print(result.stdout)

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
            "duration": test.get("call", {}).get("duration", 0)
        }

    # Calculate FMEA-weighted score
    total_weighted_score = 0
    max_weighted_score = 0
    component_scores = {}

    for test_name, fmea_info in FMEA_ITEMS.items():
        severity = fmea_info["severity"]
        component = fmea_info["component"]
        max_weighted_score += severity

        if component not in component_scores:
            component_scores[component] = {
                "passed": 0, "failed": 0,
                "weighted_score": 0, "max_score": 0
            }

        component_scores[component]["max_score"] += severity

        if test_name in test_results:
            if test_results[test_name]["outcome"] == "passed":
                total_weighted_score += severity
                component_scores[component]["passed"] += 1
                component_scores[component]["weighted_score"] += severity
            else:
                component_scores[component]["failed"] += 1

    # Summary
    summary = report.get("summary", {})
    total_tests = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)

    reliability_score = (passed / total_tests * 100) if total_tests > 0 else 0
    weighted_score = (
        (total_weighted_score / max_weighted_score * 100)
        if max_weighted_score > 0 else 0
    )

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "commit_hash": get_commit_hash(),
        "commit_message": get_commit_message(),
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,
        "reliability_score": reliability_score,
        "fmea_weighted_score": weighted_score,
        "component_scores": component_scores,
        "test_results": test_results
    }

    # Save to history
    history = []
    if FMEA_METRICS_FILE.exists():
        with open(FMEA_METRICS_FILE) as f:
            history = json.load(f)

    history.append(metrics)

    with open(FMEA_METRICS_FILE, 'w') as f:
        json.dump(history, f, indent=2)

    print_summary(metrics)
    return metrics

def print_summary(metrics):
    """Print formatted test summary"""
    print("\n" + "="*70)
    print("FMEA TEST SUMMARY")
    print("="*70)
    print(f"Commit:            {metrics['commit_hash'][:8]}")
    print(f"Message:           {metrics['commit_message'][:50]}")
    print(f"Timestamp:         {metrics['timestamp'][:19]}")
    print(f"Tests:             {metrics['passed']}/{metrics['total_tests']} passed")
    print(f"Reliability Score: {metrics['reliability_score']:.1f}%")
    print(f"FMEA Weighted:     {metrics['fmea_weighted_score']:.1f}%")

    print(f"\n🔧 Component Breakdown:")
    for component, scores in metrics['component_scores'].items():
        pct = (
            (scores['weighted_score'] / scores['max_score'] * 100)
            if scores['max_score'] > 0 else 0
        )
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"  {component:20s} [{bar}] {pct:5.1f}%")

def compare_to_commit(compare_commit):
    """Compare current metrics to a prior commit"""

    if not FMEA_METRICS_FILE.exists():
        print("❌ No metrics history found. Run tests first.")
        return

    with open(FMEA_METRICS_FILE) as f:
        history = json.load(f)

    # Find the comparison commit
    compare_metrics = None
    for entry in history:
        if entry["commit_hash"].startswith(compare_commit):
            compare_metrics = entry
            break

    if not compare_metrics:
        print(f"❌ No metrics found for commit: {compare_commit}")
        print("\nAvailable commits:")
        for entry in history[-10:]:
            print(
                f"  {entry['commit_hash'][:8]}  "
                f"{entry['timestamp'][:19]}  "
                f"{entry['reliability_score']:.1f}%  "
                f"{entry['commit_message'][:40]}"
            )
        return

    # Get current metrics (most recent)
    current_metrics = history[-1]

    print("\n" + "="*70)
    print("FMEA TEST COMPARISON")
    print("="*70)

    print(f"\n📅 BEFORE: Commit {compare_metrics['commit_hash'][:8]}")
    print(f"   {compare_metrics['commit_message'][:60]}")
    print(f"   Reliability Score:    {compare_metrics['reliability_score']:.1f}%")
    print(f"   FMEA Weighted Score:  {compare_metrics['fmea_weighted_score']:.1f}%")
    print(f"   Tests Passed:         {compare_metrics['passed']}/{compare_metrics['total_tests']}")

    print(f"\n📅 AFTER: Commit {current_metrics['commit_hash'][:8]}")
    print(f"   {current_metrics['commit_message'][:60]}")
    print(f"   Reliability Score:    {current_metrics['reliability_score']:.1f}%")
    print(f"   FMEA Weighted Score:  {current_metrics['fmea_weighted_score']:.1f}%")
    print(f"   Tests Passed:         {current_metrics['passed']}/{current_metrics['total_tests']}")

    # Differences
    score_diff = (
        current_metrics['reliability_score'] -
        compare_metrics['reliability_score']
    )
    weighted_diff = (
        current_metrics['fmea_weighted_score'] -
        compare_metrics['fmea_weighted_score']
    )

    print(f"\n📈 Improvements:")
    emoji = "✅" if score_diff >= 0 else "❌"
    print(f"  {emoji} Reliability Score:   {score_diff:+.1f}%")
    emoji = "✅" if weighted_diff >= 0 else "❌"
    print(f"  {emoji} FMEA Weighted Score: {weighted_diff:+.1f}%")

    # Component comparison
    print(f"\n🔧 Component Changes:")
    all_components = set(
        list(compare_metrics['component_scores'].keys()) +
        list(current_metrics['component_scores'].keys())
    )

    for component in sorted(all_components):
        old = compare_metrics['component_scores'].get(component, {})
        new = current_metrics['component_scores'].get(component, {})

        old_pct = (
            (old.get('weighted_score', 0) / old.get('max_score', 1) * 100)
            if old else 0
        )
        new_pct = (
            (new.get('weighted_score', 0) / new.get('max_score', 1) * 100)
            if new else 0
        )
        diff = new_pct - old_pct

        emoji = "✅" if diff >= 0 else "❌"
        print(
            f"  {emoji} {component:20s}: "
            f"{old_pct:5.1f}% → {new_pct:5.1f}% ({diff:+.1f}%)"
        )

    print("="*70)

def show_report():
    """Show historical FMEA test results"""
    if not FMEA_METRICS_FILE.exists():
        print("❌ No metrics history found")
        return

    with open(FMEA_METRICS_FILE) as f:
        history = json.load(f)

    print("\n" + "="*70)
    print("FMEA TEST HISTORY")
    print("="*70)
    print(f"\n{'Commit':<10} {'Date':<20} {'Reliability':>12} {'FMEA Score':>12} {'Message'}")
    print("-"*70)

    for entry in history[-15:]:
        print(
            f"{entry['commit_hash'][:8]:<10} "
            f"{entry['timestamp'][:19]:<20} "
            f"{entry['reliability_score']:>11.1f}% "
            f"{entry['fmea_weighted_score']:>11.1f}% "
            f"{entry['commit_message'][:30]}"
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FMEA Test Runner")
    parser.add_argument(
        "--compare",
        type=str,
        help="Compare to this commit hash"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show historical report"
    )

    args = parser.parse_args()

    if args.report:
        show_report()
    elif args.compare:
        run_fmea_tests()
        compare_to_commit(args.compare)
    else:
        run_fmea_tests()