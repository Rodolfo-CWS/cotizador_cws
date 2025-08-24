"""
PDF Manager - Sistema híbrido de gestión de PDFs para cotizaciones CWS
Sistema primario: Cloudinary (25GB gratis)  
Sistema respaldo: Almacenamiento local
Búsqueda: Google Drive (antiguas/) + Cloudinary + Local

Nota: Google Drive (nuevas/) eliminado para evitar problemas de cuotas
"""

import os
import json
import datetime
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Tuple
from google_drive_client import GoogleDriveClient
from cloudinary_manager import CloudinaryManager

class PDFManager:
    def __init__(self, database_manager, base_pdf_path: str = None):
        """
        Inicializa el gestor híbrido de PDFs
        Sistema primario: Cloudinary
        Sistema fallback: Google Drive + local
        
        Args:
            database_manager: Instancia de DatabaseManager
            base_pdf_path: Ruta base para almacenar PDFs localmente (fallback)
        """
        self.db_manager = database_manager
        
        # SISTEMA PRIMARIO: Cloudinary
        print("INIT: Inicializando PDF Manager hibrido...")
        self.cloudinary_manager = CloudinaryManager()
        self.cloudinary_disponible = self.cloudinary_manager.is_available()
        
        if self.cloudinary_disponible:
            print("OK: Sistema primario: Cloudinary activado (25GB gratis)")
        else:
            print("WARNING: Sistema primario: Cloudinary no disponible, usando fallbacks")
        
        # SISTEMA RESPALDO: Local storage
        # Configurar rutas de PDFs locales
        if base_pdf_path:
            self.base_pdf_path = Path(base_pdf_path)
        else:
            # Intentar detectar Google Drive automáticamente
            self.base_pdf_path = self._detectar_google_drive()
        
        # Crear estructura de carpetas local
        self.nuevas_path = self.base_pdf_path / "nuevas"
        self.antiguas_path = self.base_pdf_path / "antiguas"
        
        # Crear carpetas si no existen
        self._crear_estructura_carpetas()
        
        # Inicializar cliente Google Drive (solo para búsqueda en antiguas/)
        self.drive_client = GoogleDriveClient()
        
        # MongoDB eliminado - No hay colección de índices
        
        print(f"PDF: PDF Manager inicializado con arquitectura simplificada:")
        print(f"   Primario: Cloudinary ({'OK Activo' if self.cloudinary_disponible else 'ERROR Inactivo'})")
        print(f"   Respaldo Local: {self.base_pdf_path}")
        print(f"   Busqueda Drive (antiguas/): {'OK Configurado' if self.drive_client else 'ERROR No disponible'}")
    
    # MongoDB eliminado - Sistema híbrido usando solo Cloudinary + Google Drive + Local
    
    def _detectar_google_drive(self) -> Path:
        """Detecta automáticamente la ruta de Google Drive"""
        usuario = os.getenv('USERNAME') or os.getenv('USER')
        
        # Verificar si estamos en un entorno en la nube (Render, Heroku, etc.)
        es_nube = os.getenv('RENDER') or os.getenv('DYNO') or os.getenv('PORT')
        
        if es_nube:
            # En la nube, usar carpeta local temporal
            print("Entorno en la nube detectado - usando almacenamiento temporal")
            fallback = Path("./pdfs_cotizaciones")
            fallback.mkdir(parents=True, exist_ok=True)
            print(f"Usando ruta para nube: {fallback.absolute()}")
            return fallback
        
        # Rutas comunes de Google Drive en Windows
        rutas_posibles = [
            "G:/Mi unidad/CWS/CWS_Cotizaciones_PDF",  # Nueva ruta preferida
            f"C:/Users/{usuario}/Google Drive/CWS_Cotizaciones_PDF",
            f"C:/Users/{usuario}/GoogleDrive/CWS_Cotizaciones_PDF", 
            "G:/Mi unidad/CWS_Cotizaciones_PDF",
            "G:/My Drive/CWS_Cotizaciones_PDF",
            # Fallback local si no hay Google Drive
            "./pdfs_cotizaciones"
        ]
        
        for ruta in rutas_posibles:
            path_obj = Path(ruta)
            try:
                # Intentar crear la carpeta para verificar permisos
                path_obj.mkdir(parents=True, exist_ok=True)
                print(f"Usando ruta de PDFs: {path_obj.absolute()}")
                return path_obj
            except:
                continue
        
        # Si nada funciona, usar carpeta local
        fallback = Path("./pdfs_cotizaciones")
        fallback.mkdir(parents=True, exist_ok=True)
        print(f"Usando ruta fallback: {fallback.absolute()}")
        return fallback
    
    def _crear_estructura_carpetas(self):
        """Crea la estructura de carpetas necesaria"""
        try:
            print(f"Creando estructura de carpetas en: {self.base_pdf_path}")
            
            # Verificar que la ruta base sea accesible
            if not self.base_pdf_path.exists():
                print(f"Creando ruta base: {self.base_pdf_path}")
                self.base_pdf_path.mkdir(parents=True, exist_ok=True)
            
            self.nuevas_path.mkdir(parents=True, exist_ok=True)
            self.antiguas_path.mkdir(parents=True, exist_ok=True)
            
            print(f"[OK] Carpetas creadas exitosamente:")
            print(f"   [DIR] Base: {self.base_pdf_path} (existe: {self.base_pdf_path.exists()})")
            print(f"   [DIR] Nuevas: {self.nuevas_path} (existe: {self.nuevas_path.exists()})")
            print(f"   [DIR] Antiguas: {self.antiguas_path} (existe: {self.antiguas_path.exists()})")
            
            # Crear archivo README en cada carpeta
            try:
                readme_nuevas = self.nuevas_path / "README.txt"
                if not readme_nuevas.exists():
                    readme_nuevas.write_text(
                        "Esta carpeta contiene PDFs generados automáticamente por el sistema CWS.\n"
                        "Estos PDFs tienen desglose completo disponible en la base de datos.\n"
                        f"Generado: {datetime.datetime.now()}"
                    )
                
                readme_antiguas = self.antiguas_path / "README.txt"
                if not readme_antiguas.exists():
                    readme_antiguas.write_text(
                        "Esta carpeta contiene PDFs históricos importados manualmente.\n"
                        "Estos PDFs solo están disponibles para visualización.\n"
                        f"Configurado: {datetime.datetime.now()}"
                    )
                print("[OK] Archivos README creados")
            except Exception as readme_error:
                print(f"WARNING: Error creando README: {readme_error}")
                
        except Exception as e:
            print(f"[ERROR] Error creando estructura de carpetas: {e}")
            print(f"   Ruta base: {self.base_pdf_path}")
            print(f"   Error tipo: {type(e).__name__}")
            print(f"   Verificar permisos en la ruta")
    
    # Método _crear_indices_pdf eliminado - MongoDB no se usa más
    
    def almacenar_pdf_nuevo(self, pdf_content: bytes, cotizacion_data: Dict) -> Dict:
        """
        Almacena un PDF usando sistema híbrido simplificado: Cloudinary (primario) + Local (respaldo)
        
        Estrategia simplificada:
        1. Cloudinary (primario) - 25GB gratis
        2. Local (emergencia) - siempre como respaldo
        
        Nota: Google Drive (nuevas/) eliminado para evitar problemas de cuotas
        
        Args:
            pdf_content: Contenido binario del PDF
            cotizacion_data: Datos de la cotización
            
        Returns:
            Dict con resultado de la operación híbrida
        """
        try:
            # Extraer información de la cotización
            numero_cotizacion = (
                cotizacion_data.get('numeroCotizacion') or 
                cotizacion_data.get('datosGenerales', {}).get('numeroCotizacion') or 
                'Sin_Numero'
            )
            datos_generales = cotizacion_data.get('datosGenerales', {})
            
            print(f"STORE: [ALMACENAR_PDF_HIBRIDO] Numero de cotizacion: '{numero_cotizacion}'")
            print(f"📊 [ALMACENAR_PDF_HIBRIDO] Tamaño PDF: {len(pdf_content)} bytes")
            
            # Generar nombre de archivo seguro
            nombre_archivo = self._generar_nombre_archivo(numero_cotizacion)
            
            # ===== PASO 1: CLOUDINARY (SISTEMA PRIMARIO) =====
            cloudinary_result = {"success": False, "error": "No intentado"}
            
            if self.cloudinary_disponible:
                print("TARGET: [CLOUDINARY] Intentando subir a sistema primario...")
                
                # Crear archivo temporal para Cloudinary
                import tempfile
                temp_file = None
                try:
                    # Crear archivo temporal
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                        temp_file.write(pdf_content)
                        temp_file_path = temp_file.name
                    
                    # Subir a Cloudinary
                    cloudinary_result = self.cloudinary_manager.subir_pdf(
                        temp_file_path,
                        numero_cotizacion,
                        es_nueva=True
                    )
                    
                    if cloudinary_result.get("success", False):
                        print(f"OK: [CLOUDINARY] PDF subido exitosamente!")
                        print(f"   URL: {cloudinary_result.get('url', 'N/A')}")
                        print(f"   Tamaño: {cloudinary_result.get('bytes', 0)} bytes")
                        cloudinary_result["success"] = True
                    else:
                        print(f"ERROR: [CLOUDINARY] Error: {cloudinary_result.get('error', 'Desconocido')}")
                        
                except Exception as e:
                    print(f"ERROR: [CLOUDINARY] Excepcion: {e}")
                    cloudinary_result = {"success": False, "error": str(e)}
                finally:
                    # Limpiar archivo temporal
                    if temp_file and os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
            else:
                print("WARNING: [CLOUDINARY] Sistema primario no disponible, usando fallbacks")
                cloudinary_result = {"success": False, "error": "Cloudinary no configurado"}
            
            # ===== PASO 2: LOCAL (RESPALDO SIEMPRE) =====
            print("LOCAL: [LOCAL] Guardando respaldo local...")
            ruta_completa = self.nuevas_path / nombre_archivo
            ruta_completa.write_bytes(pdf_content)
            local_result = {
                "success": True,
                "ruta": str(ruta_completa.absolute()),
                "tamaño": len(pdf_content)
            }
            print(f"OK: [LOCAL] Respaldo guardado: {ruta_completa}")
            
            # ===== ELIMINADO: GOOGLE DRIVE (NUEVAS/) FALLBACK =====
            # Google Drive (nuevas/) eliminado para evitar problemas de cuotas
            # Solo se mantiene Google Drive (antiguas/) para búsqueda de PDFs históricos
            google_drive_result = {"success": False, "error": "Google Drive (nuevas/) deshabilitado"}
            
            # ===== PASO 4: REGISTRAR EN MONGODB (ÍNDICE) =====
            # Registrar en índice independientemente del resultado de almacenamiento
            registro_pdf = {
                "nombre_archivo": nombre_archivo,
                "numero_cotizacion": numero_cotizacion,
                "cliente": datos_generales.get('cliente', ''),
                "vendedor": datos_generales.get('vendedor', ''),
                "proyecto": datos_generales.get('proyecto', ''),
                "fecha": datetime.datetime.now().strftime('%Y-%m-%d'),
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                "tipo": "nueva",
                "tiene_desglose": True,
                "ruta_archivo": f"nuevas/{nombre_archivo}",
                "ruta_completa": str(ruta_completa.absolute()),
                "tamaño_bytes": len(pdf_content),
                # Información de almacenamiento híbrido
                "cloudinary": cloudinary_result,
                "google_drive": google_drive_result,
                "local": local_result
            }
            
            # MongoDB eliminado - Sistema híbrido sin dependencia de índices MongoDB
            print("OK: [HÍBRIDO] Almacenamiento completado sin dependencia de MongoDB")
            
            # ===== RESULTADO FINAL =====
            # Determinar si la operación fue exitosa (sistema simplificado)
            almacenamiento_exitoso = (
                cloudinary_result.get("success", False) or 
                local_result.get("success", False)
            )
            
            # Determinar mensaje de estado
            if cloudinary_result.get("success", False):
                estado = "OK Cloudinary (primario)"
            elif local_result.get("success", False):
                estado = "LOCAL Local (respaldo)"
            else:
                estado = "ERROR Error en todos los sistemas"
            
            resultado_final = {
                "success": almacenamiento_exitoso,
                "mensaje": f"PDF almacenado - {estado}: {nombre_archivo}",
                "estado": estado,
                "nombre_archivo": nombre_archivo,
                "tamaño": len(pdf_content),
                "ruta_local": str(ruta_completa),
                # Detalles de cada sistema
                "sistemas": {
                    "cloudinary": cloudinary_result,
                    "google_drive": google_drive_result, 
                    "local": local_result
                }
            }
            
            print(f"🎉 [RESULTADO_FINAL] {estado}")
            return resultado_final
            
        except Exception as e:
            print(f"ERROR: [ALMACENAR_PDF_HIBRIDO] Error general: {e}")
            return {
                "success": False,
                "error": f"Error almacenando PDF: {str(e)}",
                "sistemas": {
                    "cloudinary": {"success": False, "error": "No procesado por error general"},
                    "local": {"success": False, "error": "No procesado por error general"}
                }
            }
    
    def _generar_nombre_archivo(self, numero_cotizacion: str) -> str:
        """Genera un nombre de archivo seguro para el PDF usando EXACTAMENTE el nombre de la cotización"""
        print(f"[PDF_NAME] Generando nombre para cotización: '{numero_cotizacion}'")
        
        # Verificar que el número de cotización no esté vacío
        if not numero_cotizacion or numero_cotizacion.strip() == "":
            print("[PDF_NAME] ERROR: Número de cotización vacío - usando fallback temporal")
            nombre_limpio = f"SIN_NUMERO_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            # IMPORTANTE: NO agregar prefijo "Cotización_" - usar EXACTAMENTE el nombre del formulario
            nombre_limpio = numero_cotizacion.strip()
            
            # Solo limpiar caracteres que son problemáticos para nombres de archivo
            # Mantener la estructura original lo más intacta posible
            nombre_limpio = nombre_limpio.replace('/', '-').replace('\\', '-')
            nombre_limpio = nombre_limpio.replace(':', '-').replace('*', '')
            nombre_limpio = nombre_limpio.replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '-')
            
            # NO reemplazar espacios con guiones bajos - mantener el formato original
            # Solo reemplazar espacios si causan problemas específicos
            # nombre_limpio = nombre_limpio.replace(' ', '_')  # REMOVIDO
            
            print(f"[PDF_NAME] Nombre limpiado (sin prefijo): '{nombre_limpio}'")
        
        # Verificar que el nombre final no esté vacío después de la limpieza
        if not nombre_limpio or len(nombre_limpio.replace('-', '').replace(' ', '')) == 0:
            print("[PDF_NAME] ERROR: Nombre vacío después de limpieza - usando fallback")
            nombre_limpio = f"COTIZACION_ERROR_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # IMPORTANTE: El nombre final es EXACTAMENTE el nombre de la cotización + .pdf
        nombre_final = f"{nombre_limpio}.pdf"
        print(f"[PDF_NAME] Nombre final generado (sin prefijo 'Cotización_'): '{nombre_final}'")
        
        return nombre_final
    
    def buscar_pdfs(self, query: str, page: int = 1, per_page: int = 20) -> Dict:
        """
        Busca PDFs por término de búsqueda en múltiples fuentes
        
        Args:
            query: Término de búsqueda
            page: Página de resultados
            per_page: Resultados por página
            
        Returns:
            Dict con resultados de la búsqueda
        """
        try:
            print(f"[BUSCAR PDFs] Iniciando búsqueda híbrida: '{query}'")
            return self._buscar_pdfs_offline(query, page, per_page)
            
        except Exception as e:
            print(f"[BUSCAR PDFs] ERROR en búsqueda: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error en búsqueda de PDFs: {e}", "resultados": [], "total": 0}
    
    def _buscar_pdfs_offline(self, query: str, page: int, per_page: int) -> Dict:
        """Búsqueda de PDFs híbrida (Cloudinary, base de datos, Google Drive y archivos locales)"""
        print(f"[BUSCAR HÍBRIDA] Query: '{query}' - Cloudinary disponible: {self.cloudinary_disponible}")
        print(f"[BUSCAR HÍBRIDA] Drive disponible: {self.drive_client.is_available()}")
        
        try:
            resultados = []
            
            # 1. BUSCAR EN CLOUDINARY (PRIORITARIO)
            if self.cloudinary_disponible:
                print("[BUSCAR HÍBRIDA] Buscando en Cloudinary...")
                try:
                    cloudinary_pdfs = self.cloudinary_manager.buscar_pdfs(query, 1000)
                    print(f"[CLOUDINARY] PDFs encontrados: {len(cloudinary_pdfs)}")
                    resultados.extend(cloudinary_pdfs)
                except Exception as e:
                    print(f"[CLOUDINARY] Error en búsqueda: {e}")
            
            # 2. Buscar en base de datos de cotizaciones
            print("[BUSCAR HÍBRIDA] Buscando en base de datos de cotizaciones...")
            try:
                cotizaciones_result = self.db_manager.buscar_cotizaciones(query, 1, 1000)  # Obtener todas
                cotizaciones = cotizaciones_result.get('resultados', [])
                print(f"[BD] Cotizaciones encontradas: {len(cotizaciones)}")
                
                for cot in cotizaciones:
                    datos_gen = cot.get('datosGenerales', {})
                    resultados.append({
                        "numero_cotizacion": cot.get('numeroCotizacion', 'N/A'),
                        "cliente": datos_gen.get('cliente', 'N/A'),
                        "vendedor": datos_gen.get('vendedor', 'N/A'),
                        "proyecto": datos_gen.get('proyecto', 'N/A'),
                        "fecha_creacion": cot.get('fechaCreacion', 'N/A'),
                        "ruta_completa": f"cotizacion://{cot.get('_id')}",
                        "tipo": "cotizacion",
                        "tiene_desglose": True,
                        "revision": cot.get('revision', 1),
                        "_id": cot.get('_id'),
                        "fuente": "supabase" if not self.db_manager.modo_offline else "json_local"
                    })
            except Exception as e:
                print(f"[BD] Error buscando en base de datos: {e}")
                pass
            
            # 3. Buscar en Google Drive (históricos)
            if self.drive_client.is_available():
                print("[BUSCAR HÍBRIDA] Buscando PDFs históricos en Google Drive...")
                try:
                    drive_pdfs = self.drive_client.buscar_pdfs(query)
                    print(f"[GOOGLE DRIVE] PDFs encontrados: {len(drive_pdfs)}")
                except Exception as e:
                    print(f"[GOOGLE DRIVE] Error buscando: {e}")
                    drive_pdfs = []
                
                for pdf in drive_pdfs:
                    resultados.append({
                        "numero_cotizacion": pdf['numero_cotizacion'],
                        "cliente": "Google Drive",
                        "fecha_creacion": pdf.get('fecha_modificacion', 'N/A'),
                        "ruta_completa": f"gdrive://{pdf['id']}",
                        "tipo": "google_drive",
                        "tiene_desglose": True,
                        "drive_id": pdf['id'],
                        "tamaño": pdf.get('tamaño', '0'),
                        "fuente": "google_drive"
                    })
            
            # 3. Buscar en carpetas locales (fallback)
            print(f"Buscando PDFs locales en: {self.nuevas_path}")
            print(f"Carpeta nuevas existe: {self.nuevas_path.exists()}")
            
            # Buscar en carpeta de PDFs nuevos
            if self.nuevas_path.exists():
                archivos_nuevos = list(self.nuevas_path.glob("*.pdf"))
                print(f"Archivos PDF en nuevas: {len(archivos_nuevos)}")
                for pdf_file in archivos_nuevos:
                    nombre = pdf_file.stem
                    print(f"Revisando archivo nuevo: {nombre}")
                    if not query or query.lower() in nombre.lower():
                        print(f"Coincidencia encontrada en nuevos: {nombre}")
                        resultados.append({
                            "numero_cotizacion": nombre,
                            "cliente": "Local (nuevos)",
                            "fecha_creacion": "N/A",
                            "ruta_completa": str(pdf_file),
                            "tipo": "nuevo",
                            "tiene_desglose": False
                        })
            else:
                print(f"Carpeta nuevas no existe: {self.nuevas_path}")
            
            # Buscar en carpeta de PDFs antiguos  
            print(f"Carpeta antiguas existe: {self.antiguas_path.exists()}")
            if self.antiguas_path.exists():
                archivos_antiguos = list(self.antiguas_path.glob("*.pdf"))
                print(f"Archivos PDF en antiguas: {len(archivos_antiguos)}")
                for pdf_file in archivos_antiguos:
                    nombre = pdf_file.stem
                    print(f"Revisando archivo antiguo: {nombre}")
                    if not query or query.lower() in nombre.lower():
                        print(f"Coincidencia encontrada en antiguos: {nombre}")
                        resultados.append({
                            "numero_cotizacion": nombre,
                            "cliente": "Local (históricos)",
                            "fecha_creacion": "N/A", 
                            "ruta_completa": str(pdf_file),
                            "tipo": "historico",
                            "tiene_desglose": False
                        })
            else:
                print(f"Carpeta antiguas no existe: {self.antiguas_path}")
            
            # Paginar resultados
            start = (page - 1) * per_page
            end = start + per_page
            resultados_paginados = resultados[start:end]
            
            print(f"Encontrados {len(resultados)} PDFs offline, mostrando {len(resultados_paginados)}")
            
            return {
                "resultados": resultados_paginados,
                "total": len(resultados),
                "pagina": page,
                "por_pagina": per_page,
                "total_paginas": (len(resultados) + per_page - 1) // per_page,
                "modo": "offline"
            }
            
        except Exception as e:
            print(f"Error en búsqueda offline: {e}")
            return {
                "resultados": [],
                "total": 0,
                "pagina": page,
                "por_pagina": per_page,
                "total_paginas": 0,
                "modo": "offline",
                "error": f"Error en búsqueda offline: {str(e)}"
            }
    
    def _obtener_pdf_offline(self, numero_cotizacion: str) -> Dict:
        """Obtiene información de un PDF en modo offline (incluye Google Drive)"""
        print(f"Buscando PDF offline: '{numero_cotizacion}'")
        print(f"Ruta base configurada: {self.base_pdf_path}")
        
        # Variaciones del nombre a buscar (incluyendo prefijo "Cotizacion_")
        variaciones_base = [
            numero_cotizacion,
            numero_cotizacion.replace(' ', '-'),  # Espacios -> guiones
            numero_cotizacion.replace('-', ' '),  # Guiones -> espacios
            numero_cotizacion.upper(),
            numero_cotizacion.lower()
        ]
        
        # Crear variaciones con y sin prefijo "Cotizacion_"
        variaciones_nombre = []
        for variacion in variaciones_base:
            variaciones_nombre.append(variacion)  # Sin prefijo
            variaciones_nombre.append(f"Cotizacion_{variacion}")  # Con prefijo
        
        # Eliminar duplicados
        variaciones_nombre = list(set(variaciones_nombre))
        print(f"Variaciones a buscar: {variaciones_nombre}")
        
        try:
            # 1. BUSCAR EN CLOUDINARY (PRIORITARIO)
            if self.cloudinary_disponible:
                print("[OBTENER PDF] Buscando en Cloudinary...")
                try:
                    # Buscar en Cloudinary usando las variaciones
                    for variacion in variaciones_nombre:
                        # Intentar encontrar el PDF con esta variación
                        cloudinary_pdfs = self.cloudinary_manager.buscar_pdfs(variacion, 20)
                        
                        for pdf_info in cloudinary_pdfs:
                            pdf_public_id = pdf_info.get('public_id', '')
                            pdf_numero = pdf_info.get('numero_cotizacion', '')
                            
                            # Verificar coincidencia
                            if (variacion.lower() in pdf_public_id.lower() or 
                                variacion.lower() in pdf_numero.lower()):
                                
                                print(f"[CLOUDINARY] OK PDF encontrado: {pdf_public_id}")
                                return {
                                    "encontrado": True,
                                    "registro": pdf_info,
                                    "ruta_completa": pdf_info.get('ruta_completa', ''),
                                    "existe_archivo": True,
                                    "tipo": "cloudinary",
                                    "url_directa": pdf_info.get('ruta_completa', ''),
                                    "public_id": pdf_public_id
                                }
                    
                    print(f"[CLOUDINARY] PDF no encontrado en Cloudinary para: {numero_cotizacion}")
                
                except Exception as e:
                    print(f"[CLOUDINARY] Error buscando: {e}")
            
            # 2. Buscar en Google Drive (secundario)
            if self.drive_client.is_available():
                print("Buscando en Google Drive...")
                try:
                    drive_pdfs = self.drive_client.buscar_pdfs(numero_cotizacion)
                    print(f"PDFs encontrados en Drive para '{numero_cotizacion}': {len(drive_pdfs)}")
                except Exception as e:
                    print(f"Error buscando en Google Drive: {e}")
                    drive_pdfs = []
                
                # Buscar coincidencia exacta con variaciones
                print(f"   Comparando variaciones con {len(drive_pdfs)} archivos:")
                for pdf in drive_pdfs:
                    pdf_nombre = pdf['numero_cotizacion']
                    for variacion in variaciones_nombre:
                        coincide = pdf_nombre == variacion
                        if coincide:
                            print(f"     [MATCH] MATCH: '{pdf_nombre}' == '{variacion}'")
                            return {
                                "encontrado": True,
                                "ruta_completa": f"gdrive://{pdf['id']}",
                                "tipo_fuente": "google_drive",
                            "drive_id": pdf['id'],
                            "registro": {
                                "numero_cotizacion": numero_cotizacion,
                                "cliente": "Google Drive",
                                "fecha_creacion": pdf.get('fecha_modificacion', 'N/A'),
                                "tipo": "google_drive",
                                "tiene_desglose": True
                            }
                        }
            
            # 2. Buscar en carpetas locales (fallback)
            print(f"Buscando archivos locales...")
            print(f"Carpeta nuevas: {self.nuevas_path} (existe: {self.nuevas_path.exists()})")
            print(f"Carpeta antiguas: {self.antiguas_path} (existe: {self.antiguas_path.exists()})")
            
            # Buscar en carpeta de PDFs nuevos con todas las variaciones
            for variacion in variaciones_nombre:
                pdf_nuevos = self.nuevas_path / f"{variacion}.pdf"
                print(f"Buscando archivo nuevo: {pdf_nuevos}")
                if pdf_nuevos.exists():
                    print(f"[FOUND] Encontrado en nuevos: {variacion}")
                    return {
                        "encontrado": True,
                        "ruta_completa": str(pdf_nuevos),
                        "tipo_fuente": "local",
                        "registro": {
                            "numero_cotizacion": variacion,
                            "cliente": "Local (nuevos)",
                            "fecha_creacion": "N/A",
                            "tipo": "nuevo",
                            "tiene_desglose": False
                        }
                    }
            
            # Buscar en carpeta de PDFs antiguos con todas las variaciones
            for variacion in variaciones_nombre:
                pdf_antiguos = self.antiguas_path / f"{variacion}.pdf"
                print(f"Buscando archivo antiguo: {pdf_antiguos}")
                if pdf_antiguos.exists():
                    print(f"[FOUND] Encontrado en antiguos: {variacion}")
                    return {
                        "encontrado": True,
                        "ruta_completa": str(pdf_antiguos),
                        "tipo_fuente": "local",
                        "registro": {
                            "numero_cotizacion": variacion,
                            "cliente": "Local (históricos)",
                            "fecha_creacion": "N/A", 
                            "tipo": "historico",
                            "tiene_desglose": False
                        }
                    }
            
            # No encontrado en ningún lado
            return {
                "encontrado": False,
                "error": f"PDF '{numero_cotizacion}' no encontrado en Google Drive ni localmente"
            }
            
        except Exception as e:
            return {
                "encontrado": False,
                "error": f"Error buscando PDF offline: {str(e)}"
            }
    
    def obtener_pdf(self, numero_cotizacion: str) -> Dict:
        """
        Obtiene información de un PDF específico
        
        Args:
            numero_cotizacion: Número de cotización a buscar
            
        Returns:
            Dict con información del PDF
        """
        try:
            if self.db_manager.modo_offline:
                # Buscar PDF físicamente en las carpetas
                return self._obtener_pdf_offline(numero_cotizacion)
            
            # MongoDB eliminado - Búsqueda directa en Cloudinary y sistema híbrido
            registro = None  # Ya no usamos índice MongoDB
            
            # MongoDB eliminado - Usar búsqueda directa offline
            return self._obtener_pdf_offline(numero_cotizacion)
            
        except Exception as e:
            return {"error": f"Error obteniendo PDF: {str(e)}"}
    
    def importar_pdf_antiguo(self, ruta_pdf: str, metadata: Dict) -> Dict:
        """
        Importa un PDF antiguo al sistema
        
        Args:
            ruta_pdf: Ruta del PDF a importar
            metadata: Metadatos del PDF (numero, cliente, etc.)
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            origen = Path(ruta_pdf)
            if not origen.exists():
                return {"success": False, "error": f"Archivo no encontrado: {ruta_pdf}"}
            
            # Generar nombre y destino
            numero_cotizacion = metadata.get('numero_cotizacion', origen.stem)
            nombre_archivo = self._generar_nombre_archivo(numero_cotizacion)
            destino = self.antiguas_path / nombre_archivo
            
            # Copiar archivo
            shutil.copy2(origen, destino)
            
            # Registrar en índice
            registro_pdf = {
                "nombre_archivo": nombre_archivo,
                "numero_cotizacion": numero_cotizacion,
                "cliente": metadata.get('cliente', ''),
                "vendedor": metadata.get('vendedor', ''),
                "proyecto": metadata.get('proyecto', ''),
                "fecha": metadata.get('fecha', datetime.datetime.now().strftime('%Y-%m-%d')),
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                "tipo": "antigua",
                "tiene_desglose": False,
                "ruta_archivo": f"antiguas/{nombre_archivo}",
                "ruta_completa": str(destino.absolute()),
                "tamaño_bytes": destino.stat().st_size,
                "importado_desde": str(origen.absolute()),
                "fecha_importacion": datetime.datetime.now().isoformat()
            }
            
            # MongoDB eliminado - No se actualiza índice automáticamente
            
            return {
                "success": True,
                "mensaje": f"PDF antiguo importado: {nombre_archivo}",
                "destino": str(destino)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error importando PDF: {str(e)}"
            }
    
    def listar_todos_pdfs(self) -> Dict:
        """Lista todos los PDFs disponibles"""
        try:
            if self.db_manager.modo_offline:
                return {"error": "No disponible en modo offline"}
            
            # MongoDB eliminado - Obtener estadísticas de fuentes directas
            registros = []
            
            # Estadísticas desde fuentes híbridas
            total = 0
            nuevos = 0
            antiguos = 0
            
            # Obtener estadísticas de Cloudinary
            if self.cloudinary_disponible:
                try:
                    cloudinary_stats = self.cloudinary_manager.obtener_estadisticas()
                    if not cloudinary_stats.get("error"):
                        total += cloudinary_stats.get("total_archivos", 0)
                        nuevos += cloudinary_stats.get("archivos_nuevas", 0)
                        antiguos += cloudinary_stats.get("archivos_antiguas", 0)
                except Exception as e:
                    print(f"[STATS] Error obteniendo estadísticas Cloudinary: {e}")
            
            return {
                "registros": registros,
                "estadisticas": {
                    "total": total,
                    "nuevos": nuevos,
                    "antiguos": antiguos
                }
            }
            
        except Exception as e:
            return {"error": f"Error listando PDFs: {str(e)}"}
    
    def verificar_integridad(self) -> Dict:
        """Verifica la integridad del sistema de PDFs"""
        try:
            if self.db_manager.modo_offline:
                return {"error": "No disponible en modo offline"}
            
            resultados = {
                "registros_verificados": 0,
                "archivos_encontrados": 0,
                "archivos_faltantes": [],
                "registros_huerfanos": [],
                "errores": []
            }
            
            # MongoDB eliminado - Verificación directa en sistemas híbridos
            resultados["registros_verificados"] = 0  # MongoDB no se usa
            
            # Verificar archivos en Cloudinary
            if self.cloudinary_disponible:
                try:
                    cloudinary_pdfs = self.cloudinary_manager.listar_pdfs(max_resultados=1000)
                    if not cloudinary_pdfs.get("error"):
                        archivos_cloudinary = cloudinary_pdfs.get("archivos", [])
                        resultados["archivos_encontrados"] += len(archivos_cloudinary)
                        resultados["registros_verificados"] += len(archivos_cloudinary)
                except Exception as e:
                    print(f"[VERIFICAR] Error verificando Cloudinary: {e}")
            
            # Verificar archivos locales
            if self.nuevas_path.exists():
                archivos_locales = list(self.nuevas_path.glob("*.pdf"))
                resultados["archivos_encontrados"] += len(archivos_locales)
            
            return resultados
            
        except Exception as e:
            return {"error": f"Error verificando integridad: {str(e)}"}