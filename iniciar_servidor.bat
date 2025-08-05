@echo off
title CWS Cotizaciones - Servidor
echo ==========================================
echo     CWS SISTEMA DE COTIZACIONES
echo          SERVIDOR CENTRALIZADO
echo ==========================================
echo.
echo Iniciando servidor...
echo.

REM Cambiar al directorio de la aplicación
cd /d "C:\Users\SDS\cotizador_cws"

REM Activar entorno virtual si existe
if exist "env\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call env\Scripts\activate.bat
)

REM Configurar variables de entorno para producción
set FLASK_DEBUG=False
set FLASK_ENV=production

REM Mostrar información de red
echo.
echo ==========================================
echo INFORMACION DE ACCESO:
echo ==========================================
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /c:"IPv4"') do (
    echo Acceso local:  http://127.0.0.1:5000
    echo Acceso en red: http://%%i:5000
)
echo.
echo Para otros usuarios: usar la IP de red mostrada arriba
echo Ejemplo: http://192.168.1.100:5000
echo.
echo ==========================================
echo.

REM Ejecutar la aplicación
python app.py

pause