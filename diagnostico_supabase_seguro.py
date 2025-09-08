#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO SEGURO SUPABASE POSTGRESQL
=====================================
SOLO CONSULTAS SELECT - NO MODIFICA NADA
Verifica el estado actual del schema en Supabase PostgreSQL
"""

import os
import json
from dotenv import load_dotenv
from datetime import datetime

def safe_print(text):
    """Print que maneja encoding en Windows"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='ignore').decode('ascii'))

def diagnostico_supabase_schema():
    """
    Diagnóstico completo del schema Supabase PostgreSQL
    GARANTÍA: SOLO consultas SELECT - No modifica nada
    """
    safe_print("=" * 70)
    safe_print("DIAGNOSTICO SEGURO SUPABASE POSTGRESQL")
    safe_print("SOLO CONSULTAS SELECT - NO MODIFICA NADA")
    safe_print("=" * 70)
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar variables disponibles
    safe_print("\n1. VERIFICACION DE VARIABLES DE ENTORNO:")
    safe_print("-" * 50)
    
    variables_requeridas = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY'),
        'DATABASE_URL': os.getenv('DATABASE_URL')
    }
    
    for var, valor in variables_requeridas.items():
        if valor:
            safe_print(f"✅ {var}: Configurada ({len(valor)} caracteres)")
            if var == 'DATABASE_URL' and valor:
                safe_print(f"   Inicio: {valor[:50]}...")
        else:
            safe_print(f"❌ {var}: NO configurada")
    
    database_url = variables_requeridas['DATABASE_URL']
    if not database_url:
        safe_print("\n❌ ERROR: DATABASE_URL no configurada. No se puede continuar.")
        return
    
    # Intentar conexión PostgreSQL directa
    safe_print("\n2. CONEXION POSTGRESQL DIRECTA:")
    safe_print("-" * 50)
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parsear DATABASE_URL
        parsed = urlparse(database_url)
        safe_print(f"Host: {parsed.hostname}")
        safe_print(f"Puerto: {parsed.port}")
        safe_print(f"Base de datos: {parsed.path[1:]}")
        safe_print(f"Usuario: {parsed.username}")
        
        # Conectar con timeout
        safe_print("\nIntentando conexión...")
        
        conn = psycopg2.connect(
            database_url,
            connect_timeout=10,
            sslmode='require'
        )
        
        cursor = conn.cursor()
        safe_print("✅ CONEXIÓN POSTGRESQL EXITOSA!")
        
        # 3. VERIFICAR TABLAS EXISTENTES
        safe_print("\n3. TABLAS EXISTENTES EN SUPABASE:")
        safe_print("-" * 50)
        
        cursor.execute("""
            SELECT 
                table_name,
                table_type,
                table_schema
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tablas = cursor.fetchall()
        
        if tablas:
            safe_print("Tablas encontradas:")
            for tabla in tablas:
                safe_print(f"  📋 {tabla[0]} ({tabla[1]})")
        else:
            safe_print("❌ NO se encontraron tablas públicas")
        
        # Verificar tablas específicas necesarias
        tablas_necesarias = ['cotizaciones', 'cotizacion_counters', 'pdf_storage']
        tablas_existentes = [t[0] for t in tablas]
        
        safe_print("\nVerificación de tablas necesarias:")
        for tabla in tablas_necesarias:
            if tabla in tablas_existentes:
                safe_print(f"  ✅ {tabla}: EXISTE")
            else:
                safe_print(f"  ❌ {tabla}: FALTA")
        
        # 4. VERIFICAR ESTRUCTURA DE TABLA COTIZACIONES
        if 'cotizaciones' in tablas_existentes:
            safe_print("\n4. ESTRUCTURA DE TABLA 'cotizaciones':")
            safe_print("-" * 50)
            
            cursor.execute("""
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'cotizaciones'
                    AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            
            columnas = cursor.fetchall()
            
            if columnas:
                safe_print("Columnas existentes:")
                for col in columnas:
                    nombre, tipo, nullable, default, max_len = col
                    info_extra = f"({max_len})" if max_len else ""
                    safe_print(f"  📊 {nombre}: {tipo}{info_extra} | Nullable: {nullable}")
                    if default:
                        safe_print(f"       Default: {default}")
                
                # Verificar columnas críticas
                columnas_necesarias = ['numero_cotizacion', 'datos_generales', 'items', 'condiciones']
                columnas_existentes_tabla = [c[0] for c in columnas]
                
                safe_print("\nVerificación de columnas críticas:")
                for col in columnas_necesarias:
                    if col in columnas_existentes_tabla:
                        safe_print(f"  ✅ {col}: EXISTE")
                    else:
                        safe_print(f"  ❌ {col}: FALTA - PROBLEMA CRÍTICO")
            
            # Verificar datos existentes en cotizaciones
            safe_print("\n5. DATOS EXISTENTES EN COTIZACIONES:")
            safe_print("-" * 50)
            
            cursor.execute("SELECT COUNT(*) FROM cotizaciones;")
            count = cursor.fetchone()[0]
            safe_print(f"Total de registros: {count}")
            
            if count > 0:
                # Mostrar últimos 3 registros
                cursor.execute("""
                    SELECT numero_cotizacion, fecha_creacion
                    FROM cotizaciones 
                    ORDER BY fecha_creacion DESC 
                    LIMIT 3;
                """)
                
                ultimos = cursor.fetchall()
                safe_print("Últimas cotizaciones:")
                for reg in ultimos:
                    safe_print(f"  📄 {reg[0]} - {reg[1]}")
        
        else:
            safe_print("\n4. TABLA 'cotizaciones': NO EXISTE - PROBLEMA CRÍTICO")
        
        # 6. VERIFICAR TABLA COTIZACION_COUNTERS
        if 'cotizacion_counters' in tablas_existentes:
            safe_print("\n6. TABLA 'cotizacion_counters':")
            safe_print("-" * 50)
            
            cursor.execute("SELECT COUNT(*) FROM cotizacion_counters;")
            count_counters = cursor.fetchone()[0]
            safe_print(f"Total de contadores: {count_counters}")
            
            if count_counters > 0:
                cursor.execute("""
                    SELECT patron, ultimo_numero, descripcion
                    FROM cotizacion_counters 
                    ORDER BY patron;
                """)
                
                contadores = cursor.fetchall()
                safe_print("Contadores existentes:")
                for contador in contadores:
                    safe_print(f"  🔢 {contador[0]}: {contador[1]} - {contador[2]}")
        else:
            safe_print("\n6. TABLA 'cotizacion_counters': NO EXISTE - NUMERACIÓN AFECTADA")
        
        # 7. VERIFICAR ÍNDICES
        safe_print("\n7. ÍNDICES DE RENDIMIENTO:")
        safe_print("-" * 50)
        
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public' 
                AND tablename IN ('cotizaciones', 'cotizacion_counters', 'pdf_storage')
            ORDER BY tablename, indexname;
        """)
        
        indices = cursor.fetchall()
        
        if indices:
            for idx in indices:
                safe_print(f"  🔍 {idx[1]}.{idx[2]}")
        else:
            safe_print("❌ No se encontraron índices personalizados")
        
        # Cerrar conexión
        cursor.close()
        conn.close()
        
        safe_print("\n" + "=" * 70)
        safe_print("DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        safe_print("=" * 70)
        
    except ImportError:
        safe_print("❌ ERROR: psycopg2 no está instalado")
        safe_print("Instalar con: pip install psycopg2-binary")
        
    except Exception as e:
        safe_print(f"\n❌ ERROR DE CONEXIÓN POSTGRESQL:")
        safe_print(f"   {str(e)}")
        safe_print(f"   Tipo: {type(e).__name__}")
        
        # Intentar diagnóstico con Supabase SDK
        safe_print("\n8. INTENTANDO CONEXIÓN VIA SUPABASE SDK:")
        safe_print("-" * 50)
        
        try:
            from supabase_manager import SupabaseManager
            
            db = SupabaseManager()
            safe_print(f"Modo offline: {db.modo_offline}")
            
            if not db.modo_offline:
                safe_print("✅ Supabase SDK conectado - el problema es PostgreSQL directo")
                
                # Intentar consulta simple via SDK
                try:
                    result = db.supabase_client.table('cotizaciones').select('count', count='exact').execute()
                    safe_print(f"Registros via SDK: {result.count}")
                except Exception as sdk_error:
                    safe_print(f"❌ Error en consulta SDK: {sdk_error}")
            else:
                safe_print("❌ Supabase SDK también en modo offline")
                
        except Exception as sdk_error:
            safe_print(f"❌ Error importando Supabase SDK: {sdk_error}")

def resumen_diagnostico():
    """Mostrar resumen con recomendaciones"""
    safe_print("\n" + "=" * 70)
    safe_print("RESUMEN Y PRÓXIMOS PASOS:")
    safe_print("=" * 70)
    
    safe_print("\n🔍 Este diagnóstico identificará:")
    safe_print("   1. Si las tablas existen o faltan")
    safe_print("   2. Si la columna 'condiciones' existe")
    safe_print("   3. El estado de los contadores")
    safe_print("   4. La causa exacta del error SSL")
    safe_print("\n📋 Basado en los resultados, el siguiente paso será:")
    safe_print("   A. Ejecutar fix_supabase_schema.sql (si faltan tablas)")
    safe_print("   B. Solo agregar columnas faltantes (si schema parcial)")
    safe_print("   C. Arreglar configuración SSL (si schema completo)")

if __name__ == "__main__":
    diagnostico_supabase_schema()
    resumen_diagnostico()