@echo off
echo ========================================
echo    TESTS E2E - CWS COTIZADOR
echo ========================================
echo.

echo Verificando instalacion de Playwright...
call npx playwright --version
if %errorlevel% neq 0 (
    echo ERROR: Playwright no esta instalado
    echo Ejecutando instalacion...
    call npm install @playwright/test
    call npx playwright install chromium
)

echo.
echo Iniciando tests E2E...
echo Nota: El servidor Flask se iniciara automaticamente
echo.

call npx playwright test

echo.
echo ========================================
echo Tests completados. Para ver el reporte:
echo npx playwright show-report
echo ========================================
pause