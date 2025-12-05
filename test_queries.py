#!/usr/bin/env python3
"""
Quick test to verify PromQL queries return data
Tests the queries before running a full export
"""

import requests

PROMETHEUS_URL = "http://localhost:9090"

def test_query(query, description):
    """Test a single PromQL query"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={'query': query},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'success':
            results = data['data']['result']
            if results:
                # Get value from first result
                value = float(results[0]['value'][1]) if results[0].get('value') else 0
                labels = results[0].get('metric', {})
                
                print(f"✅ {description}")
                print(f"   Query: {query}")
                print(f"   Value: {value}")
                print(f"   Labels: {labels}")
                print(f"   Total results: {len(results)}")
                print()
                return True
            else:
                print(f"⚠️  {description}")
                print(f"   Query: {query}")
                print(f"   Result: EMPTY (no data)")
                print()
                return False
        else:
            print(f"❌ {description}")
            print(f"   Query: {query}")
            print(f"   Error: {data.get('error', 'Unknown error')}")
            print()
            return False
            
    except Exception as e:
        print(f"❌ {description}")
        print(f"   Query: {query}")
        print(f"   Error: {e}")
        print()
        return False

def main():
    print("="*70)
    print("Test PromQL Queries")
    print("="*70)
    print()
    
    # Test connectivity
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy", timeout=5)
        if response.status_code == 200:
            print("✓ Prometheus is reachable\n")
        else:
            print(f"❌ Prometheus status: {response.status_code}\n")
            return
    except Exception as e:
        print(f"❌ Cannot reach Prometheus: {e}\n")
        return
    
    print("Testing queries...\n")
    
    # Test queries
    queries = [
        ('sum(rate(http_requests_total[1m]))', 'Request rate (req/sec)'),
        ('sum(rate(http_request_duration_seconds_sum[1m]))', 'Duration sum rate'),
        ('sum(rate(http_request_duration_seconds_count[1m]))', 'Duration count rate'),
        ('histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))', 'P95 latency'),
        ('histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))', 'P50 latency'),
        ('sum(http_requests_total)', 'Total requests (cumulative)'),
        ('sum(rate(http_requests_total{status=~"5.."}[1m]))', 'Error rate'),
        ('sum(rate(http_requests_total{job="artist-service"}[1m]))', 'Artist service rate'),
        ('sum(rate(http_requests_total{job="album-service"}[1m]))', 'Album service rate'),
        ('sum(rate(http_requests_total{job="recommendation-service"}[1m]))', 'Recommendation service rate'),
        ('sum(rate(http_requests_total{job="api-gateway"}[1m]))', 'API Gateway rate'),
    ]
    
    passed = 0
    failed = 0
    empty = 0
    
    for query, description in queries:
        result = test_query(query, description)
        if result:
            passed += 1
        else:
            # Check if it's empty vs error
            try:
                response = requests.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params={'query': query},
                    timeout=10
                )
                data = response.json()
                if data['status'] == 'success' and not data['data']['result']:
                    empty += 1
                else:
                    failed += 1
            except:
                failed += 1
    
    print("="*70)
    print("Summary")
    print("="*70)
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Empty: {empty} (query works but no data)")
    print(f"❌ Failed: {failed}")
    print()
    
    if empty > 0:
        print("⚠️  Some queries returned no data.")
        print("   This is normal if:")
        print("   1. No traffic has been generated yet")
        print("   2. Services just started")
        print()
        print("   To generate traffic:")
        print("   • Port-forward API Gateway: kubectl port-forward svc/api-gateway-service 8000:8000")
        print("   • Run: python generate_traffic.py")
        print()
    
    if failed > 0:
        print("❌ Some queries failed!")
        print("   Check Prometheus logs:")
        print("   kubectl logs -l app=prometheus")
        print()
    
    if passed > 8:
        print("✅ Queries look good! Ready to export metrics:")
        print("   python export_runtime_summary_fixed.py --hours 2")
        print()

if __name__ == "__main__":
    main()
