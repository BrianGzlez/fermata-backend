#!/usr/bin/env python3
"""
Data synchronization script.

This script fetches data from the Consorzio website and stores it in the database.
Run this as a cron job to keep data updated.

Usage:
    python sync_data.py --all              # Sync everything
    python sync_data.py --stops            # Sync only stops
    python sync_data.py --routes           # Sync only routes
    python sync_data.py --schedules        # Sync only schedules
"""

import sys
import time
import argparse
from datetime import datetime
from sqlalchemy.orm import Session

from src.database import SessionLocal, init_db
from src.db_models import Stop, Route, Departure, Schedule, SyncLog
from src.services import ConsorzioService
from src.config import STOPS_COORDINATES
from src.utils import similarity

# Colors for terminal output
COLORS = {
    'green': '\033[92m',
    'yellow': '\033[93m',
    'red': '\033[91m',
    'blue': '\033[94m',
    'end': '\033[0m'
}


def log(message: str, color: str = None):
    """Print colored log message."""
    if color and color in COLORS:
        print(f"{COLORS[color]}{message}{COLORS['end']}")
    else:
        print(message)


def generate_stop_id(stop_name: str) -> str:
    """Generate consistent ID from stop name."""
    return stop_name.lower().replace(" ", "-").replace("'", "")


def generate_color(route_id: str) -> str:
    """Generate color for route."""
    colors = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"]
    try:
        index = int(route_id) % len(colors)
    except:
        index = 0
    return colors[index]


def sync_stops(db: Session, service: ConsorzioService) -> dict:
    """Sync all stops to database."""
    log("\n📍 Syncing stops...", "blue")
    start_time = time.time()
    
    try:
        # Build stops index from service
        stops_index = service._build_stops_index()
        
        synced = 0
        errors = []
        
        for stop_name, stop_info in stops_index.items():
            try:
                stop_id = generate_stop_id(stop_name)
                coords = stop_info.get("coordinates") or STOPS_COORDINATES.get(stop_name, {})
                
                # Check if stop exists
                db_stop = db.query(Stop).filter(Stop.id == stop_id).first()
                
                new_routes = stop_info.get("lines", [])
                new_lat = coords.get("lat")
                new_lon = coords.get("lon")
                
                if db_stop:
                    # Check if data changed
                    data_changed = (
                        db_stop.name != stop_name or
                        db_stop.routes != new_routes or
                        db_stop.latitude != new_lat or
                        db_stop.longitude != new_lon
                    )
                    
                    if data_changed:
                        db_stop.name = stop_name
                        db_stop.latitude = new_lat
                        db_stop.longitude = new_lon
                        db_stop.routes = new_routes
                        db_stop.updated_at = datetime.utcnow()
                        synced += 1
                    # else: skip, no changes
                else:
                    # Create new
                    db_stop = Stop(
                        id=stop_id,
                        name=stop_name,
                        latitude=new_lat,
                        longitude=new_lon,
                        routes=new_routes,
                        city="Cosenza",
                        region="Calabria"
                    )
                    db.add(db_stop)
                    synced += 1
                
            except Exception as e:
                errors.append(f"Error syncing stop {stop_name}: {str(e)}")
                log(f"  ❌ Error: {stop_name}", "red")
        
        db.commit()
        
        duration = time.time() - start_time
        log(f"✅ Synced {synced} stops in {duration:.2f}s", "green")
        
        return {
            "status": "success" if not errors else "partial",
            "synced": synced,
            "errors": errors,
            "duration": duration
        }
        
    except Exception as e:
        db.rollback()
        log(f"❌ Failed to sync stops: {str(e)}", "red")
        return {
            "status": "error",
            "synced": 0,
            "errors": [str(e)],
            "duration": time.time() - start_time
        }


