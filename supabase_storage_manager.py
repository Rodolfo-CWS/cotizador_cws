"""
Supabase Storage Manager - Sistema de almacenamiento de PDFs en Supabase
Reemplaza Cloudinary con almacenamiento nativo integrado
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SupabaseStorageManager:
    def __init__(self):
        """
        Inicializa el cliente de Supabase Storage para almacenamiento de PDFs
        """
        self.storage_available = False
        self.bucket_name = "cotizaciones-pdfs"
        self.folder_nuevas = "nuevas"
        self.folder_antiguas = "antiguas"
        self.max_retries = 3
        self.retry_delay = 2  # segundos
        
        try:
            from supabase import create_client, Client
            
            # Obtener credenciales de Supabase
            supabase_url = os.getenv('SUPABASE_URL')
            # Para Storage operations, necesitamos SERVICE_KEY (no ANON_KEY)
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            # Fallback a ANON_KEY si SERVICE_KEY no está disponible (solo para testing)
            if not supabase_key:
                supabase_key = os.getenv('SUPABASE_ANON_KEY')
                print("WARNING: Usando ANON_KEY - Storage operations pueden fallar")
            
            if not supabase_url or not supabase_key:
                raise Exception("Variables de entorno de Supabase no configuradas (necesita SUPABASE_SERVICE_KEY)")
            
            # Crear cliente Supabase
            self.supabase: Client = create_client(supabase_url, supabase_key)
            
            # Verificar conexión y bucket
            self._verificar_bucket()
            
            self.storage_available = True
            # Verificar tipo de clave que se está usando
            using_service_key = os.getenv('SUPABASE_SERVICE_KEY') is not None
            key_type = "SERVICE_KEY (Storage completo)" if using_service_key else "ANON_KEY (solo lectura)"
            
            print("OK: Supabase Storage configurado correctamente")
            print(f"   URL: {supabase_url}")
            print(f"   Clave: {key_type}")
            print(f"   Bucket: {self.bucket_name}")
            print(f"   Carpeta nuevas: {self.folder_nuevas}")
            print(f"   Carpeta antiguas: {self.folder_antiguas}")
            
        except ImportError:
            print("ERROR: Supabase no esta instalado: pip install supabase")
        except Exception as e:
            print(f"ERROR configurando Supabase Storage: {e}")
            print("   Verifica las variables de entorno:")
            print("   - SUPABASE_URL")
            print("   - SUPABASE_SERVICE_KEY (requerida para Storage)")
            print("   - SUPABASE_ANON_KEY (fallback solo lectura)")

    def _verificar_bucket(self):
        """Verificar que el bucket existe o crearlo"""
        try:
            # Intentar listar archivos del bucket (esto verifica que existe)
            response = self.supabase.storage.from_(self.bucket_name).list()
            print(f"BUCKET: Bucket '{self.bucket_name}' verificado exitosamente")
        except Exception as e:
            print(f"BUCKET: Error verificando bucket: {e}")
            # El bucket podría no existir, pero continuamos
            # En Supabase, los buckets generalmente se crean via dashboard

    def is_available(self) -> bool:
        """Verifica si Supabase Storage está disponible y configurado"""
        return self.storage_available
    
    def _retry_operation(self, operation_func, *args, **kwargs):
        """
        Ejecuta una operación con reintentos automáticos
        """
        import time
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
        Sube un PDF a Supabase Storage con reintentos automáticos
        
        Args:
            archivo_local: Ruta del archivo local a subir
            numero_cotizacion: Número de cotización (ej: CLIENTE-CWS-XX-001-R1-PROYECTO)
            es_nueva: True para carpeta 'nuevas', False para 'antiguas'
            
        Returns:
            Dict con información del archivo subido o error detallado
        """
        if not self.storage_available:
            print("SUPABASE_STORAGE: Servicio no disponible - usando fallback")
            return {
                "error": "Supabase Storage no disponible", 
                "fallback": True,
                "tipo_error": "servicio_no_disponible"
            }
        
        # Validaciones previas
        if not os.path.exists(archivo_local):
            print(f"SUPABASE_STORAGE: Archivo no existe: {archivo_local}")
            return {
                "error": f"Archivo no existe: {archivo_local}",
                "fallback": True,
                "tipo_error": "archivo_no_existe"
            }
        
        try:
            # Determinar carpeta de destino
            folder = self.folder_nuevas if es_nueva else self.folder_antiguas
            
            # Crear path completo para el archivo
            file_path = f"{folder}/{numero_cotizacion}.pdf"
            
            print(f"SUPABASE_STORAGE: [INICIO] Subiendo PDF: {file_path}")
            print(f"SUPABASE_STORAGE: Archivo local: {archivo_local} (tamaño: {os.path.getsize(archivo_local)} bytes)")
            
            # Función interna para la subida (para usar con retry)
            def _upload_operation():
                with open(archivo_local, 'rb') as file:
                    response = self.supabase.storage.from_(self.bucket_name).upload(
                        path=file_path,
                        file=file,
                        file_options={
                            "content-type": "application/pdf",
                            "upsert": "true"  # Sobrescribir si existe (string)
                        }
                    )
                return response
            
            # Ejecutar con reintentos
            resultado = self._retry_operation(_upload_operation)
            
            # Obtener URL pública del archivo
            url_publica = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            
            # Extraer información relevante
            info_archivo = {
                "url": url_publica,
                "file_path": file_path,
                "bytes": os.path.getsize(archivo_local),
                "formato": "pdf",
                "fecha_subida": datetime.datetime.now().isoformat(),
                "folder": folder,
                "numero_cotizacion": numero_cotizacion,
                "bucket": self.bucket_name
            }
            
            print(f"OK: PDF subido exitosamente a Supabase Storage:")
            print(f"   URL: {info_archivo['url']}")
            print(f"   Tamaño: {info_archivo['bytes']} bytes")
            print(f"   Path: {file_path}")
            
            return info_archivo
            
        except Exception as e:
            error_msg = f"Error subiendo PDF a Supabase Storage: {e}"
            error_tipo = type(e).__name__
            
            print(f"SUPABASE_STORAGE: [ERROR] {error_msg}")
            print(f"SUPABASE_STORAGE: [ERROR] Tipo: {error_tipo}")
            
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

    def descargar_pdf(self, file_path: str, destino_local: str = None) -> dict:
        """
        Descarga un PDF desde Supabase Storage
        
        Args:
            file_path: Path del archivo en el bucket (ej: "nuevas/CLIENTE-001.pdf")
            destino_local: Ruta donde guardar el archivo (opcional)
            
        Returns:
            Dict con ruta del archivo descargado o error
        """
        if not self.storage_available:
            return {"error": "Supabase Storage no disponible"}
        
        try:
            print(f"DOWNLOAD: Descargando PDF desde Supabase: {file_path}")
            
            # Descargar archivo
            response = self.supabase.storage.from_(self.bucket_name).download(file_path)
            
            # Determinar ruta de destino
            if not destino_local:
                # Crear archivo temporal
                temp_dir = tempfile.gettempdir()
                nombre_archivo = f"{file_path.split('/')[-1]}"
                destino_local = os.path.join(temp_dir, nombre_archivo)
            
            # Guardar archivo
            with open(destino_local, 'wb') as f:
                f.write(response)
            
            print(f"OK: PDF descargado: {destino_local}")
            
            return {
                "archivo_local": destino_local,
                "bytes": len(response),
                "file_path": file_path
            }
            
        except Exception as e:
            error_msg = f"Error descargando PDF desde Supabase Storage: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}

    def listar_pdfs(self, folder: str = None, max_resultados: int = 100) -> dict:
        """
        Lista PDFs almacenados en Supabase Storage
        
        Args:
            folder: Carpeta específica ('nuevas' o 'antiguas'), None para todas
            max_resultados: Máximo número de resultados
            
        Returns:
            Dict con lista de archivos o error
        """
        if not self.storage_available:
            return {"error": "Supabase Storage no disponible", "archivos": []}
        
        try:
            archivos = []
            
            # Determinar carpetas a buscar
            carpetas = [folder] if folder else [self.folder_nuevas, self.folder_antiguas]
            
            for carpeta in carpetas:
                try:
                    # Listar archivos en la carpeta
                    response = self.supabase.storage.from_(self.bucket_name).list(carpeta)
                    
                    for archivo in response:
                        if archivo['name'].endswith('.pdf'):
                            file_path = f"{carpeta}/{archivo['name']}"
                            url_publica = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                            
                            archivo_info = {
                                "file_path": file_path,
                                "url": url_publica,
                                "name": archivo['name'],
                                "bytes": archivo.get('metadata', {}).get('size', 0),
                                "fecha_creacion": archivo.get('created_at', ''),
                                "fecha_actualizacion": archivo.get('updated_at', ''),
                                "carpeta": carpeta,
                                "numero_cotizacion": archivo['name'].replace('.pdf', '')
                            }
                            archivos.append(archivo_info)
                            
                except Exception as e:
                    print(f"ERROR listando carpeta {carpeta}: {e}")
                    continue
            
            print(f"LIST: Encontrados {len(archivos)} PDFs en Supabase Storage")
            
            return {
                "archivos": archivos,
                "total": len(archivos),
                "folder": folder or "todas"
            }
            
        except Exception as e:
            error_msg = f"Error listando PDFs en Supabase Storage: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg, "archivos": []}

    def eliminar_pdf(self, file_path: str) -> dict:
        """
        Elimina un PDF de Supabase Storage
        
        Args:
            file_path: Path del archivo a eliminar (ej: "nuevas/CLIENTE-001.pdf")
            
        Returns:
            Dict con resultado de la eliminación
        """
        if not self.storage_available:
            return {"error": "Supabase Storage no disponible"}
        
        try:
            print(f"DELETE: Eliminando PDF: {file_path}")
            
            response = self.supabase.storage.from_(self.bucket_name).remove([file_path])
            
            print(f"OK: PDF eliminado exitosamente")
            return {"eliminado": True, "file_path": file_path}
            
        except Exception as e:
            error_msg = f"Error eliminando PDF de Supabase Storage: {e}"
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
        if not self.storage_available:
            return {"error": "Supabase Storage no disponible"}
        
        try:
            file_origen = f"{self.folder_nuevas}/{numero_cotizacion}.pdf"
            file_destino = f"{self.folder_antiguas}/{numero_cotizacion}.pdf"
            
            print(f"MOVE: Moviendo PDF: {file_origen} -> {file_destino}")
            
            # En Supabase, mover = copiar + eliminar
            response = self.supabase.storage.from_(self.bucket_name).move(file_origen, file_destino)
            
            url_nueva = self.supabase.storage.from_(self.bucket_name).get_public_url(file_destino)
            
            print(f"OK: PDF movido a antiguas exitosamente")
            
            return {
                "movido": True,
                "file_path_anterior": file_origen,
                "file_path_nuevo": file_destino,
                "url_nueva": url_nueva
            }
            
        except Exception as e:
            error_msg = f"Error moviendo PDF en Supabase Storage: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}

    def buscar_pdfs(self, query: str, max_resultados: int = 100) -> list:
        """
        Busca PDFs en Supabase Storage por término de búsqueda
        
        Args:
            query: Término de búsqueda (numero_cotizacion, cliente, vendedor)
            max_resultados: Máximo número de resultados
            
        Returns:
            Lista de PDFs que coinciden con la búsqueda
        """
        if not self.storage_available:
            print("[SUPABASE_STORAGE] No disponible para búsqueda")
            return []
        
        try:
            print(f"[SUPABASE_STORAGE] Buscando PDFs con query: '{query}'")
            
            # Obtener todos los PDFs
            resultado = self.listar_pdfs(max_resultados=max_resultados)
            todos_pdfs = resultado.get("archivos", [])
            
            print(f"[SUPABASE_STORAGE] Total PDFs encontrados: {len(todos_pdfs)}")
            
            # Filtrar por query si se proporciona
            if query.strip():
                pdfs_filtrados = []
                query_lower = query.lower()
                
                for pdf in todos_pdfs:
                    nombre_archivo = pdf.get("name", "")
                    numero_cotizacion = pdf.get("numero_cotizacion", "")
                    
                    # Buscar en múltiples campos
                    if (query_lower in nombre_archivo.lower() or 
                        query_lower in numero_cotizacion.lower()):
                        
                        # Parsear información del nombre del archivo
                        partes = numero_cotizacion.split("-")
                        
                        pdf_info = {
                            "numero_cotizacion": numero_cotizacion,
                            "cliente": partes[0] if len(partes) > 0 else "Supabase",
                            "vendedor": partes[2] if len(partes) > 2 else "N/A",
                            "proyecto": "-".join(partes[5:]) if len(partes) > 5 else "N/A",
                            "fecha_creacion": pdf.get("fecha_creacion", "N/A"),
                            "ruta_completa": pdf.get("url", ""),
                            "tipo": "supabase_storage",
                            "tiene_desglose": False,  # PDFs de Storage no tienen desglose automático
                            "file_path": pdf.get("file_path", ""),
                            "tamaño": pdf.get("bytes", 0),
                            "fuente": "supabase_storage"
                        }
                        pdfs_filtrados.append(pdf_info)
                
                print(f"[SUPABASE_STORAGE] PDFs filtrados por query: {len(pdfs_filtrados)}")
                return pdfs_filtrados
            else:
                # Sin query, devolver todos con formato estándar
                pdfs_formateados = []
                for pdf in todos_pdfs:
                    numero_cotizacion = pdf.get("numero_cotizacion", "")
                    partes = numero_cotizacion.split("-")
                    
                    pdf_info = {
                        "numero_cotizacion": numero_cotizacion,
                        "cliente": partes[0] if len(partes) > 0 else "Supabase",
                        "vendedor": partes[2] if len(partes) > 2 else "N/A",
                        "proyecto": "-".join(partes[5:]) if len(partes) > 5 else "N/A",
                        "fecha_creacion": pdf.get("fecha_creacion", "N/A"),
                        "ruta_completa": pdf.get("url", ""),
                        "tipo": "supabase_storage",
                        "tiene_desglose": False,
                        "file_path": pdf.get("file_path", ""),
                        "tamaño": pdf.get("bytes", 0),
                        "fuente": "supabase_storage"
                    }
                    pdfs_formateados.append(pdf_info)
                
                print(f"[SUPABASE_STORAGE] Total PDFs formateados: {len(pdfs_formateados)}")
                return pdfs_formateados
                
        except Exception as e:
            print(f"[SUPABASE_STORAGE] Error en búsqueda: {e}")
            return []

    def obtener_estadisticas(self) -> dict:
        """
        Obtiene estadísticas de uso de Supabase Storage
        
        Returns:
            Dict con estadísticas de almacenamiento
        """
        if not self.storage_available:
            return {"error": "Supabase Storage no disponible"}
        
        try:
            # Obtener conteo de PDFs por carpeta
            nuevas = self.listar_pdfs(self.folder_nuevas, max_resultados=1000)
            antiguas = self.listar_pdfs(self.folder_antiguas, max_resultados=1000)
            
            estadisticas = {
                "pdfs_nuevos": len(nuevas.get("archivos", [])),
                "pdfs_antiguos": len(antiguas.get("archivos", [])),
                "total_pdfs": len(nuevas.get("archivos", [])) + len(antiguas.get("archivos", [])),
                "bucket_name": self.bucket_name,
                "fecha_consulta": datetime.datetime.now().isoformat()
            }
            
            print(f"STATS: Estadísticas Supabase Storage:")
            print(f"   PDFs almacenados: {estadisticas['total_pdfs']}")
            print(f"   Nuevos: {estadisticas['pdfs_nuevos']}")
            print(f"   Antiguos: {estadisticas['pdfs_antiguos']}")
            
            return estadisticas
            
        except Exception as e:
            error_msg = f"Error obteniendo estadísticas de Supabase Storage: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}


# Función de utilidad para testing
def test_supabase_storage_connection():
    """Test rápido de conexión a Supabase Storage"""
    print("Probando conexión a Supabase Storage...")
    
    manager = SupabaseStorageManager()
    
    if not manager.is_available():
        print("ERROR: Supabase Storage no disponible")
        return False
    
    # Test de estadísticas
    stats = manager.obtener_estadisticas()
    
    if "error" in stats:
        print(f"ERROR en test: {stats['error']}")
        return False
    
    print("OK: Conexión a Supabase Storage exitosa")
    print(f"   Total PDFs: {stats.get('total_pdfs', 0)}")
    print(f"   Bucket: {stats.get('bucket_name', 'N/A')}")
    
    return True


if __name__ == "__main__":
    # Test directo del módulo
    test_supabase_storage_connection()