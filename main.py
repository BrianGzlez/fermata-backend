"""
Main FastAPI application for Consorzio Autolinee Cosenza API.
"""

import logging
from typing import List
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.models import (
    LineResponse, ItineraryResponse, PeriodicityResponse,
    ScheduleRequest, StopInfo, NextDeparture, RouteStep
)
from src.services import ConsorzioService
from src.utils import validate_coordinates
from src.config import STOPS_COORDINATES
from src.frontend_api import router as frontend_router
from src.database import init_db, get_db
from src.db_service import DatabaseService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Initialize services
service = ConsorzioService()
db_service = DatabaseService()
app = FastAPI(
    title="Consorzio Autolinee Cosenza API",
    description="API completa para consultar horarios de autobuses del Consorzio Autolinee Cosenza",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database tables on startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include frontend-compatible API router
app.include_router(frontend_router)

# Initialize service
service = ConsorzioService()


# ---------------------------------------------------------------------------
# Core Schedule Endpoints

@app.get("/lines", response_model=List[LineResponse], tags=["Core"])
def list_lines(db: Session = Depends(get_db)):
    """Obtener todas las líneas de autobús disponibles."""
    logger.info("API call: list_lines")
    routes = db_service.get_all_routes(db)
    # Convert to old format
    lines = [{"value": r["id"], "label": r["name"]} for r in routes]
    return JSONResponse(content=lines)


@app.get("/itineraries/{line_id}", response_model=List[ItineraryResponse], tags=["Core"])
def list_itineraries(line_id: str, db: Session = Depends(get_db)):
    """Obtener itinerarios para una línea específica desde BD."""
    logger.info(f"API call: list_itineraries for line {line_id}")
    
    if not line_id or not line_id.strip():
        raise HTTPException(status_code=400, detail="line_id no puede estar vacío")
    
    # Get schedules for this route to extract itineraries
    from src.db_models import Schedule
    schedules = db.query(Schedule).filter(Schedule.route_id == line_id.strip()).all()
    
    if not schedules:
        raise HTTPException(status_code=404, detail="Itinerarios no encontrados para la línea especificada.")
    
    # Extract unique itineraries
    itineraries_dict = {}
    for schedule in schedules:
        if schedule.itinerary not in itineraries_dict:
            direction = schedule.schedule_metadata.get("direction", "")
            label = f"{schedule.itinerary.replace('-', '')}{'A' if 'Andata' in direction else 'R' if 'Ritorno' in direction else ''}"
            itineraries_dict[schedule.itinerary] = {
                "value": schedule.itinerary,
                "label": label
            }
    
    return JSONResponse(content=list(itineraries_dict.values()))


@app.get("/periodicities/{line_id}/{itinerary}", response_model=List[PeriodicityResponse], tags=["Core"])
def list_periodicities(line_id: str, itinerary: str, db: Session = Depends(get_db)):
    """Obtener periodicidades para una línea e itinerario específicos desde BD."""
    logger.info(f"API call: list_periodicities for line {line_id}, itinerary {itinerary}")
    
    if not line_id or not line_id.strip():
        raise HTTPException(status_code=400, detail="line_id no puede estar vacío")
    if not itinerary or not itinerary.strip():
        raise HTTPException(status_code=400, detail="itinerary no puede estar vacío")
    
    # Get schedules for this route and itinerary
    from src.db_models import Schedule
    schedules = db.query(Schedule).filter(
        Schedule.route_id == line_id.strip(),
        Schedule.itinerary == itinerary.strip()
    ).all()
    
    if not schedules:
        raise HTTPException(status_code=404, detail="Periodicidades no encontradas para la combinación especificada.")
    
    # Extract unique periodicities
    periodicities = []
    seen = set()
    periodicity_labels = {
        "F": "Feriale",
        "Fer": "Feriale",
        "SCO": "Scolastico",
        "Scol": "Scolastico",
        "NS": "Non Scolastico",
        "Non Scol": "Non Scolastico",
        "FEST": "Festivo",
        "Fest": "Festivo",
        "EST": "Estivo",
        "Est": "Estivo",
        "DF": "Feriale",
        "Univ": "Universitario"
    }
    
    for schedule in schedules:
        if schedule.periodicity not in seen:
            seen.add(schedule.periodicity)
            periodicities.append({
                "value": schedule.periodicity,
                "label": periodicity_labels.get(schedule.periodicity, schedule.periodicity)
            })
    
    return JSONResponse(content=periodicities)
    if not periodicities:
        raise HTTPException(status_code=404, detail="Periodicidades no encontradas para la combinación especificada.")
    
    return JSONResponse(content=periodicities)


@app.get("/schedule/{line_id}/{itinerary}/{periodicity}", tags=["Core"])
def get_timetable(line_id: str, itinerary: str, periodicity: str, db: Session = Depends(get_db)):
    """Obtener horario estructurado para los parámetros dados desde BD."""
    logger.info(f"API call: get_timetable for line {line_id}, itinerary {itinerary}, periodicity {periodicity}")
    
    # Validate inputs
    try:
        request_data = ScheduleRequest(
            line_id=line_id,
            itinerary=itinerary,
            periodicity=periodicity
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Datos de entrada inválidos: {e}")
    
    try:
        # Get schedule from database
        from src.db_models import Schedule
        schedule = db.query(Schedule).filter(
            Schedule.route_id == request_data.line_id,
            Schedule.itinerary == request_data.itinerary,
            Schedule.periodicity == request_data.periodicity
        ).first()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Horario no encontrado")
        
        # Build response
        response = {
            "metadata": schedule.schedule_metadata or {},
            "trips": schedule.trips or [],
            "stops": schedule.stops or [],
            "schedule_matrix": schedule.schedule_matrix or {}
        }
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise


@app.get("/schedule-structured/{line_id}/{itinerary}/{periodicity}", tags=["Core"])
def get_structured_timetable(line_id: str, itinerary: str, periodicity: str, db: Session = Depends(get_db)):
    """Obtener horario estructurado desde BD (solo datos estructurados, sin fallback)."""
    logger.info(f"API call: get_structured_timetable for line {line_id}, itinerary {itinerary}, periodicity {periodicity}")
    
    try:
        request_data = ScheduleRequest(
            line_id=line_id,
            itinerary=itinerary,
            periodicity=periodicity
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Datos de entrada inválidos: {e}")
    
    try:
        # Get schedule from database
        from src.db_models import Schedule
        schedule = db.query(Schedule).filter(
            Schedule.route_id == request_data.line_id,
            Schedule.itinerary == request_data.itinerary,
            Schedule.periodicity == request_data.periodicity
        ).first()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Horario no encontrado")
        
        structured_response = {
            "metadata": schedule.schedule_metadata or {},
            "trips": schedule.trips or [],
            "stops": schedule.stops or [],
            "schedule_matrix": schedule.schedule_matrix or {},
            "summary": {
                "trips_count": len(schedule.trips or []),
                "stops_count": len(schedule.stops or []),
                "has_structured_data": len(schedule.trips or []) > 0
            }
        }
        
        return JSONResponse(content=structured_response)
        
    except HTTPException:
        raise


# ---------------------------------------------------------------------------
# Search and Discovery Endpoints

@app.get("/search/stops", tags=["Search"])
def search_stops_endpoint(
    q: str = Query(..., description="Consulta de búsqueda para nombres de paradas"), 
    limit: int = Query(10, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """Buscar paradas por nombre con coincidencia difusa."""
    logger.info(f"API call: search_stops with query '{q}'")
    
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="La consulta debe tener al menos 2 caracteres")
    
    try:
        results = db_service.search_stops(db, query=q, limit=limit)
        return JSONResponse(content={
            "query": q,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error searching stops: {e}")
        raise HTTPException(status_code=500, detail=f"Error buscando paradas: {str(e)}")


@app.get("/stops/all", tags=["Search"])
def get_all_stops(db: Session = Depends(get_db)):
    """Obtener todas las paradas disponibles con sus líneas asociadas."""
    logger.info("API call: get_all_stops")
    
    try:
        # Get all stops from database
        from src.db_models import Stop
        stops = db.query(Stop).all()
        stops_list = [s.to_dict() for s in stops]
        
        return JSONResponse(content={
            "stops": stops_list,
            "count": len(stops_list)
        })
    except Exception as e:
        logger.error(f"Error getting all stops: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo paradas: {str(e)}")


@app.get("/stops/{stop_name}/next-departures", tags=["Search"])
def get_stop_departures(
    stop_name: str, 
    limit: int = Query(5, description="Número máximo de salidas"),
    date: str = Query(None, description="Fecha en formato YYYY-MM-DD (por defecto: hoy)"),
    db: Session = Depends(get_db)
):
    """Obtener próximas salidas desde una parada específica desde BD."""
    logger.info(f"API call: get_stop_departures for '{stop_name}' on date {date}")
    
    # Parse target date
    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
    
    try:
        # Generate stop_id from name
        from src.utils import generate_stop_id
        stop_id = stop_name.lower().replace(" ", "-").replace("'", "")
        
        # Get current time for filtering
        current_time = datetime.now().strftime("%H:%M")
        
        # Get departures
        departures = db_service.get_departures(
            db, 
            stop_id, 
            limit,
            after_time=current_time
        )
        
        return JSONResponse(content={
            "stop_name": stop_name,
            "target_date": target_date.isoformat(),
            "departures": departures,
            "count": len(departures)
        })
    except Exception as e:
        logger.error(f"Error getting departures: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo salidas: {str(e)}")


@app.get("/schedule-smart/{line_id}/{itinerary}", tags=["Core"])
        try:
            from datetime import datetime
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    try:
        departures = service.get_next_departures(stop_name, limit, target_date)
        return JSONResponse(content={
            "stop_name": stop_name,
            "target_date": target_date.isoformat() if target_date else datetime.now().date().isoformat(),
            "departures": departures,
            "count": len(departures)
        })
    except Exception as e:
        logger.error(f"Error getting departures: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo salidas: {str(e)}")


@app.get("/schedule-smart/{line_id}/{itinerary}", tags=["Core"])
def get_smart_timetable(
    line_id: str, 
    itinerary: str,
    date: str = Query(None, description="Fecha en formato YYYY-MM-DD (por defecto: hoy)")
):
    """Obtener horario con periodicidad automática según la fecha."""
    logger.info(f"API call: get_smart_timetable for line {line_id}, itinerary {itinerary} on date {date}")
    
    # Parse target date
    target_date = None
    if date:
        try:
            from datetime import datetime
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    # Validate inputs
    try:
        request_data = ScheduleRequest(
            line_id=line_id,
            itinerary=itinerary,
            periodicity="AUTO"  # Will be determined automatically
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Datos de entrada inválidos: {e}")
    
    try:
        schedule = service.get_current_schedule(request_data.line_id, request_data.itinerary, target_date)
        return JSONResponse(content=schedule)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting smart schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo horario: {str(e)}")


@app.get("/periodicity/current", tags=["Core"])
def get_current_periodicity_info(
    line_id: str = Query(..., description="ID de la línea"),
    itinerary: str = Query(..., description="Valor del itinerario"),
    date: str = Query(None, description="Fecha en formato YYYY-MM-DD (por defecto: hoy)")
):
    """Obtener información sobre qué periodicidad se debe usar para una fecha específica."""
    logger.info(f"API call: get_current_periodicity_info for {line_id}/{itinerary} on {date}")
    
    # Parse target date
    target_date = None
    if date:
        try:
            from datetime import datetime
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    
    try:
        # Get available periodicities
        periodicities = service.get_periodicities(line_id, itinerary)
        if not periodicities:
            raise HTTPException(status_code=404, detail="No se encontraron periodicidades")
        
        # Determine current periodicity
        current_periodicity = service.get_current_periodicity(periodicities, target_date)
        
        # Find the selected periodicity info
        selected_info = next(
            (p for p in periodicities if p["value"] == current_periodicity),
            {"value": current_periodicity, "label": current_periodicity}
        )
        
        return JSONResponse(content={
            "line_id": line_id,
            "itinerary": itinerary,
            "target_date": target_date.isoformat() if target_date else datetime.now().date().isoformat(),
            "selected_periodicity": selected_info,
            "available_periodicities": periodicities,
            "selection_reason": _get_periodicity_reason(target_date)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting periodicity info: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo información de periodicidad: {str(e)}")


def _get_periodicity_reason(target_date=None):
    """Get human-readable reason for periodicity selection."""
    if target_date is None:
        from datetime import date
        target_date = date.today()
    
    is_weekend = target_date.weekday() >= 5
    month = target_date.month
    
    if is_weekend:
        return "Es fin de semana - usando horarios festivos"
    elif month == 8:
        return "Es agosto - usando horarios de verano"
    elif month >= 9 or month <= 6:
        return "Período escolar - usando horarios escolares"
    else:
        return "Período no escolar - usando horarios de vacaciones"


@app.get("/routes/plan", tags=["Search"])
def plan_route(
    from_stop: str = Query(..., description="Nombre de parada de origen"),
    to_stop: str = Query(..., description="Nombre de parada de destino"),
    limit: int = Query(3, description="Número máximo de opciones de ruta"),
    db: Session = Depends(get_db)
):
    """Encontrar rutas entre dos paradas desde BD."""
    logger.info(f"API call: plan_route from '{from_stop}' to '{to_stop}'")
    
    if not from_stop.strip() or not to_stop.strip():
        raise HTTPException(status_code=400, detail="Se requieren tanto from_stop como to_stop")
    
    try:
        # Generate stop IDs
        from_stop_id = from_stop.lower().replace(" ", "-").replace("'", "")
        to_stop_id = to_stop.lower().replace(" ", "-").replace("'", "")
        
        # Use db_service to find routes
        routes = db_service.plan_route(db, from_stop_id, to_stop_id, limit)
        
        # Convert to old format
        formatted_routes = []
        for route_data in routes:
            formatted_routes.append({
                "line_id": route_data["route"].id,
                "line_name": route_data["route"].name,
                "from_stop": from_stop,
                "to_stop": to_stop,
                "departure_time": route_data["from_time"],
                "arrival_time": route_data["to_time"],
                "transfers": 0
            })
        
        return JSONResponse(content={
            "from_stop": from_stop,
            "to_stop": to_stop,
            "routes": formatted_routes,
            "count": len(formatted_routes)
        })
    except Exception as e:
        logger.error(f"Error planning route: {e}")
        raise HTTPException(status_code=500, detail=f"Error planificando ruta: {str(e)}")


# ---------------------------------------------------------------------------
# Location-based Endpoints

@app.get("/stops/{stop_name}/navigation", tags=["Location"])
def get_stop_navigation(
    stop_name: str,
    user_lat: float = Query(..., description="Latitud del usuario"),
    user_lon: float = Query(..., description="Longitud del usuario")
):
    """Obtener información de navegación hacia una parada específica."""
    logger.info(f"API call: get_stop_navigation to '{stop_name}' from {user_lat}, {user_lon}")
    
    if not validate_coordinates(user_lat, user_lon):
        raise HTTPException(status_code=400, detail="Coordenadas de usuario inválidas")
    
    try:
        navigation_info = service.get_stop_navigation(stop_name, user_lat, user_lon)
        if not navigation_info:
            raise HTTPException(status_code=404, detail=f"Parada '{stop_name}' no encontrada o sin coordenadas")
        
        return JSONResponse(content=navigation_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting navigation info: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo información de navegación: {str(e)}")


@app.get("/routes/{route_id}/navigation", tags=["Location"])
def get_route_navigation(
    route_id: str,
    user_lat: float = Query(..., description="Latitud del usuario"),
    user_lon: float = Query(..., description="Longitud del usuario")
):
    """Obtener navegación hacia la parada más cercana de una ruta planificada."""
    logger.info(f"API call: get_route_navigation for route {route_id} from {user_lat}, {user_lon}")
    
    if not validate_coordinates(user_lat, user_lon):
        raise HTTPException(status_code=400, detail="Coordenadas de usuario inválidas")
    
    try:
        # For now, route_id could be "from_stop-to_stop" format
        if "-" in route_id:
            from_stop, to_stop = route_id.split("-", 1)
            navigation_info = service.get_route_navigation(from_stop, to_stop, user_lat, user_lon)
        else:
            raise HTTPException(status_code=400, detail="Formato de route_id inválido. Use 'origen-destino'")
        
        return JSONResponse(content=navigation_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting route navigation: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo navegación de ruta: {str(e)}")


@app.get("/stops/nearest-with-line", tags=["Location"])
def get_nearest_stop_with_line(
    user_lat: float = Query(..., description="Latitud del usuario"),
    user_lon: float = Query(..., description="Longitud del usuario"),
    line_id: str = Query(..., description="ID de línea requerida"),
    limit: int = Query(3, description="Número máximo de paradas")
):
    """Encontrar las paradas más cercanas que tengan una línea específica."""
    logger.info(f"API call: get_nearest_stop_with_line for line {line_id} from {user_lat}, {user_lon}")
    
    if not validate_coordinates(user_lat, user_lon):
        raise HTTPException(status_code=400, detail="Coordenadas de usuario inválidas")
    
    try:
        stops = service.find_nearest_stops_with_line(user_lat, user_lon, line_id, limit)
        return JSONResponse(content={
            "user_location": {"lat": user_lat, "lon": user_lon},
            "line_id": line_id,
            "nearest_stops": stops,
            "count": len(stops)
        })
        
    except Exception as e:
        logger.error(f"Error finding nearest stops with line: {e}")
        raise HTTPException(status_code=500, detail=f"Error encontrando paradas: {str(e)}")


@app.get("/stops/nearby", tags=["Location"])
def get_nearby_stops(
    lat: float = Query(..., description="Latitud"),
    lon: float = Query(..., description="Longitud"),
    radius: float = Query(1.0, description="Radio de búsqueda en kilómetros"),
    limit: int = Query(10, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """Encontrar paradas cerca de una ubicación dada."""
    logger.info(f"API call: get_nearby_stops at {lat}, {lon}")
    
    if not validate_coordinates(lat, lon):
        raise HTTPException(status_code=400, detail="Coordenadas inválidas")
    
    try:
        nearby = db_service.search_stops(db, lat=lat, lng=lon, radius=radius, limit=limit)
        
        # Calculate distances
        from src.utils import calculate_distance
        results = []
        for stop in nearby:
            if stop.get("latitude") and stop.get("longitude"):
                distance = calculate_distance(lat, lon, stop["latitude"], stop["longitude"])
                results.append({
                    "stop": stop,
                    "distance": round(distance, 3)
                })
        
        results.sort(key=lambda x: x["distance"])
        
        return JSONResponse(content={
            "location": {"lat": lat, "lon": lon},
            "radius_km": radius,
            "nearby_stops": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error finding nearby stops: {e}")
        raise HTTPException(status_code=500, detail=f"Error encontrando paradas cercanas: {str(e)}")


# ---------------------------------------------------------------------------
# Service Information Endpoints

@app.get("/alerts", tags=["Service"])
def get_alerts(
    line_id: str = Query(None, description="Filtrar por ID de línea"),
    db: Session = Depends(get_db)
):
    """Obtener alertas de servicio desde BD."""
    logger.info(f"API call: get_alerts for line {line_id}")
    
    try:
        alerts = db_service.get_alerts(db, line_id)
        return JSONResponse(content={
            "alerts": alerts,
            "count": len(alerts),
            "filtered_by_line": line_id
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo alertas: {str(e)}")
    logger.info(f"API call: get_alerts for line {line_id}")
    
    try:
        alerts = service.get_service_alerts(line_id)
        return JSONResponse(content={
            "alerts": alerts,
            "count": len(alerts),
            "filtered_by_line": line_id
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo alertas: {str(e)}")


@app.get("/stops/{stop_name}/accessibility", tags=["Service"])
def get_stop_accessibility(stop_name: str):
    """Obtener información de accesibilidad para una parada."""
    logger.info(f"API call: get_stop_accessibility for '{stop_name}'")
    
    try:
        accessibility = service.get_stop_accessibility_info(stop_name)
        return JSONResponse(content={
            "stop_name": stop_name,
            "accessibility": accessibility
        })
    except Exception as e:
        logger.error(f"Error getting accessibility info: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo información de accesibilidad: {str(e)}")


# ---------------------------------------------------------------------------
# User Management Endpoints

@app.get("/users/{user_id}/favorites", tags=["Users"])
def get_favorites(user_id: str):
    """Obtener paradas y líneas favoritas del usuario."""
    logger.info(f"API call: get_favorites for user {user_id}")
    
    try:
        favorites = service.get_user_favorites(user_id)
        return JSONResponse(content={
            "user_id": user_id,
            "favorites": favorites
        })
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo favoritos: {str(e)}")


@app.post("/users/{user_id}/favorites", tags=["Users"])
def add_favorite(
    user_id: str, 
    item_type: str = Query(..., description="Tipo: 'stop' o 'line'"),
    item_id: str = Query(..., description="Nombre de parada o ID de línea")
):
    """Añadir una parada o línea favorita para un usuario."""
    logger.info(f"API call: add_favorite for user {user_id}, type {item_type}, id {item_id}")
    
    if item_type not in ["stop", "line"]:
        raise HTTPException(status_code=400, detail="item_type debe ser 'stop' o 'line'")
    
    try:
        success = service.add_user_favorite(user_id, item_type, item_id)
        if success:
            return JSONResponse(content={
                "message": f"Añadido {item_type} '{item_id}' a favoritos",
                "user_id": user_id,
                "item_type": item_type,
                "item_id": item_id
            })
        else:
            return JSONResponse(content={
                "message": f"{item_type} '{item_id}' ya está en favoritos",
                "user_id": user_id
            })
    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
        raise HTTPException(status_code=500, detail=f"Error añadiendo favorito: {str(e)}")


@app.delete("/users/{user_id}/favorites", tags=["Users"])
def remove_favorite(
    user_id: str,
    item_type: str = Query(..., description="Tipo: 'stop' o 'line'"),
    item_id: str = Query(..., description="Nombre de parada o ID de línea")
):
    """Eliminar una parada o línea favorita para un usuario."""
    logger.info(f"API call: remove_favorite for user {user_id}, type {item_type}, id {item_id}")
    
    if item_type not in ["stop", "line"]:
        raise HTTPException(status_code=400, detail="item_type debe ser 'stop' o 'line'")
    
    try:
        success = service.remove_user_favorite(user_id, item_type, item_id)
        if success:
            return JSONResponse(content={
                "message": f"Eliminado {item_type} '{item_id}' de favoritos",
                "user_id": user_id
            })
        else:
            return JSONResponse(content={
                "message": f"{item_type} '{item_id}' no encontrado en favoritos",
                "user_id": user_id
            }, status_code=404)
    except Exception as e:
        logger.error(f"Error removing favorite: {e}")
        raise HTTPException(status_code=500, detail=f"Error eliminando favorito: {str(e)}")


# ---------------------------------------------------------------------------
# Testing and Debug Endpoints

@app.get("/test-flow/{line_id}", tags=["Debug"])
def test_complete_flow(line_id: str):
    """Probar el flujo completo para una línea específica."""
    logger.info(f"Testing complete flow for line {line_id}")
    
    try:
        # Step 1: Get itineraries
        itineraries = service.get_itineraries(line_id)
        if not itineraries:
            return {"error": f"No itineraries found for line {line_id}"}
        
        first_itinerary = itineraries[0]
        
        # Step 2: Get periodicities
        periodicities = service.get_periodicities(line_id, first_itinerary["value"])
        if not periodicities:
            return {"error": f"No periodicities found for line {line_id}, itinerary {first_itinerary['value']}"}
        
        first_periodicity = periodicities[0]
        
        # Step 3: Get schedule
        try:
            schedule = service.get_schedule(line_id, first_itinerary["value"], first_periodicity["value"])
            
            schedule_summary = {
                "metadata": schedule.get("metadata", {}),
                "trips_count": len(schedule.get("trips", [])),
                "stops_count": len(schedule.get("stops", [])),
                "raw_times_count": schedule.get("raw_times_count", 0),
                "has_structured_data": len(schedule.get("trips", [])) > 0,
                "sample_trips": schedule.get("trips", [])[:2],
                "sample_stops": [s["name"] for s in schedule.get("stops", [])][:5]
            }
            
            if "fallback_times" in schedule:
                fallback_summary = {}
                for page, times in schedule["fallback_times"].items():
                    fallback_summary[page] = {
                        "count": len(times),
                        "sample": times[:5]
                    }
                schedule_summary["fallback_data"] = fallback_summary
                
        except Exception as e:
            schedule_summary = {"error": f"Failed to get schedule: {str(e)}"}
        
        return {
            "line_id": line_id,
            "itineraries_count": len(itineraries),
            "first_itinerary": first_itinerary,
            "periodicities_count": len(periodicities),
            "first_periodicity": first_periodicity,
            "schedule_summary": schedule_summary
        }
        
    except Exception as e:
        logger.error(f"Error in test flow: {e}")
        return {"error": f"Test flow failed: {str(e)}"}


@app.get("/debug/values/{line_id}", tags=["Debug"])
def debug_values(line_id: str):
    """Ver los valores correctos para usar en URLs para una línea."""
    logger.info(f"Debug values for line {line_id}")
    
    try:
        itineraries = service.get_itineraries(line_id)
        if not itineraries:
            return {"error": f"No itineraries found for line {line_id}"}
        
        result = {
            "line_id": line_id,
            "itineraries": itineraries,
            "periodicities_by_itinerary": {},
            "example_urls": []
        }
        
        for itinerary in itineraries:
            itinerary_value = itinerary["value"]
            try:
                periodicities = service.get_periodicities(line_id, itinerary_value)
                result["periodicities_by_itinerary"][itinerary_value] = periodicities
                
                if periodicities:
                    first_periodicity = periodicities[0]["value"]
                    example_url = f"/schedule/{line_id}/{itinerary_value}/{first_periodicity}"
                    result["example_urls"].append({
                        "itinerary_label": itinerary["label"],
                        "itinerary_value": itinerary_value,
                        "periodicity_label": periodicities[0]["label"],
                        "periodicity_value": first_periodicity,
                        "correct_url": example_url
                    })
                    
            except Exception as e:
                result["periodicities_by_itinerary"][itinerary_value] = {"error": str(e)}
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to get debug values: {str(e)}"}


@app.get("/test-navigation", tags=["Debug"])
def test_navigation():
    """Probar funcionalidad de navegación con datos de ejemplo."""
    logger.info("Testing navigation functionality")
    
    try:
        # Test basic distance calculation
        from src.utils import calculate_distance
        distance = calculate_distance(39.3000, 16.2600, 39.2986, 16.2540)
        
        # Test navigation URL generation
        user_lat, user_lon = 39.3000, 16.2600
        stop_lat, stop_lon = 39.2986, 16.2540
        
        google_maps_url = f"https://www.google.com/maps/dir/{user_lat},{user_lon}/{stop_lat},{stop_lon}"
        apple_maps_url = f"http://maps.apple.com/?saddr={user_lat},{user_lon}&daddr={stop_lat},{stop_lon}"
        waze_url = f"https://waze.com/ul?ll={stop_lat},{stop_lon}&navigate=yes"
        
        return JSONResponse(content={
            "test_results": {
                "distance_calculation": {
                    "from": {"lat": user_lat, "lon": user_lon},
                    "to": {"lat": stop_lat, "lon": stop_lon},
                    "distance_km": round(distance, 3),
                    "distance_meters": round(distance * 1000),
                    "walking_time_minutes": round(distance * 12)
                },
                "navigation_urls": {
                    "google_maps": google_maps_url,
                    "apple_maps": apple_maps_url,
                    "waze": waze_url
                },
                "coordinates_available": len(STOPS_COORDINATES),
                "sample_stops": list(STOPS_COORDINATES.keys())[:5]
            },
            "status": "✅ Navigation functionality working"
        })
        
    except Exception as e:
        logger.error(f"Error testing navigation: {e}")
        return JSONResponse(content={
            "error": str(e),
            "status": "❌ Navigation test failed"
        }, status_code=500)


# ---------------------------------------------------------------------------
# System Endpoints

@app.get("/health", tags=["System"])
def health_check():
    """Verificación de estado del servicio."""
    return {"status": "healthy", "service": "Consorzio Autolinee API", "version": "2.1.0"}


@app.post("/admin/clear-cache", tags=["System"])
def clear_cache():
    """Limpiar todos los datos en caché."""
    logger.info("Clearing cache")
    service.clear_cache()
    return {"message": "Cache cleared successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)