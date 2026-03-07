#!/usr/bin/env python3
"""
Test /api/direct-routes endpoint against production server.
"""

import requests
import json

BASE_URL = "https://fermati-backend.onrender.com"

print("="*70)
print("🔍 TESTING /api/direct-routes IN PRODUCTION")
print("="*70)

# Test 1: Get stops info first
print("\n1️⃣  GETTING STOP INFORMATION")
print("-"*70)

test_stops = [
    "*cosenza-(via-magna-grecia---stadio)",
    "*rende-(arcavacata-contradamacchialonga-casepop.)",
]

for stop_id in test_stops:
    try:
        response = requests.get(f"{BASE_URL}/api/stops/{stop_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ {stop_id}")
            print(f"   Name: {data['name']}")
            print(f"   Routes: {data['routes']}")
        else:
            print(f"\n❌ {stop_id}: {response.status_code}")
    except Exception as e:
        print(f"\n❌ {stop_id}: {e}")

# Test 2: Get departures from first stop
print("\n2️⃣  GETTING DEPARTURES FROM FIRST STOP")
print("-"*70)

try:
    response = requests.get(
        f"{BASE_URL}/api/stops/*cosenza-(via-magna-grecia---stadio)/departures?limit=20",
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"Total departures: {len(data['departures'])}")
        
        # Group by route
        by_route = {}
        for dep in data['departures']:
            route_id = dep['routeId']
            if route_id not in by_route:
                by_route[route_id] = []
            by_route[route_id].append(dep)
        
        print("\nDepartures by route:")
        for route_id, deps in by_route.items():
            print(f"  Route {route_id}: {len(deps)} departures")
            if len(deps) > 0:
                print(f"    First: {deps[0]['departureTime']} → {deps[0]['destination']}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Get route 139 details
print("\n3️⃣  GETTING ROUTE 139 DETAILS")
print("-"*70)

try:
    response = requests.get(f"{BASE_URL}/api/routes/139", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"Route: {data['name']}")
        print(f"Total stops: {len(data['stops'])}")
        
        # Find our test stops
        stop_ids = [s['id'] for s in data['stops']]
        
        test_stop_1 = "*cosenza-(via-magna-grecia---stadio)"
        test_stop_2 = "*rende-(arcavacata-contradamacchialonga-casepop.)"
        
        if test_stop_1 in stop_ids:
            idx1 = stop_ids.index(test_stop_1)
            print(f"\n✅ {test_stop_1} found at position {idx1}")
        else:
            print(f"\n❌ {test_stop_1} NOT in route")
            # Try without asterisk
            test_stop_1_no_ast = test_stop_1.replace('*', '')
            if test_stop_1_no_ast in stop_ids:
                idx1 = stop_ids.index(test_stop_1_no_ast)
                print(f"   But found without asterisk at position {idx1}")
        
        if test_stop_2 in stop_ids:
            idx2 = stop_ids.index(test_stop_2)
            print(f"✅ {test_stop_2} found at position {idx2}")
        else:
            print(f"❌ {test_stop_2} NOT in route")
            # Try without asterisk
            test_stop_2_no_ast = test_stop_2.replace('*', '')
            if test_stop_2_no_ast in stop_ids:
                idx2 = stop_ids.index(test_stop_2_no_ast)
                print(f"   But found without asterisk at position {idx2}")
        
        print("\nFirst 10 stops in route:")
        for stop in data['stops'][:10]:
            print(f"  {stop['order']}: {stop['id']}")
            
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Try direct-routes with different combinations
print("\n4️⃣  TESTING /api/direct-routes WITH DIFFERENT COMBINATIONS")
print("-"*70)

test_cases = [
    # Original test
    ("*cosenza-(via-magna-grecia---stadio)", "*rende-(arcavacata-contradamacchialonga-casepop.)"),
    # Without asterisks
    ("cosenza-(via-magna-grecia---stadio)", "rende-(arcavacata-contradamacchialonga-casepop.)"),
    # Try known working stops
    ("*cosenza-(autostazione)", "*rende-(unical-terminal-bus)"),
    ("cosenza-(autostazione)", "rende-(unical-terminal-bus)"),
]

for from_stop, to_stop in test_cases:
    print(f"\n📍 Testing: {from_stop} → {to_stop}")
    
    url = f"{BASE_URL}/api/direct-routes?from={from_stop}&to={to_stop}&limit=20&timeWindow=1440"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print(f"   Status: {response.status_code}")
        print(f"   From: {data.get('from', {}).get('name', 'N/A')}")
        print(f"   To: {data.get('to', {}).get('name', 'N/A')}")
        print(f"   Count: {data.get('count', 0)}")
        
        if data.get('count', 0) > 0:
            print(f"   ✅ Found {data['count']} direct routes!")
            for dep in data['departures'][:3]:
                print(f"      - Route {dep['routeId']}: {dep['departureTime']} → {dep['arrivalTime']} ({dep['estimatedDuration']} min)")
        else:
            print(f"   ❌ No direct routes found")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Test 5: Check if the issue is with the specific stops
print("\n5️⃣  CHECKING STOP NORMALIZATION")
print("-"*70)

for stop_id in ["*cosenza-(via-magna-grecia---stadio)", "cosenza-(via-magna-grecia---stadio)"]:
    try:
        response = requests.get(f"{BASE_URL}/api/stops/normalize/{stop_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"\n{stop_id}")
            print(f"  → Normalized to: {data['normalizedId']}")
            print(f"  → Name: {data['name']}")
        else:
            print(f"\n❌ {stop_id}: {response.status_code}")
    except Exception as e:
        print(f"\n❌ {stop_id}: {e}")

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
