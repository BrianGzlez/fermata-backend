#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://fermati_db_user:7oudj7InyxA6TfXmS4Mv0bL3zfrhJY9H@dpg-d6lj7ap5pdvs73fhgls0-a.oregon-postgres.render.com/fermati_db"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check periodicities for Cosenza Autostazione
    result = conn.execute(text("""
        SELECT DISTINCT periodicity, COUNT(*) as count
        FROM departures 
        WHERE stop_id = '*cosenza-(autostazione)'
        GROUP BY periodicity
        ORDER BY periodicity
    """))
    
    print("Periodicidades disponibles para *cosenza-(autostazione):")
    for row in result:
        print(f"  {row[0]}: {row[1]} departures")
    
    print("\n" + "="*60)
    
    # Check what happens with FEST
    result = conn.execute(text("""
        SELECT route_id, departure_time, periodicity
        FROM departures 
        WHERE stop_id = '*cosenza-(autostazione)'
        AND periodicity = 'FEST'
        ORDER BY departure_time
        LIMIT 10
    """))
    
    rows = list(result)
    print(f"\nDepartures con FEST: {len(rows)}")
    if rows:
        for row in rows:
            print(f"  Route {row[0]}: {row[1]} ({row[2]})")
    
    # Check what happens with F
    result = conn.execute(text("""
        SELECT route_id, departure_time, periodicity
        FROM departures 
        WHERE stop_id = '*cosenza-(autostazione)'
        AND periodicity = 'F'
        ORDER BY departure_time
        LIMIT 10
    """))
    
    rows = list(result)
    print(f"\nDepartures con F: {len(rows)}")
    if rows:
        for row in rows:
            print(f"  Route {row[0]}: {row[1]} ({row[2]})")