def sync_routes(db: Session, service: ConsorzioService) -> dict:
    """Sync all routes to database."""
    log("\n🚌 Syncing routes...", "blue")
    start_time = time.time()
    
    try:
        lines = service.get_lines()
        
        synced_routes = 0
        errors = []
        
        for line in lines:
            try:
                route_id = line["value"]
                
                # Get stops for this route
                stops_order = []
                try:
                    itineraries = service.get_itineraries(route_id)
                    if itineraries:
                        first_itinerary = itineraries[0]["value"]
                        periodicities = service.get_periodicities(route_id, first_itinerary)
                        if periodicities:
                            first_periodicity = periodicities[0]["value"]
                            schedule = service.get_schedule(route_id, first_itinerary, first_periodicity)
                            stops_order = [
                                {"id": generate_stop_id(s["name"]), "name": s["name"], "order": idx}
                                for idx, s in enumerate(schedule.get("stops", []))
                            ]
                except:
                    pass
                
                # Check if route exists
                db_route = db.query(Route).filter(Route.id == route_id).first()
                
                # Generate new data
                new_name = line["label"]
                new_short_name = f"L{route_id}"
                new_color = generate_color(route_id)
                
                if db_route:
                    # Check if data changed
                    data_changed = (
                        db_route.name != new_name or
                        db_route.short_name != new_short_name or
                        db_route.stops_order != stops_order
                    )
                    
                    if data_changed:
                        db_route.name = new_name
                        db_route.short_name = new_short_name
                        db_route.color = new_color
                        db_route.stops_order = stops_order
                        db_route.updated_at = datetime.utcnow()
                        synced_routes += 1
                    # else: skip, no changes
                else:
                    # Create new
                    db_route = Route(
                        id=route_id,
                        name=new_name,
                        short_name=new_short_name,
                        color=new_color,
                        type="bus",
                        stops_order=stops_order
                    )
                    db.add(db_route)
                    synced_routes += 1
                    db.add(db_route)
                    synced_routes += 1
                
                log(f"  ✓ {route_id}: {line['label']}", "green")
                
            except Exception as e:
                errors.append(f"Error syncing route {line.get('value', 'unknown')}: {str(e)}")
                log(f"  ❌ Error: {line.get('value', 'unknown')}", "red")
        
        db.commit()
        
        duration = time.time() - start_time
        log(f"✅ Synced {synced_routes} routes in {duration:.2f}s", "green")
        
        return {
            "status": "success" if not errors else "partial",
            "synced": synced_routes,
            "errors": errors,
            "duration": duration
        }
        
    except Exception as e:
        db.rollback()
        log(f"❌ Failed to sync routes: {str(e)}", "red")
        return {
            "status": "error",
            "synced": 0,
            "errors": [str(e)],
            "duration": time.time() - start_time
        }


def sync_schedules(db: Session, service: ConsorzioService, limit: int = None) -> dict:
    """Sync schedules and departures to database."""
    log("\n📅 Syncing schedules...", "blue")
    start_time = time.time()
    
    try:
        lines = service.get_lines()
        if limit:
            lines = lines[:limit]
        
        synced_schedules = 0
        synced_departures = 0
        errors = []
        
        for line in lines:
            route_id = line["value"]
            log(f"\n  Processing route {route_id}...", "yellow")
            
            try:
                itineraries = service.get_itineraries(route_id)
                
                for itinerary in itineraries:
                    itinerary_value = itinerary["value"]
                    
                    try:
                        periodicities = service.get_periodicities(route_id, itinerary_value)
                        
                        for periodicity in periodicities:
                            periodicity_value = periodicity["value"]
                            
                            try:
                                # Get schedule
                                schedule_data = service.get_schedule(route_id, itinerary_value, periodicity_value)
                                
                                # Save schedule
                                db_schedule = db.query(Schedule).filter(
                                    Schedule.route_id == route_id,
                                    Schedule.itinerary == itinerary_value,
                                    Schedule.periodicity == periodicity_value
                                ).first()
                                
                                # Check if data changed
                                new_trips = schedule_data.get("trips", [])
                                new_stops = schedule_data.get("stops", [])
                                new_matrix = schedule_data.get("schedule_matrix", {})
                                new_metadata = schedule_data.get("metadata", {})
                                
                                if db_schedule:
                                    # Compare data to see if it changed
                                    data_changed = (
                                        db_schedule.trips != new_trips or
                                        db_schedule.stops != new_stops or
                                        db_schedule.schedule_matrix != new_matrix
                                    )
                                    
                                    if data_changed:
                                        db_schedule.trips = new_trips
                                        db_schedule.stops = new_stops
                                        db_schedule.schedule_matrix = new_matrix
                                        db_schedule.schedule_metadata = new_metadata
                                        db_schedule.updated_at = datetime.utcnow()
                                        synced_schedules += 1
                                    # else: skip, no changes
                                else:
                                    # New schedule, add it
                                    db_schedule = Schedule(
                                        route_id=route_id,
                                        itinerary=itinerary_value,
                                        periodicity=periodicity_value,
                                        direction=new_metadata.get("direction"),
                                        trips=new_trips,
                                        stops=new_stops,
                                        schedule_matrix=new_matrix,
                                        schedule_metadata=new_metadata
                                    )
                                    db.add(db_schedule)
                                    synced_schedules += 1
                                
                                # Save departures for each stop
                                for trip in schedule_data.get("trips", []):
                                    for stop_data in trip.get("stops", []):
                                        stop_name = stop_data["stop"]
                                        stop_id = generate_stop_id(stop_name)
                                        
                                        departure_id = f"{stop_id}-{route_id}-{trip['trip_id']}"
                                        
                                        db_departure = db.query(Departure).filter(
                                            Departure.id == departure_id
                                        ).first()
                                        
                                        destination = schedule_data.get("trips", [{}])[-1].get("stops", [{}])[-1].get("stop", "Unknown")
                                        
                                        if db_departure:
                                            db_departure.departure_time = stop_data["time"]
                                            db_departure.destination = destination
                                            db_departure.updated_at = datetime.utcnow()
                                        else:
                                            db_departure = Departure(
                                                id=departure_id,
                                                stop_id=stop_id,
                                                route_id=route_id,
                                                route_name=f"Línea {route_id}",
                                                destination=destination,
                                                departure_time=stop_data["time"],
                                                trip_id=trip["trip_id"],
                                                periodicity=periodicity_value,
                                                itinerary=itinerary_value
                                            )
                                            db.add(db_departure)
                                        
                                        synced_departures += 1
                                
                                log(f"    ✓ {periodicity_value}: {len(schedule_data.get('trips', []))} trips", "green")
                                
                            except Exception as e:
                                errors.append(f"Error syncing schedule {route_id}/{itinerary_value}/{periodicity_value}: {str(e)}")
                                log(f"    ❌ {periodicity_value}: {str(e)}", "red")
                    
                    except Exception as e:
                        errors.append(f"Error getting periodicities for {route_id}/{itinerary_value}: {str(e)}")
                
            except Exception as e:
                errors.append(f"Error processing route {route_id}: {str(e)}")
                log(f"  ❌ Route {route_id}: {str(e)}", "red")
        
        db.commit()
        
        duration = time.time() - start_time
        log(f"\n✅ Synced {synced_schedules} schedules and {synced_departures} departures in {duration:.2f}s", "green")
        
        return {
            "status": "success" if not errors else "partial",
            "synced": synced_schedules + synced_departures,
            "errors": errors,
            "duration": duration
        }
        
    except Exception as e:
        db.rollback()
        log(f"❌ Failed to sync schedules: {str(e)}", "red")
        return {
            "status": "error",
            "synced": 0,
            "errors": [str(e)],
            "duration": time.time() - start_time
        }


