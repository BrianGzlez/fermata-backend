"""
Backend service to fetch and parse bus schedules from the Consorzio Autolinee
Cosenza website.

This module exposes a simple HTTP API built with FastAPI.  The API allows
clients to discover the available bus lines, the itineraries associated
with each line, the valid periodicities for a given line/itinerary
combination, and finally to retrieve the timetable itself as a structured
JSON object.

The implementation mirrors the behaviour of the official site.  It
performs HTTP requests against the following endpoints:

 * ``https://www.consorzioautolineetpl.it/quadro_orario.php`` – to
   obtain the list of lines.
 * ``https://www.consorzioautolineetpl.it/select.ajaxlinea.php`` – to
   obtain itineraries or periodicities (depending on the parameters).
 * ``https://www.consorzioautolineetpl.it/download_quadro_orari.php`` – to
   download the timetable PDF for a specific line/itinerary/periodicity.

Because the timetable is delivered as a PDF, this backend uses
``pdfplumber`` to extract text from the returned document.  The text is
then post‑processed with a regular expression to pull out time values in
``HH:MM`` format.  If finer grained parsing (for example stop names
associated with each time) is required, additional logic can be added
here.

To run this service locally you can install the dependencies via:

```bash
pip install fastapi uvicorn requests beautifulsoup4 pdfplumber
```

Then start the server with:

```bash
uvicorn backend:app --reload
```

Once running, you can explore the API at ``http://127.0.0.1:8000/docs``.
"""

import io
import logging
import os
import re
from functools import lru_cache
from typing import List, Dict, Optional
from difflib import SequenceMatcher

import pdfplumber
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator


# ---------------------------------------------------------------------------
# Configuration
#
# Should the Consorzio site change its URLs in the future you can adapt
# these constants accordingly.  They are kept at module level to ease
# maintenance and testing.

# Environment variables for configuration
BASE_URL = os.getenv("CONSORZIO_BASE_URL", "https://www.consorzioautolineetpl.it")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "100"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LINES_PAGE = f"{BASE_URL}/quadro_orario.php"
SELECT_ENDPOINT = f"{BASE_URL}/select.ajaxlinea.php"
PDF_ENDPOINT = f"{BASE_URL}/download_quadro_orari.php"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Regular expression to recognise time values (e.g. ``06:45``).
TIME_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")


# ---------------------------------------------------------------------------
# Pydantic Models for validation

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


def _get_soup_from_url(url: str) -> BeautifulSoup:
    """Helper to fetch a URL and return a BeautifulSoup object.

    Raises:
        HTTPException: if the request fails or returns a non‑200 status.

    """
    logger.info(f"Fetching URL: {url}")
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        logger.info(f"Request to {url} completed with status {resp.status_code}")
    except requests.RequestException as exc:
        logger.error(f"Request failed for {url}: {exc}")
        raise HTTPException(status_code=500, detail=f"Errore nel recuperare {url}: {exc}")
    if resp.status_code != 200:
        logger.error(f"Unexpected response from {url}: {resp.status_code}")
        raise HTTPException(status_code=resp.status_code, detail=f"Risposta inattesa da {url}: {resp.status_code}")
    return BeautifulSoup(resp.text, "html.parser")


@lru_cache(maxsize=CACHE_SIZE)
def get_lines() -> List[Dict[str, str]]:
    """Retrieve the list of available bus lines.

    Returns a list of dictionaries with ``value`` and ``label`` keys.
    """
    logger.info("Fetching available bus lines")
    soup = _get_soup_from_url(LINES_PAGE)
    select = soup.find("select", attrs={"name": "linea"})
    if select is None:
        logger.error("Could not find lines select element")
        raise HTTPException(status_code=500, detail="Impossibile trovare l'elenco delle linee.")
    lines: List[Dict[str, str]] = []
    for option in select.find_all("option"):
        value = option.get("value")
        text = option.get_text(strip=True)
        # Filter out NULL and empty values
        if not value or value.upper() == "NULL" or not value.strip():
            continue
        lines.append({"value": value.strip(), "label": text})
    logger.info(f"Found {len(lines)} bus lines")
    return lines


def _post_select(params: Dict[str, str]) -> List[Dict[str, str]]:
    """Internal helper to call the select.ajaxlinea.php endpoint.

    Args:
        params: Dictionary of POST parameters.

    Returns:
        A list of options extracted from the HTML response.  Each entry is
        represented as a dict containing ``value`` (the option value) and
        ``label`` (the visible text).
    """
    logger.info(f"Making POST request to select endpoint with params: {params}")
    try:
        resp = requests.post(SELECT_ENDPOINT, data=params, timeout=REQUEST_TIMEOUT)
        logger.info(f"POST request completed with status {resp.status_code}")
    except requests.RequestException as exc:
        logger.error(f"POST request failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Errore durante la richiesta al selettore: {exc}")
    if resp.status_code != 200:
        logger.error(f"Unexpected response from selector: {resp.status_code}")
        raise HTTPException(status_code=resp.status_code, detail=f"Risposta inattesa dal selettore: {resp.status_code}")
    
    # Debug logging
    logger.debug(f"Raw response text: {resp.text[:500]}...")
    
    soup = BeautifulSoup(resp.text, "html.parser")
    options_list: List[Dict[str, str]] = []
    for option in soup.find_all("option"):
        value = option.get("value") or ""
        name = option.get_text(strip=True)
        # Filter out NULL, empty values, and placeholder options
        if not value or value.upper() == "NULL" or not value.strip() or "SELEZIONA" in name.upper():
            logger.debug(f"Skipping option: value='{value}', name='{name}'")
            continue
        options_list.append({"value": value.strip(), "label": name})
    
    logger.info(f"Found {len(options_list)} valid options")
    if not options_list:
        logger.warning(f"No valid options found. Raw response: {resp.text}")
    
    return options_list


