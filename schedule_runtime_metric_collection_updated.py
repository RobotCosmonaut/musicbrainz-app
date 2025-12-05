#!/usr/bin/env python3
"""
Schedule periodic collection of runtime metrics from Prometheus
Runs continuously and collects metrics at regular intervals
"""

import time
import requests
from datetime import datetime
from pathlib import Path
import csv
import os

# Configuration - FIXED FOR WINDOWS
PROMETHEUS_URL = "http://localhost:9090"  # Updated for port-forward
COLLECTION_INTERVAL = 60  # seconds between collections

# Use relative path that works on both Windows and Linux
SCRIPT_DIR = Path(__file__).parent.resolve()
METRICS_DIR = SCRIPT_DIR / "metrics_data"

# Create metrics directory if it doesn't exist
METRICS_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = METRICS_DIR / "runtime_summary.csv"

# Metrics to collect
METRICS_QUERIES = {
    'request_rate': 'rate(http_requests_total[1m])',
    'avg_response_time': 'rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m])',
    'error_rate': 'rate(http_requests_total{status=~"5.."}[1m])',
    'cpu_usage': 'rate(process_cpu_seconds_total[1m])',
    'memory_usage': 'process_resident_memory_bytes',
}

def query_prometheus(query):
    """Query Prometheus and return the result"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={'query': query},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'success' and data['data']['result']:
            # Return the first result value
            return float(data['data']['result'][0]['value'][1])
        return 0.0
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return 0.0

def collect_metrics():
    """Collect all metrics and return as a dictionary"""
    timestamp = datetime.now()
    
    metrics = {
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    print(f"\n[{timestamp.strftime('%H:%M:%S')}] Collecting metrics...")
    
    for metric_name, query in METRICS_QUERIES.items():
        value = query_prometheus(query)
        metrics[metric_name] = value
        print(f"  {metric_name}: {value:.4f}")
    
    return metrics

def write_metrics(metrics):
    """Write metrics to CSV file"""
    file_exists = OUTPUT_FILE.exists()
    
    try:
        with open(OUTPUT_FILE, 'a', newline='') as f:
            fieldnames = ['timestamp'] + list(METRICS_QUERIES.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header if file doesn't exist
            if not file_exists:
                writer.writeheader()
                print(f"\n✓ Created new metrics file: {OUTPUT_FILE}")
            
            writer.writerow(metrics)
            print(f"✓ Appended metrics to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error writing metrics: {e}")

def main():
    """Main collection loop"""
    print("="*70)
    print("Orchestr8r - Scheduled Metrics Collection")
    print("="*70)
    print(f"\nPrometheus URL: {PROMETHEUS_URL}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Collection interval: {COLLECTION_INTERVAL} seconds")
    print(f"\nPress Ctrl+C to stop...\n")
    
    # Test Prometheus connectivity
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=5)
        if response.status_code == 200:
            print("✓ Prometheus is reachable\n")
        else:
            print(f"⚠ Prometheus returned status {response.status_code}")
    except Exception as e:
        print(f"⚠ Warning: Could not reach Prometheus: {e}")
        print("  Make sure port-forward is running:")
        print("  kubectl port-forward svc/prometheus-service 9090:9090\n")
    
    collection_count = 0
    
    try:
        while True:
            collection_count += 1
            print(f"\n{'='*70}")
            print(f"Collection #{collection_count}")
            print('='*70)
            
            # Collect and write metrics
            metrics = collect_metrics()
            write_metrics(metrics)
            
            # Wait for next collection
            print(f"\nSleeping for {COLLECTION_INTERVAL} seconds...")
            time.sleep(COLLECTION_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"✓ Stopped after {collection_count} collections")
        print(f"✓ Data saved to: {OUTPUT_FILE}")
        print('='*70)

if __name__ == "__main__":
    main()