def main():
    """Main sync function."""
    parser = argparse.ArgumentParser(description="Sync Consorzio data to database")
    parser.add_argument("--all", action="store_true", help="Sync everything")
    parser.add_argument("--stops", action="store_true", help="Sync only stops")
    parser.add_argument("--routes", action="store_true", help="Sync only routes")
    parser.add_argument("--schedules", action="store_true", help="Sync only schedules")
    parser.add_argument("--limit", type=int, help="Limit number of routes to sync (for testing)")
    
    args = parser.parse_args()
    
    # If no specific sync type, sync all
    if not any([args.stops, args.routes, args.schedules]):
        args.all = True
    
    log("=" * 60, "blue")
    log("🚀 Starting data synchronization", "blue")
    log("=" * 60, "blue")
    
    # Initialize database
    init_db()
    
    # Create session
    db = SessionLocal()
    service = ConsorzioService()
    
    # Track overall sync
    sync_log = SyncLog(
        sync_type="all" if args.all else ",".join([
            k for k, v in vars(args).items() 
            if v is True and k in ["stops", "routes", "schedules"]
        ]),
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(sync_log)
    db.commit()
    
    total_synced = 0
    all_errors = []
    
    try:
        # Sync stops
        if args.all or args.stops:
            result = sync_stops(db, service)
            total_synced += result["synced"]
            all_errors.extend(result["errors"])
        
        # Sync routes
        if args.all or args.routes:
            result = sync_routes(db, service)
            total_synced += result["synced"]
            all_errors.extend(result["errors"])
        
        # Sync schedules
        if args.all or args.schedules:
            result = sync_schedules(db, service, limit=args.limit)
            total_synced += result["synced"]
            all_errors.extend(result["errors"])
        
        # Update sync log
        sync_log.status = "success" if not all_errors else "partial"
        sync_log.items_synced = total_synced
        sync_log.errors = all_errors[:100]  # Limit errors stored
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
        db.commit()
        
        log("\n" + "=" * 60, "blue")
        log(f"✅ Sync completed: {total_synced} items synced", "green")
        if all_errors:
            log(f"⚠️  {len(all_errors)} errors occurred", "yellow")
        log("=" * 60, "blue")
        
    except Exception as e:
        sync_log.status = "error"
        sync_log.errors = [str(e)]
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
        db.commit()
        
        log(f"\n❌ Sync failed: {str(e)}", "red")
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
