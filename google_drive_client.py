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
        # Folder IDs para búsqueda en múltiples carpetas
        self.folder_nuevas = os.getenv('GOOGLE_DRIVE_FOLDER_NUEVAS', '1h4Df0bdInRU5GUh9n7g8aXgZA4Kyt2Nf')  # Carpeta nuevas
        self.folder_antiguas = os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS', '1GqM9yfwUKd9n8nN97IUiBSUrWUZ1Vida')  # Carpeta antiguas/raíz
        # Mantener compatibilidad hacia atrás
        self.folder_id = self.folder_nuevas  # Por defecto usar nuevas
        self._initialize_service()
    
    def _initialize_service(self):
        """Inicializa el servicio de Google Drive usando Service Account"""
        try:
            # Obtener credenciales desde variable de entorno
            credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if not credentials_json:
                print("[ERROR] Google Drive: No hay credenciales configuradas")
                print("   Variable requerida: GOOGLE_SERVICE_ACCOUNT_JSON")
                return
            
            print("[INIT] Google Drive: Inicializando cliente...")
            print(f"   Folder ID: {self.folder_id}")
            
            # Parsear JSON de credenciales
            credentials_info = json.loads(credentials_json)
            
            # Verificar campos requeridos
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in credentials_info]
            
            if missing_fields:
                print(f"[ERROR] Google Drive: Faltan campos en credenciales: {missing_fields}")
                return
            
            # Crear credenciales desde el JSON
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            # Crear servicio de Google Drive
            self.service = build('drive', 'v3', credentials=credentials)
            
            # Verificar acceso
            try:
                # Test simple para verificar acceso
                self.service.files().list(pageSize=1).execute()
                print("[OK] Google Drive: Cliente inicializado correctamente")
                print(f"   Email de servicio: {credentials_info.get('client_email', 'N/A')}")
            except Exception as test_error:
                print(f"[ERROR] Google Drive: Error en test de acceso: {test_error}")
                self.service = None
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Google Drive: JSON inválido en credenciales: {e}")
            self.service = None
        except Exception as e:
            print(f"[ERROR] Google Drive: Error inicializando: {e}")
            print(f"   Tipo de error: {type(e).__name__}")
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
            print("[ERROR] Google Drive: Cliente no disponible para búsqueda")
            return []
        
        try:
            print(f"🔍 Google Drive: Buscando PDFs con query: '{query}'")
            print(f"   Carpeta nuevas: {self.folder_nuevas}")
            print(f"   Carpeta antiguas: {self.folder_antiguas}")
            
            # Buscar en ambas carpetas
            all_files = []
            carpetas = [
                ("nuevas", self.folder_nuevas),
                ("antiguas", self.folder_antiguas)
            ]
            
            for nombre_carpeta, folder_id in carpetas:
                print(f"   Buscando en carpeta {nombre_carpeta}...")
                
                # Construir query de búsqueda para esta carpeta
                search_query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
                
                if query:
                    # Buscar en el nombre del archivo
                    search_query += f" and name contains '{query}'"
                    
                print(f"   Query para {nombre_carpeta}: {search_query}")
                
                # Ejecutar búsqueda
                results = self.service.files().list(
                    q=search_query,
                    pageSize=100,
                    fields="files(id, name, size, modifiedTime, parents)"
                ).execute()
                
                files = results.get('files', [])
                print(f"   📊 {nombre_carpeta}: {len(files)} archivos encontrados")
                
                # Agregar información de la carpeta a cada archivo
                for file in files:
                    file['carpeta_origen'] = nombre_carpeta
                    all_files.append(file)
            
            print(f"📊 Google Drive: Total de archivos - {len(all_files)}")
            
            # Formatear resultados
            pdfs = []
            for file in all_files:  # Usar all_files en lugar de files
                nombre_archivo = file['name']
                carpeta = file.get('carpeta_origen', 'desconocida')
                print(f"   📄 Archivo encontrado: {nombre_archivo} (ID: {file['id']}) en {carpeta}")
                
                # Extraer número de cotización del nombre del archivo
                numero_cotizacion = nombre_archivo.replace('.pdf', '')
                # Si tiene prefijo "Cotizacion_", removerlo para el número de cotización
                if numero_cotizacion.startswith('Cotizacion_'):
                    numero_cotizacion = numero_cotizacion.replace('Cotizacion_', '')
                
                pdfs.append({
                    'id': file['id'],
                    'nombre': nombre_archivo,
                    'numero_cotizacion': numero_cotizacion,
                    'tamaño': file.get('size', '0'),
                    'fecha_modificacion': file.get('modifiedTime', ''),
                    'tipo': 'google_drive',
                    'carpeta_origen': carpeta
                })
            
            print(f"[OK] Google Drive: Procesados {len(pdfs)} PDFs exitosamente")
            return pdfs
            
        except Exception as e:
            print(f"[ERROR] Google Drive: Error buscando PDFs: {e}")
            print(f"   Tipo de error: {type(e).__name__}")
            if hasattr(e, 'resp'):
                print(f"   Código HTTP: {e.resp.status if e.resp else 'N/A'}")
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
            print(f"🔽 Google Drive: Iniciando descarga de '{nombre_archivo}'")
            
            # Crear variaciones del nombre a buscar
            nombres_a_probar = [
                nombre_archivo,
                f"Cotizacion_{nombre_archivo}"  # Con prefijo
            ]
            
            # Asegurar que todos tengan extensión .pdf
            nombres_finales = []
            for nombre in nombres_a_probar:
                if not nombre.endswith('.pdf'):
                    nombres_finales.append(f"{nombre}.pdf")
                else:
                    nombres_finales.append(nombre)
            
            print(f"   Nombres a probar: {nombres_finales}")
            
            # Buscar con cada variación de nombre en ambas carpetas
            file_id = None
            nombre_encontrado = None
            carpeta_encontrada = None
            
            carpetas = [
                ("nuevas", self.folder_nuevas),
                ("antiguas", self.folder_antiguas)
            ]
            
            for nombre_prueba in nombres_finales:
                print(f"   Probando: '{nombre_prueba}'")
                
                for nombre_carpeta, folder_id in carpetas:
                    print(f"     En carpeta {nombre_carpeta}...")
                    search_query = f"'{folder_id}' in parents and name='{nombre_prueba}' and mimeType='application/pdf' and trashed=false"
                    
                    results = self.service.files().list(
                        q=search_query,
                        pageSize=1,
                        fields="files(id, name)"
                    ).execute()
                    
                    files = results.get('files', [])
                    print(f"       Archivos encontrados: {len(files)}")
                    
                    if files:
                        file_id = files[0]['id']
                        nombre_encontrado = files[0]['name']
                        carpeta_encontrada = nombre_carpeta
                        print(f"   [FOUND] Archivo encontrado: '{nombre_encontrado}' (ID: {file_id}) en {carpeta_encontrada}")
                        break
                
                if file_id:  # Si ya encontramos el archivo, salir del loop exterior
                    break
            
            if not file_id:
                print(f"[ERROR] Google Drive: No se encontró el archivo con ninguna variación")
                # Búsqueda con 'contains' como último recurso
                nombre_base = nombre_archivo.replace('.pdf', '')
                print(f"   Intentando búsqueda con 'contains': '{nombre_base}'")
                search_query_contains = f"'{self.folder_id}' in parents and name contains '{nombre_base}' and mimeType='application/pdf' and trashed=false"
                results_contains = self.service.files().list(q=search_query_contains, pageSize=5, fields="files(id, name)").execute()
                files_contains = results_contains.get('files', [])
                print(f"   Búsqueda con 'contains': {len(files_contains)} archivos")
                for f in files_contains:
                    print(f"     - {f['name']} (ID: {f['id']})")
                return None
            
            # Descargar el archivo
            print(f"   Iniciando descarga...")
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            bytes_downloaded = 0
            
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    bytes_downloaded = status.resumable_progress
                    print(f"   Progreso: {bytes_downloaded} bytes descargados")
            
            file_buffer.seek(0)
            contenido = file_buffer.read()
            
            print(f"[OK] Google Drive: Descarga completa de '{nombre_archivo}' ({len(contenido)} bytes)")
            return contenido
            
        except Exception as e:
            print(f"[ERROR] Google Drive: Error descargando PDF: {e}")
            print(f"   Tipo de error: {type(e).__name__}")
            if hasattr(e, 'resp'):
                print(f"   Código HTTP: {e.resp.status if e.resp else 'N/A'}")
            return None
    
    def obtener_pdf_por_id(self, file_id: str, nombre_archivo: str = "archivo") -> Optional[bytes]:
        """
        Obtiene el contenido de un PDF directamente por su ID de Google Drive
        
        Args:
            file_id: ID del archivo en Google Drive
            nombre_archivo: Nombre del archivo para logging
            
        Returns:
            Contenido del archivo en bytes o None si hay error
        """
        if not self.is_available():
            print("[ERROR] Google Drive: Cliente no disponible")
            return None
        
        try:
            print(f"🔽 Google Drive: Descargando por ID: {file_id} (nombre: {nombre_archivo})")
            
            # Descargar directamente por ID
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            bytes_downloaded = 0
            
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    bytes_downloaded = status.resumable_progress
                    print(f"   Progreso: {bytes_downloaded} bytes descargados")
            
            file_buffer.seek(0)
            contenido = file_buffer.read()
            
            print(f"[OK] Google Drive: Descarga por ID completa ({len(contenido)} bytes)")
            return contenido
            
        except Exception as e:
            print(f"[ERROR] Google Drive: Error descargando por ID: {e}")
            print(f"   File ID: {file_id}")
            print(f"   Tipo de error: {type(e).__name__}")
            if hasattr(e, 'resp'):
                print(f"   Código HTTP: {e.resp.status if e.resp else 'N/A'}")
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