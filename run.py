#!/usr/bin/env python
"""Entry point for CWS Cotizador - Desarrollo local."""
import os
from cotizador import create_app

app = create_app()

if __name__ == "__main__":
    app_name = os.getenv('APP_NAME', 'CWS Cotizaciones')
    app_version = os.getenv('APP_VERSION', '1.0.0')
    environment = os.getenv('FLASK_ENV', 'development')

    print(f"Iniciando {app_name} v{app_version}")
    print(f"Entorno: {environment}")
    print(f"Servidor disponible en: http://127.0.0.1:5000")
    print(f"Info del sistema en: http://127.0.0.1:5000/info")

    port = int(os.getenv('PORT', 5000))
    app.run(
        debug=app.config.get('DEBUG', False),
        host='0.0.0.0',
        port=port
    )
