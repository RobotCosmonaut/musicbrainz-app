#!/usr/bin/env python3
"""
Export AVAILABLE Prometheus metrics (avoiding 'nan' values)
Only collects metrics that actually exist in your deployment
"""

import requests
import csv
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Configuration
PROMETHEUS_URL = "http://localhost:9090"
SCRIPT_DIR = Path(__file__).parent.resolve()
METRICS_DIR = SCRIPT_DIR / "metrics_data"
METRICS_DIR.mkdir(exist_ok=True)

def query_prometheus(query, time=None):
    """Query Prometheus"""
    try:
        params = {'query': query}
        if time:
            params['time'] = time.timestamp()
            
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'success' and data['data']['result']:
            return data['data']['result']
        return []
    except Exception as e:
        return []

def get_metric_value(results):
    """Extract metric value, summing all results"""
    if not results:
        return 0
    
    if len(results) == 1:
        return float(results[0]['value'][1])
    else:
        return sum(float(r['value'][1]) for r in results)

def collect_available_metrics(timestamp):
    """Collect only the metrics that are actually available"""
    
    print(f"  Collecting at {timestamp.strftime('%Y-%m-%d %H:%M')}...")
    
    metrics = {
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
        'date': timestamp.strftime('%Y-%m-%d'),
    }
    
    # Request rate (AVAILABLE)
    results = query_prometheus('rate(http_requests_total[1m])', timestamp)
    metrics['request_rate_per_sec'] = get_metric_value(results)
    
    # Check if duration metrics exist
    duration_sum = query_prometheus('http_request_duration_seconds_sum', timestamp)
    duration_count = query_prometheus('http_request_duration_seconds_count', timestamp)
    
    if duration_sum and duration_count:
        # Duration metrics exist! Calculate avg latency
        sum_val = get_metric_value(query_prometheus('rate(http_request_duration_seconds_sum[1m])', timestamp))
        count_val = get_metric_value(query_prometheus('rate(http_request_duration_seconds_count[1m])', timestamp))
        
        if count_val > 0:
            metrics['avg_latency_ms'] = (sum_val / count_val) * 1000
        else:
            metrics['avg_latency_ms'] = 0
        
        # Try percentiles
        for percentile in [50, 95, 99]:
            query = f'histogram_quantile({percentile/100}, rate(http_request_duration_seconds_bucket[1m]))'
            results = query_prometheus(query, timestamp)
            value = get_metric_value(results)
            metrics[f'p{percentile}_latency_ms'] = value * 1000 if value else 0
    else:
        # Duration metrics DON'T exist - set to None
        metrics['avg_latency_ms'] = None
        metrics['p50_latency_ms'] = None
        metrics['p95_latency_ms'] = None
        metrics['p99_latency_ms'] = None
    
    # Error rate (AVAILABLE)
    results = query_prometheus('rate(http_requests_total{status=~"5.."}[1m])', timestamp)
    metrics['error_rate_per_sec'] = get_metric_value(results)
    
    # Error percentage
    if metrics['request_rate_per_sec'] > 0:
        metrics['error_percentage'] = (metrics['error_rate_per_sec'] / metrics['request_rate_per_sec']) * 100
    else:
        metrics['error_percentage'] = 0
    
    # Active requests (may or may not exist)
    results = query_prometheus('http_requests_in_progress', timestamp)
    if results:
        metrics['active_requests'] = int(get_metric_value(results))
    else:
        metrics['active_requests'] = 0
    
    # Total requests (AVAILABLE)
    results = query_prometheus('http_requests_total', timestamp)
    metrics['total_requests'] = int(get_metric_value(results))
    
    # Per-service rates (AVAILABLE)
    services = ['artist-service', 'album-service', 'recommendation-service', 'api-gateway']
    for service in services:
        results = query_prometheus(f'rate(http_requests_total{{service="{service}"}}[1m])', timestamp)
        column_name = f"{service.replace('-', '_')}_requests"
        metrics[column_name] = get_metric_value(results)
    
    return metrics

