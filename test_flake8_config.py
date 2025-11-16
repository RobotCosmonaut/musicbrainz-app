#!/usr/bin/env python3
"""
Test script to verify Flake8 and plugins are working correctly
"""

import subprocess
import sys

print("=" * 60)
print("FLAKE8 CONFIGURATION TEST")
print("=" * 60)

# Test 1: Check Flake8 installation
print("\n1. Checking Flake8 installation...")
try:
    result = subprocess.run(['flake8', '--version'], capture_output=True, text=True)
    print(f"✓ Flake8 version: {result.stdout.strip()}")
except FileNotFoundError:
    print("✗ Flake8 not found! Run: pip install flake8")
    sys.exit(1)

# Test 2: Check installed plugins
print("\n2. Checking installed plugins...")
# Note: Module import names differ from package names!
plugins_to_check = {
    'mccabe': 'McCabe complexity',
    'bugbear': 'Bugbear',  # Package: flake8-bugbear, Import: bugbear
    'flake8_comprehensions': 'Comprehensions',
    'flake8_simplify': 'Simplify',
    'pydocstyle': 'Docstrings',  # Package: flake8-docstrings, Import: pydocstyle
    'flake8_import_order': 'Import Order'
}

for module, name in plugins_to_check.items():
    try:
        __import__(module)
        print(f"✓ {name} plugin installed")
    except ImportError:
        # Provide correct package name for installation
        package_map = {
            'bugbear': 'flake8-bugbear',
            'pydocstyle': 'flake8-docstrings'
        }
        package_name = package_map.get(module, module.replace('_', '-'))
        print(f"✗ {name} plugin NOT installed - run: pip install {package_name}")

# Test 3: Create a test file with known violations
print("\n3. Creating test file with known violations...")
test_file = "test_violations.py"
with open(test_file, 'w') as f:
    f.write('''
# This file intentionally has many violations for testing

import sys
import os

def function_with_long_line():
    x = "This is a very long line that exceeds 79 characters and should trigger an E501 violation in strict mode"
    return x

def function_without_docstring():
    pass

def mutable_default_argument(x, y=[]):
    y.append(x)
    return y

class ClassWithoutDocstring:
    pass

def complex_function(a, b, c, d):
    if a:
        if b:
            if c:
                if d:
                    print("nested")
                    return True
    return False

list(x for x in range(10))
''')

# Test 4: Run Flake8 on test file
print(f"\n4. Running Flake8 on test file...")
result = subprocess.run(['flake8', test_file], capture_output=True, text=True)

if result.stdout:
    violations = result.stdout.strip().split('\n')
    print(f"\n✓ Found {len(violations)} violations in test file:")
    print("-" * 60)
    for violation in violations[:10]:  # Show first 10
        print(violation)
    if len(violations) > 10:
        print(f"... and {len(violations) - 10} more")
    print("-" * 60)
else:
    print("✗ NO violations found! Something is wrong with configuration.")

# Test 5: Check specific error codes
print("\n5. Testing specific error codes...")
error_codes = {
    'E501': 'Line too long',
    'E302': 'Expected 2 blank lines',
    'D100': 'Missing docstring (docstrings plugin)',
    'B006': 'Mutable default argument (bugbear plugin)',
    'C400': 'Unnecessary comprehension (comprehensions plugin)',
    'C901': 'Function too complex (mccabe)'
}

violations_text = result.stdout
found_codes = []
missing_codes = []

for code, description in error_codes.items():
    if code in violations_text:
        found_codes.append(f"✓ {code}: {description}")
    else:
        missing_codes.append(f"✗ {code}: {description}")

for code in found_codes:
    print(code)
for code in missing_codes:
    print(code)

# Cleanup
import os
os.remove(test_file)

# Test 6: Test on actual project file
print("\n6. Testing on actual project file (services/recommendation_service.py)...")
if os.path.exists('services/recommendation_service.py'):
    result = subprocess.run(
        ['flake8', 'services/recommendation_service.py'], 
        capture_output=True, 
        text=True
    )
    if result.stdout:
        violations = len(result.stdout.strip().split('\n'))
        print(f"✓ Found {violations} violations in recommendation_service.py")
        print("\nFirst few violations:")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"  {line}")
    else:
        print("⚠ No violations found in recommendation_service.py")
        print("   (This file might genuinely be very clean)")
else:
    print("✗ services/recommendation_service.py not found")

print("\n" + "=" * 60)
print("CONFIGURATION TEST COMPLETE")
print("=" * 60)

# Summary
print("\n📊 SUMMARY:")
if found_codes:
    print(f"✓ Configuration is working! Found {len(found_codes)} different violation types.")
    print("✓ Plugins are active and detecting issues.")
else:
    print("✗ Configuration may have issues. Very few violation types detected.")
    print("⚠ Check if plugins are properly installed.")

print("\n💡 Next step: Run 'python collect_metrics.py' to collect real data")
