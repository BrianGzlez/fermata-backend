"""
Database models for storing bus schedule data.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Stop(Base):
    """Bus stop model."""
    __tablename__ = "stops"

    id = Column(String, primary_key=True, index=True)  # e.g., "cosenza"
    name = Column(String, nullable=False, index=True)  # e.g., "COSENZA"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String, default="Cosenza")
    region = Column(String, default="Calabria")
    routes = Column(JSON, default=list)  # List of route IDs
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    departures = relationship("Departure", back_populates="stop", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude or 0.0,
            "longitude": self.longitude or 0.0,
            "routes": self.routes or [],
            "city": self.city,
            "region": self.region
        }


class Route(Base):
    """Bus route/line model."""
    __tablename__ = "routes"

    id = Column(String, primary_key=True, index=True)  # e.g., "135"
    name = Column(String, nullable=False)  # e.g., "COSENZA - SCALEA"
    short_name = Column(String)  # e.g., "L135"
    color = Column(String)  # e.g., "#2563EB"
    type = Column(String, default="bus")
    stops_order = Column(JSON, default=list)  # List of stop IDs in order
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    schedules = relationship("Schedule", back_populates="route", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "shortName": self.short_name,
            "color": self.color,
            "type": self.type,
            "stops": self.stops_order or []
        }


class Departure(Base):
    """Departure from a stop."""
    __tablename__ = "departures"

    id = Column(String, primary_key=True)  # e.g., "cosenza-135-404150"
    stop_id = Column(String, ForeignKey("stops.id"), nullable=False, index=True)
    route_id = Column(String, nullable=False, index=True)
    route_name = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(String, nullable=False)  # HH:MM format
    trip_id = Column(String)
    periodicity = Column(String)  # F, SCO, FEST, etc.
    itinerary = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stop = relationship("Stop", back_populates="departures")

    # Indexes for fast queries
    __table_args__ = (
        Index('idx_stop_route', 'stop_id', 'route_id'),
        Index('idx_stop_time', 'stop_id', 'departure_time'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "routeId": self.route_id,
            "routeName": self.route_name,
            "destination": self.destination,
            "departureTime": self.departure_time,
            "estimatedTime": None,
            "delay": None,
            "status": "on-time",
            "platform": None,
            "realTime": False,
            "periodicity": self.periodicity
        }


class Schedule(Base):
    """Complete schedule for a route."""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String, ForeignKey("routes.id"), nullable=False, index=True)
    itinerary = Column(String, nullable=False)
    periodicity = Column(String, nullable=False)
    direction = Column(String)  # Andata/Ritorno
    
    # Store the complete schedule as JSON
    trips = Column(JSON, default=list)  # List of trips with stops and times
    stops = Column(JSON, default=list)  # List of stops in order
    schedule_matrix = Column(JSON, default=dict)  # Matrix of stop -> trip -> time
    schedule_metadata = Column(JSON, default=dict)  # Renamed from metadata
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    route = relationship("Route", back_populates="schedules")

    # Indexes
    __table_args__ = (
        Index('idx_route_itinerary', 'route_id', 'itinerary', 'periodicity'),
    )


class Alert(Base):
    """Service alerts."""
    __tablename__ = "alerts"

    id = Column(String, primary_key=True)
    severity = Column(String, nullable=False)  # low, medium, high
    message = Column(Text, nullable=False)
    affected_routes = Column(JSON, default=list)  # List of route IDs
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "severity": self.severity,
            "message": self.message,
            "affectedRoutes": self.affected_routes or [],
            "startTime": self.start_time.isoformat() if self.start_time else None,
            "endTime": self.end_time.isoformat() if self.end_time else None
        }


class SyncLog(Base):
    """Log of synchronization jobs."""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String, nullable=False)  # stops, routes, schedules, all
    status = Column(String, nullable=False)  # success, error, partial
    items_synced = Column(Integer, default=0)
    errors = Column(JSON, default=list)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    def to_dict(self):
        return {
            "id": self.id,
            "sync_type": self.sync_type,
            "status": self.status,
            "items_synced": self.items_synced,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds
        }
