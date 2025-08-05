@echo off
title CWS - Crear Accesos Directos para Usuarios
echo ==========================================
echo       CREAR ACCESOS DIRECTOS CWS
echo ==========================================
echo.

REM Obtener la IP del servidor
echo Detectando IP del servidor...
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /c:"IPv4" ^| find /v "127.0.0.1"') do (
    set "SERVER_IP=%%i"
    goto :ip_found
)

:ip_found
set SERVER_IP=%SERVER_IP: =%
set "URL=http://%SERVER_IP%:5000"

echo IP detectada: %SERVER_IP%
echo URL del servidor: %URL%
echo.

REM Crear carpeta para los accesos directos
if not exist "Accesos_Directos_CWS" mkdir "Accesos_Directos_CWS"

REM Crear acceso directo principal
echo Creando acceso directo principal...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('Accesos_Directos_CWS\\CWS Cotizaciones.lnk');$s.TargetPath='%URL%';$s.IconLocation='%~dp0static\\logo.ico';$s.Description='Sistema de Cotizaciones CWS Company';$s.Save()"

REM Crear script para abrir en navegador
echo @echo off > "Accesos_Directos_CWS\CWS_Cotizaciones.bat"
echo title CWS Cotizaciones >> "Accesos_Directos_CWS\CWS_Cotizaciones.bat"
echo echo Abriendo CWS Cotizaciones... >> "Accesos_Directos_CWS\CWS_Cotizaciones.bat"
echo start "" "%URL%" >> "Accesos_Directos_CWS\CWS_Cotizaciones.bat"
echo exit >> "Accesos_Directos_CWS\CWS_Cotizaciones.bat"

REM Crear archivo de instrucciones
echo # 🏢 CWS Cotizaciones - Acceso para Usuarios > "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo. >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo ## 🚀 Cómo Usar: >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo 1. **Doble clic** en `CWS Cotizaciones.lnk` >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo 2. Se abrirá automáticamente en tu navegador >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo 3. ¡Listo para crear cotizaciones! >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo. >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo ## 📱 URL Directa: >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo `%URL%` >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo. >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo ## ⚠️ Importante: >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo - El servidor debe estar ejecutándose >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo - Deben estar en la misma red WiFi >> "Accesos_Directos_CWS\INSTRUCCIONES.md"
echo - Si no funciona, contactar al administrador >> "Accesos_Directos_CWS\INSTRUCCIONES.md"

echo.
echo ✅ Accesos directos creados exitosamente!
echo.
echo 📁 Ubicación: %~dp0Accesos_Directos_CWS\
echo.
echo 📋 Para distribuir:
echo    1. Comparte la carpeta "Accesos_Directos_CWS"
echo    2. Los usuarios copian el acceso directo a su escritorio
echo    3. ¡Listo! Tendrán un icono bonito en su desktop
echo.

pause