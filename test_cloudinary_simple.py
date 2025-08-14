#!/usr/bin/env python3
"""
Test simple de Cloudinary para verificar credenciales
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_cloudinary_basico():
    """Test básico de configuración de Cloudinary"""
    print("=" * 50)
    print("TEST BASICO DE CLOUDINARY")
    print("=" * 50)
    
    # Verificar variables de entorno
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')
    
    print("1. VARIABLES DE ENTORNO:")
    print(f"   CLOUD_NAME: '{cloud_name}' (len: {len(cloud_name) if cloud_name else 0})")
    print(f"   API_KEY: '{api_key}' (len: {len(api_key) if api_key else 0})")
    print(f"   API_SECRET: '{'*' * (len(api_secret) - 4) + api_secret[-4:] if api_secret else None}' (len: {len(api_secret) if api_secret else 0})")
    
    # Verificar espacios o caracteres especiales
    if cloud_name:
        if cloud_name != cloud_name.strip():
            print(f"   [WARNING] CLOUD_NAME tiene espacios: repr='{repr(cloud_name)}'")
    
    if api_key:
        if api_key != api_key.strip():
            print(f"   [WARNING] API_KEY tiene espacios: repr='{repr(api_key)}'")
    
    if api_secret:
        if api_secret != api_secret.strip():
            print(f"   [WARNING] API_SECRET tiene espacios: repr='{repr(api_secret)}'")
    
    print()
    
    # Test de importación
    print("2. TEST DE IMPORTACION:")
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
        print("   [OK] Cloudinary importado correctamente")
    except ImportError as e:
        print(f"   [ERROR] Error importando Cloudinary: {e}")
        return False
    
    print()
    
    # Test de configuración
    print("3. TEST DE CONFIGURACION:")
    try:
        cloudinary.config(
            cloud_name=cloud_name.strip() if cloud_name else None,
            api_key=api_key.strip() if api_key else None,
            api_secret=api_secret.strip() if api_secret else None,
            secure=True
        )
        print("   [OK] Configuración aplicada")
    except Exception as e:
        print(f"   [ERROR] Error en configuración: {e}")
        return False
    
    print()
    
    # Test de ping básico (sin usar usage que causa problemas)
    print("4. TEST DE CONECTIVIDAD:")
    try:
        # Usar una operación más simple que no requiera muchos permisos
        result = cloudinary.api.ping()
        print("   [OK] Ping exitoso a Cloudinary")
        print(f"   Respuesta: {result}")
        return True
        
    except Exception as e:
        print(f"   [ERROR] Error en ping: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        
        # Intentar operación alternativa
        try:
            # Crear URL de test (no requiere autenticación)
            test_url = cloudinary.utils.cloudinary_url("test", secure=True)[0]
            print(f"   [INFO] URL de test generada: {test_url}")
            if cloud_name in test_url:
                print("   [PARTIAL] Al menos cloud_name es válido")
                return "partial"
            
        except Exception as e2:
            print(f"   [ERROR] Error generando URL: {e2}")
        
        return False

def verificar_archivos_existentes():
    """Verifica archivos específicos en Cloudinary usando búsqueda manual"""
    print()
    print("=" * 50) 
    print("VERIFICACION MANUAL DE ARCHIVOS")
    print("=" * 50)
    
    try:
        import cloudinary.api
        
        pdfs_objetivo = [
            "BOB-CWS-CM-001-R1-ROBLOX",
            "BOB-CWS-CM-001-R2-ROBLOX"
        ]
        
        print("Buscando archivos específicos...")
        
        # Intentar búsqueda por prefijo en lugar de listar todo
        for pdf in pdfs_objetivo:
            print(f"\nBuscando: {pdf}")
            
            # Probar diferentes variaciones de búsqueda
            variaciones = [
                f"cotizaciones/nuevas/{pdf}",
                f"cotizaciones/antiguas/{pdf}",
                f"cotizaciones/nuevas/Cotizacion_{pdf}",
                f"cotizaciones/antiguas/Cotizacion_{pdf}"
            ]
            
            encontrado = False
            for public_id in variaciones:
                try:
                    result = cloudinary.api.resource(
                        public_id, 
                        resource_type="raw"
                    )
                    print(f"   [ENCONTRADO] {public_id}")
                    print(f"   URL: {result.get('secure_url')}")
                    print(f"   Tamaño: {result.get('bytes')} bytes")
                    print(f"   Fecha: {result.get('created_at')}")
                    encontrado = True
                    break
                    
                except cloudinary.exceptions.NotFound:
                    continue
                except Exception as e:
                    print(f"   [ERROR] {public_id}: {e}")
                    continue
            
            if not encontrado:
                print(f"   [NO ENCONTRADO] {pdf} en ninguna variación")
    
    except Exception as e:
        print(f"Error en verificación manual: {e}")

if __name__ == "__main__":
    print("Iniciando test básico de Cloudinary...")
    
    resultado = test_cloudinary_basico()
    
    if resultado == True:
        print("\n[EXITO] Test básico completado exitosamente")
        verificar_archivos_existentes()
    elif resultado == "partial":
        print("\n[PARCIAL] Configuración parcialmente válida")
        verificar_archivos_existentes()
    else:
        print("\n[FALLO] Test básico falló - revisar configuración")
        
        # Sugerencias de solución
        print("\nSUGERENCIAS:")
        print("1. Verificar que las credenciales en .env sean correctas")
        print("2. Ir a https://cloudinary.com/console/settings/api-keys")
        print("3. Copiar exactamente Cloud name, API Key, API Secret")
        print("4. Verificar que no haya espacios extra")
        print("5. Regenerar API Secret si es necesario")