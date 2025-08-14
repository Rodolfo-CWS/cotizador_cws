#!/usr/bin/env python3
"""
Script de verificación específica de PDFs en Cloudinary
Verifica el estado de los PDFs BOB-CWS-CM-001-R1-ROBLOX y BOB-CWS-CM-001-R2-ROBLOX
"""

import os
import sys
import json
import datetime
from pathlib import Path
from cloudinary_manager import CloudinaryManager
from pdf_manager import PDFManager
from database import DatabaseManager

def verificar_pdfs_especificos():
    """Verifica el estado específico de los PDFs solicitados"""
    
    pdfs_objetivo = [
        "BOB-CWS-CM-001-R1-ROBLOX",
        "BOB-CWS-CM-001-R2-ROBLOX"
    ]
    
    print("=" * 80)
    print("VERIFICACION ESPECIFICA DE PDFs EN CLOUDINARY")
    print("=" * 80)
    print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"PDFs a verificar: {len(pdfs_objetivo)}")
    for pdf in pdfs_objetivo:
        print(f"  - {pdf}")
    print()
    
    # Inicializar managers
    print("INICIALIZANDO SISTEMAS...")
    cloudinary = CloudinaryManager()
    db_manager = DatabaseManager()
    pdf_manager = PDFManager(db_manager)
    
    # Verificar disponibilidad de Cloudinary
    print(f"Cloudinary disponible: {cloudinary.is_available()}")
    print(f"MongoDB disponible: {not db_manager.modo_offline}")
    print()
    
    resultados = {}
    
    for numero_cotizacion in pdfs_objetivo:
        print(f"VERIFICANDO: {numero_cotizacion}")
        print("-" * 60)
        
        resultado_pdf = {
            "numero": numero_cotizacion,
            "timestamp": datetime.datetime.now().isoformat(),
            "cloudinary": {"verificado": False},
            "mongodb": {"verificado": False},
            "local": {"verificado": False},
            "downloads": {"verificado": False},
            "estado_general": "NO_VERIFICADO"
        }
        
        # 1. VERIFICAR EN CLOUDINARY
        print("1. CLOUDINARY:")
        if cloudinary.is_available():
            try:
                # Buscar en carpetas nuevas
                listado_nuevas = cloudinary.listar_pdfs("nuevas", max_resultados=1000)
                # Buscar en carpetas antiguas  
                listado_antiguas = cloudinary.listar_pdfs("antiguas", max_resultados=1000)
                
                archivos_nuevas = listado_nuevas.get("archivos", [])
                archivos_antiguas = listado_antiguas.get("archivos", [])
                todos_archivos = archivos_nuevas + archivos_antiguas
                
                # Buscar coincidencia exacta
                archivo_encontrado = None
                for archivo in todos_archivos:
                    if numero_cotizacion in archivo.get("numero_cotizacion", ""):
                        archivo_encontrado = archivo
                        break
                
                if archivo_encontrado:
                    resultado_pdf["cloudinary"] = {
                        "verificado": True,
                        "encontrado": True,
                        "public_id": archivo_encontrado.get("public_id"),
                        "url": archivo_encontrado.get("url"),
                        "bytes": archivo_encontrado.get("bytes"),
                        "fecha_creacion": archivo_encontrado.get("fecha_creacion"),
                        "carpeta": "nuevas" if archivo_encontrado in archivos_nuevas else "antiguas",
                        "tags": archivo_encontrado.get("tags", []),
                        "context": archivo_encontrado.get("context", {})
                    }
                    print(f"   [OK] ENCONTRADO en Cloudinary")
                    print(f"     Carpeta: {resultado_pdf['cloudinary']['carpeta']}")
                    print(f"     URL: {resultado_pdf['cloudinary']['url']}")
                    print(f"     Tamaño: {resultado_pdf['cloudinary']['bytes']} bytes")
                else:
                    resultado_pdf["cloudinary"] = {
                        "verificado": True,
                        "encontrado": False,
                        "total_archivos_revisados": len(todos_archivos)
                    }
                    print(f"   [NO] NO ENCONTRADO en Cloudinary")
                    print(f"     Total archivos revisados: {len(todos_archivos)}")
                    
            except Exception as e:
                resultado_pdf["cloudinary"] = {
                    "verificado": True,
                    "error": str(e)
                }
                print(f"   [ERROR] ERROR en Cloudinary: {e}")
        else:
            print("   [WARNING] Cloudinary no disponible")
        
        # 2. VERIFICAR EN MONGODB
        print("2. MONGODB:")
        if not db_manager.modo_offline:
            try:
                # Buscar en colección de PDFs
                pdf_info = pdf_manager.obtener_pdf(numero_cotizacion)
                
                if pdf_info.get("encontrado"):
                    registro = pdf_info.get("registro", {})
                    resultado_pdf["mongodb"] = {
                        "verificado": True,
                        "encontrado": True,
                        "tipo": registro.get("tipo"),
                        "fecha": registro.get("fecha"),
                        "cliente": registro.get("cliente"),
                        "vendedor": registro.get("vendedor"),
                        "proyecto": registro.get("proyecto"),
                        "tiene_desglose": registro.get("tiene_desglose"),
                        "ruta_archivo": registro.get("ruta_archivo"),
                        "tamaño_bytes": registro.get("tamaño_bytes"),
                        "cloudinary_info": registro.get("cloudinary", {}),
                        "google_drive_info": registro.get("google_drive", {}),
                        "local_info": registro.get("local", {})
                    }
                    print(f"   [OK] ENCONTRADO en MongoDB")
                    print(f"     Tipo: {registro.get('tipo')}")
                    print(f"     Cliente: {registro.get('cliente')}")
                    print(f"     Fecha: {registro.get('fecha')}")
                else:
                    resultado_pdf["mongodb"] = {
                        "verificado": True,
                        "encontrado": False
                    }
                    print(f"   [NO] NO ENCONTRADO en MongoDB")
                    
            except Exception as e:
                resultado_pdf["mongodb"] = {
                    "verificado": True,
                    "error": str(e)
                }
                print(f"   [ERROR] ERROR en MongoDB: {e}")
        else:
            print("   [WARNING] MongoDB en modo offline")
        
        # 3. VERIFICAR LOCALMENTE
        print("3. LOCAL:")
        try:
            # Verificar en carpetas nuevas y antiguas
            pdf_nuevas = pdf_manager.nuevas_path / f"{numero_cotizacion}.pdf"
            pdf_nuevas_alt = pdf_manager.nuevas_path / f"Cotizacion_{numero_cotizacion}.pdf"
            pdf_antiguas = pdf_manager.antiguas_path / f"{numero_cotizacion}.pdf"
            pdf_antiguas_alt = pdf_manager.antiguas_path / f"Cotizacion_{numero_cotizacion}.pdf"
            
            archivos_locales = [pdf_nuevas, pdf_nuevas_alt, pdf_antiguas, pdf_antiguas_alt]
            archivo_local_encontrado = None
            
            for archivo in archivos_locales:
                if archivo.exists():
                    archivo_local_encontrado = archivo
                    break
            
            if archivo_local_encontrado:
                stat = archivo_local_encontrado.stat()
                resultado_pdf["local"] = {
                    "verificado": True,
                    "encontrado": True,
                    "ruta": str(archivo_local_encontrado.absolute()),
                    "tamaño": stat.st_size,
                    "fecha_modificacion": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "carpeta": "nuevas" if "nuevas" in str(archivo_local_encontrado) else "antiguas"
                }
                print(f"   [OK] ENCONTRADO localmente")
                print(f"     Ruta: {archivo_local_encontrado}")
                print(f"     Tamaño: {stat.st_size} bytes")
                print(f"     Carpeta: {resultado_pdf['local']['carpeta']}")
            else:
                resultado_pdf["local"] = {
                    "verificado": True,
                    "encontrado": False,
                    "rutas_verificadas": [str(archivo) for archivo in archivos_locales]
                }
                print(f"   [NO] NO ENCONTRADO localmente")
                print(f"     Rutas verificadas: {len(archivos_locales)}")
                
        except Exception as e:
            resultado_pdf["local"] = {
                "verificado": True,
                "error": str(e)
            }
            print(f"   [ERROR] ERROR verificando local: {e}")
        
        # 4. VERIFICAR EN DOWNLOADS
        print("4. DOWNLOADS:")
        try:
            downloads_path = Path("C:\\Users\\SDS\\Downloads")
            archivos_downloads = [
                downloads_path / f"{numero_cotizacion}.pdf",
                downloads_path / f"Cotizacion_{numero_cotizacion}.pdf"
            ]
            
            archivo_download_encontrado = None
            for archivo in archivos_downloads:
                if archivo.exists():
                    archivo_download_encontrado = archivo
                    break
            
            if archivo_download_encontrado:
                stat = archivo_download_encontrado.stat()
                resultado_pdf["downloads"] = {
                    "verificado": True,
                    "encontrado": True,
                    "ruta": str(archivo_download_encontrado.absolute()),
                    "tamaño": stat.st_size,
                    "fecha_modificacion": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
                print(f"   [OK] ENCONTRADO en Downloads")
                print(f"     Ruta: {archivo_download_encontrado}")
                print(f"     Tamaño: {stat.st_size} bytes")
            else:
                resultado_pdf["downloads"] = {
                    "verificado": True,
                    "encontrado": False
                }
                print(f"   [NO] NO ENCONTRADO en Downloads")
                
        except Exception as e:
            resultado_pdf["downloads"] = {
                "verificado": True,
                "error": str(e)
            }
            print(f"   [ERROR] ERROR verificando Downloads: {e}")
        
        # 5. DETERMINAR ESTADO GENERAL
        cloudinary_ok = resultado_pdf["cloudinary"].get("encontrado", False)
        mongodb_ok = resultado_pdf["mongodb"].get("encontrado", False)
        local_ok = resultado_pdf["local"].get("encontrado", False)
        downloads_ok = resultado_pdf["downloads"].get("encontrado", False)
        
        if cloudinary_ok:
            resultado_pdf["estado_general"] = "SEGURO_CLOUDINARY"
        elif mongodb_ok and local_ok:
            resultado_pdf["estado_general"] = "SEGURO_LOCAL"
        elif local_ok or downloads_ok:
            resultado_pdf["estado_general"] = "RECUPERABLE"
        else:
            resultado_pdf["estado_general"] = "EN_RIESGO"
        
        print(f"\n   ESTADO GENERAL: {resultado_pdf['estado_general']}")
        print()
        
        resultados[numero_cotizacion] = resultado_pdf
    
    # RESUMEN GENERAL
    print("=" * 80)
    print("RESUMEN GENERAL DE VERIFICACIÓN")
    print("=" * 80)
    
    estados_conteo = {}
    for numero, resultado in resultados.items():
        estado = resultado["estado_general"]
        estados_conteo[estado] = estados_conteo.get(estado, 0) + 1
        print(f"{numero}: {estado}")
    
    print()
    print("DISTRIBUCIÓN DE ESTADOS:")
    for estado, conteo in estados_conteo.items():
        print(f"  {estado}: {conteo} PDF(s)")
    
    # Estadísticas de Cloudinary
    print()
    print("ESTADÍSTICAS DE CLOUDINARY:")
    if cloudinary.is_available():
        try:
            stats = cloudinary.obtener_estadisticas()
            if "error" not in stats:
                print(f"  Total PDFs en Cloudinary: {stats.get('total_pdfs', 0)}")
                print(f"  PDFs en carpeta nuevas: {stats.get('pdfs_nuevos', 0)}")
                print(f"  PDFs en carpeta antiguas: {stats.get('pdfs_antiguos', 0)}")
                print(f"  Storage usado: {stats.get('storage_usado', 0)} bytes")
                print(f"  Bandwidth usado: {stats.get('bandwidth_usado', 0)} bytes")
            else:
                print(f"  Error obteniendo estadísticas: {stats['error']}")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print("  Cloudinary no disponible")
    
    # Guardar resultados
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        archivo_resultados = f"verificacion_pdfs_{timestamp}.json"
        
        with open(archivo_resultados, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        
        print(f"\nResultados guardados en: {archivo_resultados}")
        
    except Exception as e:
        print(f"\nError guardando resultados: {e}")
    
    return resultados

def generar_comandos_verificacion():
    """Genera comandos para verificación manual"""
    print()
    print("=" * 80)
    print("COMANDOS PARA VERIFICACIÓN MANUAL")
    print("=" * 80)
    
    pdfs_objetivo = [
        "BOB-CWS-CM-001-R1-ROBLOX",
        "BOB-CWS-CM-001-R2-ROBLOX"
    ]
    
    print("1. VERIFICAR EN CLOUDINARY (desde Python):")
    print("   ```python")
    print("   from cloudinary_manager import CloudinaryManager")
    print("   cm = CloudinaryManager()")
    print("   ")
    for pdf in pdfs_objetivo:
        print(f"   # Buscar {pdf}")
        print("   nuevas = cm.listar_pdfs('nuevas')")
        print("   antiguas = cm.listar_pdfs('antiguas')")
        print(f"   # Buscar '{pdf}' en los resultados")
        print("   ")
    print("   ```")
    
    print("\n2. VERIFICAR ARCHIVOS LOCALES:")
    for pdf in pdfs_objetivo:
        print(f"   dir \"*{pdf}*\" /s /p")
    
    print("\n3. VERIFICAR EN CLOUDINARY (Web Console):")
    print("   - Ir a: https://console.cloudinary.com")
    print("   - Media Library > Search")
    print("   - Buscar: 'cotizaciones/nuevas/' o 'cotizaciones/antiguas/'")
    for pdf in pdfs_objetivo:
        print(f"   - Filtrar por: {pdf}")
    
    print("\n4. TEST DE CONEXIÓN CLOUDINARY:")
    print("   ```bash")
    print("   python test_cloudinary.py")
    print("   ```")
    
    print("\n5. LISTAR TODOS LOS PDFs EN CLOUDINARY:")
    print("   ```python")
    print("   from cloudinary_manager import CloudinaryManager")
    print("   cm = CloudinaryManager()")
    print("   stats = cm.obtener_estadisticas()")
    print("   print(f'Total PDFs: {stats.get(\"total_pdfs\", 0)}')")
    print("   todas_nuevas = cm.listar_pdfs('nuevas', max_resultados=1000)")
    print("   todas_antiguas = cm.listar_pdfs('antiguas', max_resultados=1000)")
    print("   ```")

def evaluar_riesgos_deploy():
    """Evalúa riesgos específicos del deploy"""
    print()
    print("=" * 80)
    print("EVALUACIÓN DE RIESGOS DE DEPLOY")
    print("=" * 80)
    
    print("RIESGOS IDENTIFICADOS:")
    print()
    
    print("1. RIESGO BAJO - PDFs en Cloudinary:")
    print("   - Cloudinary es servicio independiente")
    print("   - Deploy de Render NO afecta archivos en Cloudinary")
    print("   - URLs permanecen válidas después del deploy")
    print("   - Redundancia automática del servicio")
    
    print("\n2. RIESGO MEDIO - Variables de entorno:")
    print("   - Verificar que CLOUDINARY_* estén configuradas en Render")
    print("   - Deploy podría fallar si faltan variables")
    print("   - Verificar en Render Dashboard > Settings > Environment Variables")
    
    print("\n3. RIESGO BAJO - Archivos temporales:")
    print("   - Render elimina archivos temporales en cada deploy")
    print("   - PDFs locales se pierden (esperado)")
    print("   - Cloudinary mantiene los archivos permanentemente")
    
    print("\n4. RIESGO NULO - Procesos de limpieza:")
    print("   - No hay procesos automáticos de limpieza configurados")
    print("   - Cloudinary no elimina archivos automáticamente")
    print("   - Retención indefinida por defecto")
    
    print("\nRECOMENDACIONES PRE-DEPLOY:")
    print("[OK] Verificar variables CLOUDINARY_* en Render")
    print("[OK] Confirmar que PDFs críticos están en Cloudinary")
    print("[OK] Hacer backup local de PDFs importantes")
    print("[OK] Documentar URLs de PDFs críticos")
    print("[OK] Verificar que test_cloudinary.py pasa exitosamente")

if __name__ == "__main__":
    try:
        print("Iniciando verificación específica de PDFs...")
        resultados = verificar_pdfs_especificos()
        generar_comandos_verificacion()
        evaluar_riesgos_deploy()
        
    except KeyboardInterrupt:
        print("\nVerificación interrumpida por el usuario")
    except Exception as e:
        print(f"\nError en verificación: {e}")
        import traceback
        traceback.print_exc()