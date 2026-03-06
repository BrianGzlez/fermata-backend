#!/usr/bin/env python3
"""
Script para ejecutar el servidor de desarrollo con configuración personalizada.
"""

import os
import uvicorn
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "main:app",  # Changed from "app:app" to "main:app"
        host=host,
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )