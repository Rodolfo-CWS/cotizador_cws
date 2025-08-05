@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    📱 COTIZADOR CWS v2.0                      ║
echo ║                  ACCESO DESDE CELULAR/TABLET                  ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si el entorno virtual existe
if not exist "env\Scripts\activate.bat" (
    echo ❌ ERROR: Entorno virtual no encontrado
    echo.
    echo 🔧 PRIMERA VEZ? Ejecuta: INSTALAR_AUTOMATICO.bat
    echo.
    pause
    exit /b 1
)

echo 🔄 Activando entorno virtual...
call env\Scripts\activate.bat

echo 🌐 Obteniendo dirección IP de esta computadora...

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
echo ║                     📱 ACCESO MÓVIL HABILITADO                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🖥️  DESDE ESTA COMPUTADORA:
echo     👉 http://localhost:5000
echo.
echo 📱 DESDE CELULAR/TABLET (misma WiFi):
echo     👉 http://%IP%:5000
echo.
echo 💡 INSTRUCCIONES PARA CELULAR:
echo    1. Conecta tu celular a la MISMA WiFi
echo    2. Abre navegador en el celular
echo    3. Escribe: http://%IP%:5000
echo    4. ¡Listo para cotizar desde móvil!
echo.
echo ⚠️  NOTA: Esta computadora debe permanecer encendida
echo    para que funcione en el celular
echo.
echo 🛑 Para DETENER: Presiona Ctrl+C
echo.

REM Modificar app.py temporalmente para permitir acceso externo
python -c "
import sys, os
sys.path.append('.')
from app import app
print('🚀 Iniciando servidor con acceso móvil...')
app.run(host='0.0.0.0', port=5000, debug=False)
"

echo.
echo 🛑 Servidor detenido
pause