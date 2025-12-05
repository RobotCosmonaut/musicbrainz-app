#!/usr/bin/env python3
"""
Diagnose Prometheus metrics availability
Identifies what metrics exist and what's missing
"""

import requests
import json

PROMETHEUS_URL = "http://localhost:9090"

def check_prometheus_health():
    """Check if Prometheus is reachable"""
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Cannot reach Prometheus: {e}")
        print("   Make sure port-forward is running:")
        print("   kubectl port-forward svc/prometheus-service 9090:9090\n")
        return False

def get_all_metric_names():
    """Get all metric names from Prometheus"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/label/__name__/values",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'success':
            return sorted(data['data'])
        return []
    except Exception as e:
        print(f"Error getting metrics: {e}")
        return []

def query_metric_sample(metric_name):
    """Get a sample of a metric"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={'query': metric_name},
            timeout=5
        )
        data = response.json()
        
        if data['status'] == 'success' and data['data']['result']:
            return data['data']['result'][0]
        return None
    except:
        return None

def diagnose_metrics():
    """Diagnose what metrics are available and what's missing"""
    
    print("="*70)
    print("Prometheus Metrics Diagnostic")
    print("="*70)
    print()
    
    # Check connectivity
    if not check_prometheus_health():
        return
    
    print("✓ Prometheus is reachable\n")
    
    # Get all metrics
    print("Fetching all metric names...")
    all_metrics = get_all_metric_names()
    
    if not all_metrics:
        print("❌ No metrics found!")
        return
    
    print(f"✓ Found {len(all_metrics)} total metrics\n")
    
    # Categorize metrics
    print("="*70)
    print("METRIC AVAILABILITY CHECK")
    print("="*70)
    print()
    
    # Critical metrics for runtime_summary.csv
    required_metrics = {
        'http_requests_total': 'Request counter (for request rate)',
        'http_request_duration_seconds_sum': 'Duration sum (for avg latency)',
        'http_request_duration_seconds_count': 'Duration count (for avg latency)',
        'http_request_duration_seconds_bucket': 'Duration histogram (for percentiles)',
        'http_requests_in_progress': 'Active requests gauge',
    }
    
    print("REQUIRED METRICS FOR LATENCY TRACKING:")
    print("-" * 70)
    
    missing_metrics = []
    
    for metric, description in required_metrics.items():
        if any(m.startswith(metric) for m in all_metrics):
            print(f"✅ {metric:45s} - {description}")
            
            # Get a sample
            sample = query_metric_sample(metric)
            if sample:
                labels = sample.get('metric', {})
                value = sample.get('value', ['', ''])[1]
                print(f"   Sample: {labels} = {value}")
        else:
            print(f"❌ {metric:45s} - {description}")
            missing_metrics.append(metric)
    
    print()
    
    # Show HTTP-related metrics
    http_metrics = [m for m in all_metrics if 'http' in m.lower()]
    if http_metrics:
        print("="*70)
        print(f"ALL HTTP-RELATED METRICS ({len(http_metrics)} found):")
        print("-" * 70)
        for metric in http_metrics:
            print(f"  • {metric}")
        print()
    
    # Diagnosis
    print("="*70)
    print("DIAGNOSIS")
    print("="*70)
    print()
    
    if not missing_metrics:
        print("✅ All required metrics are available!")
        print()
        print("If you're still seeing 'nan' values, the issue might be:")
        print("  1. No traffic has been generated yet")
        print("  2. Histogram buckets are configured incorrectly")
        print("  3. PromQL queries in the export script are wrong")
        print()
        print("Try generating some traffic:")
        print("  python generate_traffic.py")
        
    else:
        print("❌ MISSING METRICS DETECTED!")
        print()
        print("Your services are NOT instrumenting request durations.")
        print("This is why you're seeing 'nan' for all latency metrics.")
        print()
        print("Missing metrics:")
        for metric in missing_metrics:
            print(f"  • {metric}")
        print()
        print("="*70)
        print("HOW TO FIX")
        print("="*70)
        print()
        print("You need to add Histogram instrumentation to your services.")
        print()
        print("In each service (artist-service, album-service, etc.), add:")
        print()
        print("```python")
        print("from prometheus_client import Histogram")
        print()
        print("# Add this histogram")
        print("http_request_duration_seconds = Histogram(")
        print("    'http_request_duration_seconds',")
        print("    'HTTP request duration in seconds',")
        print("    ['method', 'endpoint', 'service'],")
        print("    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)")
        print(")")
        print()
        print("# Then in your request handler, measure time:")
        print("import time")
        print()
        print("@app.route('/api/artists/search')")
        print("def search_artists():")
        print("    start_time = time.time()")
        print("    try:")
        print("        # Your handler code")
        print("        result = do_search()")
        print("        return result")
        print("    finally:")
        print("        duration = time.time() - start_time")
        print("        http_request_duration_seconds.labels(")
        print("            method='GET',")
        print("            endpoint='/api/artists/search',")
        print("            service='artist-service'")
        print("        ).observe(duration)")
        print("```")
        print()
        print("After updating your services:")
        print("  1. Rebuild Docker images: docker-compose build")
        print("  2. Redeploy to Kubernetes: kubectl apply -f k8s.yaml")
        print("  3. Wait 1-2 minutes for metrics to appear")
        print("  4. Run this diagnostic again")
    
    print()
    print("="*70)
    print("WORKAROUND FOR NOW")
    print("="*70)
    print()
    print("Until you fix the instrumentation, you can still collect:")
    print("  • Request rate (requests/sec) ✅")
    print("  • Total requests ✅")
    print("  • Error rate ✅")
    print("  • Per-service request counts ✅")
    print()
    print("But you CANNOT collect:")
    print("  • Average latency ❌")
    print("  • Percentile latencies (p50, p95, p99) ❌")
    print()
    print("For your research paper, you'll need to add the histogram")
    print("instrumentation to get complete quality metrics.")
    print()

if __name__ == "__main__":
    diagnose_metrics()
