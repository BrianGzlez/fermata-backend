# 🚀 Guía Completa de Integración Backend-Frontend

## 📋 Tabla de Contenidos

1. [Inicio Rápido (5 minutos)](#inicio-rápido)
2. [Configuración del Backend](#configuración-del-backend)
3. [Configuración del Frontend](#configuración-del-frontend)
4. [Endpoints Disponibles](#endpoints-disponibles)
5. [Ejemplos de Uso](#ejemplos-de-uso)
6. [Formato de Datos](#formato-de-datos)
7. [Testing](#testing)
8. [Solución de Problemas](#solución-de-problemas)

---

## 🚀 Inicio Rápido

### Paso 1: Iniciar el Backend

```bash
# En la carpeta del backend
pip install -r requirements.txt
python run.py
```

✅ Backend disponible en: **http://localhost:8000**

### Paso 2: Verificar que Funciona

```bash
# Health check
curl http://localhost:8000/health

# Probar búsqueda
curl "http://localhost:8000/api/stops/search?query=cosenza"

# Ver documentación
open http://localhost:8000/docs
```

### Paso 3: Configurar el Frontend

```env
# .env.local en Next.js
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_MODE=real
```

### Paso 4: Conectar desde Next.js

```typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export const api = {
  // Buscar paradas
  searchStops: async (query: string) => {
    const res = await fetch(`${API_URL}/api/stops/search?query=${query}`);
    if (!res.ok) throw new Error('Error buscando paradas');
    return res.json();
  },
  
  // Próximas salidas
  getDepartures: async (stopId: string) => {
    const res = await fetch(`${API_URL}/api/stops/${stopId}/departures`);
    if (!res.ok) throw new Error('Error obteniendo salidas');
    return res.json();
  },
  
  // Planificar ruta
  planRoute: async (from: string, to: string) => {
    const res = await fetch(`${API_URL}/api/routes/plan?from=${from}&to=${to}`);
    if (!res.ok) throw new Error('Error planificando ruta');
    return res.json();
  },
  
  // Todas las líneas
  getRoutes: async () => {
    const res = await fetch(`${API_URL}/api/routes`);
    if (!res.ok) throw new Error('Error obteniendo líneas');
    return res.json();
  },
  
  // Detalle de línea
  getRoute: async (routeId: string) => {
    const res = await fetch(`${API_URL}/api/routes/${routeId}`);
    if (!res.ok) throw new Error('Error obteniendo línea');
    return res.json();
  },
  
  // Horarios de línea
  getRouteSchedule: async (routeId: string, date?: string) => {
    const url = date 
      ? `${API_URL}/api/routes/${routeId}/schedule?date=${date}`
      : `${API_URL}/api/routes/${routeId}/schedule`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Error obteniendo horarios');
    return res.json();
  },
  
  // Alertas
  getAlerts: async () => {
    const res = await fetch(`${API_URL}/api/alerts`);
    if (!res.ok) throw new Error('Error obteniendo alertas');
    return res.json();
  }
};
```

---

## ⚙️ Configuración del Backend

### Variables de Entorno

Crea un archivo `.env` en la raíz del backend:

```env
# Servidor
HOST=127.0.0.1
PORT=8000

# Logging
LOG_LEVEL=INFO

# Performance
CACHE_SIZE=100
REQUEST_TIMEOUT=30

# Consorzio (no cambiar)
CONSORZIO_BASE_URL=https://www.consorzioautolineetpl.it
```

### Iniciar en Desarrollo

```bash
python run.py
```

### Iniciar en Producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🌐 Configuración del Frontend

### Variables de Entorno Next.js

```env
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_MODE=real
```

### CORS

El backend ya está configurado para aceptar peticiones de cualquier origen en desarrollo.

**Para producción**, actualiza `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tu-dominio.com",
        "https://www.tu-dominio.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📡 Endpoints Disponibles

### 1. Búsqueda de Paradas

**GET** `/api/stops/search`

Busca paradas por texto o GPS.

**Parámetros:**
- `query` (string, opcional): Texto de búsqueda
- `lat` (number, opcional): Latitud
- `lng` (number, opcional): Longitud
- `radius` (number, opcional): Radio en km (default: 2)
- `limit` (number, opcional): Máximo resultados (default: 10)

**Ejemplo:**
```bash
# Por texto
curl "http://localhost:8000/api/stops/search?query=cosenza&limit=5"

# Por GPS
curl "http://localhost:8000/api/stops/search?lat=39.2986&lng=16.2540&radius=2"
```

**Respuesta:**
```json
{
  "stops": [
    {
      "id": "cosenza",
      "name": "COSENZA",
      "latitude": 39.2986,
      "longitude": 16.2540,
      "routes": ["135", "139"],
      "city": "Cosenza",
      "region": "Calabria"
    }
  ]
}
```

---

### 2. Detalle de Parada

**GET** `/api/stops/{stopId}`

Obtiene información de una parada específica.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/stops/cosenza"
```

**Respuesta:**
```json
{
  "id": "cosenza",
  "name": "COSENZA",
  "latitude": 39.2986,
  "longitude": 16.2540,
  "routes": ["135", "139"],
  "city": "Cosenza",
  "region": "Calabria"
}
```

---

### 3. Próximas Salidas

**GET** `/api/stops/{stopId}/departures`

Obtiene próximas salidas desde una parada.

**Parámetros:**
- `limit` (number, opcional): Número de salidas (default: 10)
- `timeWindow` (number, opcional): Ventana en minutos (default: 60)

**Ejemplo:**
```bash
curl "http://localhost:8000/api/stops/cosenza/departures?limit=5"
```

**Respuesta:**
```json
{
  "stopId": "cosenza",
  "stopName": "COSENZA",
  "departures": [
    {
      "id": "cosenza-135-404150",
      "routeId": "135",
      "routeName": "Línea 135",
      "destination": "SCALEA",
      "departureTime": "07:00",
      "estimatedTime": null,
      "delay": null,
      "status": "on-time",
      "platform": null,
      "realTime": false,
      "periodicity": "F"
    }
  ],
  "timestamp": "2026-03-06T14:27:00Z"
}
```

---

### 4. Planificar Ruta

**GET** `/api/routes/plan`

Calcula rutas entre dos paradas.

**Parámetros:**
- `from` (string, requerido): ID parada origen
- `to` (string, requerido): ID parada destino
- `time` (string, opcional): Hora salida (ISO 8601)
- `arriveBy` (boolean, opcional): Si true, time es hora llegada
- `maxTransfers` (number, opcional): Máximo transbordos (default: 2)

**Ejemplo:**
```bash
curl "http://localhost:8000/api/routes/plan?from=cosenza&to=scalea"
```

**Respuesta:**
```json
{
  "from": {"id": "cosenza", "name": "COSENZA"},
  "to": {"id": "scalea", "name": "SCALEA"},
  "journeys": [
    {
      "id": "journey-1",
      "origin": {
        "id": "cosenza",
        "name": "COSENZA",
        "latitude": 39.2986,
        "longitude": 16.2540
      },
      "destination": {
        "id": "scalea",
        "name": "SCALEA",
        "latitude": 39.8167,
        "longitude": 15.7833
      },
      "legs": [
        {
          "type": "transit",
          "routeId": "135",
          "routeName": "Línea 135",
          "from": {"id": "cosenza", "name": "COSENZA"},
          "to": {"id": "scalea", "name": "SCALEA"},
          "departureTime": "07:00",
          "arrivalTime": "08:30",
          "duration": 90,
          "distance": 75.5,
          "stops": []
        }
      ],
      "totalDuration": 90,
      "totalDistance": 75.5,
      "departureTime": "07:00",
      "arrivalTime": "08:30",
      "transfers": 0
    }
  ],
  "timestamp": "2026-03-06T14:27:00Z"
}
```

---

### 5. Todas las Líneas

**GET** `/api/routes`

Lista todas las líneas disponibles.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/routes"
```

**Respuesta:**
```json
{
  "routes": [
    {
      "id": "135",
      "name": "COSENZA - SCALEA",
      "shortName": "L135",
      "color": "#2563EB",
      "type": "bus",
      "stops": []
    }
  ]
}
```

---

### 6. Detalle de Línea

**GET** `/api/routes/{routeId}`

Obtiene información detallada de una línea.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/routes/135"
```

**Respuesta:**
```json
{
  "id": "135",
  "name": "COSENZA - SCALEA",
  "shortName": "L135",
  "color": "#2563EB",
  "type": "bus",
  "stops": [
    {"id": "cosenza", "name": "COSENZA", "order": 0},
    {"id": "scalea", "name": "SCALEA", "order": 1}
  ]
}
```

---

### 7. Horarios de Línea

**GET** `/api/routes/{routeId}/schedule`

Obtiene horarios de una línea para una fecha.

**Parámetros:**
- `date` (string, opcional): Fecha YYYY-MM-DD (default: hoy)
- `stopId` (string, opcional): Filtrar por parada

**Ejemplo:**
```bash
curl "http://localhost:8000/api/routes/135/schedule?date=2026-03-06"
```

**Respuesta:**
```json
{
  "routeId": "135",
  "routeName": "COSENZA - SCALEA",
  "date": "2026-03-06",
  "schedules": [
    {
      "stopId": "cosenza",
      "stopName": "COSENZA",
      "times": [
        {"departureTime": "07:00", "periodicity": "F", "realTime": false}
      ]
    }
  ]
}
```

---

### 8. Alertas de Servicio

**GET** `/api/alerts`

Obtiene alertas activas del servicio.

**Parámetros:**
- `routeId` (string, opcional): Filtrar por línea
- `severity` (string, opcional): Filtrar por severidad

**Ejemplo:**
```bash
curl "http://localhost:8000/api/alerts"
```

**Respuesta:**
```json
{
  "alerts": [
    {
      "id": "alert_001",
      "severity": "medium",
      "message": "Possibili ritardi di 10-15 minuti",
      "affectedRoutes": ["139"],
      "startTime": "2026-03-03T10:00:00Z",
      "endTime": null
    }
  ],
  "timestamp": "2026-03-06T14:27:00Z"
}
```

---

## 💻 Ejemplos de Uso en React/Next.js

### Componente de Búsqueda de Paradas

```typescript
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export function StopSearch() {
  const [query, setQuery] = useState('');
  const [stops, setStops] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (searchQuery: string) => {
    if (searchQuery.length < 2) return;
    
    setLoading(true);
    try {
      const data = await api.searchStops(searchQuery);
      setStops(data.stops);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          handleSearch(e.target.value);
        }}
        placeholder="Buscar parada..."
      />
      
      {loading && <p>Buscando...</p>}
      
      <ul>
        {stops.map((stop: any) => (
          <li key={stop.id}>
            {stop.name} - {stop.routes.join(', ')}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Componente de Próximas Salidas

```typescript
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export function NextDepartures({ stopId }: { stopId: string }) {
  const [departures, setDepartures] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDepartures = async () => {
      try {
        const data = await api.getDepartures(stopId);
        setDepartures(data.departures);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDepartures();
    
    // Actualizar cada 30 segundos
    const interval = setInterval(fetchDepartures, 30000);
    return () => clearInterval(interval);
  }, [stopId]);

  if (loading) return <p>Cargando...</p>;

  return (
    <div>
      <h2>Próximas Salidas</h2>
      <ul>
        {departures.map((dep: any) => (
          <li key={dep.id}>
            <strong>{dep.routeName}</strong> → {dep.destination}
            <br />
            Salida: {dep.departureTime}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Componente de Planificación de Rutas

```typescript
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export function RoutePlanner() {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [journeys, setJourneys] = useState([]);
  const [loading, setLoading] = useState(false);

  const handlePlan = async () => {
    if (!from || !to) return;
    
    setLoading(true);
    try {
      const data = await api.planRoute(from, to);
      setJourneys(data.journeys);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={from}
        onChange={(e) => setFrom(e.target.value)}
        placeholder="Desde..."
      />
      
      <input
        type="text"
        value={to}
        onChange={(e) => setTo(e.target.value)}
        placeholder="Hasta..."
      />
      
      <button onClick={handlePlan} disabled={loading}>
        {loading ? 'Buscando...' : 'Buscar Ruta'}
      </button>
      
      {journeys.map((journey: any) => (
        <div key={journey.id}>
          <p>Duración: {journey.totalDuration} min</p>
          <p>Distancia: {journey.totalDistance} km</p>
          <p>Transbordos: {journey.transfers}</p>
          
          {journey.legs.map((leg: any, idx: number) => (
            <div key={idx}>
              <strong>{leg.routeName}</strong>
              <p>{leg.from.name} → {leg.to.name}</p>
              <p>{leg.departureTime} - {leg.arrivalTime}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

---

## 📊 Formato de Datos

### IDs de Paradas

Los IDs se generan automáticamente desde el nombre:
- `"COSENZA"` → `"cosenza"`
- `"PIAZZA TELESIO"` → `"piazza-telesio"`
- `"SAN VINCENZO LA COSTA"` → `"san-vincenzo-la-costa"`

### Campos Opcionales

Algunos campos pueden ser `null`:
- `estimatedTime`: Solo con datos en tiempo real
- `delay`: Solo con datos en tiempo real
- `platform`: No siempre disponible
- `endTime` en alertas: Puede ser null

### Periodicidad

Códigos de periodicidad:
- `F`: Feriale (días laborables)
- `SCO`: Scolastico (período escolar)
- `FEST`: Festivo (fines de semana)
- `EST`: Estivo (verano)
- `NS`: Non Scolastico (vacaciones)

### Timestamps

Formato ISO 8601 con zona horaria UTC:
- `2026-03-06T14:27:00Z`

---

## 🧪 Testing

### Probar el Backend

```bash
# Script de prueba automatizado
python test_frontend_api.py

# O manualmente con cURL
curl "http://localhost:8000/api/stops/search?query=cosenza"
curl "http://localhost:8000/api/stops/cosenza/departures"
curl "http://localhost:8000/api/routes/plan?from=cosenza&to=scalea"
```

### Swagger UI

Abre en tu navegador: **http://localhost:8000/docs**

Aquí puedes:
- Ver todos los endpoints
- Probar peticiones en vivo
- Ver esquemas de datos
- Copiar ejemplos de código

---

## 🐛 Solución de Problemas

### El servidor no inicia

```bash
# Verificar dependencias
pip install -r requirements.txt

# Verificar puerto
lsof -i :8000

# Iniciar con logs detallados
LOG_LEVEL=DEBUG python run.py
```

### Error de CORS

El CORS ya está configurado. Si persiste:

1. Verifica que el frontend use la URL correcta
2. En producción, actualiza `allow_origins` en `main.py`

### No encuentra paradas

Prueba con nombres conocidos:
- "cosenza"
- "scalea"
- "rende"
- "paola"

### Respuestas vacías

1. Verifica los logs: `LOG_LEVEL=DEBUG python run.py`
2. Prueba con Swagger UI: http://localhost:8000/docs
3. Verifica que el servicio del Consorzio esté disponible

### Datos desactualizados

```bash
# Limpiar caché
curl -X POST http://localhost:8000/admin/clear-cache
```

---

## 📚 Recursos Adicionales

### Documentación Interactiva
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Archivos de Referencia
- `FRONTEND_EXAMPLES.md` - Ejemplos de respuestas
- `test_frontend_api.py` - Tests automatizados
- `src/frontend_api.py` - Código fuente de endpoints

### Endpoints de Debug
- `GET /health` - Estado del servicio
- `GET /test-flow/{line_id}` - Probar flujo completo
- `POST /admin/clear-cache` - Limpiar caché

---

## ✅ Checklist de Integración

- [ ] Backend instalado y ejecutándose
- [ ] Health check funciona
- [ ] Swagger UI accesible
- [ ] Variables de entorno configuradas en frontend
- [ ] Cliente API creado en `lib/api.ts`
- [ ] Primer componente conectado
- [ ] Búsqueda de paradas funciona
- [ ] Próximas salidas funciona
- [ ] Planificación de rutas funciona
- [ ] Manejo de errores implementado
- [ ] Loading states implementados

---

## 🎉 ¡Listo!

Tu backend está completamente configurado y listo para conectar con el frontend.

**Siguiente paso**: Empieza a desarrollar tus componentes usando el cliente API.

**¿Problemas?** Revisa:
1. Los logs del servidor
2. Swagger UI (http://localhost:8000/docs)
3. Los tests (`python test_frontend_api.py`)
4. Esta guía

**¡Feliz desarrollo!** 🚀


---

## 🎨 Ejemplos Avanzados

### Hook Personalizado para API

```typescript
// hooks/useApi.ts
import { useState, useEffect } from 'react';

export function useApi<T>(
  fetcher: () => Promise<T>,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await fetcher();
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err as Error);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, dependencies);

  return { data, loading, error };
}

// Uso
function MyComponent() {
  const { data, loading, error } = useApi(
    () => api.searchStops('cosenza'),
    []
  );

  if (loading) return <div>Cargando...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return <div>{/* Renderizar data */}</div>;
}
```

### Context para Estado Global

```typescript
// context/TransportContext.tsx
'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import { api } from '@/lib/api';

interface TransportContextType {
  selectedStop: any | null;
  setSelectedStop: (stop: any) => void;
  departures: any[];
  loadDepartures: (stopId: string) => Promise<void>;
  loading: boolean;
}

const TransportContext = createContext<TransportContextType | undefined>(undefined);

export function TransportProvider({ children }: { children: ReactNode }) {
  const [selectedStop, setSelectedStop] = useState(null);
  const [departures, setDepartures] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadDepartures = async (stopId: string) => {
    setLoading(true);
    try {
      const data = await api.getDepartures(stopId);
      setDepartures(data.departures);
    } catch (error) {
      console.error('Error loading departures:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <TransportContext.Provider
      value={{
        selectedStop,
        setSelectedStop,
        departures,
        loadDepartures,
        loading
      }}
    >
      {children}
    </TransportContext.Provider>
  );
}

export function useTransport() {
  const context = useContext(TransportContext);
  if (!context) {
    throw new Error('useTransport must be used within TransportProvider');
  }
  return context;
}

// Uso en app/layout.tsx
export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <TransportProvider>
          {children}
        </TransportProvider>
      </body>
    </html>
  );
}
```

### Componente de Mapa con Paradas

```typescript
// components/StopsMap.tsx
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export function StopsMap() {
  const [userLocation, setUserLocation] = useState<{lat: number, lng: number} | null>(null);
  const [nearbyStops, setNearbyStops] = useState([]);

  useEffect(() => {
    // Obtener ubicación del usuario
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const location = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          };
          setUserLocation(location);

          // Buscar paradas cercanas
          try {
            const data = await api.searchStops('', {
              lat: location.lat,
              lng: location.lng,
              radius: 2,
              limit: 10
            });
            setNearbyStops(data.stops);
          } catch (error) {
            console.error('Error finding nearby stops:', error);
          }
        },
        (error) => {
          console.error('Error getting location:', error);
        }
      );
    }
  }, []);

  return (
    <div>
      <h2>Paradas Cercanas</h2>
      {userLocation && (
        <p>Tu ubicación: {userLocation.lat.toFixed(4)}, {userLocation.lng.toFixed(4)}</p>
      )}
      
      <ul>
        {nearbyStops.map((stop: any) => (
          <li key={stop.id}>
            <strong>{stop.name}</strong>
            <br />
            Líneas: {stop.routes.join(', ')}
            <br />
            Coordenadas: {stop.latitude}, {stop.longitude}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Actualización del Cliente API con Búsqueda GPS

```typescript
// lib/api.ts (versión completa)
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

interface SearchStopsParams {
  query?: string;
  lat?: number;
  lng?: number;
  radius?: number;
  limit?: number;
}

export const api = {
  // Búsqueda flexible de paradas
  searchStops: async (query?: string, params?: SearchStopsParams) => {
    const searchParams = new URLSearchParams();
    
    if (query) {
      searchParams.append('query', query);
    }
    
    if (params?.lat !== undefined && params?.lng !== undefined) {
      searchParams.append('lat', params.lat.toString());
      searchParams.append('lng', params.lng.toString());
      if (params.radius) searchParams.append('radius', params.radius.toString());
    }
    
    if (params?.limit) {
      searchParams.append('limit', params.limit.toString());
    }
    
    const res = await fetch(`${API_URL}/api/stops/search?${searchParams}`);
    if (!res.ok) throw new Error('Error buscando paradas');
    return res.json();
  },

  // Detalle de parada
  getStop: async (stopId: string) => {
    const res = await fetch(`${API_URL}/api/stops/${stopId}`);
    if (!res.ok) throw new Error('Error obteniendo parada');
    return res.json();
  },

  // Próximas salidas
  getDepartures: async (stopId: string, limit: number = 10) => {
    const res = await fetch(
      `${API_URL}/api/stops/${stopId}/departures?limit=${limit}`
    );
    if (!res.ok) throw new Error('Error obteniendo salidas');
    return res.json();
  },

  // Planificar ruta
  planRoute: async (from: string, to: string, options?: {
    time?: string;
    arriveBy?: boolean;
    maxTransfers?: number;
  }) => {
    const params = new URLSearchParams({
      from,
      to,
      ...(options?.time && { time: options.time }),
      ...(options?.arriveBy && { arriveBy: 'true' }),
      ...(options?.maxTransfers && { maxTransfers: options.maxTransfers.toString() })
    });
    
    const res = await fetch(`${API_URL}/api/routes/plan?${params}`);
    if (!res.ok) throw new Error('Error planificando ruta');
    return res.json();
  },

  // Todas las líneas
  getRoutes: async () => {
    const res = await fetch(`${API_URL}/api/routes`);
    if (!res.ok) throw new Error('Error obteniendo líneas');
    return res.json();
  },

  // Detalle de línea
  getRoute: async (routeId: string) => {
    const res = await fetch(`${API_URL}/api/routes/${routeId}`);
    if (!res.ok) throw new Error('Error obteniendo línea');
    return res.json();
  },

  // Horarios de línea
  getRouteSchedule: async (routeId: string, options?: {
    date?: string;
    stopId?: string;
  }) => {
    const params = new URLSearchParams();
    if (options?.date) params.append('date', options.date);
    if (options?.stopId) params.append('stopId', options.stopId);
    
    const url = params.toString()
      ? `${API_URL}/api/routes/${routeId}/schedule?${params}`
      : `${API_URL}/api/routes/${routeId}/schedule`;
    
    const res = await fetch(url);
    if (!res.ok) throw new Error('Error obteniendo horarios');
    return res.json();
  },

  // Alertas
  getAlerts: async (options?: {
    routeId?: string;
    severity?: string;
  }) => {
    const params = new URLSearchParams();
    if (options?.routeId) params.append('routeId', options.routeId);
    if (options?.severity) params.append('severity', options.severity);
    
    const url = params.toString()
      ? `${API_URL}/api/alerts?${params}`
      : `${API_URL}/api/alerts`;
    
    const res = await fetch(url);
    if (!res.ok) throw new Error('Error obteniendo alertas');
    return res.json();
  }
};
```

---

## 🔐 Seguridad y Mejores Prácticas

### Manejo de Errores

```typescript
// lib/api-error.ts
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Wrapper para fetch con manejo de errores
async function apiFetch(url: string, options?: RequestInit) {
  try {
    const res = await fetch(url, options);
    
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new ApiError(
        error.message || 'Error en la petición',
        res.status,
        error
      );
    }
    
    return res.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError('Error de red o servidor no disponible');
  }
}

// Uso en componentes
try {
  const data = await api.searchStops('cosenza');
} catch (error) {
  if (error instanceof ApiError) {
    if (error.statusCode === 404) {
      // Manejar no encontrado
    } else if (error.statusCode === 500) {
      // Manejar error de servidor
    }
  }
}
```

### Rate Limiting en el Cliente

```typescript
// lib/rate-limiter.ts
class RateLimiter {
  private requests: number[] = [];
  private maxRequests: number;
  private timeWindow: number;

  constructor(maxRequests: number = 10, timeWindowMs: number = 1000) {
    this.maxRequests = maxRequests;
    this.timeWindow = timeWindowMs;
  }

  async throttle() {
    const now = Date.now();
    
    // Limpiar requests antiguos
    this.requests = this.requests.filter(
      time => now - time < this.timeWindow
    );

    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = this.requests[0];
      const waitTime = this.timeWindow - (now - oldestRequest);
      await new Promise(resolve => setTimeout(resolve, waitTime));
      return this.throttle();
    }

    this.requests.push(now);
  }
}

const limiter = new RateLimiter(10, 1000); // 10 requests por segundo

// Uso
export const api = {
  searchStops: async (query: string) => {
    await limiter.throttle();
    // ... resto del código
  }
};
```

### Caché en el Cliente

```typescript
// lib/cache.ts
class ApiCache {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private ttl: number;

  constructor(ttlMs: number = 60000) {
    this.ttl = ttlMs;
  }

  get(key: string) {
    const cached = this.cache.get(key);
    if (!cached) return null;

    const now = Date.now();
    if (now - cached.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  set(key: string, data: any) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  clear() {
    this.cache.clear();
  }
}

const cache = new ApiCache(60000); // 1 minuto

// Uso
export const api = {
  searchStops: async (query: string) => {
    const cacheKey = `stops:${query}`;
    const cached = cache.get(cacheKey);
    if (cached) return cached;

    const data = await fetch(/* ... */);
    cache.set(cacheKey, data);
    return data;
  }
};
```

---

## 📱 Optimización para Móviles

### Detección de Conexión

```typescript
// hooks/useOnlineStatus.ts
import { useState, useEffect } from 'react';

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

// Uso
function MyComponent() {
  const isOnline = useOnlineStatus();

  if (!isOnline) {
    return <div>Sin conexión a internet</div>;
  }

  // ... resto del componente
}
```

### Service Worker para Offline

```typescript
// public/sw.js
const CACHE_NAME = 'fermati-v1';
const API_CACHE = 'fermati-api-v1';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/',
        '/offline.html'
      ]);
    })
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Cachear respuestas de API
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.open(API_CACHE).then((cache) => {
        return fetch(request)
          .then((response) => {
            cache.put(request, response.clone());
            return response;
          })
          .catch(() => {
            return cache.match(request);
          });
      })
    );
  }
});
```

---

## 🎯 Casos de Uso Completos

### Caso 1: Búsqueda y Selección de Parada

```typescript
// app/stops/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function StopsPage() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [stops, setStops] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (searchQuery: string) => {
    if (searchQuery.length < 2) {
      setStops([]);
      return;
    }

    setLoading(true);
    try {
      const data = await api.searchStops(searchQuery);
      setStops(data.stops);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectStop = (stopId: string) => {
    router.push(`/stops/${stopId}`);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Buscar Parada</h1>
      
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          handleSearch(e.target.value);
        }}
        placeholder="Escribe el nombre de la parada..."
        className="w-full p-2 border rounded"
      />

      {loading && <p className="mt-4">Buscando...</p>}

      <div className="mt-4 space-y-2">
        {stops.map((stop: any) => (
          <div
            key={stop.id}
            onClick={() => handleSelectStop(stop.id)}
            className="p-4 border rounded cursor-pointer hover:bg-gray-100"
          >
            <h3 className="font-bold">{stop.name}</h3>
            <p className="text-sm text-gray-600">
              Líneas: {stop.routes.join(', ')}
            </p>
            <p className="text-xs text-gray-500">
              {stop.city}, {stop.region}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Caso 2: Vista de Parada con Salidas

```typescript
// app/stops/[stopId]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';

export default function StopDetailPage() {
  const params = useParams();
  const stopId = params.stopId as string;
  
  const [stop, setStop] = useState<any>(null);
  const [departures, setDepartures] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [stopData, departuresData] = await Promise.all([
          api.getStop(stopId),
          api.getDepartures(stopId, 10)
        ]);
        
        setStop(stopData);
        setDepartures(departuresData.departures);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Actualizar cada 30 segundos
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [stopId]);

  if (loading) return <div>Cargando...</div>;
  if (!stop) return <div>Parada no encontrada</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-2">{stop.name}</h1>
      <p className="text-gray-600 mb-4">
        Líneas: {stop.routes.join(', ')}
      </p>

      <h2 className="text-xl font-bold mb-4">Próximas Salidas</h2>
      
      <div className="space-y-2">
        {departures.map((dep: any) => (
          <div key={dep.id} className="p-4 border rounded">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-bold">{dep.routeName}</h3>
                <p className="text-sm text-gray-600">→ {dep.destination}</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold">{dep.departureTime}</p>
                <p className="text-xs text-gray-500">{dep.periodicity}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Caso 3: Planificador de Rutas Completo

```typescript
// app/planner/page.tsx
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export default function RoutePlannerPage() {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [journeys, setJourneys] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePlan = async () => {
    if (!from || !to) {
      setError('Por favor ingresa origen y destino');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const data = await api.planRoute(from, to);
      setJourneys(data.journeys);
      
      if (data.journeys.length === 0) {
        setError('No se encontraron rutas entre estas paradas');
      }
    } catch (err) {
      setError('Error al planificar la ruta');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Planificar Ruta</h1>

      <div className="space-y-4 mb-6">
        <input
          type="text"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          placeholder="Desde (ej: cosenza)"
          className="w-full p-2 border rounded"
        />
        
        <input
          type="text"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="Hasta (ej: scalea)"
          className="w-full p-2 border rounded"
        />
        
        <button
          onClick={handlePlan}
          disabled={loading}
          className="w-full p-2 bg-blue-500 text-white rounded disabled:bg-gray-300"
        >
          {loading ? 'Buscando...' : 'Buscar Ruta'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-100 text-red-700 rounded mb-4">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {journeys.map((journey: any) => (
          <div key={journey.id} className="border rounded p-4">
            <div className="flex justify-between mb-4">
              <div>
                <p className="text-sm text-gray-600">Duración</p>
                <p className="font-bold">{journey.totalDuration} min</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Distancia</p>
                <p className="font-bold">{journey.totalDistance} km</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Transbordos</p>
                <p className="font-bold">{journey.transfers}</p>
              </div>
            </div>

            <div className="space-y-3">
              {journey.legs.map((leg: any, idx: number) => (
                <div key={idx} className="pl-4 border-l-4 border-blue-500">
                  <p className="font-bold text-blue-600">{leg.routeName}</p>
                  <p className="text-sm">
                    {leg.from.name} → {leg.to.name}
                  </p>
                  <p className="text-xs text-gray-600">
                    {leg.departureTime} - {leg.arrivalTime} ({leg.duration} min)
                  </p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🚀 Deploy a Producción

### Backend (Railway/Render/Heroku)

```bash
# Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4

# runtime.txt
python-3.11

# requirements.txt ya está listo
```

### Frontend (Vercel/Netlify)

```env
# Variables de entorno en producción
NEXT_PUBLIC_API_BASE_URL=https://tu-backend.railway.app
NEXT_PUBLIC_API_MODE=real
```

### Docker (Opcional)

```dockerfile
# Dockerfile para backend
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - CACHE_SIZE=100
    restart: unless-stopped
```

---

## ✅ Checklist Final

### Backend
- [x] Servidor ejecutándose
- [x] Health check funciona
- [x] Swagger UI accesible
- [x] CORS configurado
- [x] Variables de entorno configuradas

### Frontend
- [ ] Variables de entorno configuradas
- [ ] Cliente API creado
- [ ] Primer componente conectado
- [ ] Manejo de errores implementado
- [ ] Loading states implementados
- [ ] Caché implementado (opcional)
- [ ] Service worker configurado (opcional)

### Testing
- [ ] Tests del backend pasando
- [ ] Componentes del frontend probados
- [ ] Flujos completos verificados
- [ ] Manejo de errores probado

### Producción
- [ ] Backend deployado
- [ ] Frontend deployado
- [ ] Variables de entorno de producción configuradas
- [ ] CORS actualizado para producción
- [ ] Monitoreo configurado (opcional)

---

## 🎉 ¡Felicidades!

Ahora tienes todo lo necesario para integrar completamente el backend con tu frontend Fermati.

**Recursos finales:**
- Swagger UI: http://localhost:8000/docs
- Tests: `python test_frontend_api.py`
- Esta guía: `GUIA_COMPLETA_INTEGRACION.md`

**¡Éxito con tu proyecto!** 🚌✨