def export_metrics(hours=24, interval_minutes=1):
    """Export available metrics"""
    
    print("="*70)
    print("Export Available Prometheus Metrics (No 'nan' values)")
    print("="*70)
    print()
    
    # Test connectivity
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=5)
        if response.status_code != 200:
            print(f"⚠ Prometheus returned status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot reach Prometheus: {e}")
        print("   Run: kubectl port-forward svc/prometheus-service 9090:9090")
        return
    
    print("✓ Prometheus is reachable")
    
    # Check what metrics are available
    print("\nChecking available metrics...")
    
    has_duration = bool(query_prometheus('http_request_duration_seconds_sum'))
    has_histogram = bool(query_prometheus('http_request_duration_seconds_bucket'))
    
    if has_duration and has_histogram:
        print("✅ Duration metrics AVAILABLE - will include latency data")
    else:
        print("⚠️  Duration metrics NOT AVAILABLE - latency columns will be empty")
        print("   (This is why you're seeing 'nan' values)")
    
    print()
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    print(f"Time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Interval: {interval_minutes} minute(s)\n")
    
    # Generate timestamps
    timestamps = []
    current = start_time
    while current <= end_time:
        timestamps.append(current)
        current += timedelta(minutes=interval_minutes)
    
    print(f"Collecting {len(timestamps)} data points...\n")
    
    # Collect metrics
    all_metrics = []
    for i, ts in enumerate(timestamps, 1):
        try:
            metrics = collect_available_metrics(ts)
            all_metrics.append(metrics)
            
            if i % 60 == 0:
                print(f"  Progress: {i}/{len(timestamps)} ({i*100//len(timestamps)}%)")
        except Exception as e:
            print(f"  Error at {ts}: {e}")
            continue
    
    if not all_metrics:
        print("\n⚠ No metrics collected!")
        return
    
    # Write to CSV
    output_file = METRICS_DIR / f"runtime_available_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    fieldnames = [
        'timestamp',
        'date',
        'request_rate_per_sec',
        'avg_latency_ms',
        'p50_latency_ms',
        'p95_latency_ms',
        'p99_latency_ms',
        'error_rate_per_sec',
        'error_percentage',
        'active_requests',
        'total_requests',
        'artist_service_requests',
        'album_service_requests',
        'recommendation_service_requests',
        'api_gateway_requests'
    ]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_metrics)
    
    print(f"\n{'='*70}")
    print(f"✓ Exported {len(all_metrics)} data points")
    print(f"✓ Output: {output_file}")
    print(f"{'='*70}\n")
    
    # Summary
    if all_metrics:
        print("Collected Metrics:")
        print(f"  ✅ Request rate: {sum(m['request_rate_per_sec'] for m in all_metrics)/len(all_metrics):.2f} avg req/sec")
        print(f"  ✅ Total requests: {all_metrics[-1]['total_requests']}")
        print(f"  ✅ Error rate: {sum(m['error_rate_per_sec'] for m in all_metrics):.4f} total errors/sec")
        
        if all_metrics[0]['avg_latency_ms'] is not None:
            print(f"  ✅ Latency data: Available")
        else:
            print(f"  ⚠️  Latency data: Not available (columns will be empty)")
            print(f"\n📝 To get latency data, you need to:")
            print(f"     1. Add Histogram instrumentation to your services")
            print(f"     2. Rebuild and redeploy")
            print(f"     3. Run: python diagnose_prometheus_metrics.py")
    
    print()

def main():
    parser = argparse.ArgumentParser(
        description='Export available Prometheus metrics (avoiding nan values)'
    )
    parser.add_argument('--hours', type=int, default=24, help='Hours of history (default: 24)')
    parser.add_argument('--interval', type=int, default=1, help='Minutes between points (default: 1)')
    
    args = parser.parse_args()
    export_metrics(hours=args.hours, interval_minutes=args.interval)

if __name__ == "__main__":
    main()
