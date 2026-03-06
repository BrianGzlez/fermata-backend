#!/usr/bin/env python3
"""
Script de prueba para verificar que la API funciona correctamente.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, description):
    """Test a single endpoint and print results."""
    print(f"\n🔍 Testing {description}")
    print(f"   Endpoint: {endpoint}")
    
    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success ({elapsed:.2f}s)")
            
            if isinstance(data, list):
                print(f"   📊 Found {len(data)} items")
                if data:
                    print(f"   📝 Sample: {data[0]}")
            elif isinstance(data, dict):
                if "error" in data:
                    print(f"   ⚠️  API Error: {data['error']}")
                else:
                    print(f"   📊 Keys: {list(data.keys())}")
            
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   📝 Response: {response.text[:200]}...")
            
    except requests.exceptions.Timeout:
        print(f"   ⏰ Timeout after 30 seconds")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")

def main():
    """Run all API tests."""
    print("🚀 Testing Consorzio Autolinee API")
    print("=" * 50)
    
    # Test 1: Health check
    test_endpoint("/health", "Health Check")
    
    # Test 2: Get all lines
    test_endpoint("/lines", "Get All Lines")
    
    # Get a sample line for further testing
    try:
        response = requests.get(f"{BASE_URL}/lines", timeout=10)
        if response.status_code == 200:
            lines = response.json()
            if lines:
                sample_line = lines[0]["value"]  # Use 'value' instead of 'id'
                print(f"\n📌 Using line {sample_line} for detailed testing")
                
                # Test 3: Get itineraries for sample line
                test_endpoint(f"/itineraries/{sample_line}", f"Get Itineraries for Line {sample_line}")
                
                # Get sample itinerary
                response = requests.get(f"{BASE_URL}/itineraries/{sample_line}", timeout=10)
                if response.status_code == 200:
                    itineraries = response.json()
                    if itineraries:
                        sample_itinerary = itineraries[0]["value"]  # Use 'value' instead of 'id'
                        
                        # Test 4: Get periodicities
                        test_endpoint(f"/periodicities/{sample_line}/{sample_itinerary}", 
                                    f"Get Periodicities for Line {sample_line}, Itinerary {sample_itinerary}")
                        
                        # Get sample periodicity
                        response = requests.get(f"{BASE_URL}/periodicities/{sample_line}/{sample_itinerary}", timeout=10)
                        if response.status_code == 200:
                            periodicities = response.json()
                            if periodicities:
                                sample_periodicity = periodicities[0]["value"]  # Use 'value' instead of 'id'
                                
                                # Test 5: Get schedule (this might take longer)
                                print(f"\n⚠️  Schedule test might take 10-30 seconds...")
                                test_endpoint(f"/schedule/{sample_line}/{sample_itinerary}/{sample_periodicity}", 
                                            f"Get Schedule for Line {sample_line}")
                                
                                # Test 5b: Debug raw PDF if schedule failed
                                print(f"\n🔍 Debug raw PDF response...")
                                test_endpoint(f"/debug/raw-pdf/{sample_line}/{sample_itinerary}/{sample_periodicity}", 
                                            f"Debug Raw PDF for Line {sample_line}")
                
                # Test 6: Test complete flow endpoint
                test_endpoint(f"/test-flow/{sample_line}", f"Test Complete Flow for Line {sample_line}")
                
                # Test 7: Debug values endpoint
                test_endpoint(f"/debug/values/{sample_line}", f"Debug Values for Line {sample_line}")
                
                # Test 8: Search stops
                test_endpoint("/search/stops?q=cosenza", "Search Stops")
                
                # Test 9: Get all stops
                test_endpoint("/stops/all", "Get All Stops")
                
                # Test 10: Nearby stops (sample coordinates)
                test_endpoint("/stops/nearby?lat=39.2986&lon=16.2540&radius=2.0", "Find Nearby Stops")
                
                # Test 11: Service alerts
                test_endpoint("/alerts", "Get Service Alerts")
                
                # Test 12: User favorites
                test_endpoint("/users/test_user/favorites", "Get User Favorites")
                
    except Exception as e:
        print(f"\n❌ Could not get sample line for detailed testing: {e}")
    
    # Test next departures if we found stops
    try:
        response = requests.get(f"{BASE_URL}/stops/all", timeout=10)
        if response.status_code == 200:
            stops_data = response.json()
            if stops_data.get("stops"):
                sample_stop = stops_data["stops"][0]["name"]
                test_endpoint(f"/stops/{sample_stop}/next-departures", f"Next Departures for {sample_stop}")
                test_endpoint(f"/stops/{sample_stop}/accessibility", f"Accessibility Info for {sample_stop}")
    except Exception as e:
        print(f"\n❌ Could not test stop-specific endpoints: {e}")
    
    # Test route planning
    try:
        test_endpoint("/routes/plan?from_stop=COSENZA&to_stop=SCALEA", "Route Planning")
    except Exception as e:
        print(f"\n❌ Could not test route planning: {e}")
    
    # Test 13: Clear cache
    print(f"\n🔍 Testing Clear Cache")
    try:
        response = requests.post(f"{BASE_URL}/admin/clear-cache", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Cache cleared successfully")
        else:
            print(f"   ❌ Failed to clear cache: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cache clear failed: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")
    print("\n💡 New Features Available:")
    print("   - 🔍 Search stops: /search/stops?q=<name>")
    print("   - 🚌 Next departures: /stops/<stop_name>/next-departures")
    print("   - 🗺️  Route planning: /routes/plan?from_stop=A&to_stop=B")
    print("   - 📍 Nearby stops: /stops/nearby?lat=X&lon=Y")
    print("   - 🚨 Service alerts: /alerts")
    print("   - ⭐ User favorites: /users/<user_id>/favorites")
    print("   - ♿ Accessibility: /stops/<stop_name>/accessibility")
    print("   - 📊 All stops index: /stops/all")
    print("\n📖 Documentation:")
    print("   - Visit http://localhost:8000/docs for interactive API documentation")
    print("   - Check logs for detailed information about each request")
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")
    print("\n💡 Tips:")
    print("   - Visit http://localhost:8000/docs for interactive API documentation")
    print("   - Use /test-flow/{line_id} to quickly test a complete workflow")
    print("   - Check logs for detailed information about each request")

if __name__ == "__main__":
    main()