@lru_cache(maxsize=CACHE_SIZE)
def get_itineraries(line_id: str) -> List[Dict[str, str]]:
    """Fetch itineraries for a given line.

    Args:
        line_id: Identifier of the bus line.

    Returns:
        A list of itineraries (id and name pairs).
    """
    logger.info(f"Fetching itineraries for line {line_id}")
    params = {"id": line_id, "tipo": "ITINERARIO"}
    return _post_select(params)


@lru_cache(maxsize=CACHE_SIZE)
def get_periodicities(line_id: str, itinerary: str) -> List[Dict[str, str]]:
    """Fetch periodicity options for a given line and itinerary.

    Args:
        line_id: Identifier of the bus line.
        itinerary: Identifier of the itinerary (the VALUE from get_itineraries).

    Returns:
        A list of periodicities (value and label pairs).
    """
    logger.info(f"Fetching periodicities for line {line_id}, itinerary {itinerary}")
    params = {
        "id": line_id,
        "id_itinerario": itinerary,  # This should be the VALUE, not the label
        "tipo": "PERIODICITA",  # Nota: la web usa "PERIODICITA" sin la "Y"
    }
    periodicities = _post_select(params)
    
    # Si no hay periodicidades específicas, la web a veces usa 'F' como default
    if not periodicities:
        logger.info("No periodicities found, checking for default 'F'")
        # Intentar con periodicidad por defecto 'F' (Feriale - días laborables)
        default_periodicities = [{"value": "F", "label": "Feriale (Giorni lavorativi)"}]
        return default_periodicities
    
    return periodicities


def _parse_pdf_schedule(pdf_bytes: bytes) -> Dict:
    """Extract structured timetable from a PDF.

    The Consorzio PDFs contain structured timetables with:
    - Columns = Trips (N° Corsa)
    - Rows = Stops (FERMATE)
    - Cells = Time when that trip passes through that stop
    - "-" means the trip doesn't stop there

    Args:
        pdf_bytes: Raw bytes of the downloaded PDF.

    Returns:
        A structured dictionary with trips, stops, and metadata.
    """
    logger.info("Parsing structured PDF schedule")
    
    result = {
        "metadata": {},
        "trips": [],
        "stops": [],
        "schedule_matrix": {},
        "raw_times_count": 0  # For backward compatibility
    }
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            logger.info(f"PDF has {len(pdf.pages)} pages")
            
            all_text_lines = []
            
            for page_num, page in enumerate(pdf.pages, start=1):
                logger.debug(f"Processing page {page_num}")
                
                # Extract text line by line
                text = page.extract_text() or ""
                lines = text.split('\n')
                all_text_lines.extend(lines)
                
                # Try to extract tables
                try:
                    tables = page.extract_tables()
                    if tables:
                        logger.info(f"Found {len(tables)} tables on page {page_num}")
                        for table_idx, table in enumerate(tables):
                            logger.debug(f"Table {table_idx} has {len(table)} rows")
                            result = _process_schedule_table(table, result, page_num)
                except Exception as e:
                    logger.warning(f"Could not extract tables from page {page_num}: {e}")
            
            # Extract metadata from text
            result["metadata"] = _extract_metadata_from_text(all_text_lines)
            
            # Extract all times for backward compatibility
            all_times = TIME_PATTERN.findall('\n'.join(all_text_lines))
            result["raw_times_count"] = len(all_times)
            
            # If no structured data was found, fall back to simple time extraction
            if not result["trips"] and not result["stops"]:
                logger.warning("No structured data found, falling back to simple time extraction")
                result["fallback_times"] = {}
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    times = TIME_PATTERN.findall(text)
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_times = []
                    for t in times:
                        if t not in seen:
                            seen.add(t)
                            unique_times.append(t)
                    result["fallback_times"][str(page_num)] = unique_times
            
    except Exception as exc:
        logger.error(f"Error parsing PDF: {exc}")
        raise HTTPException(status_code=500, detail=f"Errore nel parsing del PDF: {exc}")
    
    return result


def _extract_metadata_from_text(lines: List[str]) -> Dict[str, str]:
    """Extract metadata from PDF text lines."""
    metadata = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract line number
        if line.startswith("Linea N°") or line.startswith("Linea"):
            metadata["line"] = line
        
        # Extract macroitinerary
        if "Macroitinerario:" in line or "Itinerario:" in line:
            metadata["itinerary"] = line
        
        # Extract periodicity
        if "Periodicità:" in line or "Periodicit" in line:
            metadata["periodicity"] = line
        
        # Extract direction
        if "Corse Andata" in line:
            metadata["direction"] = "Andata"
        elif "Corse Ritorno" in line:
            metadata["direction"] = "Ritorno"
        
        # Extract tipo
        if "Tipo:" in line:
            metadata["type"] = line
    
    return metadata


