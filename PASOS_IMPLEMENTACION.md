# Pasos para Completar la Implementación

## ✅ YA COMPLETADO

1. ✅ Modelos de base de datos creados (`src/db_models.py`)
2. ✅ Servicio de base de datos creado (`src/db_service.py`)
3. ✅ Script de sincronización creado (`sync_data.py`)
4. ✅ Configuración de base de datos (`src/database.py`)
5. ✅ API actualizada para usar base de datos (`src/frontend_api.py`)
6. ✅ Inicialización de DB en startup (`main.py`)
7. ✅ Configuración de Render con cron job (`render.yaml`)

## 🔧 PASOS PARA EJECUTAR

### LOCAL (Desarrollo)

1. **Instalar dependencias nuevas:**
```bash
pip install -r requirements.txt
```

2. **Probar conexión a base de datos:**
```bash
python test_db.py
```

3. **Sincronizar datos (primera vez):**
```bash
python sync_data.py --all
```
Esto tomará 5-10 minutos y llenará la base de datos.

4. **Verificar que hay datos:**
```bash
python test_db.py
```

5. **Iniciar servidor:**
```bash
uvicorn main:app --reload
```

6. **Probar endpoints:**
```bash
# Buscar paradas
curl "http://localhost:8000/api/stops/search?query=cosenza"

# Ver rutas
curl "http://localhost:8000/api/routes"

# Ver salidas de una parada
curl "http://localhost:8000/api/stops/cosenza-autostazione/departures"
```

### RENDER (Producción)

1. **Crear base de datos PostgreSQL en Render:**
   - Ve a tu dashboard de Render
   - Click en "New +" → "PostgreSQL"
   - Nombre: `fermati-db`
   - Plan: Free
   - Crear

2. **Actualizar servicio web:**
   - El `render.yaml` ya está configurado
   - Render detectará automáticamente la configuración
   - La variable `DATABASE_URL` se conectará automáticamente

3. **Hacer push a GitHub:**
```bash
git add .
git commit -m "Add database caching with PostgreSQL"
git push
```

4. **Render desplegará automáticamente:**
   - Web service: API principal
   - Cron job: Sincronización semanal (domingos 2 AM)

5. **Sincronizar datos manualmente (primera vez):**
   - Ve a Render Dashboard → fermati-sync (cron job)
   - Click en "Trigger Job" para ejecutar manualmente
   - Espera 5-10 minutos

6. **Verificar que funciona:**
```bash
curl "https://fermati-backend.onrender.com/health"
curl "https://fermati-backend.onrender.com/api/routes"
```

## 📊 RESULTADO ESPERADO

- **Antes:** Requests de 3-5 segundos (scraping en tiempo real)
- **Después:** Requests de < 100ms (lectura de base de datos)

## 🔄 SINCRONIZACIÓN

El cron job se ejecutará automáticamente cada domingo a las 2 AM.

Para ejecutar manualmente:
- **Local:** `python sync_data.py --all`
- **Render:** Click en "Trigger Job" en el dashboard

## 🐛 TROUBLESHOOTING

Si algo falla:

1. **Error de conexión a DB:**
   - Verifica que `DATABASE_URL` esté configurada
   - Local: usa SQLite por defecto (no necesitas PostgreSQL)

2. **Tablas no existen:**
   - Ejecuta `python test_db.py` para crear tablas

3. **No hay datos:**
   - Ejecuta `python sync_data.py --all`

4. **Render no encuentra DATABASE_URL:**
   - Verifica que la base de datos esté creada
   - Verifica que `render.yaml` esté en el repo
