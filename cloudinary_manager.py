"""
Cloudinary Manager - Sistema de almacenamiento de PDFs en Cloudinary
Reemplaza Google Drive con almacenamiento gratuito de 25GB
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

class CloudinaryManager:
    def __init__(self):
        """
        Inicializa el cliente de Cloudinary para almacenamiento de PDFs
        """
        self.cloudinary_available = False
        self.folder_nuevas = "cotizaciones/nuevas"
        self.folder_antiguas = "cotizaciones/antiguas" 
        
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

    def subir_pdf(self, archivo_local: str, numero_cotizacion: str, es_nueva: bool = True) -> dict:
        """
        Sube un PDF a Cloudinary
        
        Args:
            archivo_local: Ruta del archivo local a subir
            numero_cotizacion: Número de cotización (ej: CLIENTE-CWS-XX-001-R1-PROYECTO)
            es_nueva: True para carpeta 'nuevas', False para 'antiguas'
            
        Returns:
            Dict con información del archivo subido o error
        """
        if not self.cloudinary_available:
            return {"error": "Cloudinary no disponible", "fallback": True}
        
        try:
            # Determinar carpeta de destino
            folder = self.folder_nuevas if es_nueva else self.folder_antiguas
            
            # Crear nombre público único
            public_id = f"{folder}/{numero_cotizacion}"
            
            # Subir archivo
            print(f"📤 Subiendo PDF a Cloudinary: {public_id}")
            
            resultado = self.cloudinary.uploader.upload(
                archivo_local,
                public_id=public_id,
                resource_type="raw",  # Para archivos no-imagen como PDFs
                overwrite=True,       # Sobrescribir si ya existe
                invalidate=True,      # Invalidar cache CDN
                tags=["cotizacion", "pdf", "cws"],  # Tags para organización
                context=f"numero={numero_cotizacion}|fecha={datetime.datetime.now().isoformat()}"
            )
            
            # Extraer información relevante
            info_archivo = {
                "url": resultado['secure_url'],
                "public_id": resultado['public_id'],
                "bytes": resultado['bytes'],
                "formato": resultado['format'],
                "fecha_subida": resultado['created_at'],
                "version": resultado['version'],
                "etag": resultado.get('etag', ''),
                "folder": folder,
                "numero_cotizacion": numero_cotizacion
            }
            
            print(f"✅ PDF subido exitosamente:")
            print(f"   URL: {info_archivo['url']}")
            print(f"   Tamaño: {info_archivo['bytes']} bytes")
            
            return info_archivo
            
        except Exception as e:
            error_msg = f"Error subiendo PDF a Cloudinary: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "fallback": True}

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
            
            # Obtener URL del archivo
            url = self.cloudinary.utils.cloudinary_url(
                public_id, 
                resource_type="raw",
                secure=True
            )[0]
            
            print(f"📥 Descargando PDF desde: {url}")
            
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
            
            print(f"✅ PDF descargado: {destino_local}")
            
            return {
                "archivo_local": destino_local,
                "bytes": len(response.content),
                "url_cloudinary": url
            }
            
        except Exception as e:
            error_msg = f"Error descargando PDF desde Cloudinary: {e}"
            print(f"❌ {error_msg}")
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
                    "url": recurso['secure_url'],
                    "bytes": recurso['bytes'],
                    "fecha_creacion": recurso['created_at'],
                    "version": recurso['version'],
                    "tags": recurso.get('tags', []),
                    "context": recurso.get('context', {}),
                    "numero_cotizacion": recurso['public_id'].split('/')[-1]
                }
                archivos.append(archivo_info)
            
            print(f"📋 Encontrados {len(archivos)} PDFs en Cloudinary")
            
            return {
                "archivos": archivos,
                "total": len(archivos),
                "folder": folder or "todas"
            }
            
        except Exception as e:
            error_msg = f"Error listando PDFs en Cloudinary: {e}"
            print(f"❌ {error_msg}")
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
            print(f"🗑️ Eliminando PDF: {public_id}")
            
            resultado = self.cloudinary.uploader.destroy(
                public_id,
                resource_type="raw",
                invalidate=True
            )
            
            if resultado.get('result') == 'ok':
                print(f"✅ PDF eliminado exitosamente")
                return {"eliminado": True, "public_id": public_id}
            else:
                error_msg = f"Error eliminando PDF: {resultado}"
                print(f"❌ {error_msg}")
                return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"Error eliminando PDF de Cloudinary: {e}"
            print(f"❌ {error_msg}")
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
            
            print(f"📁 Moviendo PDF: {public_id_origen} → {public_id_destino}")
            
            # Renombrar archivo (mover entre carpetas)
            resultado = self.cloudinary.uploader.rename(
                public_id_origen,
                public_id_destino,
                resource_type="raw",
                overwrite=True,
                invalidate=True
            )
            
            print(f"✅ PDF movido a antiguas exitosamente")
            
            return {
                "movido": True,
                "public_id_anterior": public_id_origen,
                "public_id_nuevo": public_id_destino,
                "url_nueva": resultado['secure_url']
            }
            
        except Exception as e:
            error_msg = f"Error moviendo PDF en Cloudinary: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}

    def obtener_estadisticas(self) -> dict:
        """
        Obtiene estadísticas de uso de Cloudinary
        
        Returns:
            Dict con estadísticas de almacenamiento
        """
        if not self.cloudinary_available:
            return {"error": "Cloudinary no disponible"}
        
        try:
            # Obtener información de la cuenta
            info = self.cloudinary.api.usage()
            
            estadisticas = {
                "creditos_usados": info.get('credits', 0),
                "creditos_limite": info.get('limit', 0),
                "bandwidth_usado": info.get('bandwidth', 0),
                "storage_usado": info.get('storage', 0),
                "transformaciones": info.get('transformations', 0),
                "fecha_consulta": datetime.datetime.now().isoformat()
            }
            
            # Obtener conteo de PDFs por carpeta
            nuevas = self.listar_pdfs("nuevas", max_resultados=1000)
            antiguas = self.listar_pdfs("antiguas", max_resultados=1000)
            
            estadisticas["pdfs_nuevos"] = len(nuevas.get("archivos", []))
            estadisticas["pdfs_antiguos"] = len(antiguas.get("archivos", []))
            estadisticas["total_pdfs"] = estadisticas["pdfs_nuevos"] + estadisticas["pdfs_antiguos"]
            
            print(f"📊 Estadísticas Cloudinary:")
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