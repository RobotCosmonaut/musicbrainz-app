#!/usr/bin/env python3
"""
Comprehensive Test Metrics Collection
Collects multiple dimensions of test quality metrics

Author: Ron Denny
"""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import csv
import json
import re
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent
METRICS_DIR = PROJECT_ROOT / "metrics_data"
METRICS_DIR.mkdir(exist_ok=True)

class ComprehensiveTestMetrics:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.metrics = {
            'timestamp': self.timestamp,
            'date': self.date,
            
            # Basic test metrics
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            
            # Coverage metrics
            'line_coverage': 0.0,
            'branch_coverage': 0.0,
            'function_coverage': 0.0,
            
            # Performance metrics
            'avg_test_duration': 0.0,
            'slowest_test_duration': 0.0,
            'fastest_test_duration': 0.0,
            
            # Test distribution
            'unit_tests': 0,
            'integration_tests': 0,
            'api_tests': 0,
            'security_tests': 0,
            'performance_tests': 0,
            
            # Code quality from tests
            'assertions_per_test': 0.0,
            'test_code_ratio': 0.0,  # test LOC / production LOC
            
            # Mutation testing (if enabled)
            'mutation_score': 0.0,
            'mutations_killed': 0,
            'mutations_survived': 0,
            
            # Additional metrics
            'flaky_tests': 0,
            'test_files': 0,
            'avg_assertions': 0.0
        }
    
    def run_comprehensive_tests(self):
        """Run all test categories with detailed reporting"""
        print(f"\n{'='*60}")
        print(f"Running Comprehensive Test Suite - {self.timestamp}")
        print(f"{'='*60}\n")
        
        try:
            # Run with all markers and detailed output
            result = subprocess.run([
                'pytest',
                '-v',
                '--tb=short',
                '--cov=services',
                '--cov=gateway', 
                '--cov=shared',
                '--cov-report=html:metrics_data/coverage_html',
                '--cov-report=xml:metrics_data/coverage.xml',
                '--cov-report=term-missing',
                '--cov-branch',  # Enable branch coverage
                '--html=metrics_data/pytest_report.html',
                '--self-contained-html',
                '--junitxml=metrics_data/pytest_report.xml',
                '--timeout=30',
                '-m', '',  # Run all markers
                '--benchmark-only',  # Include benchmarks if pytest-benchmark installed
                '--durations=10'  # Show 10 slowest tests
            ],
            capture_output=True,
            text=True,
            timeout=600
            )
            
            print(result.stdout)
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Test suite timed out")
            return False
        except FileNotFoundError:
            print("❌ pytest not installed")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def parse_junit_detailed(self):
        """Parse JUnit XML with detailed test information"""
        junit_file = METRICS_DIR / "pytest_report.xml"
        
        if not junit_file.exists():
            return False
        
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
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
            
            # Parse individual test cases for detailed metrics
            test_durations = []
            test_markers = defaultdict(int)
            assertion_counts = []
            
            for testcase in root.findall('.//testcase'):
                # Duration
                duration = float(testcase.get('time', 0))
                test_durations.append(duration)
                
                # Test markers (unit, integration, etc.)
                classname = testcase.get('classname', '')
                if 'integration' in classname:
                    test_markers['integration'] += 1
                elif 'api' in classname:
                    test_markers['api'] += 1
                elif 'security' in classname:
                    test_markers['security'] += 1
                elif 'performance' in classname or 'benchmark' in classname:
                    test_markers['performance'] += 1
                else:
                    test_markers['unit'] += 1
            
            # Calculate performance metrics
            if test_durations:
                self.metrics['avg_test_duration'] = sum(test_durations) / len(test_durations)
                self.metrics['slowest_test_duration'] = max(test_durations)
                self.metrics['fastest_test_duration'] = min(test_durations)
            
            # Store test distribution
            self.metrics['unit_tests'] = test_markers.get('unit', 0)
            self.metrics['integration_tests'] = test_markers.get('integration', 0)
            self.metrics['api_tests'] = test_markers.get('api', 0)
            self.metrics['security_tests'] = test_markers.get('security', 0)
            self.metrics['performance_tests'] = test_markers.get('performance', 0)
            
            print(f"✓ Parsed detailed test results")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing JUnit: {e}")
            return False
    
    def parse_coverage_detailed(self):
        """Parse coverage with branch coverage"""
        coverage_file = METRICS_DIR / "coverage.xml"
        
        if not coverage_file.exists():
            return False
        
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            coverage = root.find('.//coverage')
            if coverage is not None:
                # Line coverage
                lines_covered = int(coverage.get('lines-covered', 0))
                lines_valid = int(coverage.get('lines-valid', 0))
                
                if lines_valid > 0:
                    self.metrics['line_coverage'] = (lines_covered / lines_valid) * 100
                
                # Branch coverage
                branches_covered = int(coverage.get('branches-covered', 0))
                branches_valid = int(coverage.get('branches-valid', 0))
                
                if branches_valid > 0:
                    self.metrics['branch_coverage'] = (branches_covered / branches_valid) * 100
            
            print(f"✓ Coverage: {self.metrics['line_coverage']:.2f}% lines, "
                  f"{self.metrics['branch_coverage']:.2f}% branches")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing coverage: {e}")
            return False
    
    def calculate_test_code_ratio(self):
        """Calculate ratio of test code to production code"""
        try:
            # Count production code lines
            prod_files = [
                "services/artist_service.py",
                "services/album_service.py",
                "services/recommendation_service.py",
                "services/musicbrainz_service.py",
                "gateway/main.py",
                "shared/database.py",
                "shared/models.py"
            ]
            
            prod_lines = 0
            for filepath in prod_files:
                if Path(filepath).exists():
                    with open(filepath, 'r') as f:
                        prod_lines += len([l for l in f if l.strip() and not l.strip().startswith('#')])
            
            # Count test code lines
            test_lines = 0
            test_files = 0
            for test_file in Path('tests').rglob('test_*.py'):
                test_files += 1
                with open(test_file, 'r') as f:
                    test_lines += len([l for l in f if l.strip() and not l.strip().startswith('#')])
            
            self.metrics['test_files'] = test_files
            
            if prod_lines > 0:
                self.metrics['test_code_ratio'] = test_lines / prod_lines
            
            print(f"✓ Test/Production ratio: {self.metrics['test_code_ratio']:.2f}")
            
        except Exception as e:
            print(f"⚠️  Could not calculate code ratio: {e}")
    
    def run_mutation_testing(self):
        """Run mutation testing with mutmut"""
        print("\n" + "="*60)
        print("Running Mutation Testing")
        print("="*60)
        
        try:
            # Check if mutmut is installed
            subprocess.run(['mutmut', '--version'], 
                         capture_output=True, check=True)
            
            # Run mutmut
            result = subprocess.run([
                'mutmut', 'run',
                '--paths-to-mutate=services/,gateway/,shared/'
            ], capture_output=True, text=True, timeout=300)
            
            # Parse results
            results_match = re.search(r'(\d+) mutations\. (\d+) killed, (\d+) survived', 
                                    result.stdout)
            if results_match:
                total = int(results_match.group(1))
                killed = int(results_match.group(2))
                survived = int(results_match.group(3))
                
                self.metrics['mutations_killed'] = killed
                self.metrics['mutations_survived'] = survived
                if total > 0:
                    self.metrics['mutation_score'] = (killed / total) * 100
                
                print(f"✓ Mutation score: {self.metrics['mutation_score']:.2f}%")
            
        except FileNotFoundError:
            print("⚠️  mutmut not installed (pip install mutmut)")
        except subprocess.TimeoutExpired:
            print("⚠️  Mutation testing timed out")
        except Exception as e:
            print(f"⚠️  Mutation testing error: {e}")
    
    def save_comprehensive_summary(self):
        """Save comprehensive metrics summary"""
        summary_file = METRICS_DIR / "comprehensive_test_metrics.csv"
        
        file_exists = summary_file.exists()
        
        with open(summary_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    'Date', 'Timestamp',
                    # Basic metrics
                    'Total_Tests', 'Passed', 'Failed', 'Skipped',
                    # Coverage
                    'Line_Coverage_%', 'Branch_Coverage_%',
                    # Performance
                    'Avg_Duration_ms', 'Slowest_ms', 'Fastest_ms',
                    # Distribution
                    'Unit_Tests', 'Integration_Tests', 'API_Tests', 
                    'Security_Tests', 'Performance_Tests',
                    # Quality
                    'Test_Code_Ratio', 'Test_Files',
                    # Mutation
                    'Mutation_Score_%', 'Mutations_Killed', 'Mutations_Survived'
                ])
            
            writer.writerow([
                self.metrics['date'],
                self.metrics['timestamp'],
                self.metrics['total_tests'],
                self.metrics['passed_tests'],
                self.metrics['failed_tests'],
                self.metrics['skipped_tests'],
                f"{self.metrics['line_coverage']:.2f}",
                f"{self.metrics['branch_coverage']:.2f}",
                f"{self.metrics['avg_test_duration']*1000:.2f}",
                f"{self.metrics['slowest_test_duration']*1000:.2f}",
                f"{self.metrics['fastest_test_duration']*1000:.2f}",
                self.metrics['unit_tests'],
                self.metrics['integration_tests'],
                self.metrics['api_tests'],
                self.metrics['security_tests'],
                self.metrics['performance_tests'],
                f"{self.metrics['test_code_ratio']:.2f}",
                self.metrics['test_files'],
                f"{self.metrics['mutation_score']:.2f}",
                self.metrics['mutations_killed'],
                self.metrics['mutations_survived']
            ])
        
        print(f"\n✓ Comprehensive metrics saved to: {summary_file}")
    
    def generate_detailed_report(self):
        """Generate detailed test quality report"""
        print(f"\n{'='*60}")
        print("COMPREHENSIVE TEST METRICS REPORT")
        print(f"{'='*60}")
        print(f"Date: {self.date}")
        
        print(f"\n📊 Test Execution:")
        print(f"  Total Tests: {self.metrics['total_tests']}")
        print(f"  ✓ Passed: {self.metrics['passed_tests']}")
        print(f"  ✗ Failed: {self.metrics['failed_tests']}")
        print(f"  ⊘ Skipped: {self.metrics['skipped_tests']}")
        
        if self.metrics['total_tests'] > 0:
            pass_rate = (self.metrics['passed_tests'] / self.metrics['total_tests']) * 100
            print(f"  Pass Rate: {pass_rate:.2f}%")
        
        print(f"\n📈 Code Coverage:")
        print(f"  Line Coverage: {self.metrics['line_coverage']:.2f}%")
        print(f"  Branch Coverage: {self.metrics['branch_coverage']:.2f}%")
        
        print(f"\n⚡ Performance:")
        print(f"  Average Test Duration: {self.metrics['avg_test_duration']*1000:.2f}ms")
        print(f"  Slowest Test: {self.metrics['slowest_test_duration']*1000:.2f}ms")
        print(f"  Fastest Test: {self.metrics['fastest_test_duration']*1000:.2f}ms")
        
        print(f"\n🎯 Test Distribution:")
        print(f"  Unit Tests: {self.metrics['unit_tests']}")
        print(f"  Integration Tests: {self.metrics['integration_tests']}")
        print(f"  API Tests: {self.metrics['api_tests']}")
        print(f"  Security Tests: {self.metrics['security_tests']}")
        print(f"  Performance Tests: {self.metrics['performance_tests']}")
        
        print(f"\n📝 Test Quality:")
        print(f"  Test/Production Code Ratio: {self.metrics['test_code_ratio']:.2f}")
        print(f"  Test Files: {self.metrics['test_files']}")
        
        if self.metrics['mutation_score'] > 0:
            print(f"\n🧬 Mutation Testing:")
            print(f"  Mutation Score: {self.metrics['mutation_score']:.2f}%")
            print(f"  Mutations Killed: {self.metrics['mutations_killed']}")
            print(f"  Mutations Survived: {self.metrics['mutations_survived']}")
        
        print(f"{'='*60}\n")

def main():
    collector = ComprehensiveTestMetrics()
    
    # Run comprehensive test suite
    if not collector.run_comprehensive_tests():
        print("⚠️  Test execution had issues")
    
    # Parse detailed results
    collector.parse_junit_detailed()
    collector.parse_coverage_detailed()
    
    # Additional metrics
    collector.calculate_test_code_ratio()
    collector.run_mutation_testing()
    
    # Save and report
    collector.save_comprehensive_summary()
    collector.generate_detailed_report()
    
    print("✓ Comprehensive metrics collection complete!")

if __name__ == "__main__":
    main()