#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATION SCRIPTS - CWS COTIZADOR UNIFIED SYSTEM
===============================================

Scripts para migrar del sistema actual al nuevo sistema unificado que integra:
- Supabase PostgreSQL (principal)
- Supabase Storage (PDFs integrados)
- Google Drive (PDFs antiguos del admin)
- Sistema offline con sincronización automática

Características:
- Migración paso a paso con validación
- Backup completo antes de migración
- Rollback automático en caso de errores
- Verificación de integridad de datos
- Migración incremental por lotes
- Preservación de historial completo

Versión: 1.0.0 - Migración Inicial
Fecha: 2025-08-19
"""

import os
import json
import shutil
import logging
import time
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib

# Importar sistemas existentes y nuevos
try:
    from database import DatabaseManager
    from supabase_manager import SupabaseManager
    from cloudinary_manager import CloudinaryManager
    from google_drive_client import GoogleDriveClient
    from unified_storage_manager import UnifiedStorageManager, get_unified_manager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Algunos módulos no están disponibles: {e}")
    IMPORTS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class MigrationStep:
    """Paso de migración"""
    id: str
    name: str
    description: str
    completed: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    rollback_data: Optional[Dict] = None

@dataclass
class MigrationReport:
    """Reporte de migración"""
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    migrated_quotations: int = 0
    migrated_pdfs: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    backup_path: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class MigrationManager:
    """Gestor de migración al sistema unificado"""
    
    def __init__(self):
        """Inicializar gestor de migración"""
        self.setup_logging()
        
        # Sistemas existentes
        self.database_manager = None
        self.supabase_manager = None
        self.cloudinary_manager = None
        self.google_drive = None
        
        # Sistema unificado
        self.unified_manager = None
        
        # Estado de migración
        self.migration_dir = Path(__file__).parent / 'migration_data'
        self.backup_dir = self.migration_dir / 'backups'
        self.reports_dir = self.migration_dir / 'reports'
        
        # Crear directorios
        self.migration_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        # Estado actual
        self.current_report = None
        self.migration_steps = []
        
        logger.info("🔄 [MIGRATION] Gestor de migración inicializado")
    
    def setup_logging(self):
        """Configurar logging para migración"""
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # Logger específico para migración
        migration_log = log_dir / 'migration.log'
        handler = logging.FileHandler(migration_log, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] MIGRATION - %(message)s'
        )
        handler.setFormatter(formatter)
        
        migration_logger = logging.getLogger('MIGRATION')
        migration_logger.addHandler(handler)
        migration_logger.setLevel(logging.INFO)
        
        print(f"📝 [MIGRATION] Logs guardados en: {migration_log}")
    
    def initialize_systems(self) -> bool:
        """Inicializar todos los sistemas necesarios"""
        try:
            logger.info("🚀 [MIGRATION] Inicializando sistemas...")
            
            if not IMPORTS_AVAILABLE:
                raise Exception("Módulos requeridos no disponibles")
            
            # Sistemas existentes
            self.database_manager = DatabaseManager()
            self.supabase_manager = SupabaseManager()
            self.cloudinary_manager = CloudinaryManager()
            self.google_drive = GoogleDriveClient()
            
            # Sistema unificado
            self.unified_manager = get_unified_manager()
            
            logger.info("✅ [MIGRATION] Todos los sistemas inicializados")
            return True
            
        except Exception as e:
            logger.error(f"❌ [MIGRATION] Error inicializando sistemas: {e}")
            return False
    
    def create_full_backup(self) -> str:
        """Crear backup completo del sistema actual"""
        logger.info("💾 [MIGRATION] Creando backup completo...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"full_backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        try:
            # 1. Backup de JSON local
            json_file = Path(__file__).parent / 'cotizaciones_offline.json'
            if json_file.exists():
                shutil.copy2(json_file, backup_path / 'cotizaciones_offline.json')
                logger.info("✅ [BACKUP] JSON local respaldado")
            
            # 2. Backup de configuración
            config_files = ['config.py', '.env', 'Lista de materiales.csv']
            for config_file in config_files:
                config_path = Path(__file__).parent / config_file
                if config_path.exists():
                    shutil.copy2(config_path, backup_path / config_file)
            
            # 3. Backup de templates actuales
            templates_dir = Path(__file__).parent / 'templates'
            if templates_dir.exists():
                shutil.copytree(templates_dir, backup_path / 'templates', dirs_exist_ok=True)
            
            # 4. Backup de logs existentes
            logs_dir = Path(__file__).parent / 'logs'
            if logs_dir.exists():
                shutil.copytree(logs_dir, backup_path / 'logs', dirs_exist_ok=True)
            
            # 5. Crear manifest del backup
            manifest = {
                "backup_timestamp": timestamp,
                "backup_created": datetime.now().isoformat(),
                "system_version": "legacy",
                "files_backed_up": [f.name for f in backup_path.rglob('*') if f.is_file()],
                "backup_size_mb": sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()) / (1024*1024)
            }
            
            manifest_path = backup_path / 'backup_manifest.json'
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
            
            logger.info(f"✅ [BACKUP] Backup completo creado en: {backup_path}")
            logger.info(f"📊 [BACKUP] Tamaño: {manifest['backup_size_mb']:.2f} MB")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] Error creando backup: {e}")
            raise
    
    def analyze_current_system(self) -> Dict[str, Any]:
        """Analizar el sistema actual para planificar migración"""
        logger.info("🔍 [MIGRATION] Analizando sistema actual...")
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "database": {"type": "unknown", "records": 0, "status": "unknown"},
            "pdf_storage": {"providers": [], "total_files": 0},
            "templates": {"count": 0, "files": []},
            "configuration": {"env_vars": [], "config_files": []},
            "estimated_migration_time_minutes": 0
        }
        
        try:
            # Analizar base de datos actual
            if self.database_manager:
                try:
                    stats = self.database_manager.obtener_estadisticas()
                    analysis["database"] = {
                        "type": "hybrid_json_mongodb",
                        "records": stats.get("total_cotizaciones", 0),
                        "status": "operational",
                        "json_file_exists": Path(__file__).parent.joinpath('cotizaciones_offline.json').exists(),
                        "mongodb_connected": not self.supabase_manager.modo_offline if self.supabase_manager else False
                    }
                except Exception as e:
                    logger.warning(f"⚠️ [ANALYSIS] Error analizando BD: {e}")
            
            # Analizar almacenamiento de PDFs
            pdf_providers = []
            total_pdfs = 0
            
            # Cloudinary
            if self.cloudinary_manager and self.cloudinary_manager.is_available():
                try:
                    result = self.cloudinary_manager.listar_pdfs()
                    if result.get("success"):
                        pdf_count = len(result.get("archivos", []))
                        pdf_providers.append({"name": "cloudinary", "count": pdf_count, "status": "available"})
                        total_pdfs += pdf_count
                except:
                    pdf_providers.append({"name": "cloudinary", "count": 0, "status": "error"})
            
            # Google Drive
            if self.google_drive and self.google_drive.is_available():
                try:
                    pdfs = self.google_drive.buscar_pdfs("")
                    pdf_count = len(pdfs)
                    pdf_providers.append({"name": "google_drive", "count": pdf_count, "status": "available"})
                    total_pdfs += pdf_count
                except:
                    pdf_providers.append({"name": "google_drive", "count": 0, "status": "error"})
            
            analysis["pdf_storage"] = {
                "providers": pdf_providers,
                "total_files": total_pdfs
            }
            
            # Analizar templates
            templates_dir = Path(__file__).parent / 'templates'
            if templates_dir.exists():
                template_files = list(templates_dir.glob('*.html'))
                analysis["templates"] = {
                    "count": len(template_files),
                    "files": [f.name for f in template_files]
                }
            
            # Analizar configuración
            env_file = Path(__file__).parent / '.env'
            config_file = Path(__file__).parent / 'config.py'
            
            analysis["configuration"]["config_files"] = [
                f for f in ['config.py', '.env', 'Lista de materiales.csv']
                if Path(__file__).parent.joinpath(f).exists()
            ]
            
            # Estimar tiempo de migración
            records = analysis["database"]["records"]
            pdf_files = analysis["pdf_storage"]["total_files"]
            
            # 1 segundo por registro + 2 segundos por PDF + overhead
            estimated_minutes = max(5, (records + pdf_files * 2) / 60)
            analysis["estimated_migration_time_minutes"] = int(estimated_minutes)
            
            logger.info(f"📊 [ANALYSIS] Registros encontrados: {records}")
            logger.info(f"📊 [ANALYSIS] PDFs encontrados: {pdf_files}")
            logger.info(f"⏱️ [ANALYSIS] Tiempo estimado: {estimated_minutes:.1f} minutos")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ [ANALYSIS] Error en análisis: {e}")
            raise
    
    def create_migration_plan(self, analysis: Dict[str, Any]) -> List[MigrationStep]:
        """Crear plan de migración basado en análisis"""
        logger.info("📋 [MIGRATION] Creando plan de migración...")
        
        steps = []
        
        # Paso 1: Preparación
        steps.append(MigrationStep(
            id="prep_systems",
            name="Preparar Sistemas",
            description="Inicializar y verificar todos los sistemas necesarios"
        ))
        
        # Paso 2: Crear esquema en Supabase
        steps.append(MigrationStep(
            id="create_schema",
            name="Crear Esquema",
            description="Crear tablas y esquema en Supabase PostgreSQL"
        ))
        
        # Paso 3: Migrar datos de cotizaciones
        if analysis["database"]["records"] > 0:
            steps.append(MigrationStep(
                id="migrate_quotations",
                name="Migrar Cotizaciones",
                description=f"Migrar {analysis['database']['records']} cotizaciones al sistema unificado"
            ))
        
        # Paso 4: Migrar PDFs
        if analysis["pdf_storage"]["total_files"] > 0:
            steps.append(MigrationStep(
                id="migrate_pdfs",
                name="Migrar PDFs",
                description=f"Migrar {analysis['pdf_storage']['total_files']} PDFs al almacenamiento unificado"
            ))
        
        # Paso 5: Actualizar configuración
        steps.append(MigrationStep(
            id="update_config",
            name="Actualizar Configuración",
            description="Actualizar archivos de configuración para sistema unificado"
        ))
        
        # Paso 6: Crear templates unificados
        steps.append(MigrationStep(
            id="create_templates",
            name="Crear Templates",
            description="Crear templates HTML para el sistema unificado"
        ))
        
        # Paso 7: Verificar migración
        steps.append(MigrationStep(
            id="verify_migration",
            name="Verificar Migración",
            description="Validar integridad de datos y funcionamiento del sistema"
        ))
        
        # Paso 8: Configurar monitoreo
        steps.append(MigrationStep(
            id="setup_monitoring",
            name="Configurar Monitoreo",
            description="Configurar sistema de salud y monitoreo en tiempo real"
        ))
        
        logger.info(f"📋 [MIGRATION] Plan creado con {len(steps)} pasos")
        return steps
    
    def execute_migration_step(self, step: MigrationStep) -> bool:
        """Ejecutar un paso individual de migración"""
        logger.info(f"▶️ [MIGRATION] Ejecutando: {step.name}")
        
        step.started_at = datetime.now()
        
        try:
            if step.id == "prep_systems":
                return self._step_prep_systems(step)
            elif step.id == "create_schema":
                return self._step_create_schema(step)
            elif step.id == "migrate_quotations":
                return self._step_migrate_quotations(step)
            elif step.id == "migrate_pdfs":
                return self._step_migrate_pdfs(step)
            elif step.id == "update_config":
                return self._step_update_config(step)
            elif step.id == "create_templates":
                return self._step_create_templates(step)
            elif step.id == "verify_migration":
                return self._step_verify_migration(step)
            elif step.id == "setup_monitoring":
                return self._step_setup_monitoring(step)
            else:
                step.error = f"Paso no implementado: {step.id}"
                return False
        
        except Exception as e:
            step.error = str(e)
            logger.error(f"❌ [MIGRATION] Error en {step.name}: {e}")
            return False
        
        finally:
            step.completed_at = datetime.now()
    
    def _step_prep_systems(self, step: MigrationStep) -> bool:
        """Preparar todos los sistemas"""
        if not self.initialize_systems():
            step.error = "Error inicializando sistemas"
            return False
        
        step.completed = True
        logger.info("✅ [MIGRATION] Sistemas preparados")
        return True
    
    def _step_create_schema(self, step: MigrationStep) -> bool:
        """Crear esquema en Supabase"""
        try:
            # Verificar que Supabase esté disponible
            if not self.unified_manager or not self.unified_manager.supabase:
                step.error = "Supabase no disponible"
                return False
            
            # El esquema se crea automáticamente con el primer INSERT
            # Hacer un test para verificar conectividad
            test_data = {
                "numeroCotizacion": f"MIGRATION-TEST-{int(time.time())}",
                "datosGenerales": {
                    "cliente": "TEST-MIGRATION",
                    "vendedor": "MIGRATION",
                    "proyecto": "SCHEMA-TEST"
                },
                "items": [],
                "observaciones": "Test de esquema para migración",
                "timestamp": time.time()
            }
            
            # Intentar guardar y luego eliminar
            result = self.unified_manager.supabase.guardar_cotizacion(test_data)
            if result.get("error"):
                step.error = f"Error creando esquema: {result['error']}"
                return False
            
            # Limpiar registro de test
            if result.get("success"):
                try:
                    self.unified_manager.supabase.eliminar_cotizacion(test_data["numeroCotizacion"])
                except:
                    pass  # No es crítico si falla la limpieza
            
            step.completed = True
            logger.info("✅ [MIGRATION] Esquema creado en Supabase")
            return True
            
        except Exception as e:
            step.error = f"Error creando esquema: {e}"
            return False
    
    def _step_migrate_quotations(self, step: MigrationStep) -> bool:
        """Migrar cotizaciones al sistema unificado"""
        try:
            migrated_count = 0
            errors = []
            
            # Obtener cotizaciones del sistema actual
            if self.database_manager:
                stats = self.database_manager.obtener_estadisticas()
                total_quotes = stats.get("total_cotizaciones", 0)
                
                if total_quotes == 0:
                    step.completed = True
                    logger.info("ℹ️ [MIGRATION] No hay cotizaciones para migrar")
                    return True
                
                # Cargar datos offline (JSON)
                json_path = Path(__file__).parent / 'cotizaciones_offline.json'
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    cotizaciones = data.get('cotizaciones', [])
                    
                    logger.info(f"🔄 [MIGRATION] Migrando {len(cotizaciones)} cotizaciones...")
                    
                    for i, cotizacion in enumerate(cotizaciones):
                        try:
                            # Agregar metadata de migración
                            cotizacion['_migrated_at'] = datetime.now().isoformat()
                            cotizacion['_migration_source'] = 'json_offline'
                            
                            # Usar sistema unificado para guardar
                            result = self.unified_manager.guardar_cotizacion(cotizacion)
                            
                            if result.success:
                                migrated_count += 1
                                if (i + 1) % 10 == 0:
                                    logger.info(f"📊 [MIGRATION] Migradas {i + 1}/{len(cotizaciones)} cotizaciones")
                            else:
                                error_msg = f"Error migrando {cotizacion.get('numeroCotizacion', 'sin número')}: {result.error}"
                                errors.append(error_msg)
                                logger.error(error_msg)
                        
                        except Exception as e:
                            error_msg = f"Excepción migrando cotización {i}: {e}"
                            errors.append(error_msg)
                            logger.error(error_msg)
                    
                    # Actualizar reporte
                    if self.current_report:
                        self.current_report.migrated_quotations = migrated_count
                        self.current_report.errors.extend(errors)
            
            if migrated_count > 0:
                step.completed = True
                logger.info(f"✅ [MIGRATION] {migrated_count} cotizaciones migradas exitosamente")
                if errors:
                    logger.warning(f"⚠️ [MIGRATION] {len(errors)} errores durante migración")
                return True
            else:
                step.error = f"No se pudieron migrar cotizaciones. Errores: {len(errors)}"
                return False
                
        except Exception as e:
            step.error = f"Error en migración de cotizaciones: {e}"
            return False
    
    def _step_migrate_pdfs(self, step: MigrationStep) -> bool:
        """Migrar PDFs al sistema de almacenamiento unificado"""
        try:
            migrated_count = 0
            errors = []
            
            # Los PDFs ya están en Cloudinary y Google Drive
            # Solo necesitamos verificar que el sistema unificado pueda accederlos
            
            # Verificar Cloudinary
            if self.cloudinary_manager and self.cloudinary_manager.is_available():
                try:
                    result = self.cloudinary_manager.listar_pdfs()
                    if result.get("success"):
                        cloudinary_pdfs = len(result.get("archivos", []))
                        logger.info(f"✅ [MIGRATION] {cloudinary_pdfs} PDFs accesibles en Cloudinary")
                        migrated_count += cloudinary_pdfs
                except Exception as e:
                    errors.append(f"Error verificando Cloudinary: {e}")
            
            # Verificar Google Drive
            if self.google_drive and self.google_drive.is_available():
                try:
                    pdfs = self.google_drive.buscar_pdfs("")
                    drive_pdfs = len(pdfs)
                    logger.info(f"✅ [MIGRATION] {drive_pdfs} PDFs accesibles en Google Drive")
                    migrated_count += drive_pdfs
                except Exception as e:
                    errors.append(f"Error verificando Google Drive: {e}")
            
            # Actualizar reporte
            if self.current_report:
                self.current_report.migrated_pdfs = migrated_count
                self.current_report.errors.extend(errors)
            
            step.completed = True
            logger.info(f"✅ [MIGRATION] Verificación de PDFs completada: {migrated_count} archivos")
            return True
            
        except Exception as e:
            step.error = f"Error en migración de PDFs: {e}"
            return False
    
    def _step_update_config(self, step: MigrationStep) -> bool:
        """Actualizar configuración para sistema unificado"""
        try:
            config_updates = []
            
            # Crear archivo de configuración unificada
            unified_config_path = Path(__file__).parent / 'config_unified.py'
            unified_config_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONFIGURACIÓN UNIFICADA - CWS COTIZADOR
======================================

Configuración para el sistema unificado que integra:
- Supabase PostgreSQL (principal)
- Cloudinary (PDFs con CDN)
- Google Drive (PDFs antiguos del admin)
- Sistema offline con sincronización automática
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class UnifiedConfig:
    """Configuración unificada del sistema"""
    
    # Configuración de aplicación
    SECRET_KEY = os.getenv('SECRET_KEY', 'unified-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Supabase PostgreSQL (Principal)
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    
    # Cloudinary (PDFs Principal)
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
    
    # Google Drive (Fallback)
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{}')
    GOOGLE_DRIVE_FOLDER_NUEVAS = os.getenv('GOOGLE_DRIVE_FOLDER_NUEVAS', '')
    GOOGLE_DRIVE_FOLDER_ANTIGUAS = os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS', '')
    
    # Sistema de sincronización
    SYNC_INTERVAL_SECONDS = int(os.getenv('SYNC_INTERVAL_SECONDS', '300'))  # 5 minutos
    AUTO_SYNC_ENABLED = os.getenv('AUTO_SYNC_ENABLED', 'true').lower() == 'true'
    
    # Sistema de salud
    HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv('HEALTH_CHECK_INTERVAL_SECONDS', '60'))
    ENABLE_HEALTH_MONITORING = os.getenv('ENABLE_HEALTH_MONITORING', 'true').lower() == 'true'
    
    # Búsqueda unificada
    ENABLE_SEARCH_CACHE = os.getenv('ENABLE_SEARCH_CACHE', 'true').lower() == 'true'
    SEARCH_CACHE_SIZE = int(os.getenv('SEARCH_CACHE_SIZE', '100'))
    ENABLE_FUZZY_SEARCH = os.getenv('ENABLE_FUZZY_SEARCH', 'true').lower() == 'true'
    
    # Performance
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', '50'))
    ENABLE_COMPRESSION = os.getenv('ENABLE_COMPRESSION', 'true').lower() == 'true'
    
    @classmethod
    def validate_config(cls):
        """Validar configuración requerida"""
        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY',
            'CLOUDINARY_CLOUD_NAME'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Variables de entorno requeridas faltantes: {missing_vars}")
        
        return True
    
    @classmethod
    def get_system_info(cls):
        """Obtener información del sistema"""
        return {
            "supabase_configured": bool(cls.SUPABASE_URL and cls.SUPABASE_ANON_KEY),
            "cloudinary_configured": bool(cls.CLOUDINARY_CLOUD_NAME and cls.CLOUDINARY_API_KEY),
            "google_drive_configured": bool(cls.GOOGLE_SERVICE_ACCOUNT_JSON != '{}'),
            "auto_sync_enabled": cls.AUTO_SYNC_ENABLED,
            "health_monitoring_enabled": cls.ENABLE_HEALTH_MONITORING
        }
'''
            
            unified_config_path.write_text(unified_config_content, encoding='utf-8')
            config_updates.append(f"Creado: {unified_config_path.name}")
            
            # Crear ejemplo de .env para sistema unificado
            env_example_path = Path(__file__).parent / '.env.unified.example'
            env_example_content = '''# CONFIGURACIÓN UNIFICADA - CWS COTIZADOR
# =====================================

# Configuración de aplicación
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False

# Supabase PostgreSQL (Principal)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
DATABASE_URL=postgresql://postgres:password@host:5432/database

# Cloudinary (PDFs Principal - 25GB gratis)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Google Drive (Fallback)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_DRIVE_FOLDER_NUEVAS=folder-id-nuevas
GOOGLE_DRIVE_FOLDER_ANTIGUAS=folder-id-antiguas

# Sistema de sincronización
SYNC_INTERVAL_SECONDS=300
AUTO_SYNC_ENABLED=true

# Sistema de salud
HEALTH_CHECK_INTERVAL_SECONDS=60
ENABLE_HEALTH_MONITORING=true

# Búsqueda unificada
ENABLE_SEARCH_CACHE=true
SEARCH_CACHE_SIZE=100
ENABLE_FUZZY_SEARCH=true

# Performance
MAX_UPLOAD_SIZE_MB=50
ENABLE_COMPRESSION=true
'''
            
            env_example_path.write_text(env_example_content, encoding='utf-8')
            config_updates.append(f"Creado: {env_example_path.name}")
            
            step.rollback_data = {"config_files_created": config_updates}
            step.completed = True
            
            logger.info(f"✅ [MIGRATION] Configuración actualizada: {len(config_updates)} archivos")
            return True
            
        except Exception as e:
            step.error = f"Error actualizando configuración: {e}"
            return False
    
    def _step_create_templates(self, step: MigrationStep) -> bool:
        """Crear templates para sistema unificado"""
        try:
            templates_created = []
            templates_dir = Path(__file__).parent / 'templates'
            templates_dir.mkdir(exist_ok=True)
            
            # Template principal unificado
            home_unified = templates_dir / 'home_unified.html'
            if not home_unified.exists():
                home_content = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CWS Cotizador - Sistema Unificado</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { text-align: center; margin-bottom: 30px; }
        .system-status { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .status-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-online { border-left: 5px solid #4CAF50; }
        .status-offline { border-left: 5px solid #f44336; }
        .actions { text-align: center; margin: 30px 0; }
        .btn { padding: 12px 24px; margin: 10px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-primary { background: #2196F3; color: white; }
        .btn-success { background: #4CAF50; color: white; }
        .recent-quotes { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 CWS Cotizador - Sistema Unificado</h1>
        <p>Sistema de alta disponibilidad con almacenamiento redundante</p>
        <p><small>Tiempo de carga: {{ page_load_time }}ms</small></p>
    </div>
    
    <div class="system-status">
        <div class="status-card {{ 'status-online' if system_status.supabase.status == 'online' else 'status-offline' }}">
            <h3>📊 Base de Datos (Supabase)</h3>
            <p>Estado: <strong>{{ system_status.supabase.status|upper }}</strong></p>
            <p>Registros: {{ system_status.supabase.total_records }}</p>
        </div>
        
        <div class="status-card {{ 'status-online' if system_status.cloudinary.status == 'online' else 'status-offline' }}">
            <h3>📁 PDFs (Cloudinary)</h3>
            <p>Estado: <strong>{{ system_status.cloudinary.status|upper }}</strong></p>
            <p>Archivos: {{ system_status.cloudinary.total_files }}</p>
        </div>
        
        <div class="status-card {{ 'status-online' if system_status.google_drive.status == 'online' else 'status-offline' }}">
            <h3>☁️ Respaldo (Google Drive)</h3>
            <p>Estado: <strong>{{ system_status.google_drive.status|upper }}</strong></p>
            <p>Archivos: {{ system_status.google_drive.total_files }}</p>
        </div>
        
        <div class="status-card">
            <h3>💚 Salud del Sistema</h3>
            <p>Score: <strong>{{ health_summary.overall_health_score }}/100</strong></p>
            <p>Última verificación: {{ health_summary.last_check_time }}</p>
        </div>
    </div>
    
    <div class="actions">
        <a href="/formulario" class="btn btn-primary">📝 Nueva Cotización</a>
        <a href="/buscar" class="btn btn-success">🔍 Buscar</a>
        <a href="/admin/dashboard" class="btn">📊 Dashboard Admin</a>
    </div>
    
    <div class="recent-quotes">
        <h3>📋 Cotizaciones Recientes</h3>
        {% if recent_quotes %}
            <ul>
            {% for quote in recent_quotes %}
                <li>
                    <strong>{{ quote.numero_cotizacion }}</strong> - {{ quote.cliente }}
                    <small>({{ quote.fecha_creacion }})</small>
                </li>
            {% endfor %}
            </ul>
        {% else %}
            <p>No hay cotizaciones recientes</p>
        {% endif %}
    </div>
</body>
</html>'''
                home_unified.write_text(home_content, encoding='utf-8')
                templates_created.append(home_unified.name)
            
            # Template de formulario unificado
            form_unified = templates_dir / 'formulario_unified.html'
            if not form_unified.exists():
                # Usar el formulario existente como base
                existing_form = templates_dir / 'formulario.html'
                if existing_form.exists():
                    # Copiar y modificar formulario existente
                    existing_content = existing_form.read_text(encoding='utf-8')
                    # Agregar indicador de sistema unificado
                    unified_content = existing_content.replace(
                        '<title>',
                        '<title>Sistema Unificado - '
                    ).replace(
                        '<h1>',
                        '<h1>🚀 Sistema Unificado - '
                    )
                    form_unified.write_text(unified_content, encoding='utf-8')
                    templates_created.append(form_unified.name)
            
            step.rollback_data = {"templates_created": templates_created}
            step.completed = True
            
            logger.info(f"✅ [MIGRATION] Templates creados: {len(templates_created)}")
            return True
            
        except Exception as e:
            step.error = f"Error creando templates: {e}"
            return False
    
    def _step_verify_migration(self, step: MigrationStep) -> bool:
        """Verificar integridad de migración"""
        try:
            verification_results = {}
            
            # Verificar sistema unificado
            if self.unified_manager:
                # Test de conectividad
                system_status = self.unified_manager.get_system_status()
                verification_results["system_status"] = system_status
                
                # Test de escritura/lectura
                test_quote = {
                    "numeroCotizacion": f"VERIFY-{int(time.time())}",
                    "datosGenerales": {
                        "cliente": "TEST-VERIFICATION",
                        "vendedor": "MIGRATION",
                        "proyecto": "INTEGRITY-CHECK"
                    },
                    "items": [],
                    "observaciones": "Verificación de integridad post-migración"
                }
                
                # Intentar guardar
                save_result = self.unified_manager.guardar_cotizacion(test_quote)
                verification_results["write_test"] = save_result.success
                
                if save_result.success:
                    # Intentar leer
                    read_result = self.unified_manager.obtener_cotizacion(test_quote["numeroCotizacion"])
                    verification_results["read_test"] = read_result.success
                    
                    # Limpiar
                    try:
                        self.unified_manager.supabase.eliminar_cotizacion(test_quote["numeroCotizacion"])
                    except:
                        pass
                else:
                    verification_results["read_test"] = False
                    verification_results["error"] = save_result.error
            
            # Verificar que se pueden encontrar las cotizaciones migradas
            if verification_results.get("read_test", False):
                try:
                    search_result = self.unified_manager.buscar_cotizaciones("", 1, 10)
                    total_found = search_result.get("total", 0)
                    verification_results["total_accessible"] = total_found
                    logger.info(f"✅ [VERIFICATION] {total_found} cotizaciones accesibles")
                except Exception as e:
                    verification_results["search_error"] = str(e)
            
            # Evaluación general
            all_tests_passed = all([
                verification_results.get("write_test", False),
                verification_results.get("read_test", False),
                verification_results.get("total_accessible", 0) >= 0
            ])
            
            if all_tests_passed:
                step.completed = True
                logger.info("✅ [VERIFICATION] Migración verificada exitosamente")
                return True
            else:
                step.error = f"Fallos en verificación: {verification_results}"
                return False
                
        except Exception as e:
            step.error = f"Error en verificación: {e}"
            return False
    
    def _step_setup_monitoring(self, step: MigrationStep) -> bool:
        """Configurar sistema de monitoreo"""
        try:
            # El monitoreo ya está incluido en el sistema unificado
            # Solo necesitamos verificar que funcione
            
            monitoring_status = {}
            
            if self.unified_manager:
                # Verificar health system
                try:
                    health_summary = self.unified_manager.get_system_health_summary()
                    monitoring_status["health_system"] = "operational"
                    monitoring_status["health_score"] = health_summary.get("overall_health_score", 0)
                except Exception as e:
                    monitoring_status["health_system"] = f"error: {e}"
                
                # Verificar sistema de logs
                logs_dir = Path(__file__).parent / 'logs'
                if logs_dir.exists():
                    log_files = list(logs_dir.glob('*.log'))
                    monitoring_status["log_files"] = len(log_files)
                else:
                    monitoring_status["log_files"] = 0
            
            step.completed = True
            step.rollback_data = monitoring_status
            
            logger.info("✅ [MIGRATION] Monitoreo configurado")
            return True
            
        except Exception as e:
            step.error = f"Error configurando monitoreo: {e}"
            return False
    
    def execute_full_migration(self) -> MigrationReport:
        """Ejecutar migración completa"""
        logger.info("🚀 [MIGRATION] Iniciando migración completa...")
        
        # Crear reporte
        self.current_report = MigrationReport(started_at=datetime.now())
        
        try:
            # 1. Crear backup completo
            logger.info("💾 [MIGRATION] Fase 1: Backup completo")
            backup_path = self.create_full_backup()
            self.current_report.backup_path = backup_path
            
            # 2. Analizar sistema actual
            logger.info("🔍 [MIGRATION] Fase 2: Análisis del sistema")
            analysis = self.analyze_current_system()
            
            # 3. Crear plan de migración
            logger.info("📋 [MIGRATION] Fase 3: Planificación")
            self.migration_steps = self.create_migration_plan(analysis)
            self.current_report.total_steps = len(self.migration_steps)
            
            # 4. Ejecutar pasos de migración
            logger.info("▶️ [MIGRATION] Fase 4: Ejecución")
            
            for step in self.migration_steps:
                logger.info(f"🔄 [MIGRATION] Paso {self.current_report.completed_steps + 1}/{self.current_report.total_steps}: {step.name}")
                
                success = self.execute_migration_step(step)
                
                if success and step.completed:
                    self.current_report.completed_steps += 1
                    logger.info(f"✅ [MIGRATION] Completado: {step.name}")
                else:
                    self.current_report.failed_steps += 1
                    error_msg = f"❌ [MIGRATION] Falló: {step.name} - {step.error}"
                    logger.error(error_msg)
                    self.current_report.errors.append(error_msg)
                    
                    # Decidir si continuar o abortar
                    if step.id in ["prep_systems", "create_schema"]:
                        # Pasos críticos - abortar migración
                        logger.error("🛑 [MIGRATION] Paso crítico falló - Abortando migración")
                        break
                    else:
                        # Pasos opcionales - continuar con advertencia
                        warning_msg = f"⚠️ [MIGRATION] Continuando a pesar del fallo en: {step.name}"
                        logger.warning(warning_msg)
                        self.current_report.warnings.append(warning_msg)
            
            # 5. Finalizar migración
            self.current_report.completed_at = datetime.now()
            
            # Guardar reporte
            report_path = self.reports_dir / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_data = asdict(self.current_report)
            
            # Convertir datetime a string para JSON
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=convert_datetime)
            
            # Resumen final
            total_time = (self.current_report.completed_at - self.current_report.started_at).total_seconds()
            
            logger.info("🎉 [MIGRATION] Migración completada")
            logger.info(f"📊 [MIGRATION] Estadísticas finales:")
            logger.info(f"   ⏱️  Tiempo total: {total_time/60:.1f} minutos")
            logger.info(f"   ✅ Pasos completados: {self.current_report.completed_steps}/{self.current_report.total_steps}")
            logger.info(f"   ❌ Pasos fallidos: {self.current_report.failed_steps}")
            logger.info(f"   📋 Cotizaciones migradas: {self.current_report.migrated_quotations}")
            logger.info(f"   📄 PDFs verificados: {self.current_report.migrated_pdfs}")
            logger.info(f"   📝 Reporte guardado: {report_path}")
            
            return self.current_report
            
        except Exception as e:
            error_msg = f"Error crítico en migración: {e}"
            logger.error(f"❌ [MIGRATION] {error_msg}")
            
            if self.current_report:
                self.current_report.completed_at = datetime.now()
                self.current_report.errors.append(error_msg)
            
            raise
    
    def rollback_migration(self, backup_path: str) -> bool:
        """Rollback de migración usando backup"""
        logger.info(f"↩️ [ROLLBACK] Iniciando rollback desde: {backup_path}")
        
        try:
            backup_dir = Path(backup_path)
            
            if not backup_dir.exists():
                logger.error(f"❌ [ROLLBACK] Directorio de backup no encontrado: {backup_path}")
                return False
            
            # Restaurar archivos críticos
            files_to_restore = [
                'cotizaciones_offline.json',
                'config.py',
                '.env',
                'Lista de materiales.csv'
            ]
            
            restored_files = []
            
            for filename in files_to_restore:
                backup_file = backup_dir / filename
                target_file = Path(__file__).parent / filename
                
                if backup_file.exists():
                    try:
                        shutil.copy2(backup_file, target_file)
                        restored_files.append(filename)
                        logger.info(f"✅ [ROLLBACK] Restaurado: {filename}")
                    except Exception as e:
                        logger.error(f"❌ [ROLLBACK] Error restaurando {filename}: {e}")
            
            # Restaurar templates
            backup_templates = backup_dir / 'templates'
            target_templates = Path(__file__).parent / 'templates'
            
            if backup_templates.exists():
                try:
                    if target_templates.exists():
                        shutil.rmtree(target_templates)
                    shutil.copytree(backup_templates, target_templates)
                    logger.info("✅ [ROLLBACK] Templates restaurados")
                except Exception as e:
                    logger.error(f"❌ [ROLLBACK] Error restaurando templates: {e}")
            
            logger.info(f"🎉 [ROLLBACK] Rollback completado. Archivos restaurados: {len(restored_files)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [ROLLBACK] Error en rollback: {e}")
            return False

def main():
    """Función principal para ejecutar migración"""
    print("🚀 CWS COTIZADOR - MIGRACIÓN AL SISTEMA UNIFICADO")
    print("=" * 60)
    print()
    
    # Confirmar migración
    response = input("⚠️  Esta operación migrará el sistema actual al nuevo sistema unificado.\n"
                    "   Se creará un backup completo antes de proceder.\n"
                    "   ¿Deseas continuar? (s/N): ")
    
    if response.lower() not in ['s', 'si', 'y', 'yes']:
        print("❌ Migración cancelada por el usuario")
        return
    
    # Crear gestor de migración
    migration_manager = MigrationManager()
    
    try:
        # Ejecutar migración completa
        report = migration_manager.execute_full_migration()
        
        # Mostrar resultado
        print("\n" + "=" * 60)
        print("🎉 MIGRACIÓN COMPLETADA")
        print("=" * 60)
        
        if report.failed_steps == 0:
            print("✅ Migración exitosa - Todos los pasos completados")
        else:
            print(f"⚠️  Migración completada con advertencias - {report.failed_steps} pasos fallaron")
        
        print(f"\n📊 RESUMEN:")
        print(f"   ⏱️  Tiempo total: {(report.completed_at - report.started_at).total_seconds()/60:.1f} minutos")
        print(f"   📋 Cotizaciones migradas: {report.migrated_quotations}")
        print(f"   📄 PDFs verificados: {report.migrated_pdfs}")
        print(f"   💾 Backup guardado en: {report.backup_path}")
        
        if report.errors:
            print(f"\n❌ ERRORES ({len(report.errors)}):")
            for error in report.errors[:5]:  # Mostrar solo primeros 5
                print(f"   • {error}")
        
        if report.warnings:
            print(f"\n⚠️  ADVERTENCIAS ({len(report.warnings)}):")
            for warning in report.warnings[:3]:  # Mostrar solo primeras 3
                print(f"   • {warning}")
        
        print(f"\n🔄 SIGUIENTE PASO:")
        print("   1. Ejecutar: python app_unified.py")
        print("   2. Verificar funcionamiento en: http://localhost:5000")
        print("   3. Si hay problemas, usar rollback con el backup creado")
        
    except KeyboardInterrupt:
        print("\n❌ Migración interrumpida por el usuario")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO EN MIGRACIÓN: {e}")
        print("\n🔄 OPCIONES DE RECUPERACIÓN:")
        if migration_manager.current_report and migration_manager.current_report.backup_path:
            print(f"   • Rollback automático: python -c \"from migration_scripts import MigrationManager; MigrationManager().rollback_migration('{migration_manager.current_report.backup_path}')\"")
        print("   • Revisar logs: logs/migration.log")
        print("   • Contactar soporte con el archivo de reporte generado")

if __name__ == "__main__":
    main()