#!/usr/bin/env python3
"""
Runtime Metrics Collection for Orchestr8r
Queries Prometheus and saves metrics alongside static analysis data
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

PROMETHEUS_URL = "http://localhost:9090"
METRICS_DIR = Path(__file__).parent / "metrics_data"

def query_prometheus(query):
    """Query Prometheus API"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={'query': query},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()['data']['result']
        return []
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return []

def collect_runtime_metrics():
    """Collect runtime metrics from Prometheus"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    date = datetime.now().strftime("%Y-%m-%d")
    
    metrics = {
        'timestamp': timestamp,
        'date': date,
    }
    
    # Request rate
    result = query_prometheus('sum(rate(http_requests_total[5m]))')
    metrics['request_rate'] = float(result[0]['value'][1]) if result else 0
    
    # Average latency
    result = query_prometheus('avg(http_request_duration_seconds)')
    metrics['avg_latency_ms'] = float(result[0]['value'][1]) * 1000 if result else 0
    
    # Error rate
    result = query_prometheus('sum(rate(http_requests_total{status=~"5.."}[5m]))')
    metrics['error_rate'] = float(result[0]['value'][1]) if result else 0
    
    # Active requests
    result = query_prometheus('sum(http_requests_in_progress)')
    metrics['active_requests'] = int(float(result[0]['value'][1])) if result else 0
    
    # Save to CSV
    runtime_file = METRICS_DIR / "runtime_summary.csv"
    df = pd.DataFrame([metrics])
    
    if runtime_file.exists():
        df.to_csv(runtime_file, mode='a', header=False, index=False)
    else:
        df.to_csv(runtime_file, index=False)
    
    print(f"✓ Runtime metrics collected: {metrics}")
    return metrics

if __name__ == "__main__":
    collect_runtime_metrics()