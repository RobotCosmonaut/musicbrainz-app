#!/usr/bin/env python3
"""
Compare complete reliability results (FMEA + Reliability tests)
"""

import json
import sys
from pathlib import Path

METRICS_FILE = Path("metrics_data/complete_reliability_results.json")

def compare(old_label, new_label):
    if not METRICS_FILE.exists():
        print("❌ No metrics file found")
        return

    with open(METRICS_FILE) as f:
        history = json.load(f)

    old = next((h for h in history if h.get("label") == old_label), None)
    new = next((h for h in history if h.get("label") == new_label), None)

    if not old or not new:
        print(f"❌ Labels not found: {old_label}, {new_label}")
        print("\nAvailable labels:")
        for entry in history:
            print(f"  - {entry['label']}")
        return

    print("\n" + "=" * 70)
    print("COMPLETE RELIABILITY COMPARISON")
    print("(FMEA + Reliability Tests)")
    print("=" * 70)

    # Old commit
    print(f"\n[OLD] {old['label']}")
    print(f"   Commit:  {old['commit_hash'][:8]}")
    print(f"   FMEA Tests:        {old['fmea_tests']['passed']}/{old['fmea_tests']['total']} ({old['fmea_tests']['reliability_score']:.1f}%)")
    print(f"   Reliability Tests: {old['reliability_tests']['passed']}/{old['reliability_tests']['total']} ({old['reliability_tests']['reliability_score']:.1f}%)")
    print(f"   COMBINED:          {old['combined']['passed']}/{old['combined']['total']} ({old['combined']['reliability_score']:.1f}%)")

    # New commit
    print(f"\n[NEW] {new['label']}")
    print(f"   Commit:  {new['commit_hash'][:8]}")
    print(f"   FMEA Tests:        {new['fmea_tests']['passed']}/{new['fmea_tests']['total']} ({new['fmea_tests']['reliability_score']:.1f}%)")
    print(f"   Reliability Tests: {new['reliability_tests']['passed']}/{new['reliability_tests']['total']} ({new['reliability_tests']['reliability_score']:.1f}%)")
    print(f"   COMBINED:          {new['combined']['passed']}/{new['combined']['total']} ({new['combined']['reliability_score']:.1f}%)")

    # Changes
    fmea_change = new['fmea_tests']['reliability_score'] - old['fmea_tests']['reliability_score']
    reliability_change = new['reliability_tests']['reliability_score'] - old['reliability_tests']['reliability_score']
    combined_change = new['combined']['reliability_score'] - old['combined']['reliability_score']

    print("\n[IMPROVEMENTS]")
    print(f"   FMEA:        {fmea_change:+.1f}%")
    print(f"   Reliability: {reliability_change:+.1f}%")
    print(f"   COMBINED:    {combined_change:+.1f}%")

    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_complete_reliability.py <old_label> <new_label>")
        sys.exit(1)

    compare(sys.argv[1], sys.argv[2])