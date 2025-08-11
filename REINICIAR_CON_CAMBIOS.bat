@echo off
echo ========================================
echo  REINICIAR SERVIDOR CON CAMBIOS APLICADOS
echo ========================================
echo.

echo [INFO] Los siguientes cambios han sido aplicados:
echo   1. PDF sin prefijo "Cotizacion_" 
echo   2. Calculos de subtotales en revisiones corregidos
echo   3. Integracion Google Drive implementada
echo.

echo [PASO 1] Deteniendo procesos Python existentes...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul

echo [PASO 2] Activando entorno virtual...
if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
    echo Entorno virtual activado
) else (
    echo [WARNING] No se encontro entorno virtual, usando Python global
)

echo.
echo [PASO 3] Iniciando servidor Flask con cambios aplicados...
echo.
echo ==========================================
echo  SERVIDOR REINICIADO - CAMBIOS APLICADOS
echo ==========================================
echo.
echo Las correcciones implementadas:
echo  - PDFs sin prefijo confuso
echo  - Calculos correctos en revisiones  
echo  - Google Drive automatico
echo.
echo Presiona Ctrl+C para detener el servidor
echo ==========================================
echo.

python app.py

pause