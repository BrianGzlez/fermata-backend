# Fermati - Especificación de API Backend

## Contexto del Proyecto

**Fermati** es una aplicación web de información de transporte público en tiempo real para Cosenza, Italia. El frontend está construido con Next.js 14, TypeScript, Tailwind CSS y shadcn/ui.

### Características Implementadas en el Frontend

1. **Búsqueda de Rutas**: Permite buscar rutas entre dos paradas (origen y destino)
2. **Próximas Salidas**: Muestra los próximos autobuses desde una parada específica con countdown
3. **Calendario Inteligente**: Visualiza qué líneas operan en cada franja horaria, con filtro por parada
4. **Paradas Cercanas**: Usa geolocalización para encontrar paradas próximas al usuario
5. **Horarios por Línea**: Muestra todos los horarios de una línea específica
6. **Sistema de Favoritos**: Guarda rutas y paradas favoritas (localStorage)
7. **Internacionalización**: Soporte para Italiano, Español e Inglés
8. **Modo Oscuro**: Tema claro/oscuro con persistencia
9. **Responsive**: Optimizado para móviles y tablets

---

## Estructura de Datos del Frontend

### BusStop (Parada)
```typescript
interface BusStop {
  id: string;                    // ID único de la parada
  name: string;                  // Nombre de la parada
  latitude: number;              // Coordenada latitud
  longitude: number;             // Coordenada longitud
  routes: string[];              // IDs de líneas que pasan por esta parada
  city: string;                  // Ciudad
  region: string;                // Región
}
```

### Departure (Salida)
```typescript
interface Departure {
  id: string;                    // ID único de la salida
  routeId: string;               // ID de la línea
  routeName: string;             // Nombre de la línea (ej: "Línea 1")
  destination: string;           // Destino final
  departureTime: string;         // Hora de salida (formato: "HH:mm")
  estimatedTime?: string;        // Hora estimada si hay retraso
  delay?: number;                // Minutos de retraso
  status: 'on-time' | 'delayed' | 'cancelled';
  platform?: string;             // Plataforma/andén
  realTime: boolean;             // Si es dato en tiempo real o programado
  periodicity: 'F' | 'SCO' | 'NS' | 'EST' | 'FEST'; // Tipo de servicio
}
```

### Route (Ruta/Línea)
```typescript
interface Route {
  id: string;                    // ID de la línea
  name: string;                  // Nombre (ej: "Línea 1")
  shortName: string;             // Nombre corto (ej: "L1")
  color?: string;                // Color de la línea (hex)
  type: 'bus' | 'tram' | 'metro'; // Tipo de transporte
  stops: string[];               // IDs de paradas en orden
}
```

### ServiceAlert (Alerta de Servicio)
```typescript
interface ServiceAlert {
  id: string;                    // ID único de la alerta
  severity: 'low' | 'medium' | 'high';
  message: string;               // Mensaje de la alerta
  affectedRoutes: string[];      // IDs de líneas afectadas
  startTime?: string;            // Inicio de la alerta (ISO 8601)
  endTime?: string;              // Fin de la alerta (ISO 8601)
}
```

### Journey (Viaje/Ruta calculada)
```typescript
interface Journey {
  id: string;                    // ID único del viaje
  origin: BusStop;               // Parada de origen
  destination: BusStop;          // Parada de destino
  legs: JourneyLeg[];            // Segmentos del viaje
  totalDuration: number;         // Duración total en minutos
  totalDistance: number;         // Distancia total en km
  departureTime: string;         // Hora de salida
  arrivalTime: string;           // Hora de llegada
  transfers: number;             // Número de transbordos
}

interface JourneyLeg {
  type: 'transit' | 'walk';      // Tipo de segmento
  routeId?: string;              // ID de línea (si es transit)
  routeName?: string;            // Nombre de línea
  from: BusStop;                 // Parada de inicio
  to: BusStop;                   // Parada de fin
  departureTime: string;         // Hora de salida
  arrivalTime: string;           // Hora de llegada
  duration: number;              // Duración en minutos
  distance: number;              // Distancia en km
  stops?: BusStop[];             // Paradas intermedias
}
```

---

## Endpoints Requeridos

### 1. Búsqueda de Paradas
**GET** `/api/stops/search`

Busca paradas por nombre o ubicación.

**Query Parameters:**
- `query` (string, opcional): Texto de búsqueda
- `lat` (number, opcional): Latitud para búsqueda por proximidad
- `lng` (number, opcional): Longitud para búsqueda por proximidad
- `radius` (number, opcional): Radio en km (default: 2)
- `limit` (number, opcional): Máximo de resultados (default: 10)

**Response:**
```json
{
  "stops": [
    {
      "id": "stop-1",
      "name": "Piazza Telesio",
      "latitude": 39.303,
      "longitude": 16.452,
      "routes": ["1", "2", "5"],
      "city": "Cosenza",
      "region": "Calabria"
    }
  ]
}
```

