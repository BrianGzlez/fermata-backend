"""
Frontend-compatible API endpoints for Fermati application.

This module provides endpoints that match the exact structure expected by the
Next.js frontend, adapting the backend data to the required format.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Query

from .services import ConsorzioService
from .config import STOPS_COORDINATES
from .utils import similarity, calculate_distance, calculate_time_diff

logger = logging.getLogger(__name__)

# Create router for frontend API endpoints
router = APIRouter(prefix="/api", tags=["Frontend API"])

# Initialize service
service = ConsorzioService()


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
        "id": _generate_stop_id(stop_name),
        "name": stop_name,
        "latitude": coords.get("lat", 0.0),
        "longitude": coords.get("lon", 0.0),
        "routes": list(stop_info.get("lines", [])),
        "city": "Cosenza",
        "region": "Calabria"
    }


def _departure_to_frontend_format(departure: Dict, stop_id: str) -> Dict:
    """Convert backend departure format to frontend Departure format."""
    departure_time = departure.get("departure_time", "")
    
    # Calculate minutes until departure (simplified - would need current time)
    # For now, we'll leave it as None
    
    return {
        "id": f"{stop_id}-{departure.get('line_id', '')}-{departure.get('trip_id', '')}",
        "routeId": departure.get("line_id", ""),
        "routeName": f"Línea {departure.get('line_id', '')}",
        "destination": departure.get("destination", ""),
        "departureTime": departure_time,
        "estimatedTime": None,  # Would need real-time data
        "delay": None,
        "status": "on-time",  # Would need real-time data
        "platform": None,
        "realTime": False,  # Our data is scheduled, not real-time
        "periodicity": departure.get("periodicity_value", "F")
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
    limit: int = Query(10, description="Maximum results")
):
    """
    Search stops by name or location.
    
    Supports both text search and proximity-based search.
    """
    logger.info(f"Frontend API: search_stops - query={query}, lat={lat}, lng={lng}")
    
    stops = []
    
    # Proximity search
    if lat is not None and lng is not None:
        try:
            nearby = service.find_nearby_stops(lat, lng, radius, limit)
            stops = [_stop_to_frontend_format(item["stop"], item["stop"]["name"]) 
                    for item in nearby]
        except Exception as e:
            logger.error(f"Error in proximity search: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Text search
    elif query:
        try:
            results = service.search_stops(query, limit)
            stops = [_stop_to_frontend_format(stop, stop["name"]) for stop in results]
        except Exception as e:
            logger.error(f"Error in text search: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    else:
        raise HTTPException(
            status_code=400, 
            detail="Either 'query' or both 'lat' and 'lng' must be provided"
        )
    
    return {"stops": stops}


@router.get("/stops/{stop_id}")
def get_stop_by_id(stop_id: str):
    """
    Get detailed information about a specific stop.
    """
    logger.info(f"Frontend API: get_stop_by_id - {stop_id}")
    
    # Convert ID back to name (reverse of _generate_stop_id)
    stop_name = stop_id.replace("-", " ").upper()
    
    try:
        # Search for the stop
        results = service.search_stops(stop_name, limit=5)
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Stop with ID '{stop_id}' not found")
        
        # Find best match
        best_match = None
        best_score = 0
        
        for stop in results:
            score = similarity(_generate_stop_id(stop["name"]), stop_id)
            if score > best_score:
                best_score = score
                best_match = stop
        
        if best_match and best_score > 0.8:
            return _stop_to_frontend_format(best_match, best_match["name"])
        else:
            raise HTTPException(status_code=404, detail=f"Stop with ID '{stop_id}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stop by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stops/{stop_id}/departures")
def get_stop_departures(
    stop_id: str,
    limit: int = Query(10, description="Number of departures"),
    timeWindow: int = Query(60, description="Time window in minutes")
):
    """
    Get next departures from a specific stop.
    """
    logger.info(f"Frontend API: get_stop_departures - {stop_id}")
    
    # Convert ID to name
    stop_name = stop_id.replace("-", " ").upper()
    
    try:
        # Get departures
        departures_data = service.get_next_departures(stop_name, limit)
        
        # Convert to frontend format
        departures = [_departure_to_frontend_format(dep, stop_id) 
                     for dep in departures_data]
        
        return {
            "stopId": stop_id,
            "stopName": stop_name,
            "departures": departures,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting departures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Routes Endpoints

@router.get("/routes")
def get_all_routes():
    """
    Get all available bus routes/lines.
    """
    logger.info("Frontend API: get_all_routes")
    
    try:
        lines = service.get_lines()
        routes = [_route_to_frontend_format(line) for line in lines]
        
        return {"routes": routes}
        
    except Exception as e:
        logger.error(f"Error getting routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/{route_id}")
def get_route_details(route_id: str):
    """
    Get detailed information about a specific route/line.
    """
    logger.info(f"Frontend API: get_route_details - {route_id}")
    
    try:
        # Get itineraries for this line
        itineraries = service.get_itineraries(route_id)
        
        if not itineraries:
            raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found")
        
        # Get schedule for first itinerary to extract stops
        first_itinerary = itineraries[0]["value"]
        periodicities = service.get_periodicities(route_id, first_itinerary)
        
        if periodicities:
            first_periodicity = periodicities[0]["value"]
            schedule = service.get_schedule(route_id, first_itinerary, first_periodicity)
            
            # Extract stops in order
            stops_list = []
            for idx, stop in enumerate(schedule.get("stops", [])):
                stop_data = {
                    "id": _generate_stop_id(stop["name"]),
                    "name": stop["name"],
                    "order": idx
                }
                stops_list.append(stop_data)
            
            # Get line info
            lines = service.get_lines()
            line_info = next((l for l in lines if l["value"] == route_id), None)
            
            if line_info:
                route = _route_to_frontend_format(line_info, schedule.get("stops", []))
                route["stops"] = stops_list
                return route
        
        raise HTTPException(status_code=404, detail=f"Could not get details for route '{route_id}'")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting route details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/{route_id}/schedule")
def get_route_schedule(
    route_id: str,
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    stopId: str = Query(None, description="Filter by specific stop")
):
    """
    Get schedule for a specific route on a given date.
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
        # Get itineraries
        itineraries = service.get_itineraries(route_id)
        
        if not itineraries:
            raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found")
        
        # Get schedule for first itinerary with smart periodicity
        first_itinerary = itineraries[0]["value"]
        schedule = service.get_current_schedule(route_id, first_itinerary, target_date)
        
        # Build schedule response
        schedules = []
        
        for stop in schedule.get("stops", []):
            stop_name = stop["name"]
            stop_id_generated = _generate_stop_id(stop_name)
            
            # Filter by stopId if provided
            if stopId and stop_id_generated != stopId:
                continue
            
            # Get times for this stop
            times = []
            if stop_name in schedule.get("schedule_matrix", {}):
                stop_times = schedule["schedule_matrix"][stop_name]
                for trip_id, time in stop_times.items():
                    times.append({
                        "departureTime": time,
                        "periodicity": schedule.get("metadata", {}).get("selected_periodicity", "F"),
                        "realTime": False
                    })
            
            # Sort times
            times.sort(key=lambda x: x["departureTime"])
            
            schedules.append({
                "stopId": stop_id_generated,
                "stopName": stop_name,
                "times": times
            })
        
        # Get line info
        lines = service.get_lines()
        line_info = next((l for l in lines if l["value"] == route_id), None)
        route_name = line_info["label"] if line_info else f"Línea {route_id}"
        
        return {
            "routeId": route_id,
            "routeName": route_name,
            "date": target_date.isoformat(),
            "schedules": schedules
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting route schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/plan")
def plan_journey(
    from_stop: str = Query(..., alias="from", description="Origin stop ID"),
    to_stop: str = Query(..., alias="to", description="Destination stop ID"),
    time: str = Query(None, description="Desired departure time (ISO 8601)"),
    arriveBy: bool = Query(False, description="If true, 'time' is arrival time"),
    maxTransfers: int = Query(2, description="Maximum number of transfers"),
    modes: str = Query("bus", description="Transport modes (comma-separated)")
):
    """
    Calculate routes between two stops.
    """
    logger.info(f"Frontend API: plan_journey - from={from_stop}, to={to_stop}")
    
    # Convert IDs to names
    from_name = from_stop.replace("-", " ").upper()
    to_name = to_stop.replace("-", " ").upper()
    
    try:
        # Find routes
        routes = service.find_routes(from_name, to_name, limit=3)
        
        # Convert to Journey format
        journeys = []
        
        for idx, route in enumerate(routes):
            # Build legs
            legs = []
            
            for step in route.get("steps", []):
                # Get stop details
                from_stop_info = {"id": _generate_stop_id(step["from_stop"]), "name": step["from_stop"]}
                to_stop_info = {"id": _generate_stop_id(step["to_stop"]), "name": step["to_stop"]}
                
                # Get coordinates if available
                from_coords = STOPS_COORDINATES.get(step["from_stop"], {})
                to_coords = STOPS_COORDINATES.get(step["to_stop"], {})
                
                if from_coords:
                    from_stop_info.update({"latitude": from_coords["lat"], "longitude": from_coords["lon"]})
                if to_coords:
                    to_stop_info.update({"latitude": to_coords["lat"], "longitude": to_coords["lon"]})
                
                # Calculate distance if coordinates available
                distance = 0
                if from_coords and to_coords:
                    distance = calculate_distance(
                        from_coords["lat"], from_coords["lon"],
                        to_coords["lat"], to_coords["lon"]
                    )
                
                duration = calculate_time_diff(step["departure_time"], step["arrival_time"])
                
                leg = {
                    "type": "transit",
                    "routeId": step["line_id"],
                    "routeName": f"Línea {step['line_id']}",
                    "from": from_stop_info,
                    "to": to_stop_info,
                    "departureTime": step["departure_time"],
                    "arrivalTime": step["arrival_time"],
                    "duration": duration,
                    "distance": round(distance, 2),
                    "stops": []  # Could be populated with intermediate stops
                }
                
                legs.append(leg)
            
            # Calculate totals
            if legs:
                total_duration = route.get("total_time", 0)
                total_distance = sum(leg["distance"] for leg in legs)
                
                journey = {
                    "id": f"journey-{idx + 1}",
                    "origin": legs[0]["from"],
                    "destination": legs[-1]["to"],
                    "legs": legs,
                    "totalDuration": total_duration,
                    "totalDistance": round(total_distance, 2),
                    "departureTime": legs[0]["departureTime"],
                    "arrivalTime": legs[-1]["arrivalTime"],
                    "transfers": route.get("transfers", 0)
                }
                
                journeys.append(journey)
        
        return {
            "from": {"id": from_stop, "name": from_name},
            "to": {"id": to_stop, "name": to_name},
            "journeys": journeys,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error planning journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Alerts Endpoint

@router.get("/alerts")
def get_service_alerts(
    routeId: str = Query(None, description="Filter by route ID"),
    severity: str = Query(None, description="Filter by severity")
):
    """
    Get active service alerts.
    """
    logger.info(f"Frontend API: get_service_alerts - routeId={routeId}, severity={severity}")
    
    try:
        alerts_data = service.get_service_alerts(routeId)
        
        # Filter by severity if provided
        if severity:
            alerts_data = [a for a in alerts_data if a.get("severity") == severity]
        
        # Convert to frontend format
        alerts = []
        for alert in alerts_data:
            alerts.append({
                "id": alert.get("id", ""),
                "severity": alert.get("severity", "low"),
                "message": alert.get("message", ""),
                "affectedRoutes": alert.get("line_ids", []),
                "startTime": alert.get("created_at"),
                "endTime": None  # Would need to be added to backend data
            })
        
        return {
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
