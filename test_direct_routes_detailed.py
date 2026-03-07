#!/usr/bin/env python3
"""
Detailed test of /api/direct-routes endpoint to diagnose why it returns empty.
"""

import requests
import json
from src.database import SessionLocal
from src.db_models import Stop, Route, Departure

print("="*70)
print("🔍 DETAILED TEST: /api/direct-routes")
print("="*70)

# Test 1: Check database directly
print("\n1️⃣  CHECKING DATABASE DIRECTLY")
print("-"*70)
db = SessionLocal()

# Find stops with "139" in their routes
stops_with_139 = db.query(Stop).filter(Stop.routes.contains(["139"])).all()
print(f"Stops with route 139: {len(stops_with_139)}")
for stop in stops_with_139[:5]:
    print(f"  - {stop.id}: {stop.name}")

# Get departures for route 139
departures_139 = db.query(Departure).filter(Departure.route_id == "139").limit(10).all()
print(f"\nDepartures for route 139: {db.query(Departure).filter(Departure.route_id == '139').count()}")
print("Sample departures:")
for dep in departures_139[:3]:
    print(f"  - Stop: {dep.stop_id}, Time: {dep.departure_time}, Dest: {dep.destination}")

db.close()

# Test 2: Try different stop combinations
print("\n2️⃣  TESTING DIFFERENT STOP COMBINATIONS")
print("-"*70)

test_cases = [
    # From frontend test
    ("*cosenza-(via-magna-grecia---stadio)", "*rende-(arcavacata-contradamacchialonga-casepop.)"),
    # Without asterisks
    ("cosenza-(via-magna-grecia---stadio)", "rende-(arcavacata-contradamacchialonga-casepop.)"),
    # Try other stops on route 139
    ("*cosenza-(via-magna-grecia---stadio)", "rende-(unical-terminal-bus)"),
    ("cosenza-(autostazione)", "rende-(unical-terminal-bus)"),
]

BASE_URL = "https://fermati-backend.onrender.com"

for from_stop, to_stop in test_cases:
    print(f"\nTest: {from_stop} → {to_stop}")
    url = f"{BASE_URL}/api/direct-routes?from={from_stop}&to={to_stop}&limit=20"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print(f"  Status: {response.status_code}")
        print(f"  Count: {data.get('count', 0)}")
        
        if data.get('count', 0) > 0:
            print(f"  ✅ Found {data['count']} departures!")
            for dep in data['departures'][:2]:
                print(f"    - Route {dep['routeId']}: {dep['departureTime']} → {dep['arrivalTime']}")
        else:
            print(f"  ❌ No departures found")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Test 3: Check if stops exist in database
print("\n3️⃣  CHECKING IF STOPS EXIST")
print("-"*70)

db = SessionLocal()
test_stops = [
    "*cosenza-(via-magna-grecia---stadio)",
    "cosenza-(via-magna-grecia---stadio)",
    "*rende-(arcavacata-contradamacchialonga-casepop.)",
    "rende-(arcavacata-contradamacchialonga-casepop.)",
]

for stop_id in test_stops:
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if stop:
        print(f"✅ {stop_id}")
        print(f"   Routes: {stop.routes}")
    else:
        print(f"❌ {stop_id} NOT FOUND")

db.close()

# Test 4: Check route 139 stops order
print("\n4️⃣  CHECKING ROUTE 139 STOPS ORDER")
print("-"*70)

db = SessionLocal()
route_139 = db.query(Route).filter(Route.id == "139").first()
if route_139:
    print(f"Route 139: {route_139.name}")
    print(f"Total stops: {len(route_139.stops_order)}")
    print("\nFirst 10 stops:")
    for stop in route_139.stops_order[:10]:
        print(f"  {stop['order']}: {stop['id']} - {stop['name']}")
else:
    print("❌ Route 139 not found")

db.close()

# Test 5: Manual check - do these stops appear in route 139?
print("\n5️⃣  MANUAL CHECK: Are test stops in route 139?")
print("-"*70)

db = SessionLocal()
route_139 = db.query(Route).filter(Route.id == "139").first()
if route_139:
    stop_ids_in_route = [s['id'] for s in route_139.stops_order]
    
    test_stops_check = [
        "*cosenza-(via-magna-grecia---stadio)",
        "cosenza-(via-magna-grecia---stadio)",
        "*rende-(arcavacata-contradamacchialonga-casepop.)",
        "rende-(arcavacata-contradamacchialonga-casepop.)",
    ]
    
    for stop_id in test_stops_check:
        if stop_id in stop_ids_in_route:
            idx = stop_ids_in_route.index(stop_id)
            print(f"✅ {stop_id} is at position {idx}")
        else:
            print(f"❌ {stop_id} NOT in route 139")
            # Try to find similar
            similar = [s for s in stop_ids_in_route if stop_id.replace('*', '') in s or s in stop_id.replace('*', '')]
            if similar:
                print(f"   Similar stops found: {similar[:3]}")

db.close()

# Test 6: Check departures for specific stops
print("\n6️⃣  CHECKING DEPARTURES FOR SPECIFIC STOPS")
print("-"*70)

db = SessionLocal()
test_stop = "*cosenza-(via-magna-grecia---stadio)"
departures = db.query(Departure).filter(
    Departure.stop_id == test_stop,
    Departure.route_id == "139"
).limit(5).all()

print(f"Departures from {test_stop} on route 139: {len(departures)}")
for dep in departures:
    print(f"  - {dep.departure_time} → {dep.destination} (trip: {dep.trip_id})")

db.close()

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
