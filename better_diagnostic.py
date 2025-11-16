#!/usr/bin/env python3
"""
Improved diagnostic - checks working directory and config conflicts
"""

import subprocess
import os
import sys
from pathlib import Path

print("=" * 70)
print("IMPROVED FLAKE8 DIAGNOSTIC")
print("=" * 70)

# Show exactly where we are
current_dir = Path.cwd()
script_dir = Path(__file__).parent

print(f"\n📁 Script location: {script_dir}")
print(f"📁 Current working directory: {current_dir}")
print(f"📁 Are they the same? {script_dir == current_dir}")

# Check for .flake8 in multiple locations
print("\n" + "=" * 70)
print("CHECKING FOR .FLAKE8 FILES")
print("=" * 70)

locations_to_check = [
    ("Current directory", current_dir / ".flake8"),
    ("Script directory", script_dir / ".flake8"),
    ("User home", Path.home() / ".flake8"),
    ("User config", Path.home() / ".config" / "flake8"),
]

config_files_found = []

for location_name, location_path in locations_to_check:
    if location_path.exists():
        print(f"\n✓ FOUND: {location_name}")
        print(f"  Path: {location_path}")
        config_files_found.append((location_name, location_path))
        
        # Show first 20 lines
        try:
            with open(location_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"  Lines: {len(lines)}")
                print("  First few lines:")
                for line in lines[:10]:
                    print(f"    {line.rstrip()}")
        except Exception as e:
            print(f"  ✗ Error reading: {e}")
    else:
        print(f"✗ Not found: {location_name} ({location_path})")

# Check what Flake8 is actually using
print("\n" + "=" * 70)
print("WHAT FLAKE8 IS ACTUALLY USING")
print("=" * 70)

# Create a test file in current directory
test_file = "temp_test.py"
with open(test_file, 'w') as f:
    f.write('x = "This line is deliberately longer than seventy nine characters to trigger E501 violation"\n')

print(f"\nCreated test file: {current_dir / test_file}")

# Test 1: Run Flake8 with verbose to see what config it's using
print("\nTest 1: Running Flake8 with --verbose")
result = subprocess.run(
    ['flake8', '--verbose', test_file],
    capture_output=True,
    text=True,
    cwd=str(current_dir)  # Ensure we run in current directory
)

print("STDOUT:")
print(result.stdout[:500] if result.stdout else "  (empty)")
print("\nSTDERR:")
print(result.stderr[:500] if result.stderr else "  (empty)")

# Test 2: Run without any config
print("\n\nTest 2: Running Flake8 ignoring all configs")
result = subprocess.run(
    ['flake8', '--isolated', '--max-line-length=79', test_file],
    capture_output=True,
    text=True,
    cwd=str(current_dir)
)

if result.stdout:
    print(f"✓ With --isolated flag, found violations:")
    print(result.stdout)
else:
    print("✗ Even with --isolated, no violations!")

# Test 3: Check if file actually has long lines
print("\n\nTest 3: Analyzing test file")
with open(test_file, 'r') as f:
    line = f.readline()
    print(f"Line length: {len(line.rstrip())} characters")
    print(f"Line content: {line.rstrip()}")
    print(f"Should trigger E501? {len(line.rstrip()) > 79}")

# Cleanup
os.remove(test_file)

# Test 4: Check actual project file
print("\n" + "=" * 70)
print("TESTING ACTUAL PROJECT FILE")
print("=" * 70)

project_file = "services/recommendation_service.py"
if os.path.exists(project_file):
    print(f"\nAnalyzing: {project_file}")
    
    # Count long lines manually
    with open(project_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        long_lines = [(i+1, len(line.rstrip()), line.rstrip()[:80]) 
                      for i, line in enumerate(lines) 
                      if len(line.rstrip()) > 79]
    
    print(f"Total lines: {len(lines)}")
    print(f"Lines over 79 chars: {len(long_lines)}")
    
    if long_lines:
        print("\nFirst 5 long lines:")
        for line_num, length, content in long_lines[:5]:
            print(f"  Line {line_num} ({length} chars): {content}...")
    else:
        print("  All lines are under 79 characters!")
    
    # Now test with Flake8
    print(f"\nRunning Flake8 on {project_file}:")
    result = subprocess.run(
        ['flake8', project_file, '--max-line-length=79'],
        capture_output=True,
        text=True,
        cwd=str(current_dir)
    )
    
    if result.stdout:
        violations = result.stdout.strip().split('\n')
        print(f"  Found {len(violations)} violations")
        for v in violations[:5]:
            print(f"  {v}")
    else:
        print("  No violations found by Flake8")
else:
    print(f"✗ {project_file} not found")

# Summary
print("\n" + "=" * 70)
print("DIAGNOSTIC SUMMARY")
print("=" * 70)

print(f"\n.flake8 files found: {len(config_files_found)}")
for name, path in config_files_found:
    print(f"  - {name}: {path}")

if len(config_files_found) > 1:
    print("\n⚠️  WARNING: Multiple config files found!")
    print("   Flake8 uses the FIRST one it finds in this order:")
    print("   1. .flake8 in current directory")
    print("   2. setup.cfg in current directory") 
    print("   3. tox.ini in current directory")
    print("   4. .flake8 in home directory")
    print("   5. ~/.config/flake8")

if len(config_files_found) == 0:
    print("\n❌ PROBLEM: No .flake8 file found!")
    print("   ACTION: Create .flake8 in project root")

print("\n💡 RECOMMENDED ACTIONS:")
if len(config_files_found) > 1:
    print("1. Check if home directory .flake8 is overriding project config")
    print("2. Remove or rename home directory .flake8 if not needed")
print("3. Ensure you run collect_metrics.py from project root")
print("4. Try: cd [project-root] && python collect_metrics.py")

print("\n" + "=" * 70)
