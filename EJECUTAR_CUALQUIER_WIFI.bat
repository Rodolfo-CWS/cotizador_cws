@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                📶 COTIZADOR CWS - CUALQUIER WIFI               ║
echo ║              Detecta automáticamente tu red WiFi              ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar entorno virtual
if not exist "env\Scripts\activate.bat" (
    echo ❌ ERROR: Entorno virtual no encontrado
    echo 🔧 Ejecuta primero: INSTALAR_AUTOMATICO.bat
    pause
    exit /b 1
)

echo 🔄 Activando entorno virtual...
call env\Scripts\activate.bat

echo 🌐 Detectando red WiFi actual...

REM Detectar IP automáticamente
set LOCAL_IP=
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "192.168"') do (
    set LOCAL_IP=%%i
    goto :found_ip
)

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "10."') do (
    set LOCAL_IP=%%i
    goto :found_ip
)

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "172."') do (
    set LOCAL_IP=%%i
    goto :found_ip
)

:found_ip
REM Limpiar espacios
set LOCAL_IP=%LOCAL_IP: =%

if "%LOCAL_IP%"=="" (
    echo ❌ No se pudo detectar IP de red local
    echo 💡 Asegúrate de estar conectado a WiFi
    pause
    exit /b 1
)

REM Obtener nombre de la red WiFi
for /f "tokens=2 delims=:" %%i in ('netsh wlan show profiles ^| find "Perfil de todos los usuarios"') do (
    set WIFI_NAME=%%i
    goto :found_wifi
)

:found_wifi
set WIFI_NAME=%WIFI_NAME: =%

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    📶 RED DETECTADA                            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📶 Red WiFi: %WIFI_NAME%
echo 🖥️  IP de esta computadora: %LOCAL_IP%
echo 🌐 Puerto: 5000
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                   📱 ACCESO DESDE MÓVIL                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🔗 COPIA ESTA DIRECCIÓN EN TU CELULAR:
echo.
echo     👉 http://%LOCAL_IP%:5000
echo.
echo 📋 INSTRUCCIONES:
echo    1. Conecta tu CELULAR a la WiFi: %WIFI_NAME%
echo    2. Abre navegador en el celular
echo    3. Pega la dirección: http://%LOCAL_IP%:5000
echo    4. ¡Listo para cotizar!
echo.
echo ⚡ VENTAJA: Esta IP se actualiza automáticamente
echo    para cada red WiFi diferente
echo.
echo 🛑 Para DETENER: Presiona Ctrl+C
echo.

REM Crear archivo con la IP actual para referencia
echo %LOCAL_IP% > ip_actual.txt
echo http://%LOCAL_IP%:5000 > direccion_movil.txt

echo 💾 IP guardada en: ip_actual.txt
echo 📱 Dirección móvil guardada en: direccion_movil.txt
echo.

echo 🚀 Iniciando servidor...
python app.py

echo.
echo 🛑 Servidor detenido
pause