def _process_schedule_table(table: List[List[str]], result: Dict, page_num: int) -> Dict:
    """Process a schedule table from the PDF."""
    if not table or len(table) < 2:
        return result
    
    logger.debug(f"Processing table with {len(table)} rows")
    
    # Find the header row with trip numbers (N° Corsa)
    trip_header_row = None
    stop_column_idx = None
    
    for row_idx, row in enumerate(table):
        if not row:
            continue
        
        # Look for "FERMATE" or similar to identify stops column
        for col_idx, cell in enumerate(row):
            if cell and ("FERMATE" in cell.upper() or "FERMATA" in cell.upper()):
                stop_column_idx = col_idx
                break
        
        # Look for trip numbers (usually numeric)
        if any(cell and cell.isdigit() and len(cell) >= 4 for cell in row if cell):
            trip_header_row = row_idx
            break
    
    if trip_header_row is None or stop_column_idx is None:
        logger.debug("Could not identify table structure")
        return result
    
    # Extract trip IDs
    trip_row = table[trip_header_row]
    trip_ids = []
    for col_idx, cell in enumerate(trip_row):
        if col_idx != stop_column_idx and cell and cell.strip() and cell.strip().isdigit():
            trip_ids.append(cell.strip())
    
    logger.info(f"Found {len(trip_ids)} trips: {trip_ids[:5]}...")
    
    # Process data rows (after headers)
    for row_idx in range(trip_header_row + 1, len(table)):
        row = table[row_idx]
        if not row or len(row) <= stop_column_idx:
            continue
        
        stop_name = row[stop_column_idx]
        if not stop_name or not stop_name.strip():
            continue
        
        # Skip technical rows
        if any(keyword in stop_name.upper() for keyword in ["PERIODO", "CADENZA", "KM TOT", "N° CORSA"]):
            continue
        
        stop_name = stop_name.strip()
        
        # Add stop if not already present
        if stop_name not in [s["name"] for s in result["stops"]]:
            result["stops"].append({"name": stop_name, "index": len(result["stops"])})
        
        # Extract times for this stop
        stop_times = {}
        for col_idx, cell in enumerate(row):
            if col_idx == stop_column_idx:
                continue
            
            if col_idx - stop_column_idx - 1 < len(trip_ids):
                trip_id = trip_ids[col_idx - stop_column_idx - 1]
                if cell and cell.strip() and cell.strip() != "-":
                    time_match = TIME_PATTERN.search(cell.strip())
                    if time_match:
                        stop_times[trip_id] = time_match.group()
        
        if stop_times:
            result["schedule_matrix"][stop_name] = stop_times
    
    # Build trips structure
    for trip_id in trip_ids:
        trip_stops = []
        for stop in result["stops"]:
            stop_name = stop["name"]
            if stop_name in result["schedule_matrix"] and trip_id in result["schedule_matrix"][stop_name]:
                trip_stops.append({
                    "stop": stop_name,
                    "time": result["schedule_matrix"][stop_name][trip_id]
                })
        
        if trip_stops:
            result["trips"].append({
                "trip_id": trip_id,
                "stops": trip_stops
            })
    
    return result


def get_schedule(line_id: str, itinerary: str, periodicity: str) -> Dict:
    """Download and parse the timetable for the given parameters.

    Args:
        line_id: Identifier of the bus line (e.g. ``135``).
        itinerary: Identifier of the itinerary (VALUE from get_itineraries).
        periodicity: Identifier of the periodicity (VALUE from get_periodicities).

    Returns:
        A structured dictionary with trips, stops, metadata, and schedule matrix.
        Format:
        {
            "metadata": {"line": "...", "itinerary": "...", "direction": "..."},
            "trips": [{"trip_id": "404150", "stops": [{"stop": "ORSOMARSO", "time": "07:00"}]}],
            "stops": [{"name": "ORSOMARSO", "index": 0}],
            "schedule_matrix": {"ORSOMARSO": {"404150": "07:00"}},
            "fallback_times": {"1": ["07:00", "07:21"]} // if structured parsing fails
        }
    """
    logger.info(f"Downloading schedule for line {line_id}, itinerary {itinerary}, periodicity {periodicity}")
    payload = {
        "linea": line_id,
        "itinerario": itinerary,
        "periodicita": periodicity,
    }
    logger.debug(f"Payload sent to download_quadro_orari.php: {payload}")
    
    try:
        resp = requests.post(PDF_ENDPOINT, data=payload, timeout=REQUEST_TIMEOUT)
        logger.info(f"PDF download request completed with status {resp.status_code}")
    except requests.RequestException as exc:
        logger.error(f"PDF download failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Errore durante il download del PDF: {exc}")
    
    # Expecting a PDF (content-type application/pdf)
    if resp.status_code != 200:
        logger.error(f"PDF download failed with status {resp.status_code}")
        raise HTTPException(status_code=resp.status_code, detail=f"Impossibile scaricare il PDF: {resp.status_code}")
    
    content_type = resp.headers.get("Content-Type", "").lower()
    content_length = len(resp.content)
    content_preview = resp.content[:50]  # First 50 bytes for debugging
    
    logger.debug(f"Response Content-Type: {content_type}")
    logger.debug(f"Response Content-Length: {content_length}")
    logger.debug(f"Response Content Preview: {content_preview}")
    
    # Validate that we received a real PDF
    if "pdf" not in content_type:
        logger.error(f"Invalid content type received: {content_type}")
        # Check if it contains PDF content anywhere
        if b'%PDF-' not in resp.content:
            logger.error(f"Content does not contain PDF magic bytes. Content preview: {resp.content[:200]}")
            raise HTTPException(
                status_code=422, 
                detail={
                    "error": "El servidor no devolvió un PDF válido; probablemente periodicity inválida",
                    "content_type": content_type,
                    "content_preview": resp.content[:200].decode('utf-8', errors='ignore'),
                    "suggestion": "Verifica que estés usando el 'value' correcto de periodicities, no el 'label'"
                }
            )
        else:
            logger.warning(f"Content-Type is not PDF but content contains PDF data")
    
    # Additional check for PDF magic bytes even if content-type is correct
    # Sometimes the server returns HTML errors before the PDF content
    pdf_start = resp.content.find(b'%PDF-')
    if pdf_start == -1:
        logger.error(f"Content does not contain PDF magic bytes anywhere")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "El contenido no contiene un PDF válido (no se encontró %PDF-)",
                "content_type": content_type,
                "content_preview": resp.content[:200].decode('utf-8', errors='ignore')
            }
        )
    
    # If PDF starts after some HTML errors, extract just the PDF part
    if pdf_start > 0:
        logger.warning(f"PDF content starts at byte {pdf_start}, extracting PDF portion")
        logger.debug(f"Skipped content: {resp.content[:pdf_start].decode('utf-8', errors='ignore')}")
        pdf_content = resp.content[pdf_start:]
    else:
        pdf_content = resp.content
    
    return _parse_pdf_schedule(pdf_content)


