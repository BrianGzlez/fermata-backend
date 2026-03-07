#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://fermati_db_user:7oudj7InyxA6TfXmS4Mv0bL3zfrhJY9H@dpg-d6lj7ap5pdvs73fhgls0-a.oregon-postgres.render.com/fermati_db"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check ALL periodicities in database
    result = conn.execute(text("""
        SELECT DISTINCT periodicity, COUNT(*) as count
        FROM departures 
        GROUP BY periodicity
        ORDER BY count DESC
    """))
    
    print("TODAS las periodicidades en la base de datos:")
    print("="*60)
    for row in result:
        print(f"  {row[0]:15s}: {row[1]:6d} departures")
    
    print("\n" + "="*60)
    print("INTERPRETACIÓN según la documentación:")
    print("="*60)
    
    mapping = {
        "Fer": "Feriale annuale (todo el año, días laborales)",
        "Fer*": "Feriale annuale (excluido agosto)",
        "Est": "Estivo (1 ago - 9 sept)",
        "Est*": "Estivo (1 ago - 31 agosto)",
        "Fest": "Domingo y festivos",
        "Fest*": "Domingo y festivos (excluido agosto)",
        "Non Scol": "Non scolastico (vacaciones escolares)",
        "Non Scol*": "Non scolastico (excluido agosto)",
        "Scol": "Scolastico (período escolar)",
        "Univ*": "Universitario (1 ene-30 jun; 10 sep-31 dic)",
        "Univ": "Universitario (1 ene-31 jul; 10 sep-31 dic)",
        "F": "Feriale (días laborales)",
        "S": "Scolastico (escolar)",
        "NS": "Non Scolastico (no escolar)",
        "DF": "Desconocido - posiblemente Domenica/Festivo"
    }
    
    result = conn.execute(text("""
        SELECT DISTINCT periodicity
        FROM departures 
        ORDER BY periodicity
    """))
    
    for row in result:
        per = row[0]
        desc = mapping.get(per, "Desconocido")
        print(f"  {per:15s}: {desc}")
