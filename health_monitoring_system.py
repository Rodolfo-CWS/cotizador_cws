#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HEALTH MONITORING & INTEGRITY VALIDATION SYSTEM
==============================================

Sistema avanzado de monitoreo de salud y validación de integridad que:
- Monitorea todos los sistemas de almacenamiento
- Valida consistencia de datos entre fuentes
- Detecta anomalías y degradación de performance
- Genera alertas automáticas
- Proporciona métricas en tiempo real
- Realiza auto-recuperación cuando es posible
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import statistics
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Estados de salud"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"

class AlertLevel(Enum):
    """Niveles de alerta"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class CheckType(Enum):
    """Tipos de verificación"""
    CONNECTIVITY = "connectivity"
    PERFORMANCE = "performance"
    INTEGRITY = "integrity"
    CAPACITY = "capacity"
    CONSISTENCY = "consistency"
    SECURITY = "security"

@dataclass
class HealthMetric:
    """Métrica de salud"""
    name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    status: HealthStatus = HealthStatus.HEALTHY
    
    def __post_init__(self):
        if self.value >= self.threshold_critical:
            self.status = HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            self.status = HealthStatus.WARNING
        else:
            self.status = HealthStatus.HEALTHY

@dataclass
class HealthCheck:
    """Verificación de salud"""
    check_id: str
    name: str
    description: str
    check_type: CheckType
    target_system: str
    status: HealthStatus
    last_run: datetime
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    duration_ms: int
    error_message: str = ""
    metrics: List[HealthMetric] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = []

@dataclass
class Alert:
    """Alerta del sistema"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    system: str
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    resolution_message: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class IntegrityReport:
    """Reporte de integridad"""
    report_id: str
    systems_checked: List[str]
    total_records: int
    consistent_records: int
    inconsistent_records: int
    missing_records: int
    duplicate_records: int
    corruption_detected: bool
    issues: List[str]
    timestamp: datetime
    duration_ms: int
    
    @property
    def consistency_rate(self) -> float:
        if self.total_records == 0:
            return 100.0
        return (self.consistent_records / self.total_records) * 100

