"""
Database service for fast queries.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from .db_models import Stop, Route, Departure, Schedule, Alert
from .utils import similarity, calculate_distance

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for querying cached data from database."""
    
    def search_stops(
        self, 
        db: Session, 
        query: str = None, 
        lat: float = None, 
        lng: float = None, 
        radius: float = 2.0, 
        limit: int = 10
    ) -> List[Dict]:
        """Search stops by text or GPS coordinates."""
        
        # GPS search
        if lat is not None and lng is not None:
            stops = db.query(Stop).filter(
                Stop.latitude.isnot(None),
                Stop.longitude.isnot(None)
            ).all()
            
            # Calculate distances
            results = []
            for stop in stops:
                distance = calculate_distance(lat, lng, stop.latitude, stop.longitude)
                if distance <= radius:
                    results.append({
                        "stop": stop.to_dict(),
                        "distance": distance
                    })
            
            # Sort by distance
            results.sort(key=lambda x: x["distance"])
            return [r["stop"] for r in results[:limit]]
        
        # Text search
        if query:
            query_lower = query.lower()
            
            # Try exact match first
            stops = db.query(Stop).filter(
                or_(
                    func.lower(Stop.name).contains(query_lower),
                    func.lower(Stop.id).contains(query_lower)
                )
            ).limit(limit * 2).all()
            
            # Calculate similarity scores
            results = []
            for stop in stops:
                score = similarity(query, stop.name)
                if score > 0.3 or query_lower in stop.name.lower():
                    results.append({
                        "stop": stop.to_dict(),
                        "score": score + (0.5 if query_lower in stop.name.lower() else 0)
                    })
            
            # Sort by score
            results.sort(key=lambda x: x["score"], reverse=True)
            return [r["stop"] for r in results[:limit]]
        
        return []
    
    def get_stop(self, db: Session, stop_id: str) -> Optional[Dict]:
        """Get stop by ID."""
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        return stop.to_dict() if stop else None
    
    def get_departures(
        self, 
        db: Session, 
        stop_id: str, 
        limit: int = 10,
        periodicity: str = None
    ) -> List[Dict]:
        """Get next departures from a stop."""
        query = db.query(Departure).filter(Departure.stop_id == stop_id)
        
        if periodicity:
            query = query.filter(Departure.periodicity == periodicity)
        
        departures = query.order_by(Departure.departure_time).limit(limit * 2).all()
        
        # Convert to dict and sort by time
        results = [d.to_dict() for d in departures]
        results.sort(key=lambda x: x["departureTime"])
        
        return results[:limit]
    
    def get_all_routes(self, db: Session) -> List[Dict]:
        """Get all routes."""
        routes = db.query(Route).all()
        return [r.to_dict() for r in routes]
    
    def get_route(self, db: Session, route_id: str) -> Optional[Dict]:
        """Get route by ID with stops."""
        route = db.query(Route).filter(Route.id == route_id).first()
        return route.to_dict() if route else None
    
    def get_route_schedule(
        self, 
        db: Session, 
        route_id: str, 
        target_date: date = None,
        stop_id: str = None
    ) -> Optional[Dict]:
        """Get schedule for a route."""
        if target_date is None:
            target_date = date.today()
        
        # Determine periodicity based on date
        is_weekend = target_date.weekday() >= 5
        month = target_date.month
        
        # Priority order for periodicity
        if is_weekend:
            periodicity_priority = ["FEST", "F"]
        elif month == 8:
            periodicity_priority = ["EST", "F"]
        elif month >= 9 or month <= 6:
            periodicity_priority = ["SCO", "F"]
        else:
            periodicity_priority = ["F"]
        
        # Try to find schedule with preferred periodicity
        schedule = None
        for periodicity in periodicity_priority:
            schedule = db.query(Schedule).filter(
                Schedule.route_id == route_id,
                Schedule.periodicity == periodicity
            ).first()
            if schedule:
                break
        
        if not schedule:
            # Fallback to any schedule
            schedule = db.query(Schedule).filter(
                Schedule.route_id == route_id
            ).first()
        
        if not schedule:
            return None
        
        # Build response
        schedules = []
        for stop in schedule.stops:
            stop_name = stop["name"]
            stop_id_generated = stop_name.lower().replace(" ", "-").replace("'", "")
            
            # Filter by stop if requested
            if stop_id and stop_id_generated != stop_id:
                continue
            
            # Get times for this stop
            times = []
            if stop_name in schedule.schedule_matrix:
                stop_times = schedule.schedule_matrix[stop_name]
                for trip_id, time in stop_times.items():
                    times.append({
                        "departureTime": time,
                        "periodicity": schedule.periodicity,
                        "realTime": False
                    })
            
            # Sort times
            times.sort(key=lambda x: x["departureTime"])
            
            schedules.append({
                "stopId": stop_id_generated,
                "stopName": stop_name,
                "times": times
            })
        
        # Get route info
        route = db.query(Route).filter(Route.id == route_id).first()
        route_name = route.name if route else f"Línea {route_id}"
        
        return {
            "routeId": route_id,
            "routeName": route_name,
            "date": target_date.isoformat(),
            "schedules": schedules
        }
    
    def plan_route(
        self, 
        db: Session, 
        from_stop_id: str, 
        to_stop_id: str, 
        limit: int = 3
    ) -> List[Dict]:
        """Find routes between two stops."""
        # Get all routes
        routes = db.query(Route).all()
        
        results = []
        
        for route in routes:
            # Check if both stops are in this route
            stop_ids = [s["id"] for s in route.stops_order]
            
            if from_stop_id in stop_ids and to_stop_id in stop_ids:
                from_idx = stop_ids.index(from_stop_id)
                to_idx = stop_ids.index(to_stop_id)
                
                # Only if from comes before to
                if from_idx < to_idx:
                    # Get schedule to find times
                    schedule = db.query(Schedule).filter(
                        Schedule.route_id == route.id
                    ).first()
                    
                    if schedule and schedule.trips:
                        # Find trips that go through both stops
                        for trip in schedule.trips:
                            from_time = None
                            to_time = None
                            
                            for stop in trip["stops"]:
                                stop_name = stop["stop"]
                                stop_id = stop_name.lower().replace(" ", "-").replace("'", "")
                                
                                if stop_id == from_stop_id:
                                    from_time = stop["time"]
                                elif stop_id == to_stop_id and from_time:
                                    to_time = stop["time"]
                                    break
                            
                            if from_time and to_time:
                                results.append({
                                    "route": route,
                                    "from_time": from_time,
                                    "to_time": to_time,
                                    "trip_id": trip["trip_id"]
                                })
        
        return results[:limit]
    
    def get_alerts(
        self, 
        db: Session, 
        route_id: str = None, 
        severity: str = None
    ) -> List[Dict]:
        """Get service alerts."""
        query = db.query(Alert).filter(Alert.active == 1)
        
        if route_id:
            query = query.filter(Alert.affected_routes.contains([route_id]))
        
        if severity:
            query = query.filter(Alert.severity == severity)
        
        alerts = query.all()
        return [a.to_dict() for a in alerts]
