# Consorzio Autolinee Cosenza API 🚌

API completa y moderna para consultar horarios de autobuses del Consorzio Autolinee Cosenza con funcionalidades avanzadas de búsqueda, planificación de rutas y gestión de usuarios.

**✨ NUEVA VERSIÓN 2.2.0: Integración Completa con Frontend Fermati**

[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

## 🎉 **NUEVO: API Compatible con Frontend Next.js** ⭐

La API ahora incluye endpoints completamente compatibles con el frontend **Fermati** (Next.js 14 + TypeScript).

### **Endpoints Frontend-Ready** (`/api/*`)

Todos los endpoints que el frontend necesita están implementados y listos:

- ✅ **GET** `/api/stops/search` - Búsqueda de paradas (texto + GPS)
- ✅ **GET** `/api/stops/{stopId}` - Detalle de parada por ID
- ✅ **GET** `/api/stops/{stopId}/departures` - Próximas salidas
- ✅ **GET** `/api/routes/plan` - Calcular rutas entre paradas
- ✅ **GET** `/api/routes/{routeId}` - Información de línea
- ✅ **GET** `/api/routes/{routeId}/schedule` - Horarios de línea
- ✅ **GET** `/api/routes` - Todas las líneas
- ✅ **GET** `/api/alerts` - Alertas de servicio

📖 **Ver documentación completa**: [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md)

## 🎯 **NUEVA FUNCIONALIDAD: Periodicidad Inteligente** ⭐

### **Problema Resuelto:**
Antes la API devolvía todos los horarios del año, pero los usuarios necesitan saber **qué autobuses pasan HOY**.

### **Solución Automática:**
La API ahora determina automáticamente qué periodicidad usar según la fecha:

- **Lunes-Viernes (período escolar)**: Horarios escolásticos
- **Lunes-Viernes (vacaciones)**: Horarios no escolásticos  
- **Fines de semana**: Horarios festivos
- **Agosto**: Horarios de verano
- **Días festivos**: Horarios festivos

### **Nuevos Endpoints Inteligentes:**

```bash
# Próximas salidas CON periodicidad automática
GET /stops/{stop_name}/next-departures?date=2026-03-05

# Horario CON periodicidad automática
GET /schedule-smart/{line_id}/{itinerary}?date=2026-03-05

# Ver qué periodicidad se usará para una fecha
GET /periodicity/current?line_id=139&itinerary=139A&date=2026-03-05
```

### **Ejemplo de Respuesta Mejorada:**
```json
{
  "stop_name": "COSENZA",
  "target_date": "2026-03-05",
  "departures": [
    {
      "line_id": "139",
      "departure_time": "14:25",
      "destination": "SCALEA",
      "periodicity": "Scolastico",
      "periodicity_value": "SCO",
      "is_today": true
    }
  ]
}
```

### **🔥 Funcionalidades Esenciales**
- 🔍 **Búsqueda inteligente de paradas** con coincidencia difusa
- 🚌 **Próximas salidas** desde cualquier parada
- 🗺️ **Planificador de rutas** entre dos puntos
- 📍 **Paradas cercanas** basado en GPS
- 📊 **Horarios estructurados** (viajes × paradas)

### **⚡ Funcionalidades Avanzadas**
- 🚨 **Alertas de servicio** (retrasos, desvíos, huelgas)
- ♿ **Información de accesibilidad** de paradas
- ⭐ **Sistema de favoritos** por usuario
- 🏷️ **API organizada por tags** para mejor navegación


### **🛠️ Características Técnicas**
- 📁 **Arquitectura modular** bien organizada
- ⚡ **Cache LRU** para alto rendimiento
- 🛡️ **Validación robusta** con Pydantic
- 📝 **Logging detallado** para debugging
- 🧪 **Suite de tests** completa
- 📚 **Documentación automática** con Swagger UI

## 📦 Instalación Rápida

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd consorzio-autolinee-api

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar entorno
cp .env.example .env

# 4. Ejecutar servidor
python run.py
```

### **Verificar Instalación**
```bash
# Verificar que funciona
curl http://localhost:8000/health

# Ver documentación interactiva
open http://localhost:8000/docs

# Probar endpoint del frontend
curl "http://localhost:8000/api/stops/search?query=cosenza"
```

### **🔗 Conectar con Frontend Next.js**

En tu aplicación Next.js, configura:

```env
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_MODE=real
```

```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export const apiClient = {
  searchStops: async (query: string) => {
    const res = await fetch(`${API_BASE_URL}/api/stops/search?query=${query}`);
    return res.json();
  },
  
  getDepartures: async (stopId: string) => {
    const res = await fetch(`${API_BASE_URL}/api/stops/${stopId}/departures`);
    return res.json();
  },
  
  planRoute: async (from: string, to: string) => {
    const res = await fetch(`${API_BASE_URL}/api/routes/plan?from=${from}&to=${to}`);
    return res.json();
  }
};
```

📖 **Guía completa de integración**: [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md)

## 🔧 Configuración

### Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `CONSORZIO_BASE_URL` | URL base del servicio | `https://www.consorzioautolineetpl.it` |
| `REQUEST_TIMEOUT` | Timeout para requests HTTP (segundos) | `30` |
| `CACHE_SIZE` | Tamaño del cache LRU | `100` |
| `LOG_LEVEL` | Nivel de logging (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `HOST` | Host del servidor | `127.0.0.1` |
| `PORT` | Puerto del servidor | `8000` |

### Niveles de Logging

- **DEBUG**: Información muy detallada (incluye tiempos encontrados por página)
- **INFO**: Información general de operaciones
- **WARNING**: Advertencias
- **ERROR**: Solo errores

## 📚 Documentación de la API

### **🔗 Endpoints Principales**

| Categoría | Endpoint | Descripción |
|-----------|----------|-------------|
| **Core** | `GET /lines` | Obtener todas las líneas |
| **Core** | `GET /itineraries/{line_id}` | Itinerarios de una línea |
| **Core** | `GET /schedule/{line_id}/{itinerary}/{periodicity}` | Horario estructurado |
| **Core** | `GET /schedule-smart/{line_id}/{itinerary}?date=YYYY-MM-DD` | **Horario con periodicidad automática** |
| **Core** | `GET /periodicity/current?line_id=X&itinerary=Y&date=Z` | **Qué periodicidad usar hoy** |
| **Search** | `GET /search/stops?q={query}` | Buscar paradas |
| **Search** | `GET /stops/{stop_name}/next-departures?date=YYYY-MM-DD` | **Próximas salidas inteligentes** |
| **Search** | `GET /routes/plan?from_stop=A&to_stop=B` | Planificar ruta |
| **Location** | `GET /stops/nearby?lat={lat}&lon={lon}` | Paradas cercanas |
| **Location** | `GET /stops/{stop_name}/navigation?user_lat=X&user_lon=Y` | **Navegación a parada específica** |
| **Location** | `GET /routes/{route_id}/navigation?user_lat=X&user_lon=Y` | **Navegación a ruta planificada** |
| **Location** | `GET /stops/nearest-with-line?user_lat=X&user_lon=Y&line_id=Z` | **Paradas cercanas con línea específica** |
| **Service** | `GET /alerts` | Alertas de servicio |
| **Users** | `GET /users/{user_id}/favorites` | Favoritos de usuario |

### **🎯 Ejemplos de Uso**

```bash
# Buscar paradas que contengan "cosenza"
curl "http://localhost:8000/search/stops?q=cosenza"

# Próximos buses desde una parada (HOY con periodicidad automática)
curl "http://localhost:8000/stops/COSENZA/next-departures?limit=5"

# Próximos buses para una fecha específica
curl "http://localhost:8000/stops/COSENZA/next-departures?date=2026-03-10"

# Horario inteligente (periodicidad automática según fecha)
curl "http://localhost:8000/schedule-smart/139/139A"

# Ver qué periodicidad se usará para una fecha
curl "http://localhost:8000/periodicity/current?line_id=139&itinerary=139A&date=2026-03-10"

# Planificar viaje de A a B
curl "http://localhost:8000/routes/plan?from_stop=COSENZA&to_stop=SCALEA"

# Paradas cerca de coordenadas GPS
curl "http://localhost:8000/stops/nearby?lat=39.2986&lon=16.2540&radius=2.0"

# 🗺️ NAVEGACIÓN: Cómo llegar a una parada específica
curl "http://localhost:8000/stops/COSENZA/navigation?user_lat=39.3000&user_lon=16.2600"

# 🗺️ NAVEGACIÓN: Cómo llegar a la parada de una ruta planificada
curl "http://localhost:8000/routes/COSENZA-SCALEA/navigation?user_lat=39.3000&user_lon=16.2600"

# 🗺️ Paradas cercanas que tengan una línea específica
curl "http://localhost:8000/stops/nearest-with-line?user_lat=39.3000&user_lon=16.2600&line_id=139"

# Obtener alertas de servicio
curl "http://localhost:8000/alerts"

# Gestionar favoritos de usuario
curl -X POST "http://localhost:8000/users/mi_usuario/favorites?item_type=stop&item_id=COSENZA"
```

### **📊 Respuesta de Navegación:**

```json
{
  "stop_name": "COSENZA",
  "stop_coordinates": {"lat": 39.2986, "lon": 16.2540},
  "user_location": {"lat": 39.3000, "lon": 16.2600},
  "distance_km": 0.15,
  "distance_meters": 150,
  "walking_time_minutes": 2,
  "navigation_urls": {
    "google_maps": "https://www.google.com/maps/dir/39.3000,16.2600/39.2986,16.2540",
    "apple_maps": "http://maps.apple.com/?saddr=39.3000,16.2600&daddr=39.2986,16.2540",
    "waze": "https://waze.com/ul?ll=39.2986,16.2540&navigate=yes"
  },
  "lines_at_stop": ["135", "139", "142"],
  "accessibility": {
    "wheelchair_accessible": true,
    "has_shelter": true
  }
}
```

```json
{
  "metadata": {
    "line": "Linea N° 139",
    "direction": "Andata",
    "periodicity": "Feriale"
  },
  "trips": [
    {
      "trip_id": "404150",
      "stops": [
        {"stop": "COSENZA", "time": "07:00"},
        {"stop": "RENDE", "time": "07:15"},
        {"stop": "SCALEA", "time": "08:30"}
      ]
    }
  ],
  "stops": [
    {"name": "COSENZA", "index": 0},
    {"name": "RENDE", "index": 1}
  ],
  "schedule_matrix": {
    "COSENZA": {"404150": "07:00"},
    "RENDE": {"404150": "07:15"}
  }
}
```

## 🔄 Flujo de la Aplicación Original

Tu API replica exactamente el comportamiento de la web oficial:

### 1. **Obtener Líneas** (`GET /lines`)
- Parsea `quadro_orario.php` 
- Extrae `<select id="linea">` con todas las opciones
- **Filtra NULL y placeholders**
- Devuelve: `[{"value": "135", "label": "Linea 135 - ..."}]`

### 2. **Obtener Itinerarios** (`GET /itineraries/{line_id}`)
- POST a `select.ajaxlinea.php` con:
  ```
  id = {line_id}
  tipo = ITINERARIO
  ```
- Parsea respuesta HTML con `<option>` tags
- **Filtra NULL y "SELEZIONA"**
- Devuelve: `[{"value": "139A", "label": "Andata"}, {"value": "139R", "label": "Ritorno"}]`

### 3. **Obtener Periodicidades** (`GET /periodicities/{line_id}/{itinerary_value}`)
- POST a `select.ajaxlinea.php` con:
  ```
  id = {line_id}
  id_itinerario = {itinerary_value}  # ⚠️ Usa VALUE, no label
  tipo = PERIODICITA
  ```
- Si no hay respuesta, usa default "F" (Feriale)
- Devuelve: `[{"value": "F", "label": "Feriale"}, {"value": "SCO", "label": "Scolastico"}]`

### 4. **Obtener Horarios** (`GET /schedule/{line_id}/{itinerary_value}/{periodicity_value}`)
- POST a `download_quadro_orari.php` con:
  ```
  linea = {line_id}
  itinerario = {itinerary_value}     # ⚠️ Usa VALUE
  periodicita = {periodicity_value}  # ⚠️ Usa VALUE
  ```
- **Valida que la respuesta sea PDF real** (Content-Type + %PDF-)
- Si no es PDF, devuelve error 422 con snippet para debug
- **Parsea estructura matricial del PDF**:
  - Columnas = Viajes (N° Corsa)
  - Filas = Paradas (FERMATE)  
  - Celdas = Hora de paso
- Devuelve estructura completa:
  ```json
  {
    "metadata": {"line": "139", "direction": "Andata"},
    "trips": [{"trip_id": "404150", "stops": [{"stop": "ORSOMARSO", "time": "07:00"}]}],
    "stops": [{"name": "ORSOMARSO", "index": 0}],
    "schedule_matrix": {"ORSOMARSO": {"404150": "07:00"}},
    "fallback_times": {"1": ["07:00", "07:21"]} // si falla parsing estructurado
  }
  ```

### 5. **Obtener Horarios Estructurados** (`GET /schedule-structured/{line_id}/{itinerary_value}/{periodicity_value}`)
- Igual que `/schedule` pero devuelve **solo datos estructurados**
- Sin fallback_times para respuesta más limpia
- Ideal para apps que necesitan estructura de viajes/paradas

## 📚 Uso de la API

### Endpoints Principales

1. **Obtener líneas disponibles:**
```bash
GET /lines
```

2. **Obtener itinerarios de una línea:**
```bash
GET /itineraries/{line_id}
```

3. **Obtener periodicidades:**
```bash
GET /periodicities/{line_id}/{itinerary}
```

4. **Obtener horarios:**
```bash
GET /schedule/{line_id}/{itinerary}/{periodicity}
```

### Endpoints Adicionales

5. **Health check:**
```bash
GET /health
```

6. **Test completo:**
```bash
GET /test-flow/{line_id}
```

7. **Limpiar cache:**
```bash
POST /admin/clear-cache
```

8. **Debug PDF raw (para debugging):**
```bash
GET /debug/raw-pdf/{line_id}/{itinerary}/{periodicity}
```

9. **Debug values correctos (muy útil):**
```bash
GET /debug/values/{line_id}
```

### Ejemplos de Uso

```bash
# 1. Obtener todas las líneas
curl http://localhost:8000/lines

# 2. Obtener itinerarios de la línea 135
curl http://localhost:8000/itineraries/135

# 3. Obtener periodicidades para línea 135, itinerario 139A (usa el VALUE)
curl http://localhost:8000/periodicities/135/139A

# 4. Obtener horario completo (estructura matricial)
curl http://localhost:8000/schedule/135/139A/F

# 5. Obtener solo datos estructurados (sin fallback)
curl http://localhost:8000/schedule-structured/135/139A/F

# 6. Probar flujo completo para línea 135
curl http://localhost:8000/test-flow/135

# 7. Verificar estado del servicio
curl http://localhost:8000/health

# 8. Limpiar cache (útil durante desarrollo)
curl -X POST http://localhost:8000/admin/clear-cache

# 9. Debug: Ver respuesta cruda del servidor para PDF
curl http://localhost:8000/debug/raw-pdf/139/139-/F

# 10. Buscar paradas por nombre
curl "http://localhost:8000/search/stops?q=cosenza&limit=5"

# 11. Próximas salidas de una parada
curl http://localhost:8000/stops/COSENZA/next-departures

# 12. Planificar ruta entre dos paradas
curl "http://localhost:8000/routes/plan?from_stop=COSENZA&to_stop=SCALEA"

# 13. Paradas cercanas a ubicación
curl "http://localhost:8000/stops/nearby?lat=39.2986&lon=16.2540&radius=2.0"

# 14. Alertas de servicio
curl http://localhost:8000/alerts

# 15. Favoritos de usuario
curl http://localhost:8000/users/test_user/favorites

# 16. Información de accesibilidad
curl http://localhost:8000/stops/COSENZA/accessibility

# 17. Índice completo de paradas
curl http://localhost:8000/stops/all
```

## 🚀 **Estructura de Datos Mejorada**

### **Antes (Lista Plana - Incorrecto):**
```json
{
  "1": ["07:00", "07:21", "07:46", "11:00", "11:26"],
  "2": ["13:20", "16:00", "16:26"]
}
```

### **Ahora (Estructura Matricial - Correcto):**
```json
{
  "metadata": {
    "line": "Linea N° 139",
    "itinerary": "Macroitinerario: 139A", 
    "direction": "Andata",
    "periodicity": "Periodicità: Feriale"
  },
  "trips": [
    {
      "trip_id": "404150",
      "stops": [
        {"stop": "ORSOMARSO", "time": "07:00"},
        {"stop": "MARCELLINA", "time": "07:21"},
        {"stop": "SCALEA", "time": "07:46"}
      ]
    }
  ],
  "stops": [
    {"name": "ORSOMARSO", "index": 0},
    {"name": "MARCELLINA", "index": 1}
  ],
  "schedule_matrix": {
    "ORSOMARSO": {"404150": "07:00", "403794": "11:00"},
    "MARCELLINA": {"404150": "07:21", "403794": "11:26"}
  }
}
```

### **Ventajas de la Nueva Estructura:**
- ✅ **Viajes identificados**: Cada trip_id representa un viaje completo
- ✅ **Paradas ordenadas**: Lista de paradas en orden de ruta
- ✅ **Relaciones claras**: Qué hora pertenece a qué viaje y parada
- ✅ **Metadata extraída**: Línea, itinerario, dirección, periodicidad
- ✅ **Matriz navegable**: Fácil consulta por parada o por viaje
- ✅ **Compatibilidad**: Fallback a formato anterior si falla parsing

### ⚠️ **IMPORTANTE: Usar VALUES, no Labels**

Los endpoints ahora devuelven `{"value": "...", "label": "..."}`:
- **✅ Correcto**: Usar `value` para llamadas posteriores
- **❌ Incorrecto**: Usar `label` (texto visible)

**Ejemplo correcto:**
```json
// /itineraries/139 devuelve:
[{"value": "139A", "label": "Andata"}]

// Usar "139A" (value) en la siguiente llamada:
GET /periodicities/139/139A
```

### Script de Prueba Automatizado

```bash
# Ejecutar todas las pruebas automáticamente
python test_api.py
```

## 🐛 Debugging y Solución de Problemas

### ⚠️ **Error Más Común: Usar Labels en lugar de Values**

**Problema**: Error 422 "no se encontró %PDF-" cuando el endpoint `/test-flow` funciona bien.

**Causa**: Estás usando el `label` visible en lugar del `value` real.

**Ejemplo del problema:**
```bash
# ❌ INCORRECTO (falla con 422)
curl http://localhost:8000/schedule/139/139A/F

# ✅ CORRECTO (funciona)
curl http://localhost:8000/schedule/139/139-/F
```

**Cómo encontrar los values correctos:**
```bash
# 1. Ver todos los values correctos para una línea
curl http://localhost:8000/debug/values/139

# 2. Usar el endpoint de test que siempre usa values correctos
curl http://localhost:8000/test-flow/139
```

### Error "No /Root object! - Is this really a PDF?"

Este error ocurre cuando el servidor no devuelve un PDF válido:

**Causas comunes:**
1. **Periodicity inválida**: Estás enviando el `label` en lugar del `value`
2. **Itinerary incorrecto**: Estás usando el `label` en lugar del `value`
3. **Combinación inexistente**: La combinación línea/itinerario/periodicidad no existe

**Solución:**
```bash
# ❌ Incorrecto (usando labels)
curl http://localhost:8000/schedule/139/Andata/Scolastico

# ✅ Correcto (usando values)
curl http://localhost:8000/schedule/139/139A/SCO
```

### Logs de Debug

Para ver información detallada:
```bash
LOG_LEVEL=DEBUG python run.py
```

Los logs mostrarán:
- Payload enviado a cada endpoint
- Respuestas crudas del servidor
- Content-Type y primeros bytes de PDFs
- Opciones filtradas (NULL, placeholders)

### Validación de PDF Mejorada

La API ahora maneja PDFs que vienen con HTML de error al principio:
- Busca `%PDF-` en cualquier parte del contenido
- Extrae solo la porción PDF si hay contenido HTML antes
- Logs detallados sobre qué se está saltando

### Endpoint de Debug

Para ver exactamente qué devuelve el servidor:
```bash
curl http://localhost:8000/debug/raw-pdf/139/139-/F
```

Este endpoint muestra:
- Status code y headers completos
- Content-Type y longitud
- Posición donde empieza el PDF
- Preview del contenido crudo
- Si contiene magic bytes PDF

## 🔍 Monitoreo y Debugging

### Ver Logs en Tiempo Real

```bash
# Ejecutar con logging detallado
LOG_LEVEL=DEBUG python run.py
```

### Documentación Interactiva

Una vez ejecutando, visita:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🚀 Mejoras Implementadas

### 1. **Logging Completo**
- Seguimiento de todas las requests HTTP
- Información detallada del parsing de PDFs
- Logs estructurados con timestamps

### 2. **Cache Inteligente**
- Cache LRU para líneas, itinerarios y periodicidades
- Configurable por variable de entorno
- Endpoint para limpiar cache

### 3. **Validación Robusta**
- Modelos Pydantic para validación de entrada
- Validación de campos vacíos
- Mensajes de error claros

### 4. **Configuración Flexible**
- Todas las configuraciones via variables de entorno
- Archivo .env.example incluido
- Script de ejecución personalizable

### 5. **Manejo de Errores Mejorado**
- Logging de errores detallado
- Manejo específico de errores de PDF
- Validación de content-type

### 6. **Documentación Automática**
- Swagger UI en `/docs`
- ReDoc en `/redoc`
- Esquemas OpenAPI generados automáticamente

## 🛠️ Desarrollo

Para desarrollo local con recarga automática:

```bash
# Con logging detallado
LOG_LEVEL=DEBUG uvicorn app:app --reload

# En puerto específico
uvicorn app:app --reload --port 8080

# Con el script personalizado
python run.py
```

## 📊 Performance

El cache mejora significativamente el rendimiento:
- **Sin cache**: ~2-3 segundos por request
- **Con cache**: ~50-100ms para datos cacheados

Para limpiar el cache durante desarrollo:
```bash
curl -X POST http://localhost:8000/admin/clear-cache
```

## 🌟 Ventajas de FastAPI

- **Performance superior**: ~2-3x más rápido que Flask
- **Documentación automática**: Swagger UI y ReDoc incluidos
- **Validación nativa**: Pydantic integrado
- **Async/await**: Soporte nativo para operaciones asíncronas
- **Type hints**: Mejor experiencia de desarrollo
- **Estándares modernos**: OpenAPI, JSON Schema

## 🚀 Producción

Para producción, usa uvicorn con configuración optimizada:

```bash
# Producción básica
uvicorn app:app --host 0.0.0.0 --port 8000

# Producción con workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# Con configuración completa
uvicorn app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --access-log \
  --use-colors
```

## 🧪 Testing

### **Ejecutar Tests**
```bash
# Tests automatizados
python tests/test_api.py

# Tests con pytest (si está instalado)
pytest tests/ -v

# Test específico
python test_api.py  # El script original
```

### **Verificar Funcionalidades**
```bash
# Health check
curl http://localhost:8000/health

# Documentación interactiva
open http://localhost:8000/docs

# Test completo de una línea
curl http://localhost:8000/test-flow/139
```

## 🔧 Configuración

### **Variables de Entorno**

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `CONSORZIO_BASE_URL` | URL base del servicio | `https://www.consorzioautolineetpl.it` |
| `REQUEST_TIMEOUT` | Timeout para requests HTTP (segundos) | `30` |
| `CACHE_SIZE` | Tamaño del cache LRU | `100` |
| `LOG_LEVEL` | Nivel de logging (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `HOST` | Host del servidor | `127.0.0.1` |
| `PORT` | Puerto del servidor | `8000` |

### **Configuración para Producción**
```bash
# Con uvicorn directamente
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Con variables de entorno
HOST=0.0.0.0 PORT=8080 LOG_LEVEL=WARNING python run.py
```

## 📁 Estructura del Proyecto

```
consorzio-autolinee-api/
├── src/                    # 📦 Código fuente modular
│   ├── config.py          # ⚙️ Configuración
│   ├── models.py          # 📋 Modelos Pydantic
│   ├── utils.py           # 🛠️ Utilidades
│   ├── consorzio_client.py # 🌐 Cliente web
│   ├── pdf_parser.py      # 📄 Parser PDF
│   └── services.py        # 🏢 Lógica de negocio
├── tests/                 # 🧪 Tests automatizados
├── main.py               # 🚀 Aplicación principal
├── run.py                # 🏃 Script de desarrollo
├── requirements.txt      # 📋 Dependencias
└── README.md            # 📚 Documentación
```

## 🚀 Mejoras Implementadas

### **🏗️ Arquitectura Modular**
- Código organizado en módulos especializados
- Separación clara de responsabilidades
- Fácil mantenimiento y extensión

### **⚡ Performance Optimizada**
- Cache LRU inteligente por niveles
- Parsing PDF estructurado eficiente
- Búsqueda optimizada con índices

### **🛡️ Robustez y Confiabilidad**
- Validación completa de entrada
- Manejo de errores detallado
- Logging estructurado para debugging

### **🌐 Preparado para Producción**
- Configuración por variables de entorno
- Health checks y monitoreo
- Logging estructurado

### **📚 Documentación Completa**
- API docs automática con Swagger UI
- Tests automatizados
- Guías de contribución

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles sobre el proceso de desarrollo.

### **Desarrollo Local**
```bash
# 1. Fork y clonar
git clone <tu-fork>
cd consorzio-autolinee-api

# 2. Crear entorno
python -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Hacer cambios y probar
python run.py
python tests/test_api.py

# 5. Crear PR
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver [LICENSE](LICENSE) para detalles.

## 🙏 Agradecimientos

- [Consorzio Autolinee Cosenza](https://www.consorzioautolineetpl.it) por proporcionar los datos
- [FastAPI](https://fastapi.tiangolo.com) por el excelente framework
- [pdfplumber](https://github.com/jsvine/pdfplumber) por el parsing de PDFs

---

**¿Necesitas ayuda?** 
- 📚 Revisa la [documentación interactiva](http://localhost:8000/docs)
- 🐛 Reporta bugs en [Issues](../../issues)
- 💡 Sugiere funcionalidades en [Discussions](../../discussions)

**Hecho con ❤️ para mejorar el transporte público en Cosenza** 🚌✨