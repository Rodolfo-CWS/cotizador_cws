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
        # Folder IDs para búsqueda en múltiples carpetas - configurable desde variables de entorno
        self.folder_nuevas = os.getenv('GOOGLE_DRIVE_FOLDER_NUEVAS', '1h4Df0bdInRU5GUh9n7g8aXgZA4Kyt2Nf')  # Carpeta nuevas
        self.folder_antiguas = os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS', '1GqM9yfwUKd9n8nN97IUiBSUrWUZ1Vida')  # Carpeta antiguas/raíz
        # Mantener compatibilidad hacia atrás
        self.folder_id = self.folder_nuevas  # Por defecto usar nuevas
        
        print(f"[GOOGLE_DRIVE] Configuración de carpetas:")
        print(f"  Carpeta nuevas: {self.folder_nuevas}")
        print(f"  Carpeta antiguas: {self.folder_antiguas}")
        print(f"  Carpeta por defecto: {self.folder_id}")
        self._initialize_service()
    
    def _initialize_service(self):
        """Inicializa el servicio de Google Drive con autenticación robusta para serverless"""
        try:
            # MEJORADO: Detección de entorno para logging específico
            es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
            entorno = "RENDER" if es_render else "LOCAL"
            print(f"[GOOGLE_DRIVE] [INIT] Inicializando en entorno: {entorno}")
            
            # Obtener credenciales desde variable de entorno con validación mejorada
            credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if not credentials_json:
                print("[ERROR] Google Drive: No hay credenciales configuradas")
                print("   Variable requerida: GOOGLE_SERVICE_ACCOUNT_JSON")
                print("   En Render: Configurar en Environment Variables")
                print("   En Local: Configurar en archivo .env")
                return
            
            print(f"[GOOGLE_DRIVE] Credenciales encontradas - Longitud: {len(credentials_json)} chars")
            
            # NUEVO: Validación previa del JSON antes de parsear
            if not credentials_json.strip().startswith('{'):
                print("[ERROR] Google Drive: Credenciales no parecen ser JSON válido")
                print(f"   Primeros 100 chars: {credentials_json[:100]}...")
                return
            
            print("[INIT] Google Drive: Inicializando cliente...")
            print(f"   Folder ID: {self.folder_id}")
            
            # MEJORADO: Parsear JSON con mejor manejo de errores
            print("[GOOGLE_DRIVE] Parseando credenciales JSON...")
            try:
                credentials_info = json.loads(credentials_json)
                print("[GOOGLE_DRIVE] [OK] JSON parseado exitosamente")
            except json.JSONDecodeError as json_error:
                print(f"[ERROR] Google Drive: JSON inválido - {json_error}")
                print(f"   Línea {json_error.lineno}, columna {json_error.colno}")
                if json_error.pos < len(credentials_json):
                    print(f"   Contexto: ...{credentials_json[max(0, json_error.pos-20):json_error.pos+20]}...")
                return
            
            # MEJORADO: Verificar campos requeridos con detalle
            required_fields = {
                'type': 'Tipo de cuenta de servicio',
                'project_id': 'ID del proyecto Google Cloud',
                'private_key_id': 'ID de la clave privada',
                'private_key': 'Clave privada RSA',
                'client_email': 'Email de la cuenta de servicio',
                'client_id': 'ID del cliente OAuth2',
                'auth_uri': 'URI de autenticación',
                'token_uri': 'URI de token'
            }
            
            missing_fields = []
            for field, description in required_fields.items():
                if field not in credentials_info or not credentials_info[field]:
                    missing_fields.append(f"{field} ({description})")
            
            if missing_fields:
                print(f"[ERROR] Google Drive: Faltan campos críticos en credenciales:")
                for field in missing_fields:
                    print(f"   ❌ {field}")
                return
            
            print(f"[GOOGLE_DRIVE] [OK] Todos los campos requeridos presentes")
            print(f"   Proyecto: {credentials_info.get('project_id')}")
            print(f"   Email: {credentials_info.get('client_email')}")
            
            # MEJORADO: Crear credenciales con scopes específicos y manejo de errores
            print("[GOOGLE_DRIVE] Creando credenciales de servicio...")
            try:
                scopes = [
                    'https://www.googleapis.com/auth/drive.file',  # Acceso a archivos creados por la app
                    'https://www.googleapis.com/auth/drive'        # Acceso completo a Drive
                ]
                
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=scopes
                )
                print(f"[GOOGLE_DRIVE] [OK] Credenciales creadas con {len(scopes)} scopes")
                
            except Exception as cred_error:
                print(f"[ERROR] Google Drive: Error creando credenciales: {cred_error}")
                print(f"   Tipo: {type(cred_error).__name__}")
                return
            
            # MEJORADO: Crear servicio con mejor manejo de errores
            print("[GOOGLE_DRIVE] Construyendo servicio Drive API v3...")
            try:
                self.service = build('drive', 'v3', credentials=credentials)
                print("[GOOGLE_DRIVE] [OK] Servicio Drive API construido")
            except Exception as service_error:
                print(f"[ERROR] Google Drive: Error construyendo servicio: {service_error}")
                print(f"   Tipo: {type(service_error).__name__}")
                self.service = None
                return
            
            # CRÍTICO: Verificación completa de acceso y permisos
            print("[GOOGLE_DRIVE] [TEST] Ejecutando tests de verificación...")
            
            tests_passed = 0
            total_tests = 3
            
            try:
                # Test 1: Verificación básica de API
                print("[TEST 1] Verificación básica de API...")
                about_info = self.service.about().get(fields='user').execute()
                print(f"[TEST 1] [OK] API accesible - Usuario: {about_info.get('user', {}).get('emailAddress', 'N/A')}")
                tests_passed += 1
                
                # Test 2: Verificación de acceso a carpeta "nuevas"
                print(f"[TEST 2] Verificando acceso a carpeta 'nuevas': {self.folder_nuevas}")
                try:
                    folder_info = self.service.files().get(
                        fileId=self.folder_nuevas,
                        fields='id,name,permissions'
                    ).execute()
                    print(f"[TEST 2] [OK] Carpeta 'nuevas' accesible: {folder_info.get('name', 'Sin nombre')}")
                    tests_passed += 1
                except Exception as folder_error:
                    print(f"[TEST 2] [FAIL] Error accediendo carpeta 'nuevas': {folder_error}")
                    print(f"   ID de carpeta: {self.folder_nuevas}")
                    print(f"   Verificar permisos de la cuenta de servicio")
                
                # Test 3: Verificación de acceso a carpeta "antiguas"
                print(f"[TEST 3] Verificando acceso a carpeta 'antiguas': {self.folder_antiguas}")
                try:
                    folder_info = self.service.files().get(
                        fileId=self.folder_antiguas,
                        fields='id,name'
                    ).execute()
                    print(f"[TEST 3] [OK] Carpeta 'antiguas' accesible: {folder_info.get('name', 'Sin nombre')}")
                    tests_passed += 1
                except Exception as folder_error:
                    print(f"[TEST 3] [WARN] Carpeta 'antiguas' no accesible (no crítico): {folder_error}")
                    tests_passed += 1  # No es crítico para las operaciones principales
                
                # Evaluación final
                print(f"[GOOGLE_DRIVE] Tests completados: {tests_passed}/{total_tests} exitosos")
                
                if tests_passed >= 2:
                    print("[GOOGLE_DRIVE] [SUCCESS] INICIALIZACIÓN EXITOSA")
                    print(f"   Proyecto: {credentials_info.get('project_id')}")
                    print(f"   Email: {credentials_info.get('client_email')}")
                    print(f"   Entorno: {entorno}")
                else:
                    print("[ERROR] Google Drive: Falló verificación mínima")
                    self.service = None
                    
            except Exception as test_error:
                print(f"[ERROR] Google Drive: Error crítico en tests: {test_error}")
                print(f"   Tipo: {type(test_error).__name__}")
                if hasattr(test_error, 'resp'):
                    print(f"   HTTP Status: {test_error.resp.status}")
                    print(f"   HTTP Reason: {test_error.resp.reason}")
                self.service = None
            
        except Exception as e:
            print(f"[ERROR] Google Drive: Error crítico durante inicialización: {e}")
            print(f"   Tipo de error: {type(e).__name__}")
            print(f"   Entorno: {entorno}")
            
            # Log adicional para debugging en producción
            if es_render:
                print("[DEBUG RENDER] Información adicional para Render:")
                print(f"   Variables de entorno Drive configuradas: {bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))}")
                print(f"   Carpeta nuevas configurada: {bool(self.folder_nuevas)}")
                print(f"   Carpeta antiguas configurada: {bool(self.folder_antiguas)}")
            
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
            print(f"[SEARCH] Google Drive: Buscando PDFs con query: '{query}'")
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

                # PAGINACIÓN: Obtener TODOS los archivos iterando sobre páginas
                page_token = None
                files_carpeta = []

                while True:
                    # Ejecutar búsqueda con paginación
                    results = self.service.files().list(
                        q=search_query,
                        pageSize=1000,  # Máximo permitido por Google Drive API
                        pageToken=page_token,
                        fields="nextPageToken, files(id, name, size, modifiedTime, parents)"
                    ).execute()

                    files_pagina = results.get('files', [])
                    files_carpeta.extend(files_pagina)

                    print(f"   [PAGE] {nombre_carpeta}: +{len(files_pagina)} archivos (total parcial: {len(files_carpeta)})")

                    # Verificar si hay más páginas
                    page_token = results.get('nextPageToken')
                    if not page_token:
                        break  # No hay más páginas

                print(f"   [FILES] {nombre_carpeta}: {len(files_carpeta)} archivos encontrados en total")

                # Agregar información de la carpeta a cada archivo
                for file in files_carpeta:
                    file['carpeta_origen'] = nombre_carpeta
                    all_files.append(file)
            
            print(f"[TOTAL] Google Drive: Total de archivos - {len(all_files)}")
            
            # Formatear resultados
            pdfs = []
            for file in all_files:  # Usar all_files en lugar de files
                nombre_archivo = file['name']
                carpeta = file.get('carpeta_origen', 'desconocida')
                print(f"   [PDF] Archivo encontrado: {nombre_archivo} (ID: {file['id']}) en {carpeta}")
                
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
            print(f"[DOWNLOAD] Google Drive: Iniciando descarga de '{nombre_archivo}'")
            
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
            print(f"[DOWNLOAD_ID] Google Drive: Descargando por ID: {file_id} (nombre: {nombre_archivo})")
            
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