---

### 2. Obtener Parada por ID
**GET** `/api/stops/:stopId`

Obtiene información detallada de una parada.

**Response:**
```json
{
  "id": "stop-1",
  "name": "Piazza Telesio",
  "latitude": 39.303,
  "longitude": 16.452,
  "routes": ["1", "2", "5"],
  "city": "Cosenza",
  "region": "Calabria"
}
```

---

### 3. Próximas Salidas desde una Parada
**GET** `/api/stops/:stopId/departures`

Obtiene las próximas salidas desde una parada específica.

**Query Parameters:**
- `limit` (number, opcional): Número de salidas (default: 10)
- `timeWindow` (number, opcional): Ventana de tiempo en minutos (default: 60)

**Response:**
```json
{
  "stopId": "stop-1",
  "stopName": "Piazza Telesio",
  "departures": [
    {
      "id": "dep-1",
      "routeId": "1",
      "routeName": "Línea 1",
      "destination": "Università della Calabria",
      "departureTime": "14:32",
      "estimatedTime": "14:35",
      "delay": 3,
      "status": "delayed",
      "platform": "A",
      "realTime": true,
      "periodicity": "F"
    }
  ],
  "timestamp": "2026-03-06T14:27:00Z"
}
```

---

### 4. Calcular Ruta entre Dos Paradas
**GET** `/api/routes/plan`

Calcula las mejores rutas entre origen y destino.

**Query Parameters:**
- `from` (string, requerido): ID de parada de origen
- `to` (string, requerido): ID de parada de destino
- `time` (string, opcional): Hora de salida deseada (ISO 8601)
- `arriveBy` (boolean, opcional): Si true, 'time' es hora de llegada
- `maxTransfers` (number, opcional): Máximo de transbordos (default: 2)
- `modes` (string, opcional): Modos de transporte separados por coma (default: "bus")

**Response:**
```json
{
  "from": {
    "id": "stop-1",
    "name": "Piazza Telesio"
  },
  "to": {
    "id": "stop-4",
    "name": "Università della Calabria"
  },
  "journeys": [
    {
      "id": "journey-1",
      "origin": { "id": "stop-1", "name": "Piazza Telesio" },
      "destination": { "id": "stop-4", "name": "Università della Calabria" },
      "legs": [
        {
          "type": "transit",
          "routeId": "1",
          "routeName": "Línea 1",
          "from": { "id": "stop-1", "name": "Piazza Telesio" },
          "to": { "id": "stop-4", "name": "Università della Calabria" },
          "departureTime": "14:32",
          "arrivalTime": "15:05",
          "duration": 33,
          "distance": 12.5,
          "stops": [
            { "id": "stop-2", "name": "Viale Giacomo Mancini" },
            { "id": "stop-3", "name": "Ospedale dell'Annunziata" }
          ]
        }
      ],
      "totalDuration": 33,
      "totalDistance": 12.5,
      "departureTime": "14:32",
      "arrivalTime": "15:05",
      "transfers": 0
    }
  ],
  "timestamp": "2026-03-06T14:27:00Z"
}
```

---

### 5. Obtener Información de una Línea
**GET** `/api/routes/:routeId`

Obtiene información detallada de una línea.

**Response:**
```json
{
  "id": "1",
  "name": "Línea 1",
  "shortName": "L1",
  "color": "#2563EB",
  "type": "bus",
  "stops": [
    {
      "id": "stop-1",
      "name": "Piazza Telesio",
      "order": 0
    },
    {
      "id": "stop-2",
      "name": "Viale Giacomo Mancini",
      "order": 1
    }
  ]
}
```

---

### 6. Horarios de una Línea
**GET** `/api/routes/:routeId/schedule`

Obtiene todos los horarios de una línea para un día específico.

**Query Parameters:**
- `date` (string, opcional): Fecha en formato YYYY-MM-DD (default: hoy)
- `stopId` (string, opcional): Filtrar por parada específica

**Response:**
```json
{
  "routeId": "1",
  "routeName": "Línea 1",
  "date": "2026-03-06",
  "schedules": [
    {
      "stopId": "stop-1",
      "stopName": "Piazza Telesio",
      "times": [
        {
          "departureTime": "07:00",
          "periodicity": "F",
          "realTime": false
        },
        {
          "departureTime": "07:15",
          "periodicity": "F",
          "realTime": false
        }
      ]
    }
  ]
}
```

---

### 7. Alertas de Servicio
**GET** `/api/alerts`

Obtiene alertas activas del servicio.

