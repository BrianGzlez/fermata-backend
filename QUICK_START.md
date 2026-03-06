# 🚀 Quick Start - Fermati Backend API

## ⚡ Inicio Rápido (5 minutos)

### 1. Instalar y Ejecutar

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python run.py
```

✅ El servidor estará disponible en: **http://localhost:8000**

### 2. Verificar que Funciona

```bash
# Health check
curl http://localhost:8000/health

# Buscar paradas
curl "http://localhost:8000/api/stops/search?query=cosenza"

# Ver documentación interactiva
open http://localhost:8000/docs
```

---

## 🎯 Para Desarrolladores Frontend

### Configuración en Next.js

```env
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_MODE=real
```

### Cliente API Básico

```typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export const api = {
  // Buscar paradas
  searchStops: (query: string) =>
    fetch(`${API_URL}/api/stops/search?query=${query}`).then(r => r.json()),
  
  // Próximas salidas
  getDepartures: (stopId: string) =>
    fetch(`${API_URL}/api/stops/${stopId}/departures`).then(r => r.json()),
  
  // Planificar ruta
  planRoute: (from: string, to: string) =>
    fetch(`${API_URL}/api/routes/plan?from=${from}&to=${to}`).then(r => r.json()),
  
  // Todas las líneas
  getRoutes: () =>
    fetch(`${API_URL}/api/routes`).then(r => r.json()),
  
  // Alertas
  getAlerts: () =>
    fetch(`${API_URL}/api/alerts`).then(r => r.json()),
};
```

### Ejemplo de Uso

```typescript
// components/StopSearch.tsx
import { api } from '@/lib/api';

export function StopSearch() {
  const [stops, setStops] = useState([]);
  
  const search = async (query: string) => {
    const { stops } = await api.searchStops(query);
    setStops(stops);
  };
  
  return (
    <input 
      onChange={(e) => search(e.target.value)}
      placeholder="Buscar parada..."
    />
  );
}
```

---

## 📚 Endpoints Principales

| Endpoint | Descripción | Ejemplo |
|----------|-------------|---------|
| `GET /api/stops/search` | Buscar paradas | `?query=cosenza` |
| `GET /api/stops/{id}` | Detalle de parada | `/api/stops/cosenza` |
| `GET /api/stops/{id}/departures` | Próximas salidas | `/api/stops/cosenza/departures` |
| `GET /api/routes` | Todas las líneas | `/api/routes` |
| `GET /api/routes/{id}` | Detalle de línea | `/api/routes/135` |
| `GET /api/routes/{id}/schedule` | Horarios | `/api/routes/135/schedule` |
| `GET /api/routes/plan` | Planificar ruta | `?from=cosenza&to=scalea` |
| `GET /api/alerts` | Alertas | `/api/alerts` |

---

## 🧪 Probar la API

### Opción 1: cURL

```bash
# Buscar paradas
curl "http://localhost:8000/api/stops/search?query=cosenza"

# Próximas salidas
curl "http://localhost:8000/api/stops/cosenza/departures"

# Planificar ruta
curl "http://localhost:8000/api/routes/plan?from=cosenza&to=scalea"
```

### Opción 2: Script de Prueba

```bash
python test_frontend_api.py
```

### Opción 3: Swagger UI

Abre en tu navegador: **http://localhost:8000/docs**

---

## 📖 Documentación Completa

- **[FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md)** - Guía completa de integración
- **[FRONTEND_EXAMPLES.md](FRONTEND_EXAMPLES.md)** - Ejemplos de respuestas
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Resumen técnico
- **[README.md](README.md)** - Documentación general

---

## 🔧 Configuración Avanzada

### Variables de Entorno

```env
# .env
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
CACHE_SIZE=100
REQUEST_TIMEOUT=30
```

### Ejecutar en Producción

```bash
# Con uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Con el script
HOST=0.0.0.0 PORT=8000 python run.py
```

---

## ❓ Problemas Comunes

### El servidor no inicia

```bash
# Verificar que las dependencias estén instaladas
pip install -r requirements.txt

# Verificar que el puerto no esté en uso
lsof -i :8000
```

### Error de CORS

El backend ya tiene CORS configurado para desarrollo. En producción, actualiza `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tu-dominio.com"],  # Cambiar aquí
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### No encuentra paradas

Las paradas se buscan por nombre. Prueba con:
- "cosenza"
- "scalea"
- "rende"
- "paola"

---

## 🎉 ¡Listo!

Tu backend está completamente configurado y listo para conectar con el frontend.

**Siguiente paso**: Conecta tu aplicación Next.js y empieza a desarrollar! 🚀

---

## 💡 Tips

1. **Usa Swagger UI** para explorar la API interactivamente
2. **Revisa los logs** si algo no funciona (`LOG_LEVEL=DEBUG`)
3. **Consulta los ejemplos** en FRONTEND_EXAMPLES.md
4. **Ejecuta los tests** con `python test_frontend_api.py`

---

**¿Necesitas ayuda?**
- 📖 Lee la documentación completa
- 🐛 Revisa los logs del servidor
- 🧪 Ejecuta los tests automatizados
- 🌐 Usa Swagger UI para probar endpoints

**¡Feliz desarrollo!** ✨
