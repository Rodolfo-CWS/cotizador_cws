"""
Cloudinary Manager - Sistema de almacenamiento de PDFs en Cloudinary
Reemplaza Google Drive con almacenamiento gratuito de 25GB
"""

import os
import json
import datetime
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class CloudinaryManager:
    def __init__(self):
        """
        Inicializa el cliente de Cloudinary para almacenamiento de PDFs
        """
        self.cloudinary_available = False
        self.folder_nuevas = "cotizaciones/nuevas"
        self.folder_antiguas = "cotizaciones/antiguas"
        self.max_retries = 3
        self.retry_delay = 2  # segundos 
        
        try:
            import cloudinary
            import cloudinary.uploader
            import cloudinary.utils
            import cloudinary.api
            
            # Configurar Cloudinary con variables de entorno
            cloudinary.config(
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                api_key=os.getenv('CLOUDINARY_API_KEY'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET'),
                secure=True
            )
            
            # Verificar configuración
            if not all([
                os.getenv('CLOUDINARY_CLOUD_NAME'),
                os.getenv('CLOUDINARY_API_KEY'), 
                os.getenv('CLOUDINARY_API_SECRET')
            ]):
                raise Exception("Variables de entorno de Cloudinary no configuradas")
            
            self.cloudinary = cloudinary
            self.cloudinary_available = True
            print("OK: Cloudinary configurado correctamente")
            print(f"   Cloud: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
            print(f"   Carpeta nuevas: {self.folder_nuevas}")
            print(f"   Carpeta antiguas: {self.folder_antiguas}")
            
        except ImportError:
            print("ERROR: Cloudinary no esta instalado: pip install cloudinary")
        except Exception as e:
            print(f"ERROR configurando Cloudinary: {e}")
            print("   Verifica las variables de entorno:")
            print("   - CLOUDINARY_CLOUD_NAME")
            print("   - CLOUDINARY_API_KEY") 
            print("   - CLOUDINARY_API_SECRET")

    def is_available(self) -> bool:
        """Verifica si Cloudinary está disponible y configurado"""
        return self.cloudinary_available
    
    def _retry_operation(self, operation_func, *args, **kwargs):
        """
        Ejecuta una operación con reintentos automáticos
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = operation_func(*args, **kwargs)
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Solo reintentar en ciertos errores
                if any(keyword in error_str for keyword in ['timeout', 'connection', 'network', 'temporary']):
                    print(f"RETRY: Intento {attempt + 1}/{self.max_retries} fallo: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                else:
                    # Error no recuperable, no reintentar
                    break
        
        # Si llegamos aquí, todos los intentos fallaron
        raise last_error

    def subir_pdf(self, archivo_local: str, numero_cotizacion: str, es_nueva: bool = True) -> dict:
        """
        Sube un PDF a Cloudinary con reintentos automáticos y manejo robusto de errores
        
        Args:
            archivo_local: Ruta del archivo local a subir
            numero_cotizacion: Número de cotización (ej: CLIENTE-CWS-XX-001-R1-PROYECTO)
            es_nueva: True para carpeta 'nuevas', False para 'antiguas'
            
        Returns:
            Dict con información del archivo subido o error detallado
        """
        if not self.cloudinary_available:
            print("CLOUDINARY: Servicio no disponible - usando fallback")
            return {
                "error": "Cloudinary no disponible", 
                "fallback": True,
                "tipo_error": "servicio_no_disponible"
            }
        
        # Validaciones previas
        if not os.path.exists(archivo_local):
            print(f"CLOUDINARY: Archivo no existe: {archivo_local}")
            return {
                "error": f"Archivo no existe: {archivo_local}",
                "fallback": True,
                "tipo_error": "archivo_no_existe"
            }
        
        try:
            # Determinar carpeta de destino
            folder = self.folder_nuevas if es_nueva else self.folder_antiguas
            
            # Crear nombre público único
            public_id = f"{folder}/{numero_cotizacion}"
            
            print(f"CLOUDINARY: [INICIO] Subiendo PDF: {public_id}")
            print(f"CLOUDINARY: Archivo local: {archivo_local} (tamaño: {os.path.getsize(archivo_local)} bytes)")
            
            # Función interna para la subida (para usar con retry)
            def _upload_operation():
                return self.cloudinary.uploader.upload(
                    archivo_local,
                    public_id=public_id,
                    resource_type="raw",
                    access_mode="public",  # Asegurar acceso público
                    overwrite=True,
                    invalidate=True,
                    tags=["cotizacion", "pdf", "cws"],
                    context=f"numero={numero_cotizacion}|fecha={datetime.datetime.now().isoformat()}"
                )
            
            # Ejecutar con reintentos
            resultado = self._retry_operation(_upload_operation)
            
            # Extraer información relevante
            info_archivo = {
                "url": resultado['secure_url'],  # Usar URL directa de Cloudinary
                "public_id": resultado['public_id'],
                "bytes": resultado['bytes'],
                "formato": resultado.get('format', 'pdf'),  # Default to 'pdf' for raw files
                "fecha_subida": resultado['created_at'],
                "version": resultado['version'],
                "etag": resultado.get('etag', ''),
                "folder": folder,
                "numero_cotizacion": numero_cotizacion
            }
            
            print(f"OK: PDF subido exitosamente:")
            print(f"   URL: {info_archivo['url']}")
            print(f"   Tamano: {info_archivo['bytes']} bytes")
            
            return info_archivo
            
        except Exception as e:
            error_msg = f"Error subiendo PDF a Cloudinary: {e}"
            error_tipo = type(e).__name__
            
            print(f"CLOUDINARY: [ERROR] {error_msg}")
            print(f"CLOUDINARY: [ERROR] Tipo: {error_tipo}")
            
            # Log detallado para debugging
            import logging
            logging.error(f"CLOUDINARY ERROR: {error_msg} - Archivo: {archivo_local} - Cotización: {numero_cotizacion}")
            
            # Determinar tipo de error específico
            tipo_error_especifico = "error_desconocido"
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                tipo_error_especifico = "error_autenticacion"
            elif "network" in str(e).lower() or "timeout" in str(e).lower():
                tipo_error_especifico = "error_red"
            elif "quota" in str(e).lower() or "limit" in str(e).lower():
                tipo_error_especifico = "error_cuota"
            
            return {
                "error": error_msg, 
                "fallback": True,
                "tipo_error": tipo_error_especifico,
                "error_tipo": error_tipo,
                "numero_cotizacion": numero_cotizacion
            }

    def descargar_pdf(self, public_id: str, destino_local: str = None) -> dict:
        """
        Descarga un PDF desde Cloudinary
        
        Args:
            public_id: ID público del archivo en Cloudinary
            destino_local: Ruta donde guardar el archivo (opcional)
            
        Returns:
            Dict con ruta del archivo descargado o error
        """
        if not self.cloudinary_available:
            return {"error": "Cloudinary no disponible"}
        
        try:
            import requests
            
            # Obtener URL del archivo (método original)
            url = self.cloudinary.utils.cloudinary_url(
                public_id, 
                resource_type="raw",
                secure=True
            )[0]
            
            print(f"DOWNLOAD: Descargando PDF desde: {url}")
            
            # Descargar archivo
            response = requests.get(url)
            response.raise_for_status()
            
            # Determinar ruta de destino
            if not destino_local:
                # Crear archivo temporal
                temp_dir = tempfile.gettempdir()
                nombre_archivo = f"{public_id.split('/')[-1]}.pdf"
                destino_local = os.path.join(temp_dir, nombre_archivo)
            
            # Guardar archivo
            with open(destino_local, 'wb') as f:
                f.write(response.content)
            
            print(f"OK: PDF descargado: {destino_local}")
            
            return {
                "archivo_local": destino_local,
                "bytes": len(response.content),
                "url_cloudinary": url
            }
            
        except Exception as e:
            error_msg = f"Error descargando PDF desde Cloudinary: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}

    def listar_pdfs(self, folder: str = None, max_resultados: int = 100) -> dict:
        """
        Lista PDFs almacenados en Cloudinary
        
        Args:
            folder: Carpeta específica ('nuevas' o 'antiguas'), None para todas
            max_resultados: Máximo número de resultados
            
        Returns:
            Dict con lista de archivos o error
        """
        if not self.cloudinary_available:
            return {"error": "Cloudinary no disponible", "archivos": []}
        
        try:
            # Determinar filtros
            if folder:
                prefix = f"cotizaciones/{folder}/"
            else:
                prefix = "cotizaciones/"
            
            # Buscar archivos
            resultado = self.cloudinary.api.resources(
                type="upload",
                resource_type="raw",
                prefix=prefix,
                max_results=max_resultados,
                tags=True,
                context=True
            )
            
            # Procesar resultados
            archivos = []
            for recurso in resultado.get('resources', []):
                archivo_info = {
                    "public_id": recurso['public_id'],
                    "url": recurso['secure_url'],  # URL directa de Cloudinary
                    "bytes": recurso['bytes'],
                    "fecha_creacion": recurso['created_at'],
                    "version": recurso['version'],
                    "tags": recurso.get('tags', []),
                    "context": recurso.get('context', {}),
                    "numero_cotizacion": recurso['public_id'].split('/')[-1]
                }
                archivos.append(archivo_info)
            
            print(f"LIST: Encontrados {len(archivos)} PDFs en Cloudinary")
            
            return {
                "archivos": archivos,
                "total": len(archivos),
                "folder": folder or "todas"
            }
            
        except Exception as e:
            error_msg = f"Error listando PDFs en Cloudinary: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg, "archivos": []}

    def eliminar_pdf(self, public_id: str) -> dict:
        """
        Elimina un PDF de Cloudinary
        
        Args:
            public_id: ID público del archivo a eliminar
            
        Returns:
            Dict con resultado de la eliminación
        """
        if not self.cloudinary_available:
            return {"error": "Cloudinary no disponible"}
        
        try:
            print(f"DELETE: Eliminando PDF: {public_id}")
            
            resultado = self.cloudinary.uploader.destroy(
                public_id,
                resource_type="raw",
                invalidate=True
            )
            
            if resultado.get('result') == 'ok':
                print(f"OK: PDF eliminado exitosamente")
                return {"eliminado": True, "public_id": public_id}
            else:
                error_msg = f"Error eliminando PDF: {resultado}"
                print(f"ERROR: {error_msg}")
                return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"Error eliminando PDF de Cloudinary: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}

    def mover_a_antiguas(self, numero_cotizacion: str) -> dict:
        """
        Mueve un PDF de 'nuevas' a 'antiguas'
        
        Args:
            numero_cotizacion: Número de cotización a mover
            
        Returns:
            Dict con resultado del movimiento
        """
        if not self.cloudinary_available:
            return {"error": "Cloudinary no disponible"}
        
        try:
            public_id_origen = f"{self.folder_nuevas}/{numero_cotizacion}"
            public_id_destino = f"{self.folder_antiguas}/{numero_cotizacion}"
            
            print(f"MOVE: Moviendo PDF: {public_id_origen} -> {public_id_destino}")
            
            # Renombrar archivo (mover entre carpetas)
            resultado = self.cloudinary.uploader.rename(
                public_id_origen,
                public_id_destino,
                resource_type="raw",
                overwrite=True,
                invalidate=True
            )
            
            print(f"OK: PDF movido a antiguas exitosamente")
            
            return {
                "movido": True,
                "public_id_anterior": public_id_origen,
                "public_id_nuevo": public_id_destino,
                "url_nueva": resultado['secure_url']
            }
            
        except Exception as e:
            error_msg = f"Error moviendo PDF en Cloudinary: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}

    def buscar_pdfs(self, query: str, max_resultados: int = 100) -> list:
        """
        Busca PDFs en Cloudinary por término de búsqueda
        
        Args:
            query: Término de búsqueda (numero_cotizacion, cliente, vendedor)
            max_resultados: Máximo número de resultados
            
        Returns:
            Lista de PDFs que coinciden con la búsqueda
        """
        if not self.cloudinary_available:
            print("[CLOUDINARY] No disponible para búsqueda")
            return []
        
        try:
            print(f"[CLOUDINARY] Buscando PDFs con query: '{query}'")
            
            # Obtener todos los PDFs de Cloudinary
            resultado_nuevas = self.listar_pdfs("nuevas", max_resultados)
            resultado_antiguas = self.listar_pdfs("antiguas", max_resultados)
            
            todos_pdfs = []
            if not resultado_nuevas.get("error"):
                todos_pdfs.extend(resultado_nuevas.get("archivos", []))
            if not resultado_antiguas.get("error"):
                todos_pdfs.extend(resultado_antiguas.get("archivos", []))
            
            print(f"[CLOUDINARY] Total PDFs encontrados: {len(todos_pdfs)}")
            
            # Filtrar por query si se proporciona
            if query.strip():
                pdfs_filtrados = []
                query_lower = query.lower()
                
                for pdf in todos_pdfs:
                    # Extraer información del nombre del archivo o metadatos
                    public_id = pdf.get("public_id", "")
                    numero_cotizacion = pdf.get("numero_cotizacion", "")
                    
                    # Buscar en múltiples campos
                    if (query_lower in public_id.lower() or 
                        query_lower in numero_cotizacion.lower()):
                        
                        # Parsear información del nombre del archivo
                        nombre_archivo = public_id.split("/")[-1]  # Obtener solo el nombre
                        
                        # Intentar extraer datos del formato: CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO
                        partes = nombre_archivo.replace(".pdf", "").split("-")
                        
                        pdf_info = {
                            "numero_cotizacion": numero_cotizacion or nombre_archivo.replace(".pdf", ""),
                            "cliente": partes[0] if len(partes) > 0 else "Cloudinary",
                            "vendedor": partes[2] if len(partes) > 2 else "N/A",
                            "proyecto": "-".join(partes[5:]) if len(partes) > 5 else "N/A",
                            "fecha_creacion": pdf.get("fecha_creacion", "N/A"),
                            "ruta_completa": pdf.get("url", ""),
                            "tipo": "cloudinary",
                            "tiene_desglose": False,  # PDFs de Cloudinary no tienen desglose
                            "public_id": public_id,
                            "tamaño": pdf.get("bytes", 0),
                            "fuente": "cloudinary"
                        }
                        pdfs_filtrados.append(pdf_info)
                
                print(f"[CLOUDINARY] PDFs filtrados por query: {len(pdfs_filtrados)}")
                return pdfs_filtrados
            else:
                # Sin query, devolver todos con formato estándar
                pdfs_formateados = []
                for pdf in todos_pdfs:
                    public_id = pdf.get("public_id", "")
                    nombre_archivo = public_id.split("/")[-1]
                    partes = nombre_archivo.replace(".pdf", "").split("-")
                    
                    pdf_info = {
                        "numero_cotizacion": pdf.get("numero_cotizacion", nombre_archivo.replace(".pdf", "")),
                        "cliente": partes[0] if len(partes) > 0 else "Cloudinary",
                        "vendedor": partes[2] if len(partes) > 2 else "N/A",
                        "proyecto": "-".join(partes[5:]) if len(partes) > 5 else "N/A",
                        "fecha_creacion": pdf.get("fecha_creacion", "N/A"),
                        "ruta_completa": pdf.get("url", ""),
                        "tipo": "cloudinary",
                        "tiene_desglose": False,
                        "public_id": public_id,
                        "tamaño": pdf.get("bytes", 0),
                        "fuente": "cloudinary"
                    }
                    pdfs_formateados.append(pdf_info)
                
                print(f"[CLOUDINARY] Total PDFs formateados: {len(pdfs_formateados)}")
                return pdfs_formateados
                
        except Exception as e:
            print(f"[CLOUDINARY] Error en búsqueda: {e}")
            return []

    def obtener_estadisticas(self) -> dict:
        """
        Obtiene estadísticas de uso de Cloudinary con reintentos
        
        Returns:
            Dict con estadísticas de almacenamiento
        """
        if not self.cloudinary_available:
            return {"error": "Cloudinary no disponible"}
        
        try:
            # Función interna para obtener estadísticas
            def _stats_operation():
                return self.cloudinary.api.usage()
            
            # Ejecutar con reintentos
            info = self._retry_operation(_stats_operation)
            
            estadisticas = {
                "creditos_usados": info.get('credits', 0),
                "creditos_limite": info.get('limit', 0),
                "bandwidth_usado": info.get('bandwidth', 0),
                "storage_usado": info.get('storage', 0),
                "transformaciones": info.get('transformations', 0),
                "fecha_consulta": datetime.datetime.now().isoformat()
            }
            
            # Obtener conteo de PDFs por carpeta (también con retry)
            try:
                nuevas = self.listar_pdfs("nuevas", max_resultados=1000)
                antiguas = self.listar_pdfs("antiguas", max_resultados=1000)
                
                estadisticas["pdfs_nuevos"] = len(nuevas.get("archivos", []))
                estadisticas["pdfs_antiguos"] = len(antiguas.get("archivos", []))
                estadisticas["total_pdfs"] = estadisticas["pdfs_nuevos"] + estadisticas["pdfs_antiguos"]
            except Exception as list_error:
                print(f"WARNING: No se pudieron obtener conteos de archivos: {list_error}")
                estadisticas["pdfs_nuevos"] = 0
                estadisticas["pdfs_antiguos"] = 0
                estadisticas["total_pdfs"] = 0
            
            print(f"STATS: Estadisticas Cloudinary:")
            print(f"   PDFs almacenados: {estadisticas['total_pdfs']}")
            print(f"   Storage usado: {estadisticas['storage_usado']} bytes")
            print(f"   Bandwidth usado: {estadisticas['bandwidth_usado']} bytes")
            
            return estadisticas
            
        except Exception as e:
            error_msg = f"Error obteniendo estadísticas de Cloudinary: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}


# Función de utilidad para testing
def test_cloudinary_connection():
    """Test rápido de conexión a Cloudinary"""
    print("Probando conexion a Cloudinary...")
    
    manager = CloudinaryManager()
    
    if not manager.is_available():
        print("ERROR: Cloudinary no disponible")
        return False
    
    # Test de estadísticas (no consume recursos)
    stats = manager.obtener_estadisticas()
    
    if "error" in stats:
        print(f"ERROR en test: {stats['error']}")
        return False
    
    print("OK: Conexion a Cloudinary exitosa")
    print(f"   Total PDFs: {stats.get('total_pdfs', 0)}")
    print(f"   Storage usado: {stats.get('storage_usado', 0)} bytes")
    
    return True


if __name__ == "__main__":
    # Test directo del módulo
    test_cloudinary_connection()