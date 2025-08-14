#!/usr/bin/env python3
"""
Test directo de Cloudinary con credenciales específicas
"""

import cloudinary
import cloudinary.api
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_cloudinary_directo():
    """Test directo sin managers intermedios"""
    print("=" * 50)
    print("TEST DIRECTO CLOUDINARY")
    print("=" * 50)
    
    # Obtener credenciales
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')
    
    print(f"Cloud Name: {cloud_name}")
    print(f"API Key: {api_key}")
    print(f"API Secret: {'*' * (len(api_secret) - 4) if api_secret else 'None'}{api_secret[-4:] if api_secret else ''}")
    
    if not all([cloud_name, api_key, api_secret]):
        print("❌ ERROR: Credenciales faltantes")
        return False
    
    try:
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        
        print("\n🔧 Configuración aplicada")
        
        # Test básico - ping
        print("🔍 Ejecutando ping...")
        result = cloudinary.api.ping()
        print("✅ PING EXITOSO:")
        print(f"   Status: {result}")
        
        # Test de recursos
        print("\n🔍 Listando recursos...")
        resources = cloudinary.api.resources(max_results=5)
        print(f"✅ RECURSOS OBTENIDOS: {len(resources.get('resources', []))} archivos")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"   Tipo: {type(e).__name__}")
        
        # Información adicional del error
        if hasattr(e, 'response'):
            print(f"   Response: {e.response}")
        if hasattr(e, 'status_code'):
            print(f"   Status Code: {e.status_code}")
            
        return False

if __name__ == "__main__":
    test_cloudinary_directo()