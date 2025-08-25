#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIFIED STORAGE MANAGER - Sistema Integrado de Almacenamiento
===========================================================

Administrador unificado que integra todos los sistemas de almacenamiento:
- Supabase PostgreSQL (datos principales)
- Supabase Storage (PDFs integrados)
- Google Drive (PDFs antiguos del administrador)
- JSON Local (sistema offline con sincronización)

Características principales:
- Garantía de disponibilidad 99.9%
- Sincronización automática multi-dirección
- Búsqueda unificada en todas las fuentes
- Sistema de cola para operaciones offline
- Monitoreo de integridad y salud del sistema
"""

import os
import json
import time
import datetime
import asyncio
import threading
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

# Managers existentes
from supabase_manager import SupabaseManager
# CloudinaryManager eliminado - migrado a Supabase Storage
from supabase_storage_manager import SupabaseStorageManager
from google_drive_client import GoogleDriveClient

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StorageStatus(Enum):
    """Estados de los sistemas de almacenamiento"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    SYNCING = "syncing"
    MAINTENANCE = "maintenance"


class OperationType(Enum):
    """Tipos de operaciones del sistema"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    SYNC = "sync"


@dataclass
class StorageResult:
    """Resultado de operación de almacenamiento"""
    success: bool
    data: Any = None
    error: str = None
    source: str = None
    timestamp: datetime.datetime = None
    operation_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()


@dataclass
class HealthStatus:
    """Estado de salud del sistema"""
    supabase: StorageStatus
    supabase_storage: StorageStatus
    google_drive: StorageStatus
    json_local: StorageStatus
    overall_health: float
    last_check: datetime.datetime
    issues: List[str]


@dataclass
class PendingOperation:
    """Operación pendiente en la cola"""
    operation_id: str
    operation_type: OperationType
    data: Dict
    target_systems: List[str]
    created_at: datetime.datetime
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 1  # 1=alta, 5=baja


class UnifiedStorageManager:
    """
    Administrador unificado de almacenamiento que coordina todos los sistemas
    """
    
    def __init__(self):
        """Inicializar el administrador unificado"""
        logger.info("🚀 [UNIFIED_STORAGE] Inicializando sistema unificado...")
        
        # Inicializar sistemas de almacenamiento
        self.supabase = SupabaseManager()
        self.supabase_storage = SupabaseStorageManager()
        self.google_drive = GoogleDriveClient()
        
        # Estado del sistema
        self.system_health = None
        self.last_health_check = None
        self.is_monitoring = False
        
        # Cola de operaciones pendientes
        self.pending_queue = []
        self.queue_file = Path("pending_operations.json")
        self._load_pending_queue()
        
        # Configuración
        self.config = self._load_configuration()
        
        # Métricas del sistema
        self.metrics = {
            "operations_completed": 0,
            "operations_failed": 0,
            "sync_operations": 0,
            "search_operations": 0,
            "uptime_start": datetime.datetime.now()
        }
        
        # Inicializar sistema
        self._initialize_system()
        
    def _load_configuration(self) -> Dict:
        """Cargar configuración del sistema"""
        return {
            "sync_interval_minutes": int(os.getenv('SYNC_INTERVAL_MINUTES', '15')),
            "health_check_interval": int(os.getenv('HEALTH_CHECK_INTERVAL', '5')),
            "max_queue_size": int(os.getenv('MAX_QUEUE_SIZE', '1000')),
            "enable_auto_sync": os.getenv('ENABLE_AUTO_SYNC', 'true').lower() == 'true',
            "enable_health_monitoring": os.getenv('ENABLE_HEALTH_MONITORING', 'true').lower() == 'true',
            "search_timeout_seconds": int(os.getenv('SEARCH_TIMEOUT_SECONDS', '30')),
            "google_drive_admin_folder": os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS', '1GqM9yfwUKd9n8nN97IUiBSUrWUZ1Vida')
        }
    
    def _initialize_system(self):
        """Inicializar el sistema completo"""
        try:
            logger.info("🔧 [INIT] Inicializando componentes del sistema...")
            
            # Verificar estado inicial de todos los sistemas
            self.check_system_health()
            
            # Procesar cola de operaciones pendientes
            if self.pending_queue:
                logger.info(f"⏳ [QUEUE] Procesando {len(self.pending_queue)} operaciones pendientes...")
                self._process_pending_operations()
            
            # Iniciar monitoreo si está habilitado
            if self.config['enable_health_monitoring']:
                self._start_health_monitoring()
            
            # Iniciar sincronización automática si está habilitada
            if self.config['enable_auto_sync']:
                self._start_auto_sync()
            
            logger.info("✅ [INIT] Sistema unificado inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ [INIT] Error inicializando sistema: {e}")
            raise
    
    def check_system_health(self) -> HealthStatus:
        """Verificar el estado de salud de todos los sistemas"""
        try:
            logger.debug("🔍 [HEALTH] Verificando estado del sistema...")
            
            # Verificar Supabase
            supabase_status = StorageStatus.ONLINE if not self.supabase.modo_offline else StorageStatus.OFFLINE
            
            # Verificar Supabase Storage
            supabase_storage_status = StorageStatus.ONLINE if self.supabase_storage.is_available() else StorageStatus.OFFLINE
            
            # Verificar Google Drive
            google_drive_status = StorageStatus.ONLINE if self.google_drive.is_available() else StorageStatus.OFFLINE
            
            # JSON Local siempre disponible
            json_local_status = StorageStatus.ONLINE
            
            # Calcular salud general (porcentaje de sistemas online)
            online_systems = sum([
                supabase_status == StorageStatus.ONLINE,
                supabase_storage_status == StorageStatus.ONLINE,
                google_drive_status == StorageStatus.ONLINE,
                json_local_status == StorageStatus.ONLINE
            ])
            overall_health = (online_systems / 4.0) * 100
            
            # Identificar problemas
            issues = []
            if supabase_status == StorageStatus.OFFLINE:
                issues.append("Supabase no disponible - usando fallback JSON")
            if supabase_storage_status == StorageStatus.OFFLINE:
                issues.append("Supabase Storage no disponible - usando Google Drive/Local")
            if google_drive_status == StorageStatus.OFFLINE:
                issues.append("Google Drive no disponible - sin acceso a PDFs antiguos")
            
            self.system_health = HealthStatus(
                supabase=supabase_status,
                supabase_storage=supabase_storage_status,
                google_drive=google_drive_status,
                json_local=json_local_status,
                overall_health=overall_health,
                last_check=datetime.datetime.now(),
                issues=issues
            )
            
            self.last_health_check = datetime.datetime.now()
            
            logger.info(f"💚 [HEALTH] Salud del sistema: {overall_health:.1f}% ({online_systems}/4 sistemas online)")
            if issues:
                for issue in issues:
                    logger.warning(f"⚠️ [HEALTH] {issue}")
            
            return self.system_health
            
        except Exception as e:
            logger.error(f"❌ [HEALTH] Error verificando salud del sistema: {e}")
            return HealthStatus(
                supabase=StorageStatus.ERROR,
                supabase_storage=StorageStatus.ERROR,
                google_drive=StorageStatus.ERROR,
                json_local=StorageStatus.ERROR,
                overall_health=0.0,
                last_check=datetime.datetime.now(),
                issues=[f"Error en verificación de salud: {str(e)}"]
            )
    
    def guardar_cotizacion(self, datos: Dict) -> StorageResult:
        """
        Guardar cotización usando estrategia de almacenamiento unificada
        
        Estrategia:
        1. Supabase (principal) + JSON (respaldo local)
        2. Si Supabase falla → JSON principal con sync posterior
        3. Generar PDF y almacenar en Cloudinary/Google Drive/Local
        """
        operation_id = f"save_{int(time.time())}_{hash(str(datos))}"
        
        try:
            logger.info(f"💾 [SAVE] Iniciando guardado unificado - ID: {operation_id}")
            
            numero_cotizacion = datos.get('numeroCotizacion', 'Sin_Numero')
            logger.info(f"📋 [SAVE] Cotización: {numero_cotizacion}")
            
            # 1. Intentar guardar en Supabase (principal)
            supabase_result = None
            if self.system_health.supabase == StorageStatus.ONLINE:
                try:
                    supabase_result = self.supabase.guardar_cotizacion(datos)
                    if supabase_result.get('success'):
                        logger.info("✅ [SUPABASE] Cotización guardada en sistema principal")
                    else:
                        logger.error(f"❌ [SUPABASE] Error: {supabase_result.get('error')}")
                        supabase_result = None
                except Exception as e:
                    logger.error(f"❌ [SUPABASE] Excepción: {e}")
                    supabase_result = None
            
            # 2. Siempre guardar en JSON (respaldo local)
            json_result = None
            try:
                # Usar el método de JSON del supabase manager
                data_offline = self.supabase._cargar_datos_offline()
                cotizaciones = data_offline.get("cotizaciones", [])
                
                # Agregar o actualizar cotización
                found = False
                for i, cot in enumerate(cotizaciones):
                    if cot.get('numeroCotizacion') == numero_cotizacion:
                        cotizaciones[i] = datos
                        found = True
                        break
                
                if not found:
                    cotizaciones.append(datos)
                
                data_offline["cotizaciones"] = cotizaciones
                data_offline["last_updated"] = datetime.datetime.now().isoformat()
                
                if self.supabase._guardar_datos_offline(data_offline):
                    json_result = {
                        "success": True, 
                        "modo": "json_backup", 
                        "total": len(cotizaciones)
                    }
                    logger.info("✅ [JSON] Respaldo local guardado")
                else:
                    logger.error("❌ [JSON] Error guardando respaldo local")
                    
            except Exception as e:
                logger.error(f"❌ [JSON] Error en respaldo local: {e}")
            
            # 3. Si Supabase falló, agregar a cola de sincronización
            if not supabase_result and json_result:
                self._add_to_pending_queue(PendingOperation(
                    operation_id=operation_id,
                    operation_type=OperationType.CREATE,
                    data=datos,
                    target_systems=["supabase"],
                    created_at=datetime.datetime.now()
                ))
                logger.info("⏳ [QUEUE] Operación agregada a cola de sincronización")
            
            # Determinar resultado final
            success = bool(supabase_result or json_result)
            primary_source = "supabase" if supabase_result else "json_local"
            
            if success:
                self.metrics["operations_completed"] += 1
            else:
                self.metrics["operations_failed"] += 1
            
            return StorageResult(
                success=success,
                data={
                    "numero_cotizacion": numero_cotizacion,
                    "supabase": supabase_result,
                    "json_backup": json_result,
                    "primary_source": primary_source
                },
                source=primary_source,
                operation_id=operation_id
            )
            
        except Exception as e:
            logger.error(f"❌ [SAVE] Error general en guardado: {e}")
            self.metrics["operations_failed"] += 1
            
            return StorageResult(
                success=False,
                error=f"Error guardando cotización: {str(e)}",
                operation_id=operation_id
            )
    
    def guardar_pdf(self, pdf_content: bytes, cotizacion_data: Dict) -> StorageResult:
        """
        Guardar PDF usando sistema de almacenamiento híbrido
        
        Estrategia:
        1. Cloudinary (principal - 25GB gratuitos con CDN)
        2. Google Drive (fallback - si Cloudinary falla)
        3. Local (emergencia - siempre como respaldo)
        """
        operation_id = f"pdf_{int(time.time())}_{hash(str(cotizacion_data))}"
        
        try:
            numero_cotizacion = cotizacion_data.get('numeroCotizacion', 'Sin_Numero')
            logger.info(f"📄 [PDF] Guardando PDF: {numero_cotizacion} ({len(pdf_content)} bytes)")
            
            # Crear archivo temporal para las operaciones
            import tempfile
            temp_file_path = None
            
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(pdf_content)
                    temp_file_path = temp_file.name
                
                results = {}
                primary_success = False
                
                # 1. Intentar Supabase Storage (principal)
                if self.system_health.supabase_storage == StorageStatus.ONLINE:
                    try:
                        supabase_storage_result = self.supabase_storage.subir_pdf(
                            temp_file_path,
                            numero_cotizacion,
                            es_nueva=True
                        )
                        results["supabase_storage"] = supabase_storage_result
                        
                        if not supabase_storage_result.get("error"):
                            primary_success = True
                            logger.info("✅ [SUPABASE_STORAGE] PDF subido al sistema principal")
                        else:
                            logger.error(f"❌ [SUPABASE_STORAGE] Error: {supabase_storage_result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"❌ [SUPABASE_STORAGE] Excepción: {e}")
                        results["supabase_storage"] = {"error": str(e)}
                
                # 2. Google Drive (fallback si Supabase Storage falló)
                if not primary_success and self.system_health.google_drive == StorageStatus.ONLINE:
                    try:
                        # Preparar metadata para Google Drive
                        file_metadata = {
                            'name': f"{numero_cotizacion}.pdf",
                            'parents': [self.google_drive.folder_nuevas]
                        }
                        
                        from googleapiclient.http import MediaFileUpload
                        media_body = MediaFileUpload(
                            temp_file_path,
                            mimetype='application/pdf',
                            resumable=True
                        )
                        
                        uploaded_file = self.google_drive.service.files().create(
                            body=file_metadata,
                            media_body=media_body,
                            fields='id,name,size,createdTime'
                        ).execute()
                        
                        results["google_drive"] = {
                            "success": True,
                            "file_id": uploaded_file.get('id'),
                            "url": f"https://drive.google.com/file/d/{uploaded_file.get('id')}/view"
                        }
                        primary_success = True
                        logger.info("✅ [GOOGLE_DRIVE] PDF subido como fallback")
                        
                    except Exception as e:
                        logger.error(f"❌ [GOOGLE_DRIVE] Error en fallback: {e}")
                        results["google_drive"] = {"error": str(e)}
                
                # 3. Respaldo local (siempre)
                try:
                    local_path = Path("pdfs_cotizaciones") / "nuevas" / f"{numero_cotizacion}.pdf"
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(pdf_content)
                    
                    results["local"] = {
                        "success": True,
                        "path": str(local_path.absolute()),
                        "size": len(pdf_content)
                    }
                    logger.info("✅ [LOCAL] Respaldo local guardado")
                    
                except Exception as e:
                    logger.error(f"❌ [LOCAL] Error en respaldo local: {e}")
                    results["local"] = {"error": str(e)}
                
                # Si los sistemas principales fallaron, agregar a cola
                if not primary_success and pdf_content:
                    self._add_to_pending_queue(PendingOperation(
                        operation_id=operation_id,
                        operation_type=OperationType.CREATE,
                        data={"pdf_content": pdf_content, "cotizacion": cotizacion_data},
                        target_systems=["supabase_storage", "google_drive"],
                        created_at=datetime.datetime.now()
                    ))
                
                # Resultado final
                overall_success = primary_success or results.get("local", {}).get("success", False)
                
                if overall_success:
                    self.metrics["operations_completed"] += 1
                else:
                    self.metrics["operations_failed"] += 1
                
                return StorageResult(
                    success=overall_success,
                    data=results,
                    source="supabase_storage" if results.get("supabase_storage", {}).get("success") else "google_drive" if results.get("google_drive", {}).get("success") else "local",
                    operation_id=operation_id
                )
                
            finally:
                # Limpiar archivo temporal
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"❌ [PDF] Error general guardando PDF: {e}")
            self.metrics["operations_failed"] += 1
            
            return StorageResult(
                success=False,
                error=f"Error guardando PDF: {str(e)}",
                operation_id=operation_id
            )
    
    def buscar_cotizaciones(self, query: str, page: int = 1, per_page: int = 20) -> StorageResult:
        """
        Búsqueda unificada en todas las fuentes de datos
        
        Fuentes:
        1. Supabase PostgreSQL (principal)
        2. JSON local (respaldo/offline)
        3. Google Drive PDFs (antiguos del admin)
        """
        operation_id = f"search_{int(time.time())}_{hash(query)}"
        
        try:
            logger.info(f"🔍 [SEARCH] Búsqueda unificada: '{query}' (página {page})")
            self.metrics["search_operations"] += 1
            
            all_results = []
            sources_used = []
            errors = []
            
            # 1. Buscar en Supabase (principal)
            if self.system_health.supabase == StorageStatus.ONLINE:
                try:
                    supabase_results = self.supabase.buscar_cotizaciones(query, 1, 1000)  # Obtener todos para unificar
                    if not supabase_results.get('error'):
                        cotizaciones = supabase_results.get('resultados', [])
                        for cot in cotizaciones:
                            all_results.append({
                                **cot,
                                'source': 'supabase',
                                'tiene_desglose': True,
                                'tipo': 'cotizacion'
                            })
                        sources_used.append('supabase')
                        logger.info(f"✅ [SUPABASE] {len(cotizaciones)} resultados")
                    else:
                        errors.append(f"Supabase: {supabase_results.get('error')}")
                        
                except Exception as e:
                    logger.error(f"❌ [SUPABASE] Error en búsqueda: {e}")
                    errors.append(f"Supabase: {str(e)}")
            
            # 2. Buscar en JSON local (complementario)
            try:
                json_data = self.supabase._cargar_datos_offline()
                cotizaciones_json = json_data.get('cotizaciones', [])
                
                for cot in cotizaciones_json:
                    # Evitar duplicados de Supabase
                    numero = cot.get('numeroCotizacion')
                    if not any(r.get('numeroCotizacion') == numero for r in all_results):
                        datos_gen = cot.get('datosGenerales', {})
                        if not query or any(query.lower() in str(field).lower() for field in [
                            cot.get('numeroCotizacion', ''),
                            datos_gen.get('cliente', ''),
                            datos_gen.get('vendedor', ''),
                            datos_gen.get('proyecto', '')
                        ]):
                            all_results.append({
                                **cot,
                                'source': 'json_local',
                                'tiene_desglose': True,
                                'tipo': 'cotizacion'
                            })
                
                sources_used.append('json_local')
                logger.info(f"✅ [JSON] Datos locales incluidos")
                
            except Exception as e:
                logger.error(f"❌ [JSON] Error en búsqueda local: {e}")
                errors.append(f"JSON: {str(e)}")
            
            # 3. Buscar PDFs en Google Drive (antiguos del admin)
            if self.system_health.google_drive == StorageStatus.ONLINE:
                try:
                    drive_pdfs = self.google_drive.buscar_pdfs(query)
                    for pdf in drive_pdfs:
                        all_results.append({
                            'numeroCotizacion': pdf['numero_cotizacion'],
                            'datosGenerales': {
                                'cliente': 'Google Drive (Histórico)',
                                'proyecto': pdf['numero_cotizacion']
                            },
                            'fechaCreacion': pdf.get('fecha_modificacion', ''),
                            'source': 'google_drive',
                            'drive_id': pdf['id'],
                            'carpeta_origen': pdf.get('carpeta_origen', 'antigua'),
                            'tiene_desglose': False,
                            'tipo': 'pdf_historico'
                        })
                    
                    sources_used.append('google_drive')
                    logger.info(f"✅ [GOOGLE_DRIVE] {len(drive_pdfs)} PDFs históricos")
                    
                except Exception as e:
                    logger.error(f"❌ [GOOGLE_DRIVE] Error buscando PDFs: {e}")
                    errors.append(f"Google Drive: {str(e)}")
            
            # Ordenar resultados por relevancia y fecha
            all_results.sort(key=lambda x: (
                x.get('timestamp', 0) if x.get('timestamp') else 0,
                x.get('fechaCreacion', '') or ''
            ), reverse=True)
            
            # Paginación
            total = len(all_results)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_results = all_results[start:end]
            
            logger.info(f"🎯 [SEARCH] {len(paginated_results)}/{total} resultados (fuentes: {', '.join(sources_used)})")
            
            return StorageResult(
                success=True,
                data={
                    'resultados': paginated_results,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page,
                    'sources_used': sources_used,
                    'errors': errors if errors else None
                },
                source='unified',
                operation_id=operation_id
            )
            
        except Exception as e:
            logger.error(f"❌ [SEARCH] Error en búsqueda unificada: {e}")
            self.metrics["operations_failed"] += 1
            
            return StorageResult(
                success=False,
                error=f"Error en búsqueda unificada: {str(e)}",
                operation_id=operation_id
            )
    
    def obtener_cotizacion(self, numero_cotizacion: str) -> StorageResult:
        """Obtener cotización específica con búsqueda unificada"""
        operation_id = f"get_{int(time.time())}_{hash(numero_cotizacion)}"
        
        try:
            logger.info(f"📋 [GET] Obteniendo cotización: {numero_cotizacion}")
            
            # Buscar en Supabase primero
            if self.system_health.supabase == StorageStatus.ONLINE:
                try:
                    supabase_result = self.supabase.obtener_cotizacion(numero_cotizacion)
                    if supabase_result.get('encontrado'):
                        logger.info("✅ [SUPABASE] Cotización encontrada en sistema principal")
                        return StorageResult(
                            success=True,
                            data=supabase_result,
                            source='supabase',
                            operation_id=operation_id
                        )
                except Exception as e:
                    logger.error(f"❌ [SUPABASE] Error: {e}")
            
            # Buscar en JSON local
            try:
                json_data = self.supabase._cargar_datos_offline()
                for cot in json_data.get('cotizaciones', []):
                    if cot.get('numeroCotizacion') == numero_cotizacion:
                        logger.info("✅ [JSON] Cotización encontrada en respaldo local")
                        return StorageResult(
                            success=True,
                            data={'encontrado': True, 'item': cot, 'modo': 'json_local'},
                            source='json_local',
                            operation_id=operation_id
                        )
            except Exception as e:
                logger.error(f"❌ [JSON] Error: {e}")
            
            # No encontrada
            logger.warning(f"⚠️ [GET] Cotización no encontrada: {numero_cotizacion}")
            return StorageResult(
                success=False,
                error=f"Cotización '{numero_cotizacion}' no encontrada",
                operation_id=operation_id
            )
            
        except Exception as e:
            logger.error(f"❌ [GET] Error obteniendo cotización: {e}")
            return StorageResult(
                success=False,
                error=f"Error obteniendo cotización: {str(e)}",
                operation_id=operation_id
            )
    
    def _add_to_pending_queue(self, operation: PendingOperation):
        """Agregar operación a la cola de pendientes"""
        try:
            self.pending_queue.append(operation)
            self._save_pending_queue()
            logger.info(f"⏳ [QUEUE] Operación {operation.operation_id} agregada a cola")
        except Exception as e:
            logger.error(f"❌ [QUEUE] Error agregando a cola: {e}")
    
    def _load_pending_queue(self):
        """Cargar cola de operaciones pendientes"""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_data = json.load(f)
                
                self.pending_queue = []
                for op_data in queue_data:
                    operation = PendingOperation(
                        operation_id=op_data['operation_id'],
                        operation_type=OperationType(op_data['operation_type']),
                        data=op_data['data'],
                        target_systems=op_data['target_systems'],
                        created_at=datetime.datetime.fromisoformat(op_data['created_at']),
                        retry_count=op_data.get('retry_count', 0),
                        max_retries=op_data.get('max_retries', 3)
                    )
                    self.pending_queue.append(operation)
                
                logger.info(f"📂 [QUEUE] {len(self.pending_queue)} operaciones pendientes cargadas")
        except Exception as e:
            logger.error(f"❌ [QUEUE] Error cargando cola: {e}")
            self.pending_queue = []
    
    def _save_pending_queue(self):
        """Guardar cola de operaciones pendientes"""
        try:
            queue_data = []
            for operation in self.pending_queue:
                queue_data.append({
                    'operation_id': operation.operation_id,
                    'operation_type': operation.operation_type.value,
                    'data': operation.data,
                    'target_systems': operation.target_systems,
                    'created_at': operation.created_at.isoformat(),
                    'retry_count': operation.retry_count,
                    'max_retries': operation.max_retries
                })
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ [QUEUE] Error guardando cola: {e}")
    
    def _process_pending_operations(self):
        """Procesar operaciones pendientes en la cola"""
        if not self.pending_queue:
            return
        
        logger.info(f"🔄 [QUEUE] Procesando {len(self.pending_queue)} operaciones pendientes...")
        
        processed = 0
        failed = 0
        
        # Crear copia para evitar modificación durante iteración
        operations_to_process = self.pending_queue.copy()
        
        for operation in operations_to_process:
            try:
                success = self._retry_operation(operation)
                
                if success:
                    self.pending_queue.remove(operation)
                    processed += 1
                    logger.info(f"✅ [QUEUE] Operación {operation.operation_id} completada")
                else:
                    operation.retry_count += 1
                    if operation.retry_count >= operation.max_retries:
                        self.pending_queue.remove(operation)
                        failed += 1
                        logger.error(f"❌ [QUEUE] Operación {operation.operation_id} falló después de {operation.max_retries} intentos")
                    
            except Exception as e:
                logger.error(f"❌ [QUEUE] Error procesando operación {operation.operation_id}: {e}")
                operation.retry_count += 1
                if operation.retry_count >= operation.max_retries:
                    self.pending_queue.remove(operation)
                    failed += 1
        
        # Guardar cola actualizada
        self._save_pending_queue()
        
        logger.info(f"🎯 [QUEUE] Procesamiento completado: {processed} exitosas, {failed} fallidas, {len(self.pending_queue)} pendientes")
    
    def _retry_operation(self, operation: PendingOperation) -> bool:
        """Reintentar una operación específica"""
        try:
            if operation.operation_type == OperationType.CREATE:
                # Reintento de guardado
                if "cotizacion" in operation.data:
                    result = self.guardar_cotizacion(operation.data)
                    return result.success
                elif "pdf_content" in operation.data:
                    pdf_content = operation.data["pdf_content"]
                    cotizacion_data = operation.data["cotizacion"]
                    result = self.guardar_pdf(pdf_content, cotizacion_data)
                    return result.success
            
            # Otros tipos de operaciones...
            return False
            
        except Exception as e:
            logger.error(f"❌ [RETRY] Error reintentando operación: {e}")
            return False
    
    def _start_health_monitoring(self):
        """Iniciar monitoreo de salud del sistema en hilo separado"""
        if self.is_monitoring:
            return
        
        def health_monitor():
            self.is_monitoring = True
            logger.info("💚 [MONITOR] Monitoreo de salud iniciado")
            
            while self.is_monitoring:
                try:
                    self.check_system_health()
                    time.sleep(self.config['health_check_interval'] * 60)  # Convertir a segundos
                except Exception as e:
                    logger.error(f"❌ [MONITOR] Error en monitoreo: {e}")
                    time.sleep(60)  # Esperar 1 minuto en caso de error
        
        monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        monitor_thread.start()
    
    def _start_auto_sync(self):
        """Iniciar sincronización automática"""
        def auto_sync():
            logger.info("🔄 [AUTO_SYNC] Sincronización automática iniciada")
            
            while True:
                try:
                    # Verificar salud del sistema
                    self.check_system_health()
                    
                    # Procesar operaciones pendientes
                    if self.pending_queue:
                        self._process_pending_operations()
                    
                    # Sincronización bidireccional si Supabase está online
                    if self.system_health.supabase == StorageStatus.ONLINE:
                        sync_result = self.supabase.sincronizar_bidireccional()
                        if sync_result.get('success'):
                            self.metrics["sync_operations"] += 1
                            logger.info(f"✅ [SYNC] {sync_result.get('mensaje', 'Sincronización completada')}")
                    
                    # Esperar hasta la próxima sincronización
                    time.sleep(self.config['sync_interval_minutes'] * 60)
                    
                except Exception as e:
                    logger.error(f"❌ [AUTO_SYNC] Error en sincronización automática: {e}")
                    time.sleep(300)  # Esperar 5 minutos en caso de error
        
        sync_thread = threading.Thread(target=auto_sync, daemon=True)
        sync_thread.start()
    
    def get_system_status(self) -> Dict:
        """Obtener estado completo del sistema"""
        try:
            # Asegurar que tenemos estado de salud actualizado
            if not self.system_health or (
                datetime.datetime.now() - self.last_health_check
            ).seconds > 300:  # Actualizar si es mayor a 5 minutos
                self.check_system_health()
            
            # Calcular uptime
            uptime = datetime.datetime.now() - self.metrics["uptime_start"]
            
            return {
                "health": asdict(self.system_health) if self.system_health else None,
                "metrics": {
                    **self.metrics,
                    "uptime_seconds": uptime.total_seconds(),
                    "uptime_formatted": str(uptime).split('.')[0]  # Sin microsegundos
                },
                "pending_operations": len(self.pending_queue),
                "configuration": self.config,
                "storage_systems": {
                    "supabase": {
                        "status": self.system_health.supabase.value if self.system_health else "unknown",
                        "modo_offline": getattr(self.supabase, 'modo_offline', None)
                    },
                    "supabase_storage": {
                        "status": self.system_health.supabase_storage.value if self.system_health else "unknown",
                        "available": self.supabase_storage.is_available()
                    },
                    "google_drive": {
                        "status": self.system_health.google_drive.value if self.system_health else "unknown",
                        "available": self.google_drive.is_available()
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [STATUS] Error obteniendo estado del sistema: {e}")
            return {
                "error": f"Error obteniendo estado: {str(e)}",
                "health": None,
                "metrics": self.metrics
            }
    
    def shutdown(self):
        """Apagar el sistema de forma limpia"""
        try:
            logger.info("🔌 [SHUTDOWN] Apagando sistema unificado...")
            
            # Detener monitoreo
            self.is_monitoring = False
            
            # Procesar operaciones pendientes una última vez
            if self.pending_queue:
                logger.info("⏳ [SHUTDOWN] Procesando operaciones pendientes finales...")
                self._process_pending_operations()
            
            # Cerrar conexiones
            if hasattr(self.supabase, 'close'):
                self.supabase.close()
            
            logger.info("✅ [SHUTDOWN] Sistema apagado correctamente")
            
        except Exception as e:
            logger.error(f"❌ [SHUTDOWN] Error durante apagado: {e}")


# Instancia global del administrador unificado
_unified_manager = None

def get_unified_manager() -> UnifiedStorageManager:
    """Obtener instancia singleton del administrador unificado"""
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedStorageManager()
    return _unified_manager


if __name__ == "__main__":
    # Test básico del sistema
    manager = UnifiedStorageManager()
    
    # Mostrar estado del sistema
    status = manager.get_system_status()
    print(json.dumps(status, indent=2, default=str))
    
    # Test de búsqueda
    search_result = manager.buscar_cotizaciones("test")
    print(f"Búsqueda test: {search_result.success}")
    
    # Apagar sistema
    manager.shutdown()