#!/usr/bin/env python3
"""
Export Prometheus metrics to runtime_summary.csv format
Matches the exact schema from the original runtime_summary.csv
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

def query_prometheus_range(query, start_time, end_time, step='1m'):
    """Query Prometheus for a time range"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                'query': query,
                'start': start_time.timestamp(),
                'end': end_time.timestamp(),
                'step': step
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'success':
            return data['data']['result']
        return []
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return []

def query_prometheus_instant(query, time=None):
    """Query Prometheus at a specific time"""
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
        print(f"Error querying: {e}")
        return []

def get_metric_value(results, service=None):
    """Extract metric value from Prometheus results"""
    if not results:
        return 0
    
    if service:
        # Filter by service label
        for result in results:
            if result.get('metric', {}).get('service') == service:
                return float(result['value'][1])
        return 0
    else:
        # Return first result or sum all
        if len(results) == 1:
            return float(results[0]['value'][1])
        else:
            # Sum all results
            return sum(float(r['value'][1]) for r in results)

def calculate_percentile(query_template, percentile, time):
    """Calculate latency percentile"""
    query = query_template.replace('PERCENTILE', str(percentile/100))
    results = query_prometheus_instant(query, time)
    value = get_metric_value(results)
    return value * 1000 if value else 0  # Convert to ms

def collect_metrics_at_time(timestamp):
    """Collect all metrics at a specific timestamp"""
    
    print(f"  Collecting metrics for {timestamp.strftime('%Y-%m-%d %H:%M')}...")
    
    metrics = {
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
        'date': timestamp.strftime('%Y-%m-%d'),
    }
    
    # Request rate per second (1-minute rate)
    query = 'rate(http_requests_total[1m])'
    results = query_prometheus_instant(query, timestamp)
    metrics['request_rate_per_sec'] = get_metric_value(results)
    
    # Average latency in milliseconds
    query = 'rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m])'
    results = query_prometheus_instant(query, timestamp)
    avg_latency = get_metric_value(results)
    metrics['avg_latency_ms'] = avg_latency * 1000 if avg_latency else 0
    
    # Percentile latencies (p50, p95, p99)
    percentile_query = 'histogram_quantile(PERCENTILE, rate(http_request_duration_seconds_bucket[1m]))'
    metrics['p50_latency_ms'] = calculate_percentile(percentile_query, 50, timestamp)
    metrics['p95_latency_ms'] = calculate_percentile(percentile_query, 95, timestamp)
    metrics['p99_latency_ms'] = calculate_percentile(percentile_query, 99, timestamp)
    
    # Error rate per second
    query = 'rate(http_requests_total{status=~"5.."}[1m])'
    results = query_prometheus_instant(query, timestamp)
    metrics['error_rate_per_sec'] = get_metric_value(results)
    
    # Error percentage
    if metrics['request_rate_per_sec'] > 0:
        metrics['error_percentage'] = (metrics['error_rate_per_sec'] / metrics['request_rate_per_sec']) * 100
    else:
        metrics['error_percentage'] = 0
    
    # Active requests
    query = 'http_requests_in_progress'
    results = query_prometheus_instant(query, timestamp)
    metrics['active_requests'] = int(get_metric_value(results))
    
    # Total requests (cumulative)
    query = 'http_requests_total'
    results = query_prometheus_instant(query, timestamp)
    metrics['total_requests'] = int(get_metric_value(results))
    
    # Per-service request rates
    services = ['artist-service', 'album-service', 'recommendation-service', 'api-gateway']
    for service in services:
        query = f'rate(http_requests_total{{service="{service}"}}[1m])'
        results = query_prometheus_instant(query, timestamp)
        column_name = f"{service.replace('-', '_')}_requests"
        metrics[column_name] = get_metric_value(results)
    
    return metrics

def export_historical_metrics(hours=24, interval_minutes=1):
    """Export historical metrics for the specified time range"""
    
    print("="*70)
    print("Exporting Historical Prometheus Metrics to runtime_summary.csv")
    print("="*70)
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    print(f"\nTime range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Interval: {interval_minutes} minute(s)")
    print(f"Prometheus: {PROMETHEUS_URL}\n")
    
    # Test connectivity
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=5)
        if response.status_code != 200:
            print(f"⚠ Warning: Prometheus returned status {response.status_code}")
    except Exception as e:
        print(f"⚠ Warning: Cannot reach Prometheus: {e}")
        print("  Make sure port-forward is running:")
        print("  kubectl port-forward svc/prometheus-service 9090:9090\n")
        return
    
    print("✓ Prometheus is reachable\n")
    
    # Generate timestamps
    timestamps = []
    current = start_time
    while current <= end_time:
        timestamps.append(current)
        current += timedelta(minutes=interval_minutes)
    
    print(f"Collecting {len(timestamps)} data points...\n")
    
    # Collect metrics for each timestamp
    all_metrics = []
    for i, ts in enumerate(timestamps, 1):
        try:
            metrics = collect_metrics_at_time(ts)
            all_metrics.append(metrics)
            
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(timestamps)} ({i*100//len(timestamps)}%)")
        except Exception as e:
            print(f"  Error at {ts}: {e}")
            continue
    
    # Write to CSV
    if not all_metrics:
        print("\n⚠ No metrics collected!")
        return
    
    output_file = METRICS_DIR / f"runtime_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # CSV columns in exact order from the original file
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
    print(f"✓ Successfully exported {len(all_metrics)} data points")
    print(f"✓ Output file: {output_file}")
    print(f"{'='*70}\n")
    
    # Show summary statistics
    if all_metrics:
        print("Summary Statistics:")
        print(f"  Time range: {all_metrics[0]['timestamp']} to {all_metrics[-1]['timestamp']}")
        
        avg_request_rate = sum(m['request_rate_per_sec'] for m in all_metrics) / len(all_metrics)
        print(f"  Avg request rate: {avg_request_rate:.2f} req/sec")
        
        avg_latency = sum(m['avg_latency_ms'] for m in all_metrics) / len(all_metrics)
        print(f"  Avg latency: {avg_latency:.2f} ms")
        
        total_errors = sum(m['error_rate_per_sec'] for m in all_metrics)
        print(f"  Total error rate: {total_errors:.2f} errors/sec")
        
        print(f"\n✓ Ready for analysis in your research paper!")

def main():
    parser = argparse.ArgumentParser(
        description='Export Prometheus metrics to runtime_summary.csv format'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Number of hours of historical data to export (default: 24)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=1,
        help='Interval in minutes between data points (default: 1)'
    )
    
    args = parser.parse_args()
    
    export_historical_metrics(hours=args.hours, interval_minutes=args.interval)

if __name__ == "__main__":
    main()
