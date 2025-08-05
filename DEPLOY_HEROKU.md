# 🌊 **DEPLOY EN HEROKU - TAMBIÉN SÚPER FÁCIL**

## ⚡ **PASOS RÁPIDOS (15 MINUTOS)**

### **1️⃣ Crear cuenta en Heroku**
- Ve a: https://heroku.com
- Crear cuenta gratuita
- Verificar email

### **2️⃣ Instalar Heroku CLI**
- Descargar: https://devcenter.heroku.com/articles/heroku-cli
- Instalar en tu computadora
- Abrir cmd y probar: `heroku --version`

### **3️⃣ Login y crear app**
```bash
# En tu computadora:
cd "C:\Users\SDS\cotizador_cws"

# Login en Heroku
heroku login

# Crear aplicación
heroku create cotizador-cws-2024

# Configurar variables
heroku config:set SECRET_KEY=cotizador-cws-super-secreto-2024
heroku config:set FLASK_DEBUG=False
heroku config:set APP_NAME="CWS Cotizaciones"
```

### **4️⃣ Preparar Git y Deploy**
```bash
# Inicializar Git (si no está hecho)
git init
git add .  
git commit -m "🚀 Cotizador CWS para Heroku"

# Deploy a Heroku
git push heroku main
```

### **5️⃣ ¡LISTO!**
- Heroku te da URL: https://cotizador-cws-2024.herokuapp.com
- ✅ Accesible mundialmente
- ✅ HTTPS automático
- ✅ Logs y monitoreo incluidos

---

## 💰 **COSTO: $7/mes (Eco Dyno)**
- Necesitas agregar tarjeta de crédito
- Más funciones que Railway
- Muy estable y confiable

## 🎉 **RESULTADO FINAL:**
**Tu cotizador estará en:** `https://cotizador-cws-2024.herokuapp.com`