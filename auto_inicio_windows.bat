@echo off
title Configurar Auto-Inicio CWS
echo ==========================================
echo   CONFIGURAR AUTO-INICIO CON WINDOWS
echo ==========================================
echo.
echo Este script configurará CWS Cotizaciones para
echo que se inicie automáticamente con Windows.
echo.
echo ¿Desea continuar? (S/N)
set /p respuesta=

if /i "%respuesta%"=="S" (
    echo.
    echo Configurando auto-inicio...
    
    REM Crear acceso directo en la carpeta de inicio
    set "carpeta_inicio=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    set "ruta_script=%~dp0iniciar_servidor.bat"
    
    REM Crear script VBS para ejecutar sin ventana visible
    echo Set oWS = WScript.CreateObject("WScript.Shell") > "%~dp0iniciar_silencioso.vbs"
    echo oWS.Run """" ^& "%ruta_script%" ^& """", 0 >> "%~dp0iniciar_silencioso.vbs"
    
    REM Crear acceso directo
    powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%carpeta_inicio%\CWS Cotizaciones.lnk');$s.TargetPath='%~dp0iniciar_silencioso.vbs';$s.Save()"
    
    echo.
    echo ✅ Configuración completada!
    echo.
    echo CWS Cotizaciones se iniciará automáticamente
    echo la próxima vez que reinicie Windows.
    echo.
    echo Para desactivar:
    echo 1. Ir a Configuración ^> Aplicaciones ^> Inicio
    echo 2. Desactivar "CWS Cotizaciones"
    echo.
) else (
    echo.
    echo Configuración cancelada.
    echo.
)

echo Presione cualquier tecla para salir...
pause >nul