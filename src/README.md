# Estructura del Código Fuente

Esta carpeta contiene todo el código fuente modular de la API.

## 📁 Archivos

### `config.py`
**Configuración y constantes**

- Variables de entorno
- URLs de endpoints del Consorzio
- Coordenadas GPS de paradas
- Alertas de servicio
- Datos de accesibilidad
- Configuración de logging

```python
from src.config import STOPS_COORDINATES, SERVICE_ALERTS
```

---

### `models.py`
**Modelos Pydantic para validación**

Define los esquemas de datos para:
- Requests (ScheduleRequest)
- Responses (LineResponse, ItineraryResponse, etc.)
- Entidades (StopInfo, NextDeparture, RouteStep, etc.)

```python
from src.models import ScheduleRequest, LineResponse
```

---

### `utils.py`
**Funciones utilitarias**

Funciones auxiliares para:
- Cálculo de similitud de strings
- Cálculo de distancias (Haversine)
- Cálculo de diferencias de tiempo
- Extracción de patrones de tiempo
- Validación de coordenadas
- Limpieza de nombres de paradas

```python
from src.utils import similarity, calculate_distance
```

---

### `consorzio_client.py`
**Cliente HTTP para el sitio web del Consorzio**

Clase `ConsorzioClient` que maneja:
- Peticiones HTTP al sitio web
- Parsing de HTML con BeautifulSoup
- Descarga de PDFs
- Validación de respuestas
- Manejo de errores de red

```python
from src.consorzio_client import ConsorzioClient

client = ConsorzioClient()
lines = client.get_lines()
```

---

### `pdf_parser.py`
**Parser de PDFs de horarios**

Clase `PDFScheduleParser` que:
- Extrae tablas de PDFs con pdfplumber
- Parsea estructura matricial (viajes × paradas)
- Extrae metadata (línea, dirección, periodicidad)
- Maneja fallback a extracción simple de tiempos
- Filtra filas técnicas

```python
from src.pdf_parser import PDFScheduleParser

parser = PDFScheduleParser()
schedule = parser.parse_schedule(pdf_bytes)
```

---

### `services.py`
**Lógica de negocio**

Clase `ConsorzioService` que implementa:
- Búsqueda de paradas
- Próximas salidas
- Planificación de rutas
- Paradas cercanas
- Selección inteligente de periodicidad
- Gestión de favoritos
- Información de accesibilidad
- Navegación a paradas

```python
from src.services import ConsorzioService

service = ConsorzioService()
stops = service.search_stops("cosenza")
```

---

### `frontend_api.py`
**Endpoints compatibles con el frontend**

Router FastAPI con endpoints `/api/*`:
- Conversión de formatos backend → frontend
- Generación de IDs consistentes
- Enriquecimiento de datos (coordenadas, colores)
- Adaptación a interfaces TypeScript del frontend

```python
from src.frontend_api import router

app.include_router(router)
```

---

## 🔄 Flujo de Datos

```
Frontend Request
    ↓
frontend_api.py (conversión de formato)
    ↓
services.py (lógica de negocio)
    ↓
consorzio_client.py (peticiones HTTP)
    ↓
pdf_parser.py (parsing de PDFs)
    ↓
models.py (validación)
    ↓
utils.py (cálculos auxiliares)
    ↓
config.py (configuración y datos)
```

---

## 🏗️ Arquitectura

### Capa de Presentación
- `frontend_api.py`: Endpoints REST para el frontend

### Capa de Negocio
- `services.py`: Lógica de aplicación

### Capa de Datos
- `consorzio_client.py`: Acceso a datos externos
- `pdf_parser.py`: Procesamiento de documentos

### Capa de Soporte
- `models.py`: Validación y esquemas
- `utils.py`: Funciones auxiliares
- `config.py`: Configuración

---

## 🔧 Extensibilidad

### Agregar Nueva Funcionalidad

1. **Agregar endpoint frontend**:
   - Editar `frontend_api.py`
   - Agregar ruta con `@router.get()` o `@router.post()`

2. **Agregar lógica de negocio**:
   - Editar `services.py`
   - Agregar método a `ConsorzioService`

3. **Agregar modelo de datos**:
   - Editar `models.py`
   - Crear clase Pydantic

4. **Agregar utilidad**:
   - Editar `utils.py`
   - Agregar función auxiliar

5. **Agregar configuración**:
   - Editar `config.py`
   - Agregar constante o variable de entorno

---

## 📝 Convenciones

### Nombres de Funciones
- `get_*`: Obtener datos
- `search_*`: Buscar con filtros
- `find_*`: Encontrar con criterios
- `calculate_*`: Cálculos
- `validate_*`: Validaciones
- `_private_*`: Funciones privadas (prefijo `_`)

### Nombres de Clases
- `*Client`: Clientes HTTP
- `*Parser`: Parsers de datos
- `*Service`: Servicios de negocio
- `*Request`: Modelos de request
- `*Response`: Modelos de response

### Logging
```python
logger.info("Operación normal")
logger.debug("Información detallada")
logger.warning("Advertencia")
logger.error("Error")
```

---

## 🧪 Testing

Cada módulo puede ser probado independientemente:

```python
# Test config
from src.config import STOPS_COORDINATES
assert "COSENZA" in STOPS_COORDINATES

# Test utils
from src.utils import similarity
assert similarity("cosenza", "COSENZA") > 0.9

# Test client
from src.consorzio_client import ConsorzioClient
client = ConsorzioClient()
lines = client.get_lines()
assert len(lines) > 0

# Test service
from src.services import ConsorzioService
service = ConsorzioService()
stops = service.search_stops("cosenza")
assert len(stops) > 0
```

---

## 📚 Dependencias

### Externas
- `fastapi`: Framework web
- `pydantic`: Validación de datos
- `requests`: Cliente HTTP
- `beautifulsoup4`: Parsing HTML
- `pdfplumber`: Parsing PDF

### Internas
- Cada módulo importa solo lo que necesita
- Sin dependencias circulares
- Imports relativos dentro de `src/`

---

## 🔒 Seguridad

### Validación de Entrada
- Todos los endpoints usan modelos Pydantic
- Validación de coordenadas GPS
- Sanitización de nombres de paradas

### Manejo de Errores
- Try-catch en operaciones críticas
- Logging de errores
- Respuestas HTTP apropiadas

### Rate Limiting
- Implementar en producción
- Usar Redis o similar
- Configurar por IP o usuario

---

## 🚀 Performance

### Caché
- LRU cache en funciones costosas
- Cache de líneas, itinerarios, periodicidades
- Cache del índice de paradas

### Optimizaciones
- Búsqueda con índices
- Cálculos lazy cuando sea posible
- Reutilización de conexiones HTTP

---

## 📖 Documentación

Cada función y clase tiene docstrings:

```python
def search_stops(self, query: str, limit: int = 10) -> List[Dict]:
    """
    Search stops by name with fuzzy matching.
    
    Args:
        query: Search text
        limit: Maximum number of results
        
    Returns:
        List of matching stops with similarity scores
    """
```

---

## 🤝 Contribuir

Al agregar código:

1. Seguir las convenciones de nombres
2. Agregar docstrings
3. Agregar logging apropiado
4. Manejar errores
5. Agregar tests si es posible
6. Actualizar esta documentación

---

**Estructura clara = Código mantenible** ✨
