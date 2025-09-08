#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final para verificar que la visualización de PDFs funciona correctamente
"""

import requests
from supabase_storage_manager import SupabaseStorageManager

def test_pdf_visualization_fix():
    """Test completo de visualización de PDFs"""
    print("=" * 60)
    print("TEST FINAL: VISUALIZACIÓN DE PDFs CORREGIDA")
    print("=" * 60)
    
    # 1. Verificar que hay PDFs en Supabase Storage
    print("\n1. VERIFICANDO PDFs EN SUPABASE STORAGE:")
    storage = SupabaseStorageManager()
    
    if not storage.is_available():
        print("ERROR: Supabase Storage no disponible")
        return False
    
    resultado = storage.listar_pdfs()
    if "error" in resultado:
        print(f"ERROR: {resultado['error']}")
        return False
    
    archivos = resultado.get("archivos", [])
    print(f"PDFs encontrados: {len(archivos)}")
    
    if len(archivos) == 0:
        print("ERROR: No hay PDFs para probar")
        return False
    
    # 2. Seleccionar PDF para probar
    test_pdf = archivos[0]
    numero_cotizacion = test_pdf.get("numero_cotizacion", "")
    url_directa = test_pdf.get("url", "")
    
    print(f"PDF de prueba: {numero_cotizacion}")
    print(f"URL directa: {url_directa}")
    
    # 3. Verificar URL directa funciona
    print(f"\n2. VERIFICANDO URL DIRECTA:")
    try:
        response = requests.get(url_directa, timeout=10)
        if response.status_code == 200 and response.content.startswith(b'%PDF'):
            print(f"SUCCESS: URL directa funciona ({len(response.content)} bytes)")
        else:
            print(f"ERROR: URL directa falla ({response.status_code})")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    # 4. Simular comportamiento del endpoint /pdf/
    print(f"\n3. SIMULANDO ENDPOINT /PDF/ MEJORADO:")
    
    # Lo que debería hacer el endpoint ahora:
    try:
        # Descargar desde Supabase Storage
        print("   Descargando desde Supabase Storage...")
        response = requests.get(url_directa, timeout=30)
        
        if response.status_code == 200:
            print(f"   SUCCESS: Descarga exitosa ({len(response.content)} bytes)")
            
            # Verificar contenido
            if response.content.startswith(b'%PDF'):
                print("   SUCCESS: Contenido es PDF válido")
                print("   SUCCESS: El endpoint debería servir este PDF correctamente")
                return True
            else:
                print("   ERROR: Contenido no es PDF válido")
                return False
        else:
            print(f"   ERROR: Descarga falló ({response.status_code})")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_production_endpoint():
    """Test del endpoint en producción (si está disponible)"""
    print(f"\n4. PROBANDO ENDPOINT EN PRODUCCIÓN:")
    
    # Obtener un PDF para probar
    storage = SupabaseStorageManager()
    resultado = storage.listar_pdfs()
    
    if "error" in resultado or len(resultado.get("archivos", [])) == 0:
        print("No hay PDFs para probar en producción")
        return False
    
    primer_pdf = resultado["archivos"][0]
    numero_cotizacion = primer_pdf.get("numero_cotizacion", "")
    
    # URL de producción
    from urllib.parse import quote
    numero_encoded = quote(numero_cotizacion, safe='-')
    production_url = f"https://cotizador-cws.onrender.com/pdf/{numero_encoded}"
    
    print(f"   URL de producción: {production_url}")
    
    try:
        response = requests.get(production_url, timeout=30)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            if response.content.startswith(b'%PDF'):
                print(f"   SUCCESS: PDF servido correctamente ({len(response.content)} bytes)")
                return True
            else:
                print("   ERROR: Respuesta no es PDF válido")
                print(f"   Contenido: {response.text[:200]}...")
                return False
        else:
            print(f"   ERROR: Endpoint falla ({response.status_code})")
            if response.text:
                print(f"   Respuesta: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"   ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Ejecutando test de visualización de PDFs...")
    
    success_local = test_pdf_visualization_fix()
    success_production = test_production_endpoint()
    
    print(f"\n" + "=" * 60)
    print(f"RESULTADO LOCAL: {'SUCCESS' if success_local else 'FALLA'}")
    print(f"RESULTADO PRODUCCIÓN: {'SUCCESS' if success_production else 'FALLA'}")
    print("=" * 60)
    
    if success_local and success_production:
        print("\n🎉 VISUALIZACIÓN DE PDFs CORREGIDA EXITOSAMENTE")
        print("   - PDFs se sirven directamente desde Flask")
        print("   - No más problemas de redirección")
        print("   - Funcionando en producción")
    else:
        print("\n❌ PROBLEMAS DETECTADOS:")
        if not success_local:
            print("   - Problema con la lógica de descarga")
        if not success_production:
            print("   - Problema en el endpoint de producción")
            print("   - Esperar unos minutos para el deployment")