# 🚀 **COTIZADOR CWS - INSTALACIÓN EN CUALQUIER COMPUTADORA**

## ⚡ **INSTALACIÓN SÚPER RÁPIDA (3 PASOS)**

### **PASO 1: Copiar Archivos**
- Copia TODA la carpeta `cotizador_cws` a la nueva computadora
- Ubicación recomendada: `C:\cotizador_cws` o `Escritorio\cotizador_cws`

### **PASO 2: Instalar Automáticamente**  
- **Doble clic** en: `INSTALAR_AUTOMATICO.bat`
- Espera 2-5 minutos (descarga e instala todo automáticamente)
- ✅ Si aparece "INSTALACIÓN COMPLETADA" = ¡Listo!

### **PASO 3: Ejecutar**
- **Doble clic** en: `EJECUTAR_RAPIDO.bat` 
- Abre navegador en: http://localhost:5000
- ¡Ya puedes usar el cotizador!

---

## 🔧 **SI ALGO FALLA...**

### **❌ "Python no está instalado"**
1. Ve a: https://www.python.org/downloads/
2. Descarga **Python 3.9 o superior**
3. **✅ IMPORTANTE**: Marca "Add Python to PATH" durante instalación
4. Reinicia la computadora
5. Ejecuta `INSTALAR_AUTOMATICO.bat` nuevamente

### **❌ "Error en dependencias"**
- El script instala automáticamente todo lo necesario
- Si falla, instala manualmente con: `pip install flask python-dotenv`

### **❌ "No se puede generar PDF"**  
- WeasyPrint falló (es opcional)
- La app funciona perfectamente sin PDFs
- Para habilitar PDFs: `pip install weasyprint`

---

## 📁 **ARCHIVOS IMPORTANTES**

| Archivo | Descripción |
|---------|-------------|
| `INSTALAR_AUTOMATICO.bat` | 🔧 Instala todo automáticamente |
| `EJECUTAR_RAPIDO.bat` | 🚀 Inicia la aplicación |
| `cotizaciones_offline.json` | 💾 Tus cotizaciones guardadas |
| `Lista de materiales.csv` | 📋 Catálogo de materiales |
| `app.py` | 🐍 Código principal |
| `templates/` | 🎨 Interfaz web |

---

## 🌐 **USO DIARIO**

### **Para Iniciar el Cotizador:**
1. Doble clic en: `EJECUTAR_RAPIDO.bat`
2. Abre navegador: http://localhost:5000
3. ¡Comienza a cotizar!

### **Para Detener:**
- En la ventana negra: Presiona `Ctrl + C`
- O simplemente cierra la ventana

---

## 💡 **CONSEJOS PRO**

### **✅ Backup Automático**
- Tus cotizaciones se guardan en: `cotizaciones_offline.json`
- Copia este archivo regularmente como respaldo

### **✅ Uso en Múltiples Computadoras**
- Copia la carpeta completa a USB/Google Drive  
- En cada computadora: ejecuta `INSTALAR_AUTOMATICO.bat`
- Todas compartirán las mismas cotizaciones

### **✅ Actualizar Materiales**
- Edita: `Lista de materiales.csv`
- Reinicia la aplicación para ver cambios

---

## 🚨 **SOPORTE TÉCNICO**

### **Computadora Nueva:**
```bash
1. Copiar carpeta cotizador_cws
2. Ejecutar INSTALAR_AUTOMATICO.bat  
3. Ejecutar EJECUTAR_RAPIDO.bat
4. ¡Listo!
```

### **Si Necesitas Ayuda:**
- Revisa el archivo: `README.md`
- O contacta al administrador del sistema

---

**🎉 ¡El Cotizador CWS ahora funciona en CUALQUIER computadora Windows!**