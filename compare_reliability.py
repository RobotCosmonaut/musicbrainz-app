"""
Compare reliability metrics across git commits
Usage: python compare_reliability.py <commit1> <commit2>
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

METRICS_FILE = Path("metrics_data/reliability_metrics.json")

def get_metrics_for_commit(commit_hash):
    """Get reliability metrics for a specific commit"""
    if not METRICS_FILE.exists():
        return None
    
    with open(METRICS_FILE) as f:
        history = json.load(f)
    
    for entry in history:
        if entry["commit_hash"].startswith(commit_hash):
            return entry
    
    return None

def compare_commits(commit1, commit2):
    """Compare reliability between two commits"""
    
    metrics1 = get_metrics_for_commit(commit1)
    metrics2 = get_metrics_for_commit(commit2)
    
    if not metrics1 or not metrics2:
        print("❌ Metrics not found for one or both commits")
        print("   Run: python tests/collect_reliability_metrics.py")
        return
    
    print("\n" + "="*70)
    print("RELIABILITY COMPARISON")
    print("="*70)
    
    print(f"\nCommit 1: {commit1[:8]}")
    print(f"  Date: {metrics1['timestamp']}")
    print(f"  Reliability: {metrics1['reliability_score']:.1f}%")
    print(f"  Tests: {metrics1['passed']}/{metrics1['total']}")
    
    print(f"\nCommit 2: {commit2[:8]}")
    print(f"  Date: {metrics2['timestamp']}")
    print(f"  Reliability: {metrics2['reliability_score']:.1f}%")
    print(f"  Tests: {metrics2['passed']}/{metrics2['total']}")
    
    # Calculate improvements
    score_diff = metrics2['reliability_score'] - metrics1['reliability_score']
    duration_diff = metrics2['avg_test_duration'] - metrics1['avg_test_duration']
    
    print(f"\n📈 Changes:")
    print(f"  Reliability: {score_diff:+.1f}%")
    print(f"  Avg Duration: {duration_diff:+.3f}s")
    
    # Service-specific comparison
    print(f"\n🔧 Service-Specific Changes:")
    for service in ["artist_service", "recommendation_service", "gateway"]:
        if (service in metrics1.get("test_details", {}) and 
            service in metrics2.get("test_details", {})):
            
            old_rel = metrics1["test_details"][service]["reliability"]
            new_rel = metrics2["test_details"][service]["reliability"]
            diff = new_rel - old_rel
            
            print(f"  {service}: {old_rel:.1f}% → {new_rel:.1f}% ({diff:+.1f}%)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_reliability.py <commit1> <commit2>")
        sys.exit(1)
    
    compare_commits(sys.argv[1], sys.argv[2])