# 🚂 **DEPLOY DIRECTO CON RAILWAY CLI**

## ⚡ **MÉTODO ALTERNATIVO (MÁS DIRECTO)**

Si no aparece tu repositorio en Railway, usa este método:

### **1️⃣ Instalar Railway CLI**
```bash
# Opción A: Con npm (si tienes Node.js)
npm install -g @railway/cli

# Opción B: Descargar desde Railway
# Ve a: https://railway.app/cli
```

### **2️⃣ Login en Railway**
```bash
cd "C:\Users\SDS\cotizador_cws"
railway login
```
Se abrirá tu navegador para autorizar.

### **3️⃣ Inicializar proyecto**
```bash
railway init
```
- Te preguntará el nombre: `cotizador-cws`
- Selecciona "Empty project"

### **4️⃣ Deploy directo**
```bash
railway up
```
¡Eso es todo! Railway detecta Python automáticamente.

### **5️⃣ Configurar variables**
```bash
railway variables set SECRET_KEY=cotizador-cws-super-secreto-2024
railway variables set FLASK_DEBUG=False
railway variables set APP_NAME="CWS Cotizaciones"
```

### **6️⃣ Ver tu aplicación**
```bash
railway open
```
Te abrirá tu cotizador en el navegador.

---

## 🎉 **RESULTADO**
URL como: `https://cotizador-cws-production.railway.app`