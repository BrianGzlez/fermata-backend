#!/usr/bin/env python3
"""
Test timezone fix for /api/direct-routes endpoint.
"""

import requests
from datetime import datetime
import pytz

BASE_URL = "https://fermati-backend.onrender.com"

print("="*70)
print("🔍 TESTING TIMEZONE FIX")
print("="*70)

# Get current time in Italy
italy_tz = pytz.timezone('Europe/Rome')
now_italy = datetime.now(italy_tz)
current_time_italy = now_italy.strftime("%H:%M")

print(f"\n⏰ Current time in Italy (Europe/Rome): {current_time_italy}")
print(f"   Full datetime: {now_italy}")

# Test /api/direct-routes
print("\n1️⃣  Testing /api/direct-routes")
print("-"*70)

url = f"{BASE_URL}/api/direct-routes?from=rende-(arcavacata-piazza-cuticchia)&to=rende-(surdo-piazza,via-f.petrarca-n.21)&limit=10"

try:
    response = requests.get(url, timeout=15)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: 200")
        print(f"   Count: {data['count']}")
        
        if data['count'] > 0:
            print(f"\n   Departures returned:")
            for i, dep in enumerate(data['departures'][:5], 1):
                dep_time = dep['departureTime']
                print(f"   {i}. {dep_time} - Route {dep['routeId']} ({dep['periodicity']})")
                
                # Check if departure is in the future
                dep_hour, dep_min = map(int, dep_time.split(':'))
                current_hour, current_min = map(int, current_time_italy.split(':'))
                
                dep_minutes = dep_hour * 60 + dep_min
                current_minutes = current_hour * 60 + current_min
                
                if dep_minutes > current_minutes:
                    print(f"      ✅ Future departure ({dep_minutes - current_minutes} min from now)")
                else:
                    print(f"      ❌ Past departure ({current_minutes - dep_minutes} min ago)")
        else:
            print(f"   ⚠️  No departures found")
            print(f"   This might be normal if there are no more buses today")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test /api/stops/departures
print("\n2️⃣  Testing /api/stops/departures")
print("-"*70)

url = f"{BASE_URL}/api/stops/rende-(arcavacata-piazza-cuticchia)/departures?limit=10"

try:
    response = requests.get(url, timeout=15)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: 200")
        print(f"   Departures: {len(data['departures'])}")
        print(f"   Timestamp: {data['timestamp']}")
        
        if data['departures']:
            print(f"\n   Departures returned:")
            for i, dep in enumerate(data['departures'][:5], 1):
                dep_time = dep['departureTime']
                print(f"   {i}. {dep_time} - Route {dep['routeId']} ({dep['periodicity']})")
                
                # Check if departure is in the future
                dep_hour, dep_min = map(int, dep_time.split(':'))
                current_hour, current_min = map(int, current_time_italy.split(':'))
                
                dep_minutes = dep_hour * 60 + dep_min
                current_minutes = current_hour * 60 + current_min
                
                if dep_minutes > current_minutes:
                    print(f"      ✅ Future departure ({dep_minutes - current_minutes} min from now)")
                else:
                    print(f"      ❌ Past departure ({current_minutes - dep_minutes} min ago)")
        else:
            print(f"   ⚠️  No departures found")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
print("\nExpected behavior:")
print("- All returned departures should be AFTER current Italy time")
print("- If no departures, it means no more buses today (normal)")
print("- Timestamp should reflect Italy timezone")
