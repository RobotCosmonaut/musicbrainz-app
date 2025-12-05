#!/usr/bin/env python3
"""
Export Prometheus metrics with CORRECT label names
Matches the actual metric structure from your services
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
    """Query Prometheus at a specific time or now"""
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
        print(f"  Query error: {e}")
        return []

def get_metric_value(results):
    """Extract and sum metric values"""
    if not results:
        return 0
    
    try:
        if len(results) == 1:
            return float(results[0]['value'][1])
        else:
            # Sum all results
            return sum(float(r['value'][1]) for r in results if r.get('value'))
    except (ValueError, TypeError, KeyError):
        return 0

def collect_metrics_at_time(timestamp):
    """Collect metrics with correct label names"""
    
    print(f"  [{timestamp.strftime('%H:%M')}]", end=" ", flush=True)
    
    metrics = {
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
        'date': timestamp.strftime('%Y-%m-%d'),
    }
    
    # Request rate per second (sum across all services/handlers)
    query = 'sum(rate(http_requests_total[1m]))'
    results = query_prometheus(query, timestamp)
    metrics['request_rate_per_sec'] = get_metric_value(results)
    
    # Average latency in milliseconds
    # Calculate: sum(rate(duration_sum)) / sum(rate(duration_count))
    query_sum = 'sum(rate(http_request_duration_seconds_sum[1m]))'
    query_count = 'sum(rate(http_request_duration_seconds_count[1m]))'
    
    sum_results = query_prometheus(query_sum, timestamp)
    count_results = query_prometheus(query_count, timestamp)
    
    sum_val = get_metric_value(sum_results)
    count_val = get_metric_value(count_results)
    
    if count_val > 0:
        metrics['avg_latency_ms'] = (sum_val / count_val) * 1000
    else:
        metrics['avg_latency_ms'] = 0
    
    print(f"rate={metrics['request_rate_per_sec']:.2f} ", end="", flush=True)
    print(f"latency={metrics['avg_latency_ms']:.2f}ms ", end="", flush=True)
    
    # Percentile latencies (p50, p95, p99)
    # Using histogram_quantile across all buckets
    for percentile in [50, 95, 99]:
        quantile = percentile / 100
        query = f'histogram_quantile({quantile}, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))'
        results = query_prometheus(query, timestamp)
        value = get_metric_value(results)
        metrics[f'p{percentile}_latency_ms'] = value * 1000 if value > 0 else 0
    
    print(f"p95={metrics['p95_latency_ms']:.1f}ms ", end="", flush=True)
    
    # Error rate per second (status 5xx)
    query = 'sum(rate(http_requests_total{status=~"5.."}[1m]))'
    results = query_prometheus(query, timestamp)
    metrics['error_rate_per_sec'] = get_metric_value(results)
    
    # Error percentage
    if metrics['request_rate_per_sec'] > 0:
        metrics['error_percentage'] = (metrics['error_rate_per_sec'] / metrics['request_rate_per_sec']) * 100
    else:
        metrics['error_percentage'] = 0
    
    # Active requests (metric doesn't exist, set to 0)
    metrics['active_requests'] = 0
    
    # Total requests (cumulative, not rate)
    query = 'sum(http_requests_total)'
    results = query_prometheus(query, timestamp)
    metrics['total_requests'] = int(get_metric_value(results))
    
    # Per-service request rates using 'job' label
    # Your services use job names like: artist-service, album-service, etc.
    services = {
        'artist-service': 'artist_service_requests',
        'album-service': 'album_service_requests',
        'recommendation-service': 'recommendation_service_requests',
        'api-gateway': 'api_gateway_requests'
    }
    
    for service_name, column_name in services.items():
        query = f'sum(rate(http_requests_total{{job="{service_name}"}}[1m]))'
        results = query_prometheus(query, timestamp)
        metrics[column_name] = get_metric_value(results)
    
    print("✓")
    
    return metrics

def export_metrics(hours=24, interval_minutes=1):
    """Export historical metrics"""
    
    print("="*70)
    print("Export Prometheus Metrics (FIXED Label Names)")
    print("="*70)
    print()
    
    # Test connectivity
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=5)
        if response.status_code != 200:
            print(f"❌ Prometheus returned status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot reach Prometheus: {e}")
        print("   Make sure port-forward is running:")
        print("   kubectl port-forward svc/prometheus-service 9090:9090\n")
        return
    
    print("✓ Prometheus is reachable\n")
    
    # Verify metrics exist
    print("Verifying metrics availability...")
    test_query = query_prometheus('http_request_duration_seconds_bucket')
    if test_query:
        print("✅ Duration histogram available")
        sample_labels = test_query[0].get('metric', {})
        print(f"   Sample labels: {list(sample_labels.keys())}")
    else:
        print("⚠️  Warning: Duration histogram might be empty")
    
    print()
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    print(f"Time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Interval: {interval_minutes} minute(s)")
    print()
    
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
            metrics = collect_metrics_at_time(ts)
            all_metrics.append(metrics)
            
        except Exception as e:
            print(f"\n  Error at {ts}: {e}")
            continue
    
    if not all_metrics:
        print("\n❌ No metrics collected!")
        return
    
    # Write to CSV
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = METRICS_DIR / f"runtime_summary_{timestamp_str}.csv"
    
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
    print(f"✅ Successfully exported {len(all_metrics)} data points")
    print(f"✅ Output file: {output_file}")
    print(f"{'='*70}\n")
    
    # Show summary
    if all_metrics:
        print("Summary Statistics:")
        print(f"  Time span: {all_metrics[0]['timestamp']} to {all_metrics[-1]['timestamp']}")
        
        # Calculate averages
        avg_rate = sum(m['request_rate_per_sec'] for m in all_metrics) / len(all_metrics)
        avg_latency = sum(m['avg_latency_ms'] for m in all_metrics) / len(all_metrics)
        avg_p95 = sum(m['p95_latency_ms'] for m in all_metrics) / len(all_metrics)
        total_errors = sum(m['error_rate_per_sec'] for m in all_metrics)
        
        print(f"  Average request rate: {avg_rate:.2f} req/sec")
        print(f"  Average latency: {avg_latency:.2f} ms")
        print(f"  Average P95 latency: {avg_p95:.2f} ms")
        print(f"  Total error rate: {total_errors:.4f} errors/sec")
        
        # Check for data quality
        non_zero_latencies = sum(1 for m in all_metrics if m['avg_latency_ms'] > 0)
        print(f"\n  Data quality: {non_zero_latencies}/{len(all_metrics)} periods with latency data")
        
        if non_zero_latencies == 0:
            print("\n  ⚠️  WARNING: All latency values are 0!")
            print("     This might mean:")
            print("     1. No traffic during this time period")
            print("     2. Need to generate traffic: python generate_traffic.py")
        elif non_zero_latencies < len(all_metrics) * 0.1:
            print("\n  ⚠️  WARNING: Very little latency data!")
            print("     Consider generating more traffic during collection")
        else:
            print("\n  ✅ Good data quality - ready for analysis!")
        
        print(f"\n📊 Open in Excel or analyze with pandas!")
        print(f"   import pandas as pd")
        print(f"   df = pd.read_csv('{output_file}')")
        print(f"   df.describe()")
    
    print()

def main():
    parser = argparse.ArgumentParser(
        description='Export Prometheus metrics with correct label names'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Number of hours of historical data (default: 24)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=1,
        help='Interval in minutes between data points (default: 1)'
    )
    
    args = parser.parse_args()
    
    export_metrics(hours=args.hours, interval_minutes=args.interval)

if __name__ == "__main__":
    main()
