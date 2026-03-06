"""
Client for interacting with the Consorzio Autolinee website.
"""

import logging
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from fastapi import HTTPException

from .config import LINES_PAGE, SELECT_ENDPOINT, PDF_ENDPOINT, REQUEST_TIMEOUT
from .utils import extract_times_from_text

logger = logging.getLogger(__name__)


class ConsorzioClient:
    """Client for fetching data from Consorzio Autolinee website."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ConsorzioAPI/2.1.0)'
        })
    
    def _get_soup_from_url(self, url: str) -> BeautifulSoup:
        """Helper to fetch a URL and return a BeautifulSoup object."""
        logger.info(f"Fetching URL: {url}")
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            logger.info(f"Request to {url} completed with status {resp.status_code}")
        except requests.RequestException as exc:
            logger.error(f"Request failed for {url}: {exc}")
            raise HTTPException(status_code=500, detail=f"Errore nel recuperare {url}: {exc}")
        
        if resp.status_code != 200:
            logger.error(f"Unexpected response from {url}: {resp.status_code}")
            raise HTTPException(status_code=resp.status_code, detail=f"Risposta inattesa da {url}: {resp.status_code}")
        
        return BeautifulSoup(resp.text, "html.parser")
    
    def _post_select(self, params: Dict[str, str]) -> List[Dict[str, str]]:
        """Internal helper to call the select.ajaxlinea.php endpoint."""
        logger.info(f"Making POST request to select endpoint with params: {params}")
        try:
            resp = self.session.post(SELECT_ENDPOINT, data=params, timeout=REQUEST_TIMEOUT)
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
    
    def get_lines(self) -> List[Dict[str, str]]:
        """Retrieve the list of available bus lines."""
        logger.info("Fetching available bus lines")
        soup = self._get_soup_from_url(LINES_PAGE)
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
    
    def get_itineraries(self, line_id: str) -> List[Dict[str, str]]:
        """Fetch itineraries for a given line."""
        logger.info(f"Fetching itineraries for line {line_id}")
        params = {"id": line_id, "tipo": "ITINERARIO"}
        return self._post_select(params)
    
    def get_periodicities(self, line_id: str, itinerary: str) -> List[Dict[str, str]]:
        """Fetch periodicity options for a given line and itinerary."""
        logger.info(f"Fetching periodicities for line {line_id}, itinerary {itinerary}")
        params = {
            "id": line_id,
            "id_itinerario": itinerary,
            "tipo": "PERIODICITA",
        }
        periodicities = self._post_select(params)
        
        # If no periodicities found, return default
        if not periodicities:
            logger.info("No periodicities found, using default 'F'")
            return [{"value": "F", "label": "Feriale (Giorni lavorativi)"}]
        
        return periodicities
    
    def download_pdf(self, line_id: str, itinerary: str, periodicity: str) -> bytes:
        """Download PDF schedule for given parameters."""
        logger.info(f"Downloading PDF for line {line_id}, itinerary {itinerary}, periodicity {periodicity}")
        
        payload = {
            "linea": line_id,
            "itinerario": itinerary,
            "periodicita": periodicity,
        }
        logger.debug(f"Payload sent to download_quadro_orari.php: {payload}")
        
        try:
            resp = self.session.post(PDF_ENDPOINT, data=payload, timeout=REQUEST_TIMEOUT)
            logger.info(f"PDF download request completed with status {resp.status_code}")
        except requests.RequestException as exc:
            logger.error(f"PDF download failed: {exc}")
            raise HTTPException(status_code=500, detail=f"Errore durante il download del PDF: {exc}")
        
        if resp.status_code != 200:
            logger.error(f"PDF download failed with status {resp.status_code}")
            raise HTTPException(status_code=resp.status_code, detail=f"Impossibile scaricare il PDF: {resp.status_code}")
        
        content_type = resp.headers.get("Content-Type", "").lower()
        content_length = len(resp.content)
        content_preview = resp.content[:50]
        
        logger.debug(f"Response Content-Type: {content_type}")
        logger.debug(f"Response Content-Length: {content_length}")
        logger.debug(f"Response Content Preview: {content_preview}")
        
        # Validate PDF content
        self._validate_pdf_content(resp.content, content_type)
        
        return resp.content
    
    def _validate_pdf_content(self, content: bytes, content_type: str) -> bytes:
        """Validate and extract PDF content from response."""
        # Find PDF start position
        pdf_start = content.find(b'%PDF-')
        
        if pdf_start == -1:
            logger.error("Content does not contain PDF magic bytes anywhere")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "El contenido no contiene un PDF válido (no se encontró %PDF-)",
                    "content_type": content_type,
                    "content_preview": content[:200].decode('utf-8', errors='ignore')
                }
            )
        
        # If PDF starts after some HTML errors, extract just the PDF part
        if pdf_start > 0:
            logger.warning(f"PDF content starts at byte {pdf_start}, extracting PDF portion")
            logger.debug(f"Skipped content: {content[:pdf_start].decode('utf-8', errors='ignore')}")
            return content[pdf_start:]
        
        return content