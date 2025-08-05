#!/usr/bin/env python3
"""
Script para crear aplicación de escritorio CWS Cotizaciones
usando webview (alternativa ligera a Electron)
"""

import os
import sys
import subprocess

def instalar_dependencias():
    """Instala las dependencias necesarias"""
    print("🔧 Instalando dependencias...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "pyinstaller"])
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error instalando dependencias")
        return False

def crear_app_escritorio():
    """Crea el archivo principal de la aplicación de escritorio"""
    
    app_content = '''
import webview
import threading
import time
import requests
import sys
import os

class CWSApp:
    def __init__(self):
        self.server_url = "http://127.0.0.1:5000"
        self.server_running = False
    
    def verificar_servidor(self):
        """Verifica si el servidor está corriendo"""
        try:
            response = requests.get(self.server_url, timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def mostrar_mensaje_servidor(self):
        """Muestra mensaje si el servidor no está disponible"""
        mensaje = """
        <html>
        <head>
            <title>CWS Cotizaciones</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    max-width: 500px;
                    margin: 0 auto;
                }
                h1 { color: #2c5282; }
                .error { color: #dc2626; margin: 20px 0; }
                .instructions { text-align: left; margin: 20px 0; }
                li { margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏢 CWS Cotizações</h1>
                <div class="error">⚠️ Servidor no disponible</div>
                <div class="instructions">
                    <p><strong>Para usar la aplicación:</strong></p>
                    <ol>
                        <li>Asegúrate de que el servidor esté ejecutándose</li>
                        <li>Ejecuta <code>iniciar_servidor.bat</code></li>
                        <li>Vuelve a abrir esta aplicación</li>
                    </ol>
                </div>
                <p><small>Si el problema persiste, contacta al administrador del sistema.</small></p>
            </div>
        </body>
        </html>
        """
        return mensaje

def main():
    app = CWSApp()
    
    # Verificar si el servidor está corriendo
    if app.verificar_servidor():
        # Servidor disponible - mostrar la aplicación web
        window = webview.create_window(
            title='CWS Cotizaciones',
            url=app.server_url,
            width=1200,
            height=800,
            resizable=True,
            shadow=True
        )
    else:
        # Servidor no disponible - mostrar mensaje
        window = webview.create_window(
            title='CWS Cotizaciones - Servidor Requerido',
            html=app.mostrar_mensaje_servidor(),
            width=600,
            height=400,
            resizable=False
        )
    
    # Configurar la ventana
    webview.start(debug=False)

if __name__ == '__main__':
    main()
'''
    
    with open('cws_app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    
    print("✅ Archivo cws_app.py creado")

def crear_ejecutable():
    """Crea el ejecutable usando PyInstaller"""
    print("🔨 Creando ejecutable...")
    
    # Comando PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=CWS_Cotizaciones",
        "--icon=static/logo.ico",  # Si tienes un archivo .ico
        "cws_app.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("✅ Ejecutable creado en dist/CWS_Cotizaciones.exe")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error creando ejecutable")
        return False

def main():
    print("🏢 CWS Cotizaciones - Creador de App de Escritorio")
    print("=" * 60)
    
    if not instalar_dependencias():
        return
    
    crear_app_escritorio()
    
    respuesta = input("\\n¿Crear ejecutable ahora? (S/N): ")
    if respuesta.upper() == 'S':
        crear_ejecutable()
        print("\\n🎉 ¡App de escritorio creada exitosamente!")
        print("📁 Archivo: dist/CWS_Cotizaciones.exe")
        print("📋 Puedes distribuir este archivo a otros usuarios")
    
    print("\\n✅ Proceso completado")

if __name__ == "__main__":
    main()