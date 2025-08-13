# 🔍 GUÍA COMPLETA DE DEBUGGING - Sistema CWS Cotizaciones

## 🚨 PROBLEMA IDENTIFICADO

**Cotización "MONGO-CWS-CM-001-R1-BOBOX":**
- ❌ **Búsqueda por nombre**: No aparece resultado
- ✅ **Búsqueda por vendedor**: Aparece pero PDF incorrecto
- 🔄 **Botones inconsistentes**: PDF/desglose diferentes según método

## 🎯 CAUSA RAÍZ CONFIRMADA

### **Sistema en Modo Offline**
- 🔌 **MongoDB Atlas**: Desconectado
- 🌐 **Google Drive**: No responde correctamente
- 📂 **Datos locales**: Usando archivo de respaldo

### **Flujos de Búsqueda Inconsistentes**
1. **Búsqueda por nombre** → `/buscar_pdfs` → Falla → Sin fallback
2. **Búsqueda por vendedor** → `/buscar_pdfs` → Falla → Fallback automático → `/buscar` → Éxito

## 📋 PASOS PARA REPRODUCIR

### **Escenario 1: Búsqueda por Nombre (Problemática)**
```
1. Ir a: https://cotizador-cws.onrender.com
2. Buscar: "MONGO-CWS-CM-001-R1-BOBOX"
3. Observar: "No se encontraron PDFs"
4. Abrir DevTools → Console
5. Verificar: Solo se ejecuta /buscar_pdfs, NO hay fallback
```

### **Escenario 2: Búsqueda por Vendedor (Funciona)**
```
1. Ir a: https://cotizador-cws.onrender.com
2. Buscar: "Carlos Martinez" o "CM"
3. Observar: Aparecen 8 resultados incluyendo MONGO-CWS-CM-001-R1-BOBOX
4. Abrir DevTools → Console
5. Verificar: Se ejecuta /buscar_pdfs → Falla → Fallback a /buscar → Éxito
```

## 🛠️ DEBUGGING PASO A PASO

### **1. Verificar Modo del Sistema**
```bash
# Ejecutar en local:
python "C:\Users\SDS\cotizador_cws\debug_cotizacion_especifica.py"

# Resultado esperado:
# Modo: offline (confirma el problema)
```

### **2. Inspeccionar en Browser DevTools**
```javascript
// En console del navegador:

// Test búsqueda PDFs
fetch('/buscar_pdfs', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: 'MONGO-CWS-CM-001-R1-BOBOX'})
}).then(r => r.json()).then(console.log);

// Test búsqueda cotizaciones
fetch('/buscar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: 'MONGO-CWS-CM-001-R1-BOBOX'})
}).then(r => r.json()).then(console.log);
```

### **3. Analizar Respuestas**
- **PDFs**: `{total: 0, resultados: [], modo: "offline"}`
- **Cotizaciones**: `{total: 2, resultados: [...], modo: "offline"}`

### **4. Verificar Renderizado de Botones**
```javascript
// Inspeccionar variables en frontend:
console.log('esCotizacion:', pdf._id && !pdf.numero_cotizacion);
console.log('tieneDesglose:', pdf.tiene_desglose);
```

## 🔧 SOLUCIONES IMPLEMENTADAS

### **Solución 1: Fallback Automático Mejorado**
- ✅ **Archivo**: `solucion_fallback_mejorado.js`
- 🎯 **Propósito**: Hacer fallback automático cuando `/buscar_pdfs` no encuentra resultados
- 📝 **Cambios**:
  - Fallback automático en todas las búsquedas
  - Mejor detección de origen de datos
  - Botones consistentes para cotizaciones

### **Solución 2: Verificador de Conectividad**
- ✅ **Archivo**: `verificar_conectividad.py`
- 🎯 **Propósito**: Diagnosticar problemas de MongoDB Atlas y Google Drive
- 📊 **Información**: Estado de servicios, variables de entorno, configuración

## 🚀 IMPLEMENTACIÓN DE SOLUCIONES

### **Paso 1: Aplicar Fallback Mejorado**
```bash
# 1. Backup del archivo actual
cp templates/home.html templates/home.html.backup

# 2. Aplicar cambios del archivo solucion_fallback_mejorado.js
# Reemplazar las funciones buscar() y mostrarResultados() en home.html
```

### **Paso 2: Verificar Conectividad**
```bash
# Ejecutar diagnóstico
python "C:\Users\SDS\cotizador_cws\verificar_conectividad.py"
```

### **Paso 3: Corregir Variables de Entorno en Render**
```
1. Ir a: https://dashboard.render.com
2. Seleccionar: cotizador-cws
3. Environment → Edit
4. Verificar:
   - MONGODB_URI (debe estar completa)
   - GOOGLE_APPLICATION_CREDENTIALS_JSON
5. Deploy manual si es necesario
```

## 📊 MONITOREO POST-IMPLEMENTACIÓN

### **Tests de Verificación**
```bash
# 1. Test automatizado
python debug_cotizacion_especifica.py

# 2. Verificar que todas las búsquedas encuentren la cotización:
# - Por nombre: MONGO-CWS-CM-001-R1-BOBOX
# - Por vendedor: Carlos Martinez
# - Por vendedor corto: CM
```

### **Indicadores de Éxito**
- ✅ **Búsqueda por nombre**: Encuentra la cotización
- ✅ **Botones consistentes**: PDF y desglose disponibles en ambos métodos
- ✅ **Modo online**: Sistema conectado a MongoDB Atlas
- ✅ **Sin errores JS**: Console limpia en DevTools

## 🐛 DEBUGGING AVANZADO

### **Logs del Servidor**
```
1. Render Dashboard → cotizador-cws → Logs
2. Buscar errores relacionados con:
   - "MongoDB connection"
   - "Google Drive API"
   - "MONGO-CWS-CM-001-R1-BOBOX"
```

### **Test de Endpoints Directos**
```bash
# Curl tests
curl -X POST https://cotizador-cws.onrender.com/buscar_pdfs \
     -H "Content-Type: application/json" \
     -d '{"query":"MONGO-CWS-CM-001-R1-BOBOX"}'

curl -X POST https://cotizador-cws.onrender.com/buscar \
     -H "Content-Type: application/json" \
     -d '{"query":"MONGO-CWS-CM-001-R1-BOBOX"}'
```

## ⚡ SOLUCIÓN RÁPIDA (TEMPORAL)

Si necesitas una solución inmediata, implementa el fallback mejorado:

```javascript
// Agregar al final de la función buscar() en home.html:
.then(data => {
    // Si no hay resultados, hacer fallback automático
    if (!data.resultados || data.resultados.length === 0) {
        return fetch('/buscar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query: query})
        }).then(r => r.json());
    }
    return data;
})
```

Esta solución temporal asegura que todas las búsquedas encuentren los resultados disponibles mientras se corrige la conectividad de los servicios principales.