# ---------------------------------------------------------------------------
# Stop Management and Search Functions

# Global cache for stops index
_stops_index = None
_stops_coordinates = {
    # Sample coordinates - in a real app, these would come from a database or external API
    "COSENZA": {"lat": 39.2986, "lon": 16.2540},
    "RENDE": {"lat": 39.3167, "lon": 16.2333},
    "SCALEA": {"lat": 39.8167, "lon": 15.7833},
    "ORSOMARSO": {"lat": 39.7833, "lon": 15.8167},
    "MARCELLINA": {"lat": 39.8000, "lon": 15.8000}
}

# Simple in-memory storage for user favorites (in production, use a database)
_user_favorites = {}

# Service alerts storage
_service_alerts = [
    {
        "id": "alert_001",
        "line_ids": ["139"],
        "type": "delay",
        "title": "Ritardi sulla linea 139",
        "message": "Possibili ritardi di 10-15 minuti a causa di traffico intenso",
        "severity": "medium",
        "active": True,
        "created_at": "2026-03-03T10:00:00Z"
    }
]

def _similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


@lru_cache(maxsize=1)
def _build_stops_index() -> Dict[str, Dict]:
    """Build a searchable index of all stops from all lines."""
    logger.info("Building stops index from all available lines")
    
    stops_index = {}
    
    try:
        # Get all lines
        lines = get_lines()
        
        for line in lines:
            line_id = line["value"]
            logger.debug(f"Processing line {line_id}")
            
            try:
                # Get itineraries for this line
                itineraries = get_itineraries(line_id)
                
                for itinerary in itineraries:
                    itinerary_value = itinerary["value"]
                    
                    try:
                        # Get periodicities
                        periodicities = get_periodicities(line_id, itinerary_value)
                        
                        if periodicities:
                            # Use first periodicity to get schedule
                            first_periodicity = periodicities[0]["value"]
                            
                            try:
                                schedule = get_schedule(line_id, itinerary_value, first_periodicity)
                                
                                # Extract stops from schedule
                                for stop in schedule.get("stops", []):
                                    stop_name = stop["name"]
                                    
                                    if stop_name not in stops_index:
                                        stops_index[stop_name] = {
                                            "name": stop_name,
                                            "lines": set(),
                                            "itineraries": set(),
                                            "coordinates": _stops_coordinates.get(stop_name)
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


def search_stops(query: str, limit: int = 10) -> List[Dict]:
    """Search stops by name with fuzzy matching."""
    stops_index = _build_stops_index()
    
    if not query.strip():
        return []
    
    query = query.lower().strip()
    results = []
    
    for stop_name, stop_info in stops_index.items():
        # Calculate similarity
        similarity = _similarity(query, stop_name)
        
        # Also check if query is contained in stop name
        contains_match = query in stop_name.lower()
        
        if similarity > 0.3 or contains_match:
            score = similarity
            if contains_match:
                score += 0.5  # Boost for exact substring matches
            
            results.append({
                "stop": stop_info,
                "score": score
            })
    
    # Sort by score (descending) and limit results
    results.sort(key=lambda x: x["score"], reverse=True)
    return [r["stop"] for r in results[:limit]]


def get_next_departures(stop_name: str, limit: int = 5) -> List[Dict]:
    """Get next departures from a specific stop."""
    logger.info(f"Getting next departures for stop: {stop_name}")
    
    departures = []
    current_time = "08:00"  # TODO: Use actual current time
    
    try:
        # Get all lines
        lines = get_lines()
        
        for line in lines:
            line_id = line["value"]
            
            try:
                # Get itineraries for this line
                itineraries = get_itineraries(line_id)
                
                for itinerary in itineraries:
                    itinerary_value = itinerary["value"]
                    
                    try:
                        # Get periodicities (use first available)
                        periodicities = get_periodicities(line_id, itinerary_value)
                        
                        if periodicities:
                            first_periodicity = periodicities[0]["value"]
                            
                            try:
                                schedule = get_schedule(line_id, itinerary_value, first_periodicity)
                                
                                # Look for this stop in the schedule
                                for trip in schedule.get("trips", []):
                                    for stop in trip["stops"]:
                                        if _similarity(stop["stop"], stop_name) > 0.8:
                                            departures.append({
                                                "line_id": line_id,
                                                "trip_id": trip["trip_id"],
                                                "destination": _get_trip_destination(trip),
                                                "departure_time": stop["time"],
                                                "itinerary": itinerary["label"],
                                                "periodicity": periodicities[0]["label"]
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


def _get_trip_destination(trip: Dict) -> str:
    """Get the destination (last stop) of a trip."""
    if trip.get("stops"):
        return trip["stops"][-1]["stop"]
    return "Unknown"


def find_routes(from_stop: str, to_stop: str, limit: int = 3) -> List[Dict]:
    """Find routes between two stops."""
    logger.info(f"Finding routes from {from_stop} to {to_stop}")
    
    routes = []
    
    try:
        # Get all lines
        lines = get_lines()
        
        for line in lines:
            line_id = line["value"]
            
            try:
                # Get itineraries for this line
                itineraries = get_itineraries(line_id)
                
                for itinerary in itineraries:
                    itinerary_value = itinerary["value"]
                    
                    try:
                        # Get periodicities (use first available)
                        periodicities = get_periodicities(line_id, itinerary_value)
                        
                        if periodicities:
                            first_periodicity = periodicities[0]["value"]
                            
                            try:
                                schedule = get_schedule(line_id, itinerary_value, first_periodicity)
                                
                                # Check each trip for direct connection
                                for trip in schedule.get("trips", []):
                                    from_found = False
                                    to_found = False
                                    from_time = None
                                    to_time = None
                                    
                                    for stop in trip["stops"]:
                                        if _similarity(stop["stop"], from_stop) > 0.8:
                                            from_found = True
                                            from_time = stop["time"]
                                        elif _similarity(stop["stop"], to_stop) > 0.8 and from_found:
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
                                            "total_time": _calculate_time_diff(from_time, to_time),
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


def _calculate_time_diff(start_time: str, end_time: str) -> int:
    """Calculate time difference in minutes."""
    try:
        start_h, start_m = map(int, start_time.split(':'))
        end_h, end_m = map(int, end_time.split(':'))
        
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        return end_minutes - start_minutes
    except:
        return 0


def find_nearby_stops(lat: float, lon: float, radius_km: float = 1.0, limit: int = 10) -> List[Dict]:
    """Find stops near a given location."""
    logger.info(f"Finding stops near {lat}, {lon} within {radius_km}km")
    
    nearby_stops = []
    stops_index = _build_stops_index()
    
    for stop_name, stop_info in stops_index.items():
        if stop_info.get("coordinates"):
            stop_coords = stop_info["coordinates"]
            distance = _calculate_distance(lat, lon, stop_coords["lat"], stop_coords["lon"])
            
            if distance <= radius_km:
                nearby_stops.append({
                    "stop": stop_info,
                    "distance_km": round(distance, 2)
                })
    
    # Sort by distance
    nearby_stops.sort(key=lambda x: x["distance_km"])
    return nearby_stops[:limit]


def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    import math
    
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


def get_service_alerts(line_id: str = None) -> List[Dict]:
    """Get service alerts, optionally filtered by line."""
    if line_id:
        return [alert for alert in _service_alerts 
                if alert["active"] and (not alert["line_ids"] or line_id in alert["line_ids"])]
    return [alert for alert in _service_alerts if alert["active"]]


def add_user_favorite(user_id: str, item_type: str, item_id: str) -> bool:
    """Add a favorite stop or line for a user."""
    if user_id not in _user_favorites:
        _user_favorites[user_id] = {"stops": [], "lines": []}
    
    if item_type == "stop" and item_id not in _user_favorites[user_id]["stops"]:
        _user_favorites[user_id]["stops"].append(item_id)
        return True
    elif item_type == "line" and item_id not in _user_favorites[user_id]["lines"]:
        _user_favorites[user_id]["lines"].append(item_id)
        return True
    
    return False


def remove_user_favorite(user_id: str, item_type: str, item_id: str) -> bool:
    """Remove a favorite stop or line for a user."""
    if user_id not in _user_favorites:
        return False
    
    try:
        if item_type == "stop" and item_id in _user_favorites[user_id]["stops"]:
            _user_favorites[user_id]["stops"].remove(item_id)
            return True
        elif item_type == "line" and item_id in _user_favorites[user_id]["lines"]:
            _user_favorites[user_id]["lines"].remove(item_id)
            return True
    except ValueError:
        pass
    
    return False


def get_user_favorites(user_id: str) -> Dict:
    """Get all favorites for a user."""
    return _user_favorites.get(user_id, {"stops": [], "lines": []})


def get_stop_accessibility_info(stop_name: str) -> Dict:
    """Get accessibility information for a stop."""
    # In a real app, this would come from a database
    # For now, return sample data
    accessibility_data = {
        "wheelchair_accessible": True,  # Default assumption
        "has_shelter": None,  # Unknown
        "has_seating": None,  # Unknown
        "tactile_paving": None,  # Unknown
        "audio_announcements": False,  # Default assumption
        "notes": "Accessibility information not yet surveyed for this stop"
    }
    
    # Some sample data for known stops
    known_accessibility = {
        "COSENZA": {
            "wheelchair_accessible": True,
            "has_shelter": True,
            "has_seating": True,
            "tactile_paving": True,
            "audio_announcements": True,
            "notes": "Fully accessible main station"
        }
    }
    
    return known_accessibility.get(stop_name, accessibility_data)


# ---------------------------------------------------------------------------
# FastAPI application

app = FastAPI(
    title="Consorzio Autolinee Cosenza Schedules API",
    description="API para consultar horarios de autobuses del Consorzio Autolinee Cosenza",
    version="2.0.0"
)


@app.get("/lines", response_model=List[LineResponse])
def list_lines():
    """Endpoint to list all bus lines.

    Returns:
        JSON array of available lines.
    """
    logger.info("API call: list_lines")
    return JSONResponse(content=get_lines())


@app.get("/itineraries/{line_id}", response_model=List[ItineraryResponse])
def list_itineraries(line_id: str):
    """Endpoint to list itineraries for a given line."""
    logger.info(f"API call: list_itineraries for line {line_id}")
    
    # Validate line_id
    if not line_id or not line_id.strip():
        raise HTTPException(status_code=400, detail="line_id no puede estar vacío")
    
    itineraries = get_itineraries(line_id.strip())
    if not itineraries:
        raise HTTPException(status_code=404, detail="Itinerari non trovati per la linea specificata.")
    return JSONResponse(content=itineraries)


@app.get("/periodicities/{line_id}/{itinerary}", response_model=List[PeriodicityResponse])
def list_periodicities(line_id: str, itinerary: str):
    """Endpoint to list periodicities for a given line and itinerary."""
    logger.info(f"API call: list_periodicities for line {line_id}, itinerary {itinerary}")
    
    # Validate inputs
    if not line_id or not line_id.strip():
        raise HTTPException(status_code=400, detail="line_id no puede estar vacío")
    if not itinerary or not itinerary.strip():
        raise HTTPException(status_code=400, detail="itinerary no puede estar vacío")
    
    periodicities = get_periodicities(line_id.strip(), itinerary.strip())
    if not periodicities:
        raise HTTPException(status_code=404, detail="Periodicità non trovate per la combinazione specificata.")
    return JSONResponse(content=periodicities)


@app.get("/schedule-structured/{line_id}/{itinerary}/{periodicity}")
def get_structured_timetable(line_id: str, itinerary: str, periodicity: str):
    """Get structured timetable data with trips and stops.
    
    This endpoint returns the properly parsed schedule as a matrix of
    trips × stops instead of a flat list of times.
    """
    logger.info(f"API call: get_structured_timetable for line {line_id}, itinerary {itinerary}, periodicity {periodicity}")
    
    # Validate inputs using Pydantic model
    try:
        request_data = ScheduleRequest(
            line_id=line_id,
            itinerary=itinerary,
            periodicity=periodicity
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Datos de entrada inválidos: {e}")
    
    try:
        schedule = get_schedule(request_data.line_id, request_data.itinerary, request_data.periodicity)
        
        # Return structured data, excluding fallback times for cleaner response
        structured_response = {
            "metadata": schedule.get("metadata", {}),
            "trips": schedule.get("trips", []),
            "stops": schedule.get("stops", []),
            "schedule_matrix": schedule.get("schedule_matrix", {}),
            "summary": {
                "trips_count": len(schedule.get("trips", [])),
                "stops_count": len(schedule.get("stops", [])),
                "has_structured_data": len(schedule.get("trips", [])) > 0
            }
        }
        
        return JSONResponse(content=structured_response)
        
    except HTTPException:
        raise


@app.get("/schedule/{line_id}/{itinerary}/{periodicity}")
def get_timetable(line_id: str, itinerary: str, periodicity: str):
    """Endpoint to fetch the timetable for the given parameters.
    
    Returns both structured data (trips/stops) and fallback flat times
    for backward compatibility.
    """
    logger.info(f"API call: get_timetable for line {line_id}, itinerary {itinerary}, periodicity {periodicity}")
    
    # Validate inputs using Pydantic model
    try:
        request_data = ScheduleRequest(
            line_id=line_id,
            itinerary=itinerary,
            periodicity=periodicity
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Datos de entrada inválidos: {e}")
    
    try:
        schedule = get_schedule(request_data.line_id, request_data.itinerary, request_data.periodicity)
        
        # For backward compatibility, if no structured data, return fallback format
        if not schedule.get("trips") and "fallback_times" in schedule:
            return JSONResponse(content=schedule["fallback_times"])
        
        # Return full structured response
        return JSONResponse(content=schedule)
        
    except HTTPException:
        raise


@app.get("/search/stops")
def search_stops_endpoint(q: str = Query(..., description="Search query for stop names"), 
                         limit: int = Query(10, description="Maximum number of results")):
    """Search stops by name with fuzzy matching.
    
    Returns stops that match the search query, ordered by relevance.
    """
    logger.info(f"API call: search_stops with query '{q}'")
    
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
    
    try:
        results = search_stops(q, limit)
        return JSONResponse(content={
            "query": q,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error searching stops: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching stops: {str(e)}")


@app.get("/stops/{stop_name}/next-departures")
def get_stop_departures(stop_name: str, limit: int = Query(5, description="Maximum number of departures")):
    """Get next departures from a specific stop.
    
    Returns upcoming bus departures from the specified stop.
    """
    logger.info(f"API call: get_stop_departures for '{stop_name}'")
    
    try:
        departures = get_next_departures(stop_name, limit)
        return JSONResponse(content={
            "stop_name": stop_name,
            "departures": departures,
            "count": len(departures)
        })
    except Exception as e:
        logger.error(f"Error getting departures: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting departures: {str(e)}")


@app.get("/routes/plan")
def plan_route(from_stop: str = Query(..., description="Origin stop name"),
               to_stop: str = Query(..., description="Destination stop name"),
               limit: int = Query(3, description="Maximum number of route options")):
    """Find routes between two stops.
    
    Returns possible routes from origin to destination.
    """
    logger.info(f"API call: plan_route from '{from_stop}' to '{to_stop}'")
    
    if not from_stop.strip() or not to_stop.strip():
        raise HTTPException(status_code=400, detail="Both from_stop and to_stop are required")
    
    try:
        routes = find_routes(from_stop, to_stop, limit)
        return JSONResponse(content={
            "from_stop": from_stop,
            "to_stop": to_stop,
            "routes": routes,
            "count": len(routes)
        })
    except Exception as e:
        logger.error(f"Error planning route: {e}")
        raise HTTPException(status_code=500, detail=f"Error planning route: {str(e)}")


@app.get("/stops/all")
def get_all_stops():
    """Get all available stops with their associated lines.
    
    Returns a complete index of all stops in the system.
    """
    logger.info("API call: get_all_stops")
    
    try:
        stops_index = _build_stops_index()
        return JSONResponse(content={
            "stops": list(stops_index.values()),
            "count": len(stops_index)
        })
    except Exception as e:
        logger.error(f"Error getting all stops: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting all stops: {str(e)}")


@app.get("/stops/nearby")
def get_nearby_stops(lat: float = Query(..., description="Latitude"),
                    lon: float = Query(..., description="Longitude"),
                    radius: float = Query(1.0, description="Search radius in kilometers"),
                    limit: int = Query(10, description="Maximum number of results")):
    """Find stops near a given location.
    
    Returns stops within the specified radius, ordered by distance.
    """
    logger.info(f"API call: get_nearby_stops at {lat}, {lon}")
    
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    
    try:
        nearby = find_nearby_stops(lat, lon, radius, limit)
        return JSONResponse(content={
            "location": {"lat": lat, "lon": lon},
            "radius_km": radius,
            "nearby_stops": nearby,
            "count": len(nearby)
        })
    except Exception as e:
        logger.error(f"Error finding nearby stops: {e}")
        raise HTTPException(status_code=500, detail=f"Error finding nearby stops: {str(e)}")


@app.get("/alerts")
def get_alerts(line_id: str = Query(None, description="Filter by line ID")):
    """Get service alerts.
    
    Returns active service alerts, optionally filtered by line.
    """
    logger.info(f"API call: get_alerts for line {line_id}")
    
    try:
        alerts = get_service_alerts(line_id)
        return JSONResponse(content={
            "alerts": alerts,
            "count": len(alerts),
            "filtered_by_line": line_id
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")


@app.get("/stops/{stop_name}/accessibility")
def get_stop_accessibility(stop_name: str):
    """Get accessibility information for a stop.
    
    Returns accessibility features and information for the specified stop.
    """
    logger.info(f"API call: get_stop_accessibility for '{stop_name}'")
    
    try:
        accessibility = get_stop_accessibility_info(stop_name)
        return JSONResponse(content={
            "stop_name": stop_name,
            "accessibility": accessibility
        })
    except Exception as e:
        logger.error(f"Error getting accessibility info: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting accessibility info: {str(e)}")


@app.get("/users/{user_id}/favorites")
def get_favorites(user_id: str):
    """Get user's favorite stops and lines.
    
    Returns all favorites for the specified user.
    """
    logger.info(f"API call: get_favorites for user {user_id}")
    
    try:
        favorites = get_user_favorites(user_id)
        return JSONResponse(content={
            "user_id": user_id,
            "favorites": favorites
        })
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting favorites: {str(e)}")


@app.post("/users/{user_id}/favorites")
def add_favorite(user_id: str, 
                item_type: str = Query(..., description="Type: 'stop' or 'line'"),
                item_id: str = Query(..., description="Stop name or line ID")):
    """Add a favorite stop or line for a user.
    
    Adds the specified stop or line to the user's favorites.
    """
    logger.info(f"API call: add_favorite for user {user_id}, type {item_type}, id {item_id}")
    
    if item_type not in ["stop", "line"]:
        raise HTTPException(status_code=400, detail="item_type must be 'stop' or 'line'")
    
    try:
        success = add_user_favorite(user_id, item_type, item_id)
        if success:
            return JSONResponse(content={
                "message": f"Added {item_type} '{item_id}' to favorites",
                "user_id": user_id,
                "item_type": item_type,
                "item_id": item_id
            })
        else:
            return JSONResponse(content={
                "message": f"{item_type} '{item_id}' already in favorites",
                "user_id": user_id
            })
    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding favorite: {str(e)}")


@app.delete("/users/{user_id}/favorites")
def remove_favorite(user_id: str,
                   item_type: str = Query(..., description="Type: 'stop' or 'line'"),
                   item_id: str = Query(..., description="Stop name or line ID")):
    """Remove a favorite stop or line for a user.
    
    Removes the specified stop or line from the user's favorites.
    """
    logger.info(f"API call: remove_favorite for user {user_id}, type {item_type}, id {item_id}")
    
    if item_type not in ["stop", "line"]:
        raise HTTPException(status_code=400, detail="item_type must be 'stop' or 'line'")
    
    try:
        success = remove_user_favorite(user_id, item_type, item_id)
        if success:
            return JSONResponse(content={
                "message": f"Removed {item_type} '{item_id}' from favorites",
                "user_id": user_id
            })
        else:
            return JSONResponse(content={
                "message": f"{item_type} '{item_id}' not found in favorites",
                "user_id": user_id
            }, status_code=404)
    except Exception as e:
        logger.error(f"Error removing favorite: {e}")
        raise HTTPException(status_code=500, detail=f"Error removing favorite: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Consorzio Autolinee API"}


@app.get("/test-flow/{line_id}")
def test_complete_flow(line_id: str):
    """Test endpoint to verify the complete flow for a specific line.
    
    This endpoint helps debug the entire process:
    1. Get itineraries for the line
    2. Get periodicities for the first itinerary
    3. Get schedule for the first periodicity
    
    Useful for testing and understanding the data structure.
    """
    logger.info(f"Testing complete flow for line {line_id}")
    
    try:
        # Step 1: Get itineraries
        itineraries = get_itineraries(line_id)
        if not itineraries:
            return {"error": f"No itineraries found for line {line_id}"}
        
        first_itinerary = itineraries[0]
        logger.info(f"Using first itinerary: {first_itinerary}")
        
        # Step 2: Get periodicities (use VALUE, not label)
        periodicities = get_periodicities(line_id, first_itinerary["value"])
        if not periodicities:
            return {"error": f"No periodicities found for line {line_id}, itinerary {first_itinerary['value']}"}
        
        first_periodicity = periodicities[0]
        logger.info(f"Using first periodicity: {first_periodicity}")
        
        # Step 3: Get schedule (use VALUES for all parameters)
        try:
            schedule = get_schedule(line_id, first_itinerary["value"], first_periodicity["value"])
            
            # Create summary of structured data
            schedule_summary = {
                "metadata": schedule.get("metadata", {}),
                "trips_count": len(schedule.get("trips", [])),
                "stops_count": len(schedule.get("stops", [])),
                "raw_times_count": schedule.get("raw_times_count", 0),
                "has_structured_data": len(schedule.get("trips", [])) > 0,
                "sample_trips": schedule.get("trips", [])[:2],  # First 2 trips
                "sample_stops": [s["name"] for s in schedule.get("stops", [])][:5]  # First 5 stops
            }
            
            # Include fallback data if structured parsing failed
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


@app.get("/debug/values/{line_id}")
def debug_values(line_id: str):
    """Debug endpoint to see the correct values to use for a line.
    
    This shows the exact values you should use in URLs, not the labels.
    """
    logger.info(f"Debug values for line {line_id}")
    
    try:
        # Get itineraries
        itineraries = get_itineraries(line_id)
        if not itineraries:
            return {"error": f"No itineraries found for line {line_id}"}
        
        result = {
            "line_id": line_id,
            "itineraries": itineraries,
            "periodicities_by_itinerary": {},
            "example_urls": []
        }
        
        # Get periodicities for each itinerary
        for itinerary in itineraries:
            itinerary_value = itinerary["value"]
            try:
                periodicities = get_periodicities(line_id, itinerary_value)
                result["periodicities_by_itinerary"][itinerary_value] = periodicities
                
                # Generate example URLs
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


@app.get("/debug/raw-pdf/{line_id}/{itinerary}/{periodicity}")
def debug_raw_pdf(line_id: str, itinerary: str, periodicity: str):
    """Debug endpoint to see exactly what the server returns for PDF requests.
    
    This endpoint shows the raw response without processing, useful for debugging
    PDF parsing issues.
    """
    logger.info(f"Debug raw PDF for line {line_id}, itinerary {itinerary}, periodicity {periodicity}")
    
    payload = {
        "linea": line_id,
        "itinerario": itinerary,
        "periodicita": periodicity,
    }
    
    try:
        resp = requests.post(PDF_ENDPOINT, data=payload, timeout=REQUEST_TIMEOUT)
        
        content_type = resp.headers.get("Content-Type", "")
        content_length = len(resp.content)
        
        # Find PDF start
        pdf_start = resp.content.find(b'%PDF-')
        
        # Decode content preview safely
        try:
            content_preview = resp.content[:500].decode('utf-8', errors='replace')
        except:
            content_preview = str(resp.content[:500])
        
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "content_type": content_type,
            "content_length": content_length,
            "pdf_start_position": pdf_start,
            "content_preview": content_preview,
            "payload_sent": payload,
            "has_pdf_magic": b'%PDF-' in resp.content,
            "starts_with_pdf": resp.content.startswith(b'%PDF-')
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch raw PDF: {str(e)}"}


# Clear cache endpoint for development/debugging
@app.post("/admin/clear-cache")
def clear_cache():
    """Clear all cached data."""
    logger.info("Clearing cache")
    get_lines.cache_clear()
    get_itineraries.cache_clear()
    get_periodicities.cache_clear()
    return {"message": "Cache cleared successfully"}
