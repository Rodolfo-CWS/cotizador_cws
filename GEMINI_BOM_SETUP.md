# Configuración del Sistema de Análisis BOM con Gemini AI

## Resumen

Se ha implementado exitosamente el sistema de análisis automático de PDFs para extracción de Bills of Materials (BOMs) utilizando Google Gemini AI, siguiendo exactamente la estrategia de 5 pasos solicitada.

## 🎯 Funcionalidades Implementadas

### Proceso de Análisis de 5 Pasos

1. **Análisis por página individual del PDF** - Gemini procesa cada página independientemente
2. **Extracción de tablas de materiales** - Identifica y transcribe tablas con:
   - Item ID
   - Cantidad por item
   - UDM (Unidad de medida)
   - Descripción
   - Dimensiones (separadas por largo y ancho)
   - Espesor
   - Clasificación de item
3. **Repetir proceso en cada página** - Procesa todas las páginas del PDF
4. **Consolidar tablas en tabla master** - Genera subtotales dimensionales de cada item
5. **Clasificar materiales repetidos** - Sumariza grand total final

### Componentes Implementados

- ✅ **Módulo principal**: `gemini_pdf_analyzer.py`
- ✅ **Base de datos BOM**: Esquema completo en Supabase
- ✅ **Manager de BD**: `bom_database_manager.py`
- ✅ **Integración con PDF Manager**: Funcionalidades añadidas a `pdf_manager.py`
- ✅ **API endpoints**: 8 endpoints nuevos en `app.py`
- ✅ **Interface web**: `templates/bom_analysis.html`
- ✅ **Integración UI**: Botones en cotización y home
- ✅ **Configuración**: Variables de entorno en `config.py`
- ✅ **Dependencias**: Actualizadas en `requirements.txt`

## 🚀 Configuración

### 1. Variables de Entorno Requeridas

Agregar al archivo `.env` o variables de entorno:

```env
# Google Gemini AI API Key (REQUERIDA)
GOOGLE_GEMINI_API_KEY=tu_api_key_aqui

# Configuración opcional BOM
BOM_ANALYSIS_ENABLED=True
BOM_MAX_PDF_SIZE_MB=50
BOM_MAX_PAGES=20
GEMINI_MODEL_VISION=gemini-pro-vision
GEMINI_MODEL_TEXT=gemini-pro
```

### 2. Obtener API Key de Google Gemini

1. Ir a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crear un nuevo proyecto o usar uno existente
3. Generar API Key
4. Configurar la variable `GOOGLE_GEMINI_API_KEY`

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Nuevas dependencias añadidas:**
- `google-generativeai>=0.7.0` - Cliente oficial de Gemini AI
- `pdf2image>=1.16.3` - Conversión PDF a imágenes
- `PyPDF2>=3.0.1` - Manipulación básica de PDFs

### 4. Configurar Base de Datos

El sistema creará automáticamente las tablas BOM en Supabase al inicializar, pero puedes ejecutar manualmente:

```sql
-- El archivo bom_database_schema.sql contiene el esquema completo
-- Se ejecuta automáticamente al primer uso
```

## 📊 Uso del Sistema

### Desde la Interfaz Web

1. **Análisis directo desde cotización:**
   - Ir a cualquier cotización existente
   - Hacer clic en el botón morado "Analizar BOM"
   - Confirmar el análisis de 5 pasos
   - Ver resultados detallados

2. **Ver análisis existentes:**
   - Hacer clic en "Ver BOM" desde la cotización
   - O ir directamente a `/bom_analysis`

3. **Desde página principal:**
   - Botón morado "Análisis BOM" en la home page

### API Endpoints

#### `POST /analizar_pdf_bom`
Ejecuta análisis completo de 5 pasos:
```json
{
  "ruta_pdf": "CWS-001.pdf",
  "numero_cotizacion": "CWS-001"
}
```

#### `POST /verificar_pdf_bom`
Verifica si PDF es analizable:
```json
{
  "ruta_pdf": "CWS-001.pdf"
}
```

#### `GET /obtener_analisis_bom/<id>`
Obtiene análisis específico

#### `GET /buscar_analisis_bom?numero_cotizacion=CWS-001`
Busca análisis por cotización

#### `GET /listar_analisis_bom`
Lista análisis recientes

#### `GET /estadisticas_bom`
Estadísticas del sistema

#### `GET /bom_analysis`
Interfaz web completa

#### `DELETE /eliminar_analisis_bom/<id>`
Elimina análisis específico

