# 👋 ¡Bienvenido al Backend de Fermati!

## 🎯 Inicio Rápido

### 1. Instalar y Ejecutar

```bash
pip install -r requirements.txt
python run.py
```

✅ Backend disponible en: **http://localhost:8000**

### 2. Verificar

```bash
curl http://localhost:8000/health
```

### 3. Ver Documentación

Abre en tu navegador: **http://localhost:8000/docs**

---

## 📖 Documentación Completa

**Lee esto para conectar el frontend:**

👉 **[GUIA_COMPLETA_INTEGRACION.md](GUIA_COMPLETA_INTEGRACION.md)** 👈

Esta guía única contiene TODO lo que necesitas:
- ✅ Configuración del backend
- ✅ Configuración del frontend
- ✅ Todos los endpoints explicados
- ✅ Ejemplos de código completos
- ✅ Componentes React/Next.js
- ✅ Hooks personalizados
- ✅ Manejo de errores
- ✅ Optimizaciones
- ✅ Deploy a producción
- ✅ Solución de problemas

---

## 🚀 Conectar con Next.js

### Paso 1: Variables de Entorno

```env
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_MODE=real
```

### Paso 2: Cliente API

```typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export const api = {
  searchStops: (query: string) =>
    fetch(`${API_URL}/api/stops/search?query=${query}`).then(r => r.json()),
  
  getDepartures: (stopId: string) =>
    fetch(`${API_URL}/api/stops/${stopId}/departures`).then(r => r.json()),
  
  planRoute: (from: string, to: string) =>
    fetch(`${API_URL}/api/routes/plan?from=${from}&to=${to}`).then(r => r.json()),
};
```

### Paso 3: Usar en Componentes

```typescript
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export function StopSearch() {
  const [stops, setStops] = useState([]);
  
  const search = async (query: string) => {
    const data = await api.searchStops(query);
    setStops(data.stops);
  };
  
  return (
    <input onChange={(e) => search(e.target.value)} />
  );
}
```

---

## 📡 Endpoints Principales

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/stops/search` | Buscar paradas |
| `GET /api/stops/{id}/departures` | Próximas salidas |
| `GET /api/routes/plan` | Planificar ruta |
| `GET /api/routes` | Todas las líneas |
| `GET /api/routes/{id}` | Detalle de línea |
| `GET /api/routes/{id}/schedule` | Horarios |
| `GET /api/alerts` | Alertas |

---

## 🧪 Probar

```bash
# Tests automatizados
python test_frontend_api.py

# O manualmente
curl "http://localhost:8000/api/stops/search?query=cosenza"
```

---

## 📚 Más Documentación

Si necesitas más detalles:

- **[GUIA_COMPLETA_INTEGRACION.md](GUIA_COMPLETA_INTEGRACION.md)** - Guía completa (¡EMPIEZA AQUÍ!)
- **[README.md](README.md)** - Documentación general del proyecto
- **[FRONTEND_EXAMPLES.md](FRONTEND_EXAMPLES.md)** - Ejemplos de respuestas
- **Swagger UI** - http://localhost:8000/docs (interactivo)

---

## ❓ Problemas

### El servidor no inicia
```bash
pip install -r requirements.txt
python run.py
```

### Error al desplegar (Render/Heroku)
Si ves error de "pydantic-core requires Rust":

✅ **Ya está resuelto** - El `requirements.txt` usa versiones compatibles

Lee: **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** para más detalles

### No encuentra paradas
Prueba con: "cosenza", "scalea", "rende", "paola"

### Más ayuda
Lee la **[GUIA_COMPLETA_INTEGRACION.md](GUIA_COMPLETA_INTEGRACION.md)**

---

## ✅ Checklist

- [ ] Backend ejecutándose
- [ ] Health check funciona (`curl http://localhost:8000/health`)
- [ ] Swagger UI accesible (http://localhost:8000/docs)
- [ ] Variables de entorno configuradas en frontend
- [ ] Cliente API creado
- [ ] Primer componente conectado

---

## 🎉 ¡Listo!

Tu backend está completo y funcionando.

**Siguiente paso**: Lee la **[GUIA_COMPLETA_INTEGRACION.md](GUIA_COMPLETA_INTEGRACION.md)** para conectar el frontend.

**¡Feliz desarrollo!** 🚀
