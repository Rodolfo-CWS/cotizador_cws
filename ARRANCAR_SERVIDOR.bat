@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                 🚀 ARRANCAR SERVIDOR CWS                      ║
echo ║                   MODO DIAGNÓSTICO                            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo [INFO] Cambiando al directorio del proyecto...
cd /d "C:\Users\SDS\cotizador_cws"

echo [INFO] Activando entorno virtual...
if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
    echo [OK] Entorno virtual activado
) else (
    echo [ERROR] Entorno virtual no encontrado - ejecuta INSTALAR_AUTOMATICO.bat primero
    pause
    exit /b 1
)

echo.
echo [INFO] Verificando dependencias críticas...
python -c "import flask, pymongo; print('[OK] Flask y PyMongo disponibles')" 2>nul
if errorlevel 1 (
    echo [ERROR] Dependencias faltantes - ejecuta: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                      SERVIDOR INICIANDO                       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🌐 URL DEL FORMULARIO: http://127.0.0.1:5000/formulario
echo 🌐 URL DE ADMIN:       http://127.0.0.1:5000/admin  
echo 🌐 URL PRINCIPAL:      http://127.0.0.1:5000/
echo.
echo ⚠️  IMPORTANTE: Mantén esta ventana ABIERTA mientras uses la app
echo ⚠️  Para DETENER: Presiona Ctrl+C
echo.
echo ════════════════════════════════════════════════════════════════
echo                       LOGS DEL SERVIDOR:
echo ════════════════════════════════════════════════════════════════

python app.py

echo.
echo [INFO] Servidor detenido
pause