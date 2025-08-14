#!/usr/bin/env python3
"""
Script para subir PDFs existentes a Cloudinary
Sube los PDFs específicos desde Downloads a Cloudinary
"""

import os
import sys
from pathlib import Path
from cloudinary_manager import CloudinaryManager
from database import DatabaseManager

def subir_pdfs_especificos():
    """Sube los PDFs específicos solicitados"""
    print("="*60)
    print("SUBIENDO PDFs ESPECÍFICOS A CLOUDINARY")
    print("="*60)
    
    # PDFs objetivo
    pdfs_objetivo = [
        "BOB-CWS-CM-001-R1-ROBLOX", 
        "BOB-CWS-CM-001-R2-ROBLOX"
    ]
    
    # Inicializar managers
    try:
        cloudinary_manager = CloudinaryManager()
        if not cloudinary_manager.is_available():
            print("❌ ERROR: Cloudinary no disponible. Verificar credenciales.")
            return False
            
        db_manager = DatabaseManager()
        
    except Exception as e:
        print(f"❌ ERROR inicializando managers: {e}")
        return False
    
    # Buscar archivos en Downloads
    downloads_path = Path("C:/Users/SDS/Downloads")
    archivos_encontrados = []
    
    print(f"🔍 Buscando PDFs en: {downloads_path}")
    print()
    
    for pdf_nombre in pdfs_objetivo:
        variaciones = [f"{pdf_nombre}.pdf", f"Cotizacion_{pdf_nombre}.pdf"]
        encontrado = False
        
        for variacion in variaciones:
            archivo_path = downloads_path / variacion
            if archivo_path.exists():
                archivos_encontrados.append({
                    "nombre_cotizacion": pdf_nombre,
                    "archivo_local": archivo_path,
                    "nombre_archivo": variacion
                })
                print(f"✅ ENCONTRADO: {variacion}")
                encontrado = True
                break
        
        if not encontrado:
            print(f"❌ NO ENCONTRADO: {pdf_nombre}")
    
    if not archivos_encontrados:
        print("\n❌ No se encontraron PDFs para subir.")
        return False
    
    print(f"\n📤 Subiendo {len(archivos_encontrados)} archivos...")
    print("-" * 40)
    
    # Subir cada archivo
    resultados = []
    
    for archivo_info in archivos_encontrados:
        nombre_cotizacion = archivo_info["nombre_cotizacion"]
        archivo_local = archivo_info["archivo_local"]
        nombre_archivo = archivo_info["nombre_archivo"]
        
        print(f"\n📤 Subiendo: {nombre_archivo}")
        
        try:
            # Leer archivo
            with open(archivo_local, 'rb') as f:
                contenido_pdf = f.read()
            
            print(f"   📋 Tamaño: {len(contenido_pdf):,} bytes")
            
            # Determinar carpeta (nuevas por defecto)
            carpeta = "nuevas"  # Puedes cambiar lógica aquí si necesario
            
            # Subir a Cloudinary
            resultado = cloudinary_manager.subir_pdf(
                contenido_pdf=contenido_pdf,
                nombre_archivo=nombre_cotizacion,
                carpeta=carpeta
            )
            
            if resultado.get("success"):
                url_cloudinary = resultado.get("url")
                public_id = resultado.get("public_id")
                
                print(f"   ✅ SUBIDO a Cloudinary")
                print(f"   🔗 URL: {url_cloudinary}")
                print(f"   🆔 ID: {public_id}")
                
                # Actualizar base de datos con URL de Cloudinary
                try:
                    # Buscar cotización en base de datos
                    cotizacion = db_manager.obtener_cotizacion(nombre_cotizacion)
                    
                    if cotizacion.get("encontrado"):
                        # Actualizar con URL de Cloudinary
                        datos_cotizacion = cotizacion["datos"]
                        if "archivos" not in datos_cotizacion:
                            datos_cotizacion["archivos"] = {}
                        
                        datos_cotizacion["archivos"]["cloudinary_url"] = url_cloudinary
                        datos_cotizacion["archivos"]["cloudinary_public_id"] = public_id
                        
                        # Guardar cambios
                        resultado_db = db_manager.actualizar_cotizacion(
                            nombre_cotizacion, 
                            datos_cotizacion
                        )
                        
                        if resultado_db.get("success"):
                            print(f"   ✅ Base de datos actualizada")
                        else:
                            print(f"   ⚠️  Error actualizando BD: {resultado_db.get('error', 'Unknown')}")
                    
                    else:
                        print(f"   ⚠️  Cotización no encontrada en BD: {nombre_cotizacion}")
                        
                except Exception as e:
                    print(f"   ⚠️  Error actualizando BD: {e}")
                
                resultados.append({
                    "archivo": nombre_archivo,
                    "status": "SUCCESS",
                    "url": url_cloudinary,
                    "public_id": public_id
                })
                
            else:
                error = resultado.get("error", "Error desconocido")
                print(f"   ❌ ERROR subiendo: {error}")
                resultados.append({
                    "archivo": nombre_archivo,
                    "status": "ERROR", 
                    "error": error
                })
                
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN: {e}")
            resultados.append({
                "archivo": nombre_archivo,
                "status": "EXCEPTION",
                "error": str(e)
            })
    
    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE SUBIDA")
    print("="*60)
    
    exitosos = [r for r in resultados if r["status"] == "SUCCESS"]
    errores = [r for r in resultados if r["status"] != "SUCCESS"]
    
    print(f"✅ EXITOSOS: {len(exitosos)}")
    for resultado in exitosos:
        print(f"   - {resultado['archivo']}: {resultado['url']}")
    
    if errores:
        print(f"\n❌ ERRORES: {len(errores)}")
        for resultado in errores:
            print(f"   - {resultado['archivo']}: {resultado.get('error', 'Unknown')}")
    
    print(f"\n📊 TOTAL: {len(exitosos)}/{len(resultados)} archivos subidos exitosamente")
    
    return len(exitosos) == len(resultados)