class HealthMonitoringSystem:
    """Sistema de monitoreo de salud y validación de integridad"""
    
    def __init__(self, storage_manager):
        """Inicializar sistema de monitoreo"""
        self.storage_manager = storage_manager
        
        # Estado del sistema
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_health_check = None
        
        # Datos de monitoreo
        self.health_checks: Dict[str, HealthCheck] = {}
        self.active_alerts: List[Alert] = []
        self.resolved_alerts: List[Alert] = []
        self.integrity_reports: List[IntegrityReport] = []
        
        # Métricas en tiempo real
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        
        # Configuración
        self.config = {
            "health_check_interval_seconds": int(os.getenv('HEALTH_CHECK_INTERVAL', '300')),  # 5 min
            "integrity_check_interval_hours": int(os.getenv('INTEGRITY_CHECK_INTERVAL', '6')),  # 6 horas
            "performance_check_interval_seconds": int(os.getenv('PERFORMANCE_CHECK_INTERVAL', '60')),  # 1 min
            "enable_auto_recovery": os.getenv('ENABLE_AUTO_RECOVERY', 'true').lower() == 'true',
            "enable_alerting": os.getenv('ENABLE_ALERTING', 'true').lower() == 'true',
            "alert_email": os.getenv('ALERT_EMAIL', ''),
            "max_alerts_per_hour": int(os.getenv('MAX_ALERTS_PER_HOUR', '10')),
            "metrics_retention_hours": int(os.getenv('METRICS_RETENTION_HOURS', '24')),
            
            # Umbrales de performance
            "response_time_warning_ms": int(os.getenv('RESPONSE_TIME_WARNING_MS', '5000')),
            "response_time_critical_ms": int(os.getenv('RESPONSE_TIME_CRITICAL_MS', '10000')),
            "error_rate_warning_percent": float(os.getenv('ERROR_RATE_WARNING_PERCENT', '5.0')),
            "error_rate_critical_percent": float(os.getenv('ERROR_RATE_CRITICAL_PERCENT', '10.0')),
            "disk_usage_warning_percent": float(os.getenv('DISK_USAGE_WARNING_PERCENT', '80.0')),
            "disk_usage_critical_percent": float(os.getenv('DISK_USAGE_CRITICAL_PERCENT', '90.0')),
            
            # Umbrales de integridad
            "consistency_warning_percent": float(os.getenv('CONSISTENCY_WARNING_PERCENT', '95.0')),
            "consistency_critical_percent": float(os.getenv('CONSISTENCY_CRITICAL_PERCENT', '90.0'))
        }
        
        # Archivos de persistencia
        self.alerts_file = Path("health_alerts.json")
        self.reports_file = Path("integrity_reports.json")
        self.metrics_file = Path("health_metrics.json")
        
        # Contadores de alertas
        self.alert_counts = defaultdict(int)
        self.last_alert_reset = datetime.now()
        
        # Inicializar verificaciones
        self._initialize_health_checks()
        
        # Cargar estado persistente
        self._load_persistent_state()
        
        logger.info("💚 [HEALTH_MONITOR] Sistema de monitoreo de salud iniciado")
        logger.info(f"   Intervalo verificaciones: {self.config['health_check_interval_seconds']}s")
        logger.info(f"   Intervalo integridad: {self.config['integrity_check_interval_hours']}h")
        logger.info(f"   Auto-recuperación: {'Habilitada' if self.config['enable_auto_recovery'] else 'Deshabilitada'}")
    
    def start_monitoring(self):
        """Iniciar monitoreo de salud"""
        if self.is_monitoring:
            logger.warning("⚠️ [HEALTH_MONITOR] Sistema ya está monitoreando")
            return
        
        logger.info("🚀 [HEALTH_MONITOR] Iniciando monitoreo...")
        
        # Verificación inicial
        try:
            self._run_all_health_checks()
            logger.info("✅ [HEALTH_MONITOR] Verificación inicial completada")
        except Exception as e:
            logger.error(f"❌ [HEALTH_MONITOR] Error en verificación inicial: {e}")
        
        # Iniciar hilo de monitoreo
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("✅ [HEALTH_MONITOR] Monitoreo iniciado")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        logger.info("🛑 [HEALTH_MONITOR] Deteniendo monitoreo...")
        
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        # Guardar estado final
        self._save_persistent_state()
        
        logger.info("✅ [HEALTH_MONITOR] Monitoreo detenido")
    
    def _initialize_health_checks(self):
        """Inicializar verificaciones de salud"""
        # Verificación de conectividad Supabase
        self.health_checks["supabase_connectivity"] = HealthCheck(
            check_id="supabase_connectivity",
            name="Conectividad Supabase",
            description="Verificar conectividad y respuesta de Supabase PostgreSQL",
            check_type=CheckType.CONNECTIVITY,
            target_system="supabase",
            status=HealthStatus.HEALTHY,
            last_run=datetime.now(),
            last_success=None,
            last_failure=None,
            duration_ms=0
        )
        
        # Verificación de conectividad Cloudinary
        self.health_checks["cloudinary_connectivity"] = HealthCheck(
            check_id="cloudinary_connectivity",
            name="Conectividad Cloudinary",
            description="Verificar conectividad y respuesta de Cloudinary",
            check_type=CheckType.CONNECTIVITY,
            target_system="cloudinary",
            status=HealthStatus.HEALTHY,
            last_run=datetime.now(),
            last_success=None,
            last_failure=None,
            duration_ms=0
        )
        
        # Verificación de Google Drive
        self.health_checks["google_drive_connectivity"] = HealthCheck(
            check_id="google_drive_connectivity",
            name="Conectividad Google Drive",
            description="Verificar conectividad y respuesta de Google Drive API",
            check_type=CheckType.CONNECTIVITY,
            target_system="google_drive",
            status=HealthStatus.HEALTHY,
            last_run=datetime.now(),
            last_success=None,
            last_failure=None,
            duration_ms=0
        )
        
        # Verificación de integridad de datos
        self.health_checks["data_integrity"] = HealthCheck(
            check_id="data_integrity",
            name="Integridad de Datos",
            description="Verificar consistencia entre Supabase y JSON local",
            check_type=CheckType.INTEGRITY,
            target_system="unified",
            status=HealthStatus.HEALTHY,
            last_run=datetime.now(),
            last_success=None,
            last_failure=None,
            duration_ms=0
        )
        
        # Verificación de performance
        self.health_checks["system_performance"] = HealthCheck(
            check_id="system_performance",
            name="Performance del Sistema",
            description="Verificar tiempos de respuesta y throughput",
            check_type=CheckType.PERFORMANCE,
            target_system="unified",
            status=HealthStatus.HEALTHY,
            last_run=datetime.now(),
            last_success=None,
            last_failure=None,
            duration_ms=0
        )
        
        # Verificación de capacidad de almacenamiento
        self.health_checks["storage_capacity"] = HealthCheck(
            check_id="storage_capacity",
            name="Capacidad de Almacenamiento",
            description="Verificar uso de espacio en todos los sistemas",
            check_type=CheckType.CAPACITY,
            target_system="unified",
            status=HealthStatus.HEALTHY,
            last_run=datetime.now(),
            last_success=None,
            last_failure=None,
            duration_ms=0
        )
    
    def _monitoring_loop(self):
        """Bucle principal de monitoreo"""
        logger.info("🔄 [HEALTH_MONITOR] Bucle de monitoreo iniciado")
        
        last_health_check = datetime.now() - timedelta(seconds=self.config['health_check_interval_seconds'])
        last_integrity_check = datetime.now() - timedelta(hours=self.config['integrity_check_interval_hours'])
        last_performance_check = datetime.now() - timedelta(seconds=self.config['performance_check_interval_seconds'])
        
        while self.is_monitoring:
            try:
                now = datetime.now()
                
                # Verificaciones de salud generales
                if (now - last_health_check).seconds >= self.config['health_check_interval_seconds']:
                    self._run_connectivity_checks()
                    self._run_capacity_checks()
                    last_health_check = now
                
                # Verificaciones de integridad (menos frecuentes)
                if (now - last_integrity_check).seconds >= (self.config['integrity_check_interval_hours'] * 3600):
                    self._run_integrity_check()
                    last_integrity_check = now
                
                # Verificaciones de performance (más frecuentes)
                if (now - last_performance_check).seconds >= self.config['performance_check_interval_seconds']:
                    self._run_performance_checks()
                    last_performance_check = now
                
                # Limpiar métricas antiguas
                self._cleanup_old_metrics()
                
                # Procesar auto-recuperación si está habilitada
                if self.config['enable_auto_recovery']:
                    self._attempt_auto_recovery()
                
                # Dormir hasta el próximo ciclo
                time.sleep(min(
                    self.config['performance_check_interval_seconds'],
                    30  # Máximo 30 segundos entre ciclos
                ))
                
            except Exception as e:
                logger.error(f"❌ [HEALTH_MONITOR] Error en bucle de monitoreo: {e}")
                time.sleep(60)  # Esperar 1 minuto en caso de error
        
        logger.info("🛑 [HEALTH_MONITOR] Bucle de monitoreo detenido")
    
    def _run_all_health_checks(self):
        """Ejecutar todas las verificaciones de salud"""
        logger.info("🔍 [HEALTH_CHECK] Ejecutando todas las verificaciones...")
        
        self._run_connectivity_checks()
        self._run_performance_checks()
        self._run_capacity_checks()
        
        # Verificación de integridad (más costosa, solo si es necesario)
        if not self.integrity_reports or (datetime.now() - self.integrity_reports[-1].timestamp).hours >= 6:
            self._run_integrity_check()
    
    def _run_connectivity_checks(self):
        """Ejecutar verificaciones de conectividad"""
        # Verificar Supabase
        self._check_supabase_connectivity()
        
        # Verificar Cloudinary
        self._check_cloudinary_connectivity()
        
        # Verificar Google Drive
        self._check_google_drive_connectivity()
    
    def _check_supabase_connectivity(self):
        """Verificar conectividad con Supabase"""
        check = self.health_checks["supabase_connectivity"]
        start_time = time.time()
        
        try:
            # Intentar operación simple
            test_result = self.storage_manager.supabase.obtener_estadisticas()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if test_result.get('error'):
                # Error en la operación
                check.status = HealthStatus.WARNING
                check.error_message = test_result['error']
                check.last_failure = datetime.now()
                check.consecutive_failures += 1
                
                self._create_alert(
                    AlertLevel.WARNING,
                    "Supabase Connection Issue",
                    f"Supabase respondió con error: {test_result['error']}",
                    "supabase"
                )
                
            elif duration_ms > self.config['response_time_critical_ms']:
                # Respuesta muy lenta
                check.status = HealthStatus.CRITICAL
                check.error_message = f"Tiempo de respuesta muy alto: {duration_ms}ms"
                check.last_failure = datetime.now()
                check.consecutive_failures += 1
                
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "Supabase Performance Critical",
                    f"Tiempo de respuesta crítico: {duration_ms}ms",
                    "supabase"
                )
                
            elif duration_ms > self.config['response_time_warning_ms']:
                # Respuesta lenta pero tolerable
                check.status = HealthStatus.WARNING
                check.error_message = f"Tiempo de respuesta elevado: {duration_ms}ms"
                check.consecutive_failures = 0
                check.last_success = datetime.now()
                
                self._create_alert(
                    AlertLevel.WARNING,
                    "Supabase Performance Warning",
                    f"Tiempo de respuesta elevado: {duration_ms}ms",
                    "supabase"
                )
                
            else:
                # Todo OK
                check.status = HealthStatus.HEALTHY
                check.error_message = ""
                check.consecutive_failures = 0
                check.last_success = datetime.now()
            
            # Registrar métrica
            metric = HealthMetric(
                name="supabase_response_time",
                value=duration_ms,
                unit="ms",
                threshold_warning=self.config['response_time_warning_ms'],
                threshold_critical=self.config['response_time_critical_ms'],
                timestamp=datetime.now()
            )
            check.metrics.append(metric)
            self.metrics_history["supabase_response_time"].append((datetime.now(), duration_ms))
            
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
        except Exception as e:
            # Error de conectividad
            duration_ms = int((time.time() - start_time) * 1000)
            
            check.status = HealthStatus.CRITICAL
            check.error_message = str(e)
            check.last_failure = datetime.now()
            check.consecutive_failures += 1
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
            self._create_alert(
                AlertLevel.CRITICAL,
                "Supabase Connection Failed",
                f"No se pudo conectar a Supabase: {str(e)}",
                "supabase"
            )
    
    def _check_cloudinary_connectivity(self):
        """Verificar conectividad con Cloudinary"""
        check = self.health_checks["cloudinary_connectivity"]
        start_time = time.time()
        
        try:
            if not self.storage_manager.cloudinary.is_available():
                # Cloudinary no está configurado
                check.status = HealthStatus.DOWN
                check.error_message = "Cloudinary no configurado"
                check.last_failure = datetime.now()
                check.duration_ms = int((time.time() - start_time) * 1000)
                check.last_run = datetime.now()
                return
            
            # Intentar obtener estadísticas
            stats_result = self.storage_manager.cloudinary.obtener_estadisticas()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if stats_result.get('error'):
                check.status = HealthStatus.CRITICAL
                check.error_message = stats_result['error']
                check.last_failure = datetime.now()
                check.consecutive_failures += 1
                
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "Cloudinary Connection Failed",
                    f"Error en Cloudinary: {stats_result['error']}",
                    "cloudinary"
                )
                
            else:
                check.status = HealthStatus.HEALTHY
                check.error_message = ""
                check.consecutive_failures = 0
                check.last_success = datetime.now()
                
                # Verificar uso de storage
                storage_usado = stats_result.get('storage_usado', 0)
                if storage_usado > 0:
                    usage_metric = HealthMetric(
                        name="cloudinary_storage_usage",
                        value=storage_usado,
                        unit="bytes",
                        threshold_warning=20 * 1024 * 1024 * 1024,  # 20GB
                        threshold_critical=24 * 1024 * 1024 * 1024,  # 24GB
                        timestamp=datetime.now()
                    )
                    check.metrics.append(usage_metric)
                    self.metrics_history["cloudinary_storage"].append((datetime.now(), storage_usado))
            
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            check.status = HealthStatus.CRITICAL
            check.error_message = str(e)
            check.last_failure = datetime.now()
            check.consecutive_failures += 1
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
            self._create_alert(
                AlertLevel.CRITICAL,
                "Cloudinary Check Failed",
                f"Error verificando Cloudinary: {str(e)}",
                "cloudinary"
            )
    
    def _check_google_drive_connectivity(self):
        """Verificar conectividad con Google Drive"""
        check = self.health_checks["google_drive_connectivity"]
        start_time = time.time()
        
        try:
            if not self.storage_manager.google_drive.is_available():
                check.status = HealthStatus.DOWN
                check.error_message = "Google Drive no configurado"
                check.last_failure = datetime.now()
                check.duration_ms = int((time.time() - start_time) * 1000)
                check.last_run = datetime.now()
                return
            
            # Intentar listar archivos
            test_pdfs = self.storage_manager.google_drive.buscar_pdfs("")
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if test_pdfs is not None:  # None indica error, [] es válido
                check.status = HealthStatus.HEALTHY
                check.error_message = ""
                check.consecutive_failures = 0
                check.last_success = datetime.now()
                
                # Métrica de archivos encontrados
                files_metric = HealthMetric(
                    name="google_drive_files_count",
                    value=len(test_pdfs),
                    unit="files",
                    threshold_warning=1000,
                    threshold_critical=2000,
                    timestamp=datetime.now()
                )
                check.metrics.append(files_metric)
                self.metrics_history["google_drive_files"].append((datetime.now(), len(test_pdfs)))
                
            else:
                check.status = HealthStatus.WARNING
                check.error_message = "No se pudieron listar archivos"
                check.consecutive_failures += 1
                check.last_failure = datetime.now()
                
                self._create_alert(
                    AlertLevel.WARNING,
                    "Google Drive Access Issue",
                    "No se pueden listar archivos en Google Drive",
                    "google_drive"
                )
            
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            check.status = HealthStatus.CRITICAL
            check.error_message = str(e)
            check.last_failure = datetime.now()
            check.consecutive_failures += 1
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
            self._create_alert(
                AlertLevel.CRITICAL,
                "Google Drive Check Failed",
                f"Error verificando Google Drive: {str(e)}",
                "google_drive"
            )
    
    def _run_performance_checks(self):
        """Ejecutar verificaciones de performance"""
        check = self.health_checks["system_performance"]
        start_time = time.time()
        
        try:
            # Test de búsqueda
            search_start = time.time()
            search_result = self.storage_manager.buscar_cotizaciones("test", 1, 5)
            search_duration = int((time.time() - search_start) * 1000)
            
            # Test de guardado (simulado)
            save_start = time.time()
            test_data = {
                "numeroCotizacion": f"HEALTH_CHECK_{int(time.time())}",
                "datosGenerales": {"cliente": "Health Check", "vendedor": "System"},
                "items": []
            }
            # No guardamos realmente, solo medimos el tiempo de preparación
            save_duration = int((time.time() - save_start) * 1000)
            
            total_duration = int((time.time() - start_time) * 1000)
            
            # Evaluar performance
            if search_duration > self.config['response_time_critical_ms']:
                check.status = HealthStatus.CRITICAL
                check.error_message = f"Búsqueda muy lenta: {search_duration}ms"
                
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "Search Performance Critical",
                    f"Tiempo de búsqueda crítico: {search_duration}ms",
                    "unified"
                )
                
            elif search_duration > self.config['response_time_warning_ms']:
                check.status = HealthStatus.WARNING
                check.error_message = f"Búsqueda lenta: {search_duration}ms"
                
            else:
                check.status = HealthStatus.HEALTHY
                check.error_message = ""
            
            # Métricas de performance
            search_metric = HealthMetric(
                name="search_response_time",
                value=search_duration,
                unit="ms",
                threshold_warning=self.config['response_time_warning_ms'],
                threshold_critical=self.config['response_time_critical_ms'],
                timestamp=datetime.now()
            )
            check.metrics.append(search_metric)
            self.metrics_history["search_performance"].append((datetime.now(), search_duration))
            
            check.duration_ms = total_duration
            check.last_run = datetime.now()
            
            if check.status == HealthStatus.HEALTHY:
                check.last_success = datetime.now()
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
                check.last_failure = datetime.now()
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            check.status = HealthStatus.CRITICAL
            check.error_message = str(e)
            check.last_failure = datetime.now()
            check.consecutive_failures += 1
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
            self._create_alert(
                AlertLevel.CRITICAL,
                "Performance Check Failed",
                f"Error en verificación de performance: {str(e)}",
                "unified"
            )
    
    def _run_capacity_checks(self):
        """Ejecutar verificaciones de capacidad"""
        check = self.health_checks["storage_capacity"]
        start_time = time.time()
        
        try:
            capacity_issues = []
            
            # Verificar Cloudinary si está disponible
            if self.storage_manager.cloudinary.is_available():
                try:
                    stats = self.storage_manager.cloudinary.obtener_estadisticas()
                    if not stats.get('error'):
                        storage_used = stats.get('storage_usado', 0)
                        storage_limit = 25 * 1024 * 1024 * 1024  # 25GB límite gratuito
                        usage_percent = (storage_used / storage_limit) * 100
                        
                        if usage_percent >= self.config['disk_usage_critical_percent']:
                            capacity_issues.append(f"Cloudinary: {usage_percent:.1f}% usado (crítico)")
                        elif usage_percent >= self.config['disk_usage_warning_percent']:
                            capacity_issues.append(f"Cloudinary: {usage_percent:.1f}% usado (advertencia)")
                        
                        # Métrica de uso de Cloudinary
                        usage_metric = HealthMetric(
                            name="cloudinary_usage_percent",
                            value=usage_percent,
                            unit="%",
                            threshold_warning=self.config['disk_usage_warning_percent'],
                            threshold_critical=self.config['disk_usage_critical_percent'],
                            timestamp=datetime.now()
                        )
                        check.metrics.append(usage_metric)
                        self.metrics_history["cloudinary_usage"].append((datetime.now(), usage_percent))
                        
                except Exception as e:
                    capacity_issues.append(f"Error verificando Cloudinary: {e}")
            
            # Verificar espacio en disco local
            try:
                import shutil
                local_path = Path(".")
                total, used, free = shutil.disk_usage(local_path)
                local_usage_percent = (used / total) * 100
                
                if local_usage_percent >= self.config['disk_usage_critical_percent']:
                    capacity_issues.append(f"Disco local: {local_usage_percent:.1f}% usado (crítico)")
                elif local_usage_percent >= self.config['disk_usage_warning_percent']:
                    capacity_issues.append(f"Disco local: {local_usage_percent:.1f}% usado (advertencia)")
                
                # Métrica de disco local
                disk_metric = HealthMetric(
                    name="local_disk_usage_percent",
                    value=local_usage_percent,
                    unit="%",
                    threshold_warning=self.config['disk_usage_warning_percent'],
                    threshold_critical=self.config['disk_usage_critical_percent'],
                    timestamp=datetime.now()
                )
                check.metrics.append(disk_metric)
                self.metrics_history["disk_usage"].append((datetime.now(), local_usage_percent))
                
            except Exception as e:
                capacity_issues.append(f"Error verificando disco local: {e}")
            
            # Evaluar estado general
            if any("crítico" in issue for issue in capacity_issues):
                check.status = HealthStatus.CRITICAL
                check.error_message = "; ".join(capacity_issues)
                check.last_failure = datetime.now()
                check.consecutive_failures += 1
                
                for issue in capacity_issues:
                    if "crítico" in issue:
                        self._create_alert(
                            AlertLevel.CRITICAL,
                            "Storage Capacity Critical",
                            issue,
                            "storage"
                        )
                        
            elif any("advertencia" in issue for issue in capacity_issues):
                check.status = HealthStatus.WARNING
                check.error_message = "; ".join(capacity_issues)
                check.consecutive_failures = 0
                check.last_success = datetime.now()
                
                for issue in capacity_issues:
                    if "advertencia" in issue:
                        self._create_alert(
                            AlertLevel.WARNING,
                            "Storage Capacity Warning",
                            issue,
                            "storage"
                        )
                        
            else:
                check.status = HealthStatus.HEALTHY
                check.error_message = ""
                check.consecutive_failures = 0
                check.last_success = datetime.now()
            
            check.duration_ms = int((time.time() - start_time) * 1000)
            check.last_run = datetime.now()
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            check.status = HealthStatus.CRITICAL
            check.error_message = str(e)
            check.last_failure = datetime.now()
            check.consecutive_failures += 1
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
            self._create_alert(
                AlertLevel.CRITICAL,
                "Capacity Check Failed",
                f"Error en verificación de capacidad: {str(e)}",
                "storage"
            )
    
    def _run_integrity_check(self) -> IntegrityReport:
        """Ejecutar verificación completa de integridad"""
        logger.info("🔍 [INTEGRITY] Iniciando verificación de integridad...")
        
        report_id = f"integrity_{int(time.time())}"
        start_time = time.time()
        issues = []
        
        try:
            # Obtener datos de ambas fuentes
            supabase_data = {}
            json_data = {}
            
            # Datos de Supabase
            if self.storage_manager.system_health.supabase.value == "online":
                try:
                    supabase_result = self.storage_manager.supabase.buscar_cotizaciones("", 1, 10000)
                    if not supabase_result.get('error'):
                        for item in supabase_result.get('resultados', []):
                            numero = item.get('numeroCotizacion')
                            if numero:
                                supabase_data[numero] = item
                except Exception as e:
                    issues.append(f"Error accediendo a Supabase: {e}")
            
            # Datos de JSON local
            try:
                json_raw = self.storage_manager.supabase._cargar_datos_offline()
                for item in json_raw.get('cotizaciones', []):
                    numero = item.get('numeroCotizacion')
                    if numero:
                        json_data[numero] = item
            except Exception as e:
                issues.append(f"Error accediendo a JSON local: {e}")
            
            # Análisis de consistencia
            all_numbers = set(supabase_data.keys()) | set(json_data.keys())
            consistent_records = 0
            inconsistent_records = 0
            missing_records = 0
            
            for numero in all_numbers:
                supabase_item = supabase_data.get(numero)
                json_item = json_data.get(numero)
                
                if supabase_item and json_item:
                    # Comparar campos críticos
                    if self._compare_records(supabase_item, json_item):
                        consistent_records += 1
                    else:
                        inconsistent_records += 1
                        issues.append(f"Inconsistencia detectada en: {numero}")
                        
                elif supabase_item and not json_item:
                    missing_records += 1
                    issues.append(f"Falta en JSON local: {numero}")
                    
                elif json_item and not supabase_item:
                    missing_records += 1
                    issues.append(f"Falta en Supabase: {numero}")
            
            # Detectar duplicados
            duplicate_records = 0
            seen_checksums = set()
            
            for items_dict in [supabase_data, json_data]:
                for numero, item in items_dict.items():
                    checksum = self._calculate_record_checksum(item)
                    if checksum in seen_checksums:
                        duplicate_records += 1
                        issues.append(f"Posible duplicado detectado: {numero}")
                    seen_checksums.add(checksum)
            
            # Crear reporte
            total_records = len(all_numbers)
            duration_ms = int((time.time() - start_time) * 1000)
            
            report = IntegrityReport(
                report_id=report_id,
                systems_checked=["supabase", "json_local"],
                total_records=total_records,
                consistent_records=consistent_records,
                inconsistent_records=inconsistent_records,
                missing_records=missing_records,
                duplicate_records=duplicate_records,
                corruption_detected=len(issues) > 0,
                issues=issues,
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
            
            # Actualizar check de integridad
            check = self.health_checks["data_integrity"]
            
            if report.consistency_rate >= self.config['consistency_critical_percent']:
                if report.consistency_rate >= self.config['consistency_warning_percent']:
                    check.status = HealthStatus.HEALTHY
                else:
                    check.status = HealthStatus.WARNING
                    self._create_alert(
                        AlertLevel.WARNING,
                        "Data Consistency Warning",
                        f"Consistencia de datos: {report.consistency_rate:.1f}%",
                        "data_integrity"
                    )
            else:
                check.status = HealthStatus.CRITICAL
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "Data Consistency Critical",
                    f"Consistencia de datos crítica: {report.consistency_rate:.1f}%",
                    "data_integrity"
                )
            
            check.error_message = f"{len(issues)} problemas detectados" if issues else ""
            check.duration_ms = duration_ms
            check.last_run = datetime.now()
            
            if check.status == HealthStatus.HEALTHY:
                check.last_success = datetime.now()
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
                check.last_failure = datetime.now()
            
            # Agregar métricas
            consistency_metric = HealthMetric(
                name="data_consistency_rate",
                value=report.consistency_rate,
                unit="%",
                threshold_warning=self.config['consistency_warning_percent'],
                threshold_critical=self.config['consistency_critical_percent'],
                timestamp=datetime.now()
            )
            check.metrics.append(consistency_metric)
            
            # Guardar reporte
            self.integrity_reports.append(report)
            
            logger.info(f"✅ [INTEGRITY] Verificación completada: {report.consistency_rate:.1f}% consistencia")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ [INTEGRITY] Error en verificación de integridad: {e}")
            
            # Reporte de error
            return IntegrityReport(
                report_id=report_id,
                systems_checked=[],
                total_records=0,
                consistent_records=0,
                inconsistent_records=0,
                missing_records=0,
                duplicate_records=0,
                corruption_detected=True,
                issues=[f"Error en verificación: {str(e)}"],
                timestamp=datetime.now(),
                duration_ms=int((time.time() - start_time) * 1000)
            )
    
    def _compare_records(self, record1: Dict, record2: Dict) -> bool:
        """Comparar dos registros para detectar inconsistencias"""
        # Campos críticos que deben ser idénticos
        critical_fields = ['numeroCotizacion', 'datosGenerales', 'items', 'revision']
        
        for field in critical_fields:
            if field in record1 and field in record2:
                if record1[field] != record2[field]:
                    return False
            elif field in record1 or field in record2:
                # Uno tiene el campo y el otro no
                return False
        
        return True
    
    def _calculate_record_checksum(self, record: Dict) -> str:
        """Calcular checksum de un registro"""
        # Campos que participan en el checksum
        stable_fields = ['numeroCotizacion', 'datosGenerales', 'items']
        stable_data = {k: v for k, v in record.items() if k in stable_fields}
        
        record_string = json.dumps(stable_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(record_string.encode()).hexdigest()
    
    def _create_alert(self, level: AlertLevel, title: str, description: str, system: str):
        """Crear nueva alerta"""
        if not self.config['enable_alerting']:
            return
        
        # Control de rate limiting
        now = datetime.now()
        if (now - self.last_alert_reset).seconds >= 3600:  # Reset cada hora
            self.alert_counts.clear()
            self.last_alert_reset = now
        
        alert_key = f"{system}_{title}"
        if self.alert_counts[alert_key] >= self.config['max_alerts_per_hour']:
            return  # Rate limit alcanzado
        
        alert_id = f"alert_{int(time.time())}_{hash(title)}"
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            title=title,
            description=description,
            system=system,
            timestamp=now,
            metadata={
                "check_type": "health_monitoring",
                "rate_limited": False
            }
        )
        
        self.active_alerts.append(alert)
        self.alert_counts[alert_key] += 1
        
        # Log de la alerta
        level_icons = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }
        
        icon = level_icons.get(level, "🔔")
        logger.warning(f"{icon} [ALERT] {title}: {description}")
        
        # Enviar notificación si está configurada
        if self.config['alert_email'] and level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
            self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: Alert):
        """Enviar notificación de alerta (placeholder)"""
        # TODO: Implementar envío de email/webhook/etc.
        logger.info(f"📧 [NOTIFICATION] Alerta {alert.level.value}: {alert.title}")
    
    def _attempt_auto_recovery(self):
        """Intentar recuperación automática de problemas detectados"""
        critical_checks = [
            check for check in self.health_checks.values()
            if check.status == HealthStatus.CRITICAL and check.consecutive_failures >= 2
        ]
        
        for check in critical_checks:
            if check.target_system == "supabase" and check.consecutive_failures <= 5:
                logger.info(f"🔧 [AUTO_RECOVERY] Intentando reconectar Supabase...")
                try:
                    # Reinicializar conexión
                    self.storage_manager.supabase._inicializar_conexion()
                    if not self.storage_manager.supabase.modo_offline:
                        logger.info("✅ [AUTO_RECOVERY] Supabase reconectado exitosamente")
                        check.consecutive_failures = 0
                        check.status = HealthStatus.RECOVERING
                except Exception as e:
                    logger.error(f"❌ [AUTO_RECOVERY] Error reconectando Supabase: {e}")
            
            # TODO: Agregar más estrategias de auto-recuperación
    
    def _cleanup_old_metrics(self):
        """Limpiar métricas antiguas para conservar memoria"""
        cutoff_time = datetime.now() - timedelta(hours=self.config['metrics_retention_hours'])
        
        for metric_name, metric_history in self.metrics_history.items():
            # Filtrar métricas más recientes que el cutoff
            filtered_metrics = deque(
                [(timestamp, value) for timestamp, value in metric_history if timestamp > cutoff_time],
                maxlen=metric_history.maxlen
            )
            self.metrics_history[metric_name] = filtered_metrics
        
        # Limpiar métricas de health checks
        for check in self.health_checks.values():
            check.metrics = [
                metric for metric in check.metrics[-10:]  # Mantener solo las últimas 10
                if (datetime.now() - metric.timestamp).hours <= 24
            ]
    
    def _load_persistent_state(self):
        """Cargar estado persistente"""
        try:
            # Cargar alertas
            if self.alerts_file.exists():
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    alerts_data = json.load(f)
                
                for alert_data in alerts_data.get('active_alerts', []):
                    alert = Alert(
                        alert_id=alert_data['alert_id'],
                        level=AlertLevel(alert_data['level']),
                        title=alert_data['title'],
                        description=alert_data['description'],
                        system=alert_data['system'],
                        timestamp=datetime.fromisoformat(alert_data['timestamp']),
                        acknowledged=alert_data.get('acknowledged', False),
                        resolved=alert_data.get('resolved', False),
                        resolution_message=alert_data.get('resolution_message', ''),
                        metadata=alert_data.get('metadata', {})
                    )
                    
                    if not alert.resolved:
                        self.active_alerts.append(alert)
                    else:
                        self.resolved_alerts.append(alert)
                
                logger.info(f"📂 [HEALTH_MONITOR] {len(self.active_alerts)} alertas activas cargadas")
            
            # Cargar reportes de integridad
            if self.reports_file.exists():
                with open(self.reports_file, 'r', encoding='utf-8') as f:
                    reports_data = json.load(f)
                
                for report_data in reports_data.get('integrity_reports', []):
                    report = IntegrityReport(
                        report_id=report_data['report_id'],
                        systems_checked=report_data['systems_checked'],
                        total_records=report_data['total_records'],
                        consistent_records=report_data['consistent_records'],
                        inconsistent_records=report_data['inconsistent_records'],
                        missing_records=report_data['missing_records'],
                        duplicate_records=report_data['duplicate_records'],
                        corruption_detected=report_data['corruption_detected'],
                        issues=report_data['issues'],
                        timestamp=datetime.fromisoformat(report_data['timestamp']),
                        duration_ms=report_data['duration_ms']
                    )
                    self.integrity_reports.append(report)
                
                logger.info(f"📋 [HEALTH_MONITOR] {len(self.integrity_reports)} reportes de integridad cargados")
                
        except Exception as e:
            logger.error(f"❌ [HEALTH_MONITOR] Error cargando estado persistente: {e}")
    
    def _save_persistent_state(self):
        """Guardar estado persistente"""
        try:
            # Guardar alertas
            alerts_data = {
                'active_alerts': [],
                'resolved_alerts': []
            }
            
            for alert in self.active_alerts:
                alerts_data['active_alerts'].append({
                    'alert_id': alert.alert_id,
                    'level': alert.level.value,
                    'title': alert.title,
                    'description': alert.description,
                    'system': alert.system,
                    'timestamp': alert.timestamp.isoformat(),
                    'acknowledged': alert.acknowledged,
                    'resolved': alert.resolved,
                    'resolution_message': alert.resolution_message,
                    'metadata': alert.metadata
                })
            
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(alerts_data, f, ensure_ascii=False, indent=2)
            
            # Guardar reportes de integridad (solo los últimos 10)
            reports_data = {
                'integrity_reports': []
            }
            
            for report in self.integrity_reports[-10:]:
                reports_data['integrity_reports'].append({
                    'report_id': report.report_id,
                    'systems_checked': report.systems_checked,
                    'total_records': report.total_records,
                    'consistent_records': report.consistent_records,
                    'inconsistent_records': report.inconsistent_records,
                    'missing_records': report.missing_records,
                    'duplicate_records': report.duplicate_records,
                    'corruption_detected': report.corruption_detected,
                    'issues': report.issues,
                    'timestamp': report.timestamp.isoformat(),
                    'duration_ms': report.duration_ms
                })
            
            with open(self.reports_file, 'w', encoding='utf-8') as f:
                json.dump(reports_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ [HEALTH_MONITOR] Error guardando estado persistente: {e}")
    
    def get_system_health_summary(self) -> Dict:
        """Obtener resumen de salud del sistema"""
        overall_status = HealthStatus.HEALTHY
        
        # Determinar estado general basado en checks individuales
        critical_count = sum(1 for check in self.health_checks.values() if check.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for check in self.health_checks.values() if check.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            overall_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            overall_status = HealthStatus.WARNING
        
        # Calcular tiempo de actividad
        uptime = datetime.now() - min(check.last_run for check in self.health_checks.values())
        
        return {
            "overall_status": overall_status.value,
            "health_checks": {
                check_id: {
                    "status": check.status.value,
                    "last_run": check.last_run.isoformat() if check.last_run else None,
                    "last_success": check.last_success.isoformat() if check.last_success else None,
                    "consecutive_failures": check.consecutive_failures,
                    "duration_ms": check.duration_ms,
                    "error_message": check.error_message
                }
                for check_id, check in self.health_checks.items()
            },
            "alerts": {
                "active": len(self.active_alerts),
                "critical": len([a for a in self.active_alerts if a.level == AlertLevel.CRITICAL]),
                "warnings": len([a for a in self.active_alerts if a.level == AlertLevel.WARNING])
            },
            "integrity": {
                "last_check": self.integrity_reports[-1].timestamp.isoformat() if self.integrity_reports else None,
                "consistency_rate": self.integrity_reports[-1].consistency_rate if self.integrity_reports else None,
                "issues_detected": len(self.integrity_reports[-1].issues) if self.integrity_reports else 0
            },
            "uptime_seconds": uptime.total_seconds(),
            "is_monitoring": self.is_monitoring
        }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Reconocer una alerta"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"✅ [ALERT] Alerta reconocida: {alert_id}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str, resolution_message: str = "") -> bool:
        """Resolver una alerta"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolution_message = resolution_message
                
                # Mover a alertas resueltas
                self.active_alerts.remove(alert)
                self.resolved_alerts.append(alert)
                
                logger.info(f"✅ [ALERT] Alerta resuelta: {alert_id}")
                return True
        return False
    
    def force_health_check(self) -> Dict:
        """Forzar verificación de salud completa"""
        logger.info("⚡ [HEALTH_CHECK] Verificación forzada iniciada...")
        
        start_time = time.time()
        self._run_all_health_checks()
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            "completed": True,
            "duration_ms": duration_ms,
            "summary": self.get_system_health_summary()
        }
    
    def force_integrity_check(self) -> IntegrityReport:
        """Forzar verificación de integridad"""
        logger.info("⚡ [INTEGRITY] Verificación de integridad forzada...")
        return self._run_integrity_check()


if __name__ == "__main__":
    # Test del sistema de monitoreo
    from unified_storage_manager import UnifiedStorageManager
    
    storage_manager = UnifiedStorageManager()
    health_system = HealthMonitoringSystem(storage_manager)
    
    # Verificación inicial
    health_summary = health_system.get_system_health_summary()
    print(json.dumps(health_summary, indent=2, default=str))
    
    # Forzar verificación completa
    check_result = health_system.force_health_check()
    print(f"Verificación completa: {check_result['duration_ms']}ms")
    
    # Verificación de integridad
    integrity_report = health_system.force_integrity_check()
    print(f"Integridad: {integrity_report.consistency_rate:.1f}% consistencia")