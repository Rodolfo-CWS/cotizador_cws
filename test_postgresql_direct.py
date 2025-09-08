#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Directo PostgreSQL - Diferentes Configuraciones SSL
========================================================

Probar diferentes configuraciones de CONNECTION STRING para
identificar cual funciona mejor con Supabase PostgreSQL.
"""

import psycopg2
import os
from datetime import datetime

def print_status(mensaje, tipo="INFO"):
    """Imprimir mensaje con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{tipo}] {mensaje}")

def test_connection(connection_string, description):
    """Probar una configuración específica de conexión"""
    print_status(f"=== PROBANDO: {description} ===")
    
    try:
        print_status("Conectando...")
        conn = psycopg2.connect(connection_string)
        
        print_status("Conexión establecida - Probando query...")
        cursor = conn.cursor()
        
        # Test básico
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print_status(f"PostgreSQL: {version[:50]}...")
        
        # Test de tabla
        cursor.execute("SELECT COUNT(*) FROM cotizaciones;")
        count = cursor.fetchone()[0]
        print_status(f"Cotizaciones: {count}")
        
        # Test de inserción
        test_data = {
            'numeroCotizacion': f'TEST-DIRECT-{int(datetime.now().timestamp())}',
            'datosGenerales': '{"cliente": "TEST-DIRECT", "vendedor": "TEST"}',
            'items': '[]',
            'revision': 1,
            'fechaCreacion': datetime.now(),
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        cursor.execute("""
            INSERT INTO cotizaciones (numeroCotizacion, datosGenerales, items, revision, fechaCreacion, timestamp)
            VALUES (%(numeroCotizacion)s, %(datosGenerales)s, %(items)s, %(revision)s, %(fechaCreacion)s, %(timestamp)s)
            RETURNING id;
        """, test_data)
        
        inserted_id = cursor.fetchone()[0]
        print_status(f"Inserción exitosa - ID: {inserted_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_status(f"EXITO: {description} FUNCIONA CORRECTAMENTE", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"ERROR: {e}", "ERROR")
        return False

def main():
    """Probar diferentes configuraciones de conexión PostgreSQL"""
    print_status("TESTING POSTGRESQL CONNECTION CONFIGURATIONS")
    print_status("=" * 60)
    
    # Base connection info
    base_url = "postgresql://postgres.udnlhvmmmyrtrwuahbxh:DwFPdF3XUJ-@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
    
    # Diferentes configuraciones SSL
    configs = [
        (f"{base_url}?sslmode=require", "SSL REQUIRE (más estricto)"),
        (f"{base_url}?sslmode=prefer", "SSL PREFER (negociación automática)"), 
        (f"{base_url}?sslmode=allow", "SSL ALLOW (actual configuración)"),
        (f"{base_url}?sslmode=disable", "SSL DISABLE (sin SSL)"),
        (f"{base_url}", "SIN PARAMETROS SSL (default)"),
        (f"{base_url}?sslmode=require&connect_timeout=10", "SSL REQUIRE + TIMEOUT"),
        ("postgresql://postgres.udnlhvmmmyrtrwuahbxh:DwFPdF3XUJ-@aws-1-us-east-1.connect.psdb.cloud/postgres?sslmode=require", "DIRECT CONNECTION (no pooler)"),
    ]
    
    working_configs = []
    
    for conn_string, description in configs:
        result = test_connection(conn_string, description)
        if result:
            working_configs.append((conn_string, description))
        print()
    
    print_status("=" * 60)
    print_status("RESULTADOS FINALES")
    print_status("=" * 60)
    
    if working_configs:
        print_status("CONFIGURACIONES QUE FUNCIONAN:", "SUCCESS")
        for conn_string, description in working_configs:
            print_status(f"✓ {description}")
            print_status(f"  {conn_string[:80]}...")
    else:
        print_status("NINGUNA CONFIGURACIÓN FUNCIONÓ", "ERROR")
        print_status("El problema puede ser de autenticación, red o configuración de Supabase")

if __name__ == "__main__":
    main()