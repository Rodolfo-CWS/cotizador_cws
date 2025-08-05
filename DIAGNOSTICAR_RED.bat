@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    🔍 DIAGNÓSTICO DE RED                       ║
echo ║                     COTIZADOR CWS v2.0                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 📊 Recopilando información de red...
echo.

REM Obtener información de red
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                        🌐 INFORMACIÓN DE IP                     ║
echo ╚══════════════════════════════════════════════════════════════════╝
ipconfig | find "IPv4"
echo.

REM Verificar firewall
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                        🛡️  ESTADO DEL FIREWALL                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
netsh advfirewall show allprofiles state
echo.

REM Verificar regla específica del puerto 5000
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    🔐 REGLAS PARA PUERTO 5000                   ║
echo ╚══════════════════════════════════════════════════════════════════╝
netsh advfirewall firewall show rule name="Cotizador CWS" 2>nul || echo ❌ No existe regla para Cotizador CWS
echo.

REM Verificar si el puerto 5000 está en uso
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                      🌐 PUERTOS EN USO                          ║
echo ╚══════════════════════════════════════════════════════════════════╝
netstat -an | find ":5000"
if %errorLevel% neq 0 (
    echo ❌ Puerto 5000 no está activo
    echo 💡 Ejecuta EJECUTAR_RAPIDO.bat para iniciar el servidor
) else (
    echo ✅ Puerto 5000 está activo
)
echo.

REM Verificar conectividad de red básica
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    📶 CONECTIVIDAD DE RED                       ║
echo ╚══════════════════════════════════════════════════════════════════╝

REM Obtener IP para pruebas
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "192.168"') do (
    set IP=%%i
    goto :found_ip
)

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| find "IPv4" ^| find "10."') do (
    set IP=%%i
    goto :found_ip
)

:found_ip
REM Limpiar espacios de la IP
set IP=%IP: =%

echo 🖥️  IP de esta computadora: %IP%
echo.

REM Probar conectividad local
echo 🧪 Probando conectividad local...
ping -n 1 %IP% >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Conectividad local: OK
) else (
    echo ❌ Conectividad local: FALLA
)

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                        📋 RESUMEN                               ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo 📱 PARA ACCEDER DESDE EL CELULAR:
echo    👉 http://%IP%:5000
echo.
echo 🔧 PASOS A SEGUIR:
echo.
echo    SI EL PUERTO 5000 NO ESTÁ ACTIVO:
echo    1️⃣  Ejecutar: EJECUTAR_RAPIDO.bat
echo    2️⃣  Luego probar desde celular
echo.
echo    SI AÚN NO FUNCIONA:
echo    1️⃣  Ejecutar como ADMINISTRADOR: CONFIGURAR_ACCESO_MOVIL.bat
echo    2️⃣  Verificar que celular esté en misma WiFi
echo    3️⃣  Probar: http://%IP%:5000
echo.
echo    SI SIGUE FALLANDO:
echo    1️⃣  Desactivar temporalmente antivirus
echo    2️⃣  Verificar configuración del router
echo    3️⃣  Probar desde otra app en el celular
echo.
echo 💡 TIP: Copia exactamente esta dirección en tu celular:
echo     http://%IP%:5000
echo.
pause