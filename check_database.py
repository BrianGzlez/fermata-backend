#!/usr/bin/env python3
"""
Script to check database status and diagnose issues.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    print("Please set DATABASE_URL in your .env file")
    exit(1)

# Fix postgres:// to postgresql:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("=" * 60)
print("🔍 DATABASE DIAGNOSTIC TOOL")
print("=" * 60)

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("\n✅ Connected to database successfully!\n")
        
        # 1. Count departures
        print("1️⃣  CHECKING DEPARTURES TABLE")
        print("-" * 60)
        result = conn.execute(text("SELECT COUNT(*) FROM departures"))
        departures_count = result.scalar()
        print(f"   Total departures: {departures_count}")
        
        # 2. Count stops
        print("\n2️⃣  CHECKING STOPS TABLE")
        print("-" * 60)
        result = conn.execute(text("SELECT COUNT(*) FROM stops"))
        stops_count = result.scalar()
        print(f"   Total stops: {stops_count}")
        
        # 3. Count routes
        print("\n3️⃣  CHECKING ROUTES TABLE")
        print("-" * 60)
        result = conn.execute(text("SELECT COUNT(*) FROM routes"))
        routes_count = result.scalar()
        print(f"   Total routes: {routes_count}")
        
        # 4. Check departures table structure
        print("\n4️⃣  DEPARTURES TABLE STRUCTURE")
        print("-" * 60)
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'departures'
            ORDER BY ordinal_position
        """))
        print("   Columns:")
        for row in result:
            print(f"   - {row[0]}: {row[1]}")
        
        # 5. Sample departures data
        print("\n5️⃣  SAMPLE DEPARTURES DATA")
        print("-" * 60)
        result = conn.execute(text("SELECT * FROM departures LIMIT 3"))
        rows = result.fetchall()
        if rows:
            print(f"   Found {len(rows)} sample records:")
            for i, row in enumerate(rows, 1):
                print(f"\n   Record {i}:")
                for key, value in row._mapping.items():
                    print(f"     {key}: {value}")
        else:
            print("   ⚠️  No departures found!")
        
        # 6. Search for Cosenza stops
        print("\n6️⃣  SEARCHING FOR COSENZA STOPS")
        print("-" * 60)
        result = conn.execute(text("""
            SELECT DISTINCT stop_id 
            FROM departures 
            WHERE stop_id LIKE '%cosenza%' 
            LIMIT 10
        """))
        cosenza_stops = result.fetchall()
        if cosenza_stops:
            print(f"   Found {len(cosenza_stops)} Cosenza stops with departures:")
            for stop in cosenza_stops:
                print(f"   - {stop[0]}")
        else:
            print("   ⚠️  No Cosenza stops found in departures!")
        
        # 7. Check specific stop: *cosenza-(autostazione)
        print("\n7️⃣  CHECKING SPECIFIC STOP: *cosenza-(autostazione)")
        print("-" * 60)
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM departures 
            WHERE stop_id = '*cosenza-(autostazione)'
        """))
        count = result.scalar()
        print(f"   Departures for '*cosenza-(autostazione)': {count}")
        
        if count > 0:
            result = conn.execute(text("""
                SELECT route_id, departure_time, periodicity, destination
                FROM departures 
                WHERE stop_id = '*cosenza-(autostazione)'
                LIMIT 5
            """))
            print("   Sample departures:")
            for row in result:
                print(f"   - Route {row[0]}: {row[1]} ({row[2]}) → {row[3]}")
        
        # 8. Check without asterisk
        print("\n8️⃣  CHECKING WITHOUT ASTERISK: cosenza-(autostazione)")
        print("-" * 60)
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM departures 
            WHERE stop_id = 'cosenza-(autostazione)'
        """))
        count = result.scalar()
        print(f"   Departures for 'cosenza-(autostazione)': {count}")
        
        # 9. Check sync log
        print("\n9️⃣  CHECKING SYNC LOG")
        print("-" * 60)
        try:
            result = conn.execute(text("""
                SELECT sync_type, status, items_synced, started_at, completed_at
                FROM sync_logs
                ORDER BY started_at DESC
                LIMIT 5
            """))
            logs = result.fetchall()
            if logs:
                print("   Recent sync operations:")
                for log in logs:
                    print(f"   - {log[0]}: {log[1]} ({log[2]} items) at {log[3]}")
            else:
                print("   ⚠️  No sync logs found!")
        except Exception as e:
            print(f"   ⚠️  Could not read sync_logs table: {e}")
        
        # 10. Check all stops in database
        print("\n🔟  ALL STOPS IN DATABASE")
        print("-" * 60)
        result = conn.execute(text("""
            SELECT id, name 
            FROM stops 
            WHERE name LIKE '%Cosenza%' OR name LIKE '%COSENZA%'
            LIMIT 10
        """))
        stops = result.fetchall()
        if stops:
            print(f"   Found {len(stops)} Cosenza stops:")
            for stop in stops:
                print(f"   - ID: {stop[0]}")
                print(f"     Name: {stop[1]}")
        else:
            print("   ⚠️  No Cosenza stops found in stops table!")
        
        print("\n" + "=" * 60)
        print("✅ DIAGNOSTIC COMPLETE")
        print("=" * 60)
        
        # Summary
        print("\n📊 SUMMARY:")
        print(f"   Departures: {departures_count}")
        print(f"   Stops: {stops_count}")
        print(f"   Routes: {routes_count}")
        
        if departures_count == 0:
            print("\n⚠️  WARNING: No departures in database!")
            print("   Run: python sync_data.py --all")
        elif departures_count < 1000:
            print("\n⚠️  WARNING: Very few departures in database!")
            print("   Expected: 7000+ departures")
            print("   Run: python sync_data.py --all")
        else:
            print("\n✅ Database looks healthy!")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nTroubleshooting:")
    print("1. Check that DATABASE_URL is correct in .env")
    print("2. Verify database is accessible")
    print("3. Check network connection")
