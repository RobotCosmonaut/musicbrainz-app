#!/usr/bin/env python3
"""
Enhanced Flake8 Metrics Collection with Detailed Violation Reports
ACTIONABLE VERSION - Shows exactly where each issue is

Author: Ron Denny
Course: CS 8314 - Software Engineering Research
"""

import subprocess
import os
import csv
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import re
import sys

# Configuration
PROJECT_ROOT = Path(__file__).parent
METRICS_DIR = PROJECT_ROOT / "metrics_data"
METRICS_DIR.mkdir(exist_ok=True)

# Files to analyze
PYTHON_FILES = [
    "services/artist_service.py",
    "services/album_service.py",
    "services/recommendation_service.py",
    "services/musicbrainz_service.py",
    "gateway/main.py",
    "ui/app.py",
    "init_db.py",
    "shared/database.py",
    "shared/models.py"
]

class EnhancedMetricsCollector:
    """Collects detailed, actionable Flake8 metrics"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.all_violations = []  # NEW: Store all individual violations
        self.metrics = {
            'timestamp': self.timestamp,
            'date': self.date,
            'total_violations': 0,
            'total_lines': 0,
            'total_files': 0,
            'defect_density': 0.0,
            'avg_complexity': 0.0,
            'max_complexity': 0,
            'violations_by_type': defaultdict(int),
            'violations_by_file': defaultdict(int),
            'complexity_by_file': {}
        }
    
    def count_lines_of_code(self, filepath):
        """Count total lines of code in a file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
                return len(code_lines)
        except Exception as e:
            print(f"Error counting lines in {filepath}: {e}")
            return 0
    
    def parse_violation_line(self, violation_text):
        """
        Parse a Flake8 violation line into structured data
        
        Format: filepath:line:col: CODE message
        Example: ui/app.py:123:45: E501 line too long (82 > 79 characters)
        
        Returns dict with: file, line, col, code, message
        """
        try:
            # Regex to parse: filepath:line:col: CODE message
            pattern = r'^(.+?):(\d+):(\d+):\s+([A-Z]\d{3})\s+(.+)$'
            match = re.match(pattern, violation_text)
            
            if match:
                return {
                    'file': match.group(1),
                    'line': int(match.group(2)),
                    'col': int(match.group(3)),
                    'code': match.group(4),
                    'message': match.group(5).strip()
                }
        except Exception as e:
            print(f"  Warning: Could not parse violation: {violation_text[:50]}...")
        
        return None
    
    def run_flake8_detailed(self):
        """Run Flake8 and collect detailed violation information"""
        print(f"\n{'='*60}")
        print(f"Running Enhanced Flake8 Analysis - {self.timestamp}")
        print(f"{'='*60}\n")
        
        for filepath in PYTHON_FILES:
            if not os.path.exists(filepath):
                print(f"⚠️  File not found: {filepath}")
                continue
            
            print(f"Analyzing: {filepath}")
            
            # Count lines
            loc = self.count_lines_of_code(filepath)
            self.metrics['total_lines'] += loc
            self.metrics['total_files'] += 1
            
            # Run Flake8 with detailed output
            try:
                result = subprocess.run(
                    ['flake8', filepath, '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                if result.stdout:
                    violation_lines = result.stdout.strip().split('\n')
                    file_violation_count = 0
                    
                    for violation_text in violation_lines:
                        if not violation_text.strip():
                            continue
                        
                        # Parse the violation
                        violation_data = self.parse_violation_line(violation_text)
                        
                        if violation_data:
                            # Store detailed violation
                            self.all_violations.append(violation_data)
                            
                            # Update aggregates
                            self.metrics['violations_by_type'][violation_data['code']] += 1
                            file_violation_count += 1
                    
                    self.metrics['violations_by_file'][filepath] = file_violation_count
                    print(f"   Found {file_violation_count} violations")
                else:
                    print(f"   ✓ No violations found")
                    self.metrics['violations_by_file'][filepath] = 0
                
                if result.stderr:
                    print(f"   ⚠️  Warnings: {result.stderr[:100]}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.metrics['violations_by_file'][filepath] = -1
                continue
        
        self.metrics['total_violations'] = len(self.all_violations)
        
        # Calculate defect density
        if self.metrics['total_lines'] > 0:
            self.metrics['defect_density'] = (
                self.metrics['total_violations'] / self.metrics['total_lines']
            ) * 1000
        
        return True
    
    def run_complexity_analysis(self):
        """Run McCabe complexity analysis"""
        print(f"\n{'='*60}")
        print("Running Cyclomatic Complexity Analysis")
        print(f"{'='*60}\n")
        
        complexities = []
        
        for filepath in PYTHON_FILES:
            if not os.path.exists(filepath):
                continue
            
            try:
                result = subprocess.run(
                    ['flake8', filepath, '--max-complexity=8', '--select=C901'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if line and 'C901' in line:
                            match = re.search(r"is too complex \((\d+)\)", line)
                            if match:
                                complexity = int(match.group(1))
                                complexities.append(complexity)
                                self.metrics['complexity_by_file'][filepath] = complexity
                                print(f"   {filepath}: complexity = {complexity}")
                
            except Exception as e:
                print(f"   Error analyzing {filepath}: {e}")
                continue
        
        if complexities:
            self.metrics['avg_complexity'] = sum(complexities) / len(complexities)
            self.metrics['max_complexity'] = max(complexities)
        
        print(f"\nAverage Complexity: {self.metrics['avg_complexity']:.2f}")
        print(f"Maximum Complexity: {self.metrics['max_complexity']}")
    
    def save_detailed_violations_report(self):
        """
        Save detailed, actionable violations report
        THIS IS THE NEW, USEFUL REPORT!
        """
        detailed_file = METRICS_DIR / f"violations_detailed_{self.date}.csv"
        
        print(f"\n{'='*60}")
        print("Saving Detailed Violations Report")
        print(f"{'='*60}")
        
        with open(detailed_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Headers
            writer.writerow([
                'File',
                'Line',
                'Column',
                'Error_Code',
                'Description',
                'Message'
            ])
            
            # Error code descriptions
            descriptions = {
                'E1': 'Indentation',
                'E2': 'Whitespace',
                'E3': 'Blank lines',
                'E4': 'Imports',
                'E5': 'Line length',
                'E7': 'Statements',
                'E9': 'Runtime',
                'W1': 'Indentation',
                'W2': 'Whitespace',
                'W3': 'Blank lines',
                'W5': 'Line breaks',
                'W6': 'Deprecated',
                'F4': 'Import errors',
                'F8': 'Name errors',
                'C4': 'Comprehensions',
                'C9': 'Complexity',
                'D1': 'Missing docstrings',
                'D2': 'Docstring format',
                'D3': 'Docstring quotes',
                'D4': 'Docstring content',
                'B': 'Bugbear',
                'I': 'Import order'
            }
            
            # Sort violations by file, then line number
            sorted_violations = sorted(
                self.all_violations,
                key=lambda x: (x['file'], x['line'], x['col'])
            )
            
            # Write all violations
            for v in sorted_violations:
                desc = descriptions.get(v['code'][:2], 'Other')
                writer.writerow([
                    v['file'],
                    v['line'],
                    v['col'],
                    v['code'],
                    desc,
                    v['message']
                ])
        
        print(f"✓ Detailed violations saved to: {detailed_file}")
        print(f"  Total violations: {len(self.all_violations)}")
        print(f"  You can now open this CSV to see exactly where each issue is!")
        
        return detailed_file
    
    def save_violations_by_file_report(self):
        """Save a summary showing top issues per file"""
        summary_file = METRICS_DIR / f"violations_by_file_{self.date}.csv"
        
        # Group violations by file
        file_violations = defaultdict(lambda: defaultdict(int))
        
        for v in self.all_violations:
            file_violations[v['file']][v['code']] += 1
        
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['File', 'Error_Code', 'Count', 'Description'])
            
            descriptions = {
                'E501': 'Line too long',
                'W293': 'Blank line contains whitespace',
                'W291': 'Trailing whitespace',
                'E302': 'Expected 2 blank lines',
                'D400': 'First line should end with period',
                'I201': 'Missing import order',
                'E128': 'Continuation line under-indented',
                'C901': 'Function too complex',
                'D100': 'Missing module docstring',
                'F401': 'Module imported but unused'
            }
            
            # Sort by file, then by count
            for filepath in sorted(file_violations.keys()):
                codes = file_violations[filepath]
                for code, count in sorted(codes.items(), key=lambda x: x[1], reverse=True):
                    desc = descriptions.get(code, code)
                    writer.writerow([filepath, code, count, desc])
        
        print(f"✓ File summary saved to: {summary_file}")
    
    def save_daily_summary(self):
        """Save daily summary to CSV"""
        summary_file = METRICS_DIR / "daily_summary.csv"
        file_exists = summary_file.exists()
        
        with open(summary_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    'Date', 'Timestamp', 'Total_Violations', 'Total_Lines',
                    'Total_Files', 'Defect_Density', 'Avg_Complexity',
                    'Max_Complexity', 'E_Errors', 'W_Warnings', 'F_Errors'
                ])
            
            e_errors = sum(v for k, v in self.metrics['violations_by_type'].items() if k.startswith('E'))
            w_warnings = sum(v for k, v in self.metrics['violations_by_type'].items() if k.startswith('W'))
            f_errors = sum(v for k, v in self.metrics['violations_by_type'].items() if k.startswith('F'))
            
            writer.writerow([
                self.metrics['date'], self.metrics['timestamp'],
                self.metrics['total_violations'], self.metrics['total_lines'],
                self.metrics['total_files'], f"{self.metrics['defect_density']:.2f}",
                f"{self.metrics['avg_complexity']:.2f}", self.metrics['max_complexity'],
                e_errors, w_warnings, f_errors
            ])
        
        print(f"✓ Daily summary saved to: {summary_file}")
    
    def save_complexity_report(self):
        """Save complexity analysis by file"""
        complexity_file = METRICS_DIR / f"complexity_{self.date}.csv"
        
        with open(complexity_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['File', 'Complexity', 'Lines_of_Code', 'Violations'])
            
            for filepath in PYTHON_FILES:
                if os.path.exists(filepath):
                    complexity = self.metrics['complexity_by_file'].get(filepath, 0)
                    loc = self.count_lines_of_code(filepath)
                    violations = self.metrics['violations_by_file'].get(filepath, 0)
                    writer.writerow([filepath, complexity, loc, violations])
        
        print(f"✓ Complexity report saved to: {complexity_file}")
    
    def generate_top_issues_report(self):
        """Generate a report of the most common issues"""
        print(f"\n{'='*60}")
        print("TOP 10 MOST COMMON ISSUES")
        print(f"{'='*60}\n")
        
        issue_descriptions = {
            'E501': 'Line too long (>79 characters)',
            'W293': 'Blank line contains whitespace',
            'W291': 'Trailing whitespace',
            'E302': 'Expected 2 blank lines, found fewer',
            'D400': 'First line should end with a period',
            'I201': 'Missing newline between import groups',
            'E128': 'Continuation line under-indented',
            'C408': 'Unnecessary dict/list/tuple call - rewrite as literal',
            'D100': 'Missing docstring in public module',
            'F401': 'Module imported but unused',
            'I100': 'Import statements are in wrong order',
            'E251': 'Unexpected spaces around keyword/parameter equals',
            'C901': 'Function is too complex',
            'D103': 'Missing docstring in public function'
        }
        
        top_issues = sorted(
            self.metrics['violations_by_type'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        print(f"{'Code':<8} {'Count':<8} {'Description'}")
        print("-" * 60)
        for code, count in top_issues:
            desc = issue_descriptions.get(code, 'See Flake8 documentation')
            print(f"{code:<8} {count:<8} {desc}")
        
        print(f"\n{'='*60}\n")
    
    def generate_actionable_summary(self):
        """Generate an actionable summary with recommendations"""
        print(f"\n{'='*60}")
        print("ACTIONABLE SUMMARY")
        print(f"{'='*60}")
        print(f"Date: {self.date}")
        print(f"Total Violations: {self.metrics['total_violations']}")
        print(f"Total Lines of Code: {self.metrics['total_lines']}")
        print(f"Defect Density: {self.metrics['defect_density']:.2f} violations/KLOC")
        
        print(f"\n📁 Files Ranked by Violations:")
        ranked_files = sorted(
            self.metrics['violations_by_file'].items(),
            key=lambda x: x[1] if x[1] >= 0 else 0,
            reverse=True
        )
        
        for i, (filepath, count) in enumerate(ranked_files[:5], 1):
            if count >= 0:
                print(f"  {i}. {filepath}: {count} violations")
        
        print(f"\n💡 RECOMMENDED ACTIONS:")
        print(f"  1. Open: metrics_data/violations_detailed_{self.date}.csv")
        print(f"     → See EVERY violation with file, line, and column")
        print(f"  2. Open: metrics_data/violations_by_file_{self.date}.csv")
        print(f"     → See which files have which types of issues")
        print(f"  3. Focus on the most common issues first (see above)")
        print(f"  4. Use your IDE's auto-format to fix many issues automatically")
        
        print(f"\n🎯 Quick Wins (Easy to Fix):")
        quick_wins = {
            'W291': 'Trailing whitespace - auto-trim in IDE',
            'W293': 'Blank line whitespace - auto-trim in IDE', 
            'E302': 'Add blank lines between functions',
            'I100': 'Reorder imports (use isort or IDE)',
            'F401': 'Remove unused imports'
        }
        
        for code, desc in quick_wins.items():
            if code in self.metrics['violations_by_type']:
                count = self.metrics['violations_by_type'][code]
                print(f"  • {code} ({count}x): {desc}")
        
        print(f"{'='*60}\n")

def main():
    """Main execution function"""
    
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass
    
    collector = EnhancedMetricsCollector()
    
    # Run analyses
    if not collector.run_flake8_detailed():
        print("❌ Flake8 analysis failed")
        return
    
    collector.run_complexity_analysis()
    
    # Save all reports
    collector.save_detailed_violations_report()  # NEW: Most useful!
    collector.save_violations_by_file_report()   # NEW: Also useful!
    collector.save_daily_summary()
    collector.save_complexity_report()
    
    # Generate summaries
    collector.generate_top_issues_report()
    collector.generate_actionable_summary()
    
    print("✅ Enhanced metrics collection complete!")
    print(f"✅ All reports saved to: {METRICS_DIR}")

if __name__ == "__main__":
    main()
