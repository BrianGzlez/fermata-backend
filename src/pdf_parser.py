"""
PDF parsing functionality for extracting structured schedule data.
"""

import io
import logging
from typing import List, Dict
import pdfplumber
from fastapi import HTTPException

from .utils import TIME_PATTERN, is_technical_row, extract_times_from_text

logger = logging.getLogger(__name__)


class PDFScheduleParser:
    """Parser for extracting structured schedule data from PDF files."""
    
    def parse_schedule(self, pdf_bytes: bytes) -> Dict:
        """Extract structured timetable from a PDF."""
        logger.info("Parsing structured PDF schedule")
        
        result = {
            "metadata": {},
            "trips": [],
            "stops": [],
            "schedule_matrix": {},
            "raw_times_count": 0
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
                                result = self._process_schedule_table(table, result, page_num)
                    except Exception as e:
                        logger.warning(f"Could not extract tables from page {page_num}: {e}")
                
                # Extract metadata from text
                result["metadata"] = self._extract_metadata_from_text(all_text_lines)
                
                # Extract all times for backward compatibility
                all_times = TIME_PATTERN.findall('\n'.join(all_text_lines))
                result["raw_times_count"] = len(all_times)
                
                # If no structured data was found, fall back to simple time extraction
                if not result["trips"] and not result["stops"]:
                    logger.warning("No structured data found, falling back to simple time extraction")
                    result["fallback_times"] = self._extract_fallback_times(pdf)
                
        except Exception as exc:
            logger.error(f"Error parsing PDF: {exc}")
            raise HTTPException(status_code=500, detail=f"Errore nel parsing del PDF: {exc}")
        
        return result
    
    def _extract_metadata_from_text(self, lines: List[str]) -> Dict[str, str]:
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
    
    def _process_schedule_table(self, table: List[List[str]], result: Dict, page_num: int) -> Dict:
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
            if is_technical_row(stop_name):
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
    
    def _extract_fallback_times(self, pdf) -> Dict[str, List[str]]:
        """Extract times as fallback when structured parsing fails."""
        fallback_times = {}
        
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            times = extract_times_from_text(text)
            fallback_times[str(index)] = times
            logger.debug(f"Page {index}: found {len(times)} unique times")
        
        return fallback_times