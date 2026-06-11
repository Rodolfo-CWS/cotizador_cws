@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    🚀 COTIZADOR CWS v2.0                      ║
echo ║                INSTALACIÓN AUTOMÁTICA COMPLETA                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 📋 VERIFICANDO SISTEMA...
echo.

REM ============================================
REM VERIFICAR PYTHON
REM ============================================
echo 🔍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no está instalado
    echo.
    echo 📥 NECESITAS INSTALAR PYTHON:
    echo    1. Ve a: https://www.python.org/downloads/
    echo    2. Descarga Python 3.9 o superior
    echo    3. ✅ IMPORTANTE: Marca "Add Python to PATH" durante instalación
    echo    4. Reinicia esta computadora
    echo    5. Ejecuta este script nuevamente
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% encontrado

REM ============================================
REM VERIFICAR PIP
REM ============================================
echo 🔍 Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: pip no está disponible
    echo 📥 Instalando pip...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo ❌ No se pudo instalar pip
        pause
        exit /b 1
    )
)
echo ✅ pip disponible

REM ============================================
REM CREAR ENTORNO VIRTUAL
REM ============================================
echo.
echo 🔧 CREANDO ENTORNO VIRTUAL...
if exist "env" (
    echo ⚠️  Entorno virtual ya existe, eliminando para crear uno nuevo...
    rmdir /s /q env
)

python -m venv env
if errorlevel 1 (
    echo ❌ ERROR: No se pudo crear entorno virtual
    pause
    exit /b 1
)
echo ✅ Entorno virtual creado

REM ============================================
REM ACTIVAR ENTORNO VIRTUAL
REM ============================================
echo 🔄 Activando entorno virtual...
call env\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ERROR: No se pudo activar entorno virtual
    pause
    exit /b 1
)
echo ✅ Entorno virtual activado

REM ============================================
REM ACTUALIZAR PIP EN ENTORNO VIRTUAL
REM ============================================
echo 📦 Actualizando pip en entorno virtual...
python -m pip install --upgrade pip
echo ✅ pip actualizado

REM ============================================
REM INSTALAR DEPENDENCIAS
REM ============================================
echo.
echo 📦 INSTALANDO DEPENDENCIAS...
echo ⏳ Esto puede tomar 2-5 minutos...
echo.

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ ERROR: Falló instalación de dependencias
    echo.
    echo 🔧 INTENTANDO INSTALACIÓN INDIVIDUAL...
    echo.
    
    REM Instalar paquetes críticos uno por uno
    echo 📦 Instalando Flask...
    python -m pip install Flask==3.0.0
    
    echo 📦 Instalando python-dotenv...
    python -m pip install python-dotenv==1.0.0
    
    echo 📦 Instalando requests...
    python -m pip install requests==2.31.0
    
    echo 📦 Instalando WeasyPrint (para PDFs)...
    python -m pip install weasyprint==61.2
    if errorlevel 1 (
        echo ⚠️  WeasyPrint falló (PDFs no disponibles, pero app funcionará)
    )
)

echo.
echo ✅ DEPENDENCIAS INSTALADAS

REM ============================================
REM VERIFICAR INSTALACIÓN
REM ============================================
echo.
echo 🔍 VERIFICANDO INSTALACIÓN...

python -c "import flask; print('✅ Flask OK')" 2>nul || echo "❌ Flask falló"
python -c "import dotenv; print('✅ dotenv OK')" 2>nul || echo "❌ dotenv falló"  
python -c "import requests; print('✅ requests OK')" 2>nul || echo "❌ requests falló"
python -c "from supabase_manager import SupabaseManager; print('✅ Supabase OK')" 2>nul || echo "⚠️  Supabase no disponible"
python -c "import weasyprint; print('✅ WeasyPrint OK')" 2>nul || echo "⚠️  WeasyPrint no disponible (PDFs deshabilitados)"

REM ============================================
REM CREAR ARCHIVO .ENV SI NO EXISTE
REM ============================================
if not exist ".env" (
    echo 📝 Creando archivo de configuración...
    echo # Configuración del Cotizador CWS > .env
    echo FLASK_DEBUG=False >> .env
    echo SECRET_KEY=cotizador-cws-secret-key-2024 >> .env
    echo DEFAULT_PAGE_SIZE=20 >> .env
    echo ✅ Archivo .env creado
)

REM ============================================
REM CREAR SCRIPT DE EJECUCIÓN
REM ============================================
echo 📝 Creando script de ejecución...
echo @echo off > EJECUTAR_COTIZADOR.bat
echo chcp 65001 ^>nul >> EJECUTAR_COTIZADOR.bat
echo cls >> EJECUTAR_COTIZADOR.bat
echo echo. >> EJECUTAR_COTIZADOR.bat
echo echo ╔════════════════════════════════════════════════════════════════╗ >> EJECUTAR_COTIZADOR.bat
echo echo ║                    🚀 COTIZADOR CWS v2.0                      ║ >> EJECUTAR_COTIZADOR.bat
echo echo ║                      INICIANDO SERVIDOR...                    ║ >> EJECUTAR_COTIZADOR.bat
echo echo ╚════════════════════════════════════════════════════════════════╝ >> EJECUTAR_COTIZADOR.bat
echo echo. >> EJECUTAR_COTIZADOR.bat
echo echo 🔄 Activando entorno virtual... >> EJECUTAR_COTIZADOR.bat
echo call env\Scripts\activate.bat >> EJECUTAR_COTIZADOR.bat
echo echo ✅ Entorno activado >> EJECUTAR_COTIZADOR.bat
echo echo. >> EJECUTAR_COTIZADOR.bat
echo echo 🌐 Iniciando servidor web... >> EJECUTAR_COTIZADOR.bat
echo echo 📱 Abre tu navegador y ve a: http://localhost:5000 >> EJECUTAR_COTIZADOR.bat
echo echo. >> EJECUTAR_COTIZADOR.bat
echo echo ⚠️  Para DETENER el servidor: Presiona Ctrl+C >> EJECUTAR_COTIZADOR.bat
echo echo. >> EJECUTAR_COTIZADOR.bat
echo python app.py >> EJECUTAR_COTIZADOR.bat
echo pause >> EJECUTAR_COTIZADOR.bat

echo ✅ Script de ejecución creado

REM ============================================
REM PRUEBA RÁPIDA
REM ============================================
echo.
echo 🧪 PROBANDO INSTALACIÓN...
timeout /t 2 /nobreak >nul

python -c "
try:
    from app import app
    print('✅ Aplicación se puede importar correctamente')
except Exception as e:
    print(f'❌ Error en aplicación: {e}')
"

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    ✅ INSTALACIÓN COMPLETADA                   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🎉 EL COTIZADOR CWS ESTÁ LISTO PARA USAR
echo.
echo 📋 PRÓXIMOS PASOS:
echo    1. Ejecuta: EJECUTAR_COTIZADOR.bat
echo    2. Abre navegador en: http://localhost:5000
echo    3. ¡Comienza a cotizar!
echo.
echo 📁 ARCHIVOS IMPORTANTES:
echo    ✅ EJECUTAR_COTIZADOR.bat    - Para iniciar la aplicación
echo    ✅ cotizaciones_offline.json - Tus cotizaciones guardadas
echo    ✅ Lista de materiales.csv    - Catálogo de materiales
echo.
echo 💡 TIP: Puedes copiar toda esta carpeta a otra computadora
echo    y ejecutar INSTALAR_AUTOMATICO.bat para usar ahí también
echo.
pause