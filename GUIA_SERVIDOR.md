# 🖥️ CWS Cotizaciones - Servidor Centralizado

## 🚀 Inicio Rápido

### Para TI (Administrador del Servidor):
1. **Ejecutar**: Doble clic en `iniciar_servidor.bat`
2. **Anotar la IP**: El sistema mostrará algo como `http://192.168.1.100:5000`
3. **Compartir la IP** con otros usuarios

### Para Otros Usuarios:
1. **Abrir navegador** (Chrome, Firefox, Edge)
2. **Ir a**: `http://IP-DEL-SERVIDOR:5000`
3. **¡Listo!** Ya pueden crear cotizaciones

---

## 🌐 Configuración de Red

### ✅ Lo que SÍ pueden hacer otros usuarios:
- ✅ Crear nuevas cotizaciones
- ✅ Buscar cotizaciones existentes
- ✅ Ver detalles de cotizaciones
- ✅ Generar PDFs (se guardan automáticamente en tu Google Drive)
- ✅ Usar toda la funcionalidad del sistema

### ❌ Lo que NO pueden hacer:
- ❌ Acceder directamente a los archivos PDF
- ❌ Borrar PDFs del sistema
- ❌ Modificar la configuración
- ❌ Acceder a tu Google Drive

---

## 🔧 Administración

### Iniciar el Servidor:
```bash
# Opción 1: Script automático
iniciar_servidor.bat

# Opción 2: Manual
python app.py
```

### Verificar Estado:
- **Sistema**: http://IP:5000/info
- **PDFs**: http://IP:5000/admin/pdfs
- **Materiales**: http://IP:5000/debug-materiales

### Backup Automático:
- ✅ **MongoDB**: Respaldo automático online
- ✅ **Archivo local**: `cotizaciones_offline.json`
- ✅ **PDFs**: Se sincronizan en tu Google Drive

---

## 🛡️ Seguridad

### Datos Protegidos:
- 🔒 **Base de datos**: MongoDB con autenticación
- 🔒 **PDFs**: Solo en tu Google Drive privado
- 🔒 **Configuración**: Variables de entorno protegidas

### Acceso Controlado:
- 📍 **Red local únicamente**: Solo usuarios en tu misma red WiFi/LAN
- 🚫 **Sin acceso externo**: No es accesible desde internet
- 👥 **Multiusuario**: Varios usuarios pueden trabajar simultáneamente

---

## 🆘 Solución de Problemas

### "No se puede conectar":
1. ✅ Verificar que el servidor esté ejecutándose
2. ✅ Confirmar que están en la misma red WiFi
3. ✅ Usar la IP correcta mostrada al iniciar

### "Error al guardar PDF":
1. ✅ Verificar que Google Drive esté sincronizado
2. ✅ Confirmar permisos de escritura en la carpeta
3. ✅ Revisar espacio disponible

### "Materiales no cargan":
1. ✅ Verificar que `Lista de materiales.csv` exista
2. ✅ Reiniciar el servidor
3. ✅ Revisar formato del archivo CSV

---

## 📞 Contacto

**Administrador del Sistema**: Tu Nombre
**Ubicación del Servidor**: Tu Computadora
**Horario de Servicio**: Cuando tu computadora esté encendida

---

## 📈 Próximos Pasos (Opcional)

### Para Mayor Disponibilidad:
- 🖥️ **Servidor dedicado**: Instalar en computadora que esté siempre encendida
- ☁️ **Cloud hosting**: Subir a servicios como Heroku, AWS, etc.
- 🔄 **Auto-inicio**: Configurar para que inicie automáticamente con Windows

### Para Mayor Seguridad:
- 🔐 **Autenticación**: Agregar login de usuarios
- 🛡️ **HTTPS**: Certificados SSL para conexión segura
- 📊 **Logs**: Registros de actividad detallados