"""
Collect reliability metrics for comparison across commits
Outputs: JSON file with reliability scores
"""

import pytest
import json
import subprocess
from datetime import datetime
from pathlib import Path

METRICS_FILE = Path("metrics_data/reliability_metrics.json")

def collect_metrics():
    """Run all reliability tests and collect metrics"""
    
    # Run pytest with JSON output
    result = subprocess.run(
        [
            "pytest",
            "tests/",
            "-m", "reliability",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=metrics_data/reliability_report.json"
        ],
        capture_output=True,
        text=True
    )
    
    # Parse pytest output for metrics
    try:
        with open("metrics_data/reliability_report.json") as f:
            report = json.load(f)
        
        total_tests = report["summary"]["total"]
        passed = report["summary"].get("passed", 0)
        failed = report["summary"].get("failed", 0)
        
        reliability_score = (passed / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate average test duration
        durations = [test["call"]["duration"] for test in report["tests"]]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "commit_hash": subprocess.check_output(
                ["git", "rev-parse", "HEAD"]
            ).decode().strip(),
            "reliability_score": reliability_score,
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "avg_test_duration": avg_duration,
            "test_details": {
                "artist_service": extract_service_metrics(report, "artist"),
                "album_service": extract_service_metrics(report, "album"),
                "recommendation_service": extract_service_metrics(report, "recommendation"),
                "gateway": extract_service_metrics(report, "gateway"),
                "database": extract_service_metrics(report, "database"),
            }
        }
        
        # Append to historical metrics
        history = []
        if METRICS_FILE.exists():
            with open(METRICS_FILE) as f:
                history = json.load(f)
        
        history.append(metrics)
        
        METRICS_FILE.parent.mkdir(exist_ok=True)
        with open(METRICS_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"\n📊 Reliability Metrics Collected:")
        print(f"   Score: {reliability_score:.1f}%")
        print(f"   Tests: {passed}/{total_tests} passed")
        print(f"   Avg Duration: {avg_duration:.3f}s")
        print(f"   Saved to: {METRICS_FILE}")
        
        return metrics
        
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        return None

def extract_service_metrics(report, service_name):
    """Extract metrics for a specific service"""
    service_tests = [
        test for test in report["tests"]
        if service_name in test["nodeid"].lower()
    ]
    
    if not service_tests:
        return None
    
    passed = sum(1 for t in service_tests if t["outcome"] == "passed")
    total = len(service_tests)
    
    return {
        "passed": passed,
        "total": total,
        "reliability": (passed / total * 100) if total > 0 else 0
    }

if __name__ == "__main__":
    collect_metrics()