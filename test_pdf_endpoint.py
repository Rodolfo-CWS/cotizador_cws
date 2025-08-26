#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico para el endpoint /pdf/ que está fallando
"""

import requests
from supabase_storage_manager import SupabaseStorageManager

def test_pdf_endpoint():
    """Probar el endpoint /pdf/ localmente"""
    print("=" * 60)
    print("TEST: ENDPOINT /PDF/ LOCAL")
    print("=" * 60)
    
    # 1. Obtener un PDF disponible
    print("\n1. OBTENIENDO PDF DISPONIBLE:")
    storage = SupabaseStorageManager()
    
    if not storage.is_available():
        print("ERROR: Supabase Storage no disponible")
        return False
    
    resultado = storage.listar_pdfs()
    if "error" in resultado or len(resultado.get("archivos", [])) == 0:
        print("ERROR: No hay PDFs disponibles para probar")
        return False
    
    primer_pdf = resultado["archivos"][0]
    numero_cotizacion = primer_pdf.get("numero_cotizacion", "")
    url_directa = primer_pdf.get("url", "")
    
    print(f"   PDF seleccionado: {numero_cotizacion}")
    print(f"   URL directa: {url_directa}")
    
    # 2. Probar acceso directo a Supabase Storage
    print("\n2. PROBANDO ACCESO DIRECTO A SUPABASE:")
    try:
        response = requests.head(url_directa, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   SUCCESS: URL directa funciona")
        else:
            print(f"   ERROR: URL directa falla ({response.status_code})")
            return False
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    
    # 3. Probar endpoint local /pdf/ 
    print("\n3. PROBANDO ENDPOINT LOCAL /pdf/:")
    
    # Construir URL del endpoint local
    from urllib.parse import quote
    numero_encoded = quote(numero_cotizacion, safe='-')
    endpoint_url = f"http://localhost:5000/pdf/{numero_encoded}"
    
    print(f"   Endpoint URL: {endpoint_url}")
    
    try:
        # Hacer petición al endpoint local
        response = requests.get(endpoint_url, allow_redirects=False, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 302:
            # Es una redirección
            redirect_url = response.headers.get('location', '')
            print(f"   Redirect URL: {redirect_url}")
            
            # Verificar que la redirección es a la URL correcta
            if redirect_url == url_directa:
                print("   SUCCESS: Redirección correcta")
                
                # Seguir la redirección para confirmar que funciona
                print("\n4. SIGUIENDO REDIRECCIÓN:")
                response_final = requests.get(redirect_url, timeout=30)
                if response_final.status_code == 200:
                    print(f"   SUCCESS: PDF descargado ({len(response_final.content)} bytes)")
                    return True
                else:
                    print(f"   ERROR: Redirección falla ({response_final.status_code})")
                    return False
            else:
                print(f"   ERROR: Redirección incorrecta")
                print(f"   Esperada: {url_directa}")
                print(f"   Recibida: {redirect_url}")
                return False
                
        elif response.status_code == 200:
            print(f"   SUCCESS: PDF servido directamente ({len(response.content)} bytes)")
            return True
        else:
            print(f"   ERROR: Endpoint falla ({response.status_code})")
            if response.text:
                print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

if __name__ == "__main__":
    # Solo ejecutar si el servidor está corriendo
    try:
        requests.get("http://localhost:5000/", timeout=5)
        success = test_pdf_endpoint()
        print(f"\nRESULTADO: {'SUCCESS' if success else 'FALLA'}")
    except:
        print("ERROR: Servidor local no está ejecutando en localhost:5000")
        print("Ejecuta 'python app.py' o 'EJECUTAR_RAPIDO.bat' primero")