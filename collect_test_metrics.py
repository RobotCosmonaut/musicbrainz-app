#!/usr/bin/env python3
"""
Automated Test Metrics Collection Script for Orchestr8r Project
Collects pytest results and coverage data, integrates with existing metrics

Author: Ron Denny
Course: CS 8314 - Software Engineering Research
"""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import csv
import json
import re

PROJECT_ROOT = Path(__file__).parent
METRICS_DIR = PROJECT_ROOT / "metrics_data"
METRICS_DIR.mkdir(exist_ok=True)

class TestMetricsCollector:
    """Collects and stores pytest and coverage metrics"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.metrics = {
            'timestamp': self.timestamp,
            'date': self.date,
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'error_tests': 0,
            'test_duration': 0.0,
            'pass_rate': 0.0,
            'coverage_percentage': 0.0,
            'coverage_lines_covered': 0,
            'coverage_lines_total': 0,
            'avg_test_duration': 0.0
        }
    
    def run_tests(self):
        """Run pytest with coverage"""
        print(f"\n{'='*60}")
        print(f"Running Tests - {self.timestamp}")
        print(f"{'='*60}\n")
        
        try:
            # Run pytest
            result = subprocess.run(
                ['pytest', '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("❌ Tests timed out after 5 minutes")
            return False
        except FileNotFoundError:
            print("❌ pytest not installed. Run: pip install -r requirements-testing.txt")
            return False
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return False
    
    def parse_junit_xml(self):
        """Parse JUnit XML output from pytest"""
        junit_file = METRICS_DIR / "pytest_report.xml"
        
        if not junit_file.exists():
            print(f"⚠️  JUnit XML not found at {junit_file}")
            return False
        
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            # Get test suite statistics
            testsuite = root.find('.//testsuite')
            if testsuite is not None:
                self.metrics['total_tests'] = int(testsuite.get('tests', 0))
                self.metrics['failed_tests'] = int(testsuite.get('failures', 0))
                self.metrics['error_tests'] = int(testsuite.get('errors', 0))
                self.metrics['skipped_tests'] = int(testsuite.get('skipped', 0))
                self.metrics['test_duration'] = float(testsuite.get('time', 0))
                
                self.metrics['passed_tests'] = (
                    self.metrics['total_tests'] - 
                    self.metrics['failed_tests'] - 
                    self.metrics['error_tests'] - 
                    self.metrics['skipped_tests']
                )
                
                if self.metrics['total_tests'] > 0:
                    self.metrics['pass_rate'] = (
                        self.metrics['passed_tests'] / self.metrics['total_tests']
                    ) * 100
                    self.metrics['avg_test_duration'] = (
                        self.metrics['test_duration'] / self.metrics['total_tests']
                    )
            
            print(f"✓ Parsed test results: {self.metrics['total_tests']} tests")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing JUnit XML: {e}")
            return False
    
    def parse_coverage_xml(self):
        """Parse coverage XML output"""
        coverage_file = METRICS_DIR / "coverage.xml"
        
        if not coverage_file.exists():
            print(f"⚠️  Coverage XML not found at {coverage_file}")
            return False
        
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            # Get coverage statistics
            coverage = root.find('.//coverage')
            if coverage is not None:
                lines_covered = int(coverage.get('lines-covered', 0))
                lines_valid = int(coverage.get('lines-valid', 0))
                
                self.metrics['coverage_lines_covered'] = lines_covered
                self.metrics['coverage_lines_total'] = lines_valid
                
                if lines_valid > 0:
                    self.metrics['coverage_percentage'] = (
                        lines_covered / lines_valid
                    ) * 100
            
            print(f"✓ Coverage: {self.metrics['coverage_percentage']:.2f}%")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing coverage XML: {e}")
            return False
    
    def save_test_summary(self):
        """Save test summary to CSV"""
        summary_file = METRICS_DIR / "test_summary.csv"
        
        file_exists = summary_file.exists()
        
        with open(summary_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    'Date',
                    'Timestamp',
                    'Total_Tests',
                    'Passed',
                    'Failed',
                    'Skipped',
                    'Errors',
                    'Pass_Rate',
                    'Coverage_Percentage',
                    'Coverage_Lines_Covered',
                    'Coverage_Lines_Total',
                    'Test_Duration',
                    'Avg_Test_Duration'
                ])
            
            writer.writerow([
                self.metrics['date'],
                self.metrics['timestamp'],
                self.metrics['total_tests'],
                self.metrics['passed_tests'],
                self.metrics['failed_tests'],
                self.metrics['skipped_tests'],
                self.metrics['error_tests'],
                f"{self.metrics['pass_rate']:.2f}",
                f"{self.metrics['coverage_percentage']:.2f}",
                self.metrics['coverage_lines_covered'],
                self.metrics['coverage_lines_total'],
                f"{self.metrics['test_duration']:.2f}",
                f"{self.metrics['avg_test_duration']:.4f}"
            ])
        
        print(f"\n✓ Test summary saved to: {summary_file}")
    
    def generate_report(self):
        """Generate human-readable report"""
        print(f"\n{'='*60}")
        print("TEST METRICS SUMMARY")
        print(f"{'='*60}")
        print(f"Date: {self.date}")
        print(f"Total Tests: {self.metrics['total_tests']}")
        print(f"  ✓ Passed: {self.metrics['passed_tests']}")
        print(f"  ✗ Failed: {self.metrics['failed_tests']}")
        print(f"  ⊘ Skipped: {self.metrics['skipped_tests']}")
        print(f"  ⚠ Errors: {self.metrics['error_tests']}")
        print(f"Pass Rate: {self.metrics['pass_rate']:.2f}%")
        print(f"Coverage: {self.metrics['coverage_percentage']:.2f}%")
        print(f"  Lines Covered: {self.metrics['coverage_lines_covered']}/{self.metrics['coverage_lines_total']}")
        print(f"Test Duration: {self.metrics['test_duration']:.2f}s")
        print(f"  Avg per Test: {self.metrics['avg_test_duration']:.4f}s")
        print(f"{'='*60}\n")

def main():
    """Main execution function"""
    collector = TestMetricsCollector()
    
    # Run tests
    if not collector.run_tests():
        print("⚠️  Tests completed with failures")
    
    # Parse results
    collector.parse_junit_xml()
    collector.parse_coverage_xml()
    
    # Save metrics
    collector.save_test_summary()
    
    # Generate report
    collector.generate_report()
    
    print("✓ Test metrics collection complete!")
    print(f"✓ Results saved to: {METRICS_DIR}")
    print(f"\n💡 View coverage report: {METRICS_DIR / 'coverage_html' / 'index.html'}")
    print(f"💡 View test report: {METRICS_DIR / 'pytest_report.html'}")

if __name__ == "__main__":
    main()