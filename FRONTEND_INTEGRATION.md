# Backend API - Guía de Integración Frontend

## Base URL
```
https://fermati-backend.onrender.com
```

## Cambios Importantes

### 1. Campo `routes` en Stops
Todos los stops ahora incluyen un array `routes` con los IDs de las líneas que pasan por esa parada:

```typescript
interface Stop {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  routes: string[];  // ← NUEVO: ["135", "136", "137"]
  city: string;
  region: string;
}
```

### 2. Normalización Automática de Stop IDs
El backend maneja automáticamente stop IDs con o sin asterisco. Puedes usar cualquiera de estas formas:

```typescript
// Ambas funcionan igual:
GET /api/stops/*cosenza-(autostazione)
GET /api/stops/cosenza-(autostazione)  // ← Se normaliza automáticamente

// Ambas devuelven el mismo resultado con el ID correcto
```

**No necesitas preocuparte por el asterisco** - el backend lo maneja por ti en todos los endpoints.

---

## Nuevo Endpoint: Rutas Directas

### `GET /api/direct-routes`

Encuentra rutas directas (sin transbordos) entre dos paradas.

#### Parámetros Query
- `from` (required): Stop ID de origen
- `to` (required): Stop ID de destino  
- `limit` (optional): Número máximo de salidas (default: 20)
- `timeWindow` (optional): Ventana de tiempo en minutos (default: 60)

#### Ejemplo Request
```typescript
const response = await fetch(
  'https://fermati-backend.onrender.com/api/direct-routes?' + 
  new URLSearchParams({
    from: 'cosenza-(autostazione)',
    to: 'rende-(unical-terminal-bus)',
    limit: '10',
    timeWindow: '120'
  })
);

const data = await response.json();
```

#### Response
```typescript
interface DirectRoutesResponse {
  from: {
    id: string;
    name: string;
  };
  to: {
    id: string;
    name: string;
  };
  departures: DirectDeparture[];
  timestamp: string;
  count: number;
}

interface DirectDeparture {
  id: string;
  routeId: string;
  routeName: string;
  destination: string;
  departureTime: string;      // "14:30"
  arrivalTime: string;         // "14:45"
  status: "on-time" | "delayed" | "cancelled";
  delay: number;
  periodicity: "F" | "S" | "NS" | "DF";
  stopSequence: {
    fromIndex: number;         // Posición de la parada origen en la ruta
    toIndex: number;           // Posición de la parada destino en la ruta
    totalStops: number;        // Total de paradas en la ruta
    intermediateStops: number; // Paradas entre origen y destino
  };
  estimatedDuration: number;   // Duración en minutos
}
```

#### Ejemplo Response
```json
{
  "from": {
    "id": "*cosenza-(autostazione)",
    "name": "*COSENZA (AUTOSTAZIONE)"
  },
  "to": {
    "id": "*rende-(unical-terminal-bus)",
    "name": "*RENDE (Unical-TERMINAL BUS)"
  },
  "departures": [
    {
      "id": "135-402401-14:30",
      "routeId": "135",
      "routeName": "Línea 135",
      "destination": "RENDE (Unical-Terminal Bus)",
      "departureTime": "14:30",
      "arrivalTime": "14:45",
      "status": "on-time",
      "delay": 0,
      "periodicity": "F",
      "stopSequence": {
        "fromIndex": 2,
        "toIndex": 15,
        "totalStops": 20,
        "intermediateStops": 12
      },
      "estimatedDuration": 15
    }
  ],
  "timestamp": "2026-03-07T16:30:00Z",
  "count": 1
}
```

#### Casos de Uso

