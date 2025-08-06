"""
Google Drive Client - Acceso a PDFs almacenados en Google Drive
Maneja autenticación y descarga de archivos desde Google Drive para Render
"""

import os
import json
import io
from typing import Dict, List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class GoogleDriveClient:
    def __init__(self):
        """Inicializa el cliente de Google Drive"""
        self.service = None
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '1GqM9yfwUKd9n8nN97IUiBSUrWUZ1Vida')
        self._initialize_service()
    
    def _initialize_service(self):
        """Inicializa el servicio de Google Drive usando Service Account"""
        try:
            # Obtener credenciales desde variable de entorno
            credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if not credentials_json:
                print("Google Drive: No hay credenciales configuradas")
                return
            
            # Parsear JSON de credenciales
            credentials_info = json.loads(credentials_json)
            
            # Crear credenciales desde el JSON
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            # Crear servicio de Google Drive
            self.service = build('drive', 'v3', credentials=credentials)
            print("Google Drive: Cliente inicializado correctamente")
            
        except Exception as e:
            print(f"Error inicializando Google Drive: {e}")
            self.service = None
    
    def is_available(self) -> bool:
        """Verifica si el cliente de Google Drive está disponible"""
        return self.service is not None
    
    def buscar_pdfs(self, query: str = "") -> List[Dict]:
        """
        Busca archivos PDF en Google Drive
        
        Args:
            query: Término de búsqueda (opcional)
        
        Returns:
            Lista de archivos PDF encontrados
        """
        if not self.is_available():
            return []
        
        try:
            # Construir query de búsqueda
            search_query = f"'{self.folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            
            if query:
                # Buscar en el nombre del archivo
                search_query += f" and name contains '{query}'"
            
            # Ejecutar búsqueda
            results = self.service.files().list(
                q=search_query,
                pageSize=100,
                fields="files(id, name, size, modifiedTime, parents)"
            ).execute()
            
            files = results.get('files', [])
            
            # Formatear resultados
            pdfs = []
            for file in files:
                pdfs.append({
                    'id': file['id'],
                    'nombre': file['name'],
                    'numero_cotizacion': file['name'].replace('.pdf', ''),
                    'tamaño': file.get('size', '0'),
                    'fecha_modificacion': file.get('modifiedTime', ''),
                    'tipo': 'google_drive'
                })
            
            print(f"Google Drive: Encontrados {len(pdfs)} PDFs")
            return pdfs
            
        except Exception as e:
            print(f"Error buscando PDFs en Google Drive: {e}")
            return []
    
    def obtener_pdf(self, nombre_archivo: str) -> Optional[bytes]:
        """
        Obtiene el contenido de un PDF desde Google Drive
        
        Args:
            nombre_archivo: Nombre del archivo PDF (con o sin extensión)
        
        Returns:
            Contenido del archivo en bytes o None si no se encuentra
        """
        if not self.is_available():
            return None
        
        try:
            # Asegurar que el nombre tenga extensión .pdf
            if not nombre_archivo.endswith('.pdf'):
                nombre_archivo += '.pdf'
            
            # Buscar el archivo por nombre
            search_query = f"'{self.folder_id}' in parents and name='{nombre_archivo}' and mimeType='application/pdf' and trashed=false"
            
            results = self.service.files().list(
                q=search_query,
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                print(f"Google Drive: No se encontró el archivo '{nombre_archivo}'")
                return None
            
            file_id = files[0]['id']
            
            # Descargar el archivo
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            
            while done is False:
                status, done = downloader.next_chunk()
            
            file_buffer.seek(0)
            contenido = file_buffer.read()
            
            print(f"Google Drive: Descargado '{nombre_archivo}' ({len(contenido)} bytes)")
            return contenido
            
        except Exception as e:
            print(f"Error descargando PDF desde Google Drive: {e}")
            return None
    
    def listar_carpetas(self) -> List[Dict]:
        """
        Lista las subcarpetas en la carpeta principal
        
        Returns:
            Lista de carpetas encontradas
        """
        if not self.is_available():
            return []
        
        try:
            search_query = f"'{self.folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=search_query,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            print(f"Google Drive: Encontradas {len(folders)} carpetas")
            
            return [{'id': f['id'], 'nombre': f['name']} for f in folders]
            
        except Exception as e:
            print(f"Error listando carpetas: {e}")
            return []