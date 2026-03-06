#!/usr/bin/env python3
"""
Quick test script for frontend-compatible API endpoints.

This script tests all the endpoints required by the Fermati Next.js frontend.
"""

import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_endpoint(method: str, endpoint: str, description: str, params: Dict = None) -> Any:
    """Test an API endpoint and print results."""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n🔍 Testing: {description}")
    print(f"   {method} {endpoint}")
    
    if params:
        print(f"   Params: {params}")
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, params=params, timeout=10)
        else:
            print(f"   ❌ Unsupported method: {method}")
            return None
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success")
            
            # Print summary of response
            if isinstance(data, dict):
                if "stops" in data:
                    print(f"   📊 Found {len(data['stops'])} stops")
                elif "departures" in data:
                    print(f"   📊 Found {len(data['departures'])} departures")
                elif "routes" in data:
                    print(f"   📊 Found {len(data['routes'])} routes")
                elif "journeys" in data:
                    print(f"   📊 Found {len(data['journeys'])} journeys")
                elif "alerts" in data:
                    print(f"   📊 Found {len(data['alerts'])} alerts")
            
            return data
        else:
            print(f"   ❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error text: {response.text[:200]}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error: Is the server running at {BASE_URL}?")
        return None
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None


def main():
    """Run all frontend API tests."""
    print("\n" + "🚀" * 40)
    print("  FERMATI FRONTEND API - TEST SUITE")
    print("🚀" * 40)
    
    # Test 1: Search stops by text
    print_section("1. Search Stops by Text")
    stops_data = test_endpoint(
        "GET",
        f"{API_PREFIX}/stops/search",
        "Search for stops containing 'cosenza'",
        {"query": "cosenza", "limit": 3}
    )
    
    # Get a stop ID for further tests
    stop_id = None
    if stops_data and "stops" in stops_data and len(stops_data["stops"]) > 0:
        stop_id = stops_data["stops"][0]["id"]
        print(f"\n   📌 Using stop ID for next tests: {stop_id}")
    
    # Test 2: Search stops by GPS
    print_section("2. Search Stops by GPS Coordinates")
    test_endpoint(
        "GET",
        f"{API_PREFIX}/stops/search",
        "Search stops near Cosenza coordinates",
        {"lat": 39.2986, "lng": 16.2540, "radius": 2, "limit": 5}
    )
    
    # Test 3: Get stop by ID
    if stop_id:
        print_section("3. Get Stop Details by ID")
        test_endpoint(
            "GET",
            f"{API_PREFIX}/stops/{stop_id}",
            f"Get details for stop '{stop_id}'"
        )
    
    # Test 4: Get departures from stop
    if stop_id:
        print_section("4. Get Next Departures from Stop")
        test_endpoint(
            "GET",
            f"{API_PREFIX}/stops/{stop_id}/departures",
            f"Get next departures from '{stop_id}'",
            {"limit": 5}
        )
    
    # Test 5: Get all routes
    print_section("5. Get All Routes/Lines")
    routes_data = test_endpoint(
        "GET",
        f"{API_PREFIX}/routes",
        "Get all available bus routes"
    )
    
    # Get a route ID for further tests
    route_id = None
    if routes_data and "routes" in routes_data and len(routes_data["routes"]) > 0:
        route_id = routes_data["routes"][0]["id"]
        print(f"\n   📌 Using route ID for next tests: {route_id}")
    
    # Test 6: Get route details
    if route_id:
        print_section("6. Get Route Details")
        test_endpoint(
            "GET",
            f"{API_PREFIX}/routes/{route_id}",
            f"Get details for route '{route_id}'"
        )
    
    # Test 7: Get route schedule
    if route_id:
        print_section("7. Get Route Schedule")
        test_endpoint(
            "GET",
            f"{API_PREFIX}/routes/{route_id}/schedule",
            f"Get schedule for route '{route_id}'",
            {"date": "2026-03-06"}
        )
    
    # Test 8: Plan journey
    print_section("8. Plan Journey Between Stops")
    test_endpoint(
        "GET",
        f"{API_PREFIX}/routes/plan",
        "Plan route from 'cosenza' to 'scalea'",
        {"from": "cosenza", "to": "scalea"}
    )
    
    # Test 9: Get service alerts
    print_section("9. Get Service Alerts")
    test_endpoint(
        "GET",
        f"{API_PREFIX}/alerts",
        "Get all active service alerts"
    )
    
    # Test 10: Get alerts filtered by route
    if route_id:
        print_section("10. Get Alerts for Specific Route")
        test_endpoint(
            "GET",
            f"{API_PREFIX}/alerts",
            f"Get alerts for route '{route_id}'",
            {"routeId": route_id}
        )
    
    # Summary
    print_section("TEST SUMMARY")
    print("\n✅ All frontend API endpoints have been tested!")
    print("\n📖 For detailed integration guide, see: FRONTEND_INTEGRATION.md")
    print("\n🌐 Interactive documentation: http://localhost:8000/docs")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
