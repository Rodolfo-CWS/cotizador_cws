#!/usr/bin/env python3
"""
Test simple de Cloudinary - sin unicode
"""

import cloudinary
import cloudinary.api
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_cloudinary():
    """Test simple de credenciales"""
    print("=" * 50)
    print("TEST CLOUDINARY - CREDENCIALES")
    print("=" * 50)
    
    # Obtener credenciales
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')
    
    print(f"Cloud Name: {cloud_name}")
    print(f"API Key: {api_key}")
    print(f"API Secret: {'*' * 20}{api_secret[-4:] if api_secret else 'None'}")
    print()
    
    if not all([cloud_name, api_key, api_secret]):
        print("[ERROR] Credenciales faltantes")
        return False
    
    try:
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        
        print("[OK] Configuracion aplicada")
        
        # Test básico - ping
        print("[TEST] Ejecutando ping...")
        result = cloudinary.api.ping()
        
        print("[SUCCESS] PING EXITOSO!")
        print(f"Result: {result}")
        
        # Test adicional - listar recursos
        print("\n[TEST] Listando recursos...")
        resources = cloudinary.api.resources(max_results=3)
        print(f"[SUCCESS] Recursos encontrados: {len(resources.get('resources', []))}")
        
        for resource in resources.get('resources', [])[:3]:
            print(f"  - {resource.get('public_id', 'Unknown')}")
        
        print("\n[FINAL] CLOUDINARY FUNCIONAL - CREDENCIALES CORRECTAS")
        return True
        
    except Exception as e:
        print(f"[ERROR] Fallo en test: {e}")
        print(f"Tipo de error: {type(e).__name__}")
        
        # Detalles del error
        error_str = str(e)
        if "401" in error_str:
            print("[DIAGNOSTIC] Error 401 - Credenciales incorrectas")
            print("SOLUCION: Verificar API_SECRET en Cloudinary Console")
        elif "403" in error_str:
            print("[DIAGNOSTIC] Error 403 - Permisos insuficientes")
        elif "network" in error_str.lower():
            print("[DIAGNOSTIC] Error de red - Verificar conexion")
        
        return False

if __name__ == "__main__":
    success = test_cloudinary()
    if success:
        print("\n" + "="*50)
        print("RESULTADO: CLOUDINARY LISTO PARA USAR")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("RESULTADO: NECESITA CORRECCION")
        print("="*50)