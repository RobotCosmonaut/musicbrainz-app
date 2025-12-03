"""
Diagnostic script to check coverage XML
"""
import xml.etree.ElementTree as ET
from pathlib import Path

coverage_file = Path("metrics_data/coverage.xml")

if not coverage_file.exists():
    print("❌ coverage.xml not found!")
    print("\nChecking metrics_data directory:")
    metrics_dir = Path("metrics_data")
    if metrics_dir.exists():
        for file in metrics_dir.iterdir():
            print(f"  - {file.name}")
    exit(1)

print("✓ coverage.xml exists")
print(f"  Size: {coverage_file.stat().st_size} bytes")

tree = ET.parse(coverage_file)
root = tree.getroot()

print(f"\n📊 Coverage XML Structure:")
print(f"  Root tag: {root.tag}")
print(f"  Root attributes: {root.attrib}")

# Check for packages
packages = root.findall('.//package')
print(f"\n📦 Packages found: {len(packages)}")

for pkg in packages[:3]:  # Show first 3
    print(f"\n  Package: {pkg.get('name')}")
    print(f"    Line rate: {pkg.get('line-rate')}")
    print(f"    Branch rate: {pkg.get('branch-rate')}")
    
    classes = pkg.findall('.//class')
    print(f"    Classes: {len(classes)}")
    
    if classes:
        first_class = classes[0]
        print(f"      First class: {first_class.get('name')}")
        print(f"        Filename: {first_class.get('filename')}")
        print(f"        Line rate: {first_class.get('line-rate')}")

# Check overall statistics
print(f"\n📈 Overall Statistics:")
if 'line-rate' in root.attrib:
    line_rate = float(root.get('line-rate', 0))
    print(f"  Overall line rate: {line_rate * 100:.2f}%")
if 'branch-rate' in root.attrib:
    branch_rate = float(root.get('branch-rate', 0))
    print(f"  Overall branch rate: {branch_rate * 100:.2f}%")

# Count total lines
all_lines = root.findall('.//line')
print(f"  Total line elements: {len(all_lines)}")

# Sample some lines
if all_lines:
    print(f"\n  Sample lines:")
    for line in all_lines[:5]:
        print(f"    Line {line.get('number')}: hits={line.get('hits')}")