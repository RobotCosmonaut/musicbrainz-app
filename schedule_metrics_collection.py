#!/usr/bin/env python3
"""
Scheduled Runtime Metrics Collection
Runs continuously in the background, collecting metrics at specified interval
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "60"))  # seconds
METRICS_DIR = Path(os.getenv("METRICS_DIR", "/app/metrics_data"))
METRICS_DIR.mkdir(exist_ok=True)

def query_prometheus(query):
    """Query Prometheus API"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={'query': query},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()['data']['result']
            return float(result[0]['value'][1]) if result else 0
        return 0
    except Exception as e:
        logger.error(f"Error querying Prometheus: {e}")
        return 0

def collect_runtime_metrics():
    """Collect runtime metrics from Prometheus"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date = datetime.now().strftime("%Y-%m-%d")
    
    metrics = {
        'timestamp': timestamp,
        'date': date,
        # CHANGED: Use 5m window instead of 1m for smoother rate calculation
        'request_rate_per_sec': query_prometheus('sum(rate(http_requests_total[5m]))'),
        'avg_latency_ms': query_prometheus('avg(http_request_duration_seconds)') * 1000,
        'p50_latency_ms': query_prometheus('histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))') * 1000,
        'p95_latency_ms': query_prometheus('histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))') * 1000,
        'p99_latency_ms': query_prometheus('histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))') * 1000,
        'error_rate_per_sec': query_prometheus('sum(rate(http_requests_total{status=~"5.."}[5m]))'),  # CHANGED
        'error_percentage': query_prometheus('(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100'),  # CHANGED
        'active_requests': int(query_prometheus('sum(http_requests_in_progress)')),
        'total_requests': int(query_prometheus('sum(http_requests_total)')),
        
        # Per-service metrics - also use 5m window
        'artist_service_requests': query_prometheus('sum(rate(http_requests_total{job="artist-service"}[5m]))'),
        'album_service_requests': query_prometheus('sum(rate(http_requests_total{job="album-service"}[5m]))'),
        'recommendation_service_requests': query_prometheus('sum(rate(http_requests_total{job="recommendation-service"}[5m]))'),
        'api_gateway_requests': query_prometheus('sum(rate(http_requests_total{job="api-gateway"}[5m]))'),
    }
    
    # Save to CSV
    runtime_file = METRICS_DIR / "runtime_summary.csv"
    df = pd.DataFrame([metrics])
    
    if runtime_file.exists():
        df.to_csv(runtime_file, mode='a', header=False, index=False)
    else:
        df.to_csv(runtime_file, index=False)
    
    logger.info(
        f"✓ Collected: {metrics['request_rate_per_sec']:.2f} req/s | "
        f"{metrics['avg_latency_ms']:.2f}ms latency | "
        f"{metrics['error_rate_per_sec']:.4f} errors/s | "
        f"{metrics['total_requests']} total requests"
    )
    
    return metrics

def main():
    """Run continuous metrics collection"""
    logger.info("="*70)
    logger.info("Orchestr8r Runtime Metrics Collector")
    logger.info("="*70)
    logger.info(f"Prometheus URL: {PROMETHEUS_URL}")
    logger.info(f"Collection interval: {COLLECTION_INTERVAL}s")
    logger.info(f"Metrics directory: {METRICS_DIR}")
    logger.info(f"Output file: {METRICS_DIR / 'runtime_summary.csv'}")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*70 + "\n")
    
    collection_count = 0
    
    while True:
        try:
            collect_runtime_metrics()
            collection_count += 1
            
            if collection_count % 60 == 0:  # Every hour
                logger.info(f"📊 Collected {collection_count} metric snapshots so far...")
            
            time.sleep(COLLECTION_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("\n" + "="*70)
            logger.info("✓ Metrics collection stopped")
            logger.info(f"✓ Total collections: {collection_count}")
            logger.info(f"✓ Data saved to: {METRICS_DIR / 'runtime_summary.csv'}")
            logger.info("="*70)
            break
        except Exception as e:
            logger.error(f"Error in collection loop: {e}")
            time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
    main()