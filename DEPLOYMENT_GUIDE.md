# 🚀 Guía de Deployment

## Problema Resuelto

El error que viste ocurre porque `pydantic 2.10.0` requiere compilar código Rust, y Render no tiene Rust instalado por defecto.

**Solución**: Usar versiones más antiguas que tienen binarios pre-compilados.

---

## ✅ Cambios Realizados

### 1. `requirements.txt` Actualizado

```txt
fastapi==0.104.1        # Versión estable con binarios
uvicorn[standard]==0.24.0
requests==2.31.0
beautifulsoup4==4.12.2
pdfplumber==0.10.3
pydantic==2.5.0         # Versión con binarios pre-compilados
python-dotenv==1.0.0
```

### 2. `render.yaml` Creado

Configuración automática para Render:

```yaml
services:
  - type: web
    name: fermati-backend
    env: python
    region: oregon
    plan: free
    buildCommand: pip install --upgrade pip && pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

### 3. `runtime.txt` Creado

Especifica la versión de Python:

```txt
python-3.11.0
```

---

## 🌐 Deployment en Render

### Opción 1: Usando render.yaml (Recomendado)

1. **Conecta tu repositorio a Render**
   - Ve a https://render.com
   - Click en "New +" → "Blueprint"
   - Conecta tu repositorio de GitHub
   - Render detectará automáticamente `render.yaml`

2. **Deploy automático**
   - Render usará la configuración de `render.yaml`
   - El build y deploy serán automáticos

### Opción 2: Configuración Manual

1. **Crear Web Service**
   - Ve a https://render.com
   - Click en "New +" → "Web Service"
   - Conecta tu repositorio

2. **Configuración**
   ```
   Name: fermati-backend
   Environment: Python 3
   Region: Oregon (US West)
   Branch: main
   Build Command: pip install --upgrade pip && pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Variables de Entorno**
   ```
   PYTHON_VERSION=3.11.0
   LOG_LEVEL=INFO
   CACHE_SIZE=100
   REQUEST_TIMEOUT=30
   ```

4. **Plan**
   - Selecciona "Free" para empezar

5. **Deploy**
   - Click en "Create Web Service"

---

## 🚀 Deployment en Railway

Railway es más simple y no tiene el problema de Rust:

### Paso 1: Instalar Railway CLI (Opcional)

```bash
npm i -g @railway/cli
railway login
```

### Paso 2: Deploy

```bash
# Desde la carpeta del backend
railway init
railway up
```

O usa la interfaz web:

1. Ve a https://railway.app
2. Click en "New Project"
3. Selecciona "Deploy from GitHub repo"
4. Conecta tu repositorio
5. Railway detectará automáticamente que es Python
6. Deploy automático

### Variables de Entorno en Railway

```
LOG_LEVEL=INFO
CACHE_SIZE=100
REQUEST_TIMEOUT=30
```

---

## 🐳 Deployment con Docker (Heroku/Fly.io)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para pdfplumber
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Deploy en Heroku

```bash
# Instalar Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Crear app
heroku create fermati-backend

# Deploy
git push heroku main

# Ver logs
heroku logs --tail
```

### Deploy en Fly.io

```bash
# Instalar Fly CLI
# https://fly.io/docs/hands-on/install-flyctl/

# Login
fly auth login

# Crear app
fly launch

# Deploy
fly deploy
```

---

## ☁️ Deployment en Vercel (Serverless)

Vercel puede ejecutar Python como funciones serverless:

### 1. Crear `vercel.json`

```json
{
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ]
}
```

### 2. Modificar `main.py` para Vercel

Agregar al final de `main.py`:

```python
# Para Vercel
app = app  # Vercel busca 'app'
```

### 3. Deploy

```bash
# Instalar Vercel CLI
npm i -g vercel

# Deploy
vercel
```

---

## 🔧 Solución de Problemas

### Error: "pydantic-core requires Rust"

**Solución**: Ya está resuelto con `requirements.txt` actualizado.

Si persiste:
```bash
# Opción 1: Usar versión más antigua
pip install pydantic==2.5.0

# Opción 2: Instalar desde binarios
pip install pydantic --only-binary=:all:
```

### Error: "Module not found"

```bash
# Verificar que todas las dependencias estén instaladas
pip install -r requirements.txt

# Verificar estructura de archivos
ls -la
```

### Error: "Port already in use"

```bash
# En Render/Railway/Heroku, usa la variable $PORT
uvicorn main:app --host 0.0.0.0 --port $PORT

# Localmente, cambia el puerto
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Error: "CORS"

Actualiza `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tu-frontend.vercel.app",
        "https://www.tu-dominio.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🌍 URLs de Producción

Después del deploy, obtendrás URLs como:

- **Render**: `https://fermati-backend.onrender.com`
- **Railway**: `https://fermati-backend.up.railway.app`
- **Heroku**: `https://fermati-backend.herokuapp.com`
- **Fly.io**: `https://fermati-backend.fly.dev`
- **Vercel**: `https://fermati-backend.vercel.app`

### Actualizar Frontend

```env
# .env.production en Next.js
NEXT_PUBLIC_API_BASE_URL=https://tu-backend.onrender.com
NEXT_PUBLIC_API_MODE=real
```

---

## 📊 Monitoreo

### Logs en Render

```bash
# Ver logs en tiempo real
render logs -f
```

### Logs en Railway

```bash
railway logs
```

### Logs en Heroku

```bash
heroku logs --tail
```

---

## 🔒 Seguridad en Producción

### 1. Variables de Entorno Sensibles

Nunca commitees:
- API keys
- Secrets
- Passwords

Usa variables de entorno en la plataforma.

### 2. CORS Restrictivo

```python
# Producción
allow_origins=[
    "https://tu-dominio.com",
    "https://www.tu-dominio.com"
]

# NO uses "*" en producción
```

### 3. Rate Limiting

Considera agregar rate limiting:

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/stops/search")
@limiter.limit("10/minute")
async def search_stops(...):
    ...
```

---

## ✅ Checklist de Deployment

### Pre-Deploy
- [x] `requirements.txt` actualizado con versiones compatibles
- [x] `runtime.txt` creado
- [x] `render.yaml` creado (para Render)
- [ ] Variables de entorno configuradas
- [ ] CORS actualizado para producción
- [ ] Tests pasando localmente

### Post-Deploy
- [ ] URL de producción funciona
- [ ] Health check responde: `https://tu-url.com/health`
- [ ] Swagger UI accesible: `https://tu-url.com/docs`
- [ ] Frontend conectado y funcionando
- [ ] Logs sin errores
- [ ] Performance aceptable

---

## 🎯 Recomendaciones

### Para Empezar (Gratis)

1. **Railway** - Más fácil, sin problemas de Rust
2. **Render** - Buena opción con `render.yaml`
3. **Fly.io** - Rápido y global

### Para Producción

1. **Railway** - $5/mes, muy confiable
2. **Render** - $7/mes, buen soporte
3. **Heroku** - $7/mes, muy estable
4. **AWS/GCP/Azure** - Para escala empresarial

---

## 📞 Soporte

Si tienes problemas:

1. **Revisa los logs** de la plataforma
2. **Verifica las variables de entorno**
3. **Prueba localmente primero**: `python run.py`
4. **Consulta la documentación** de la plataforma

---

## 🎉 ¡Listo!

Tu backend ahora puede desplegarse sin problemas en cualquier plataforma.

**Siguiente paso**: Deploy y conecta el frontend con la URL de producción.

**¡Éxito con tu deployment!** 🚀
