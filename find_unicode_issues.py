#!/usr/bin/env python3
"""
Find problematic Unicode characters in ui/app.py that break Windows encoding
"""

import sys

filepath = "ui/app.py"

print("="*70)
print("FINDING PROBLEMATIC UNICODE CHARACTERS")
print("="*70)

try:
    # Try reading with UTF-8
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n✓ File reads successfully with UTF-8 encoding")
    print(f"  Total characters: {len(content):,}")
    
    # Find non-ASCII characters
    non_ascii = []
    for i, char in enumerate(content):
        if ord(char) > 127:
            # Get line number
            line_num = content[:i].count('\n') + 1
            col = i - content[:i].rfind('\n')
            non_ascii.append({
                'char': char,
                'ord': ord(char),
                'hex': hex(ord(char)),
                'position': i,
                'line': line_num,
                'col': col
            })
    
    if non_ascii:
        print(f"\n⚠️  Found {len(non_ascii)} non-ASCII characters:")
        print(f"\nFirst 20 occurrences:")
        print(f"{'Line':<6} {'Col':<5} {'Char':<6} {'Ord':<6} {'Hex':<8} {'Context (20 chars around)'}")
        print("-" * 70)
        
        for item in non_ascii[:20]:
            pos = item['position']
            # Get context around the character
            start = max(0, pos - 10)
            end = min(len(content), pos + 10)
            context = content[start:end]
            # Replace newlines and tabs for display
            context = context.replace('\n', '\\n').replace('\t', '\\t')
            
            char_display = item['char'] if item['char'].isprintable() else '?'
            
            print(f"{item['line']:<6} {item['col']:<5} {char_display:<6} {item['ord']:<6} {item['hex']:<8} {context}")
        
        if len(non_ascii) > 20:
            print(f"\n... and {len(non_ascii) - 20} more")
        
        # Most common problematic characters
        print(f"\n📊 Most common non-ASCII characters:")
        from collections import Counter
        char_counts = Counter([item['char'] for item in non_ascii])
        for char, count in char_counts.most_common(10):
            char_display = char if char.isprintable() else '?'
            print(f"  '{char_display}' (U+{ord(char):04X}): {count} occurrences")
        
        # Check specifically around position 18057
        print(f"\n🔍 Context around position 18057 (where error occurred):")
        if len(content) > 18057:
            start = max(0, 18057 - 50)
            end = min(len(content), 18057 + 50)
            context = content[start:end]
            print(f"  Characters {start}-{end}:")
            print(f"  {repr(context)}")
            
            # Find line number
            line_num = content[:18057].count('\n') + 1
            print(f"  This is around line {line_num}")
    else:
        print(f"\n✓ No non-ASCII characters found (all characters are ASCII)")

except UnicodeDecodeError as e:
    print(f"\n❌ UTF-8 decoding also failed: {e}")
    print(f"\n  Trying to read as binary to find the issue...")
    
    with open(filepath, 'rb') as f:
        binary_content = f.read()
    
    print(f"\n  File size: {len(binary_content):,} bytes")
    print(f"  Problematic byte at position ~18057:")
    
    start = max(0, 18057 - 20)
    end = min(len(binary_content), 18057 + 20)
    print(f"  Bytes {start}-{end}: {binary_content[start:end]}")
    print(f"  As hex: {binary_content[start:end].hex()}")

print("\n" + "="*70)
print("RECOMMENDATIONS")
print("="*70)

print("""
If non-ASCII characters were found:

1. OPTION A: Remove/replace them
   - These are often smart quotes, em-dashes, or emoji
   - Replace ' ' with regular quotes
   - Replace – with regular dash -
   - Replace emoji with text

2. OPTION B: Fix the encoding in collect_metrics.py
   - Add encoding='utf-8' to subprocess calls
   - Add errors='replace' or errors='ignore' to handle issues

3. OPTION C: Fix the encoding in the file itself
   - Re-save ui/app.py with UTF-8 encoding (no BOM)
""")
