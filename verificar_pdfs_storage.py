#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR DE PDFS EN SUPABASE STORAGE
=======================================

Script para verificar el estado de PDFs en Supabase Storage
y en la tabla pdf_storage de la base de datos.
"""

import os
import sys
from datetime import datetime

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from supabase_manager import SupabaseManager
except ImportError as e:
    print(f"Error importando SupabaseManager: {e}")
    sys.exit(1)

def verificar_estructura_tablas(db_manager):
    """Verificar estructura de tablas relacionadas con PDFs"""
    print("VERIFICANDO ESTRUCTURA DE TABLAS:")
    print("-" * 40)
    
    if db_manager.modo_offline:
        print("Modo offline - No se puede verificar estructura")
        return
    
    try:
        cursor = db_manager.pg_connection.cursor()
        
        # Verificar tabla cotizaciones
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'cotizaciones' 
            ORDER BY ordinal_position;
        """)
        
        columns_cotizaciones = cursor.fetchall()
        print("Tabla 'cotizaciones':")
        for col in columns_cotizaciones:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        print()
        
        # Verificar tabla pdf_storage
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'pdf_storage' 
            ORDER BY ordinal_position;
        """)
        
        columns_pdf = cursor.fetchall()
        print("Tabla 'pdf_storage':")
        if columns_pdf:
            for col in columns_pdf:
                print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        else:
            print("  (Tabla no encontrada o sin columnas)")
        print()
        
        cursor.close()
        
    except Exception as e:
        print(f"Error verificando estructura: {e}")

def verificar_registros_pdf_storage(db_manager):
    """Verificar todos los registros en pdf_storage"""
    print("VERIFICANDO REGISTROS PDF_STORAGE:")
    print("-" * 40)
    
    if db_manager.modo_offline:
        print("Modo offline - No se puede verificar registros")
        return
    
    try:
        cursor = db_manager.pg_connection.cursor()
        
        # Contar total de registros
        cursor.execute("SELECT COUNT(*) as total FROM pdf_storage;")
        total = cursor.fetchone()['total']
        print(f"Total registros: {total}")
        
        if total > 0:
            # Obtener todos los registros
            cursor.execute("""
                SELECT id, numero_cotizacion, filename, file_size, 
                       created_at, updated_at, pdf_data IS NOT NULL as tiene_datos,
                       CASE WHEN pdf_data IS NOT NULL 
                            THEN LENGTH(pdf_data) 
                            ELSE 0 
                       END as tamano_datos
                FROM pdf_storage 
                ORDER BY created_at DESC;
            """)
            
            registros = cursor.fetchall()
            
            print(f"\nDetalles de registros:")
            for i, reg in enumerate(registros, 1):
                print(f"[{i}] ID: {reg['id']}")
                print(f"    Cotización: {reg['numero_cotizacion']}")
                print(f"    Filename: {reg['filename']}")
                print(f"    File Size: {reg['file_size']} bytes")
                print(f"    Tiene Datos: {reg['tiene_datos']}")
                print(f"    Tamaño Datos: {reg['tamano_datos']} bytes")
                print(f"    Creado: {reg['created_at']}")
                print(f"    Actualizado: {reg['updated_at']}")
                print()
        else:
            print("No hay registros en pdf_storage")
        
        cursor.close()
        
    except Exception as e:
        print(f"Error verificando registros: {e}")

def verificar_supabase_storage_buckets(db_manager):
    """Verificar buckets en Supabase Storage"""
    print("VERIFICANDO SUPABASE STORAGE BUCKETS:")
    print("-" * 40)
    
    if not db_manager.supabase_client:
        print("Cliente Supabase no disponible")
        return
    
    try:
        # Listar buckets
        buckets_response = db_manager.supabase_client.storage.list_buckets()
        
        if buckets_response:
            print(f"Buckets encontrados: {len(buckets_response)}")
            for bucket in buckets_response:
                print(f"  - {bucket.name} (ID: {bucket.id})")
                print(f"    Público: {bucket.public}")
                print(f"    Creado: {bucket.created_at}")
                print()
        else:
            print("No se encontraron buckets")
        
        # Intentar acceder al bucket 'pdfs'
        print("Verificando bucket 'pdfs':")
        try:
            files_response = db_manager.supabase_client.storage.from_("pdfs").list()
            
            if files_response:
                print(f"Archivos en bucket 'pdfs': {len(files_response)}")
                for file_info in files_response:
                    print(f"  - {file_info['name']}")
                    print(f"    Tamaño: {file_info.get('metadata', {}).get('size', 'N/A')} bytes")
                    print(f"    Modificado: {file_info.get('updated_at', 'N/A')}")
                    print()
            else:
                print("Bucket 'pdfs' vacío")
                
        except Exception as bucket_error:
            print(f"Error accediendo a bucket 'pdfs': {bucket_error}")
        
    except Exception as e:
        print(f"Error verificando Storage: {e}")

def buscar_archivos_por_cotizacion(db_manager, numero_cotizacion):
    """Buscar archivos específicos por número de cotización"""
    print(f"BUSCANDO ARCHIVOS PARA: {numero_cotizacion}")
    print("-" * 40)
    
    # Buscar en base de datos
    if not db_manager.modo_offline:
        try:
            cursor = db_manager.pg_connection.cursor()
            cursor.execute("""
                SELECT * FROM pdf_storage 
                WHERE numero_cotizacion = %s;
            """, (numero_cotizacion,))
            
            registros = cursor.fetchall()
            if registros:
                print("Encontrado en pdf_storage:")
                for reg in registros:
                    print(f"  ID: {reg['id']}")
                    print(f"  Filename: {reg['filename']}")
                    print(f"  Tiene datos: {reg['pdf_data'] is not None}")
                    print()
            else:
                print("No encontrado en pdf_storage")
            
            cursor.close()
            
        except Exception as e:
            print(f"Error buscando en BD: {e}")
    
    # Buscar en Storage
    if db_manager.supabase_client:
        try:
            files_response = db_manager.supabase_client.storage.from_("pdfs").list()
            
            archivos_encontrados = []
            if files_response:
                for file_info in files_response:
                    if numero_cotizacion in file_info['name']:
                        archivos_encontrados.append(file_info)
            
            if archivos_encontrados:
                print("Encontrado en Storage:")
                for archivo in archivos_encontrados:
                    print(f"  Archivo: {archivo['name']}")
                    print(f"  Tamaño: {archivo.get('metadata', {}).get('size', 'N/A')}")
                    print()
            else:
                print("No encontrado en Storage")
                
        except Exception as e:
            print(f"Error buscando en Storage: {e}")

def main():
    """Función principal"""
    
    print("VERIFICADOR DE PDFS EN SUPABASE")
    print("=" * 50)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Inicializar manager
    try:
        db_manager = SupabaseManager()
    except Exception as e:
        print(f"Error inicializando manager: {e}")
        return
    
    try:
        # 1. Verificar estructura de tablas
        verificar_estructura_tablas(db_manager)
        
        # 2. Verificar registros en pdf_storage
        verificar_registros_pdf_storage(db_manager)
        
        # 3. Verificar buckets en Storage
        verificar_supabase_storage_buckets(db_manager)
        
        # 4. Buscar archivos específicos para la cotización
        buscar_archivos_por_cotizacion(db_manager, "BMW-CWS-CM-001-R1-GROW")
        
    finally:
        try:
            db_manager.close()
        except:
            pass
    
    print("=" * 50)
    print("VERIFICACION COMPLETADA")
    print("=" * 50)

if __name__ == "__main__":
    main()