#!/usr/bin/env python3
"""
Check production database data for route 139.
"""

import psycopg2
import json

# Production database connection
DB_URL = "postgresql://fermati_db_user:7oudj7InyxA6TfXmS4Mv0bL3zfrhJY9H@dpg-d6lj7ap5pdvs73fhgls0-a.oregon-postgres.render.com/fermati_db"

print("="*70)
print("🔍 CHECKING PRODUCTION DATABASE DATA")
print("="*70)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# 1. Check route 139 in routes table
print("\n1️⃣  ROUTE 139 IN ROUTES TABLE")
print("-"*70)
cur.execute("SELECT id, name, stops_order FROM routes WHERE id = '139'")
route = cur.fetchone()
if route:
    route_id, route_name, stops_order = route
    print(f"Route ID: {route_id}")
    print(f"Route Name: {route_name}")
    print(f"Stops in route: {len(stops_order) if stops_order else 0}")
    
    if stops_order:
        print("\nFirst 5 stops:")
        for i, stop in enumerate(stops_order[:5]):
            print(f"  {i}: {stop['id']} - {stop['name']}")
        
        # Check if our test stops are in the route
        stop_ids = [s['id'] for s in stops_order]
        test_stops = [
            "*cosenza-(via-magna-grecia---stadio)",
            "rende-(arcavacata-piazza-cuticchia)"
        ]
        
        print("\nTest stops in route:")
        for test_stop in test_stops:
            if test_stop in stop_ids:
                idx = stop_ids.index(test_stop)
                print(f"  ✅ {test_stop} at position {idx}")
            else:
                print(f"  ❌ {test_stop} NOT FOUND")
else:
    print("❌ Route 139 not found")

# 2. Check schedules for route 139
print("\n2️⃣  SCHEDULES FOR ROUTE 139")
print("-"*70)
cur.execute("""
    SELECT id, route_id, itinerary, periodicity, 
           jsonb_array_length(trips) as trip_count
    FROM schedules 
    WHERE route_id = '139'
""")
schedules = cur.fetchall()
print(f"Found {len(schedules)} schedules for route 139:")
for sched in schedules:
    sched_id, route_id, itinerary, periodicity, trip_count = sched
    print(f"  - {periodicity} ({itinerary}): {trip_count} trips")

# 3. Check if trips have the stops we need
print("\n3️⃣  CHECKING TRIPS DATA")
print("-"*70)
cur.execute("""
    SELECT periodicity, trips 
    FROM schedules 
    WHERE route_id = '139' 
    LIMIT 1
""")
result = cur.fetchone()
if result:
    periodicity, trips = result
    print(f"Periodicity: {periodicity}")
    print(f"Total trips: {len(trips)}")
    
    if trips and len(trips) > 0:
        first_trip = trips[0]
        print(f"\nFirst trip ID: {first_trip.get('trip_id')}")
        print(f"Stops in first trip: {len(first_trip.get('stops', []))}")
        
        # Check if our test stops are in the trip
        trip_stops = first_trip.get('stops', [])
        print("\nFirst 5 stops in trip:")
        for i, stop in enumerate(trip_stops[:5]):
            print(f"  {i}: {stop['stop']} at {stop['time']}")
        
        # Look for our test stops
        print("\nSearching for test stops in trip:")
        test_stop_names = [
            "COSENZA (Via Magna Grecia - Stadio)",
            "*COSENZA (Via Magna Grecia - Stadio)",
            "RENDE (Arcavacata-Piazza Cuticchia)"
        ]
        
        for test_name in test_stop_names:
            found = False
            for stop in trip_stops:
                if test_name.lower() in stop['stop'].lower():
                    print(f"  ✅ Found '{stop['stop']}' at {stop['time']}")
                    found = True
                    break
            if not found:
                print(f"  ❌ '{test_name}' not found")

# 4. Check departures for route 139
print("\n4️⃣  DEPARTURES FOR ROUTE 139")
print("-"*70)
cur.execute("""
    SELECT COUNT(*) 
    FROM departures 
    WHERE route_id = '139'
""")
count = cur.fetchone()[0]
print(f"Total departures for route 139: {count}")

# Check specific stops
test_stop_ids = [
    "*cosenza-(via-magna-grecia---stadio)",
    "rende-(arcavacata-piazza-cuticchia)"
]

for stop_id in test_stop_ids:
    cur.execute("""
        SELECT COUNT(*) 
        FROM departures 
        WHERE route_id = '139' AND stop_id = %s
    """, (stop_id,))
    count = cur.fetchone()[0]
    print(f"  {stop_id}: {count} departures")
    
    if count > 0:
        cur.execute("""
            SELECT departure_time, destination, periodicity
            FROM departures 
            WHERE route_id = '139' AND stop_id = %s
            LIMIT 3
        """, (stop_id,))
        deps = cur.fetchall()
        for dep in deps:
            print(f"    - {dep[0]} → {dep[1]} ({dep[2]})")

# 5. Check if stop IDs match between routes.stops_order and departures
print("\n5️⃣  CHECKING STOP ID CONSISTENCY")
print("-"*70)
cur.execute("SELECT stops_order FROM routes WHERE id = '139'")
route = cur.fetchone()
if route and route[0]:
    stops_order = route[0]
    stop_ids_in_route = [s['id'] for s in stops_order]
    
    # Get unique stop IDs from departures
    cur.execute("""
        SELECT DISTINCT stop_id 
        FROM departures 
        WHERE route_id = '139'
        LIMIT 10
    """)
    stop_ids_in_departures = [row[0] for row in cur.fetchall()]
    
    print(f"Stop IDs in route.stops_order (first 5): {stop_ids_in_route[:5]}")
    print(f"Stop IDs in departures (first 5): {stop_ids_in_departures[:5]}")
    
    # Check if they match
    matching = set(stop_ids_in_route) & set(stop_ids_in_departures)
    print(f"\nMatching stop IDs: {len(matching)} out of {len(stop_ids_in_route)}")

cur.close()
conn.close()

print("\n" + "="*70)
print("✅ CHECK COMPLETE")
print("="*70)
