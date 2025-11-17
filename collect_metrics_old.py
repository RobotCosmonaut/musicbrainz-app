#!/usr/bin/env python3
"""
Automated Flake8 Metrics Collection Script for Orchestr8r Project
FIXED VERSION - Properly counts violations per file

Author: Ron Denny
Course: CS 8314 - Software Engineering Research
"""

import subprocess
import os
import csv
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import re

# Configuration
PROJECT_ROOT = Path(__file__).parent
METRICS_DIR = PROJECT_ROOT / "metrics_data"
METRICS_DIR.mkdir(exist_ok=True)

# Files to analyze (all Python service files)
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

class FlakeMetricsCollector:
    """Collects and stores Flake8 metrics for software quality analysis"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.date = datetime.now().strftime("%Y-%m-%d")
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
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Exclude blank lines and comments
                code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
                return len(code_lines)
        except Exception as e:
            print(f"Error counting lines in {filepath}: {e}")
            return 0
    
    def run_flake8_basic(self):
        """Run basic Flake8 analysis - FIXED VERSION"""
        print(f"\n{'='*60}")
        print(f"Running Flake8 Analysis - {self.timestamp}")
        print(f"{'='*60}\n")
        
        all_violations = []
        
        for filepath in PYTHON_FILES:
            if not os.path.exists(filepath):
                print(f"⚠️  File not found: {filepath}")
                continue
            
            print(f"Analyzing: {filepath}")
            
            # Count lines
            loc = self.count_lines_of_code(filepath)
            self.metrics['total_lines'] += loc
            self.metrics['total_files'] += 1
            
            # Run Flake8
            try:
                result = subprocess.run(
                    ['flake8', filepath, '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s'],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    violations = result.stdout.strip().split('\n')
                    all_violations.extend(violations)
                    
                    # Count violations for THIS file
                    file_violation_count = 0
                    
                    # Parse violations
                    for violation in violations:
                        if violation:
                            # Extract error code - EXPANDED REGEX to catch all codes
                            match = re.search(r'([EWFCDSBI]\d{3})', violation)
                            if match:
                                error_code = match.group(1)
                                self.metrics['violations_by_type'][error_code] += 1
                                file_violation_count += 1
                    
                    # Store the actual count for this file
                    self.metrics['violations_by_file'][filepath] = file_violation_count
                    
                    print(f"   Found {file_violation_count} violations")
                else:
                    print(f"   ✓ No violations found")
                    self.metrics['violations_by_file'][filepath] = 0
                    
            except FileNotFoundError:
                print("   ❌ Flake8 not installed. Run: pip install flake8")
                return False
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        self.metrics['total_violations'] = len(all_violations)
        
        # Calculate defect density (violations per 1000 lines of code)
        if self.metrics['total_lines'] > 0:
            self.metrics['defect_density'] = (
                self.metrics['total_violations'] / self.metrics['total_lines']
            ) * 1000
        
        return True
    
    def run_complexity_analysis(self):
        """Run McCabe complexity analysis using Flake8"""
        print(f"\n{'='*60}")
        print("Running Cyclomatic Complexity Analysis")
        print(f"{'='*60}\n")
        
        complexities = []
        
        for filepath in PYTHON_FILES:
            if not os.path.exists(filepath):
                continue
            
            try:
                # Run Flake8 with McCabe complexity plugin
                result = subprocess.run(
                    ['flake8', filepath, '--max-complexity=8', '--select=C901'],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    # Parse complexity warnings
                    for line in result.stdout.strip().split('\n'):
                        if line and 'C901' in line:
                            # Extract complexity value
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
    
    def save_daily_summary(self):
        """Save daily summary to CSV"""
        summary_file = METRICS_DIR / "daily_summary.csv"
        
        # Check if file exists to determine if we need headers
        file_exists = summary_file.exists()
        
        with open(summary_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                # Write headers
                writer.writerow([
                    'Date',
                    'Timestamp',
                    'Total_Violations',
                    'Total_Lines',
                    'Total_Files',
                    'Defect_Density',
                    'Avg_Complexity',
                    'Max_Complexity',
                    'E_Errors',
                    'W_Warnings',
                    'F_Errors'
                ])
            
            # Count error types
            e_errors = sum(v for k, v in self.metrics['violations_by_type'].items() if k.startswith('E'))
            w_warnings = sum(v for k, v in self.metrics['violations_by_type'].items() if k.startswith('W'))
            f_errors = sum(v for k, v in self.metrics['violations_by_type'].items() if k.startswith('F'))
            
            # Write data
            writer.writerow([
                self.metrics['date'],
                self.metrics['timestamp'],
                self.metrics['total_violations'],
                self.metrics['total_lines'],
                self.metrics['total_files'],
                f"{self.metrics['defect_density']:.2f}",
                f"{self.metrics['avg_complexity']:.2f}",
                self.metrics['max_complexity'],
                e_errors,
                w_warnings,
                f_errors
            ])
        
        print(f"\n✓ Daily summary saved to: {summary_file}")
    
    def save_detailed_violations(self):
        """Save detailed violation breakdown"""
        violations_file = METRICS_DIR / f"violations_{self.date}.csv"
        
        with open(violations_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Error_Code', 'Count', 'Description'])
            
            # Error code descriptions
            descriptions = {
                'E1': 'Indentation errors',
                'E2': 'Whitespace errors',
                'E3': 'Blank line errors',
                'E4': 'Import errors',
                'E5': 'Line length errors',
                'E7': 'Statement errors',
                'E9': 'Runtime errors',
                'W1': 'Indentation warnings',
                'W2': 'Whitespace warnings',
                'W3': 'Blank line warnings',
                'W5': 'Line break warnings',
                'W6': 'Deprecated warnings',
                'F4': 'Module import errors',
                'F8': 'Name errors',
                'C9': 'Complexity warnings',
                'D1': 'Missing docstrings',
                'D2': 'Docstring whitespace',
                'D3': 'Docstring quotes',
                'D4': 'Docstring content',
                'S': 'Simplify suggestions',
                'B': 'Bugbear findings',
                'I': 'Import order'
            }
            
            for error_code, count in sorted(self.metrics['violations_by_type'].items()):
                desc = descriptions.get(error_code[:2], 'Other')
                writer.writerow([error_code, count, desc])
        
        print(f"✓ Detailed violations saved to: {violations_file}")
    
    def save_complexity_report(self):
        """Save complexity analysis by file"""
        complexity_file = METRICS_DIR / f"complexity_{self.date}.csv"
        
        with open(complexity_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['File', 'Complexity', 'Lines_of_Code', 'Violations'])
            
            for filepath in PYTHON_FILES:
                if os.path.exists(filepath):
                    complexity = self.metrics['complexity_by_file'].get(filepath, 0)
                    loc = self.count_lines_of_code(filepath)
                    violations = self.metrics['violations_by_file'].get(filepath, 0)
                    
                    writer.writerow([filepath, complexity, loc, violations])
        
        print(f"✓ Complexity report saved to: {complexity_file}")
    
    def generate_report(self):
        """Generate human-readable report"""
        print(f"\n{'='*60}")
        print("METRICS SUMMARY")
        print(f"{'='*60}")
        print(f"Date: {self.date}")
        print(f"Total Files Analyzed: {self.metrics['total_files']}")
        print(f"Total Lines of Code: {self.metrics['total_lines']}")
        print(f"Total Violations: {self.metrics['total_violations']}")
        print(f"Defect Density: {self.metrics['defect_density']:.2f} violations/KLOC")
        print(f"Average Complexity: {self.metrics['avg_complexity']:.2f}")
        print(f"Maximum Complexity: {self.metrics['max_complexity']}")
        
        print(f"\nTop Violation Types:")
        for error_code, count in sorted(
            self.metrics['violations_by_type'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]:
            print(f"  {error_code}: {count}")
        
        print(f"\nFiles with Most Violations:")
        for filepath, count in sorted(
            self.metrics['violations_by_file'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]:
            print(f"  {filepath}: {count}")
        
        print(f"{'='*60}\n")

def main():
    """Main execution function"""
    collector = FlakeMetricsCollector()
    
    # Run analyses
    if not collector.run_flake8_basic():
        print("❌ Flake8 analysis failed. Please install flake8:")
        print("   pip install flake8 flake8-mccabe")
        return
    
    collector.run_complexity_analysis()
    
    # Save results
    collector.save_daily_summary()
    collector.save_detailed_violations()
    collector.save_complexity_report()
    
    # Generate report
    collector.generate_report()
    
    print("✓ Metrics collection complete!")
    print(f"✓ Results saved to: {METRICS_DIR}")

if __name__ == "__main__":
    main()
