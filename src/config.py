"""
Configuration settings for the Consorzio Autolinee API.
"""

import os
import logging
from typing import Dict, Any

# Environment variables for configuration
BASE_URL = os.getenv("CONSORZIO_BASE_URL", "https://www.consorzioautolineetpl.it")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "100"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# API endpoints
LINES_PAGE = f"{BASE_URL}/quadro_orario.php"
SELECT_ENDPOINT = f"{BASE_URL}/select.ajaxlinea.php"
PDF_ENDPOINT = f"{BASE_URL}/download_quadro_orari.php"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sample coordinates - in production, these would come from a database
STOPS_COORDINATES: Dict[str, Dict[str, float]] = {
    # Main cities and towns
    "COSENZA": {"lat": 39.2986, "lon": 16.2540},
    "RENDE": {"lat": 39.3167, "lon": 16.2333},
    "SCALEA": {"lat": 39.8167, "lon": 15.7833},
    "PAOLA": {"lat": 39.3667, "lon": 15.9833},
    "AMANTEA": {"lat": 39.1333, "lon": 16.0667},
    "LAMEZIA TERME": {"lat": 38.9667, "lon": 16.3167},
    
    # Coastal towns
    "ORSOMARSO": {"lat": 39.7833, "lon": 15.8167},
    "MARCELLINA": {"lat": 39.8000, "lon": 15.8000},
    "PRAIA A MARE": {"lat": 39.8833, "lon": 15.7833},
    "TORTORA": {"lat": 39.9167, "lon": 15.8000},
    "BELVEDERE MARITTIMO": {"lat": 39.6333, "lon": 15.8500},
    "CETRARO": {"lat": 39.5167, "lon": 15.9333},
    "GUARDIA PIEMONTESE": {"lat": 39.4833, "lon": 15.9667},
    "FUSCALDO": {"lat": 39.4000, "lon": 15.9833},
    
    # Mountain towns
    "MORANO CALABRO": {"lat": 39.8500, "lon": 16.1333},
    "CASTROVILLARI": {"lat": 39.8167, "lon": 16.2000},
    "SPEZZANO ALBANESE": {"lat": 39.7000, "lon": 16.3167},
    "CASSANO ALLO IONIO": {"lat": 39.7833, "lon": 16.3167},
    
    # University and key locations
    "UNICAL": {"lat": 39.3583, "lon": 16.2278},  # University of Calabria
    "OSPEDALE COSENZA": {"lat": 39.3000, "lon": 16.2600},
    "STAZIONE COSENZA": {"lat": 39.2944, "lon": 16.2511},  # Train station
    "CENTRO STORICO COSENZA": {"lat": 39.2975, "lon": 16.2542},
    
    # Shopping and commercial areas
    "CENTRO COMMERCIALE": {"lat": 39.3100, "lon": 16.2400},
    "QUATTROMIGLIA": {"lat": 39.3200, "lon": 16.2300},
    
    # Smaller towns and villages
    "ROSE": {"lat": 39.3833, "lon": 16.2833},
    "MONTALTO UFFUGO": {"lat": 39.4000, "lon": 16.1667},
    "SAN VINCENZO LA COSTA": {"lat": 39.3333, "lon": 16.2167},
    "BISIGNANO": {"lat": 39.5000, "lon": 16.2833},
    "ACRI": {"lat": 39.4833, "lon": 16.3833},
    "SAN DEMETRIO CORONE": {"lat": 39.6000, "lon": 16.3500}
}

# Service alerts - in production, these would come from a database
SERVICE_ALERTS = [
    {
        "id": "alert_001",
        "line_ids": ["139"],
        "type": "delay",
        "title": "Ritardi sulla linea 139",
        "message": "Possibili ritardi di 10-15 minuti a causa di traffico intenso",
        "severity": "medium",
        "active": True,
        "created_at": "2026-03-03T10:00:00Z"
    },
    {
        "id": "alert_002", 
        "line_ids": [],
        "type": "maintenance",
        "title": "Manutenzione programmata",
        "message": "Domenica 7 marzo servizio ridotto dalle 06:00 alle 10:00",
        "severity": "low",
        "active": True,
        "created_at": "2026-03-03T08:00:00Z"
    }
]

# Accessibility data - in production, this would come from a database
ACCESSIBILITY_DATA: Dict[str, Dict[str, Any]] = {
    "COSENZA": {
        "wheelchair_accessible": True,
        "has_shelter": True,
        "has_seating": True,
        "tactile_paving": True,
        "audio_announcements": True,
        "notes": "Stazione principale completamente accessibile"
    },
    "RENDE": {
        "wheelchair_accessible": True,
        "has_shelter": True,
        "has_seating": True,
        "tactile_paving": False,
        "audio_announcements": False,
        "notes": "Accessibile con rampe, ma senza pavimentazione tattile"
    },
    "SCALEA": {
        "wheelchair_accessible": False,
        "has_shelter": False,
        "has_seating": False,
        "tactile_paving": False,
        "audio_announcements": False,
        "notes": "Fermata non accessibile, necessari miglioramenti"
    }
}

# Default accessibility info for unknown stops
DEFAULT_ACCESSIBILITY = {
    "wheelchair_accessible": None,
    "has_shelter": None,
    "has_seating": None,
    "tactile_paving": None,
    "audio_announcements": None,
    "notes": "Informazioni di accessibilità non ancora disponibili per questa fermata"
}