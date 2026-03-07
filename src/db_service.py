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
        """Get stop by ID, handling asterisk variations."""
        # Try exact match first
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        
        # If not found and doesn't have asterisk, try with asterisk
        if not stop and not stop_id.startswith("*"):
            stop = db.query(Stop).filter(Stop.id == f"*{stop_id}").first()
        
        # If not found and has asterisk, try without asterisk
        if not stop and stop_id.startswith("*"):
            stop = db.query(Stop).filter(Stop.id == stop_id[1:]).first()
        
        return stop.to_dict() if stop else None
    
    def get_departures(
        self, 
        db: Session, 
        stop_id: str, 
        limit: int = 10,
        periodicity: str = None,
        after_time: str = None
    ) -> List[Dict]:
        """Get next departures from a stop, handling late night (after 11 PM) and asterisk variations."""
        from datetime import datetime, time as dt_time
        
        # Normalize stop_id - try with and without asterisk
        base_query = db.query(Departure).filter(
            or_(
                Departure.stop_id == stop_id,
                Departure.stop_id == f"*{stop_id}",
                Departure.stop_id == stop_id[1:] if stop_id.startswith("*") else None
            )
        )
        
        # Determine periodicity if not provided
        if not periodicity:
            now = datetime.now()
            is_weekend = now.weekday() >= 5  # 5=Saturday, 6=Sunday
            is_sunday = now.weekday() == 6
            month = now.month
            
            # Priority order for periodicity selection based on Consorzio rules
            if is_sunday:
                # Sundays: use DF (Domenica/Festivo) - fewer buses
                periodicity = "DF"
            elif is_weekend:
                # Saturdays: use F (Feriale) - more buses than Sunday, less than weekdays
                periodicity = "F"
            elif month == 8:
                # August: try NS (Non Scolastico), then F
                periodicity = "NS"
            elif month >= 9 or month <= 6:
                # School period (Sept-June): try S (Scolastico), then F
                periodicity = "S"
            else:
                # Non-school period (July): try NS, then F
                periodicity = "NS"
        
        # Try with preferred periodicity first
        query = base_query.filter(Departure.periodicity == periodicity)
        
        # Handle late night (after 11 PM) - show tomorrow's early morning buses
        if after_time:
            current_hour = int(after_time.split(":")[0])
            if current_hour >= 23:
                # Show buses from 06:00 to 09:00 next day
                query = query.filter(
                    Departure.departure_time >= "06:00",
                    Departure.departure_time <= "09:00"
                )
            else:
                # Show buses after current time
                query = query.filter(Departure.departure_time >= after_time)
        
        departures = query.order_by(Departure.departure_time).limit(limit * 2).all()
        
        # If no departures found after current time, get first departures of the day
        if not departures and after_time:
            query = base_query.filter(Departure.periodicity == periodicity)
            departures = query.order_by(Departure.departure_time).limit(limit * 2).all()
        
        # If still no departures with preferred periodicity, try fallback periodicities
        if not departures:
            # Fallback order depends on day
            now = datetime.now()
            is_sunday = now.weekday() == 6
            
            if is_sunday:
                # Sunday: try F as fallback
                fallback_periodicities = ["F", "NS"]
            else:
                # Other days: try F as fallback
                fallback_periodicities = ["F", "DF"]
            
            for fallback_per in fallback_periodicities:
                query = base_query.filter(Departure.periodicity == fallback_per)
                if after_time:
                    current_hour = int(after_time.split(":")[0])
                    if current_hour < 23:
                        query = query.filter(Departure.departure_time >= after_time)
                departures = query.order_by(Departure.departure_time).limit(limit * 2).all()
                if departures:
                    break
        
        # Last resort: get any departures without time filter
        if not departures:
            departures = base_query.order_by(Departure.departure_time).limit(limit * 2).all()
        
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
        """Get schedule for a route with smart periodicity selection."""
        if target_date is None:
            target_date = date.today()
        
        # Determine periodicity based on date and time
        is_weekend = target_date.weekday() >= 5
        is_sunday = target_date.weekday() == 6
        month = target_date.month
        day = target_date.day
        
        # Check if it's school period (Sept 10 - June 30, excluding August)
        is_school_period = (month >= 9 or month <= 6) and month != 8
        
        # Priority order for periodicity based on Consorzio rules
        if is_sunday:
            # Sundays and holidays - use DF (Domenica/Festivo)
            periodicity_priority = ["DF", "F"]
        elif is_weekend:
            # Saturdays - use F (Feriale)
            periodicity_priority = ["F", "DF"]
        elif month == 8:
            # August (summer)
            periodicity_priority = ["EST", "Est", "Non Scol", "F", "Fer"]
        elif is_school_period:
            # School period (Sept 10 - June 30)
            if month == 9 and day < 10:
                # Before Sept 10 = non-school
                periodicity_priority = ["Non Scol", "F", "Fer"]
            else:
                # School period
                periodicity_priority = ["SCO", "Scol", "Univ", "F", "Fer"]
        else:
            # Non-school period (July, early Sept)
            periodicity_priority = ["Non Scol", "F", "Fer"]
        
        # Try to find schedule with preferred periodicity
        schedule = None
        selected_periodicity = None
        for periodicity in periodicity_priority:
            schedule = db.query(Schedule).filter(
                Schedule.route_id == route_id,
                Schedule.periodicity == periodicity
            ).first()
            if schedule:
                selected_periodicity = periodicity
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
        """Find routes between two stops, handling asterisk variations in stop IDs."""
        # Get all routes
        routes = db.query(Route).all()
        
        results = []
        
        # Normalize stop IDs - create variations
        from_variations = [from_stop_id]
        if not from_stop_id.startswith("*"):
            from_variations.append(f"*{from_stop_id}")
        else:
            from_variations.append(from_stop_id[1:])
        
        to_variations = [to_stop_id]
        if not to_stop_id.startswith("*"):
            to_variations.append(f"*{to_stop_id}")
        else:
            to_variations.append(to_stop_id[1:])
        
        for route in routes:
            # Check if both stops are in this route (with variations)
            stop_ids = [s["id"] for s in route.stops_order]
            
            from_idx = None
            to_idx = None
            
            # Find from_stop with variations
            for var in from_variations:
                if var in stop_ids:
                    from_idx = stop_ids.index(var)
                    break
            
            # Find to_stop with variations
            for var in to_variations:
                if var in stop_ids:
                    to_idx = stop_ids.index(var)
                    break
            
            if from_idx is not None and to_idx is not None:
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
    
    def plan_route_with_transfers(
        self,
        db: Session,
        from_stop_id: str,
        to_stop_id: str,
        max_transfers: int = 2,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find routes between two stops, including routes with transfers.
        
        Returns journeys with 0, 1, or 2 transfers depending on max_transfers.
        """
        all_journeys = []
        
        # 1. Try direct routes (no transfers)
        direct_routes = self.plan_route(db, from_stop_id, to_stop_id, limit=limit)
        for route_data in direct_routes:
            all_journeys.append({
                "legs": [route_data],
                "transfers": 0,
                "total_routes": 1
            })
        
        # 2. If max_transfers >= 1, try one transfer
        if max_transfers >= 1:
            one_transfer_journeys = self._find_one_transfer_routes(
                db, from_stop_id, to_stop_id, limit
            )
            all_journeys.extend(one_transfer_journeys)
        
        # 3. If max_transfers >= 2, try two transfers
        if max_transfers >= 2:
            two_transfer_journeys = self._find_two_transfer_routes(
                db, from_stop_id, to_stop_id, limit
            )
            all_journeys.extend(two_transfer_journeys)
        
        # Sort by number of transfers (prefer fewer transfers)
        all_journeys.sort(key=lambda x: x["transfers"])
        
        return all_journeys[:limit]
    
    def _find_one_transfer_routes(
        self,
        db: Session,
        from_stop_id: str,
        to_stop_id: str,
        limit: int
    ) -> List[Dict]:
        """Find routes with exactly one transfer."""
        journeys = []
        
        # Get all routes
        routes = db.query(Route).all()
        
        # Find routes that pass through from_stop
        routes_from_origin = []
        for route in routes:
            stop_ids = [s["id"] for s in route.stops_order]
            if from_stop_id in stop_ids:
                routes_from_origin.append((route, stop_ids.index(from_stop_id)))
        
        # Find routes that pass through to_stop
        routes_to_destination = []
        for route in routes:
            stop_ids = [s["id"] for s in route.stops_order]
            if to_stop_id in stop_ids:
                routes_to_destination.append((route, stop_ids.index(to_stop_id)))
        
        # Find common stops between routes (transfer points)
        for route1, from_idx in routes_from_origin:
            route1_stops = [s["id"] for s in route1.stops_order]
            stops_after_origin = route1_stops[from_idx + 1:]
            
            for route2, to_idx in routes_to_destination:
                # Skip if same route
                if route1.id == route2.id:
                    continue
                
                route2_stops = [s["id"] for s in route2.stops_order]
                stops_before_destination = route2_stops[:to_idx]
                
                # Find common stops (transfer points)
                common_stops = set(stops_after_origin) & set(stops_before_destination)
                
                for transfer_stop_id in common_stops:
                    # Get schedules for both routes
                    schedule1 = db.query(Schedule).filter(
                        Schedule.route_id == route1.id
                    ).first()
                    
                    schedule2 = db.query(Schedule).filter(
                        Schedule.route_id == route2.id
                    ).first()
                    
                    if schedule1 and schedule2 and schedule1.trips and schedule2.trips:
                        # Find times for first leg
                        leg1_data = self._find_leg_times(
                            schedule1, from_stop_id, transfer_stop_id
                        )
                        
                        # Find times for second leg
                        leg2_data = self._find_leg_times(
                            schedule2, transfer_stop_id, to_stop_id
                        )
                        
                        if leg1_data and leg2_data:
                            journeys.append({
                                "legs": [
                                    {
                                        "route": route1,
                                        "from_stop_id": from_stop_id,
                                        "to_stop_id": transfer_stop_id,
                                        "from_time": leg1_data["from_time"],
                                        "to_time": leg1_data["to_time"],
                                        "trip_id": leg1_data["trip_id"]
                                    },
                                    {
                                        "route": route2,
                                        "from_stop_id": transfer_stop_id,
                                        "to_stop_id": to_stop_id,
                                        "from_time": leg2_data["from_time"],
                                        "to_time": leg2_data["to_time"],
                                        "trip_id": leg2_data["trip_id"]
                                    }
                                ],
                                "transfers": 1,
                                "total_routes": 2,
                                "transfer_stops": [transfer_stop_id]
                            })
                            
                            # Limit results per transfer point
                            if len(journeys) >= limit * 2:
                                return journeys[:limit]
        
        return journeys
    
    def _find_two_transfer_routes(
        self,
        db: Session,
        from_stop_id: str,
        to_stop_id: str,
        limit: int
    ) -> List[Dict]:
        """Find routes with exactly two transfers."""
        # This is computationally expensive, so we limit it
        # For now, return empty list - can be implemented if needed
        return []
    
    def _find_leg_times(
        self,
        schedule: Schedule,
        from_stop_id: str,
        to_stop_id: str
    ) -> Optional[Dict]:
        """Find departure and arrival times for a leg of the journey."""
        if not schedule.trips:
            return None
        
        # Get stop names from IDs
        from_stop_name = None
        to_stop_name = None
        
        for stop in schedule.stops:
            stop_id = stop["name"].lower().replace(" ", "-").replace("'", "").replace("\n", " ").replace("  ", " ").strip()
            if stop_id == from_stop_id:
                from_stop_name = stop["name"]
            if stop_id == to_stop_id:
                to_stop_name = stop["name"]
        
        if not from_stop_name or not to_stop_name:
            return None
        
        # Find a trip that goes through both stops
        for trip in schedule.trips:
            from_time = None
            to_time = None
            found_from = False
            
            for stop_data in trip["stops"]:
                stop_name = stop_data["stop"]
                
                if stop_name == from_stop_name:
                    from_time = stop_data["time"]
                    found_from = True
                elif stop_name == to_stop_name and found_from:
                    to_time = stop_data["time"]
                    break
            
            if from_time and to_time:
                return {
                    "from_time": from_time,
                    "to_time": to_time,
                    "trip_id": trip["trip_id"]
                }
        
        return None