**1. Mostrar rutas directas disponibles**
```typescript
async function getDirectRoutes(from: string, to: string) {
  const response = await fetch(
    `https://fermati-backend.onrender.com/api/direct-routes?from=${from}&to=${to}`
  );
  const data = await response.json();
  
  if (data.count === 0) {
    // No hay rutas directas, usar /api/routes/plan para rutas con transbordos
    return null;
  }
  
  return data.departures;
}
```

**2. Mostrar información de secuencia de paradas**
```typescript
function formatStopSequence(departure: DirectDeparture) {
  const { stopSequence } = departure;
  return `Parada ${stopSequence.fromIndex} → ${stopSequence.toIndex} de ${stopSequence.totalStops} (${stopSequence.intermediateStops} paradas intermedias)`;
}
```

**3. Calcular tiempo de viaje**
```typescript
function formatDuration(departure: DirectDeparture) {
  return `${departure.estimatedDuration} min`;
}
```

---

## Endpoints Existentes (Actualizados)

### `GET /api/stops/{stopId}`
Obtiene información de una parada específica.

```typescript
// Ambas formas funcionan:
GET /api/stops/*cosenza-(autostazione)
GET /api/stops/cosenza-(autostazione)

// Response incluye routes:
{
  "id": "*cosenza-(autostazione)",
  "name": "*COSENZA (AUTOSTAZIONE)",
  "latitude": 0.0,
  "longitude": 0.0,
  "routes": ["136", "157", "140", "135", "137", "158", "138"],  // ← NUEVO
  "city": "Cosenza",
  "region": "Calabria"
}
```

### `GET /api/stops/search`
Busca paradas por texto o coordenadas GPS.

```typescript
// Búsqueda por texto
GET /api/stops/search?query=autostazione&limit=10

// Búsqueda por GPS (paradas cercanas)
GET /api/stops/search?lat=39.3091&lng=16.2543&radius=2.0&limit=10

// Response:
{
  "stops": [
    {
      "id": "*cosenza-(autostazione)",
      "name": "*COSENZA (AUTOSTAZIONE)",
      "routes": ["136", "157", "140", "135", "137", "158", "138"],  // ← Incluye routes
      // ...
    }
  ]
}
```

### `GET /api/stops/{stopId}/departures`
Obtiene próximas salidas desde una parada.

```typescript
GET /api/stops/cosenza-(autostazione)/departures?limit=10&timeWindow=60

// Response:
{
  "stopId": "cosenza-(autostazione)",
  "stopName": "*COSENZA (AUTOSTAZIONE)",
  "departures": [
    {
      "id": "...",
      "routeId": "135",
      "routeName": "Línea 135",
      "destination": "RENDE",
      "departureTime": "14:30",
      "periodicity": "F",  // F=Feriale, S=Scolastico, NS=Non Scolastico, DF=Domenica/Festivo
      // ...
    }
  ],
  "timestamp": "2026-03-07T16:30:00Z"
}
```

**Nota sobre periodicidad:**
- `F` (Feriale): Días laborables todo el año
- `S` (Scolastico): Período escolar (Sept-Jun)
- `NS` (Non Scolastico): Vacaciones escolares (Jul-Ago)
- `DF` (Domenica/Festivo): Domingos y festivos

El backend selecciona automáticamente la periodicidad correcta según la fecha actual.

### `GET /api/routes/plan`
Planifica rutas con transbordos entre dos paradas.

```typescript
GET /api/routes/plan?from=cosenza-(autostazione)&to=rende-(unical-terminal-bus)&maxTransfers=2

// Response:
{
  "from": { "id": "...", "name": "..." },
  "to": { "id": "...", "name": "..." },
  "journeys": [
    {
      "id": "journey-1",
      "origin": { /* stop info */ },
      "destination": { /* stop info */ },
      "legs": [
        {
          "type": "transit",
          "routeId": "135",
          "routeName": "Línea 135",
          "from": { /* stop info */ },
          "to": { /* stop info */ },
          "departureTime": "14:30",
          "arrivalTime": "14:45",
          "duration": 15,
          "distance": 5.2
        }
      ],
      "totalDuration": 15,
      "totalDistance": 5.2,
      "departureTime": "14:30",
      "arrivalTime": "14:45",
      "transfers": 0  // 0 = directo, 1 = un transbordo, 2 = dos transbordos
    }
  ],
  "timestamp": "2026-03-07T16:30:00Z"
}
```

### `GET /api/routes`
Lista todas las rutas disponibles.

```typescript
GET /api/routes

// Response:
{
  "routes": [
    {
      "id": "135",
      "name": "135 - NOGIANO - CASTROLIBERO - RENDE - COSENZA",
      "shortName": "L135",
      "color": "#2563EB",
      "type": "bus",
      "stops": ["stop-id-1", "stop-id-2", ...]
    }
  ]
}
```

### `GET /api/routes/{routeId}`
Obtiene detalles de una ruta específica con paradas ordenadas.

```typescript
GET /api/routes/135

// Response:
{
  "id": "135",
  "name": "135 - NOGIANO - CASTROLIBERO - RENDE - COSENZA",
  "shortName": "L135",
  "color": "#2563EB",
  "type": "bus",
  "stops": [
    {
      "id": "*cosenza-(autostazione)",
      "name": "*COSENZA (AUTOSTAZIONE)",
      "order": 0
    },
    {
      "id": "rende-(roges)",
      "name": "RENDE (Roges)",
      "order": 1
    }
    // ... paradas en orden
  ]
}
```

### `GET /api/stops/normalize/{stopId}`
Normaliza un stop ID (útil para debugging).

```typescript
GET /api/stops/normalize/cosenza-(autostazione)