## 🏗️ Arquitectura del Sistema

### Base de Datos (Supabase PostgreSQL)

**Tablas principales:**
- `bom_analysis` - Información general de cada análisis
- `bom_items` - Items individuales extraídos
- `bom_pages` - Detalle por página
- `bom_consolidated` - Materiales consolidados (Grand Total)
- `bom_classifications` - Agrupación por tipo de material

**Vistas:**
- `v_bom_analysis_summary` - Resumen de análisis
- `v_materials_ranking` - Materiales más utilizados

### Integración con Sistema Existente

- **PDF Manager**: Nuevos métodos para análisis BOM
- **Storage híbrido**: Soporta Supabase Storage, Google Drive y local
- **Arquitectura modular**: No interrumpe funcionalidades existentes

## 🔧 Configuración de Producción

### Variables de Entorno en Render/Heroku

```bash
GOOGLE_GEMINI_API_KEY=tu_api_key_real
BOM_ANALYSIS_ENABLED=True
BOM_MAX_PDF_SIZE_MB=50
BOM_MAX_PAGES=20
```

### Límites Recomendados

- **Tamaño PDF**: Máximo 50MB (configurable)
- **Páginas**: Máximo 20 páginas (configurable) 
- **Rate limiting**: Gemini AI tiene límites por minuto
- **Timeout**: Procesos largos pueden requerir timeout aumentado

## 🧪 Testing

### Verificar Sistema

1. **Conectividad Gemini:**
```bash
curl -X POST http://localhost:5000/verificar_pdf_bom \
  -H "Content-Type: application/json" \
  -d '{"ruta_pdf": "test.pdf"}'
```

2. **Estado del sistema:**
```bash
curl http://localhost:5000/estadisticas_bom
```

3. **Análisis completo:**
```bash
curl -X POST http://localhost:5000/analizar_pdf_bom \
  -H "Content-Type: application/json" \
  -d '{"ruta_pdf": "cotizacion_test.pdf", "numero_cotizacion": "TEST-001"}'
```

## 🚨 Troubleshooting

### Errores Comunes

1. **"Sistema BOM no disponible"**
   - Verificar `GOOGLE_GEMINI_API_KEY` configurada
   - Verificar dependencias instaladas
   - Revisar logs para errores de importación

2. **"PDF no analizable"**
   - Verificar que el PDF existe
   - Verificar tamaño del archivo (límite 50MB)
   - Verificar que el PDF no esté corrupto

3. **"Error de conexión Gemini"**
   - Verificar API Key válida
   - Verificar conexión a internet
   - Verificar límites de rate de la API

4. **"Error de base de datos"**
   - Verificar conexión a Supabase
   - Verificar que las tablas BOM existan
   - Revisar permisos RLS si están habilitados

### Logs de Debug

El sistema genera logs detallados:
- `[GEMINI_ANALYSIS]` - Proceso principal de análisis
- `[BOM_DB]` - Operaciones de base de datos  
- `[BOM]` - Operaciones generales BOM
- `[PASO_X]` - Cada paso del proceso de 5 pasos

## 🔍 Monitoreo

### Métricas Disponibles

- Total de análisis ejecutados
- Tasa de éxito/error
- Tiempo promedio de procesamiento
- Items más encontrados
- Clasificaciones más comunes

### Dashboard

Acceder a `/bom_analysis` para ver:
- Estadísticas en tiempo real
- Análisis recientes  
- Materiales más utilizados
- Estado del sistema

## 🎉 Beneficios Implementados

1. **Automatización completa** - Sin intervención manual
2. **Proceso de 5 pasos** - Exactamente como se solicitó
3. **Consolidación inteligente** - Suma materiales repetidos
4. **Subtotales dimensionales** - Cálculos automáticos de área/volumen  
5. **Clasificación automática** - Agrupa por tipo de material
6. **Interface profesional** - Vista detallada y amigable
7. **API completa** - Integración programática
8. **Storage híbrido** - Compatible con toda la infraestructura existente

## 📈 Próximos Pasos Recomendados

1. **Configurar API Key** en producción
2. **Probar con PDFs reales** de cotizaciones existentes
3. **Ajustar prompts** de Gemini si es necesario para mejor precisión
4. **Configurar alertas** para errores de análisis
5. **Capacitar usuarios** sobre nuevas funcionalidades

---

**Sistema implementado exitosamente** ✅  
**Fecha:** 2025-08-29  
**Versión:** 1.0.0  
**Compatible con:** Arquitectura CWS existente