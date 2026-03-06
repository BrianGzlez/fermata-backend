"""
Pydantic models for request/response validation.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, validator


class ScheduleRequest(BaseModel):
    """Model for schedule request validation."""
    line_id: str
    itinerary: str
    periodicity: str
    
    @validator('line_id', 'itinerary', 'periodicity')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class OptionResponse(BaseModel):
    """Model for option response with clear value/label distinction."""
    value: str
    label: str


class LineResponse(BaseModel):
    """Model for line response."""
    value: str
    label: str


class ItineraryResponse(BaseModel):
    """Model for itinerary response."""
    value: str
    label: str


class PeriodicityResponse(BaseModel):
    """Model for periodicity response."""
    value: str
    label: str


class StopInfo(BaseModel):
    """Model for stop information."""
    name: str
    lines: List[str]
    coordinates: Optional[Dict[str, float]] = None
    accessibility: Optional[bool] = None


class NextDeparture(BaseModel):
    """Model for next departure information."""
    line_id: str
    trip_id: str
    destination: str
    departure_time: str
    minutes_until: Optional[int] = None


class RouteStep(BaseModel):
    """Model for route planning step."""
    line_id: str
    from_stop: str
    to_stop: str
    departure_time: str
    arrival_time: str
    trip_id: str


class ServiceAlert(BaseModel):
    """Model for service alerts."""
    id: str
    line_ids: List[str]
    type: str
    title: str
    message: str
    severity: str
    active: bool
    created_at: str


class AccessibilityInfo(BaseModel):
    """Model for accessibility information."""
    wheelchair_accessible: Optional[bool]
    has_shelter: Optional[bool]
    has_seating: Optional[bool]
    tactile_paving: Optional[bool]
    audio_announcements: Optional[bool]
    notes: str


class UserFavorites(BaseModel):
    """Model for user favorites."""
    stops: List[str]
    lines: List[str]