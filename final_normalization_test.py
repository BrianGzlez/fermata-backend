#!/usr/bin/env python3
"""Final normalization test for frontend compatibility."""

import requests
import json

BASE_URL = "https://fermati-backend.onrender.com"

print("="*70)
print("🔍 FINAL NORMALIZATION TEST FOR FRONTEND")
print("="*70)

tests_passed = 0
tests_failed = 0

def test(name, url, check_func=None):
    global tests_passed, tests_failed
    print(f"\n✓ Testing: {name}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if check_func:
                if check_func(data):
                    print(f"  ✅ PASS")
                    tests_passed += 1
                else:
                    print(f"  ❌ FAIL: Check function returned False")
                    tests_failed += 1
            else:
                print(f"  ✅ PASS")
                tests_passed += 1
        else:
            print(f"  ❌ FAIL: Status {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        tests_failed += 1

# Test 1: Stop with asterisk returns routes
test(
    "Stop with asterisk has routes field",
    f"{BASE_URL}/api/stops/*cosenza-(autostazione)",
    lambda d: isinstance(d.get("routes"), list) and len(d["routes"]) > 0
)

# Test 2: Stop without asterisk normalizes and returns routes
test(
    "Stop without asterisk normalizes and has routes",
    f"{BASE_URL}/api/stops/cosenza-(autostazione)",
    lambda d: isinstance(d.get("routes"), list) and len(d["routes"]) > 0
)

# Test 3: Search returns stops with routes
test(
    "Search returns stops with routes field",
    f"{BASE_URL}/api/stops/search?query=autostazione&limit=1",
    lambda d: len(d.get("stops", [])) > 0 and isinstance(d["stops"][0].get("routes"), list)
)

# Test 4: Departures with asterisk
test(
    "Departures with asterisk works",
    f"{BASE_URL}/api/stops/*cosenza-(autostazione)/departures?limit=3",
    lambda d: "departures" in d and isinstance(d["departures"], list)
)

# Test 5: Departures without asterisk (auto-normalize)
test(
    "Departures without asterisk auto-normalizes",
    f"{BASE_URL}/api/stops/cosenza-(autostazione)/departures?limit=3",
    lambda d: "departures" in d and isinstance(d["departures"], list)
)

# Test 6: Direct routes with asterisk
test(
    "Direct routes with asterisk works",
    f"{BASE_URL}/api/direct-routes?from=*cosenza-(autostazione)&to=*rende-(unical-terminal-bus)&limit=3",
    lambda d: "departures" in d and isinstance(d["departures"], list)
)

# Test 7: Direct routes without asterisk (auto-normalize)
test(
    "Direct routes without asterisk auto-normalizes",
    f"{BASE_URL}/api/direct-routes?from=cosenza-(autostazione)&to=rende-(unical-terminal-bus)&limit=3",
    lambda d: "departures" in d and isinstance(d["departures"], list)
)

# Test 8: Route planning with asterisk
test(
    "Route planning with asterisk works",
    f"{BASE_URL}/api/routes/plan?from=*cosenza-(autostazione)&to=*rende-(unical-terminal-bus)&maxTransfers=1",
    lambda d: "journeys" in d and isinstance(d["journeys"], list)
)

# Test 9: Route planning without asterisk (auto-normalize)
test(
    "Route planning without asterisk auto-normalizes",
    f"{BASE_URL}/api/routes/plan?from=cosenza-(autostazione)&to=rende-(unical-terminal-bus)&maxTransfers=1",
    lambda d: "journeys" in d and isinstance(d["journeys"], list)
)

# Test 10: Normalize endpoint
test(
    "Normalize endpoint works",
    f"{BASE_URL}/api/stops/normalize/cosenza-(autostazione)",
    lambda d: d.get("normalizedId") == "*cosenza-(autostazione)"
)

# Test 11: Get all routes
test(
    "Get all routes works",
    f"{BASE_URL}/api/routes",
    lambda d: "routes" in d and len(d["routes"]) > 0
)

# Test 12: Get specific route
test(
    "Get specific route works",
    f"{BASE_URL}/api/routes/135",
    lambda d: d.get("id") == "135" and "stops" in d
)

print("\n" + "="*70)
print(f"📊 RESULTS: {tests_passed} passed, {tests_failed} failed")
print("="*70)

if tests_failed == 0:
    print("✅ ALL TESTS PASSED - Frontend normalization is working correctly!")
else:
    print(f"⚠️  {tests_failed} test(s) failed - review above for details")

