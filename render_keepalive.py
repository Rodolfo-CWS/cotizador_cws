"""
Render Keepalive System - Horario Laboral
==========================================

Sistema de keepalive inteligente para mantener el servicio de Render despierto
durante horario laboral (Lunes-Viernes, 7am-9pm hora México/CST).

Características:
- Ping cada 10 minutos durante horario de oficina
- Ahorra ~60% del límite de horas del plan gratuito
- Consume solo ~300 horas/mes (~40% del límite de 750 horas)
- APScheduler con CronTrigger para programación precisa

Autor: Claude Code para CWS Company
Fecha: Septiembre 2025
"""

import os
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RenderKeepalive:
    """
    Sistema de keepalive para Render con horario laboral.

    Mantiene el servicio despierto únicamente durante horario de oficina:
    - Lunes a Viernes
    - 7:00 AM - 9:00 PM (CST/México)
    - Ping cada 10 minutos
    """

    def __init__(self, app_url=None):
        """
        Inicializa el sistema de keepalive.

        Args:
            app_url: URL de la aplicación. Si es None, intenta detectarla automáticamente.
        """
        self.scheduler = BackgroundScheduler(timezone='America/Mexico_City')
        self.app_url = app_url or self._detect_app_url()
        self.health_endpoint = f"{self.app_url}/health"
        self.ping_count = 0
        self.last_ping = None
        self.is_running = False

        logger.info(f"[KEEPALIVE] Inicializado con URL: {self.app_url}")

    def _detect_app_url(self):
        """
        Detecta automáticamente la URL de la aplicación.

        Returns:
            str: URL de la aplicación
        """
        # En Render, usar la URL de producción
        if os.environ.get('RENDER'):
            return "https://cotizador-cws.onrender.com"

        # En desarrollo local, usar localhost
        port = os.environ.get('PORT', '5000')
        return f"http://localhost:{port}"

    def ping(self):
        """
        Realiza un ping al endpoint /health para mantener el servicio despierto.
        """
        try:
            response = requests.get(self.health_endpoint, timeout=10)
            self.ping_count += 1
            self.last_ping = datetime.now()

            if response.status_code == 200:
                logger.info(
                    f"[KEEPALIVE] Ping #{self.ping_count} exitoso - "
                    f"{self.last_ping.strftime('%Y-%m-%d %H:%M:%S')} - "
                    f"Status: {response.status_code}"
                )
            else:
                logger.warning(
                    f"[KEEPALIVE] Ping #{self.ping_count} con status {response.status_code}"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"[KEEPALIVE] Error en ping #{self.ping_count}: {str(e)}")

    def start(self):
        """
        Inicia el scheduler de keepalive con horario laboral.

        Configuración:
        - Lunes a Viernes (day_of_week='mon-fri')
        - 7:00 AM - 9:00 PM (hour='7-20')
        - Cada 10 minutos (minute='*/10')
        - Zona horaria: America/Mexico_City (CST)
        """
        if self.is_running:
            logger.warning("[KEEPALIVE] El scheduler ya está en ejecución")
            return

        # Solo ejecutar en producción (Render)
        if not os.environ.get('RENDER'):
            logger.info("[KEEPALIVE] Modo desarrollo detectado - Keepalive desactivado")
            return

        try:
            # Configurar cron: Lun-Vie, 7am-9pm, cada 10 min
            trigger = CronTrigger(
                day_of_week='mon-fri',  # Lunes a Viernes
                hour='7-20',            # 7 AM a 8 PM (última ejecución a las 8:50 PM)
                minute='*/10',          # Cada 10 minutos
                timezone='America/Mexico_City'
            )

            self.scheduler.add_job(
                self.ping,
                trigger=trigger,
                id='render_keepalive',
                name='Render Keepalive - Horario Laboral',
                max_instances=1,
                replace_existing=True
            )

            self.scheduler.start()
            self.is_running = True

            logger.info("=" * 70)
            logger.info("[KEEPALIVE] Sistema iniciado exitosamente")
            logger.info("[KEEPALIVE] Horario: Lunes-Viernes, 7:00 AM - 9:00 PM CST")
            logger.info("[KEEPALIVE] Frecuencia: Cada 10 minutos")
            logger.info("[KEEPALIVE] Consumo estimado: ~300 horas/mes (~40% del límite)")
            logger.info("=" * 70)

            # Mostrar próximas ejecuciones
            self._log_next_runs()

        except Exception as e:
            logger.error(f"[KEEPALIVE] Error al iniciar scheduler: {str(e)}")

    def stop(self):
        """
        Detiene el scheduler de keepalive.
        """
        if not self.is_running:
            logger.warning("[KEEPALIVE] El scheduler no está en ejecución")
            return

        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info(f"[KEEPALIVE] Scheduler detenido - Total pings realizados: {self.ping_count}")
        except Exception as e:
            logger.error(f"[KEEPALIVE] Error al detener scheduler: {str(e)}")

    def _log_next_runs(self, count=5):
        """
        Muestra las próximas ejecuciones programadas.

        Args:
            count: Número de ejecuciones futuras a mostrar
        """
        job = self.scheduler.get_job('render_keepalive')
        if job:
            logger.info(f"[KEEPALIVE] Próximas {count} ejecuciones:")
            next_run = job.next_run_time
            if next_run:
                logger.info(f"  1. {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    def get_stats(self):
        """
        Obtiene estadísticas del sistema de keepalive.

        Returns:
            dict: Estadísticas del sistema
        """
        job = self.scheduler.get_job('render_keepalive')
        next_run = job.next_run_time if job else None

        return {
            'is_running': self.is_running,
            'app_url': self.app_url,
            'health_endpoint': self.health_endpoint,
            'total_pings': self.ping_count,
            'last_ping': self.last_ping.isoformat() if self.last_ping else None,
            'next_run': next_run.isoformat() if next_run else None,
            'schedule': 'Lunes-Viernes, 7:00 AM - 9:00 PM CST, cada 10 minutos',
            'estimated_monthly_hours': '~300 horas (~40% del límite de 750 horas)'
        }


# Instancia global del keepalive
_keepalive_instance = None


def get_keepalive_instance():
    """
    Obtiene la instancia global del keepalive (patrón Singleton).

    Returns:
        RenderKeepalive: Instancia global del keepalive
    """
    global _keepalive_instance
    if _keepalive_instance is None:
        _keepalive_instance = RenderKeepalive()
    return _keepalive_instance


def init_keepalive(app_url=None):
    """
    Inicializa y arranca el sistema de keepalive.

    Args:
        app_url: URL de la aplicación (opcional)

    Returns:
        RenderKeepalive: Instancia del keepalive
    """
    keepalive = get_keepalive_instance()
    if app_url and keepalive.app_url != app_url:
        keepalive.app_url = app_url
        keepalive.health_endpoint = f"{app_url}/health"

    keepalive.start()
    return keepalive


if __name__ == '__main__':
    # Test del sistema de keepalive
    print("Iniciando test del sistema de keepalive...")
    keepalive = RenderKeepalive()

    print("\nEstadísticas iniciales:")
    import json
    print(json.dumps(keepalive.get_stats(), indent=2))

    print("\nRealizando ping de prueba...")
    keepalive.ping()

    print("\nEstadísticas después del ping:")
    print(json.dumps(keepalive.get_stats(), indent=2))

    print("\n✅ Test completado")
