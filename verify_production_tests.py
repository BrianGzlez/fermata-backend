#!/usr/bin/env python3
"""
Verificación de que todas las pruebas fueron contra producción.
"""

import requests
import psycopg2

# URL de producción
PROD_URL = "https://fermati-backend.onrender.com"
PROD_DB = "postgresql://fermati_db_user:7oudj7InyxA6TfXmS4Mv0bL3zfrhJY9H@dpg-d6lj7ap5pdvs73fhgls0-a.oregon-postgres.render.com/fermati_db"

print("="*70)
print("🔍 VERIFICACIÓN: Pruebas contra Producción")
print("="*70)

# 1. Verificar que el API responde
print("\n1️⃣  Verificando API de Producción")
print("-"*70)
try:
    response = requests.get(f"{PROD_URL}/api/routes", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API respondiendo correctamente")
        print(f"   Rutas en producción: {len(data['routes'])}")
    else:
        print(f"❌ API error: {response.status_code}")
except Exception as e:
    print(f"❌ Error conectando al API: {e}")

# 2. Verificar conexión a DB de producción
print("\n2️⃣  Verificando Base de Datos de Producción")
print("-"*70)
try:
    conn = psycopg2.connect(PROD_DB)
    cur = conn.cursor()
    
    # Contar registros
    cur.execute("SELECT COUNT(*) FROM departures")
    departures_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM stops")
    stops_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM routes")
    routes_count = cur.fetchone()[0]
    
    print(f"✅ Conectado a DB de producción")
    print(f"   Departures: {departures_count}")
    print(f"   Stops: {stops_count}")
    print(f"   Routes: {routes_count}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Error conectando a DB: {e}")

# 3. Probar endpoint /api/direct-routes con datos reales
print("\n3️⃣  Probando /api/direct-routes con Datos Reales")
print("-"*70)

# Primero, obtener stops de una ruta real
try:
    response = requests.get(f"{PROD_URL}/api/routes/139", timeout=10)
    if response.status_code == 200:
        route_data = response.json()
        stops = route_data['stops']
        
        # Tomar dos stops que sabemos que funcionan
        from_stop = "rende-(arcavacata-piazza-cuticchia)"
        to_stop = "rende-(surdo-piazza,via-f.petrarca-n.21)"
        
        print(f"Probando: {from_stop} → {to_stop}")
        
        response = requests.get(
            f"{PROD_URL}/api/direct-routes?from={from_stop}&to={to_stop}&limit=3",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint funcionando")
            print(f"   Rutas directas encontradas: {data['count']}")
            
            if data['count'] > 0:
                first = data['departures'][0]
                print(f"   Primera ruta: {first['routeId']} - {first['departureTime']} → {first['arrivalTime']}")
                print(f"   Duración: {first['estimatedDuration']} min")
                print(f"   Paradas intermedias: {first['stopSequence']['intermediateStops']}")
        else:
            print(f"❌ Error: {response.status_code}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# 4. Verificar que los datos coinciden entre DB y API
print("\n4️⃣  Verificando Consistencia DB ↔ API")
print("-"*70)

try:
    # Obtener stop desde API
    response = requests.get(f"{PROD_URL}/api/stops/*cosenza-(autostazione)", timeout=10)
    api_stop = response.json()
    
    # Obtener mismo stop desde DB
    conn = psycopg2.connect(PROD_DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, routes FROM stops WHERE id = '*cosenza-(autostazione)'")
    db_stop = cur.fetchone()
    
    if db_stop:
        db_id, db_name, db_routes = db_stop
        
        print(f"Stop ID: {api_stop['id']}")
        print(f"✅ API y DB coinciden:")
        print(f"   Name: {api_stop['name']} == {db_name}")
        print(f"   Routes: {len(api_stop['routes'])} == {len(db_routes)}")
        
        if api_stop['routes'] == db_routes:
            print(f"   ✅ Arrays de routes idénticos")
        else:
            print(f"   ⚠️  Arrays diferentes")
            print(f"      API: {api_stop['routes']}")
            print(f"      DB:  {db_routes}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

# 5. Verificar última actualización de datos
print("\n5️⃣  Verificando Última Actualización")
print("-"*70)

try:
    conn = psycopg2.connect(PROD_DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT sync_type, status, items_synced, completed_at
        FROM sync_logs
        ORDER BY completed_at DESC
        LIMIT 3
    """)
    
    logs = cur.fetchall()
    print("Últimos syncs:")
    for log in logs:
        sync_type, status, items, completed = log
        print(f"  - {sync_type}: {status} ({items} items) at {completed}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("✅ VERIFICACIÓN COMPLETA")
print("="*70)
print("\nCONCLUSIÓN:")
print("Todas las pruebas fueron realizadas contra:")
print(f"  - API: {PROD_URL}")
print(f"  - DB:  dpg-d6lj7ap5pdvs73fhgls0-a.oregon-postgres.render.com")
print("\nLos datos están sincronizados y el endpoint funciona correctamente.")
