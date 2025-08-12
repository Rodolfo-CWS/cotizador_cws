"""
Sync Scheduler - Sistema de sincronización automática JSON ↔ MongoDB
Utiliza APScheduler para sincronizar cada 15 minutos (configurable)
"""

import os
import time
import datetime
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SyncScheduler:
    def __init__(self, database_manager):
        """
        Inicializa el scheduler de sincronización
        
        Args:
            database_manager: Instancia de DatabaseManager
        """
        self.db_manager = database_manager
        self.scheduler = None
        self.scheduler_disponible = False
        self.activo = False
        self.intervalo_minutos = int(os.getenv('SYNC_INTERVAL_MINUTES', '15'))
        self.auto_sync_enabled = os.getenv('AUTO_SYNC_ENABLED', 'true').lower() == 'true'
        
        # Estadísticas
        self.ultima_sincronizacion = None
        self.sincronizaciones_exitosas = 0
        self.sincronizaciones_fallidas = 0
        self.ultima_sincronizacion_resultado = None
        
        print(f"🔄 [SYNC_SCHEDULER] Inicializando scheduler...")
        print(f"   Intervalo: {self.intervalo_minutos} minutos")
        print(f"   Auto-sync: {'✅ Habilitado' if self.auto_sync_enabled else '❌ Deshabilitado'}")
        
        # Intentar inicializar APScheduler
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            import atexit
            
            self.BackgroundScheduler = BackgroundScheduler
            self.IntervalTrigger = IntervalTrigger
            self.atexit = atexit
            self.scheduler_disponible = True
            
            print("✅ [SYNC_SCHEDULER] APScheduler disponible")
            
        except ImportError:
            print("❌ [SYNC_SCHEDULER] APScheduler no disponible: pip install APScheduler")
            print("   Sincronización automática deshabilitada")

    def is_available(self) -> bool:
        """Verifica si el scheduler está disponible"""
        return self.scheduler_disponible

    def iniciar(self) -> bool:
        """
        Inicia el scheduler de sincronización automática
        
        Returns:
            bool: True si se inició correctamente
        """
        if not self.scheduler_disponible:
            print("❌ [SYNC_SCHEDULER] No se puede iniciar - APScheduler no disponible")
            return False
        
        if not self.auto_sync_enabled:
            print("⚠️ [SYNC_SCHEDULER] Auto-sync deshabilitado por configuración")
            return False
        
        if self.activo:
            print("⚠️ [SYNC_SCHEDULER] Scheduler ya está activo")
            return True
        
        try:
            print(f"🚀 [SYNC_SCHEDULER] Iniciando scheduler...")
            print(f"   Sincronización cada {self.intervalo_minutos} minutos")
            
            # Crear scheduler
            self.scheduler = self.BackgroundScheduler()
            
            # Agregar job de sincronización
            self.scheduler.add_job(
                func=self._ejecutar_sincronizacion,
                trigger=self.IntervalTrigger(minutes=self.intervalo_minutos),
                id='sync_bidireccional',
                name='Sincronización Bidireccional JSON ↔ MongoDB',
                max_instances=1,  # Solo una instancia a la vez
                coalesce=True,    # Combinar ejecuciones pendientes
                replace_existing=True
            )
            
            # Iniciar scheduler
            self.scheduler.start()
            self.activo = True
            
            # Configurar cierre automático al cerrar la aplicación
            self.atexit.register(lambda: self.detener())
            
            print("✅ [SYNC_SCHEDULER] Scheduler iniciado exitosamente")
            
            # Ejecutar sincronización inicial (opcional)
            if os.getenv('SYNC_ON_STARTUP', 'false').lower() == 'true':
                print("🔄 [SYNC_SCHEDULER] Ejecutando sincronización inicial...")
                self._ejecutar_sincronizacion()
            
            return True
            
        except Exception as e:
            print(f"❌ [SYNC_SCHEDULER] Error iniciando scheduler: {e}")
            self.activo = False
            return False

    def detener(self) -> bool:
        """
        Detiene el scheduler de sincronización
        
        Returns:
            bool: True si se detuvo correctamente
        """
        if not self.scheduler or not self.activo:
            print("⚠️ [SYNC_SCHEDULER] Scheduler no está activo")
            return True
        
        try:
            print("🛑 [SYNC_SCHEDULER] Deteniendo scheduler...")
            self.scheduler.shutdown(wait=True)
            self.activo = False
            print("✅ [SYNC_SCHEDULER] Scheduler detenido")
            return True
            
        except Exception as e:
            print(f"❌ [SYNC_SCHEDULER] Error deteniendo scheduler: {e}")
            return False

    def _ejecutar_sincronizacion(self):
        """
        Ejecuta la sincronización bidireccional (método interno para el scheduler)
        """
        timestamp_inicio = datetime.datetime.now()
        
        try:
            print(f"🔄 [SYNC_AUTO] Iniciando sincronización automática - {timestamp_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Solo sincronizar si MongoDB está disponible
            if self.db_manager.modo_offline:
                print("⚠️ [SYNC_AUTO] MongoDB offline - saltando sincronización")
                return
            
            # Ejecutar sincronización bidireccional
            resultado = self.db_manager.sincronizar_bidireccional()
            
            # Actualizar estadísticas
            self.ultima_sincronizacion = timestamp_inicio
            self.ultima_sincronizacion_resultado = resultado
            
            if resultado.get("success", False):
                self.sincronizaciones_exitosas += 1
                print(f"✅ [SYNC_AUTO] {resultado.get('mensaje', 'Sincronización exitosa')}")
            else:
                self.sincronizaciones_fallidas += 1
                print(f"❌ [SYNC_AUTO] Error: {resultado.get('error', 'Error desconocido')}")
                
        except Exception as e:
            print(f"❌ [SYNC_AUTO] Excepción durante sincronización: {e}")
            self.sincronizaciones_fallidas += 1
            self.ultima_sincronizacion_resultado = {"success": False, "error": str(e)}

    def ejecutar_sincronizacion_manual(self) -> dict:
        """
        Ejecuta una sincronización manual (fuera del scheduler)
        
        Returns:
            dict: Resultado de la sincronización
        """
        print("🔄 [SYNC_MANUAL] Iniciando sincronización manual...")
        
        if self.db_manager.modo_offline:
            resultado = {
                "success": False,
                "error": "MongoDB offline - no se puede sincronizar",
                "timestamp": datetime.datetime.now().isoformat()
            }
        else:
            resultado = self.db_manager.sincronizar_bidireccional()
            
            # Actualizar estadísticas
            self.ultima_sincronizacion = datetime.datetime.now()
            self.ultima_sincronizacion_resultado = resultado
            
            if resultado.get("success", False):
                self.sincronizaciones_exitosas += 1
            else:
                self.sincronizaciones_fallidas += 1
        
        print(f"✅ [SYNC_MANUAL] Resultado: {resultado.get('mensaje', resultado.get('error', 'Completado'))}")
        return resultado

    def obtener_estado(self) -> dict:
        """
        Obtiene el estado actual del scheduler
        
        Returns:
            dict: Estado detallado del scheduler
        """
        return {
            "disponible": self.scheduler_disponible,
            "activo": self.activo,
            "auto_sync_habilitado": self.auto_sync_enabled,
            "intervalo_minutos": self.intervalo_minutos,
            "mongodb_disponible": not self.db_manager.modo_offline,
            "estadisticas": {
                "sincronizaciones_exitosas": self.sincronizaciones_exitosas,
                "sincronizaciones_fallidas": self.sincronizaciones_fallidas,
                "ultima_sincronizacion": self.ultima_sincronizacion.isoformat() if self.ultima_sincronizacion else None,
                "ultimo_resultado": self.ultima_sincronizacion_resultado
            },
            "configuracion": {
                "SYNC_INTERVAL_MINUTES": self.intervalo_minutos,
                "AUTO_SYNC_ENABLED": self.auto_sync_enabled,
                "SYNC_ON_STARTUP": os.getenv('SYNC_ON_STARTUP', 'false')
            }
        }

    def cambiar_intervalo(self, nuevos_minutos: int) -> bool:
        """
        Cambia el intervalo de sincronización (requiere reiniciar scheduler)
        
        Args:
            nuevos_minutos: Nuevo intervalo en minutos
            
        Returns:
            bool: True si se cambió correctamente
        """
        if nuevos_minutos < 1:
            print("❌ [SYNC_SCHEDULER] Intervalo debe ser al menos 1 minuto")
            return False
        
        print(f"🔄 [SYNC_SCHEDULER] Cambiando intervalo: {self.intervalo_minutos} → {nuevos_minutos} minutos")
        
        self.intervalo_minutos = nuevos_minutos
        
        # Si está activo, reiniciar para aplicar el cambio
        if self.activo:
            self.detener()
            return self.iniciar()
        
        return True

    def obtener_proximo_sync(self) -> Optional[datetime.datetime]:
        """
        Obtiene la fecha/hora del próximo sync programado
        
        Returns:
            datetime o None si no está programado
        """
        if not self.activo or not self.scheduler:
            return None
        
        try:
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                if job.id == 'sync_bidireccional':
                    return job.next_run_time
            return None
        except:
            return None

    def obtener_logs_sync(self, ultimos: int = 10) -> list:
        """
        Obtiene los logs de sincronización recientes (simulado)
        
        Args:
            ultimos: Número de logs a obtener
            
        Returns:
            list: Lista de logs de sincronización
        """
        # En una implementación completa, esto leería de un archivo de log
        logs_simulados = []
        
        if self.ultima_sincronizacion and self.ultima_sincronizacion_resultado:
            logs_simulados.append({
                "timestamp": self.ultima_sincronizacion.isoformat(),
                "tipo": "auto" if self.activo else "manual",
                "success": self.ultima_sincronizacion_resultado.get("success", False),
                "mensaje": self.ultima_sincronizacion_resultado.get("mensaje", ""),
                "error": self.ultima_sincronizacion_resultado.get("error", ""),
                "subidas": self.ultima_sincronizacion_resultado.get("subidas", 0),
                "descargas": self.ultima_sincronizacion_resultado.get("descargas", 0),
                "conflictos": self.ultima_sincronizacion_resultado.get("conflictos", 0)
            })
        
        return logs_simulados[-ultimos:] if logs_simulados else []


# Función de utilidad para testing
def test_sync_scheduler():
    """Test rápido del scheduler"""
    print("🧪 Probando Sync Scheduler...")
    
    # Mock de DatabaseManager para testing
    class MockDatabaseManager:
        def __init__(self):
            self.modo_offline = False
            
        def sincronizar_bidireccional(self):
            return {
                "success": True,
                "mensaje": "Test sync exitoso",
                "subidas": 0,
                "descargas": 0,
                "conflictos": 0
            }
    
    # Crear scheduler de prueba
    mock_db = MockDatabaseManager()
    scheduler = SyncScheduler(mock_db)
    
    if not scheduler.is_available():
        print("❌ APScheduler no disponible")
        return False
    
    # Test de sincronización manual
    resultado = scheduler.ejecutar_sincronizacion_manual()
    print(f"✅ Sincronización manual: {resultado.get('success', False)}")
    
    # Test de estado
    estado = scheduler.obtener_estado()
    print(f"✅ Estado scheduler: {'Disponible' if estado['disponible'] else 'No disponible'}")
    
    return True


if __name__ == "__main__":
    # Test directo del módulo
    test_sync_scheduler()