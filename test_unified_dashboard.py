#!/usr/bin/env python3
"""
Test script for unified dashboard APIs.
Tests all endpoints used by the unified dashboard.
"""
import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# Test payloads matching unified_dashboard.js
MEDIA_PAYLOAD = {
    "location": "Colombia",
    "topic": "Seguridad",
    "candidate_name": "Candidato Demo",
    "politician": "candidato",
    "max_tweets": 15,
    "time_window_days": 30,
    "language": "es"
}

FORECAST_PAYLOAD = {
    "location": "Colombia",
    "topic": "Seguridad",
    "candidate_name": "Candidato Demo",
    "politician": "candidato",
    "days_back": 30,
    "forecast_days": 14
}

TRENDING_PAYLOAD = {
    "location": "Colombia",
    "limit": 6
}


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_success(text):
    """Print success message."""
    print(f"✅ {text}")


def print_error(text):
    """Print error message."""
    print(f"❌ {text}")


def print_info(text):
    """Print info message."""
    print(f"ℹ️  {text}")


def test_endpoint(name, method, url, payload=None, params=None):
    """Test an API endpoint."""
    print_header(f"Testing {name}")
    print_info(f"URL: {url}")
    if payload:
        print_info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    if params:
        print_info(f"Params: {params}")
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, params=params, timeout=TIMEOUT)
        else:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )
        
        elapsed = time.time() - start_time
        
        print_info(f"Status: {response.status_code}")
        print_info(f"Time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print_success(f"{name} - Success!")
                
                # Print key fields
                if isinstance(data, dict):
                    if "success" in data:
                        print_info(f"Success flag: {data['success']}")
                    if "error" in data:
                        print_error(f"Error in response: {data['error']}")
                        return False
                    
                    # Print relevant fields based on endpoint
                    if "summary" in data:
                        print_info("Summary available")
                    if "forecast" in data:
                        print_info("Forecast data available")
                    if "series" in data:
                        print_info(f"Series data: {len(data.get('series', {}).get('dates', []))} points")
                    if "trending_topics" in data:
                        print_info(f"Trending topics: {len(data.get('trending_topics', []))}")
                    if "metadata" in data:
                        print_info("Metadata available")
                
                return True
            except json.JSONDecodeError:
                print_error(f"{name} - Invalid JSON response")
                print(response.text[:500])
                return False
        else:
            print_error(f"{name} - Failed with status {response.status_code}")
            try:
                error_data = response.json()
                if "error" in error_data:
                    print_error(f"Error: {error_data['error']}")
            except:
                print(response.text[:500])
            return False
            
    except requests.exceptions.Timeout:
        print_error(f"{name} - Request timeout (> {TIMEOUT}s)")
        return False
    except requests.exceptions.ConnectionError:
        print_error(f"{name} - Connection error. Is the server running?")
        return False
    except Exception as e:
        print_error(f"{name} - Unexpected error: {str(e)}")
        return False


def test_dashboard_page():
    """Test the dashboard HTML page."""
    print_header("Testing Dashboard Page")
    url = f"{BASE_URL}/dashboard"
    print_info(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print_info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            if "unified_dashboard" in content.lower() or "dashboard unificado" in content.lower():
                print_success("Dashboard page loads successfully")
                print_info(f"Content length: {len(content)} bytes")
                return True
            else:
                print_error("Dashboard page content doesn't match expected")
                return False
        else:
            print_error(f"Dashboard page failed with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Dashboard page - Error: {str(e)}")
        return False


def test_health():
    """Test health endpoint."""
    print_header("Testing Health Endpoint")
    url = f"{BASE_URL}/api/health"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print_success("Health check passed")
            data = response.json()
            print_info(f"Status: {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  UNIFIED DASHBOARD API TESTS")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    results = []
    
    # Test health first
    results.append(("Health Check", test_health()))
    
    # Test dashboard page
    results.append(("Dashboard Page", test_dashboard_page()))
    
    # Test API endpoints
    results.append((
        "Media Analyze",
        test_endpoint(
            "Media Analyze API",
            "POST",
            f"{BASE_URL}/api/media/analyze",
            payload=MEDIA_PAYLOAD
        )
    ))
    
    results.append((
        "Forecast Dashboard",
        test_endpoint(
            "Forecast Dashboard API",
            "POST",
            f"{BASE_URL}/api/forecast/dashboard",
            payload=FORECAST_PAYLOAD
        )
    ))
    
    results.append((
        "Campaign Trending",
        test_endpoint(
            "Campaign Trending API",
            "GET",
            f"{BASE_URL}/api/campaign/trending",
            params=TRENDING_PAYLOAD
        )
    ))
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! 🎉")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

