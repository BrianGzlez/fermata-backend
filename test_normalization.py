#!/usr/bin/env python3
"""
Test normalization across all endpoints to ensure frontend compatibility.
"""

import requests
import json

BASE_URL = "https://fermati-backend.onrender.com"

def test_endpoint(name, url, expected_fields=None):
    """Test an endpoint and check response."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('-'*60)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success")
            
            # Check expected fields
            if expected_fields:
                for field in expected_fields:
                    if field in data:
                        print(f"  ✓ {field}: {type(data[field]).__name__}")
                    else:
                        print(f"  ✗ Missing field: {field}")
            
            # Show sample data
            print(f"\nSample response:")
            print(json.dumps(data, indent=2)[:500])
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:200])
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

print("="*60)
print("🔍 FRONTEND NORMALIZATION TEST")
print("="*60)

# Test 1: Get stop by ID (with asterisk)
test_endpoint(
    "Get Stop by ID (with asterisk)",
    f"{BASE_URL}/api/stops/*cosenza-(autostazione)",
    ["id", "name", "routes", "latitude", "longitude"]
)

# Test 2: Get stop by ID (without asterisk - should normalize)
test_endpoint(
    "Get Stop by ID (without asterisk - auto normalize)",
    f"{BASE_URL}/api/stops/cosenza-(autostazione)",
    ["id", "name", "routes", "latitude", "longitude"]
)

# Test 3: Search stops
test_endpoint(
    "Search Stops",
    f"{BASE_URL}/api/stops/search?query=cosenza&limit=3",
    ["stops"]
)

# Test 4: Get departures (with asterisk)
test_endpoint(
    "Get Departures (with asterisk)",
    f"{BASE_URL}/api/stops/*cosenza-(autostazione)/departures?limit=5",
    ["stopId", "stopName", "departures"]
)

# Test 5: Get departures (without asterisk - should normalize)
test_endpoint(
    "Get Departures (without asterisk - auto normalize)",
    f"{BASE_URL}/api/stops/cosenza-(autostazione)/departures?limit=5",
    ["stopId", "stopName", "departures"]
)

# Test 6: Direct routes (both with asterisk)
test_endpoint(
    "Direct Routes (both with asterisk)",
    f"{BASE_URL}/api/direct-routes?from=*cosenza-(autostazione)&to=*rende-(unical-terminal-bus)&limit=5",
    ["from", "to", "departures"]
)

# Test 7: Direct routes (mixed - one with, one without)
test_endpoint(
    "Direct Routes (mixed asterisks)",
    f"{BASE_URL}/api/direct-routes?from=cosenza-(autostazione)&to=rende-(unical-terminal-bus)&limit=5",
    ["from", "to", "departures"]
)

# Test 8: Route planning (with asterisk)
test_endpoint(
    "Route Planning (with asterisk)",
    f"{BASE_URL}/api/routes/plan?from=*cosenza-(autostazione)&to=*rende-(unical-terminal-bus)&maxTransfers=1",
    ["from", "to", "journeys"]
)

# Test 9: Route planning (without asterisk)
test_endpoint(
    "Route Planning (without asterisk)",
    f"{BASE_URL}/api/routes/plan?from=cosenza-(autostazione)&to=rende-(unical-terminal-bus)&maxTransfers=1",
    ["from", "to", "journeys"]
)

# Test 10: Normalize endpoint
test_endpoint(
    "Normalize Stop ID",
    f"{BASE_URL}/api/stops/normalize/cosenza-(autostazione)",
    ["originalId", "normalizedId", "name"]
)

print("\n" + "="*60)
print("✅ NORMALIZATION TEST COMPLETE")
print("="*60)
