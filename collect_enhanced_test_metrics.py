#!/usr/bin/env python3
"""
Comprehensive Test Metrics Collection - FIXED VERSION
Runs all tests properly without skipping

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
            'error_tests': 0,
            
            # Coverage metrics
            'line_coverage': 0.0,
            'branch_coverage': 0.0,
            
            # Performance metrics
            'avg_test_duration': 0.0,
            'slowest_test_duration': 0.0,
            'fastest_test_duration': 0.0,
            'total_duration': 0.0,
            
            # Test distribution
            'unit_tests': 0,
            'integration_tests': 0,
            'api_tests': 0,
            'database_tests': 0,
            
            # Code quality from tests
            'test_code_ratio': 0.0,
            'test_files': 0,
            
            # Additional metrics
            'pass_rate': 0.0,
            'coverage_lines_covered': 0,
            'coverage_lines_total': 0
        }
    
    def run_comprehensive_tests(self):
        """Run all tests with coverage - NO --benchmark-only flag"""
        print(f"\n{'='*60}")
        print(f"Running Comprehensive Test Suite - {self.timestamp}")
        print(f"{'='*60}\n")
        
        try:
            # FIXED: Removed --benchmark-only flag
            # Run ALL tests including unit, integration, etc.
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
                '--durations=10',  # Show 10 slowest tests
                '-W', 'ignore::DeprecationWarning'  # Suppress deprecation warnings
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=600
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr[:500])
            
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
        """Parse JUnit XML using classname for classification (no file attribute)"""
        junit_file = METRICS_DIR / "pytest_report.xml"
        
        if not junit_file.exists():
            print("⚠️  JUnit XML not found")
            return False
        
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            # Get test suite stats
            testsuite = root.find('.//testsuite')
            if testsuite is not None:
                self.metrics['total_tests'] = int(testsuite.get('tests', 0))
                self.metrics['failed_tests'] = int(testsuite.get('failures', 0))
                self.metrics['error_tests'] = int(testsuite.get('errors', 0))
                self.metrics['skipped_tests'] = int(testsuite.get('skipped', 0))
                self.metrics['total_duration'] = float(testsuite.get('time', 0))
                
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
            
            # Parse individual test cases
            test_durations = []
            test_markers = defaultdict(int)
            
            print("\n📋 Analyzing individual tests (using classname for classification)...")
            
            for i, testcase in enumerate(root.findall('.//testcase'), 1):
                # Duration
                duration = float(testcase.get('time', 0))
                test_durations.append(duration)
                
                # Get test info - USE CLASSNAME since file is None
                classname = testcase.get('classname', '')
                name = testcase.get('name', '')
                
                # Show first 5 for debugging
                if i <= 5:
                    print(f"\n  Test {i}: {name}")
                    print(f"    Classname: {classname}")
                    print(f"    Duration: {duration*1000:.3f}ms")
                
                # CLASSIFICATION LOGIC USING CLASSNAME
                classname_lower = classname.lower()
                name_lower = name.lower()
                
                # Check for markers first (for future when you add them)
                properties = testcase.find('.//properties')
                has_marker = False
                
                if properties is not None:
                    for prop in properties.findall('.//property'):
                        if prop.get('name') == 'markers':
                            markers_text = prop.get('value', '').lower()
                            if 'integration' in markers_text:
                                test_markers['integration'] += 1
                                has_marker = True
                                if i <= 5:
                                    print(f"    Classification: Integration (marker)")
                                break
                            elif 'api' in markers_text:
                                test_markers['api'] += 1
                                has_marker = True
                                if i <= 5:
                                    print(f"    Classification: API (marker)")
                                break
                            elif 'database' in markers_text:
                                test_markers['database'] += 1
                                has_marker = True
                                if i <= 5:
                                    print(f"    Classification: Database (marker)")
                                break
                            elif 'unit' in markers_text:
                                test_markers['unit'] += 1
                                has_marker = True
                                if i <= 5:
                                    print(f"    Classification: Unit (marker)")
                                break
                
                # If no marker, classify by classname structure
                if not has_marker:
                    # Extract path from classname
                    # Example: "tests.unit.test_artist_service.TestArtistService" → "tests.unit"
                    # Example: "tests.integration.test_workflow" → "tests.integration"
                    
                    if 'tests.integration' in classname_lower or 'tests\\integration' in classname_lower:
                        test_markers['integration'] += 1
                        if i <= 5:
                            print(f"    Classification: Integration (classname path)")
                    
                    elif 'tests.unit' in classname_lower or 'tests\\unit' in classname_lower:
                        # Further classify unit tests by name patterns
                        if 'gateway' in classname_lower or 'gateway' in name_lower:
                            test_markers['api'] += 1
                            if i <= 5:
                                print(f"    Classification: API (gateway)")
                        
                        elif any(keyword in name_lower for keyword in ['database', 'db_', 'model', '_creation', 'unique_id']):
                            test_markers['database'] += 1
                            if i <= 5:
                                print(f"    Classification: Database (name pattern)")
                        
                        elif any(keyword in name_lower for keyword in ['health', 'search', 'list', 'get_', 'endpoint', 'client']):
                            test_markers['api'] += 1
                            if i <= 5:
                                print(f"    Classification: API (name pattern)")
                        
                        else:
                            test_markers['unit'] += 1
                            if i <= 5:
                                print(f"    Classification: Unit (default)")
                    
                    else:
                        # Fallback for tests not in standard structure
                        if any(keyword in name_lower for keyword in ['workflow', 'integration', 'end_to_end', 'e2e', 'full_']):
                            test_markers['integration'] += 1
                            if i <= 5:
                                print(f"    Classification: Integration (name)")
                        elif any(keyword in name_lower for keyword in ['database', 'db_', 'model']):
                            test_markers['database'] += 1
                            if i <= 5:
                                print(f"    Classification: Database (name)")
                        elif any(keyword in name_lower for keyword in ['api', 'endpoint', 'health']):
                            test_markers['api'] += 1
                            if i <= 5:
                                print(f"    Classification: API (name)")
                        else:
                            test_markers['unit'] += 1
                            if i <= 5:
                                print(f"    Classification: Unit (fallback)")
            
            # Calculate performance metrics (these are working!)
            if test_durations:
                non_zero = [d for d in test_durations if d > 0]
                
                if non_zero:
                    self.metrics['avg_test_duration'] = sum(non_zero) / len(non_zero)
                    self.metrics['slowest_test_duration'] = max(test_durations)
                    self.metrics['fastest_test_duration'] = min(non_zero)
                    
                    print(f"\n⚡ Performance Metrics:")
                    print(f"  Tests with measurable duration: {len(non_zero)}/{len(test_durations)}")
                    print(f"  Average: {self.metrics['avg_test_duration']*1000:.2f}ms")
                    print(f"  Slowest: {self.metrics['slowest_test_duration']*1000:.2f}ms")
                    print(f"  Fastest: {self.metrics['fastest_test_duration']*1000:.2f}ms")
                else:
                    total_time = self.metrics['total_duration']
                    num_tests = len(test_durations)
                    self.metrics['avg_test_duration'] = total_time / num_tests if num_tests > 0 else 0
                    self.metrics['slowest_test_duration'] = 0
                    self.metrics['fastest_test_duration'] = 0
                    print(f"\n⚡ All {num_tests} tests completed in < 1ms")
            
            # Store test distribution
            self.metrics['unit_tests'] = test_markers['unit']
            self.metrics['integration_tests'] = test_markers['integration']
            self.metrics['api_tests'] = test_markers['api']
            self.metrics['database_tests'] = test_markers['database']
            
            print(f"\n🎯 Test Classification Results:")
            print(f"  Unit: {self.metrics['unit_tests']}")
            print(f"  Integration: {self.metrics['integration_tests']}")
            print(f"  API: {self.metrics['api_tests']}")
            print(f"  Database: {self.metrics['database_tests']}")
            print(f"  Total Classified: {sum(test_markers.values())}")
            
            if sum(test_markers.values()) != self.metrics['total_tests']:
                print(f"  ⚠️  Mismatch: {sum(test_markers.values())} classified vs {self.metrics['total_tests']} total")
            
            return True
            
        except Exception as e:
            print(f"❌ Error parsing JUnit: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def parse_coverage_detailed(self):
        """Parse coverage with branch coverage - CORRECTED"""
        coverage_file = METRICS_DIR / "coverage.xml"
        
        if not coverage_file.exists():
            print("⚠️  Coverage XML not found")
            return False
        
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()  # root IS the <coverage> element
            
            # Get coverage stats directly from root attributes
            # Line coverage
            lines_covered = int(root.get('lines-covered', 0))
            lines_valid = int(root.get('lines-valid', 0))
            
            self.metrics['coverage_lines_covered'] = lines_covered
            self.metrics['coverage_lines_total'] = lines_valid
            
            if lines_valid > 0:
                self.metrics['line_coverage'] = (lines_covered / lines_valid) * 100
            
            # Branch coverage
            branches_covered = int(root.get('branches-covered', 0))
            branches_valid = int(root.get('branches-valid', 0))
            
            if branches_valid > 0:
                self.metrics['branch_coverage'] = (branches_covered / branches_valid) * 100
            
            print(f"✓ Coverage: {self.metrics['line_coverage']:.2f}% lines, "
                f"{self.metrics['branch_coverage']:.2f}% branches")
            print(f"  Lines: {lines_covered}/{lines_valid}")
            print(f"  Branches: {branches_covered}/{branches_valid}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error parsing coverage: {e}")
            import traceback
            traceback.print_exc()
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
                    with open(filepath, 'r', encoding='utf-8') as f:
                        prod_lines += len([l for l in f if l.strip() and not l.strip().startswith('#')])
            
            # Count test code lines
            test_lines = 0
            test_files = 0
            tests_path = Path('tests')
            if tests_path.exists():
                for test_file in tests_path.rglob('test_*.py'):
                    test_files += 1
                    with open(test_file, 'r', encoding='utf-8') as f:
                        test_lines += len([l for l in f if l.strip() and not l.strip().startswith('#')])
            
            self.metrics['test_files'] = test_files
            
            if prod_lines > 0:
                self.metrics['test_code_ratio'] = test_lines / prod_lines
            
            print(f"✓ Test code: {test_lines} lines across {test_files} files")
            print(f"  Production code: {prod_lines} lines")
            print(f"  Ratio: {self.metrics['test_code_ratio']:.2f}")
            
        except Exception as e:
            print(f"⚠️  Could not calculate code ratio: {e}")
    
    def save_comprehensive_summary(self):
        """Save comprehensive metrics summary"""
        summary_file = METRICS_DIR / "comprehensive_test_metrics.csv"
        
        try:
            print(f"\n📝 Saving metrics to: {summary_file}")
            print(f"   Directory exists: {METRICS_DIR.exists()}")
            print(f"   File exists: {summary_file.exists()}")
            
            file_exists = summary_file.exists()
            
            with open(summary_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                if not file_exists:
                    print(f"   Creating new CSV file with headers...")
                    writer.writerow([
                        'Date', 'Timestamp',
                        # Basic metrics
                        'Total_Tests', 'Passed', 'Failed', 'Skipped', 'Errors',
                        'Pass_Rate_%',
                        # Coverage
                        'Line_Coverage_%', 'Branch_Coverage_%',
                        'Lines_Covered', 'Lines_Total',
                        # Performance
                        'Total_Duration_s', 'Avg_Duration_ms', 'Slowest_ms', 'Fastest_ms',
                        # Distribution
                        'Unit_Tests', 'Integration_Tests', 'API_Tests', 'Database_Tests',
                        # Quality
                        'Test_Code_Ratio', 'Test_Files'
                    ])
                else:
                    print(f"   Appending to existing CSV file...")
                
                # Prepare the row data
                row_data = [
                    self.metrics['date'],
                    self.metrics['timestamp'],
                    self.metrics['total_tests'],
                    self.metrics['passed_tests'],
                    self.metrics['failed_tests'],
                    self.metrics['skipped_tests'],
                    self.metrics['error_tests'],
                    f"{self.metrics['pass_rate']:.2f}",
                    f"{self.metrics['line_coverage']:.2f}",
                    f"{self.metrics['branch_coverage']:.2f}",
                    self.metrics['coverage_lines_covered'],
                    self.metrics['coverage_lines_total'],
                    f"{self.metrics['total_duration']:.2f}",
                    f"{self.metrics['avg_test_duration']*1000:.2f}",
                    f"{self.metrics['slowest_test_duration']*1000:.2f}",
                    f"{self.metrics['fastest_test_duration']*1000:.2f}",
                    self.metrics['unit_tests'],
                    self.metrics['integration_tests'],
                    self.metrics['api_tests'],
                    self.metrics['database_tests'],
                    f"{self.metrics['test_code_ratio']:.2f}",
                    self.metrics['test_files']
                ]
                
                print(f"   Writing row with {len(row_data)} columns...")
                writer.writerow(row_data)
                
                # Explicitly flush to disk
                f.flush()
            
            # Verify file was created
            if summary_file.exists():
                file_size = summary_file.stat().st_size
                print(f"\n✅ Comprehensive metrics saved successfully!")
                print(f"   File: {summary_file}")
                print(f"   Size: {file_size} bytes")
                
                # Show last line of file to confirm
                with open(summary_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"   Last entry: {lines[-1][:80]}...")
            else:
                print(f"\n❌ File was not created!")
                
        except PermissionError as e:
            print(f"\n❌ Permission error writing to {summary_file}: {e}")
            print(f"   Try running as administrator or check folder permissions")
        except Exception as e:
            print(f"\n❌ Error saving comprehensive summary: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_detailed_report(self):
        """Generate detailed test quality report"""
        print(f"\n{'='*60}")
        print("COMPREHENSIVE TEST METRICS REPORT")
        print(f"{'='*60}")
        print(f"Date: {self.date}")
        
        print(f"\n📊 Test Execution:")
        print(f"  Total Tests: {self.metrics['total_tests']}")
        print(f"  ✓ Passed: {self.metrics['passed_tests']} ({self.metrics['pass_rate']:.1f}%)")
        print(f"  ✗ Failed: {self.metrics['failed_tests']}")
        print(f"  ⊘ Skipped: {self.metrics['skipped_tests']}")
        print(f"  ⚠ Errors: {self.metrics['error_tests']}")
        
        print(f"\n📈 Code Coverage:")
        print(f"  Line Coverage: {self.metrics['line_coverage']:.2f}% "
              f"({self.metrics['coverage_lines_covered']}/{self.metrics['coverage_lines_total']})")
        print(f"  Branch Coverage: {self.metrics['branch_coverage']:.2f}%")
        
        print(f"\n⚡ Performance:")
        print(f"  Total Duration: {self.metrics['total_duration']:.2f}s")
        print(f"  Average Test: {self.metrics['avg_test_duration']*1000:.2f}ms")
        print(f"  Slowest Test: {self.metrics['slowest_test_duration']*1000:.2f}ms")
        print(f"  Fastest Test: {self.metrics['fastest_test_duration']*1000:.2f}ms")
        
        print(f"\n🎯 Test Distribution:")
        print(f"  Unit Tests: {self.metrics['unit_tests']}")
        print(f"  Integration Tests: {self.metrics['integration_tests']}")
        print(f"  API Tests: {self.metrics['api_tests']}")
        print(f"  Database Tests: {self.metrics['database_tests']}")
        
        print(f"\n📝 Test Quality:")
        print(f"  Test Files: {self.metrics['test_files']}")
        print(f"  Test/Production Ratio: {self.metrics['test_code_ratio']:.2f}")
        
        # Quality assessment
        print(f"\n💡 Quality Assessment:")
        if self.metrics['pass_rate'] >= 95:
            print(f"  ✓ Excellent pass rate ({self.metrics['pass_rate']:.1f}%)")
        elif self.metrics['pass_rate'] >= 80:
            print(f"  ⚠ Good pass rate ({self.metrics['pass_rate']:.1f}%)")
        else:
            print(f"  ✗ Low pass rate ({self.metrics['pass_rate']:.1f}%) - needs attention")
        
        if self.metrics['line_coverage'] >= 80:
            print(f"  ✓ Good line coverage ({self.metrics['line_coverage']:.1f}%)")
        elif self.metrics['line_coverage'] >= 60:
            print(f"  ⚠ Fair line coverage ({self.metrics['line_coverage']:.1f}%)")
        else:
            print(f"  ✗ Low line coverage ({self.metrics['line_coverage']:.1f}%) - needs improvement")
        
        if self.metrics['test_code_ratio'] >= 1.0:
            print(f"  ✓ Excellent test/code ratio ({self.metrics['test_code_ratio']:.2f})")
        elif self.metrics['test_code_ratio'] >= 0.5:
            print(f"  ⚠ Acceptable test/code ratio ({self.metrics['test_code_ratio']:.2f})")
        else:
            print(f"  ✗ Low test/code ratio ({self.metrics['test_code_ratio']:.2f}) - add more tests")
        
        print(f"{'='*60}\n")

def main():
    """Main execution"""
    collector = ComprehensiveTestMetrics()
    
    print("🧪 Orchestr8r - Comprehensive Test Metrics Collection")
    print("="*60)
    
    # Run comprehensive test suite
    print("\n[1/4] Running test suite...")
    if not collector.run_comprehensive_tests():
        print("⚠️  Test execution completed with issues")
    
    # Parse results
    print("\n[2/4] Parsing test results...")
    collector.parse_junit_detailed()
    collector.parse_coverage_detailed()
    
    print("\n[3/4] Calculating code metrics...")
    collector.calculate_test_code_ratio()
    
    # Save and report
    print("\n[4/4] Saving metrics and generating report...")
    collector.save_comprehensive_summary()  # This should now show debug output
    collector.generate_detailed_report()
    
    print("\n" + "="*60)
    print("✅ Comprehensive metrics collection complete!")
    print(f"📁 View detailed HTML report: {METRICS_DIR / 'pytest_report.html'}")
    print(f"📁 View coverage report: {METRICS_DIR / 'coverage_html' / 'index.html'}")
    print(f"📁 View metrics CSV: {METRICS_DIR / 'comprehensive_test_metrics.csv'}")
    print("="*60)

if __name__ == "__main__":
    main()