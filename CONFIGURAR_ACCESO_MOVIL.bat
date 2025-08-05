@echo off
chcp 65001 >nul

REM Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║                    ⚠️  PERMISOS DE ADMINISTRADOR                ║
    echo ╚════════════════════════════════════════════════════════════════╝
    echo.
    echo ❌ Este script necesita ejecutarse como ADMINISTRADOR
    echo.
    echo 🔧 CÓMO EJECUTAR COMO ADMINISTRADOR:
    echo    1. Clic derecho en: CONFIGURAR_ACCESO_MOVIL.bat
    echo    2. Seleccionar: "Ejecutar como administrador"
    echo    3. Confirmar cuando Windows pregunte
    echo.
    pause
    exit /b 1
)

cls
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                  🔐 CONFIGURAR ACCESO MÓVIL                    ║
echo ║                     COTIZADOR CWS v2.0                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 🔍 Verificando configuración actual del firewall...
echo.

REM Verificar si la regla ya existe
netsh advfirewall firewall show rule name="Cotizador CWS" >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Regla del firewall ya existe
    echo 🔄 Eliminando regla anterior para recrearla...
    netsh advfirewall firewall delete rule name="Cotizador CWS"
)

echo 🔧 Creando regla de firewall para Puerto 5000...

REM Crear regla de firewall para permitir conexiones entrantes en puerto 5000
netsh advfirewall firewall add rule name="Cotizador CWS" dir=in action=allow protocol=TCP localport=5000
if %errorLevel% equ 0 (
    echo ✅ Regla de firewall creada exitosamente
) else (
    echo ❌ Error creando regla de firewall
    goto :error
)

echo.
echo 🌐 Obteniendo información de red...

REM Obtener IP local
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "192.168"') do (
    set IP=%%i
    goto :found_ip
)

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "10."') do (
    set IP=%%i
    goto :found_ip
)

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "172."') do (
    set IP=%%i
    goto :found_ip
)

:found_ip
REM Limpiar espacios de la IP
set IP=%IP: =%

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    ✅ CONFIGURACIÓN COMPLETADA                 ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🎉 El acceso móvil ha sido configurado correctamente
echo.
echo 📋 INFORMACIÓN DE CONEXIÓN:
echo    🖥️  IP de esta computadora: %IP%
echo    🌐 Puerto configurado: 5000
echo    🔐 Firewall: Configurado
echo.
echo 📱 PASOS PARA CONECTAR DESDE EL CELULAR:
echo.
echo    1. 📶 VERIFICAR WIFI:
echo       - Celular y computadora en la MISMA red WiFi
echo       - Nombre de red WiFi debe ser idéntico
echo.
echo    2. 🚀 INICIAR SERVIDOR:
echo       - Ejecutar: EJECUTAR_RAPIDO.bat (en esta computadora)
echo       - Mantener ventana abierta
echo.
echo    3. 📱 ABRIR EN CELULAR:
echo       - Navegador del celular
echo       - Escribir: http://%IP%:5000
echo       - Presionar Enter
echo.
echo 🔧 SI AÚN NO FUNCIONA:
echo    1. Verificar que ambos dispositivos estén en la misma WiFi
echo    2. Desactivar temporalmente el antivirus
echo    3. Probar con: http://%IP%:5000 (copia exacta de esta dirección)
echo.
echo ⚠️  NOTA DE SEGURIDAD:
echo    - Esta configuración permite conexiones locales únicamente
echo    - No expone tu aplicación a internet
echo    - Solo dispositivos en tu red WiFi pueden acceder
echo.
pause
goto :end

:error
echo.
echo ❌ ERROR EN LA CONFIGURACIÓN
echo.
echo 🔧 POSIBLES SOLUCIONES:
echo    1. Ejecutar como administrador
echo    2. Verificar que Windows Firewall esté habilitado
echo    3. Contactar al administrador del sistema
echo.
pause

:end