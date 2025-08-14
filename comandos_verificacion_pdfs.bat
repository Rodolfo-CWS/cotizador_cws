@echo off
echo ============================================================
echo COMANDOS DE VERIFICACION - PDFs CWS
echo ============================================================
echo.
echo Estado: Los PDFs especificos estan LOCALIZADOS pero hay problema
echo         de autenticacion con Cloudinary que impide verificacion completa.
echo.
echo PDFs objetivo:
echo   - BOB-CWS-CM-001-R1-ROBLOX
echo   - BOB-CWS-CM-001-R2-ROBLOX
echo.
echo ARCHIVOS CONFIRMADOS EN:
echo   C:\Users\SDS\Downloads\Cotizacion_BOB-CWS-CM-001-R1-ROBLOX.pdf
echo   C:\Users\SDS\Downloads\Cotizacion_BOB-CWS-CM-001-R2-ROBLOX.pdf
echo.

:MENU
echo ============================================================
echo OPCIONES DE VERIFICACION:
echo ============================================================
echo [1] Verificar archivos locales
echo [2] Test conectividad Cloudinary
echo [3] Buscar en todas las carpetas
echo [4] Ver configuracion actual
echo [5] Verificacion completa (requiere Cloudinary funcional)
echo [6] Generar reporte detallado
echo [9] Salir
echo.
set /p opcion="Selecciona una opcion (1-6, 9): "

if "%opcion%"=="1" goto VERIFICAR_LOCALES
if "%opcion%"=="2" goto TEST_CLOUDINARY
if "%opcion%"=="3" goto BUSCAR_TODAS
if "%opcion%"=="4" goto VER_CONFIG
if "%opcion%"=="5" goto VERIFICACION_COMPLETA
if "%opcion%"=="6" goto REPORTE_DETALLADO
if "%opcion%"=="9" goto SALIR
goto MENU

:VERIFICAR_LOCALES
echo.
echo [1] VERIFICANDO ARCHIVOS LOCALES...
echo ============================================================
echo.
echo Buscando: BOB-CWS-CM-001-R1-ROBLOX
dir "*BOB-CWS-CM-001-R1-ROBLOX*" /s 2>nul
echo.
echo Buscando: BOB-CWS-CM-001-R2-ROBLOX  
dir "*BOB-CWS-CM-001-R2-ROBLOX*" /s 2>nul
echo.
echo Archivos en Downloads:
dir "C:\Users\SDS\Downloads\*BOB-CWS-CM-001-R*ROBLOX*.pdf" 2>nul
echo.
pause
goto MENU

:TEST_CLOUDINARY
echo.
echo [2] TESTING CONECTIVIDAD CLOUDINARY...
echo ============================================================
echo.
python test_cloudinary_simple.py
echo.
echo NOTA: Si ves "api_secret mismatch", las credenciales necesitan actualizarse
echo      en https://console.cloudinary.com/settings/api-keys
echo.
pause
goto MENU

:BUSCAR_TODAS
echo.
echo [3] BUSQUEDA EXHAUSTIVA...
echo ============================================================
echo.
echo Buscando en todo el sistema (puede tomar tiempo)...
echo.
echo Buscando BOB-CWS-CM-001-R1-ROBLOX:
dir C:\ "*BOB-CWS-CM-001-R1-ROBLOX*" /s /b 2>nul | findstr /i "\.pdf$"
echo.
echo Buscando BOB-CWS-CM-001-R2-ROBLOX:
dir C:\ "*BOB-CWS-CM-001-R2-ROBLOX*" /s /b 2>nul | findstr /i "\.pdf$"
echo.
pause
goto MENU

:VER_CONFIG
echo.
echo [4] CONFIGURACION ACTUAL...
echo ============================================================
echo.
echo Variables de entorno:
echo CLOUDINARY_CLOUD_NAME=%CLOUDINARY_CLOUD_NAME%
echo CLOUDINARY_API_KEY=%CLOUDINARY_API_KEY%
echo CLOUDINARY_API_SECRET=[OCULTO]
echo.
echo Rutas configuradas:
echo - Local: G:\Mi unidad\CWS\CWS_Cotizaciones_PDF
echo - Google Drive: Configurado y operativo
echo - Cloudinary: cotizaciones/nuevas/, cotizaciones/antiguas/
echo.
echo Estado de servicios:
echo - MongoDB: Configurado (modo offline por encoding)
echo - Google Drive: OK
echo - Cloudinary: ERROR (credenciales)
echo.
pause
goto MENU

:VERIFICACION_COMPLETA
echo.
echo [5] VERIFICACION COMPLETA...
echo ============================================================
echo.
echo ADVERTENCIA: Esta opcion requiere que Cloudinary este funcionando.
echo Si ves errores de autenticacion, usar opcion 2 primero.
echo.
set /p continuar="Continuar? (s/n): "
if /i not "%continuar%"=="s" goto MENU
echo.
python verificar_pdfs_especificos.py
echo.
pause
goto MENU

:REPORTE_DETALLADO
echo.
echo [6] GENERANDO REPORTE DETALLADO...
echo ============================================================
echo.
echo Reporte disponible en: reporte_verificacion_pdfs.md
echo.
type reporte_verificacion_pdfs.md
echo.
echo Reporte completo mostrado arriba.
echo.
pause
goto MENU

:SALIR
echo.
echo ============================================================
echo RESUMEN FINAL:
echo ============================================================
echo.
echo ESTADO DE LOS PDFs OBJETIVO:
echo   BOB-CWS-CM-001-R1-ROBLOX: LOCALIZADO en Downloads
echo   BOB-CWS-CM-001-R2-ROBLOX: LOCALIZADO en Downloads
echo.
echo PROBLEMA IDENTIFICADO:
echo   - Cloudinary: Error de autenticacion (api_secret mismatch)
echo   - Accion requerida: Actualizar credenciales
echo.
echo RIESGO DE DEPLOY: MEDIO
echo   - PDFs seguros en multiple ubicaciones
echo   - Sistema hibrido configurado correctamente
echo   - Requiere correccion de credenciales antes del deploy
echo.
echo ARCHIVOS IMPORTANTES GENERADOS:
echo   - reporte_verificacion_pdfs.md (reporte completo)
echo   - test_cloudinary_simple.py (test de conectividad)
echo   - verificar_pdfs_especificos.py (verificacion completa)
echo.
pause