#!/usr/bin/env python3
import psycopg2

DB_URL = "postgresql://fermati_db_user:7oudj7InyxA6TfXmS4Mv0bL3zfrhJY9H@dpg-d6lj7ap5pdvs73fhgls0-a.oregon-postgres.render.com/fermati_db"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

print("Checking trip_ids for route 139...")

# Get trip_ids from Arcavacata stop
cur.execute("""
    SELECT DISTINCT trip_id, periodicity, departure_time
    FROM departures
    WHERE route_id = '139' AND stop_id = 'rende-(arcavacata-piazza-cuticchia)'
    ORDER BY departure_time
    LIMIT 5
""")
arcavacata_trips = cur.fetchall()

print(f"\nTrips from Arcavacata ({len(arcavacata_trips)}):")
for trip_id, periodicity, time in arcavacata_trips:
    print(f"  {trip_id} ({periodicity}) at {time}")
    
    # Check if this trip also stops at Cosenza Stadio
    cur.execute("""
        SELECT departure_time
        FROM departures
        WHERE route_id = '139' 
          AND stop_id = '*cosenza-(via-magna-grecia---stadio)'
          AND trip_id = %s
          AND periodicity = %s
    """, (trip_id, periodicity))
    
    cosenza_dep = cur.fetchone()
    if cosenza_dep:
        print(f"    ✅ Also stops at Cosenza Stadio at {cosenza_dep[0]}")
    else:
        print(f"    ❌ Does NOT stop at Cosenza Stadio")

cur.close()
conn.close()
