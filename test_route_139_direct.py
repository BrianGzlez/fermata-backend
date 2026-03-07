#!/usr/bin/env python3
"""Test direct routes on route 139 with correct stops."""

import requests

BASE_URL = "https://fermati-backend.onrender.com"

print("="*70)
print("🔍 TESTING ROUTE 139 DIRECT ROUTES")
print("="*70)

# Get route 139 stops
response = requests.get(f"{BASE_URL}/api/routes/139")
route_data = response.json()

print(f"\nRoute: {route_data['name']}")
print(f"Total stops: {len(route_data['stops'])}\n")

# Find stops that are in route 139
stops_139 = [s for s in route_data['stops']]

# Test with first and last stop
if len(stops_139) >= 2:
    first_stop = stops_139[0]['id']
    last_stop = stops_139[-1]['id']
    middle_stop = stops_139[len(stops_139)//2]['id']
    
    print(f"First stop: {first_stop}")
    print(f"Middle stop: {middle_stop}")
    print(f"Last stop: {last_stop}\n")
    
    # Test 1: First to middle
    print("1️⃣  Testing: First → Middle")
    print("-"*70)
    url = f"{BASE_URL}/api/direct-routes?from={first_stop}&to={middle_stop}&limit=20&timeWindow=1440"
    response = requests.get(url)
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Count: {data.get('count', 0)}")
    if data.get('count', 0) > 0:
        print("✅ Found direct routes!")
        for dep in data['departures'][:3]:
            print(f"  - Route {dep['routeId']}: {dep['departureTime']} → {dep['arrivalTime']}")
    else:
        print("❌ No direct routes")
    
    # Test 2: Middle to last
    print("\n2️⃣  Testing: Middle → Last")
    print("-"*70)
    url = f"{BASE_URL}/api/direct-routes?from={middle_stop}&to={last_stop}&limit=20&timeWindow=1440"
    response = requests.get(url)
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Count: {data.get('count', 0)}")
    if data.get('count', 0) > 0:
        print("✅ Found direct routes!")
        for dep in data['departures'][:3]:
            print(f"  - Route {dep['routeId']}: {dep['departureTime']} → {dep['arrivalTime']}")
    else:
        print("❌ No direct routes")
    
    # Test 3: Cosenza Stadio to Arcavacata (both in route 139)
    print("\n3️⃣  Testing: Cosenza Stadio → Arcavacata Piazza")
    print("-"*70)
    from_stop = "*cosenza-(via-magna-grecia---stadio)"
    to_stop = "rende-(arcavacata-piazza-cuticchia)"
    
    url = f"{BASE_URL}/api/direct-routes?from={from_stop}&to={to_stop}&limit=20&timeWindow=1440"
    response = requests.get(url)
    data = response.json()
    print(f"From: {from_stop}")
    print(f"To: {to_stop}")
    print(f"Status: {response.status_code}")
    print(f"Count: {data.get('count', 0)}")
    if data.get('count', 0) > 0:
        print("✅ Found direct routes!")
        for dep in data['departures'][:3]:
            print(f"  - Route {dep['routeId']}: {dep['departureTime']} → {dep['arrivalTime']} ({dep['estimatedDuration']} min)")
            print(f"    Stops: {dep['stopSequence']['fromIndex']} → {dep['stopSequence']['toIndex']} ({dep['stopSequence']['intermediateStops']} intermediate)")
    else:
        print("❌ No direct routes")
        print(f"Response: {data}")

print("\n" + "="*70)
