#!/usr/bin/env python3
"""
Diagnostic script to test why ui/app.py shows 0 violations
"""

import subprocess
import re
from pathlib import Path

print("="*70)
print("DIAGNOSTIC TEST: ui/app.py Flake8 Analysis")
print("="*70)

filepath = "ui/app.py"

if not Path(filepath).exists():
    print(f"❌ File not found: {filepath}")
    exit(1)

print(f"\n1. Checking if file exists and is readable...")
print(f"   ✓ File found: {filepath}")
print(f"   ✓ File size: {Path(filepath).stat().st_size:,} bytes")

# Count actual lines
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    total_lines = len(lines)
    code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

print(f"   ✓ Total lines: {total_lines:,}")
print(f"   ✓ Code lines: {code_lines:,}")

# Check for flake8: noqa comments
noqa_count = sum(1 for line in lines if '# noqa' in line.lower() or '# flake8: noqa' in line.lower())
print(f"   ✓ Lines with noqa: {noqa_count}")

print(f"\n2. Running Flake8 with your configuration...")
result = subprocess.run(
    ['flake8', filepath, '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s'],
    capture_output=True,
    text=True
)

print(f"   Return code: {result.returncode}")
print(f"   STDOUT length: {len(result.stdout)} characters")
print(f"   STDERR length: {len(result.stderr)} characters")

if result.stdout:
    violations = result.stdout.strip().split('\n')
    violations = [v for v in violations if v.strip()]  # Remove empty lines
    
    print(f"\n3. Found {len(violations)} violations")
    
    # Parse error codes
    error_codes = {}
    for violation in violations:
        match = re.search(r'([EWFCDSBI]\d{3})', violation)
        if match:
            code = match.group(1)
            error_codes[code] = error_codes.get(code, 0) + 1
    
    print(f"\n4. Error code breakdown:")
    for code, count in sorted(error_codes.items()):
        print(f"   {code}: {count}")
    
    print(f"\n5. First 10 violations:")
    for i, violation in enumerate(violations[:10], 1):
        print(f"   {i}. {violation}")
    
    if len(violations) > 10:
        print(f"   ... and {len(violations) - 10} more")
else:
    print(f"\n3. ⚠️  NO VIOLATIONS FOUND IN STDOUT")
    print(f"\n   This could mean:")
    print(f"   • The file is genuinely clean (very unlikely for 1,877 lines)")
    print(f"   • Flake8 is configured to ignore this file")
    print(f"   • There are extensive # noqa comments")
    print(f"   • The .flake8 config has issues")

if result.stderr:
    print(f"\n6. STDERR output:")
    print(result.stderr[:500])

print(f"\n7. Testing with explicit strict settings...")
result_strict = subprocess.run(
    ['flake8', filepath, '--max-line-length=79', '--max-complexity=8', '--select=E,W,F,C'],
    capture_output=True,
    text=True
)

if result_strict.stdout:
    strict_violations = result_strict.stdout.strip().split('\n')
    strict_violations = [v for v in strict_violations if v.strip()]
    print(f"   Strict mode found: {len(strict_violations)} violations")
    
    if len(strict_violations) > 0:
        print(f"   First 5 violations in strict mode:")
        for v in strict_violations[:5]:
            print(f"   • {v}")
else:
    print(f"   Even strict mode found: 0 violations")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)

if result.stdout or result_strict.stdout:
    print("\n✓ Flake8 IS finding violations")
    print("  → Your collect_metrics.py should be capturing these")
    print("  → Check the regex pattern and parsing logic")
else:
    print("\n⚠️  Flake8 finds NO violations even in strict mode")
    print("  → This is VERY unusual for 1,877 lines")
    print("  → Check for:")
    print("     1. Extensive # noqa comments in the file")
    print("     2. A .flake8 config that excludes ui/")
    print("     3. A # flake8: noqa comment at the top of the file")
