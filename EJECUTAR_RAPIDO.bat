@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    🚀 COTIZADOR CWS v2.0                      ║
echo ║                      INICIO RÁPIDO                            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si el entorno virtual existe
if not exist "env\Scripts\activate.bat" (
    echo ❌ ERROR: Entorno virtual no encontrado
    echo.
    echo 🔧 PRIMERA VEZ USANDO ESTA COMPUTADORA?
    echo    Ejecuta primero: INSTALAR_AUTOMATICO.bat
    echo.
    pause
    exit /b 1
)

echo 🔄 Activando entorno virtual...
call env\Scripts\activate.bat

echo 🌐 Iniciando Cotizador CWS...
echo.
echo 📱 ABRE TU NAVEGADOR Y VE A:
echo    👉 http://localhost:5000
echo.
echo ⚠️  Para DETENER el servidor: Presiona Ctrl+C
echo.

python app.py

echo.
echo 🛑 Servidor detenido
pause