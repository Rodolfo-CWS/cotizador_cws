@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                 🚨 SOLUCIÓN ALTERNATIVA                       ║
echo ║           Si el acceso móvil aún no funciona                  ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 🔧 MÉTODOS ALTERNATIVOS:
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    1️⃣  USAR PUERTO DIFERENTE                    ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo    • Cambiar de puerto 5000 a 8080
echo    • Menos problemas con firewall
echo    • Acceso: http://IP:8080
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    2️⃣  DESHABILITAR FIREWALL                    ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo    • Temporalmente para pruebas
echo    • Panel de Control ^> Firewall ^> Desactivar
echo    • ⚠️  Reactivar después
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    3️⃣  USAR HOTSPOT MÓVIL                       ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo    • Crear hotspot desde el celular
echo    • Conectar PC al hotspot del celular
echo    • Probar http://192.168.43.1:5000
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    4️⃣  SERVICIO NGROK (AVANZADO)                ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo    • Túnel a través de internet
echo    • Acceso desde cualquier lugar
echo    • Requiere cuenta en ngrok.com
echo.

pause

echo.
echo 🚀 ¿QUIERES PROBAR LA SOLUCIÓN DEL PUERTO 8080?
echo.
set /p respuesta="Escribe 'si' para cambiar a puerto 8080: "

if /i "%respuesta%"=="si" (
    echo.
    echo 🔄 Creando versión con puerto 8080...
    
    REM Crear script modificado para puerto 8080
    echo @echo off > EJECUTAR_PUERTO_8080.bat
    echo chcp 65001 ^>nul >> EJECUTAR_PUERTO_8080.bat
    echo cls >> EJECUTAR_PUERTO_8080.bat
    echo echo 🚀 Iniciando Cotizador CWS en puerto 8080... >> EJECUTAR_PUERTO_8080.bat
    echo call env\Scripts\activate.bat >> EJECUTAR_PUERTO_8080.bat
    echo echo 📱 Accede desde celular: http://[TU-IP]:8080 >> EJECUTAR_PUERTO_8080.bat
    echo python -c "from app import app; app.run(host='0.0.0.0', port=8080, debug=False)" >> EJECUTAR_PUERTO_8080.bat
    echo pause >> EJECUTAR_PUERTO_8080.bat
    
    echo ✅ Archivo creado: EJECUTAR_PUERTO_8080.bat
    echo.
    echo 📋 PRÓXIMOS PASOS:
    echo    1. Ejecutar: EJECUTAR_PUERTO_8080.bat
    echo    2. En celular ir a: http://[IP]:8080
    echo    3. Reemplazar [IP] por tu IP real
    echo.
) else (
    echo.
    echo 💡 No hay problema, puedes probar estas opciones después
    echo.
)

echo 🆘 SI NECESITAS AYUDA ADICIONAL:
echo    • Revisar configuración del router
echo    • Contactar administrador de red
echo    • Usar la aplicación solo en la computadora
echo.
pause