def verificar_pdfs_en_cloudinary():
    """Verifica que los PDFs estén correctamente en Cloudinary"""
    print("\n" + "="*60)
    print("VERIFICANDO PDFs EN CLOUDINARY")
    print("="*60)
    
    try:
        cloudinary_manager = CloudinaryManager()
        if not cloudinary_manager.is_available():
            print("❌ ERROR: Cloudinary no disponible")
            return False
        
        pdfs_objetivo = [
            "BOB-CWS-CM-001-R1-ROBLOX",
            "BOB-CWS-CM-001-R2-ROBLOX"
        ]
        
        print("🔍 Buscando PDFs en Cloudinary...")
        print()
        
        todos_encontrados = True
        
        for pdf_nombre in pdfs_objetivo:
            print(f"📄 Verificando: {pdf_nombre}")
            
            # Buscar en carpeta nuevas
            encontrado_nuevas = cloudinary_manager.verificar_archivo_existe(
                pdf_nombre, "nuevas"
            )
            
            # Buscar en carpeta antiguas
            encontrado_antiguas = cloudinary_manager.verificar_archivo_existe(
                pdf_nombre, "antiguas"  
            )
            
            if encontrado_nuevas:
                print(f"   ✅ ENCONTRADO en carpeta 'nuevas'")
            elif encontrado_antiguas:
                print(f"   ✅ ENCONTRADO en carpeta 'antiguas'")
            else:
                print(f"   ❌ NO ENCONTRADO en ninguna carpeta")
                todos_encontrados = False
            
        print()
        if todos_encontrados:
            print("✅ TODOS LOS PDFs VERIFICADOS EN CLOUDINARY")
        else:
            print("❌ ALGUNOS PDFs FALTAN EN CLOUDINARY")
            
        return todos_encontrados
        
    except Exception as e:
        print(f"❌ ERROR en verificación: {e}")
        return False

if __name__ == "__main__":
    try:
        print("Iniciando proceso de subida de PDFs específicos...")
        
        # Subir PDFs
        exito_subida = subir_pdfs_especificos()
        
        if exito_subida:
            # Verificar subida
            verificar_pdfs_en_cloudinary()
            
            print("\n🎉 PROCESO COMPLETADO EXITOSAMENTE")
            print("\n🔗 Los PDFs ahora están disponibles en Cloudinary")
            print("   y las URLs están guardadas en MongoDB")
            
        else:
            print("\n❌ PROCESO COMPLETADO CON ERRORES")
            print("   Revisar los errores mostrados arriba")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()