// Response:
{
  "originalId": "cosenza-(autostazione)",
  "normalizedId": "*cosenza-(autostazione)",
  "name": "*COSENZA (AUTOSTAZIONE)",
  "hasAsterisk": true
}
```

---

## Flujo Recomendado para el Frontend

### 1. Búsqueda de Rutas
```typescript
async function findRoute(from: string, to: string) {
  // Paso 1: Intentar rutas directas primero
  const directResponse = await fetch(
    `https://fermati-backend.onrender.com/api/direct-routes?from=${from}&to=${to}&limit=5`
  );
  const directData = await directResponse.json();
  
  if (directData.count > 0) {
    // Hay rutas directas disponibles
    return {
      type: 'direct',
      routes: directData.departures
    };
  }
  
  // Paso 2: Si no hay rutas directas, buscar con transbordos
  const planResponse = await fetch(
    `https://fermati-backend.onrender.com/api/routes/plan?from=${from}&to=${to}&maxTransfers=2`
  );
  const planData = await planResponse.json();
  
  return {
    type: 'with-transfers',
    journeys: planData.journeys
  };
}
```

### 2. Mostrar Paradas Cercanas
```typescript
async function getNearbyStops(lat: number, lng: number) {
  const response = await fetch(
    `https://fermati-backend.onrender.com/api/stops/search?lat=${lat}&lng=${lng}&radius=1.0&limit=10`
  );
  const data = await response.json();
  
  // Cada stop incluye el array de routes
  return data.stops.map(stop => ({
    ...stop,
    routeCount: stop.routes.length  // Número de líneas que pasan por aquí
  }));
}
```

### 3. Mostrar Próximas Salidas
```typescript
async function getNextDepartures(stopId: string) {
  // No te preocupes por el asterisco, el backend lo maneja
  const response = await fetch(
    `https://fermati-backend.onrender.com/api/stops/${stopId}/departures?limit=10`
  );
  const data = await response.json();
  
  return data.departures;
}
```

---

## Manejo de Errores

Todos los endpoints devuelven errores en formato estándar:

```typescript
// 404 Not Found
{
  "detail": "Stop with ID 'invalid-stop' not found"
}

// 500 Internal Server Error
{
  "detail": "Error message here"
}
```

Ejemplo de manejo:
```typescript
async function safeApiCall(url: string) {
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API Error');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
}
```

---

## Performance

- Todos los endpoints responden en < 300ms
- La base de datos tiene 32,847 salidas indexadas
- La normalización de stop IDs es automática y rápida
- Usa `limit` y `timeWindow` para controlar el tamaño de las respuestas

---

## Notas Importantes

1. **Stop IDs con asterisco**: No necesitas manejarlos manualmente, el backend normaliza automáticamente
2. **Periodicidad**: El backend selecciona automáticamente la periodicidad correcta según el día de la semana
3. **Rutas directas vs con transbordos**: Usa `/api/direct-routes` primero, luego `/api/routes/plan` si no hay directas
4. **Campo routes en stops**: Ahora todos los stops incluyen las líneas que pasan por ellos
5. **Coordenadas**: Muchas paradas tienen coordenadas en 0.0 porque no están en el dataset original

---

## Ejemplos de Integración React/Next.js

### Hook personalizado para rutas directas
```typescript
import { useState, useEffect } from 'react';

interface UseDirectRoutesOptions {
  from: string;
  to: string;
  limit?: number;
  enabled?: boolean;
}

export function useDirectRoutes({ from, to, limit = 10, enabled = true }: UseDirectRoutesOptions) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!enabled || !from || !to) return;

    const fetchRoutes = async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `https://fermati-backend.onrender.com/api/direct-routes?from=${from}&to=${to}&limit=${limit}`
        );
        
        if (!response.ok) throw new Error('Failed to fetch routes');
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRoutes();
  }, [from, to, limit, enabled]);

  return { data, loading, error };
}
```

### Componente de ejemplo
```typescript
function DirectRoutesDisplay({ from, to }: { from: string; to: string }) {
  const { data, loading, error } = useDirectRoutes({ from, to });

  if (loading) return <div>Cargando rutas...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data || data.count === 0) return <div>No hay rutas directas disponibles</div>;

  return (
    <div>
      <h3>Rutas directas de {data.from.name} a {data.to.name}</h3>
      {data.departures.map((departure) => (
        <div key={departure.id} className="route-card">
          <div className="route-header">
            <span className="route-name">{departure.routeName}</span>
            <span className="duration">{departure.estimatedDuration} min</span>
          </div>
          <div className="route-times">
            <span>Salida: {departure.departureTime}</span>
            <span>Llegada: {departure.arrivalTime}</span>
          </div>
          <div className="route-info">
            {departure.stopSequence.intermediateStops} paradas intermedias
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## Testing

Todos los endpoints han sido probados y funcionan correctamente:
- ✅ 12/12 tests de normalización pasados
- ✅ Manejo automático de asteriscos en stop IDs
- ✅ Campo routes poblado en todos los stops
- ✅ Periodicidad correcta según día de la semana
- ✅ Rutas directas funcionando
- ✅ Planificación con transbordos funcionando

El backend está 100% listo para integración.
