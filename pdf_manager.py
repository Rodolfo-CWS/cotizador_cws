"""
PDF Manager - Sistema híbrido de gestión de PDFs para cotizaciones CWS
Sistema primario: Cloudinary (25GB gratis)
Sistema fallback: Google Drive + almacenamiento local
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
        print("🚀 Inicializando PDF Manager híbrido...")
        self.cloudinary_manager = CloudinaryManager()
        self.cloudinary_disponible = self.cloudinary_manager.is_available()
        
        if self.cloudinary_disponible:
            print("✅ Sistema primario: Cloudinary activado (25GB gratis)")
        else:
            print("⚠️ Sistema primario: Cloudinary no disponible, usando fallbacks")
        
        # SISTEMAS FALLBACK: Google Drive + Local
        # Configurar rutas de PDFs locales (para fallback)
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
        
        # Inicializar cliente Google Drive (fallback)
        self.drive_client = GoogleDriveClient()
        
        # Colección para índice de PDFs
        self._inicializar_coleccion()
        
        print(f"📁 PDF Manager inicializado con arquitectura híbrida:")
        print(f"   Primario: Cloudinary ({'✅ Activo' if self.cloudinary_disponible else '❌ Inactivo'})")
        print(f"   Fallback Local: {self.base_pdf_path}")
        print(f"   Fallback Drive: {'✅ Configurado' if self.drive_client else '❌ No disponible'}")
    
    def _inicializar_coleccion(self):
        """Inicializa la colección de PDFs si MongoDB está disponible"""
        if not self.db_manager.modo_offline:
            self.pdf_collection = self.db_manager.db["pdf_index"]
            self._crear_indices_pdf()
            print("PDF Collection inicializada con MongoDB")
        else:
            self.pdf_collection = None
            print("PDF Manager en modo offline - colección no disponible")
    
    def _verificar_conexion_mongodb(self):
        """Verifica conexión MongoDB - no intenta reconectar para evitar errores"""
        # Simplemente verificar el estado actual
        if self.db_manager.modo_offline:
            print("MongoDB en modo offline - usando búsqueda offline")
            return False
        else:
            # Verificar que tengamos colección inicializada
            if not hasattr(self, 'pdf_collection') or self.pdf_collection is None:
                self._inicializar_coleccion()
            return True
    
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
                print(f"⚠️ Error creando README: {readme_error}")
                
        except Exception as e:
            print(f"[ERROR] Error creando estructura de carpetas: {e}")
            print(f"   Ruta base: {self.base_pdf_path}")
            print(f"   Error tipo: {type(e).__name__}")
            print(f"   Verificar permisos en la ruta")
    
    def _crear_indices_pdf(self):
        """Crea índices para optimizar búsquedas de PDFs"""
        try:
            # Índice por número de cotización
            self.pdf_collection.create_index("numero_cotizacion", unique=True)
            # Índice por cliente
            self.pdf_collection.create_index("cliente")
            # Índice por tipo (nueva/antigua)
            self.pdf_collection.create_index("tipo")
            # Índice por fecha
            self.pdf_collection.create_index("fecha")
            # Índice de texto para búsqueda
            self.pdf_collection.create_index([
                ("numero_cotizacion", "text"),
                ("cliente", "text"),
                ("vendedor", "text"),
                ("proyecto", "text")
            ])
        except Exception as e:
            print(f"Advertencia: Error creando índices PDF: {e}")
    
    def almacenar_pdf_nuevo(self, pdf_content: bytes, cotizacion_data: Dict) -> Dict:
        """
        Almacena un PDF usando sistema híbrido: Cloudinary (primario) + Fallbacks
        
        Estrategia:
        1. Cloudinary (primario) - 25GB gratis
        2. Google Drive (fallback) - si Cloudinary falla
        3. Local (emergencia) - siempre como respaldo
        
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
            
            print(f"🚀 [ALMACENAR_PDF_HIBRIDO] Número de cotización: '{numero_cotizacion}'")
            print(f"📊 [ALMACENAR_PDF_HIBRIDO] Tamaño PDF: {len(pdf_content)} bytes")
            
            # Generar nombre de archivo seguro
            nombre_archivo = self._generar_nombre_archivo(numero_cotizacion)
            
            # ===== PASO 1: CLOUDINARY (SISTEMA PRIMARIO) =====
            cloudinary_result = {"success": False, "error": "No intentado"}
            
            if self.cloudinary_disponible:
                print("🎯 [CLOUDINARY] Intentando subir a sistema primario...")
                
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
                        print(f"✅ [CLOUDINARY] PDF subido exitosamente!")
                        print(f"   URL: {cloudinary_result.get('url', 'N/A')}")
                        print(f"   Tamaño: {cloudinary_result.get('bytes', 0)} bytes")
                        cloudinary_result["success"] = True
                    else:
                        print(f"❌ [CLOUDINARY] Error: {cloudinary_result.get('error', 'Desconocido')}")
                        
                except Exception as e:
                    print(f"❌ [CLOUDINARY] Excepción: {e}")
                    cloudinary_result = {"success": False, "error": str(e)}
                finally:
                    # Limpiar archivo temporal
                    if temp_file and os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
            else:
                print("⚠️ [CLOUDINARY] Sistema primario no disponible, usando fallbacks")
                cloudinary_result = {"success": False, "error": "Cloudinary no configurado"}
            
            # ===== PASO 2: LOCAL (RESPALDO SIEMPRE) =====
            print("💾 [LOCAL] Guardando respaldo local...")
            ruta_completa = self.nuevas_path / nombre_archivo
            ruta_completa.write_bytes(pdf_content)
            local_result = {
                "success": True,
                "ruta": str(ruta_completa.absolute()),
                "tamaño": len(pdf_content)
            }
            print(f"✅ [LOCAL] Respaldo guardado: {ruta_completa}")
            
            # ===== PASO 3: GOOGLE DRIVE (FALLBACK) =====
            google_drive_result = {"success": False, "error": "No intentado"}
            
            # Solo intentar Google Drive si Cloudinary falló
            if not cloudinary_result.get("success", False) and self.drive_client and self.drive_client.is_available():
                print("🔄 [GOOGLE_DRIVE] Cloudinary falló, intentando fallback...")
                
                try:
                    # Preparar metadata del archivo para Google Drive
                    file_metadata = {
                        'name': nombre_archivo,
                        'parents': [self.drive_client.folder_nuevas]
                    }
                    
                    from googleapiclient.http import MediaIoBaseUpload
                    import io
                    
                    # Crear media upload desde el contenido binario
                    media_body = MediaIoBaseUpload(
                        io.BytesIO(pdf_content),
                        mimetype='application/pdf',
                        resumable=True
                    )
                    
                    # Subir archivo a Google Drive
                    uploaded_file = self.drive_client.service.files().create(
                        body=file_metadata,
                        media_body=media_body,
                        fields='id,name,size,createdTime,parents'
                    ).execute()
                    
                    google_drive_result = {
                        "success": True,
                        "file_id": uploaded_file.get('id'),
                        "nombre": uploaded_file.get('name'),
                        "tamaño_drive": uploaded_file.get('size'),
                        "fecha_subida": uploaded_file.get('createdTime'),
                        "carpeta_id": self.drive_client.folder_nuevas
                    }
                    
                    print(f"✅ [GOOGLE_DRIVE] Fallback exitoso!")
                    
                except Exception as drive_error:
                    print(f"❌ [GOOGLE_DRIVE] Error en fallback: {drive_error}")
                    google_drive_result = {
                        "success": False,
                        "error": str(drive_error),
                        "error_type": type(drive_error).__name__
                    }
            
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
            
            if not self.db_manager.modo_offline:
                try:
                    self.pdf_collection.replace_one(
                        {"numero_cotizacion": numero_cotizacion},
                        registro_pdf,
                        upsert=True
                    )
                    print("✅ [MONGODB] Índice actualizado")
                except Exception as e:
                    print(f"⚠️ [MONGODB] Error actualizando índice: {e}")
            
            # ===== RESULTADO FINAL =====
            # Determinar si la operación fue exitosa
            almacenamiento_exitoso = (
                cloudinary_result.get("success", False) or 
                google_drive_result.get("success", False) or
                local_result.get("success", False)
            )
            
            # Determinar mensaje de estado
            if cloudinary_result.get("success", False):
                estado = "✅ Cloudinary (primario)"
            elif google_drive_result.get("success", False):
                estado = "🔄 Google Drive (fallback)"
            elif local_result.get("success", False):
                estado = "💾 Local (emergencia)"
            else:
                estado = "❌ Error en todos los sistemas"
            
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
            print(f"❌ [ALMACENAR_PDF_HIBRIDO] Error general: {e}")
            return {
                "success": False,
                "error": f"Error almacenando PDF: {str(e)}",
                "sistemas": {
                    "cloudinary": {"success": False, "error": "No procesado por error general"},
                    "google_drive": {"success": False, "error": "No procesado por error general"},
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
        Busca PDFs por término de búsqueda
        
        Args:
            query: Término de búsqueda
            page: Página de resultados
            per_page: Resultados por página
            
        Returns:
            Dict con resultados de la búsqueda
        """
        try:
            print(f"[BUSCAR PDFs] Iniciando búsqueda: '{query}'")
            print(f"[BUSCAR PDFs] Modo offline actual: {self.db_manager.modo_offline}")
            
            # Verificar y reinicializar conexión si es necesario
            if not self._verificar_conexion_mongodb():
                print(f"[BUSCAR PDFs] Usando búsqueda offline")
                return self._buscar_pdfs_offline(query, page, per_page)
            
            # Verificar que pdf_collection existe
            if self.pdf_collection is None:
                return self._buscar_pdfs_offline(query, page, per_page)
            
            # Búsqueda en MongoDB
            skip = (page - 1) * per_page
            
            # Filtro de búsqueda (buscar en múltiples campos)
            filtro = {
                "$or": [
                    {"numero_cotizacion": {"$regex": query, "$options": "i"}},
                    {"cliente": {"$regex": query, "$options": "i"}},
                    {"vendedor": {"$regex": query, "$options": "i"}},
                    {"proyecto": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Ejecutar búsqueda
            resultados = list(
                self.pdf_collection
                .find(filtro)
                .sort("timestamp", -1)
                .skip(skip)
                .limit(per_page)
            )
            
            # Contar total
            total = self.pdf_collection.count_documents(filtro)
            
            # Limpiar ObjectId para JSON
            for resultado in resultados:
                if '_id' in resultado:
                    resultado['_id'] = str(resultado['_id'])
            
            return {
                "resultados": resultados,
                "total": total,
                "pagina": page,
                "por_pagina": per_page,
                "total_paginas": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            print(f"[BUSCAR PDFs] ERROR en búsqueda principal: {e}")
            import traceback
            traceback.print_exc()
            # En caso de cualquier error, usar búsqueda offline
            return self._buscar_pdfs_offline(query, page, per_page)
    
    def _buscar_pdfs_offline(self, query: str, page: int, per_page: int) -> Dict:
        """Búsqueda de PDFs en modo offline (incluye Google Drive)"""
        print(f"Búsqueda de PDFs en modo offline: '{query}'")
        print(f"Ruta base configurada: {self.base_pdf_path}")
        print(f"Drive disponible: {self.drive_client.is_available()}")
        
        try:
            resultados = []
            
            # 1. Buscar en Google Drive (prioritario)
            if self.drive_client.is_available():
                print("Buscando PDFs en Google Drive...")
                try:
                    drive_pdfs = self.drive_client.buscar_pdfs(query)
                    print(f"PDFs encontrados en Google Drive: {len(drive_pdfs)}")
                except Exception as e:
                    print(f"Error buscando en Google Drive: {e}")
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
                        "tamaño": pdf.get('tamaño', '0')
                    })
            
            # 2. Buscar en carpetas locales (fallback)
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
            # 1. Buscar en Google Drive (prioritario)
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
            
            # Buscar en índice
            registro = self.pdf_collection.find_one({"numero_cotizacion": numero_cotizacion})
            
            if not registro:
                return {"encontrado": False, "mensaje": "PDF no encontrado"}
            
            # Verificar que el archivo existe físicamente
            ruta_completa = Path(registro["ruta_completa"])
            if not ruta_completa.exists():
                return {
                    "encontrado": False, 
                    "error": f"Archivo PDF no encontrado en: {ruta_completa}",
                    "registro": registro
                }
            
            # Limpiar ObjectId
            if '_id' in registro:
                registro['_id'] = str(registro['_id'])
            
            return {
                "encontrado": True,
                "registro": registro,
                "ruta_completa": str(ruta_completa),
                "existe_archivo": True
            }
            
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
            
            if not self.db_manager.modo_offline:
                self.pdf_collection.replace_one(
                    {"numero_cotizacion": numero_cotizacion},
                    registro_pdf,
                    upsert=True
                )
            
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
            
            # Obtener todos los registros
            registros = list(
                self.pdf_collection
                .find()
                .sort("timestamp", -1)
            )
            
            # Limpiar ObjectIds
            for registro in registros:
                if '_id' in registro:
                    registro['_id'] = str(registro['_id'])
            
            # Estadísticas
            total = len(registros)
            nuevos = sum(1 for r in registros if r.get('tipo') == 'nueva')
            antiguos = sum(1 for r in registros if r.get('tipo') == 'antigua')
            
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
            
            # Verificar registros en base de datos
            registros = list(self.pdf_collection.find())
            resultados["registros_verificados"] = len(registros)
            
            for registro in registros:
                ruta_completa = Path(registro.get("ruta_completa", ""))
                
                if ruta_completa.exists():
                    resultados["archivos_encontrados"] += 1
                else:
                    resultados["archivos_faltantes"].append({
                        "numero": registro.get("numero_cotizacion"),
                        "archivo": registro.get("nombre_archivo"),
                        "ruta": str(ruta_completa)
                    })
            
            return resultados
            
        except Exception as e:
            return {"error": f"Error verificando integridad: {str(e)}"}