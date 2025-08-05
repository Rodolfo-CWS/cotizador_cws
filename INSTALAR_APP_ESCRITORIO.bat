@echo off
title CWS - Instalador de App de Escritorio
color 0B
echo.
echo     ██████╗██╗    ██╗███████╗
echo    ██╔════╝██║    ██║██╔════╝
echo    ██║     ██║ █╗ ██║███████╗
echo    ██║     ██║███╗██║╚════██║
echo    ╚██████╗╚███╔███╔╝███████║
echo     ╚═════╝ ╚══╝╚══╝ ╚══════╝
echo.
echo    SISTEMA DE COTIZACIONES
echo      INSTALADOR DE APP
echo ==========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python no encontrado
    echo    Instala Python desde: https://python.org
    pause
    exit /b 1
)

echo ✅ Python encontrado
echo.

echo 📋 Opciones de Instalación:
echo.
echo [1] App Completa (Electron-style) - Más profesional
echo [2] Accesos Directos Elegantes - Más rápido
echo [3] PWA (Progressive Web App) - Más moderno
echo [4] Crear todos los tipos
echo.
set /p opcion="Selecciona una opción (1-4): "

if "%opcion%"=="1" goto :app_completa
if "%opcion%"=="2" goto :accesos_directos
if "%opcion%"=="3" goto :pwa
if "%opcion%"=="4" goto :todos
goto :error

:app_completa
echo.
echo 🔨 Creando App Completa...
echo.
python crear_iconos.py
echo.
python crear_app_escritorio.py
goto :fin

:accesos_directos
echo.
echo 🔗 Creando Accesos Directos Elegantes...
echo.
python crear_iconos.py
call crear_accesos_directos.bat
goto :fin

:pwa
echo.
echo 📱 Configurando PWA...
echo.
python crear_iconos.py
echo ✅ PWA configurada
echo 📋 Los usuarios pueden instalar desde el navegador:
echo    1. Ir a la web
echo    2. Clic en el icono de "Instalar app"
echo    3. ¡Listo! App en el escritorio
goto :fin

:todos
echo.
echo 🎯 Creando TODOS los tipos...
echo.
python crear_iconos.py
echo.
python crear_app_escritorio.py
echo.
call crear_accesos_directos.bat
echo.
echo ✅ PWA también configurada
goto :fin

:error
echo.
echo ❌ Opción no válida
pause
exit /b 1

:fin
echo.
echo ==========================================
echo 🎉 ¡INSTALACIÓN COMPLETADA!
echo ==========================================
echo.
echo 📁 Archivos creados:
if exist "dist\CWS_Cotizaciones.exe" echo    ✅ dist\CWS_Cotizaciones.exe (App completa)
if exist "Accesos_Directos_CWS" echo    ✅ Accesos_Directos_CWS\ (Accesos directos)
if exist "static\manifest.json" echo    ✅ PWA configurada
echo    ✅ Iconos profesionales en static\
echo.
echo 📤 Para distribuir a usuarios:
echo    • App completa: Envía dist\CWS_Cotizaciones.exe
echo    • Accesos directos: Envía carpeta Accesos_Directos_CWS\
echo    • PWA: Los usuarios instalan desde el navegador
echo.
echo 📋 Recuerda:
echo    • El servidor debe estar ejecutándose
echo    • Usuarios deben estar en la misma red
echo    • Instrucciones incluidas para usuarios
echo.
pause