"""
Quick test script to verify database setup.
"""

import os
from src.database import init_db, SessionLocal
from src.db_models import Stop, Route, Departure, Schedule, Alert, SyncLog

def test_database():
    """Test database connection and tables."""
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialized")
    
    print("\n📊 Checking tables...")
    db = SessionLocal()
    try:
        # Count records in each table
        stops_count = db.query(Stop).count()
        routes_count = db.query(Route).count()
        departures_count = db.query(Departure).count()
        schedules_count = db.query(Schedule).count()
        alerts_count = db.query(Alert).count()
        syncs_count = db.query(SyncLog).count()
        
        print(f"  Stops: {stops_count}")
        print(f"  Routes: {routes_count}")
        print(f"  Departures: {departures_count}")
        print(f"  Schedules: {schedules_count}")
        print(f"  Alerts: {alerts_count}")
        print(f"  Sync Logs: {syncs_count}")
        
        if stops_count == 0:
            print("\n⚠️  Database is empty. Run: python sync_data.py --all")
        else:
            print("\n✅ Database has data!")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_database()
