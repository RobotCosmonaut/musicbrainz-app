#!/usr/bin/env python3
"""
Comprehensive diagnostic script to identify Flake8 configuration issues
"""

import subprocess
import os
import sys
from pathlib import Path

print("=" * 70)
print("FLAKE8 CONFIGURATION DIAGNOSTIC")
print("=" * 70)

# Get current directory
current_dir = Path.cwd()
print(f"\n📁 Current Directory: {current_dir}")

# Test 1: Check for .flake8 file location
print("\n" + "=" * 70)
print("TEST 1: Locating .flake8 Configuration File")
print("=" * 70)

possible_configs = [
    '.flake8',
    'setup.cfg',
    'tox.ini',
    '.config/flake8'
]

config_found = None
for config in possible_configs:
    config_path = current_dir / config
    if config_path.exists():
        print(f"✓ Found: {config}")
        config_found = config_path
        
        # Read and display contents
        print(f"\n  Contents of {config}:")
        print("  " + "-" * 66)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n')[:30]:  # Show first 30 lines
                    print(f"  {line}")
                if len(content.split('\n')) > 30:
                    print(f"  ... ({len(content.split('\n')) - 30} more lines)")
        except Exception as e:
            print(f"  ✗ Error reading file: {e}")
        print("  " + "-" * 66)
    else:
        print(f"✗ Not found: {config}")

if not config_found:
    print("\n⚠️  WARNING: No configuration file found!")
    print("   Flake8 will use default settings only.")

# Test 2: Check Flake8's actual configuration
print("\n" + "=" * 70)
print("TEST 2: Flake8's Active Configuration")
print("=" * 70)

result = subprocess.run(['flake8', '--version'], capture_output=True, text=True)
print(f"Flake8 Version:\n{result.stdout}")

# Test 3: Test on a real project file with manual settings
print("\n" + "=" * 70)
print("TEST 3: Manual Test on services/recommendation_service.py")
print("=" * 70)

test_file = 'services/recommendation_service.py'
if os.path.exists(test_file):
    print(f"\n3a. Default Flake8 (should use .flake8 config):")
    result = subprocess.run(['flake8', test_file], capture_output=True, text=True)
    if result.stdout:
        violations = result.stdout.strip().split('\n')
        print(f"   Found {len(violations)} violations")
        for v in violations[:5]:
            print(f"   {v}")
        if len(violations) > 5:
            print(f"   ... and {len(violations) - 5} more")
    else:
        print("   ✗ No violations found")
    
    print(f"\n3b. Force strict settings (max-line-length=79):")
    result = subprocess.run(
        ['flake8', test_file, '--max-line-length=79'],
        capture_output=True, 
        text=True
    )
    if result.stdout:
        violations = result.stdout.strip().split('\n')
        print(f"   Found {len(violations)} violations")
        for v in violations[:5]:
            print(f"   {v}")
    else:
        print("   ✗ No violations found (unexpected!)")
    
    print(f"\n3c. Check for E501 violations specifically:")
    result = subprocess.run(
        ['flake8', test_file, '--select=E501', '--max-line-length=79'],
        capture_output=True,
        text=True
    )
    if result.stdout:
        violations = result.stdout.strip().split('\n')
        print(f"   Found {len(violations)} E501 violations")
        for v in violations[:3]:
            print(f"   {v}")
    else:
        print("   ✗ No E501 violations (all lines under 79 chars?)")
    
    print(f"\n3d. Check for missing docstrings (D codes):")
    result = subprocess.run(
        ['flake8', test_file, '--select=D'],
        capture_output=True,
        text=True
    )
    if result.stdout:
        violations = result.stdout.strip().split('\n')
        print(f"   Found {len(violations)} docstring violations")
        for v in violations[:3]:
            print(f"   {v}")
    else:
        print("   ✗ No docstring violations")
    
    print(f"\n3e. Check ALL possible codes (ignore nothing):")
    result = subprocess.run(
        ['flake8', test_file, '--max-line-length=79', '--max-complexity=8'],
        capture_output=True,
        text=True
    )
    if result.stdout:
        violations = result.stdout.strip().split('\n')
        print(f"   Found {len(violations)} total violations")
        for v in violations[:10]:
            print(f"   {v}")
        if len(violations) > 10:
            print(f"   ... and {len(violations) - 10} more")
    else:
        print("   ✗ No violations found")
        print("   ⚠️  This suggests the code is genuinely very clean!")
    
    # Check actual file content
    print(f"\n3f. File analysis:")
    with open(test_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"   Total lines: {len(lines)}")
        
        # Count long lines
        long_lines = [i+1 for i, line in enumerate(lines) if len(line.rstrip()) > 79]
        print(f"   Lines over 79 chars: {len(long_lines)}")
        if long_lines:
            print(f"   First few long lines: {long_lines[:5]}")
        
        # Check for docstrings
        has_module_docstring = lines[0].strip().startswith('"""') or lines[0].strip().startswith("'''")
        print(f"   Has module docstring: {has_module_docstring}")
        
else:
    print(f"✗ File not found: {test_file}")

# Test 4: Create test file with guaranteed violations
print("\n" + "=" * 70)
print("TEST 4: Create Test File with Known Violations")
print("=" * 70)

test_file = 'diagnostic_test.py'
with open(test_file, 'w') as f:
    f.write('''# Missing module docstring (D100)
import os
import sys  # Not alphabetical (I100)

def function_without_docstring(x=[]):  # B006 mutable default
    very_long_variable_name = "This is definitely a line that is much longer than seventy nine characters and should trigger E501"
    return x
    
class MyClass:  # D101 missing docstring
    pass
''')

print(f"Created test file: {test_file}")
result = subprocess.run(['flake8', test_file, '--max-line-length=79'], 
                       capture_output=True, text=True)
if result.stdout:
    violations = result.stdout.strip().split('\n')
    print(f"\n✓ SUCCESS! Found {len(violations)} violations in test file:")
    for v in violations:
        print(f"  {v}")
    os.remove(test_file)
else:
    print("\n✗ PROBLEM! Even test file shows no violations!")
    print("  This indicates Flake8 configuration issue or plugins not working")
    os.remove(test_file)

# Test 5: Check environment
print("\n" + "=" * 70)
print("TEST 5: Python Environment Check")
print("=" * 70)

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

result = subprocess.run(['pip', 'list'], capture_output=True, text=True)
flake8_packages = [line for line in result.stdout.split('\n') if 'flake8' in line.lower()]
print("\nInstalled Flake8 packages:")
for pkg in flake8_packages:
    print(f"  {pkg}")

# Summary
print("\n" + "=" * 70)
print("DIAGNOSTIC SUMMARY")
print("=" * 70)

if config_found:
    print(f"✓ Configuration file found: {config_found.name}")
else:
    print("✗ No configuration file found")
    print("  ACTION: Ensure .flake8 is in project root")

print("\n💡 NEXT STEPS:")
print("1. Review the .flake8 contents above")
print("2. Check if test file violations were found")
print("3. Look at manual test results for recommendation_service.py")
print("4. If test file shows violations but project files don't,")
print("   your code might genuinely be very clean!")

print("\n🔍 To manually test a file:")
print(f"   flake8 services/recommendation_service.py --max-line-length=79")

print("\n" + "=" * 70)
