# 🌊 **HEROKU DEPLOY SÚPER FÁCIL (SIN CLI)**

## ⚡ **MÉTODO DIRECTO DESDE GITHUB**

### **PASO 1: Crear cuenta Heroku**
- Ve a: https://heroku.com
- **Sign up** → Crear cuenta gratuita
- Verificar email

### **PASO 2: Crear nueva aplicación**
- En Heroku Dashboard: **"New"** → **"Create new app"**
- **App name**: `cotizador-cws-2024` (debe ser único)
- **Region**: United States
- **"Create app"**

### **PASO 3: Conectar con GitHub**
- En tu app → **Deploy tab**
- **Deployment method**: **"GitHub"**
- **"Connect to GitHub"** → Autorizar
- **Repository name**: `cotizador-cws`
- **"Connect"**

### **PASO 4: Deploy automático**
- **Manual deploy** → Branch: `main`
- **"Deploy Branch"**
- ⏳ Esperar 2-3 minutos

### **PASO 5: Configurar variables**
- **Settings tab** → **"Reveal Config Vars"**
- Agregar:
  ```
  SECRET_KEY = cotizador-cws-super-secreto-2024
  FLASK_DEBUG = False  
  APP_NAME = CWS Cotizaciones
  ```

### **PASO 6: ¡LISTO!**
- **"Open app"** para ver tu cotizador
- URL será: `https://cotizador-cws-2024.herokuapp.com`

---

## 💰 **COSTO**
- **Primeros pasos**: GRATIS
- **Para uso continuo**: $7/mes (Eco Dyno)
- Necesitas agregar tarjeta de crédito

---

## 🔧 **SI HAY ERRORES**
- Ve a **"More"** → **"View logs"** para ver detalles
- Los errores más comunes se solucionan agregando las variables de entorno

## 🎉 **RESULTADO FINAL**
¡Tu cotizador funcionando en: `https://tu-app.herokuapp.com`!
Accesible desde cualquier dispositivo en el mundo 🌍