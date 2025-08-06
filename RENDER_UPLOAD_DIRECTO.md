# 📤 **RENDER - UPLOAD DIRECTO (SIN GITHUB)**

## ⚡ **MÉTODO MÁS FÁCIL:**

### **PASO 1: Preparar ZIP**
1. Seleccionar TODOS los archivos de la carpeta `cotizador_cws`
2. **MENOS** la carpeta `env/` (muy pesada)
3. **Clic derecho** → **"Enviar a"** → **"Carpeta comprimida (zip)"**
4. Nombrar: `cotizador-cws.zip`

### **PASO 2: Subir a Render**
1. Ve a: https://render.com
2. **"Get Started for Free"** → Crear cuenta
3. **"New +"** → **"Web Service"**
4. **"Deploy an existing image or build from source code"**
5. **"Upload from computer"**
6. Seleccionar tu `cotizador-cws.zip`

### **PASO 3: Configurar**
```
Name: cotizador-cws
Runtime: Python 3
Build Command: pip install -r requirements.txt  
Start Command: gunicorn app:app
```

### **PASO 4: Variables de entorno**
```
SECRET_KEY = cotizador-cws-super-secreto-2024
FLASK_DEBUG = False
APP_NAME = CWS Cotizaciones
```

### **PASO 5: Deploy**
- **"Create Web Service"**
- ⏳ Esperar 3-5 minutos
- ✅ **¡Funciona!**

---

## 🎉 **RESULTADO:**
**URL gratuita**: `https://cotizador-cws.onrender.com`

## 💡 **VENTAJAS:**
- ✅ **Sin GitHub** - Upload directo
- ✅ **750 horas gratis/mes**
- ✅ **HTTPS automático**
- ✅ **Deploy en minutos**