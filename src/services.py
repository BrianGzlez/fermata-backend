"""
Business logic services for the Consorzio Autolinee API.
"""

import logging
from functools import lru_cache
from typing import List, Dict, Optional
from datetime import datetime, date
import calendar
from fastapi import HTTPException

from .config import CACHE_SIZE, STOPS_COORDINATES, SERVICE_ALERTS, ACCESSIBILITY_DATA, DEFAULT_ACCESSIBILITY
from .consorzio_client import ConsorzioClient
from .pdf_parser import PDFScheduleParser
from .utils import similarity, calculate_distance, calculate_time_diff, get_trip_destination

logger = logging.getLogger(__name__)


class ConsorzioService:
    """Main service class for Consorzio Autolinee operations."""
    
    def __init__(self):
        self.client = ConsorzioClient()
        self.pdf_parser = PDFScheduleParser()
        self._user_favorites = {}  # In production, use a database
    
    def get_current_periodicity(self, available_periodicities: List[Dict[str, str]], target_date: date = None) -> str:
        """
        Determine which periodicity to use based on current date.
        
        Args:
            available_periodicities: List of available periodicities from API
            target_date: Date to check (defaults to today)
            
        Returns:
            The appropriate periodicity value to use
        """
        if target_date is None:
            target_date = date.today()
        
        # Extract available periodicity values
        available_values = [p["value"] for p in available_periodicities]
        
        # Check if it's weekend/holiday
        is_weekend = target_date.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        # Check if it's August (summer period)
        is_august = target_date.month == 8
        
        # Check if it's school period (rough approximation)
        # School typically: September 15 - June 15, excluding holidays
        month = target_date.month
        day = target_date.day
        
        is_school_period = (
            (month >= 9 and month <= 12) or  # Sep-Dec
            (month >= 1 and month <= 6) or   # Jan-Jun
            (month == 9 and day >= 15)       # Mid September start
        )
        
        # Priority order for periodicity selection
        logger.info(f"Determining periodicity for {target_date} (weekend: {is_weekend}, school: {is_school_period}, august: {is_august})")
        
        # Weekend/Holiday logic
        if is_weekend:
            if "FEST" in available_values:
                return "FEST"
            elif "F" in available_values:  # Feriale might include some weekend services
                return "F"
        
        # Weekday logic
        else:
            # School period
            if is_school_period:
                if "SCO" in available_values:
                    return "SCO"
                elif "SCOL" in available_values:
                    return "SCOL"
                elif "F" in available_values:
                    return "F"
            
            # Non-school period (summer, holidays)
            else:
                if "NONSCOL" in available_values:
                    return "NONSCOL"
                elif "EST" in available_values and is_august:
                    return "EST"
                elif "F" in available_values:
                    return "F"
        
        # Fallback to first available or "F"
        if "F" in available_values:
            return "F"
        elif available_periodicities:
            return available_periodicities[0]["value"]
        
        return "F"  # Ultimate fallback
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_lines(self) -> List[Dict[str, str]]:
        """Get all available bus lines."""
        return self.client.get_lines()
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_itineraries(self, line_id: str) -> List[Dict[str, str]]:
        """Get itineraries for a specific line."""
        return self.client.get_itineraries(line_id)
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_periodicities(self, line_id: str, itinerary: str) -> List[Dict[str, str]]:
        """Get periodicities for a specific line and itinerary."""
        return self.client.get_periodicities(line_id, itinerary)
    
    def get_schedule(self, line_id: str, itinerary: str, periodicity: str) -> Dict:
        """Get structured schedule for specific parameters."""
        pdf_bytes = self.client.download_pdf(line_id, itinerary, periodicity)
        return self.pdf_parser.parse_schedule(pdf_bytes)
    
    def get_current_schedule(self, line_id: str, itinerary: str, target_date: date = None) -> Dict:
        """
        Get schedule using the appropriate periodicity for the given date.
        
        Args:
            line_id: Bus line ID
            itinerary: Itinerary value
            target_date: Date to get schedule for (defaults to today)
            
        Returns:
            Schedule data with current periodicity applied
        """
        # Get available periodicities
        periodicities = self.get_periodicities(line_id, itinerary)
        
        # Determine current periodicity
        current_periodicity = self.get_current_periodicity(periodicities, target_date)
        
        logger.info(f"Using periodicity '{current_periodicity}' for line {line_id}, itinerary {itinerary}")
        
        # Get schedule with determined periodicity
        schedule = self.get_schedule(line_id, itinerary, current_periodicity)
        
        # Add metadata about periodicity selection
        if "metadata" not in schedule:
            schedule["metadata"] = {}
        
        schedule["metadata"]["selected_periodicity"] = current_periodicity
        schedule["metadata"]["target_date"] = target_date.isoformat() if target_date else date.today().isoformat()
        schedule["metadata"]["available_periodicities"] = periodicities
        
        return schedule
    
    @lru_cache(maxsize=1)
    def _build_stops_index(self) -> Dict[str, Dict]:
        """Build a searchable index of all stops from all lines."""
        logger.info("Building stops index from all available lines")
        
        stops_index = {}
        
        try:
            lines = self.get_lines()
            
            for line in lines:
                line_id = line["value"]
                logger.debug(f"Processing line {line_id}")
                
                try:
                    itineraries = self.get_itineraries(line_id)
                    
                    for itinerary in itineraries:
                        itinerary_value = itinerary["value"]
                        
                        try:
                            periodicities = self.get_periodicities(line_id, itinerary_value)
                            
                            if periodicities:
                                first_periodicity = periodicities[0]["value"]
                                
                                try:
                                    schedule = self.get_schedule(line_id, itinerary_value, first_periodicity)
                                    
                                    for stop in schedule.get("stops", []):
                                        stop_name = stop["name"]
                                        
                                        if stop_name not in stops_index:
                                            stops_index[stop_name] = {
                                                "name": stop_name,
                                                "lines": set(),
                                                "itineraries": set(),
                                                "coordinates": STOPS_COORDINATES.get(stop_name)
                                            }
                                        
                                        stops_index[stop_name]["lines"].add(line_id)
                                        stops_index[stop_name]["itineraries"].add(f"{line_id}-{itinerary_value}")
                                        
                                except Exception as e:
                                    logger.warning(f"Could not get schedule for {line_id}/{itinerary_value}: {e}")
                                    
                        except Exception as e:
                            logger.warning(f"Could not get periodicities for {line_id}/{itinerary_value}: {e}")
                            
                except Exception as e:
                    logger.warning(f"Could not get itineraries for line {line_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error building stops index: {e}")
        
        # Convert sets to lists for JSON serialization
        for stop_info in stops_index.values():
            stop_info["lines"] = list(stop_info["lines"])
            stop_info["itineraries"] = list(stop_info["itineraries"])
        
        logger.info(f"Built stops index with {len(stops_index)} stops")
        return stops_index
        """Build a searchable index of all stops from all lines."""
        logger.info("Building stops index from all available lines")
        
        stops_index = {}
        
        try:
            lines = self.get_lines()
            
            for line in lines:
                line_id = line["value"]
                logger.debug(f"Processing line {line_id}")
                
                try:
                    itineraries = self.get_itineraries(line_id)
                    
                    for itinerary in itineraries:
                        itinerary_value = itinerary["value"]
                        
                        try:
                            periodicities = self.get_periodicities(line_id, itinerary_value)
                            
                            if periodicities:
                                first_periodicity = periodicities[0]["value"]
                                
                                try:
                                    schedule = self.get_schedule(line_id, itinerary_value, first_periodicity)
                                    
                                    for stop in schedule.get("stops", []):
                                        stop_name = stop["name"]
                                        
                                        if stop_name not in stops_index:
                                            stops_index[stop_name] = {
                                                "name": stop_name,
                                                "lines": set(),
                                                "itineraries": set(),
                                                "coordinates": STOPS_COORDINATES.get(stop_name)
                                            }
                                        
                                        stops_index[stop_name]["lines"].add(line_id)
                                        stops_index[stop_name]["itineraries"].add(f"{line_id}-{itinerary_value}")
                                        
                                except Exception as e:
                                    logger.warning(f"Could not get schedule for {line_id}/{itinerary_value}: {e}")
                                    
                        except Exception as e:
                            logger.warning(f"Could not get periodicities for {line_id}/{itinerary_value}: {e}")
                            
                except Exception as e:
                    logger.warning(f"Could not get itineraries for line {line_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error building stops index: {e}")
        
        # Convert sets to lists for JSON serialization
        for stop_name in stops_index:
            stops_index[stop_name]["lines"] = list(stops_index[stop_name]["lines"])
            stops_index[stop_name]["itineraries"] = list(stops_index[stop_name]["itineraries"])
        
        logger.info(f"Built stops index with {len(stops_index)} stops")
        return stops_index
    
    def search_stops(self, query: str, limit: int = 10) -> List[Dict]:
        """Search stops by name with fuzzy matching."""
        stops_index = self._build_stops_index()
        
        if not query.strip():
            return []
        
        query = query.lower().strip()
        results = []
        
        for stop_name, stop_info in stops_index.items():
            # Calculate similarity
            sim_score = similarity(query, stop_name)
            
            # Also check if query is contained in stop name
            contains_match = query in stop_name.lower()
            
            if sim_score > 0.3 or contains_match:
                score = sim_score
                if contains_match:
                    score += 0.5  # Boost for exact substring matches
                
                results.append({
                    "stop": stop_info,
                    "score": score
                })
        
        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        return [r["stop"] for r in results[:limit]]
    
    def get_next_departures(self, stop_name: str, limit: int = 5, target_date: date = None) -> List[Dict]:
        """Get next departures from a specific stop using appropriate periodicity for the date."""
        if target_date is None:
            target_date = date.today()
            
        logger.info(f"Getting next departures for stop: {stop_name} on {target_date}")
        
        departures = []
        
        try:
            lines = self.get_lines()
            
            for line in lines:
                line_id = line["value"]
                
                try:
                    itineraries = self.get_itineraries(line_id)
                    
                    for itinerary in itineraries:
                        itinerary_value = itinerary["value"]
                        
                        try:
                            periodicities = self.get_periodicities(line_id, itinerary_value)
                            
                            if periodicities:
                                # Use smart periodicity selection
                                current_periodicity = self.get_current_periodicity(periodicities, target_date)
                                
                                try:
                                    schedule = self.get_schedule(line_id, itinerary_value, current_periodicity)
                                    
                                    # Find the periodicity info for display
                                    periodicity_info = next(
                                        (p for p in periodicities if p["value"] == current_periodicity),
                                        {"label": current_periodicity}
                                    )
                                    
                                    for trip in schedule.get("trips", []):
                                        for stop in trip["stops"]:
                                            if similarity(stop["stop"], stop_name) > 0.8:
                                                departures.append({
                                                    "line_id": line_id,
                                                    "trip_id": trip["trip_id"],
                                                    "destination": get_trip_destination(trip),
                                                    "departure_time": stop["time"],
                                                    "itinerary": itinerary["label"],
                                                    "periodicity": periodicity_info["label"],
                                                    "periodicity_value": current_periodicity,
                                                    "target_date": target_date.isoformat(),
                                                    "is_today": target_date == date.today()
                                                })
                                                
                                except Exception as e:
                                    logger.debug(f"Could not get schedule for {line_id}/{itinerary_value}: {e}")
                                    
                        except Exception as e:
                            logger.debug(f"Could not get periodicities for {line_id}/{itinerary_value}: {e}")
                            
                except Exception as e:
                    logger.debug(f"Could not get itineraries for line {line_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error getting next departures: {e}")
        
        # Sort by departure time and limit
        departures.sort(key=lambda x: x["departure_time"])
        return departures[:limit]
    
    def find_routes(self, from_stop: str, to_stop: str, limit: int = 3) -> List[Dict]:
        """Find routes between two stops."""
        logger.info(f"Finding routes from {from_stop} to {to_stop}")
        
        routes = []
        
        try:
            lines = self.get_lines()
            
            for line in lines:
                line_id = line["value"]
                
                try:
                    itineraries = self.get_itineraries(line_id)
                    
                    for itinerary in itineraries:
                        itinerary_value = itinerary["value"]
                        
                        try:
                            periodicities = self.get_periodicities(line_id, itinerary_value)
                            
                            if periodicities:
                                first_periodicity = periodicities[0]["value"]
                                
                                try:
                                    schedule = self.get_schedule(line_id, itinerary_value, first_periodicity)
                                    
                                    for trip in schedule.get("trips", []):
                                        from_found = False
                                        to_found = False
                                        from_time = None
                                        to_time = None
                                        
                                        for stop in trip["stops"]:
                                            if similarity(stop["stop"], from_stop) > 0.8:
                                                from_found = True
                                                from_time = stop["time"]
                                            elif similarity(stop["stop"], to_stop) > 0.8 and from_found:
                                                to_found = True
                                                to_time = stop["time"]
                                                break
                                        
                                        if from_found and to_found:
                                            routes.append({
                                                "type": "direct",
                                                "steps": [{
                                                    "line_id": line_id,
                                                    "from_stop": from_stop,
                                                    "to_stop": to_stop,
                                                    "departure_time": from_time,
                                                    "arrival_time": to_time,
                                                    "trip_id": trip["trip_id"]
                                                }],
                                                "total_time": calculate_time_diff(from_time, to_time),
                                                "transfers": 0
                                            })
                                            
                                except Exception as e:
                                    logger.debug(f"Could not get schedule for {line_id}/{itinerary_value}: {e}")
                                    
                        except Exception as e:
                            logger.debug(f"Could not get periodicities for {line_id}/{itinerary_value}: {e}")
                            
                except Exception as e:
                    logger.debug(f"Could not get itineraries for line {line_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error finding routes: {e}")
        
        # Sort by total time and limit
        routes.sort(key=lambda x: x.get("total_time", 999))
        return routes[:limit]
    
    def find_nearby_stops(self, lat: float, lon: float, radius_km: float = 1.0, limit: int = 10) -> List[Dict]:
        """Find stops near a given location."""
        logger.info(f"Finding stops near {lat}, {lon} within {radius_km}km")
        
        nearby_stops = []
        stops_index = self._build_stops_index()
        
        for stop_name, stop_info in stops_index.items():
            if stop_info.get("coordinates"):
                stop_coords = stop_info["coordinates"]
                distance = calculate_distance(lat, lon, stop_coords["lat"], stop_coords["lon"])
                
                if distance <= radius_km:
                    nearby_stops.append({
                        "stop": stop_info,
                        "distance_km": round(distance, 2)
                    })
        
        # Sort by distance
        nearby_stops.sort(key=lambda x: x["distance_km"])
        return nearby_stops[:limit]
    
    def get_service_alerts(self, line_id: str = None) -> List[Dict]:
        """Get service alerts, optionally filtered by line."""
        if line_id:
            return [alert for alert in SERVICE_ALERTS 
                    if alert["active"] and (not alert["line_ids"] or line_id in alert["line_ids"])]
        return [alert for alert in SERVICE_ALERTS if alert["active"]]
    
    def get_stop_accessibility_info(self, stop_name: str) -> Dict:
        """Get accessibility information for a stop."""
        return ACCESSIBILITY_DATA.get(stop_name, DEFAULT_ACCESSIBILITY)
    
    def add_user_favorite(self, user_id: str, item_type: str, item_id: str) -> bool:
        """Add a favorite stop or line for a user."""
        if user_id not in self._user_favorites:
            self._user_favorites[user_id] = {"stops": [], "lines": []}
        
        if item_type == "stop" and item_id not in self._user_favorites[user_id]["stops"]:
            self._user_favorites[user_id]["stops"].append(item_id)
            return True
        elif item_type == "line" and item_id not in self._user_favorites[user_id]["lines"]:
            self._user_favorites[user_id]["lines"].append(item_id)
            return True
        
        return False
    
    def remove_user_favorite(self, user_id: str, item_type: str, item_id: str) -> bool:
        """Remove a favorite stop or line for a user."""
        if user_id not in self._user_favorites:
            return False
        
        try:
            if item_type == "stop" and item_id in self._user_favorites[user_id]["stops"]:
                self._user_favorites[user_id]["stops"].remove(item_id)
                return True
            elif item_type == "line" and item_id in self._user_favorites[user_id]["lines"]:
                self._user_favorites[user_id]["lines"].remove(item_id)
                return True
        except ValueError:
            pass
        
        return False
    
    def get_user_favorites(self, user_id: str) -> Dict:
        """Get all favorites for a user."""
        return self._user_favorites.get(user_id, {"stops": [], "lines": []})
    
    def clear_cache(self):
        """Clear all cached data."""
        self.get_lines.cache_clear()
        self.get_itineraries.cache_clear()
        self.get_periodicities.cache_clear()
        self._build_stops_index.cache_clear()
    def get_stop_navigation(self, stop_name: str, user_lat: float, user_lon: float) -> Dict:
        """Get navigation information to a specific stop."""
        logger.info(f"Getting navigation to {stop_name} from {user_lat}, {user_lon}")
        
        # Find stop coordinates
        stops_index = self._build_stops_index()
        
        # Try exact match first
        stop_info = stops_index.get(stop_name)
        if not stop_info:
            # Try fuzzy match
            for name, info in stops_index.items():
                if similarity(name, stop_name) > 0.8:
                    stop_info = info
                    stop_name = name
                    break
        
        if not stop_info or not stop_info.get("coordinates"):
            return None
        
        stop_coords = stop_info["coordinates"]
        distance = calculate_distance(user_lat, user_lon, stop_coords["lat"], stop_coords["lon"])
        
        # Generate navigation URLs
        google_maps_url = f"https://www.google.com/maps/dir/{user_lat},{user_lon}/{stop_coords['lat']},{stop_coords['lon']}"
        apple_maps_url = f"http://maps.apple.com/?saddr={user_lat},{user_lon}&daddr={stop_coords['lat']},{stop_coords['lon']}"
        waze_url = f"https://waze.com/ul?ll={stop_coords['lat']},{stop_coords['lon']}&navigate=yes"
        
        return {
            "stop_name": stop_name,
            "stop_coordinates": stop_coords,
            "user_location": {"lat": user_lat, "lon": user_lon},
            "distance_km": round(distance, 2),
            "distance_meters": round(distance * 1000),
            "walking_time_minutes": round(distance * 12),  # ~5 km/h walking speed
            "navigation_urls": {
                "google_maps": google_maps_url,
                "apple_maps": apple_maps_url,
                "waze": waze_url
            },
            "lines_at_stop": list(stop_info.get("lines", [])),
            "accessibility": self.get_stop_accessibility_info(stop_name)
        }
    
    def get_route_navigation(self, from_stop: str, to_stop: str, user_lat: float, user_lon: float) -> Dict:
        """Get navigation to the best starting point for a planned route."""
        logger.info(f"Getting route navigation for {from_stop} → {to_stop} from user at {user_lat}, {user_lon}")
        
        # Find the route
        routes = self.find_routes(from_stop, to_stop, limit=1)
        if not routes:
            raise HTTPException(status_code=404, detail="No se encontró ruta entre las paradas especificadas")
        
        best_route = routes[0]
        first_step = best_route["steps"][0]
        departure_stop = first_step["from_stop"]
        
        # Get navigation to the departure stop
        navigation = self.get_stop_navigation(departure_stop, user_lat, user_lon)
        if not navigation:
            raise HTTPException(status_code=404, detail=f"No se encontraron coordenadas para la parada {departure_stop}")
        
        # Add route context
        navigation["route_context"] = {
            "planned_route": f"{from_stop} → {to_stop}",
            "departure_stop": departure_stop,
            "line_to_take": first_step["line_id"],
            "departure_time": first_step.get("departure_time"),
            "total_route_time": best_route.get("total_time"),
            "transfers_needed": best_route.get("transfers", 0)
        }
        
        return navigation
    
    def find_nearest_stops_with_line(self, user_lat: float, user_lon: float, line_id: str, limit: int = 3) -> List[Dict]:
        """Find nearest stops that serve a specific line."""
        logger.info(f"Finding nearest stops with line {line_id} from {user_lat}, {user_lon}")
        
        stops_with_line = []
        stops_index = self._build_stops_index()
        
        for stop_name, stop_info in stops_index.items():
            # Check if this stop serves the requested line
            if line_id in stop_info.get("lines", set()):
                if stop_info.get("coordinates"):
                    stop_coords = stop_info["coordinates"]
                    distance = calculate_distance(user_lat, user_lon, stop_coords["lat"], stop_coords["lon"])
                    
                    # Get next departures for this line from this stop
                    try:
                        departures = self.get_next_departures(stop_name, limit=3)
                        line_departures = [d for d in departures if d["line_id"] == line_id]
                    except:
                        line_departures = []
                    
                    # Generate navigation URL
                    google_maps_url = f"https://www.google.com/maps/dir/{user_lat},{user_lon}/{stop_coords['lat']},{stop_coords['lon']}"
                    
                    stops_with_line.append({
                        "stop_name": stop_name,
                        "coordinates": stop_coords,
                        "distance_km": round(distance, 2),
                        "distance_meters": round(distance * 1000),
                        "walking_time_minutes": round(distance * 12),
                        "next_departures": line_departures[:2],  # Next 2 departures for this line
                        "navigation_url": google_maps_url,
                        "all_lines": list(stop_info.get("lines", []))
                    })
        
        # Sort by distance and limit
        stops_with_line.sort(key=lambda x: x["distance_km"])
        return stops_with_line[:limit]