**Query Parameters:**
- `routeId` (string, opcional): Filtrar por línea específica
- `severity` (string, opcional): Filtrar por severidad (low, medium, high)

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert-1",
      "severity": "high",
      "message": "Línea 1 con retrasos de hasta 15 minutos por tráfico",
      "affectedRoutes": ["1"],
      "startTime": "2026-03-06T14:00:00Z",
      "endTime": "2026-03-06T16:00:00Z"
    }
  ],
  "timestamp": "2026-03-06T14:27:00Z"
}
```

---

### 8. Todas las Líneas
**GET** `/api/routes`

Obtiene lista de todas las líneas disponibles.

**Response:**
```json
{
  "routes": [
    {
      "id": "1",
      "name": "Línea 1",
      "shortName": "L1",
      "color": "#2563EB",
      "type": "bus"
    },
    {
      "id": "2",
      "name": "Línea 2",
      "shortName": "L2",
      "color": "#10B981",
      "type": "bus"
    }
  ]
}
```

---

## Configuración del Cliente API en el Frontend

El frontend tiene un cliente API configurado en `lib/api.ts`:

```typescript
export function getApiClient() {
  const mode = getApiMode(); // 'real' o 'mock'
  
  if (mode === 'mock') {
    return mockApiClient;
  }
  
  return {
    searchStops: async (query: string) => {
      const response = await fetch(`${API_BASE_URL}/api/stops/search?query=${query}`);
      return response.json();
    },
    
    getDepartures: async (stopId: string) => {
      const response = await fetch(`${API_BASE_URL}/api/stops/${stopId}/departures`);
      return response.json();
    },
    
    planRoute: async (from: string, to: string) => {
      const response = await fetch(`${API_BASE_URL}/api/routes/plan?from=${from}&to=${to}`);
      return response.json();
    },
    
    getServiceAlerts: async () => {
      const response = await fetch(`${API_BASE_URL}/api/alerts`);
      return response.json();
    },
    
    getRoute: async (routeId: string) => {
      const response = await fetch(`${API_BASE_URL}/api/routes/${routeId}`);
      return response.json();
    },
    
    getRouteSchedule: async (routeId: string, date?: string) => {
      const url = date 
        ? `${API_BASE_URL}/api/routes/${routeId}/schedule?date=${date}`
        : `${API_BASE_URL}/api/routes/${routeId}/schedule`;
      const response = await fetch(url);
      return response.json();
    }
  };
}
```

---

## Variables de Entorno Necesarias

```env
# Backend API URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:3001

# API Mode (real o mock)
NEXT_PUBLIC_API_MODE=real
```

---

## Consideraciones Importantes

### 1. CORS
El backend debe permitir peticiones desde el dominio del frontend:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

### 2. Rate Limiting
Implementar rate limiting para evitar abuso:
- 100 requests por minuto por IP
- 1000 requests por hora por IP

### 3. Caché
Implementar caché para datos que no cambian frecuentemente:
- Información de paradas: 24 horas
- Información de líneas: 24 horas
- Horarios programados: 1 hora
- Datos en tiempo real: 30 segundos
- Alertas: 5 minutos

### 4. Formato de Fechas
Usar ISO 8601 para todas las fechas y horas:
- Fecha: `2026-03-06`
- Hora: `14:32:00`
- Timestamp: `2026-03-06T14:32:00Z`

### 5. Códigos de Error HTTP
- `200`: Success
- `400`: Bad Request (parámetros inválidos)
- `404`: Not Found (recurso no existe)
- `429`: Too Many Requests (rate limit excedido)
- `500`: Internal Server Error
- `503`: Service Unavailable (API externa caída)

### 6. Estructura de Error
```json
{
  "error": {
    "code": "STOP_NOT_FOUND",
    "message": "La parada con ID 'stop-999' no existe",
    "details": {}
  }
}
```

---

## Prioridad de Implementación

### Alta Prioridad (MVP)
1. ✅ GET `/api/stops/search` - Búsqueda de paradas
2. ✅ GET `/api/stops/:stopId/departures` - Próximas salidas
3. ✅ GET `/api/routes/plan` - Calcular rutas
4. ✅ GET `/api/alerts` - Alertas de servicio

### Media Prioridad
5. ✅ GET `/api/routes/:routeId` - Info de línea
6. ✅ GET `/api/routes/:routeId/schedule` - Horarios de línea
7. ✅ GET `/api/routes` - Todas las líneas

### Baja Prioridad
8. GET `/api/stops/:stopId` - Detalle de parada (puede derivarse de search)

---

## Datos de Prueba Recomendados

Para testing, incluir al menos:
- 7-10 paradas diferentes
- 4-5 líneas de autobús
- Horarios cada 15-20 minutos
- 2-3 alertas de servicio activas
- Rutas con 0, 1 y 2 transbordos

---

## Notas Adicionales

- El frontend maneja automáticamente el modo mock/real
- Todas las traducciones están en el frontend
- El frontend calcula distancias usando Haversine
- Los favoritos se guardan en localStorage (no requiere backend)
- El tema y idioma se guardan en localStorage

---

## Contacto y Soporte

Para dudas sobre la integración, revisar:
- `lib/api.ts` - Cliente API
- `lib/types.ts` - Definiciones de tipos TypeScript
- `lib/storage.ts` - Gestión de localStorage
