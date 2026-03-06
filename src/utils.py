"""
Utility functions for the Consorzio Autolinee API.
"""

import re
import math
import logging
from typing import List, Dict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Regular expression to recognise time values (e.g. ``06:45``).
TIME_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")


def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    r = 6371
    return c * r


def calculate_time_diff(start_time: str, end_time: str) -> int:
    """Calculate time difference in minutes."""
    try:
        start_h, start_m = map(int, start_time.split(':'))
        end_h, end_m = map(int, end_time.split(':'))
        
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        return end_minutes - start_minutes
    except:
        return 0


def get_trip_destination(trip: Dict) -> str:
    """Get the destination (last stop) of a trip."""
    if trip.get("stops"):
        return trip["stops"][-1]["stop"]
    return "Unknown"


def clean_stop_name(stop_name: str) -> str:
    """Clean and normalize stop name."""
    if not stop_name:
        return ""
    
    # Remove extra whitespace
    cleaned = stop_name.strip()
    
    # Remove common prefixes/suffixes that might cause matching issues
    prefixes_to_remove = ["FERMATA ", "STAZIONE "]
    for prefix in prefixes_to_remove:
        if cleaned.upper().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    
    return cleaned


def is_technical_row(text: str) -> bool:
    """Check if a table row contains technical information rather than stop data."""
    if not text:
        return True
    
    technical_keywords = [
        "PERIODO", "CADENZA", "KM TOT", "N° CORSA", 
        "FERIALE", "SCOLASTICO", "FESTIVO",
        "LMMGVS", "LMGVS", "SABATO", "DOMENICA"
    ]
    
    text_upper = text.upper()
    return any(keyword in text_upper for keyword in technical_keywords)


def extract_times_from_text(text: str) -> List[str]:
    """Extract all time patterns from text."""
    times = TIME_PATTERN.findall(text)
    # Remove duplicates while preserving order
    seen = set()
    unique_times = []
    for t in times:
        if t not in seen:
            seen.add(t)
            unique_times.append(t)
    return unique_times


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude coordinates."""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def format_time_duration(minutes: int) -> str:
    """Format duration in minutes to human readable format."""
    if minutes < 60:
        return f"{minutes} minuti"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours} {'ora' if hours == 1 else 'ore'}"
    else:
        return f"{hours}h {remaining_minutes}m"