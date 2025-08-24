#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Migración de PDFs a Supabase Storage
==============================================

Migra PDFs existentes desde Google Drive/Local hacia Supabase Storage
"""

import os
import sys
from pathlib import Path

# Agregar el directorio actual al path para importar módulos locales
sys.path.append(str(Path(__file__).parent))

try:
    from supabase_storage_manager import SupabaseStorageManager
    from google_drive_client import GoogleDriveClient
    print("OK: Modulos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)

def migrar_pdfs_a_supabase():
    """
    Migra PDFs existentes desde Google Drive y local hacia Supabase Storage
    """
    print("🚀 INICIANDO MIGRACIÓN A SUPABASE STORAGE")
    print("=" * 50)
    
    # Inicializar managers
    print("📦 Inicializando Supabase Storage...")
    ssm = SupabaseStorageManager()
    
    print("📦 Inicializando Google Drive...")
    gdc = GoogleDriveClient()
    
    if not ssm.is_available():
        print("❌ ERROR: Supabase Storage no disponible")
        return False
    
    print("✅ Supabase Storage disponible")
    
    # Lista de PDFs conocidos a migrar (basados en los logs anteriores)
    pdfs_a_migrar = [
        "BIB-CWS-CM-001-R1-HOUSING.pdf",
        "BMW-CWS-FM-001-R1-RACK.pdf", 
        "MAGNA-CWS-RM-001-R1-LARALA.pdf"
    ]
    
    migrados_exitosamente = []
    errores = []
    
    for pdf_nombre in pdfs_a_migrar:
        print(f"\n📄 Procesando: {pdf_nombre}")
        print("-" * 30)
        
        try:
            # Paso 1: Buscar PDF en Google Drive
            print(f"🔍 Buscando en Google Drive...")
            
            # Intentar descargar desde Google Drive
            contenido_pdf = None
            if gdc and gdc.is_available():
                try:
                    contenido_pdf = gdc.obtener_pdf(pdf_nombre.replace('.pdf', ''))
                    if contenido_pdf:
                        print(f"✅ Encontrado en Google Drive: {len(contenido_pdf)} bytes")
                    else:
                        print(f"⚠️  No encontrado en Google Drive")
                except Exception as e:
                    print(f"⚠️  Error buscando en Google Drive: {e}")
            
            # Paso 2: Si no se encontró en Drive, buscar en local
            if not contenido_pdf:
                print(f"🔍 Buscando en almacenamiento local...")
                
                # Rutas posibles para archivos locales
                rutas_posibles = [
                    Path("G:/Mi unidad/CWS/CWS_Cotizaciones_PDF/nuevas") / pdf_nombre,
                    Path("./pdfs_cotizaciones/nuevas") / pdf_nombre,
                    Path("./") / pdf_nombre
                ]
                
                for ruta in rutas_posibles:
                    if ruta.exists():
                        contenido_pdf = ruta.read_bytes()
                        print(f"✅ Encontrado en local: {ruta} ({len(contenido_pdf)} bytes)")
                        break
                
                if not contenido_pdf:
                    print(f"❌ PDF no encontrado en ninguna ubicación")
                    errores.append(f"{pdf_nombre}: No encontrado")
                    continue
            
            # Paso 3: Subir a Supabase Storage
            print(f"📤 Subiendo a Supabase Storage...")
            
            # Crear archivo temporal
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(contenido_pdf)
                temp_file_path = temp_file.name
            
            try:
                # Subir a Supabase Storage
                numero_cotizacion = pdf_nombre.replace('.pdf', '')
                resultado = ssm.subir_pdf(
                    temp_file_path,
                    numero_cotizacion,
                    es_nueva=True
                )
                
                if not resultado.get("fallback", False):
                    print(f"✅ Subido exitosamente a Supabase Storage")
                    print(f"   URL: {resultado.get('url', 'N/A')}")
                    migrados_exitosamente.append(pdf_nombre)
                else:
                    error_msg = resultado.get("error", "Error desconocido")
                    print(f"❌ Error subiendo: {error_msg}")
                    errores.append(f"{pdf_nombre}: {error_msg}")
                    
            finally:
                # Limpiar archivo temporal
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Error procesando {pdf_nombre}: {e}")
            errores.append(f"{pdf_nombre}: {str(e)}")
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE MIGRACIÓN")
    print("=" * 50)
    print(f"✅ PDFs migrados exitosamente: {len(migrados_exitosamente)}")
    for pdf in migrados_exitosamente:
        print(f"   • {pdf}")
    
    if errores:
        print(f"\n❌ PDFs con errores: {len(errores)}")
        for error in errores:
            print(f"   • {error}")
    
    print(f"\n📈 Total procesados: {len(pdfs_a_migrar)}")
    print(f"📈 Tasa de éxito: {len(migrados_exitosamente)/len(pdfs_a_migrar)*100:.1f}%")
    
    # Verificar estado final de Supabase
    print(f"\n📊 Verificando estado final de Supabase Storage...")
    stats = ssm.obtener_estadisticas()
    if "error" not in stats:
        print(f"✅ PDFs ahora en Supabase: {stats.get('total_pdfs', 0)}")
    
    return len(migrados_exitosamente) > 0

def verificar_migracion():
    """
    Verifica que los PDFs migrados sean accesibles desde Supabase Storage
    """
    print("\n🔍 VERIFICANDO MIGRACIÓN")
    print("=" * 30)
    
    ssm = SupabaseStorageManager()
    if not ssm.is_available():
        print("❌ Supabase Storage no disponible para verificación")
        return False
    
    # Listar todos los PDFs en Supabase
    resultado = ssm.listar_pdfs()
    archivos = resultado.get("archivos", [])
    
    print(f"📁 PDFs encontrados en Supabase Storage: {len(archivos)}")
    
    for archivo in archivos:
        nombre = archivo.get("name", "Sin nombre")
        url = archivo.get("url", "Sin URL")
        tamaño = archivo.get("bytes", 0)
        
        print(f"✅ {nombre}")
        print(f"   URL: {url}")
        print(f"   Tamaño: {tamaño} bytes")
        print()
    
    return len(archivos) > 0

if __name__ == "__main__":
    print("🎯 MIGRACIÓN DE PDFs A SUPABASE STORAGE")
    print("Este script migra PDFs existentes desde Google Drive/Local a Supabase Storage")
    print()
    
    # Ejecutar migración
    exito = migrar_pdfs_a_supabase()
    
    if exito:
        print("\n✅ Migración completada con éxito")
        
        # Verificar migración
        verificar_migracion()
        
        print("\n🎉 ¡Migración a Supabase Storage completada!")
        print("Ahora puedes usar Supabase Storage como sistema primario de PDFs")
        
    else:
        print("\n❌ Migración falló - revisar errores arriba")
        sys.exit(1)