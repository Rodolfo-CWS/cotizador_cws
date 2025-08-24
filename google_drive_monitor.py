#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOOGLE DRIVE ADMIN FOLDER MONITOR
=================================

Sistema de monitoreo avanzado para la carpeta "Mi unidad\CWS\CWS_Cotizaciones_PDF\antiguas"
donde el administrador sube PDFs históricos manualmente.

Características:
- Detección en tiempo real de nuevos PDFs
- Indexación automática de metadatos
- Integración con sistema de búsqueda unificado
- Cache de estructura de carpetas
- Webhook simulation para cambios
- Procesamiento en lotes
- Recuperación de errores
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import re

# Para análisis de texto en PDFs
try:
    import PyPDF2
    PDF_TEXT_EXTRACTION = True
except ImportError:
    PDF_TEXT_EXTRACTION = False
    logging.warning("PyPDF2 no disponible - extracción de texto de PDFs deshabilitada")

logger = logging.getLogger(__name__)

class FileChangeType(Enum):
    """Tipos de cambios en archivos"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"

class ProcessingStatus(Enum):
    """Estados de procesamiento"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class DriveFileInfo:
    """Información de archivo en Google Drive"""
    file_id: str
    name: str
    size: int
    modified_time: datetime
    created_time: datetime
    md5_checksum: str = ""
    mime_type: str = ""
    parent_folder: str = ""
    folder_name: str = ""
    web_view_link: str = ""
    download_link: str = ""

@dataclass
class FileChangeEvent:
    """Evento de cambio de archivo"""
    event_id: str
    file_info: DriveFileInfo
    change_type: FileChangeType
    detected_at: datetime
    processed_at: Optional[datetime] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"change_{int(time.time())}_{hash(self.file_info.file_id)}"

@dataclass
class PDFMetadata:
    """Metadatos extraídos de PDF"""
    numero_cotizacion: str
    titulo: str = ""
    autor: str = ""
    creador: str = ""
    fecha_creacion: Optional[datetime] = None
    numero_paginas: int = 0
    texto_extraido: str = ""
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []

