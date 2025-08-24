#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENHANCED SYNCHRONIZATION SYSTEM
================================

Sistema avanzado de sincronización con:
- Cola de operaciones con prioridades
- Sincronización inteligente (solo cambios incrementales)  
- Monitoreo de Google Drive para PDFs del administrador
- Detección automática de conflictos
- Recuperación automática de fallos
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class SyncStatus(Enum):
    """Estados de sincronización"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"  
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    CANCELLED = "cancelled"

class ConflictResolution(Enum):
    """Estrategias de resolución de conflictos"""
    LAST_WRITE_WINS = "last_write_wins"
    MANUAL_REVIEW = "manual_review"
    MERGE_FIELDS = "merge_fields"
    KEEP_BOTH = "keep_both"

@dataclass
class SyncOperation:
    """Operación de sincronización"""
    id: str
    source: str
    target: str
    operation_type: str  # create, update, delete
    data: Dict
    checksum: str
    priority: int = 5  # 1=alta, 5=baja
    created_at: datetime = None
    updated_at: datetime = None
    status: SyncStatus = SyncStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass  
class SyncConflict:
    """Conflicto de sincronización"""
    id: str
    operation_id: str
    source_data: Dict
    target_data: Dict
    conflict_fields: List[str]
    resolution_strategy: ConflictResolution
    resolved: bool = False
    resolution_data: Dict = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class GoogleDriveChange:
    """Cambio detectado en Google Drive"""
    file_id: str
    file_name: str
    change_type: str  # added, modified, deleted
    folder: str  # nuevas, antiguas
    detected_at: datetime
    processed: bool = False
    
class EnhancedSyncSystem:
    """Sistema avanzado de sincronización multi-dirección"""
    
    def __init__(self, storage_manager):
        """Inicializar sistema de sincronización"""
        self.storage_manager = storage_manager
        
        # Colas de operaciones
        self.sync_queue: List[SyncOperation] = []
        self.conflict_queue: List[SyncConflict] = []
        self.completed_operations: List[SyncOperation] = []
        
        # Control de estado
        self.is_syncing = False
        self.sync_thread = None
        self.monitoring_thread = None
        self.is_monitoring_drive = False
        
        # Archivos de persistencia
        self.queue_file = Path("sync_queue.json")
        self.conflicts_file = Path("sync_conflicts.json")
        self.sync_log_file = Path("sync_operations.log")
        
        # Configuración
        self.config = {
            "sync_interval_seconds": int(os.getenv('SYNC_INTERVAL_SECONDS', '900')),  # 15 min
            "drive_monitor_interval": int(os.getenv('DRIVE_MONITOR_INTERVAL', '300')), # 5 min
            "max_queue_size": int(os.getenv('MAX_SYNC_QUEUE_SIZE', '1000')),
            "enable_incremental_sync": os.getenv('ENABLE_INCREMENTAL_SYNC', 'true').lower() == 'true',
            "conflict_resolution": ConflictResolution(os.getenv('CONFLICT_RESOLUTION', 'last_write_wins')),
            "enable_drive_monitoring": os.getenv('ENABLE_DRIVE_MONITORING', 'true').lower() == 'true'
        }
        
        # Estado del último sync
        self.last_sync_times = {
            "supabase_to_json": None,
            "json_to_supabase": None,
            "drive_monitor": None
        }
        
        # Cargar estado persistente
        self._load_persistent_state()
        
        logger.info("🔄 [ENHANCED_SYNC] Sistema avanzado de sincronización iniciado")
        logger.info(f"   Intervalo: {self.config['sync_interval_seconds']}s")
        logger.info(f"   Monitoreo Drive: {'Habilitado' if self.config['enable_drive_monitoring'] else 'Deshabilitado'}")
        logger.info(f"   Sync incremental: {'Habilitado' if self.config['enable_incremental_sync'] else 'Deshabilitado'}")
    
    def start_sync_system(self):
        """Iniciar el sistema de sincronización"""
        if self.is_syncing:
            logger.warning("⚠️ [SYNC] Sistema ya está ejecutándose")
            return
        
        logger.info("🚀 [SYNC] Iniciando sistema de sincronización...")
        
        # Iniciar hilo de sincronización
        self.is_syncing = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        
        # Iniciar monitoreo de Google Drive si está habilitado
        if self.config['enable_drive_monitoring']:
            self._start_drive_monitoring()
        
        logger.info("✅ [SYNC] Sistema de sincronización iniciado")
    
    def stop_sync_system(self):
        """Detener el sistema de sincronización"""
        logger.info("🛑 [SYNC] Deteniendo sistema de sincronización...")
        
        self.is_syncing = False
        self.is_monitoring_drive = False
        
        # Esperar a que terminen los hilos
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=10)
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        # Guardar estado
        self._save_persistent_state()
        
        logger.info("✅ [SYNC] Sistema detenido correctamente")
    
    def add_sync_operation(self, source: str, target: str, operation_type: str, 
                          data: Dict, priority: int = 5) -> str:
        """Agregar operación a la cola de sincronización"""
        
        # Generar ID y checksum únicos
        operation_id = f"{source}_{target}_{operation_type}_{int(time.time())}_{hash(str(data))}"
        checksum = self._calculate_checksum(data)
        
        operation = SyncOperation(
            id=operation_id,
            source=source,
            target=target, 
            operation_type=operation_type,
            data=data,
            checksum=checksum,
            priority=priority
        )
        
        # Verificar duplicados por checksum
        if any(op.checksum == checksum for op in self.sync_queue):
            logger.debug(f"🔍 [SYNC] Operación duplicada ignorada: {operation_id}")
            return operation_id
        
        # Agregar a cola (ordenado por prioridad)
        self.sync_queue.append(operation)
        self.sync_queue.sort(key=lambda x: (x.priority, x.created_at))
        
        # Limitar tamaño de cola
        if len(self.sync_queue) > self.config['max_queue_size']:
            removed = self.sync_queue.pop()  # Remover el menos prioritario
            logger.warning(f"⚠️ [SYNC] Cola llena, removida operación: {removed.id}")
        
        logger.info(f"➕ [SYNC] Operación agregada: {operation_id} (prioridad: {priority})")
        
        # Guardar estado
        self._save_persistent_state()
        
        return operation_id
    
    def process_sync_queue(self) -> Dict:
        """Procesar cola de sincronización"""
        if not self.sync_queue:
            return {"processed": 0, "failed": 0, "conflicts": 0}
        
        logger.info(f"🔄 [SYNC] Procesando {len(self.sync_queue)} operaciones...")
        
        processed = 0
        failed = 0
        conflicts = 0
        
        # Procesar operaciones por prioridad
        operations_to_process = self.sync_queue.copy()
        
        for operation in operations_to_process:
            try:
                operation.status = SyncStatus.IN_PROGRESS
                operation.updated_at = datetime.now()
                
                result = self._execute_sync_operation(operation)
                
                if result["success"]:
                    operation.status = SyncStatus.COMPLETED
                    self.sync_queue.remove(operation)
                    self.completed_operations.append(operation)
                    processed += 1
                    
                    logger.info(f"✅ [SYNC] {operation.id} completada")
                    
                elif result.get("conflict"):
                    operation.status = SyncStatus.CONFLICT
                    conflict = self._handle_sync_conflict(operation, result["conflict_data"])
                    self.conflict_queue.append(conflict)
                    conflicts += 1
                    
                    logger.warning(f"⚠️ [SYNC] Conflicto detectado en {operation.id}")
                    
                else:
                    operation.retry_count += 1
                    operation.error_message = result.get("error", "Error desconocido")
                    
                    if operation.retry_count >= operation.max_retries:
                        operation.status = SyncStatus.FAILED
                        self.sync_queue.remove(operation)
                        failed += 1
                        logger.error(f"❌ [SYNC] {operation.id} falló permanentemente")
                    else:
                        operation.status = SyncStatus.PENDING
                        logger.warning(f"🔄 [SYNC] {operation.id} reintentará ({operation.retry_count}/{operation.max_retries})")
                
            except Exception as e:
                operation.retry_count += 1
                operation.error_message = str(e)
                operation.status = SyncStatus.FAILED if operation.retry_count >= operation.max_retries else SyncStatus.PENDING
                
                if operation.status == SyncStatus.FAILED:
                    self.sync_queue.remove(operation)
                    failed += 1
                
                logger.error(f"❌ [SYNC] Error procesando {operation.id}: {e}")
        
        # Guardar estado actualizado
        self._save_persistent_state()
        
        result = {"processed": processed, "failed": failed, "conflicts": conflicts}
        logger.info(f"🎯 [SYNC] Resultado: {processed} exitosas, {failed} fallidas, {conflicts} conflictos")
        
        return result
    
    def _execute_sync_operation(self, operation: SyncOperation) -> Dict:
        """Ejecutar una operación de sincronización específica"""
        try:
            source = operation.source
            target = operation.target
            op_type = operation.operation_type
            data = operation.data
            
            logger.debug(f"🔧 [SYNC] Ejecutando: {source} → {target} ({op_type})")
            
            # Sincronización Supabase ↔ JSON
            if source == "supabase" and target == "json":
                return self._sync_supabase_to_json(data, op_type)
            elif source == "json" and target == "supabase":
                return self._sync_json_to_supabase(data, op_type)
            
            # Sincronización de PDFs
            elif source == "cloudinary" and target == "drive":
                return self._sync_pdf_cloudinary_to_drive(data)
            elif source == "drive" and target == "cloudinary":
                return self._sync_pdf_drive_to_cloudinary(data)
            
            # Google Drive → Base de datos (PDFs antiguos del admin)
            elif source == "drive_admin" and target == "database":
                return self._sync_drive_admin_to_database(data)
            
            else:
                return {"success": False, "error": f"Tipo de sincronización no soportado: {source} → {target}"}
                
        except Exception as e:
            logger.error(f"❌ [SYNC] Error ejecutando operación: {e}")
            return {"success": False, "error": str(e)}
    
    def _sync_supabase_to_json(self, data: Dict, operation_type: str) -> Dict:
        """Sincronizar datos de Supabase a JSON local"""
        try:
            # Obtener datos actuales del JSON
            json_data = self.storage_manager.supabase._cargar_datos_offline()
            cotizaciones = json_data.get("cotizaciones", [])
            
            numero_cotizacion = data.get("numeroCotizacion") or data.get("numero_cotizacion")
            
            if operation_type == "create" or operation_type == "update":
                # Buscar si existe
                found_index = None
                for i, cot in enumerate(cotizaciones):
                    if cot.get("numeroCotizacion") == numero_cotizacion:
                        found_index = i
                        break
                
                # Detectar conflicto si existe y hay diferencias
                if found_index is not None and operation_type == "update":
                    existing = cotizaciones[found_index]
                    conflict = self._detect_conflict(existing, data)
                    if conflict:
                        return {"success": False, "conflict": True, "conflict_data": conflict}
                
                # Actualizar o crear
                if found_index is not None:
                    cotizaciones[found_index] = data
                else:
                    cotizaciones.append(data)
                
            elif operation_type == "delete":
                cotizaciones = [cot for cot in cotizaciones if cot.get("numeroCotizacion") != numero_cotizacion]
            
            # Guardar JSON actualizado
            json_data["cotizaciones"] = cotizaciones
            json_data["last_sync_from_supabase"] = datetime.now().isoformat()
            
            success = self.storage_manager.supabase._guardar_datos_offline(json_data)
            
            if success:
                self.last_sync_times["supabase_to_json"] = datetime.now()
            
            return {"success": success}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _sync_json_to_supabase(self, data: Dict, operation_type: str) -> Dict:
        """Sincronizar datos de JSON local a Supabase"""
        try:
            if self.storage_manager.supabase.modo_offline:
                return {"success": False, "error": "Supabase offline"}
            
            numero_cotizacion = data.get("numeroCotizacion")
            
            if operation_type == "create" or operation_type == "update":
                # Verificar conflictos en Supabase
                existing_result = self.storage_manager.supabase.obtener_cotizacion(numero_cotizacion)
                
                if existing_result.get("encontrado") and operation_type == "update":
                    existing = existing_result["item"]
                    conflict = self._detect_conflict(existing, data)
                    if conflict:
                        return {"success": False, "conflict": True, "conflict_data": conflict}
                
                # Guardar en Supabase
                result = self.storage_manager.supabase.guardar_cotizacion(data)
                
                if result.get("success"):
                    self.last_sync_times["json_to_supabase"] = datetime.now()
                
                return {"success": result.get("success", False), "error": result.get("error")}
                
            elif operation_type == "delete":
                # Implementar eliminación en Supabase si es necesario
                return {"success": True, "message": "Delete not implemented yet"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _sync_pdf_cloudinary_to_drive(self, data: Dict) -> Dict:
        """Sincronizar PDF de Cloudinary a Google Drive"""
        # Implementar según necesidades específicas
        return {"success": True, "message": "Cloudinary to Drive sync not implemented yet"}
    
    def _sync_pdf_drive_to_cloudinary(self, data: Dict) -> Dict:
        """Sincronizar PDF de Google Drive a Cloudinary"""
        # Implementar según necesidades específicas
        return {"success": True, "message": "Drive to Cloudinary sync not implemented yet"}
    
    def _sync_drive_admin_to_database(self, data: Dict) -> Dict:
        """Sincronizar PDFs nuevos del administrador desde Google Drive"""
        try:
            file_id = data.get("file_id")
            file_name = data.get("file_name")
            
            # Descargar archivo desde Google Drive
            pdf_content = self.storage_manager.google_drive.obtener_pdf_por_id(file_id, file_name)
            
            if not pdf_content:
                return {"success": False, "error": "No se pudo descargar PDF de Google Drive"}
            
            # Crear registro de cotización para el PDF histórico
            numero_cotizacion = file_name.replace('.pdf', '').replace('Cotizacion_', '')
            
            cotizacion_data = {
                "numeroCotizacion": numero_cotizacion,
                "datosGenerales": {
                    "cliente": "Google Drive (Histórico)",
                    "vendedor": "Administrador",
                    "proyecto": numero_cotizacion,
                    "fecha": datetime.now().strftime('%Y-%m-%d')
                },
                "items": [],
                "origen": "google_drive_admin",
                "fechaCreacion": datetime.now().isoformat(),
                "timestamp": int(time.time() * 1000)
            }
            
            # Guardar cotización
            save_result = self.storage_manager.guardar_cotizacion(cotizacion_data)
            
            # Guardar PDF
            if save_result.success:
                pdf_result = self.storage_manager.guardar_pdf(pdf_content, cotizacion_data)
                return {"success": pdf_result.success, "pdf_result": pdf_result.data}
            
            return {"success": save_result.success, "error": save_result.error}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _detect_conflict(self, existing_data: Dict, new_data: Dict) -> Optional[Dict]:
        """Detectar conflictos entre datos existentes y nuevos"""
        conflicts = {}
        
        # Comparar timestamps si están disponibles
        existing_timestamp = existing_data.get("timestamp", 0)
        new_timestamp = new_data.get("timestamp", 0)
        
        # Si el timestamp nuevo es menor, hay conflicto potencial
        if existing_timestamp > new_timestamp:
            conflicts["timestamp"] = {
                "existing": existing_timestamp,
                "new": new_timestamp,
                "message": "Datos nuevos son más antiguos que los existentes"
            }
        
        # Comparar campos específicos que pueden cambiar
        fields_to_check = ["datosGenerales", "items", "revision", "observaciones"]
        
        for field in fields_to_check:
            if field in existing_data and field in new_data:
                if existing_data[field] != new_data[field]:
                    conflicts[field] = {
                        "existing": existing_data[field],
                        "new": new_data[field],
                        "message": f"Campo {field} tiene diferencias"
                    }
        
        return conflicts if conflicts else None
    
    def _handle_sync_conflict(self, operation: SyncOperation, conflict_data: Dict) -> SyncConflict:
        """Manejar conflicto de sincronización"""
        conflict_id = f"conflict_{operation.id}_{int(time.time())}"
        
        conflict = SyncConflict(
            id=conflict_id,
            operation_id=operation.id,
            source_data=operation.data,
            target_data=conflict_data,
            conflict_fields=list(conflict_data.keys()),
            resolution_strategy=self.config["conflict_resolution"]
        )
        
        # Aplicar estrategia de resolución automática
        if conflict.resolution_strategy == ConflictResolution.LAST_WRITE_WINS:
            # Usar datos con timestamp más reciente
            source_timestamp = operation.data.get("timestamp", 0)
            target_timestamp = conflict_data.get("existing", {}).get("timestamp", 0)
            
            if source_timestamp >= target_timestamp:
                conflict.resolution_data = operation.data
                conflict.resolved = True
                logger.info(f"🔧 [CONFLICT] Resuelto automáticamente (last-write-wins): {conflict_id}")
            else:
                conflict.resolution_data = conflict_data.get("existing", {})
                conflict.resolved = True
                logger.info(f"🔧 [CONFLICT] Datos existentes prevalecen: {conflict_id}")
        
        return conflict
    
    def _start_drive_monitoring(self):
        """Iniciar monitoreo de cambios en Google Drive"""
        if not self.storage_manager.google_drive.is_available():
            logger.warning("⚠️ [DRIVE_MONITOR] Google Drive no disponible")
            return
        
        def drive_monitor():
            self.is_monitoring_drive = True
            logger.info("👀 [DRIVE_MONITOR] Monitoreo de Google Drive iniciado")
            
            last_check_time = datetime.now() - timedelta(hours=1)  # Revisar última hora
            
            while self.is_monitoring_drive:
                try:
                    # Buscar cambios en la carpeta de antiguos (admin folder)
                    changes = self._detect_drive_changes(last_check_time)
                    
                    for change in changes:
                        logger.info(f"📄 [DRIVE_MONITOR] Cambio detectado: {change.file_name} ({change.change_type})")
                        
                        # Agregar operación de sincronización
                        self.add_sync_operation(
                            source="drive_admin",
                            target="database",
                            operation_type="create",
                            data={
                                "file_id": change.file_id,
                                "file_name": change.file_name,
                                "change_type": change.change_type,
                                "folder": change.folder
                            },
                            priority=2  # Alta prioridad para cambios del admin
                        )
                    
                    last_check_time = datetime.now()
                    self.last_sync_times["drive_monitor"] = last_check_time
                    
                    time.sleep(self.config["drive_monitor_interval"])
                    
                except Exception as e:
                    logger.error(f"❌ [DRIVE_MONITOR] Error en monitoreo: {e}")
                    time.sleep(60)  # Esperar 1 minuto en caso de error
        
        self.monitoring_thread = threading.Thread(target=drive_monitor, daemon=True)
        self.monitoring_thread.start()
    
    def _detect_drive_changes(self, since: datetime) -> List[GoogleDriveChange]:
        """Detectar cambios en Google Drive desde una fecha"""
        changes = []
        
        try:
            # Buscar archivos modificados desde la fecha especificada
            query = f"'{self.storage_manager.google_drive.folder_antiguas}' in parents and mimeType='application/pdf' and modifiedTime > '{since.isoformat()}Z'"
            
            results = self.storage_manager.google_drive.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, parents)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            for file in files:
                change = GoogleDriveChange(
                    file_id=file['id'],
                    file_name=file['name'],
                    change_type="added",  # Simplificado por ahora
                    folder="antiguas",
                    detected_at=datetime.now()
                )
                changes.append(change)
                
        except Exception as e:
            logger.error(f"❌ [DRIVE_CHANGES] Error detectando cambios: {e}")
        
        return changes
    
    def _sync_loop(self):
        """Bucle principal de sincronización"""
        logger.info("🔄 [SYNC_LOOP] Bucle de sincronización iniciado")
        
        while self.is_syncing:
            try:
                # Procesar cola de sincronización
                if self.sync_queue:
                    result = self.process_sync_queue()
                    logger.debug(f"🔄 [SYNC_LOOP] Resultado: {result}")
                
                # Ejecutar sincronización bidireccional si hay sistemas online
                if (self.storage_manager.system_health.supabase.value == "online" and 
                    self.config["enable_incremental_sync"]):
                    
                    # Solo sincronizar si han pasado suficientes minutos
                    last_sync = self.last_sync_times.get("json_to_supabase")
                    if (not last_sync or 
                        (datetime.now() - last_sync).seconds > self.config["sync_interval_seconds"]):
                        
                        logger.info("🔄 [SYNC_LOOP] Ejecutando sincronización bidireccional...")
                        sync_result = self.storage_manager.supabase.sincronizar_bidireccional()
                        
                        if sync_result.get("success"):
                            logger.info(f"✅ [SYNC_LOOP] Sincronización exitosa: {sync_result.get('mensaje')}")
                        else:
                            logger.error(f"❌ [SYNC_LOOP] Error en sincronización: {sync_result.get('error')}")
                
                # Esperar hasta el próximo ciclo
                time.sleep(self.config["sync_interval_seconds"])
                
            except Exception as e:
                logger.error(f"❌ [SYNC_LOOP] Error en bucle: {e}")
                time.sleep(60)  # Esperar 1 minuto en caso de error
        
        logger.info("🛑 [SYNC_LOOP] Bucle de sincronización detenido")
    
    def _calculate_checksum(self, data: Dict) -> str:
        """Calcular checksum de datos para detección de duplicados"""
        # Crear representación estable del dict
        stable_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(stable_string.encode()).hexdigest()
    
    def _load_persistent_state(self):
        """Cargar estado persistente desde archivos"""
        try:
            # Cargar cola de sincronización
            if self.queue_file.exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_data = json.load(f)
                
                self.sync_queue = []
                for op_data in queue_data:
                    operation = SyncOperation(
                        id=op_data['id'],
                        source=op_data['source'],
                        target=op_data['target'],
                        operation_type=op_data['operation_type'],
                        data=op_data['data'],
                        checksum=op_data['checksum'],
                        priority=op_data.get('priority', 5),
                        created_at=datetime.fromisoformat(op_data['created_at']),
                        updated_at=datetime.fromisoformat(op_data['updated_at']),
                        status=SyncStatus(op_data.get('status', 'pending')),
                        retry_count=op_data.get('retry_count', 0),
                        max_retries=op_data.get('max_retries', 3),
                        error_message=op_data.get('error_message')
                    )
                    self.sync_queue.append(operation)
                
                logger.info(f"📂 [PERSISTENT] {len(self.sync_queue)} operaciones cargadas")
            
            # Cargar conflictos
            if self.conflicts_file.exists():
                with open(self.conflicts_file, 'r', encoding='utf-8') as f:
                    conflicts_data = json.load(f)
                
                self.conflict_queue = []
                for conf_data in conflicts_data:
                    conflict = SyncConflict(
                        id=conf_data['id'],
                        operation_id=conf_data['operation_id'],
                        source_data=conf_data['source_data'],
                        target_data=conf_data['target_data'],
                        conflict_fields=conf_data['conflict_fields'],
                        resolution_strategy=ConflictResolution(conf_data['resolution_strategy']),
                        resolved=conf_data.get('resolved', False),
                        resolution_data=conf_data.get('resolution_data'),
                        created_at=datetime.fromisoformat(conf_data['created_at'])
                    )
                    self.conflict_queue.append(conflict)
                
                logger.info(f"⚠️ [PERSISTENT] {len(self.conflict_queue)} conflictos cargados")
                
        except Exception as e:
            logger.error(f"❌ [PERSISTENT] Error cargando estado: {e}")
    
    def _save_persistent_state(self):
        """Guardar estado persistente en archivos"""
        try:
            # Guardar cola de sincronización
            queue_data = []
            for operation in self.sync_queue:
                queue_data.append({
                    'id': operation.id,
                    'source': operation.source,
                    'target': operation.target,
                    'operation_type': operation.operation_type,
                    'data': operation.data,
                    'checksum': operation.checksum,
                    'priority': operation.priority,
                    'created_at': operation.created_at.isoformat(),
                    'updated_at': operation.updated_at.isoformat(),
                    'status': operation.status.value,
                    'retry_count': operation.retry_count,
                    'max_retries': operation.max_retries,
                    'error_message': operation.error_message
                })
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, ensure_ascii=False, indent=2)
            
            # Guardar conflictos
            conflicts_data = []
            for conflict in self.conflict_queue:
                conflicts_data.append({
                    'id': conflict.id,
                    'operation_id': conflict.operation_id,
                    'source_data': conflict.source_data,
                    'target_data': conflict.target_data,
                    'conflict_fields': conflict.conflict_fields,
                    'resolution_strategy': conflict.resolution_strategy.value,
                    'resolved': conflict.resolved,
                    'resolution_data': conflict.resolution_data,
                    'created_at': conflict.created_at.isoformat()
                })
            
            with open(self.conflicts_file, 'w', encoding='utf-8') as f:
                json.dump(conflicts_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ [PERSISTENT] Error guardando estado: {e}")
    
    def get_sync_status(self) -> Dict:
        """Obtener estado del sistema de sincronización"""
        return {
            "is_running": self.is_syncing,
            "queue_size": len(self.sync_queue),
            "conflicts_pending": len([c for c in self.conflict_queue if not c.resolved]),
            "last_sync_times": {k: v.isoformat() if v else None for k, v in self.last_sync_times.items()},
            "completed_operations": len(self.completed_operations),
            "drive_monitoring": self.is_monitoring_drive,
            "configuration": self.config
        }
    
    def force_sync_operation(self, source: str, target: str, operation_type: str, data: Dict) -> str:
        """Forzar una operación de sincronización inmediata"""
        operation_id = self.add_sync_operation(source, target, operation_type, data, priority=1)
        
        # Procesar inmediatamente
        for operation in self.sync_queue:
            if operation.id == operation_id:
                result = self._execute_sync_operation(operation)
                if result["success"]:
                    operation.status = SyncStatus.COMPLETED
                    self.sync_queue.remove(operation)
                    self.completed_operations.append(operation)
                    logger.info(f"⚡ [FORCE_SYNC] Operación {operation_id} completada inmediatamente")
                break
        
        return operation_id
    
    def resolve_conflict(self, conflict_id: str, resolution_data: Dict) -> bool:
        """Resolver un conflicto manualmente"""
        for conflict in self.conflict_queue:
            if conflict.id == conflict_id and not conflict.resolved:
                conflict.resolution_data = resolution_data
                conflict.resolved = True
                
                # Re-agregar operación a la cola con datos resueltos
                self.add_sync_operation(
                    source="conflict_resolution",
                    target="unified",
                    operation_type="update",
                    data=resolution_data,
                    priority=1
                )
                
                logger.info(f"🔧 [CONFLICT] Conflicto {conflict_id} resuelto manualmente")
                return True
        
        return False


if __name__ == "__main__":
    # Test del sistema de sincronización
    from unified_storage_manager import UnifiedStorageManager
    
    storage_manager = UnifiedStorageManager()
    sync_system = EnhancedSyncSystem(storage_manager)
    
    # Mostrar estado
    status = sync_system.get_sync_status()
    print(json.dumps(status, indent=2, default=str))
    
    # Agregar operación de prueba
    test_data = {
        "numeroCotizacion": "TEST-SYNC-001",
        "datosGenerales": {"cliente": "Test", "vendedor": "Sync"},
        "timestamp": int(time.time() * 1000)
    }
    
    op_id = sync_system.add_sync_operation("json", "supabase", "create", test_data, priority=1)
    print(f"Operación agregada: {op_id}")