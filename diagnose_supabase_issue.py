#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico Enfocado del Problema Supabase
=========================================

Script para diagnosticar exactamente qué está fallando con Supabase:
1. Conexión PostgreSQL directa
2. SDK de Supabase REST API
3. Configuración de variables de entorno
"""

import os
import sys
from datetime import datetime

def print_status(mensaje, tipo="INFO"):
    """Imprimir mensaje con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{tipo}] {mensaje}")

def test_environment_variables():
    """Test 1: Verificar variables de entorno"""
    print_status("=== TEST 1: VARIABLES DE ENTORNO ===")
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY', 
        'SUPABASE_SERVICE_KEY',
        'DATABASE_URL'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mostrar solo primeros/últimos caracteres por seguridad
            if len(value) > 20:
                masked = f"{value[:10]}...{value[-10:]}"
            else:
                masked = f"{value[:5]}..."
            print_status(f"{var}: CONFIGURADA ({masked})")
        else:
            print_status(f"{var}: NO CONFIGURADA", "ERROR")
    print()

def test_supabase_imports():
    """Test 2: Verificar imports de librerías"""
    print_status("=== TEST 2: IMPORTS DE LIBRERIAS ===")
    
    try:
        import supabase
        print_status(f"supabase: OK (versión {supabase.__version__})")
    except ImportError as e:
        print_status(f"supabase: ERROR - {e}", "ERROR")
        
    try:
        import psycopg2
        print_status("psycopg2: OK")
    except ImportError as e:
        print_status(f"psycopg2: ERROR - {e}", "ERROR")
        
    print()

def test_postgresql_direct():
    """Test 3: Conexión PostgreSQL directa"""
    print_status("=== TEST 3: POSTGRESQL DIRECTO ===")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print_status("DATABASE_URL no configurada", "ERROR")
        return
        
    try:
        import psycopg2
        print_status("Intentando conexión PostgreSQL directa...")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test básico
        cursor.execute("SELECT version();")
        result = cursor.fetchone()
        print_status(f"PostgreSQL conectado: {result[0][:50]}...")
        
        # Test de tabla cotizaciones
        cursor.execute("SELECT COUNT(*) FROM cotizaciones;")
        count = cursor.fetchone()[0]
        print_status(f"Cotizaciones en BD: {count}")
        
        cursor.close()
        conn.close()
        print_status("PostgreSQL directo: FUNCIONANDO", "SUCCESS")
        
    except Exception as e:
        print_status(f"PostgreSQL directo: ERROR - {e}", "ERROR")
        
    print()

def test_supabase_sdk():
    """Test 4: SDK de Supabase"""
    print_status("=== TEST 4: SUPABASE SDK ===")
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print_status("Variables Supabase no configuradas", "ERROR")
        return
        
    try:
        from supabase import create_client
        print_status("Creando cliente Supabase...")
        
        supabase_client = create_client(supabase_url, supabase_key)
        print_status("Cliente Supabase creado")
        
        # Test de lectura
        print_status("Probando lectura de cotizaciones...")
        response = supabase_client.table('cotizaciones').select('*').limit(1).execute()
        
        print_status(f"SDK Supabase lectura: OK ({len(response.data)} registros)")
        
        # Test de inserción simple
        print_status("Probando inserción de prueba...")
        test_data = {
            'numeroCotizacion': f'TEST-SDK-{int(datetime.now().timestamp())}',
            'datosGenerales': {'cliente': 'TEST-SDK'},
            'items': [],
            'revision': 1,
            'fechaCreacion': datetime.now().isoformat(),
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        response = supabase_client.table('cotizaciones').insert(test_data).execute()
        print_status(f"SDK Supabase inserción: OK (ID: {response.data[0].get('id', 'N/A')})")
        
        print_status("Supabase SDK: FUNCIONANDO", "SUCCESS")
        
    except Exception as e:
        print_status(f"Supabase SDK: ERROR - {e}", "ERROR")
        
    print()

def test_local_supabase_manager():
    """Test 5: SupabaseManager local"""
    print_status("=== TEST 5: SUPABASE MANAGER LOCAL ===")
    
    try:
        # Importar el manager local
        sys.path.insert(0, '.')
        from supabase_manager import SupabaseManager
        
        print_status("Creando SupabaseManager...")
        db = SupabaseManager()
        
        print_status(f"Modo offline: {db.modo_offline}")
        
        if not db.modo_offline:
            print_status("SupabaseManager: ONLINE - Probando operaciones...")
            
            # Test de guardado
            datos_test = {
                'datosGenerales': {
                    'cliente': 'TEST-MANAGER',
                    'vendedor': 'DEBUG', 
                    'proyecto': 'DIAGNÓSTICO'
                },
                'items': [{'descripcion': 'Test item', 'cantidad': 1, 'precio': 100}],
                'observaciones': 'Test diagnóstico SupabaseManager'
            }
            
            resultado = db.guardar_cotizacion(datos_test)
            print_status(f"Guardar resultado: {resultado.get('success', False)} - {resultado.get('mensaje', resultado.get('error', 'Sin mensaje'))}")
            
        else:
            print_status("SupabaseManager: OFFLINE - Usando JSON fallback")
            
    except Exception as e:
        print_status(f"SupabaseManager local: ERROR - {e}", "ERROR")
        import traceback
        traceback.print_exc()
        
    print()

def main():
    """Ejecutar todos los tests de diagnóstico"""
    print_status("INICIANDO DIAGNÓSTICO COMPLETO DE SUPABASE")
    print_status("=" * 50)
    
    test_environment_variables()
    test_supabase_imports()
    test_postgresql_direct()
    test_supabase_sdk()
    test_local_supabase_manager()
    
    print_status("DIAGNÓSTICO COMPLETO TERMINADO")
    print_status("=" * 50)

if __name__ == "__main__":
    main()