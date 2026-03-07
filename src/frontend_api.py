"""
Frontend-compatible API endpoints for Fermati application.

This module provides endpoints that match the exact structure expected by the
Next.js frontend, adapting the backend data to the required format.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from .database import get_db
from .db_service import DatabaseService
from .config import STOPS_COORDINATES
from .utils import similarity, calculate_distance, calculate_time_diff

logger = logging.getLogger(__name__)

# Create router for frontend API endpoints
router = APIRouter(prefix="/api", tags=["Frontend API"])

# Initialize database service
db_service = DatabaseService()


def _generate_stop_id(stop_name: str) -> str:
    """Generate a consistent ID from stop name."""
    # Use lowercase, replace spaces with hyphens
    return stop_name.lower().replace(" ", "-").replace("'", "")


def _stop_to_frontend_format(stop_info: Dict, stop_name: str = None) -> Dict:
    """Convert backend stop format to frontend BusStop format."""
    if stop_name is None:
        stop_name = stop_info.get("name", "")
    
    coords = stop_info.get("coordinates") or STOPS_COORDINATES.get(stop_name, {})
    
    return {
        "id": stop_info.get("id", _generate_stop_id(stop_name)),
        "name": stop_name,
        "latitude": stop_info.get("latitude") or coords.get("lat", 0.0),
        "longitude": stop_info.get("longitude") or coords.get("lon", 0.0),
        "routes": stop_info.get("routes", []),
        "city": stop_info.get("city", "Cosenza"),
        "region": stop_info.get("region", "Calabria")
    }


def _departure_to_frontend_format(departure: Dict, stop_id: str) -> Dict:
    """Convert backend departure format to frontend Departure format."""
    departure_time = departure.get("departureTime", "")
    
    # Calculate minutes until departure (simplified - would need current time)
    # For now, we'll leave it as None
    
    return {
        "id": f"{stop_id}-{departure.get('routeId', '')}-{departure.get('tripId', '')}",
        "routeId": departure.get("routeId", ""),
        "routeName": f"Línea {departure.get('routeId', '')}",
        "destination": departure.get("destination", ""),
        "departureTime": departure_time,
        "estimatedTime": None,  # Would need real-time data
        "delay": None,
        "status": "on-time",  # Would need real-time data
        "platform": None,
        "realTime": False,  # Our data is scheduled, not real-time
        "periodicity": departure.get("periodicity", "F")
    }


def _route_to_frontend_format(line: Dict, stops: List[Dict] = None) -> Dict:
    """Convert backend line format to frontend Route format."""
    line_id = line.get("value", "")
    
    # Generate color based on line ID (simple hash-based color)
    colors = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"]
    color_index = int(line_id) % len(colors) if line_id.isdigit() else 0
    
    return {
        "id": line_id,
        "name": line.get("label", f"Línea {line_id}"),
        "shortName": f"L{line_id}",
        "color": colors[color_index],
        "type": "bus",
        "stops": [_generate_stop_id(s["name"]) for s in (stops or [])]
    }


# ---------------------------------------------------------------------------
# Stops Endpoints

@router.get("/stops/search")
def search_stops(
    query: str = Query(None, description="Search text"),
    lat: float = Query(None, description="Latitude for proximity search"),
    lng: float = Query(None, description="Longitude for proximity search"),
    radius: float = Query(2.0, description="Search radius in km"),
    limit: int = Query(10, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Search stops by name or location.
    
    Supports both text search and proximity-based search.
    """
    logger.info(f"Frontend API: search_stops - query={query}, lat={lat}, lng={lng}")
    
    try:
        results = db_service.search_stops(db, query, lat, lng, radius, limit)
        stops = [_stop_to_frontend_format(stop, stop["name"]) for stop in results]
        return {"stops": stops}
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stops/{stop_id}")
def get_stop_by_id(stop_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific stop.
    """
    logger.info(f"Frontend API: get_stop_by_id - {stop_id}")
    
    try:
        stop = db_service.get_stop(db, stop_id)
        
        if not stop:
            raise HTTPException(status_code=404, detail=f"Stop with ID '{stop_id}' not found")
        
        return _stop_to_frontend_format(stop, stop["name"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stop by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stops/{stop_id}/departures")
def get_stop_departures(
    stop_id: str,
    limit: int = Query(10, description="Number of departures"),
    timeWindow: int = Query(60, description="Time window in minutes"),
    db: Session = Depends(get_db)
):
    """
    Get next departures from a specific stop.
    Handles late night (after 11 PM) by showing tomorrow's early buses.
    Uses Italy timezone (Europe/Rome) for current time.
    """
    logger.info(f"Frontend API: get_stop_departures - {stop_id}")
    
    try:
        from datetime import datetime
        import pytz
        
        # Get stop info
        stop = db_service.get_stop(db, stop_id)
        if not stop:
            raise HTTPException(status_code=404, detail=f"Stop '{stop_id}' not found")
        
        # Get current time in Italy timezone (Europe/Rome)
        italy_tz = pytz.timezone('Europe/Rome')
        now_italy = datetime.now(italy_tz)
        current_time = now_italy.strftime("%H:%M")
        
        # Get departures (handles late night automatically)
        departures_data = db_service.get_departures(
            db, 
            stop_id, 
            limit,
            after_time=current_time
        )
        
        # Convert to frontend format
        departures = [_departure_to_frontend_format(dep, stop_id) 
                     for dep in departures_data]
        
        return {
            "stopId": stop_id,
            "stopName": stop["name"],
            "departures": departures,
            "timestamp": now_italy.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting departures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Routes Endpoints

@router.get("/routes")
def get_all_routes(db: Session = Depends(get_db)):
    """
    Get all available bus routes/lines.
    """
    logger.info("Frontend API: get_all_routes")
    
    try:
        routes_data = db_service.get_all_routes(db)
        routes = [_route_to_frontend_format({"value": r["id"], "label": r["name"]}) for r in routes_data]
        
        return {"routes": routes}
        
    except Exception as e:
        logger.error(f"Error getting routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/plan")
def plan_journey(
    from_stop: str = Query(..., alias="from", description="Origin stop ID"),
    to_stop: str = Query(..., alias="to", description="Destination stop ID"),
    time: str = Query(None, description="Desired departure time (ISO 8601)"),
    arriveBy: bool = Query(False, description="If true, 'time' is arrival time"),
    maxTransfers: int = Query(2, description="Maximum number of transfers"),
    modes: str = Query("bus", description="Transport modes (comma-separated)"),
    db: Session = Depends(get_db)
):
    """
    Calculate routes between two stops, including routes with transfers.
    
    This endpoint finds:
    - Direct routes (no transfers)
    - Routes with 1 transfer (change bus once)
    - Routes with 2 transfers (change bus twice)
    """
    logger.info(f"Frontend API: plan_journey - from={from_stop}, to={to_stop}, maxTransfers={maxTransfers}")
    
    try:
        # Get origin and destination info first (outside loop)
        origin_obj = db_service.get_stop(db, from_stop)
        destination_obj = db_service.get_stop(db, to_stop)
        
        origin_info = {
            "id": from_stop,
            "name": origin_obj["name"] if origin_obj else from_stop,
            "latitude": origin_obj.get("latitude", 0) if origin_obj else 0,
            "longitude": origin_obj.get("longitude", 0) if origin_obj else 0
        }
        
        destination_info = {
            "id": to_stop,
            "name": destination_obj["name"] if destination_obj else to_stop,
            "latitude": destination_obj.get("latitude", 0) if destination_obj else 0,
            "longitude": destination_obj.get("longitude", 0) if destination_obj else 0
        }
        
        # Find routes with transfers
        journeys_data = db_service.plan_route_with_transfers(
            db, from_stop, to_stop, maxTransfers, limit=5
        )
        
        # Convert to Journey format
        journeys = []
        
        for idx, journey_data in enumerate(journeys_data):
            legs_list = []
            total_duration = 0
            total_distance = 0
            
            departure_time = None
            arrival_time = None
            
            for leg_idx, leg in enumerate(journey_data["legs"]):
                route = leg["route"]
                from_time = leg["from_time"]
                to_time = leg["to_time"]
                
                if leg_idx == 0:
                    departure_time = from_time
                if leg_idx == len(journey_data["legs"]) - 1:
                    arrival_time = to_time
                
                # Get stop details
                from_stop_obj = db_service.get_stop(db, leg["from_stop_id"])
                to_stop_obj = db_service.get_stop(db, leg["to_stop_id"])
                
                from_stop_info = {
                    "id": leg["from_stop_id"],
                    "name": from_stop_obj["name"] if from_stop_obj else leg["from_stop_id"],
                    "latitude": from_stop_obj.get("latitude", 0) if from_stop_obj else 0,
                    "longitude": from_stop_obj.get("longitude", 0) if from_stop_obj else 0
                }
                
                to_stop_info = {
                    "id": leg["to_stop_id"],
                    "name": to_stop_obj["name"] if to_stop_obj else leg["to_stop_id"],
                    "latitude": to_stop_obj.get("latitude", 0) if to_stop_obj else 0,
                    "longitude": to_stop_obj.get("longitude", 0) if to_stop_obj else 0
                }
                
                # Calculate distance
                distance = 0
                if from_stop_info["latitude"] and to_stop_info["latitude"]:
                    distance = calculate_distance(
                        from_stop_info["latitude"], from_stop_info["longitude"],
                        to_stop_info["latitude"], to_stop_info["longitude"]
                    )
                
                duration = calculate_time_diff(from_time, to_time)
                total_duration += duration
                total_distance += distance
                
                leg_formatted = {
                    "type": "transit",
                    "routeId": route.id,
                    "routeName": route.name,
                    "from": from_stop_info,
                    "to": to_stop_info,
                    "departureTime": from_time,
                    "arrivalTime": to_time,
                    "duration": duration,
                    "distance": round(distance, 2),
                    "stops": []
                }
                
                legs_list.append(leg_formatted)
            
            journey = {
                "id": f"journey-{idx + 1}",
                "origin": origin_info,
                "destination": destination_info,
                "legs": legs_list,
                "totalDuration": total_duration,
                "totalDistance": round(total_distance, 2),
                "departureTime": departure_time,
                "arrivalTime": arrival_time,
                "transfers": journey_data["transfers"]
            }
            
            journeys.append(journey)
        
        return {
            "from": {"id": from_stop, "name": origin_info["name"]},
            "to": {"id": to_stop, "name": destination_info["name"]},
            "journeys": journeys,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error planning journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/{route_id}")
def get_route_details(route_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific route/line.
    """
    logger.info(f"Frontend API: get_route_details - {route_id}")
    
    try:
        route_data = db_service.get_route(db, route_id)
        
        if not route_data:
            raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found")
        
        # Extract stops in order
        stops_list = []
        for idx, stop in enumerate(route_data.get("stops", [])):
            stop_data = {
                "id": stop["id"],
                "name": stop["name"],
                "order": idx
            }
            stops_list.append(stop_data)
        
        route = _route_to_frontend_format(
            {"value": route_data["id"], "label": route_data["name"]},
            route_data.get("stops", [])
        )
        route["stops"] = stops_list
        return route
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting route details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/{route_id}/schedule")
def get_route_schedule(
    route_id: str,
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    stopId: str = Query(None, description="Filter by specific stop"),
    db: Session = Depends(get_db)
):
    """
    Get schedule for a specific route on a given date.
    Returns 200 with empty schedules array if no data found.
    """
    logger.info(f"Frontend API: get_route_schedule - {route_id}, date={date}, stopId={stopId}")
    
    # Parse date
    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
    
    try:
        schedule = db_service.get_route_schedule(db, route_id, target_date, stopId)
        
        if not schedule:
            # Return empty schedule instead of 404
            route_data = db_service.get_route(db, route_id)
            route_name = route_data["name"] if route_data else f"Línea {route_id}"
            
            return {
                "routeId": route_id,
                "routeName": route_name,
                "date": target_date.isoformat(),
                "schedules": []
            }
        
        return schedule
        
    except Exception as e:
        logger.error(f"Error getting route schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# ---------------------------------------------------------------------------
# Alerts Endpoint

@router.get("/alerts")
def get_service_alerts(
    routeId: str = Query(None, description="Filter by route ID"),
    severity: str = Query(None, description="Filter by severity"),
    db: Session = Depends(get_db)
):
    """
    Get active service alerts.
    """
    logger.info(f"Frontend API: get_service_alerts - routeId={routeId}, severity={severity}")
    
    try:
        alerts_data = db_service.get_alerts(db, routeId, severity)
        
        # Convert to frontend format
        alerts = []
        for alert in alerts_data:
            alerts.append({
                "id": alert.get("id", ""),
                "severity": alert.get("severity", "low"),
                "message": alert.get("message", ""),
                "affectedRoutes": alert.get("affectedRoutes", []),
                "startTime": alert.get("createdAt"),
                "endTime": None
            })
        
        return {
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stops/normalize/{stop_id}")
def normalize_stop_id(stop_id: str, db: Session = Depends(get_db)):
    """
    Normalize a stop ID by finding the correct version (with or without asterisk).
    
    This endpoint helps the frontend handle stop IDs that may or may not have
    an asterisk prefix.
    """
    logger.info(f"Frontend API: normalize_stop_id - {stop_id}")
    
    try:
        # Try to find the stop with normalization
        stop = db_service.get_stop(db, stop_id)
        
        if not stop:
            raise HTTPException(status_code=404, detail=f"Stop '{stop_id}' not found")
        
        return {
            "originalId": stop_id,
            "normalizedId": stop["id"],
            "name": stop["name"],
            "hasAsterisk": stop["id"].startswith("*")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error normalizing stop ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/direct-routes")
def get_direct_routes(
    from_stop: str = Query(..., alias="from", description="Origin stop ID"),
    to_stop: str = Query(..., alias="to", description="Destination stop ID"),
    limit: int = Query(20, description="Maximum number of departures"),
    timeWindow: int = Query(60, description="Time window in minutes"),
    db: Session = Depends(get_db)
):
    """
    Get direct routes between two stops (no transfers required).
    
    Only returns departures where the route passes through both stops
    in the correct order (from → to).
    """
    logger.info(f"Frontend API: get_direct_routes - from={from_stop}, to={to_stop}")
    
    try:
        # Get stop info
        from_stop_obj = db_service.get_stop(db, from_stop)
        to_stop_obj = db_service.get_stop(db, to_stop)
        
        if not from_stop_obj:
            raise HTTPException(status_code=404, detail=f"Origin stop '{from_stop}' not found")
        if not to_stop_obj:
            raise HTTPException(status_code=404, detail=f"Destination stop '{to_stop}' not found")
        
        # Get direct routes
        direct_routes = db_service.get_direct_routes(
            db, 
            from_stop_obj["id"],  # Use normalized ID
            to_stop_obj["id"],    # Use normalized ID
            limit,
            timeWindow
        )
        
        # Convert to frontend format
        departures = []
        for route_data in direct_routes:
            departure = {
                "id": f"{route_data['route_id']}-{route_data['trip_id']}-{route_data['from_time']}",
                "routeId": route_data["route_id"],
                "routeName": route_data["route_name"],
                "destination": route_data["destination"],
                "departureTime": route_data["from_time"],
                "arrivalTime": route_data["to_time"],
                "status": "on-time",
                "delay": 0,
                "periodicity": route_data["periodicity"],
                "stopSequence": {
                    "fromIndex": route_data["from_index"],
                    "toIndex": route_data["to_index"],
                    "totalStops": route_data["total_stops"],
                    "intermediateStops": route_data["to_index"] - route_data["from_index"] - 1
                },
                "estimatedDuration": calculate_time_diff(route_data["from_time"], route_data["to_time"])
            }
            departures.append(departure)
        
        return {
            "from": {
                "id": from_stop_obj["id"],
                "name": from_stop_obj["name"]
            },
            "to": {
                "id": to_stop_obj["id"],
                "name": to_stop_obj["name"]
            },
            "departures": departures,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "count": len(departures)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting direct routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
