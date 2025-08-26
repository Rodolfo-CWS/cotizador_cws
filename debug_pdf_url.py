#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug específico para URLs de PDFs en Supabase Storage
"""

import os
import requests
from supabase_storage_manager import SupabaseStorageManager

def debug_pdf_urls():
    """Verificar URLs de PDFs en Supabase Storage"""
    print("=" * 60)
    print("DEBUG: URLS DE PDFs EN SUPABASE STORAGE")
    print("=" * 60)
    
    # 1. Inicializar Supabase Storage
    print("\n1. INICIALIZANDO SUPABASE STORAGE:")
    storage = SupabaseStorageManager()
    
    if not storage.is_available():
        print("ERROR: Supabase Storage no disponible")
        return False
    
    print("OK: Supabase Storage inicializado")
    
    # 2. Listar PDFs disponibles
    print("\n2. LISTANDO PDFs DISPONIBLES:")
    resultado = storage.listar_pdfs()
    
    if "error" in resultado:
        print(f"ERROR: {resultado['error']}")
        return False
    
    archivos = resultado.get("archivos", [])
    print(f"Total PDFs encontrados: {len(archivos)}")
    
    if len(archivos) == 0:
        print("No hay PDFs para probar")
        return False
    
    # 3. Probar URL del primer PDF
    primer_pdf = archivos[0]
    print(f"\n3. PROBANDO URL DEL PRIMER PDF:")
    print(f"   Nombre: {primer_pdf.get('name', 'N/A')}")
    print(f"   File path: {primer_pdf.get('file_path', 'N/A')}")
    print(f"   URL: {primer_pdf.get('url', 'N/A')}")
    
    url_pdf = primer_pdf.get('url')
    if not url_pdf:
        print("ERROR: No hay URL disponible")
        return False
    
    # 4. Verificar accesibilidad de la URL
    print(f"\n4. VERIFICANDO ACCESIBILIDAD DE LA URL:")
    try:
        response = requests.head(url_pdf, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"   Content-Length: {response.headers.get('content-length', 'N/A')}")
        
        if response.status_code == 200:
            print("SUCCESS: URL accesible correctamente")
            
            # 5. Probar descarga completa
            print(f"\n5. PROBANDO DESCARGA COMPLETA:")
            response_full = requests.get(url_pdf, timeout=30)
            if response_full.status_code == 200:
                content_length = len(response_full.content)
                print(f"SUCCESS: PDF descargado exitosamente ({content_length} bytes)")
                
                # Verificar que es un PDF válido
                if response_full.content.startswith(b'%PDF'):
                    print("SUCCESS: Archivo es un PDF válido")
                    return True
                else:
                    print("ERROR: Archivo descargado no es un PDF válido")
                    print(f"   Primeros 50 bytes: {response_full.content[:50]}")
            else:
                print(f"ERROR: Descarga falló con código {response_full.status_code}")
                
        elif response.status_code == 302:
            print("WARNING: URL redirige (302)")
            print(f"   Location: {response.headers.get('location', 'N/A')}")
            # Seguir la redirección
            if response.headers.get('location'):
                print("   Siguiendo redirección...")
                return debug_redirect_url(response.headers.get('location'))
        else:
            print(f"ERROR: URL no accesible (código {response.status_code})")
            
    except requests.RequestException as e:
        print(f"ERROR: Excepción al acceder URL: {e}")
        return False
    
    return False

def debug_redirect_url(redirect_url):
    """Debug específico para URL de redirección"""
    print(f"   PROBANDO URL DE REDIRECCIÓN: {redirect_url}")
    
    try:
        response = requests.head(redirect_url, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   SUCCESS: URL de redirección funciona")
            return True
        else:
            print(f"   ERROR: URL de redirección también falla ({response.status_code})")
            return False
            
    except requests.RequestException as e:
        print(f"   ERROR: Excepción en redirección: {e}")
        return False

def debug_bucket_policies():
    """Verificar políticas del bucket"""
    print("\n6. VERIFICANDO CONFIGURACIÓN DEL BUCKET:")
    
    # Obtener información del bucket
    storage = SupabaseStorageManager()
    bucket_name = storage.bucket_name
    
    print(f"   Bucket: {bucket_name}")
    
    # Intentar obtener información de políticas (esto requiere permisos admin)
    try:
        # Esto podría fallar si no tenemos permisos suficientes
        print("   Verificando acceso público...")
        
        # Crear URL manual para verificar formato
        supabase_url = os.getenv('SUPABASE_URL')
        if supabase_url:
            url_ejemplo = f"{supabase_url}/storage/v1/object/public/{bucket_name}/nuevas/test.pdf"
            print(f"   Formato URL esperado: {url_ejemplo}")
            
            # Verificar si la URL base responde
            base_storage_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}"
            response = requests.head(base_storage_url, timeout=10)
            print(f"   Status base storage URL: {response.status_code}")
            
    except Exception as e:
        print(f"   ERROR verificando bucket: {e}")

if __name__ == "__main__":
    success = debug_pdf_urls()
    debug_bucket_policies()
    
    print(f"\nRESULTADO: {'SUCCESS' if success else 'FALLA'}")
    
    if not success:
        print("\nPROBLEMA DETECTADO:")
        print("- Las URLs de Supabase Storage no son accesibles públicamente")
        print("- Verificar configuración de políticas RLS en Supabase")
        print("- El bucket debe tener acceso público para visualización directa")