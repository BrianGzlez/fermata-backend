#!/usr/bin/env python3
"""Check production database data for route 139."""

import psycopg2
import json

DB_URL = "postgresql://fermati_db_user:7oudj7InyxA6TfXmS4Mv0bL3zfrhJY9H@dpg-d6lj7ap5pdvs73fhgls0-a.oregon-postgres.render.com/fermati_db"

print("="*70)
print("🔍 CHECKING PRODUCTION DATABASE DATA")
print("="*70)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# 1. Check route 139 stops
print("\n1️⃣  ROUTE 139 STOPS")
print("-"*70)
cur.execute("SELECT id, name, stops_order FROM routes WHERE id = '139'")
route = cur.fetchone()
if route:
    route_id, route_name, stops_order = route
    print(f"Route: {route_name}")
    print(f"Total stops: {len(stops_order)}")
    
    stop_ids = [s['id'] for s in stops_order]
    
    # Check test stops
    test_stops = [
        "*cosenza-(via-magna-grecia---stadio)",
        "rende-(arcavacata-piazza-cuticchia)"
    ]
    
    for test_stop in test_stops:
        if test_stop in stop_ids:
            idx = stop_ids.index(test_stop)
            print(f"  ✅ {test_stop} at position {idx}")
        else:
            print(f"  ❌ {test_stop} NOT FOUND")

# 2. Check schedules
print("\n2️⃣  SCHEDULES FOR ROUTE 139")
print("-"*70)
cur.execute("""
    SELECT id, periodicity, trips 
    FROM schedules 
    WHERE route_id = '139'
""")
schedules = cur.fetchall()
print(f"Found {len(schedules)} schedules")

for sched_id, periodicity, trips in schedules:
    print(f"\n  Periodicity: {periodicity}")
    print(f"  Trips: {len(trips) if trips else 0}")
    
    if trips and len(trips) > 0:
        # Check first trip
        first_trip = trips[0]
        trip_stops = first_trip.get('stops', [])
        print(f"  First trip has {len(trip_stops)} stops")
        
        # Look for our test stops by name
        from_stop_found = False
        to_stop_found = False
        
        for stop in trip_stops:
            stop_name = stop['stop']
            if 'magna grecia' in stop_name.lower() and 'stadio' in stop_name.lower():
                print(f"    ✅ Found FROM stop: '{stop_name}' at {stop['time']}")
                from_stop_found = True
            if 'arcavacata' in stop_name.lower() and 'piazza' in stop_name.lower():
                print(f"    ✅ Found TO stop: '{stop_name}' at {stop['time']}")
                to_stop_found = True
        
        if not from_stop_found:
            print(f"    ❌ FROM stop not found in trip")
        if not to_stop_found:
            print(f"    ❌ TO stop not found in trip")

# 3. Check departures
print("\n3️⃣  DEPARTURES FOR ROUTE 139")
print("-"*70)
cur.execute("""
    SELECT COUNT(*) 
    FROM departures 
    WHERE route_id = '139'
""")
count = cur.fetchone()[0]
print(f"Total departures: {count}")

# Check specific stops
for stop_id in ["*cosenza-(via-magna-grecia---stadio)", "rende-(arcavacata-piazza-cuticchia)"]:
    cur.execute("""
        SELECT COUNT(*) 
        FROM departures 
        WHERE route_id = '139' AND stop_id = %s
    """, (stop_id,))
    count = cur.fetchone()[0]
    print(f"  {stop_id}: {count} departures")

# 4. Check stop ID format in trips vs departures
print("\n4️⃣  CHECKING STOP ID GENERATION")
print("-"*70)

# Get a sample trip
cur.execute("""
    SELECT trips 
    FROM schedules 
    WHERE route_id = '139' 
    LIMIT 1
""")
result = cur.fetchone()
if result and result[0]:
    trips = result[0]
    if len(trips) > 0:
        first_trip = trips[0]
        trip_stops = first_trip.get('stops', [])
        
        print("Sample stop names from trip and their generated IDs:")
        for stop in trip_stops[:5]:
            stop_name = stop['stop']
            # Generate ID same way as sync script
            generated_id = stop_name.lower().replace(" ", "-").replace("'", "").replace("\n", " ").replace("  ", " ").strip()
            print(f"  Name: {stop_name}")
            print(f"  Generated ID: {generated_id}")
            
            # Check if this ID exists in departures
            cur.execute("""
                SELECT COUNT(*) 
                FROM departures 
                WHERE stop_id = %s AND route_id = '139'
            """, (generated_id,))
            dep_count = cur.fetchone()[0]
            print(f"  Departures with this ID: {dep_count}")
            print()

cur.close()
conn.close()

print("="*70)
print("✅ CHECK COMPLETE")
print("="*70)
