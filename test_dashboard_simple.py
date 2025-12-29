#!/usr/bin/env python3
"""
Simple test script to verify dashboard endpoints are accessible.
Tests basic connectivity without requiring full service initialization.
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5001"

def test_endpoint(name, method, url, **kwargs):
    """Test an endpoint and print results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"Method: {method}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10, **kwargs)
        else:
            response = requests.post(url, timeout=30, **kwargs)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code < 500:
            print("✅ Endpoint is accessible")
            try:
                data = response.json()
                if "error" in data:
                    print(f"⚠️  Error message: {data.get('error')}")
                elif "success" in data:
                    print(f"✅ Success: {data.get('success')}")
            except:
                pass
        else:
            print(f"❌ Server error: {response.status_code}")
            try:
                error = response.json()
                print(f"   Error: {error.get('error', 'Unknown')}")
            except:
                print(f"   Response: {response.text[:200]}")
        
        return response.status_code < 500
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - Is the server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    print("\n" + "="*60)
    print("UNIFIED DASHBOARD - SIMPLE CONNECTIVITY TEST")
    print("="*60)
    
    # Test 1: Health endpoint
    test_endpoint(
        "Health Check",
        "GET",
        f"{BASE_URL}/api/health"
    )
    
    # Test 2: Dashboard page
    test_endpoint(
        "Dashboard Page",
        "GET",
        f"{BASE_URL}/dashboard"
    )
    
    # Test 3: Media API (will fail if services not initialized)
    test_endpoint(
        "Media Analyze API",
        "POST",
        f"{BASE_URL}/api/media/analyze",
        json={
            "location": "Colombia",
            "max_tweets": 5,
            "time_window_days": 7,
            "language": "es"
        }
    )
    
    # Test 4: Forecast API
    test_endpoint(
        "Forecast Dashboard API",
        "POST",
        f"{BASE_URL}/api/forecast/dashboard",
        json={
            "location": "Colombia",
            "days_back": 7,
            "forecast_days": 7
        }
    )
    
    # Test 5: Trending API
    test_endpoint(
        "Campaign Trending API",
        "GET",
        f"{BASE_URL}/api/campaign/trending",
        params={"location": "Colombia", "limit": 3}
    )
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\n📝 Note: If APIs return 503/500, check:")
    print("   1. Environment variables (.env file)")
    print("   2. Twitter API token (TWITTER_BEARER_TOKEN)")
    print("   3. OpenAI API key (OPENAI_API_KEY)")
    print("   4. Server logs for initialization errors")
    print("\n🌐 Dashboard URL: http://localhost:5001/dashboard")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

