#!/usr/bin/env python3
"""
Test script for direct routes endpoint.
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://fermati-backend.onrender.com"

print("=" * 80)
print("🧪 TESTING DIRECT ROUTES ENDPOINT")
print("=" * 80)

# Test 1: Direct routes from Cosenza Autostazione to Rende
print("\n1️⃣  TEST: Cosenza Autostazione → Rende (any stop)")
print("-" * 80)

from_stop = "*cosenza-(autostazione)"
to_stop = "*rende-(roges-via-crati-n.c.12)"

url = f"{BASE_URL}/api/routes/direct?from={from_stop}&to={to_stop}&limit=10&timeWindow=1440"
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS!")
        print(f"From: {data['from']['name']}")
        print(f"To: {data['to']['name']}")
        print(f"Found {data['count']} direct routes\n")
        
        if data['departures']:
            print("Sample departures:")
            for i, dep in enumerate(data['departures'][:5], 1):
                print(f"\n  {i}. Route {dep['routeId']}: {dep['routeName']}")
                print(f"     Departure: {dep['departureTime']}")
                print(f"     Arrival: {dep['arrivalTime']}")
                print(f"     Duration: {dep['estimatedDuration']} minutes")
                print(f"     Stops: {dep['stopSequence']['fromIndex']} → {dep['stopSequence']['toIndex']} ({dep['stopSequence']['intermediateStops']} intermediate)")
                print(f"     Periodicity: {dep['periodicity']}")
        else:
            print("⚠️  No direct routes found")
            print("This might be normal if:")
            print("  - No routes connect these stops directly")
            print("  - All buses already departed")
            print("  - Wrong periodicity for current day/time")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")

# Test 2: Try without asterisk
print("\n\n2️⃣  TEST: Same route without asterisk (normalization test)")
print("-" * 80)

from_stop_no_asterisk = "cosenza-(autostazione)"
to_stop_no_asterisk = "rende-(roges-via-crati-n.c.12)"

url = f"{BASE_URL}/api/routes/direct?from={from_stop_no_asterisk}&to={to_stop_no_asterisk}&limit=5"
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Normalization works!")
        print(f"Found {data['count']} routes")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")

# Test 3: Check if stops have routes populated
print("\n\n3️⃣  TEST: Check if stops have routes field populated")
print("-" * 80)

url = f"{BASE_URL}/api/stops/*cosenza-(autostazione)"
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Stop found!")
        print(f"Name: {data['name']}")
        print(f"Routes: {data['routes']}")
        
        if data['routes']:
            print(f"✅ Routes field is populated with {len(data['routes'])} routes")
        else:
            print(f"⚠️  Routes field is EMPTY - needs to be populated during sync")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")

# Test 4: Check route details
print("\n\n4️⃣  TEST: Check route details (stops in order)")
print("-" * 80)

url = f"{BASE_URL}/api/routes/136"
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Route found!")
        print(f"Name: {data['name']}")
        print(f"Total stops: {len(data['stops'])}")
        
        if data['stops']:
            print(f"\nFirst 5 stops in order:")
            for stop in data['stops'][:5]:
                print(f"  {stop.get('order', '?')}. {stop['name']}")
        else:
            print(f"⚠️  No stops in route")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")

print("\n" + "=" * 80)
print("✅ TESTS COMPLETE")
print("=" * 80)
