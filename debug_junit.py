"""
Diagnostic script to inspect JUnit XML structure
"""
import xml.etree.ElementTree as ET
from pathlib import Path

junit_file = Path("metrics_data/pytest_report.xml")

if not junit_file.exists():
    print("❌ pytest_report.xml not found!")
    exit(1)

tree = ET.parse(junit_file)
root = tree.getroot()

print("="*60)
print("JUNIT XML STRUCTURE ANALYSIS")
print("="*60)

# Get testsuite stats
testsuite = root.find('.//testsuite')
if testsuite:
    print(f"\n📊 Test Suite Stats:")
    print(f"  Total tests: {testsuite.get('tests')}")
    print(f"  Failures: {testsuite.get('failures')}")
    print(f"  Errors: {testsuite.get('errors')}")
    print(f"  Skipped: {testsuite.get('skipped')}")
    print(f"  Time: {testsuite.get('time')}s")

# Analyze first 5 test cases in detail
print(f"\n🔍 Detailed Analysis of First 5 Tests:")
print("="*60)

for i, testcase in enumerate(root.findall('.//testcase')[:5], 1):
    print(f"\nTest #{i}:")
    print(f"  Name: {testcase.get('name')}")
    print(f"  Classname: {testcase.get('classname')}")
    print(f"  File: {testcase.get('file')}")
    print(f"  Time: {testcase.get('time')}s")
    
    # Check for properties (where markers are stored)
    properties = testcase.find('.//properties')
    if properties:
        print(f"  Properties found:")
        for prop in properties.findall('.//property'):
            print(f"    {prop.get('name')}: {prop.get('value')}")
    else:
        print(f"  Properties: None")
    
    # Check for failure/error/skip
    if testcase.find('.//failure') is not None:
        print(f"  Status: FAILED")
    elif testcase.find('.//error') is not None:
        print(f"  Status: ERROR")
    elif testcase.find('.//skipped') is not None:
        print(f"  Status: SKIPPED")
    else:
        print(f"  Status: PASSED")

# Count all tests by file
print(f"\n📁 Tests by File:")
print("="*60)
file_counts = {}
for testcase in root.findall('.//testcase'):
    file_path = testcase.get('file', 'unknown')
    file_counts[file_path] = file_counts.get(file_path, 0) + 1

for file_path, count in sorted(file_counts.items()):
    print(f"  {file_path}: {count} tests")

# Check all durations
print(f"\n⏱️  Duration Analysis:")
print("="*60)
durations = [float(tc.get('time', 0)) for tc in root.findall('.//testcase')]
if durations:
    print(f"  Total tests: {len(durations)}")
    print(f"  Zero durations: {len([d for d in durations if d == 0])}")
    print(f"  Non-zero durations: {len([d for d in durations if d > 0])}")
    print(f"  Min: {min(durations)}s")
    print(f"  Max: {max(durations)}s")
    print(f"  Avg: {sum(durations)/len(durations)}s")
    
    print(f"\n  First 10 durations:")
    for i, d in enumerate(durations[:10], 1):
        print(f"    Test {i}: {d}s ({d*1000:.3f}ms)")

print("\n" + "="*60)