class GoogleDriveMonitor:
    """Monitor avanzado de carpeta de Google Drive del administrador"""
    
    def __init__(self, storage_manager):
        """Inicializar monitor de Google Drive"""
        self.storage_manager = storage_manager
        
        # Estado del monitor
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_sync_time = None
        
        # Cache de archivos conocidos
        self.known_files: Dict[str, DriveFileInfo] = {}
        self.file_checksums: Dict[str, str] = {}
        
        # Cola de eventos
        self.change_events: List[FileChangeEvent] = []
        self.processed_events: List[FileChangeEvent] = []
        
        # Configuración
        self.config = {
            "monitor_interval_seconds": int(os.getenv('DRIVE_MONITOR_INTERVAL', '300')),  # 5 min
            "admin_folder_id": os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS', '1GqM9yfwUKd9n8nN97IUiBSUrWUZ1Vida'),
            "enable_text_extraction": os.getenv('ENABLE_PDF_TEXT_EXTRACTION', 'true').lower() == 'true' and PDF_TEXT_EXTRACTION,
            "max_file_size_mb": int(os.getenv('MAX_PDF_SIZE_MB', '50')),
            "enable_batch_processing": os.getenv('ENABLE_BATCH_PROCESSING', 'true').lower() == 'true',
            "batch_size": int(os.getenv('BATCH_SIZE', '10')),
            "enable_webhook_simulation": os.getenv('ENABLE_WEBHOOK_SIMULATION', 'true').lower() == 'true'
        }
        
        # Archivos de persistencia
        self.cache_file = Path("drive_monitor_cache.json")
        self.events_file = Path("drive_monitor_events.json")
        
        # Estadísticas
        self.stats = {
            "files_monitored": 0,
            "changes_detected": 0,
            "files_processed": 0,
            "processing_errors": 0,
            "last_scan_duration_ms": 0,
            "total_scan_time_ms": 0,
            "uptime_start": datetime.now()
        }
        
        # Patrones de nombres de archivo
        self.filename_patterns = [
            r'^(.+)\.pdf$',  # Cualquier PDF
            r'^[Cc]otizaci[oó]n[_\s](.+)\.pdf$',  # Con prefijo "Cotización"
            r'^([A-Z0-9\-_]+)\.pdf$',  # Formato código
            r'^(.+)[_\s][Rr](\d+)\.pdf$',  # Con revisión
        ]
        
        # Cargar estado persistente
        self._load_persistent_state()
        
        logger.info("👀 [DRIVE_MONITOR] Monitor de Google Drive iniciado")
        logger.info(f"   Carpeta objetivo: {self.config['admin_folder_id']}")
        logger.info(f"   Intervalo: {self.config['monitor_interval_seconds']}s")
        logger.info(f"   Extracción de texto: {'Habilitada' if self.config['enable_text_extraction'] else 'Deshabilitada'}")
    
    def start_monitoring(self):
        """Iniciar monitoreo de la carpeta"""
        if self.is_monitoring:
            logger.warning("⚠️ [DRIVE_MONITOR] Monitor ya está ejecutándose")
            return
        
        if not self.storage_manager.google_drive.is_available():
            logger.error("❌ [DRIVE_MONITOR] Google Drive no disponible")
            return
        
        logger.info("🚀 [DRIVE_MONITOR] Iniciando monitoreo...")
        
        # Escaneo inicial
        try:
            initial_scan_result = self._perform_full_scan()
            logger.info(f"📊 [DRIVE_MONITOR] Escaneo inicial: {initial_scan_result['files_found']} archivos")
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error en escaneo inicial: {e}")
        
        # Iniciar hilo de monitoreo
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("✅ [DRIVE_MONITOR] Monitoreo iniciado")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        logger.info("🛑 [DRIVE_MONITOR] Deteniendo monitoreo...")
        
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        # Procesar eventos pendientes
        if self.change_events:
            logger.info(f"⏳ [DRIVE_MONITOR] Procesando {len(self.change_events)} eventos pendientes...")
            self._process_pending_events()
        
        # Guardar estado
        self._save_persistent_state()
        
        logger.info("✅ [DRIVE_MONITOR] Monitor detenido correctamente")
    
    def _monitor_loop(self):
        """Bucle principal de monitoreo"""
        logger.info("🔄 [DRIVE_MONITOR] Bucle de monitoreo iniciado")
        
        while self.is_monitoring:
            try:
                start_time = time.time()
                
                # Buscar cambios
                changes = self._detect_changes()
                
                if changes:
                    logger.info(f"📄 [DRIVE_MONITOR] {len(changes)} cambios detectados")
                    
                    # Procesar cambios
                    if self.config['enable_batch_processing']:
                        self._process_changes_batch(changes)
                    else:
                        self._process_changes_sequential(changes)
                
                # Procesar eventos pendientes
                if self.change_events:
                    self._process_pending_events()
                
                # Actualizar estadísticas
                scan_time_ms = int((time.time() - start_time) * 1000)
                self.stats["last_scan_duration_ms"] = scan_time_ms
                self.stats["total_scan_time_ms"] += scan_time_ms
                
                # Esperar hasta el próximo escaneo
                time.sleep(self.config['monitor_interval_seconds'])
                
            except Exception as e:
                logger.error(f"❌ [DRIVE_MONITOR] Error en bucle de monitoreo: {e}")
                time.sleep(60)  # Esperar 1 minuto en caso de error
        
        logger.info("🛑 [DRIVE_MONITOR] Bucle de monitoreo detenido")
    
    def _perform_full_scan(self) -> Dict:
        """Realizar escaneo completo de la carpeta"""
        try:
            logger.info("🔍 [DRIVE_MONITOR] Iniciando escaneo completo...")
            
            # Buscar todos los PDFs en la carpeta admin
            query = f"'{self.config['admin_folder_id']}' in parents and mimeType='application/pdf' and trashed=false"
            
            results = self.storage_manager.google_drive.service.files().list(
                q=query,
                fields="files(id,name,size,modifiedTime,createdTime,md5Checksum,mimeType,parents,webViewLink)",
                pageSize=1000  # Obtener hasta 1000 archivos
            ).execute()
            
            files = results.get('files', [])
            new_files = []
            updated_files = []
            
            current_file_ids = set()
            
            for file_data in files:
                file_info = self._parse_drive_file(file_data)
                current_file_ids.add(file_info.file_id)
                
                if file_info.file_id not in self.known_files:
                    # Archivo nuevo
                    new_files.append(file_info)
                    self.known_files[file_info.file_id] = file_info
                    
                else:
                    # Verificar si cambió
                    known_file = self.known_files[file_info.file_id]
                    if (file_info.modified_time > known_file.modified_time or 
                        file_info.md5_checksum != known_file.md5_checksum):
                        updated_files.append(file_info)
                        self.known_files[file_info.file_id] = file_info
            
            # Detectar archivos eliminados
            deleted_file_ids = set(self.known_files.keys()) - current_file_ids
            deleted_files = [self.known_files[fid] for fid in deleted_file_ids]
            
            # Remover archivos eliminados del cache
            for fid in deleted_file_ids:
                del self.known_files[fid]
            
            # Crear eventos para archivos nuevos y modificados
            for file_info in new_files:
                event = FileChangeEvent(
                    event_id="",
                    file_info=file_info,
                    change_type=FileChangeType.ADDED,
                    detected_at=datetime.now()
                )
                self.change_events.append(event)
            
            for file_info in updated_files:
                event = FileChangeEvent(
                    event_id="",
                    file_info=file_info,
                    change_type=FileChangeType.MODIFIED,
                    detected_at=datetime.now()
                )
                self.change_events.append(event)
            
            for file_info in deleted_files:
                event = FileChangeEvent(
                    event_id="",
                    file_info=file_info,
                    change_type=FileChangeType.DELETED,
                    detected_at=datetime.now()
                )
                self.change_events.append(event)
            
            # Actualizar estadísticas
            self.stats["files_monitored"] = len(self.known_files)
            self.stats["changes_detected"] += len(new_files) + len(updated_files) + len(deleted_files)
            
            result = {
                "files_found": len(files),
                "new_files": len(new_files),
                "updated_files": len(updated_files),
                "deleted_files": len(deleted_files),
                "total_changes": len(new_files) + len(updated_files) + len(deleted_files)
            }
            
            logger.info(f"✅ [DRIVE_MONITOR] Escaneo completo: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error en escaneo completo: {e}")
            return {"error": str(e)}
    
    def _detect_changes(self) -> List[FileChangeEvent]:
        """Detectar cambios desde el último escaneo"""
        try:
            # Si es el primer escaneo, usar escaneo completo
            if not self.last_sync_time:
                full_scan = self._perform_full_scan()
                self.last_sync_time = datetime.now()
                return self.change_events[-full_scan.get('total_changes', 0):]
            
            # Buscar archivos modificados desde el último escaneo
            since_time = self.last_sync_time.isoformat() + 'Z'
            query = f"'{self.config['admin_folder_id']}' in parents and mimeType='application/pdf' and modifiedTime > '{since_time}' and trashed=false"
            
            results = self.storage_manager.google_drive.service.files().list(
                q=query,
                fields="files(id,name,size,modifiedTime,createdTime,md5Checksum,mimeType,parents,webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            changes = []
            
            for file_data in files:
                file_info = self._parse_drive_file(file_data)
                
                # Determinar tipo de cambio
                if file_info.file_id not in self.known_files:
                    change_type = FileChangeType.ADDED
                else:
                    change_type = FileChangeType.MODIFIED
                
                event = FileChangeEvent(
                    event_id="",
                    file_info=file_info,
                    change_type=change_type,
                    detected_at=datetime.now()
                )
                changes.append(event)
                
                # Actualizar cache
                self.known_files[file_info.file_id] = file_info
            
            self.last_sync_time = datetime.now()
            
            return changes
            
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error detectando cambios: {e}")
            return []
    
    def _parse_drive_file(self, file_data: Dict) -> DriveFileInfo:
        """Parsear información de archivo de Google Drive"""
        return DriveFileInfo(
            file_id=file_data.get('id', ''),
            name=file_data.get('name', ''),
            size=int(file_data.get('size', '0')),
            modified_time=self._parse_drive_time(file_data.get('modifiedTime')),
            created_time=self._parse_drive_time(file_data.get('createdTime')),
            md5_checksum=file_data.get('md5Checksum', ''),
            mime_type=file_data.get('mimeType', ''),
            parent_folder=self.config['admin_folder_id'],
            folder_name="antiguas",
            web_view_link=file_data.get('webViewLink', ''),
            download_link=f"https://drive.google.com/uc?id={file_data.get('id', '')}"
        )
    
    def _parse_drive_time(self, time_str: str) -> datetime:
        """Parsear timestamp de Google Drive"""
        if not time_str:
            return datetime.now()
        
        try:
            # Formato: 2024-01-15T10:30:45.123Z
            return datetime.fromisoformat(time_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except:
            return datetime.now()
    
    def _process_changes_batch(self, changes: List[FileChangeEvent]):
        """Procesar cambios en lotes"""
        try:
            logger.info(f"📦 [DRIVE_MONITOR] Procesando {len(changes)} cambios en lotes...")
            
            # Dividir en lotes
            batch_size = self.config['batch_size']
            batches = [changes[i:i + batch_size] for i in range(0, len(changes), batch_size)]
            
            for batch_index, batch in enumerate(batches):
                logger.info(f"🔄 [DRIVE_MONITOR] Procesando lote {batch_index + 1}/{len(batches)}")
                
                for event in batch:
                    self._process_single_event(event)
                    self.change_events.append(event)
                
                # Pausa entre lotes para no sobrecargar APIs
                if batch_index < len(batches) - 1:
                    time.sleep(2)
            
            logger.info(f"✅ [DRIVE_MONITOR] {len(changes)} cambios procesados en lotes")
            
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error procesando lotes: {e}")
    
    def _process_changes_sequential(self, changes: List[FileChangeEvent]):
        """Procesar cambios secuencialmente"""
        try:
            logger.info(f"📝 [DRIVE_MONITOR] Procesando {len(changes)} cambios secuencialmente...")
            
            for event in changes:
                self._process_single_event(event)
                self.change_events.append(event)
            
            logger.info(f"✅ [DRIVE_MONITOR] {len(changes)} cambios procesados")
            
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error procesando secuencialmente: {e}")
    
    def _process_single_event(self, event: FileChangeEvent) -> bool:
        """Procesar un evento individual"""
        try:
            event.processing_status = ProcessingStatus.PROCESSING
            event.processed_at = datetime.now()
            
            logger.info(f"🔧 [DRIVE_MONITOR] Procesando: {event.file_info.name} ({event.change_type.value})")
            
            if event.change_type == FileChangeType.ADDED or event.change_type == FileChangeType.MODIFIED:
                success = self._process_new_or_modified_file(event)
            elif event.change_type == FileChangeType.DELETED:
                success = self._process_deleted_file(event)
            else:
                logger.warning(f"⚠️ [DRIVE_MONITOR] Tipo de cambio no soportado: {event.change_type}")
                success = False
            
            if success:
                event.processing_status = ProcessingStatus.COMPLETED
                self.stats["files_processed"] += 1
                logger.info(f"✅ [DRIVE_MONITOR] Procesado exitosamente: {event.file_info.name}")
            else:
                event.processing_status = ProcessingStatus.FAILED
                event.retry_count += 1
                self.stats["processing_errors"] += 1
                logger.error(f"❌ [DRIVE_MONITOR] Error procesando: {event.file_info.name}")
            
            return success
            
        except Exception as e:
            event.processing_status = ProcessingStatus.FAILED
            event.error_message = str(e)
            event.retry_count += 1
            self.stats["processing_errors"] += 1
            
            logger.error(f"❌ [DRIVE_MONITOR] Excepción procesando {event.file_info.name}: {e}")
            return False
    
    def _process_new_or_modified_file(self, event: FileChangeEvent) -> bool:
        """Procesar archivo nuevo o modificado"""
        try:
            file_info = event.file_info
            
            # Verificar tamaño
            size_mb = file_info.size / (1024 * 1024)
            if size_mb > self.config['max_file_size_mb']:
                logger.warning(f"⚠️ [DRIVE_MONITOR] Archivo demasiado grande ({size_mb:.1f}MB): {file_info.name}")
                event.processing_status = ProcessingStatus.SKIPPED
                return True
            
            # Extraer número de cotización del nombre del archivo
            numero_cotizacion = self._extract_cotizacion_number(file_info.name)
            
            # Extraer metadatos del PDF si está habilitado
            pdf_metadata = None
            if self.config['enable_text_extraction']:
                try:
                    pdf_metadata = self._extract_pdf_metadata(file_info)
                except Exception as e:
                    logger.warning(f"⚠️ [DRIVE_MONITOR] Error extrayendo metadatos PDF: {e}")
            
            # Crear registro de cotización histórica
            cotizacion_data = {
                "numeroCotizacion": numero_cotizacion,
                "datosGenerales": {
                    "cliente": "Google Drive (Histórico)",
                    "vendedor": "Administrador",
                    "proyecto": numero_cotizacion,
                    "fecha": file_info.created_time.strftime('%Y-%m-%d') if file_info.created_time else datetime.now().strftime('%Y-%m-%d'),
                    "atencionA": "Sistema Automático",
                    "contacto": "drive-monitor@cws.com"
                },
                "items": [],
                "revision": 1,
                "observaciones": f"PDF histórico importado automáticamente desde Google Drive. Archivo: {file_info.name}",
                "origen": "google_drive_admin_monitor",
                "fechaCreacion": datetime.now().isoformat(),
                "timestamp": int(time.time() * 1000),
                "metadata_pdf": asdict(pdf_metadata) if pdf_metadata else None,
                "drive_file_info": {
                    "file_id": file_info.file_id,
                    "web_view_link": file_info.web_view_link,
                    "download_link": file_info.download_link,
                    "size_bytes": file_info.size,
                    "md5_checksum": file_info.md5_checksum
                }
            }
            
            # Guardar cotización en sistema unificado
            save_result = self.storage_manager.guardar_cotizacion(cotizacion_data)
            
            if not save_result.success:
                logger.error(f"❌ [DRIVE_MONITOR] Error guardando cotización: {save_result.error}")
                return False
            
            # Opcional: Descargar y almacenar PDF en sistemas locales
            try:
                pdf_content = self.storage_manager.google_drive.obtener_pdf_por_id(
                    file_info.file_id, 
                    file_info.name
                )
                
                if pdf_content:
                    pdf_result = self.storage_manager.guardar_pdf(pdf_content, cotizacion_data)
                    if pdf_result.success:
                        logger.info(f"📄 [DRIVE_MONITOR] PDF almacenado en sistemas locales: {file_info.name}")
                    else:
                        logger.warning(f"⚠️ [DRIVE_MONITOR] Error almacenando PDF localmente: {pdf_result.error}")
                        
            except Exception as e:
                logger.warning(f"⚠️ [DRIVE_MONITOR] Error descargando PDF: {e}")
            
            # Notificar al sistema de sincronización
            if hasattr(self.storage_manager, 'sync_system'):
                self.storage_manager.sync_system.add_sync_operation(
                    source="drive_admin",
                    target="unified_search",
                    operation_type="index",
                    data={
                        "numero_cotizacion": numero_cotizacion,
                        "file_info": asdict(file_info),
                        "metadata": asdict(pdf_metadata) if pdf_metadata else None
                    },
                    priority=3  # Prioridad media para indexación
                )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error procesando archivo: {e}")
            return False
    
    def _process_deleted_file(self, event: FileChangeEvent) -> bool:
        """Procesar archivo eliminado"""
        try:
            file_info = event.file_info
            numero_cotizacion = self._extract_cotizacion_number(file_info.name)
            
            logger.info(f"🗑️ [DRIVE_MONITOR] Archivo eliminado: {file_info.name}")
            
            # Marcar como eliminado en el sistema (opcional)
            # Por ahora solo registrar el evento
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error procesando eliminación: {e}")
            return False
    
    def _extract_cotizacion_number(self, filename: str) -> str:
        """Extraer número de cotización del nombre del archivo"""
        # Remover extensión
        name_without_ext = filename.replace('.pdf', '').replace('.PDF', '')
        
        # Intentar diferentes patrones
        patterns = [
            r'^[Cc]otizaci[oó]n[_\s]*(.+)$',  # "Cotización NUMERO"
            r'^(.+)[_\s]*[Cc]otizaci[oó]n$',  # "NUMERO Cotización"
            r'^([A-Z0-9\-_]+)$',  # Formato código directo
            r'^(.+?)(?:\s*-\s*R\d+)?$',  # Con revisión opcional
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name_without_ext.strip())
            if match:
                numero = match.group(1).strip()
                if numero and len(numero) > 2:  # Mínimo 3 caracteres
                    return numero
        
        # Fallback: usar el nombre completo sin extensión
        return name_without_ext.strip() or f"DRIVE_{int(time.time())}"
    
    def _extract_pdf_metadata(self, file_info: DriveFileInfo) -> PDFMetadata:
        """Extraer metadatos de PDF"""
        if not PDF_TEXT_EXTRACTION:
            return PDFMetadata(numero_cotizacion=self._extract_cotizacion_number(file_info.name))
        
        try:
            # Descargar PDF temporalmente
            pdf_content = self.storage_manager.google_drive.obtener_pdf_por_id(
                file_info.file_id,
                file_info.name
            )
            
            if not pdf_content:
                return PDFMetadata(numero_cotizacion=self._extract_cotizacion_number(file_info.name))
            
            # Crear objeto PDF
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            
            # Extraer información básica
            num_pages = len(pdf_reader.pages)
            
            # Metadatos del documento
            metadata = pdf_reader.metadata if pdf_reader.metadata else {}
            
            titulo = metadata.get('/Title', file_info.name) if metadata else file_info.name
            autor = metadata.get('/Author', '') if metadata else ''
            creador = metadata.get('/Creator', '') if metadata else ''
            
            # Extraer texto de las primeras páginas
            texto_extraido = ""
            max_pages_to_extract = min(3, num_pages)  # Solo primeras 3 páginas
            
            for page_num in range(max_pages_to_extract):
                try:
                    page = pdf_reader.pages[page_num]
                    texto_extraido += page.extract_text() + "\n"
                except Exception as e:
                    logger.debug(f"Error extrayendo texto de página {page_num}: {e}")
            
            # Extraer palabras clave del texto
            keywords = self._extract_keywords_from_text(texto_extraido)
            
            return PDFMetadata(
                numero_cotizacion=self._extract_cotizacion_number(file_info.name),
                titulo=titulo,
                autor=autor,
                creador=creador,
                fecha_creacion=file_info.created_time,
                numero_paginas=num_pages,
                texto_extraido=texto_extraido[:1000],  # Limitar tamaño
                keywords=keywords
            )
            
        except Exception as e:
            logger.error(f"❌ [PDF_METADATA] Error extrayendo metadatos: {e}")
            return PDFMetadata(numero_cotizacion=self._extract_cotizacion_number(file_info.name))
    
    def _extract_keywords_from_text(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extraer palabras clave del texto"""
        if not text or len(text.strip()) < 10:
            return []
        
        # Limpiar texto
        import re
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = cleaned_text.split()
        
        # Filtrar palabras comunes en español
        stop_words = {
            'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 
            'da', 'su', 'por', 'son', 'con', 'no', 'me', 'una', 'ti', 'al', 'del', 'las',
            'cotización', 'cliente', 'proyecto', 'precio', 'total', 'subtotal', 'iva'
        }
        
        # Contar frecuencia de palabras
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Ordenar por frecuencia y tomar las más comunes
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:max_keywords] if freq > 1]
        
        return keywords
    
    def _process_pending_events(self):
        """Procesar eventos pendientes"""
        pending = [e for e in self.change_events if e.processing_status == ProcessingStatus.PENDING]
        
        if not pending:
            return
        
        logger.info(f"⏳ [DRIVE_MONITOR] Procesando {len(pending)} eventos pendientes...")
        
        for event in pending:
            if event.retry_count >= event.max_retries:
                event.processing_status = ProcessingStatus.FAILED
                continue
            
            success = self._process_single_event(event)
            
            if success or event.retry_count >= event.max_retries:
                # Mover a procesados
                self.processed_events.append(event)
                self.change_events.remove(event)
    
    def _load_persistent_state(self):
        """Cargar estado persistente"""
        try:
            # Cargar cache de archivos
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                self.known_files = {}
                for file_id, file_data in cache_data.get('known_files', {}).items():
                    self.known_files[file_id] = DriveFileInfo(
                        file_id=file_data['file_id'],
                        name=file_data['name'],
                        size=file_data['size'],
                        modified_time=datetime.fromisoformat(file_data['modified_time']),
                        created_time=datetime.fromisoformat(file_data['created_time']),
                        md5_checksum=file_data.get('md5_checksum', ''),
                        mime_type=file_data.get('mime_type', ''),
                        parent_folder=file_data.get('parent_folder', ''),
                        folder_name=file_data.get('folder_name', ''),
                        web_view_link=file_data.get('web_view_link', ''),
                        download_link=file_data.get('download_link', '')
                    )
                
                self.last_sync_time = None
                if cache_data.get('last_sync_time'):
                    self.last_sync_time = datetime.fromisoformat(cache_data['last_sync_time'])
                
                logger.info(f"📂 [DRIVE_MONITOR] {len(self.known_files)} archivos cargados del cache")
            
            # Cargar eventos
            if self.events_file.exists():
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    events_data = json.load(f)
                
                # Cargar solo eventos no completados
                for event_data in events_data.get('pending_events', []):
                    file_info = DriveFileInfo(**event_data['file_info'])
                    event = FileChangeEvent(
                        event_id=event_data['event_id'],
                        file_info=file_info,
                        change_type=FileChangeType(event_data['change_type']),
                        detected_at=datetime.fromisoformat(event_data['detected_at']),
                        processed_at=datetime.fromisoformat(event_data['processed_at']) if event_data.get('processed_at') else None,
                        processing_status=ProcessingStatus(event_data['processing_status']),
                        error_message=event_data.get('error_message', ''),
                        retry_count=event_data.get('retry_count', 0)
                    )
                    
                    if event.processing_status != ProcessingStatus.COMPLETED:
                        self.change_events.append(event)
                
                logger.info(f"⏳ [DRIVE_MONITOR] {len(self.change_events)} eventos pendientes cargados")
                
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error cargando estado persistente: {e}")
    
    def _save_persistent_state(self):
        """Guardar estado persistente"""
        try:
            # Guardar cache de archivos
            cache_data = {
                'known_files': {},
                'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None
            }
            
            for file_id, file_info in self.known_files.items():
                cache_data['known_files'][file_id] = {
                    'file_id': file_info.file_id,
                    'name': file_info.name,
                    'size': file_info.size,
                    'modified_time': file_info.modified_time.isoformat(),
                    'created_time': file_info.created_time.isoformat(),
                    'md5_checksum': file_info.md5_checksum,
                    'mime_type': file_info.mime_type,
                    'parent_folder': file_info.parent_folder,
                    'folder_name': file_info.folder_name,
                    'web_view_link': file_info.web_view_link,
                    'download_link': file_info.download_link
                }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # Guardar eventos pendientes
            events_data = {
                'pending_events': []
            }
            
            for event in self.change_events:
                if event.processing_status != ProcessingStatus.COMPLETED:
                    events_data['pending_events'].append({
                        'event_id': event.event_id,
                        'file_info': asdict(event.file_info),
                        'change_type': event.change_type.value,
                        'detected_at': event.detected_at.isoformat(),
                        'processed_at': event.processed_at.isoformat() if event.processed_at else None,
                        'processing_status': event.processing_status.value,
                        'error_message': event.error_message,
                        'retry_count': event.retry_count
                    })
            
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ [DRIVE_MONITOR] Error guardando estado persistente: {e}")
    
    def get_monitor_status(self) -> Dict:
        """Obtener estado del monitor"""
        uptime = datetime.now() - self.stats["uptime_start"]
        
        return {
            "is_monitoring": self.is_monitoring,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "files_monitored": len(self.known_files),
            "pending_events": len([e for e in self.change_events if e.processing_status == ProcessingStatus.PENDING]),
            "failed_events": len([e for e in self.change_events if e.processing_status == ProcessingStatus.FAILED]),
            "completed_events": len(self.processed_events),
            "statistics": {
                **self.stats,
                "uptime_seconds": uptime.total_seconds(),
                "uptime_formatted": str(uptime).split('.')[0]
            },
            "configuration": self.config
        }
    
    def force_full_scan(self) -> Dict:
        """Forzar escaneo completo manual"""
        logger.info("⚡ [DRIVE_MONITOR] Iniciando escaneo completo forzado...")
        return self._perform_full_scan()


if __name__ == "__main__":
    # Test del monitor
    from unified_storage_manager import UnifiedStorageManager
    
    storage_manager = UnifiedStorageManager()
    monitor = GoogleDriveMonitor(storage_manager)
    
    # Mostrar estado
    status = monitor.get_monitor_status()
    print(json.dumps(status, indent=2, default=str))
    
    # Forzar escaneo
    if storage_manager.google_drive.is_available():
        scan_result = monitor.force_full_scan()
        print(f"Escaneo forzado: {scan_result}")
    else:
        print("Google Drive no disponible para test")