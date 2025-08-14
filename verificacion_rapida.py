#!/usr/bin/env python3
"""
Verificación rápida del estado de los PDFs específicos
Sin caracteres unicode problemáticos
"""

import os
from pathlib import Path

def verificacion_rapida():
    """Verificación rápida sin dependencias externas"""
    print("="*60)
    print("VERIFICACION RAPIDA - PDFs CRITICOS")
    print("="*60)
    
    pdfs_objetivo = [
        "BOB-CWS-CM-001-R1-ROBLOX",
        "BOB-CWS-CM-001-R2-ROBLOX"
    ]
    
    print("PDFs a verificar:")
    for pdf in pdfs_objetivo:
        print(f"  - {pdf}")
    print()
    
    # Verificar en Downloads
    print("1. VERIFICANDO DOWNLOADS:")
    downloads_path = Path("C:/Users/SDS/Downloads")
    encontrados_downloads = 0
    
    for pdf in pdfs_objetivo:
        variaciones = [f"{pdf}.pdf", f"Cotizacion_{pdf}.pdf"]
        encontrado = False
        
        for variacion in variaciones:
            archivo = downloads_path / variacion
            if archivo.exists():
                stat = archivo.stat()
                print(f"   [OK] {variacion}")
                print(f"        Tamaño: {stat.st_size} bytes")
                encontrado = True
                encontrados_downloads += 1
                break
        
        if not encontrado:
            print(f"   [NO] {pdf} - No encontrado")
    
    print(f"   Resumen Downloads: {encontrados_downloads}/{len(pdfs_objetivo)} encontrados")
    print()
    
    # Verificar en carpetas configuradas
    print("2. VERIFICANDO CARPETAS LOCALES:")
    base_path = Path("G:/Mi unidad/CWS/CWS_Cotizaciones_PDF")
    carpetas = [base_path / "nuevas", base_path / "antiguas"]
    encontrados_locales = 0
    
    for carpeta in carpetas:
        print(f"   Carpeta: {carpeta.name}")
        if carpeta.exists():
            for pdf in pdfs_objetivo:
                variaciones = [f"{pdf}.pdf", f"Cotizacion_{pdf}.pdf"]
                encontrado = False
                
                for variacion in variaciones:
                    archivo = carpeta / variacion
                    if archivo.exists():
                        stat = archivo.stat()
                        print(f"     [OK] {variacion}")
                        print(f"          Tamaño: {stat.st_size} bytes")
                        encontrado = True
                        encontrados_locales += 1
                        break
                
                if not encontrado:
                    print(f"     [NO] {pdf}")
        else:
            print(f"     [ERROR] Carpeta no existe: {carpeta}")
    
    print(f"   Resumen Locales: {encontrados_locales} archivos encontrados")
    print()
    
    # Verificar variables de entorno
    print("3. VERIFICANDO VARIABLES DE ENTORNO:")
    variables_cloudinary = [
        ("CLOUDINARY_CLOUD_NAME", os.getenv('CLOUDINARY_CLOUD_NAME')),
        ("CLOUDINARY_API_KEY", os.getenv('CLOUDINARY_API_KEY')),
        ("CLOUDINARY_API_SECRET", os.getenv('CLOUDINARY_API_SECRET'))
    ]
    
    config_ok = True
    for var_name, var_value in variables_cloudinary:
        if var_value:
            # Ocultar API_SECRET excepto últimos 4 caracteres
            if "SECRET" in var_name and len(var_value) > 4:
                valor_mostrar = "*" * (len(var_value) - 4) + var_value[-4:]
            else:
                valor_mostrar = var_value
            print(f"   [OK] {var_name}: {valor_mostrar}")
        else:
            print(f"   [ERROR] {var_name}: NO CONFIGURADA")
            config_ok = False
    
    print()
    
    # Resumen final
    print("4. RESUMEN FINAL:")
    print("-" * 40)
    
    if encontrados_downloads == len(pdfs_objetivo):
        print("   [OK] Todos los PDFs encontrados en Downloads")
    else:
        print(f"   [WARNING] Solo {encontrados_downloads}/{len(pdfs_objetivo)} PDFs en Downloads")
    
    if encontrados_locales > 0:
        print(f"   [INFO] {encontrados_locales} PDFs adicionales en carpetas locales")
    
    if config_ok:
        print("   [OK] Variables Cloudinary configuradas")
    else:
        print("   [ERROR] Variables Cloudinary incompletas")
    
    print()
    
    # Estado general
    if encontrados_downloads == len(pdfs_objetivo) and config_ok:
        estado = "OPTIMO"
        mensaje = "PDFs seguros, configuración completa"
    elif encontrados_downloads == len(pdfs_objetivo):
        estado = "BUENO"
        mensaje = "PDFs seguros, corregir configuración Cloudinary"
    elif encontrados_downloads > 0:
        estado = "ACEPTABLE" 
        mensaje = "Algunos PDFs encontrados, revisar configuración"
    else:
        estado = "CRITICO"
        mensaje = "PDFs no encontrados, verificar manualmente"
    
    print(f"ESTADO GENERAL: {estado}")
    print(f"MENSAJE: {mensaje}")
    print()
    
    # Próximos pasos
    print("5. PROXIMOS PASOS:")
    print("-" * 40)
    
    if not config_ok:
        print("   1. [CRITICO] Actualizar credenciales Cloudinary:")
        print("      - Ir a: https://console.cloudinary.com/settings/api-keys")
        print("      - Regenerar API Secret")
        print("      - Actualizar archivo .env")
        print()
    
    print("   2. [VERIFICACION] Ejecutar test de conectividad:")
    print("      python test_cloudinary_simple.py")
    print()
    
    print("   3. [DEPLOY] Verificar variables en Render Dashboard")
    print("      antes del deploy")
    print()
    
    print("   4. [POST-DEPLOY] Ejecutar verificación completa:")
    print("      python verificar_pdfs_especificos.py")
    
    return {
        "pdfs_downloads": encontrados_downloads,
        "pdfs_locales": encontrados_locales,
        "config_ok": config_ok,
        "estado": estado
    }

if __name__ == "__main__":
    try:
        resultado = verificacion_rapida()
        print()
        print("Verificación rápida completada.")
        
        # Código de salida basado en estado
        if resultado["estado"] in ["OPTIMO", "BUENO"]:
            exit(0)  # Éxito
        elif resultado["estado"] == "ACEPTABLE":
            exit(1)  # Warning
        else:
            exit(2)  # Error
            
    except Exception as e:
        print(f"\nError en verificación: {e}")
        exit(3)