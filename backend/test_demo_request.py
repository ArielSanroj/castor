"""
Test script for demo request endpoint.
Tests the /api/demo-request endpoint to ensure it saves data to PostgreSQL.
"""
import sys
import os
import requests
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def test_demo_request():
    """Test demo request endpoint."""
    base_url = os.getenv('API_BASE_URL', 'http://localhost:5001')
    endpoint = f"{base_url}/api/demo-request"
    
    # Test data
    test_data = {
        "first_name": "Juan",
        "last_name": "Pérez",
        "email": f"test_{os.urandom(4).hex()}@example.com",  # Unique email
        "phone": "+573001234567",
        "interest": "forecast",
        "location": "Bogotá"
    }
    
    print("=" * 60)
    print("Testing Demo Request Endpoint")
    print("=" * 60)
    print(f"Endpoint: {endpoint}")
    print(f"Test Data: {json.dumps(test_data, indent=2)}")
    print("-" * 60)
    
    try:
        # Make request
        response = requests.post(
            endpoint,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            result = response.json()
            if result.get('success'):
                print("\n✅ SUCCESS: Demo request created successfully!")
                print(f"   Lead ID: {result.get('lead_id')}")
                return True
            else:
                print("\n❌ FAILED: Request returned success=False")
                return False
        else:
            print(f"\n❌ FAILED: Status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server.")
        print("   Make sure the Flask server is running on", base_url)
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False


def test_multiple_interests():
    """Test with different interest values."""
    base_url = os.getenv('API_BASE_URL', 'http://localhost:5001')
    endpoint = f"{base_url}/api/demo-request"
    
    interests = ["forecast", "campañas", "medios"]
    results = []
    
    print("\n" + "=" * 60)
    print("Testing Multiple Interest Values")
    print("=" * 60)
    
    for interest in interests:
        test_data = {
            "first_name": "Test",
            "last_name": f"User_{interest}",
            "email": f"test_{interest}_{os.urandom(4).hex()}@example.com",
            "phone": "+573001234567",
            "interest": interest,
            "location": "Medellín"
        }
        
        try:
            response = requests.post(
                endpoint,
                json=test_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            success = response.status_code == 201 and response.json().get('success')
            results.append((interest, success))
            status = "✅" if success else "❌"
            print(f"{status} {interest}: {response.status_code}")
            
        except Exception as e:
            results.append((interest, False))
            print(f"❌ {interest}: Error - {str(e)}")
    
    print("-" * 60)
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("✅ All interest types work correctly!")
    else:
        print("❌ Some interest types failed")
    
    return all_passed


if __name__ == '__main__':
    print("\n🧪 Starting Demo Request Tests\n")
    
    # Test 1: Basic demo request
    test1_passed = test_demo_request()
    
    # Test 2: Multiple interests
    test2_passed = test_multiple_interests()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Basic Request: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Multiple Interests: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        sys.exit(1)

