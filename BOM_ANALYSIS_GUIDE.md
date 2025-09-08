# 📋 Guía de Uso - Sistema de Análisis BOM Mejorado

## 🔧 Mejoras Implementadas

### ❌ **Problema Anterior**
- El análisis fallaba con planos de ingeniería
- Solo detectaba "steel required" genérico
- No extraía información específica de materiales

### ✅ **Solución Implementada**

#### **1. Prompt Especializado para Planos de Ingeniería**
- Busca tablas de materiales Y anotaciones en dibujos  
- Reconoce perfiles estructurales (IPR, PTR, canales)
- Extrae dimensiones en formato pies/pulgadas
- Identifica placas, láminas y conexiones

#### **2. Manejo Robusto de Errores**
- Retry automático en fallos
- Manejo específico de límites de cuota Gemini
- Mejor procesamiento de respuestas JSON
- Logs detallados para debugging

#### **3. Extracción Inteligente**
- Convierte medidas imperiales a métricas
- Procesa perfiles como "IPR 6x4x3/8 @ 12'-0 LONG"
- Extrae información tanto de tablas como de anotaciones
- Valida datos antes de guardar

## 🚀 Cómo Usar el Sistema

### **Desde la Interfaz Web**

1. **Ve a cualquier cotización**
2. **Haz clic en "Analizar BOM"** (botón morado)
3. **Confirma el análisis** - El sistema mostrará:
   - PDF: X páginas
   - Proceso de 5 pasos automático
4. **Espera el resultado** (puede tomar 1-2 minutos)
5. **Ver resultados detallados** en nueva pestaña

### **Desde API**

```bash
curl -X POST http://localhost:5000/analizar_pdf_bom \
  -H "Content-Type: application/json" \
  -d '{
    "ruta_pdf": "mi_plano.pdf",
    "numero_cotizacion": "CWS-001"
  }'
```

## 🎯 Qué Detecta el Sistema Mejorado

### **Información de Tablas de Materiales:**
- ✅ Perfiles estructurales (IPR, PTR, HSS, etc.)
- ✅ Placas y láminas con espesores
- ✅ Pernos, soldaduras, conexiones
- ✅ Cantidades exactas
- ✅ Dimensiones en pies/pulgadas

### **Anotaciones en Dibujos:**
- ✅ "4 IPR 6x4x3/8 @ 12'-0 LONG"
- ✅ "PL 1/2 x 8 x 10"
- ✅ "HSS 4x4x1/4"
- ✅ Medidas dimensionales

### **Conversiones Automáticas:**
- 🔄 Pies/pulgadas → milímetros
- 🔄 Fracciones → decimales
- 🔄 Unidades imperiales → métricas

## ⚡ Proceso de 5 Pasos

### **Paso 1: Análisis por Página**
- Convierte cada página PDF a imagen
- Gemini analiza con prompt especializado

### **Paso 2: Extracción de Tablas** 
- Identifica tablas de materiales
- Transcribe perfiles y especificaciones
- Extrae: Item ID, cantidad, UDM, descripción, dimensiones

### **Paso 3: Procesamiento Completo**
- Repite análisis en todas las páginas
- Consolida información por página

### **Paso 4: Tabla Master**
- Consolida items similares
- Calcula subtotales dimensionales
- Genera área y volumen totales

### **Paso 5: Grand Total**
- Identifica materiales repetidos
- Clasifica por tipo de material
- Suma cantidades finales

## 🚨 Manejo de Errores Comunes

### **Error: "Límite de cuota alcanzado"**
**Causa:** Plan gratuito de Gemini tiene límites:
- 15 requests/minuto
- 1,500 requests/día

**Solución:**
1. Espera unos minutos
2. Usa modelo `gemini-1.5-flash` (más eficiente)
3. Considera plan pagado para uso intensivo

### **Error: "PDF no encontrado"**
**Causa:** El PDF no está en las ubicaciones esperadas

**Solución:**
1. Verifica que el PDF existe
2. Usa ruta completa al archivo
3. Asegúrate que está en carpetas configuradas

### **Error: "Sin materiales detectados"**
**Causa:** PDF no contiene información estructural clara

**Solución:**
1. Verifica que el PDF tiene tablas de materiales
2. Asegúrate que es un plano técnico/estructural
3. Verifica calidad de imagen del PDF

## 🔍 Interpretación de Resultados

### **Interfaz BOM Analysis**

La página `/bom_analysis` muestra:

**📊 Estadísticas:**
- Total items encontrados
- Items únicos vs consolidados
- Páginas con tablas

**📋 Materiales Consolidados:**
- Lista completa de materiales
- Cantidades totales
- Dimensiones y áreas
- Repeticiones por página

**🏷️ Por Clasificación:**
- Perfiles estructurales
- Placas y láminas
- Conexiones
- Sin clasificar

**📄 Por Página:**
- Qué se encontró en cada página
- Estado del análisis
- Errores si los hay

## 🎛️ Configuración Avanzada

### **Variables de Entorno**

```env
# REQUERIDA: API Key de Gemini
GOOGLE_GEMINI_API_KEY=tu_api_key_aqui

# Límites de procesamiento
BOM_MAX_PDF_SIZE_MB=50
BOM_MAX_PAGES=20

# Modelos Gemini (opcional)
GEMINI_MODEL_VISION=gemini-1.5-flash-latest
GEMINI_MODEL_TEXT=gemini-1.5-flash-latest
```

### **Mejores Prácticas**

1. **PDFs de calidad:** Usa archivos con texto legible
2. **Tamaño razonable:** Máximo 50MB, 20 páginas
3. **Contenido estructural:** Funciona mejor con planos técnicos
4. **Paciencia:** El análisis puede tomar 1-3 minutos por PDF

## 🔄 Próximas Mejoras Sugeridas

1. **Caché de resultados** - Evitar re-análisis
2. **Análisis por lotes** - Múltiples PDFs simultáneos  
3. **Export a Excel** - Tablas BOM descargables
4. **Templates personalizados** - Formatos específicos por cliente
5. **Machine Learning** - Mejor reconocimiento con entrenamiento

## 📞 Soporte

Si el análisis sigue fallando:

1. **Revisa logs** en la consola del navegador
2. **Verifica API key** de Gemini válida
3. **Prueba con PDF más simple** primero
4. **Revisa límites de cuota** en Google AI Studio

---

**Sistema funcionando correctamente** ✅  
**Fecha actualización:** 2025-08-29  
**Versión:** 2.0 - Especializado para planos de ingeniería