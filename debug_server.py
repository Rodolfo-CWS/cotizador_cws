#!/usr/bin/env python3
"""
Script de debug para el servidor CWS con logging mejorado
"""

import logging
import sys
from datetime import datetime
from app import app, db_manager

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'cws_debug_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def log_request_debug():
    """Middleware para logear todas las requests"""
    from flask import request, g
    import time
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
        logger.info(f"🔵 REQUEST: {request.method} {request.path}")
        if request.method == 'POST' and request.is_json:
            logger.info(f"📝 POST DATA: {request.get_json()}")
    
    @app.after_request
    def after_request(response):
        duration = time.time() - g.start_time
        logger.info(f"✅ RESPONSE: {response.status_code} - Duration: {duration:.3f}s")
        return response

if __name__ == "__main__":
    print("[DEBUG] Iniciando servidor CWS con debug mejorado...")
    print(f"[ESTADO] MongoDB: {'ONLINE' if not db_manager.modo_offline else 'OFFLINE'}")
    print(f"[URL] http://127.0.0.1:5000/")
    print(f"[ADMIN] http://127.0.0.1:5000/admin")
    print(f"[FORMULARIO] http://127.0.0.1:5000/formulario")
    print("=" * 60)
    
    # Activar logging de requests
    log_request_debug()
    
    # Ejecutar servidor
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,
        use_reloader=False  # Evitar doble carga en modo debug
    )