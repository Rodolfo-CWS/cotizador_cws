# 🏗️ CWS Cotizador - Sistema Profesional de Cotizaciones

**Sistema profesional de cotizaciones con arquitectura híbrida Supabase, almacenamiento permanente en la nube y capacidades offline completas.**

## 🌐 Aplicación en Producción

**URL:** https://cotizador-cws.onrender.com/
**Status:** ✅ **100% Operacional - Sistema Bulletproof con Triple Redundancia + IA**
**Última actualización:** Junio 18, 2026 - IA Text Generation + Minor Edits + PDF Preview

---

## 🎉 ARQUITECTURA BULLETPROOF (Septiembre 2025)

### ✅ Sistema Híbrido Triple-Capa - PRODUCCIÓN LISTA

#### **Capa 1: PostgreSQL Directo** (Más Rápido)
- Conexión directa a Supabase PostgreSQL
- Intenta primero para máxima velocidad
- ✅ Optimizado para operaciones de alta frecuencia

#### **Capa 2: Supabase SDK REST** (Fallback Estable)
- API REST de Supabase cuando PostgreSQL falla
- Maneja automáticamente SSL/autenticación
- ✅ Bypass completo de problemas de SSL/certificados

#### **Capa 3: JSON Local** (Siempre Disponible)
- Garantía de almacenamiento local
- Funciona 100% offline
- ✅ Zero data loss bajo cualquier circunstancia

### 🔄 Auto-Fallback Inteligente
- **Seamless**: Cambio automático entre capas sin intervención del usuario
- **Transparente**: El usuario nunca ve errores técnicos
- **Resiliente**: Sistema garantizado operacional 24/7/365

---

## ✅ FUNCIONALIDADES PRINCIPALES

### 📝 **Sistema de Cotizaciones**
- ✅ Formulario dinámico con items y materiales
- ✅ Cálculos automáticos en tiempo real (subtotales, IVA 16%, total)
- ✅ Sistema de revisiones (R1, R2, R3...) con justificación obligatoria
- ✅ Numeración automática: `CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO`
- ✅ Validación completa client-side y server-side

### 💾 **Sistema de Borradores (Drafts)**
- ✅ **Auto-guardado cada 30 segundos** mientras editas
- ✅ **Guardado automático al cerrar** la ventana del navegador
- ✅ **Badge con contador** en página principal mostrando borradores pendientes
- ✅ **Gestión completa**: Listar, continuar editando, eliminar borradores
- ✅ **Almacenamiento dual**: Supabase + JSON local con fallback automático
- 📖 [Documentación completa del sistema de drafts](README_DRAFTS.md)

### 📄 **Generación Profesional de PDFs**
- ✅ **ReportLab** como motor principal (PDFs de 36KB+)
- ✅ **WeasyPrint** como motor de respaldo
- ✅ Diseño corporativo CWS con logo y colores oficiales
- ✅ Formato profesional: encabezado, tablas estructuradas, resumen financiero
- ✅ Descarga automática con nombres descriptivos
- ✅ **Vista previa interactiva** antes de generar el PDF final
- ✅ **Texto introductorio personalizado** generado por IA o editable manualmente

### 🤖 **Generación de Texto con Inteligencia Artificial**
- ✅ **Claude (Anthropic)** como motor de IA para texto introductorio
- ✅ Texto personalizado basado en cliente, proyecto, items y vendedor
- ✅ **Detección de revisiones**: el prompt incluye cambios vs revisión anterior
- ✅ **Fallback inteligente**: si la IA no está disponible, usa texto guardado en BD
- ✅ **Texto genérico** como último recurso (nunca se pierde el texto)
- ✅ **Persistencia automática**: el texto se guarda en la cotización al generar PDF
- ✅ **Preservación entre revisiones**: el texto IA se hereda a nuevas revisiones
- ✅ **Preservación en ediciones menores**: el texto sobrevive correcciones de typos
- ✅ Configuración simple: solo requiere `ANTHROPIC_API_KEY` en `.env`

### ✏️ **Sistema de Edición Menor**
- ✅ **Corrección de typos y texto** sin generar nueva revisión
- ✅ Preserva el número de cotización y revisión original
- ✅ **Whitelist de campos editables**: atención, contacto, tiempos, comentarios, items
- ✅ **Regeneración automática del PDF** tras guardar la corrección
- ✅ **Auditoría**: registro de cambios en `observaciones.ediciones_menores`
- ✅ **Texto IA preservado**: el texto introductorio no se pierde al corregir

### ☁️ **Almacenamiento Permanente de PDFs**
- ✅ **Supabase Storage** (Primario): CDN global, URLs directas, escalable
- ✅ **Google Drive** (Fallback): Carpetas organizadas (nuevas/antiguas)
- ✅ **Local Storage** (Emergencia): Siempre disponible como último recurso
- ✅ **Smart Routing**: Failover automático entre sistemas

### 🔍 **Búsqueda y Gestión**
- ✅ Búsqueda unificada por cliente, vendedor, proyecto
- ✅ Resultados paginados con información completa
- ✅ Vista detallada (breakdown) de cada cotización
- ✅ Visualización directa de PDFs sin redirects

---

## 🚀 INSTALACIÓN Y CONFIGURACIÓN

### 1. Instalación Rápida (Windows)

```bash
# Instalación automática completa
INSTALAR_AUTOMATICO.bat

# Ejecución rápida
EJECUTAR_RAPIDO.bat
```

### 2. Instalación Manual

```bash
# Clonar repositorio
git clone https://github.com/Rodolfo-CWS/cotizador_cws.git
cd cotizador_cws

# Crear entorno virtual
python -m venv env

# Activar entorno
env\Scripts\activate     # Windows
source env/bin/activate  # Linux/macOS

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno

Crear archivo `.env` con la siguiente configuración:

```bash
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Supabase Database & Storage (Primario - Requerido)
DATABASE_URL=postgresql://postgres.[REF]:[PASS]@aws-1-us-east-2.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key  # REQUERIDO para Storage

# Anthropic API (Claude - IA para generación de texto personalizado)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Google Drive (Fallback - Opcional)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_DRIVE_FOLDER_NUEVAS=folder-id-nuevas
GOOGLE_DRIVE_FOLDER_ANTIGUAS=folder-id-antiguas

# System Configuration
APP_VERSION=2.3.0
DEFAULT_PAGE_SIZE=20
```

### 4. Configurar Supabase Storage

```bash
# Ejecutar script de configuración
python configurar_supabase_storage.py
```

Este script:
- Crea el bucket `cotizaciones-pdfs` si no existe
- Configura políticas de acceso público para lectura
- Verifica permisos y conectividad

### 5. Crear Tabla de Drafts en Supabase

Ejecutar el script SQL en Supabase Dashboard:

```bash
# Ver archivo: create_drafts_table.sql
# O ejecutar desde línea de comandos:
psql $DATABASE_URL -f create_drafts_table.sql
```

---

## 📁 ESTRUCTURA DEL PROYECTO

```
cotizador_cws/
├── app.py                           # Flask app principal con endpoints
├── supabase_manager.py              # Gestor híbrido Supabase (PostgreSQL + SDK REST + JSON)
├── supabase_storage_manager.py      # Integración Supabase Storage
├── unified_storage_manager.py       # Gestor unificado de almacenamiento (Supabase + Drive + Local)
├── pdf_manager.py                   # Generador de PDFs (ReportLab + WeasyPrint)
├── google_drive_client.py           # Cliente Google Drive API (fallback)
├── config.py                        # Configuración basada en entorno
├── Lista de materiales.csv          # Catálogo de materiales
├── cotizaciones_offline.json        # Base de datos JSON (fallback)
├── drafts_offline.json              # Almacenamiento local de borradores
├── requirements.txt                 # Dependencias Python
├── Procfile                         # Configuración Render deployment
├── runtime.txt                      # Versión Python para Render
├── logs/                            # Sistema de logs
│   ├── cotizador_fallos_criticos.log
│   └── fallos_silenciosos_detectados.log
├── static/
│   ├── logo.png                     # Logo CWS
│   └── manifest.json                # PWA manifest
├── templates/
│   ├── home.html                    # Página principal con búsqueda y drafts
│   ├── formulario.html              # Formulario con auto-guardado
│   ├── formato_pdf_cws.html         # Template PDF WeasyPrint
│   └── ver_cotizacion.html          # Visualizador de cotizaciones
├── test_*.py                        # Suite completa de tests
├── create_drafts_table.sql          # Script SQL para tabla drafts
├── CLAUDE.md                        # Documentación técnica completa
├── README_DRAFTS.md                 # Documentación sistema drafts
└── *.bat                            # Scripts de automatización Windows
```

---

## 🎯 USO DEL SISTEMA

### 1. Crear Nueva Cotización

1. **Acceder al formulario**: Click en "Nueva Cotización" desde home
2. **Llenar datos generales**:
   - Vendedor (seleccionar de lista)
   - Cliente, proyecto, atención
   - Número de cotización (generado automáticamente)
3. **Agregar items**:
   - Descripción del item
   - Agregar materiales desde catálogo CSV
   - Cantidades y precios se calculan automáticamente
4. **Definir condiciones comerciales**:
   - Moneda (MXN/USD)
   - Tiempo de entrega
   - Términos de pago
   - Comentarios adicionales
5. **Guardar**: Sistema guarda en Supabase/JSON con triple redundancia
6. **Auto-guardado**: El borrador se guarda automáticamente cada 30 segundos

### 2. Sistema de Borradores (Drafts)

#### **Auto-Guardado Automático**
- Mientras editas, el sistema guarda automáticamente cada 30 segundos
- Al cerrar la ventana, se guarda automáticamente antes de salir
- No necesitas hacer nada, es completamente transparente

#### **Gestionar Borradores**
1. En la página principal, observa el botón naranja **"Borradores"** con badge
2. El badge muestra el número de borradores pendientes (ej: 🔔 3)
3. Click en el botón para abrir el modal de gestión
4. Opciones disponibles:
   - **Continuar editando**: Abre el formulario con todos los datos
   - **Eliminar**: Elimina el borrador (con confirmación)

#### **Recuperar Trabajo Incompleto**
- Los borradores se guardan con: nombre, vendedor, última modificación
- Puedes salir y volver cuando quieras
- Tus datos están seguros en Supabase + JSON local

### 3. Buscar Cotizaciones

1. **Ir a página principal** (`/`)
2. **Usar barra de búsqueda**: Busca por cliente, vendedor, proyecto
3. **Ver resultados paginados**: 20 resultados por página
4. **Acciones disponibles**:
   - Ver desglose completo
   - Descargar PDF
   - Crear nueva revisión (R2, R3...)

### 4. Generar y Visualizar PDFs

1. **Click en "Generar PDF"**: Abre el modal de vista previa
2. **Texto introductorio**: Generado automáticamente por IA (Claude) basado en los datos de la cotización
3. **Editar texto**: Puedes modificar el texto introductorio antes de generar el PDF
4. **Click en "Generar PDF"**: El PDF se descarga y se abre en nueva pestaña
5. **Triple almacenamiento**: PDF guardado en Supabase Storage + Google Drive + Local
6. **Texto IA persistido**: El texto se guarda en la cotización para futuras referencias

### 5. Sistema de Revisiones

1. **Crear revisión**: Desde cotización existente, click en "Nueva Revisión"
2. **Justificación obligatoria**: Para R2 y superiores, se requiere justificación
3. **Numeración automática**: Sistema incrementa R1 → R2 → R3...
4. **Datos preservados**: La revisión original se mantiene intacta
5. **Texto IA heredado**: El texto introductorio se preserva de la revisión anterior

### 6. Edición Menor (Corrección sin Nueva Revisión)

1. **Acceder**: Desde la vista de cotización, click en "Corregir typos o texto"
2. **Solo campos de texto**: Edita atención, contacto, tiempos, comentarios e items
3. **Guardar**: Click en "Guardar Corrección" — no genera nueva revisión
4. **PDF regenerado**: El PDF se regenera automáticamente con los cambios
5. **Texto IA preservado**: El texto introductorio no se pierde

---

## 🌐 API ENDPOINTS

### **Rutas Principales**

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET/POST | Página principal con búsqueda |
| `/formulario` | GET/POST | Formulario de cotización con auto-guardado |
| `/formulario?draft=ID` | GET | Cargar borrador específico en formulario |
| `/formulario?revision=ID` | GET | Crear nueva revisión desde cotización existente |
| `/formulario?edicion_menor=ID` | GET | Corregir cotización sin generar nueva revisión |
| `/generar_pdf` | POST | Generar PDF con texto personalizado y triple almacenamiento |
| `/pdf/<id>` | GET | Servir PDF directamente (sin redirects) |
| `/ver/<id>` | GET | Ver cotización completa (breakdown) |
| `/desglose/<id>` | GET | Desglose detallado de cotización |
| `/buscar` | POST | Búsqueda unificada con paginación |
| `/info` | GET | Información del sistema y estado |
| `/stats` | GET | Estadísticas de base de datos |

### **API IA y Edición Menor**

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/api/generar-texto-ia` | POST | Genera texto introductorio con Claude AI |
| `/api/cotizacion/<id>/edicion-menor` | PATCH | Aplica corrección sin nueva revisión |

### **API Drafts (Sistema de Borradores)**

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/api/draft/save` | POST | Guardar/actualizar borrador |
| `/api/draft/list` | GET | Listar borradores (filtrable por vendedor) |
| `/api/draft/load/<id>` | GET | Cargar borrador específico |
| `/api/draft/delete/<id>` | DELETE | Eliminar borrador |

**Ejemplo de uso:**

```bash
# Guardar borrador
curl -X POST https://cotizador-cws.onrender.com/api/draft/save \
  -H "Content-Type: application/json" \
  -d '{
    "vendedor": "RCWS",
    "datos": {
      "datosGenerales": {...},
      "items": [...],
      "condiciones": {...}
    }
  }'

# Listar borradores
curl https://cotizador-cws.onrender.com/api/draft/list?vendedor=RCWS

# Cargar borrador
curl https://cotizador-cws.onrender.com/api/draft/load/draft_1234567890

# Eliminar borrador
curl -X DELETE https://cotizador-cws.onrender.com/api/draft/delete/draft_1234567890
```

---

## 🧪 TESTING Y VALIDACIÓN

### Tests Completos del Sistema

```bash
# Test completo de Supabase (Database + Storage)
python test_simple_supabase.py

# Test específico de Supabase Storage
python test_supabase_storage.py

# Test de generación de PDFs
python test_pdf_completo.py

# Test de numeración automática
python test_numero_automatico.py

# Test de servidor local
python test_servidor.py

# Verificar librerías PDF
python -c "import reportlab; print('ReportLab: OK')"
python -c "import weasyprint; print('WeasyPrint: OK')"
```

### Verificación de Estado del Sistema

```bash
# Estado general (Python)
python -c "
from supabase_manager import SupabaseManager
from supabase_storage_manager import SupabaseStorageManager
db = SupabaseManager()
storage = SupabaseStorageManager()
print(f'Database: {\"ONLINE\" if not db.modo_offline else \"OFFLINE (JSON fallback)\"}')
print(f'Storage: {\"OK\" if storage.storage_available else \"OFFLINE (fallback)\"}')
"

# Estado desde producción (curl)
curl https://cotizador-cws.onrender.com/info
curl https://cotizador-cws.onrender.com/stats
```

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### ❌ **Problema: Aplicación no inicia en producción**

**Síntomas:**
- Render se detiene en "Running 'gunicorn app:app'"
- Errores Python sobre variables no definidas
- Cotizaciones se guardan localmente pero no en Supabase

**Diagnóstico:**
```bash
# Revisar logs de Render para errores de Python
# Buscar patrones como: UnboundLocalError, NameError
```

**Solución:**
1. ✅ **Resuelto en Sept 8, 2025**: Variable `estado_cambio` scope error corregido
2. Verificar que todas las variables de entorno estén configuradas en Render
3. Revisar `supabase_manager.py` para errores de alcance de variables

---

### ❌ **Problema: PDFs no se visualizan**

**Síntomas:**
- "URL del PDF no disponible"
- Redirect loops o páginas en blanco

**Solución:**
1. ✅ **Resuelto en Aug 26, 2025**: Sistema de serving directo implementado
2. Verificar `SUPABASE_SERVICE_KEY` configurado en Render
3. Ejecutar: `python configurar_supabase_storage.py`
4. Confirmar bucket `cotizaciones-pdfs` existe y tiene políticas públicas

---

### ❌ **Problema: Búsqueda devuelve resultados vacíos**

**Síntomas:**
- Búsqueda no encuentra cotizaciones existentes
- "No se encontraron PDFs"

**Diagnóstico:**
```bash
# Test búsqueda local
python -c "
from supabase_manager import SupabaseManager
db = SupabaseManager()
resultados = db.buscar_cotizaciones('', pagina=1, por_pagina=20)
print(f'Encontradas: {resultados[\"total\"]} cotizaciones')
"
```

**Solución:**
1. ✅ **Resuelto en Aug 20, 2025**: Búsqueda unificada implementada
2. Verificar logs de Render para errores de conexión Supabase
3. Sistema debe caer automáticamente a JSON si Supabase falla

---

### ❌ **Problema: Auto-guardado de drafts no funciona**

**Síntomas:**
- No aparece notificación "Borrador guardado"
- Badge no muestra contador de drafts
- Drafts no aparecen en modal

**Diagnóstico:**
```bash
# Verificar consola del navegador (F12)
# Buscar mensajes: "[DRAFT] Inicializando sistema..."

# Test API drafts
curl https://cotizador-cws.onrender.com/api/draft/list
```

**Solución:**
1. Verificar que tabla `drafts` existe en Supabase
2. Ejecutar `create_drafts_table.sql` si es necesario
3. Confirmar que hay datos en formulario (vendedor o cliente)
4. Verificar `drafts_offline.json` se crea como fallback

---

### ❌ **Problema: Cotizaciones USD muestran MXN**

**Síntomas:**
- PDFs de cotizaciones USD muestran moneda MXN
- Términos comerciales aparecen como "A definir"

**Solución:**
1. ✅ **Resuelto en Sept 8, 2025**: Campo `condiciones` agregado a SDK REST save
2. Verificar que formulario incluye sección de condiciones comerciales
3. Confirmar que PDFs se regeneran después del fix

---

## 📊 PROBLEMAS RESUELTOS (Historial)

### ✅ **PDF null + Texto IA perdido en edición menor** (Junio 18, 2026)
- **Problema**: Tras edición menor, PDF no se encontraba (`/pdf/null`) y texto IA se perdía
- **Solución**: 
  - Número de cotización guardado antes de cerrar modal de preview
  - PDF servido directamente como blob (elimina segunda request)
  - Texto IA persistido en BD y preservado en ediciones menores
  - Salvaguarda de merge de condiciones en edición menor
- **Impacto**: Robustez completa en flujo de edición y generación de PDFs
- **Archivos**: `app.py`, `pdf_manager.py`, `supabase_manager.py`, `templates/formulario.html`

### ✅ **IA Text Generation + Preview Modal** (Junio 17, 2026)
- **Problema**: Texto introductorio de PDFs era siempre genérico
- **Solución**: Integración con Claude API (Anthropic) para generar texto personalizado basado en cliente, proyecto e items. Modal de vista previa permite editar el texto antes de generar el PDF.
- **Impacto**: PDFs profesionales con texto introductorio personalizado
- **Archivos**: `app.py`, `templates/formulario.html`, `cotizador/pdf_generator.py`

### ✅ **Persistencia de texto IA entre revisiones** (Junio 17, 2026)
- **Problema**: Texto IA se perdía al crear nuevas revisiones o editar
- **Solución**: Texto guardado en `datosGenerales.textoIntroductorio` al generar PDF, heredado en nuevas revisiones via `preparar_datos_nueva_revision`, y preservado en ediciones menores via PATCH.
- **Impacto**: El texto IA sobrevive a todo el ciclo de vida de la cotización
- **Archivos**: `app.py`, `supabase_manager.py`, `templates/formulario.html`

### ✅ **UnboundLocalError Deployment Crash** (Sept 8, 2025)
- **Problema**: App no iniciaba por error de alcance de variable `estado_cambio`
- **Solución**: Variable movida a scope del exception handler
- **Impacto**: Sistema completamente funcional en producción
- **Archivo**: `supabase_manager.py:168`

### ✅ **Missing Condiciones in USD Quotes** (Sept 8, 2025)
- **Problema**: Cotizaciones USD mostraban MXN y términos genéricos
- **Solución**: Campo `condiciones` agregado a payload de SDK REST
- **Impacto**: Integridad completa de datos comerciales
- **Archivo**: `supabase_manager.py:627, 653`

### ✅ **PDF Visualization Issues** (Aug 26, 2025)
- **Problema**: Redirects fallaban, URLs vacías
- **Solución**: Serving directo de PDFs, actualización Supabase client
- **Impacto**: Visualización perfecta de PDFs
- **Archivos**: `app.py`, `supabase_storage_manager.py`

### ✅ **Frontend-Backend Disconnection** (Aug 20, 2025)
- **Problema**: Búsqueda y breakdown no funcionaban en producción
- **Solución**: Mapeo de datos estandarizado, búsqueda unificada
- **Impacto**: Sistema end-to-end completamente funcional
- **Archivos**: `app.py`, `supabase_manager.py`

### ✅ **Cloudinary to Supabase Storage Migration** (Aug 25, 2025)
- **Migración**: Eliminación completa de Cloudinary
- **Beneficio**: Plataforma unificada Supabase, menores costos
- **Archivos**: Todos los archivos de storage actualizados

---

## 🎉 CARACTERÍSTICAS DESTACADAS

### ✨ Sistema Bulletproof
- ✅ **Zero Downtime**: Triple capa garantiza 100% disponibilidad
- ✅ **Auto-Fallback**: Cambio automático entre PostgreSQL → SDK REST → JSON
- ✅ **Offline-Ready**: Funciona perfectamente sin internet
- ✅ **Zero Data Loss**: Triple redundancia en almacenamiento

### ✨ Auto-Guardado Inteligente
- ✅ **Cada 30 segundos**: Guardado transparente mientras trabajas
- ✅ **Al cerrar ventana**: Usando `sendBeacon` para guardar antes de salir
- ✅ **Detección de cambios**: Solo guarda si hay modificaciones
- ✅ **Dual storage**: Supabase + JSON local automático

### ✨ PDFs Profesionales
- ✅ **Diseño corporativo CWS**: Logo, colores, estructura oficial
- ✅ **36KB+ tamaño**: Documentos completos y profesionales
- ✅ **Triple almacenamiento**: Supabase Storage + Google Drive + Local
- ✅ **URLs directas**: Acceso inmediato sin redirects

### ✨ Numeración Automática
- ✅ **Formato**: `CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO`
- ✅ **Sequential por vendedor**: Contadores independientes
- ✅ **Revisiones**: R1 → R2 → R3... automático con justificación

---

## 🚀 DEPLOYMENT A PRODUCCIÓN (Render)

### 1. Preparación del Repositorio

```bash
# Commit cambios
git add .
git commit -m "Descripción de cambios"

# Push a GitHub
git push origin main
```

### 2. Configuración en Render

**Variables de Entorno Requeridas:**

```bash
# Supabase (CRÍTICO)
DATABASE_URL=postgresql://postgres.[REF]:[PASS]@aws-1-us-east-2.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key  # REQUERIDO

# Flask
FLASK_ENV=production
FLASK_DEBUG=False

# Google Drive (Opcional - Fallback)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_DRIVE_FOLDER_NUEVAS=folder-id
GOOGLE_DRIVE_FOLDER_ANTIGUAS=folder-id

# Anthropic API (IA para texto personalizado)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# App
APP_VERSION=2.3.0
DEFAULT_PAGE_SIZE=20
```

### 3. Verificación Post-Deployment

```bash
# 1. Estado general
curl https://cotizador-cws.onrender.com/info

# 2. Test de búsqueda
curl -X POST https://cotizador-cws.onrender.com/buscar \
  -H "Content-Type: application/json" \
  -d '{"query":"","pagina":1,"por_pagina":5}'

# 3. Test de drafts
curl https://cotizador-cws.onrender.com/api/draft/list

# 4. Verificar PDF serving
curl -I https://cotizador-cws.onrender.com/pdf/TEST-CWS-TEST-001-R1-TEST
```

### 4. Monitoreo Continuo

- **Logs de Render**: Dashboard > Logs (streaming en tiempo real)
- **Estado del sistema**: Endpoint `/info` para verificar componentes
- **Database status**: Revisar logs para confirmación de capa activa (PostgreSQL/SDK/JSON)

---

## 📖 DOCUMENTACIÓN ADICIONAL

- **[CLAUDE.md](CLAUDE.md)**: Documentación técnica completa del sistema
- **[README_DRAFTS.md](README_DRAFTS.md)**: Documentación detallada del sistema de borradores
- **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)**: Guía completa de deployment a Render
- **[INSTRUCCIONES_PDF.md](INSTRUCCIONES_PDF.md)**: Configuración de generación de PDFs

---

## 💡 NOTAS IMPORTANTES

### ⚠️ Para Desarrolladores
- **SIEMPRE ejecutar tests** antes de hacer deploy: `python test_simple_supabase.py`
- **Verificar SUPABASE_SERVICE_KEY** configurado en producción para Storage
- **Mantener fallbacks**: Nunca eliminar sistemas de respaldo (JSON, Google Drive)
- **Logs estructurados**: Revisar `/logs/` para diagnósticos detallados

### ⚠️ Para Producción
- **Triple redundancia**: PDFs garantizados en 3 ubicaciones
- **Modo offline**: Sistema funciona sin conexión a internet
- **Auto-recovery**: Recuperación automática cuando servicios vuelven online
- **Zero data loss**: Datos seguros incluso con fallos de infraestructura

### ⚠️ Compatibilidad
- **Python**: 3.11.5 o superior
- **Navegadores**: Chrome, Firefox, Safari, Edge (últimas versiones)
- **Responsive**: Optimizado para desktop, tablet y móvil
- **PWA**: Instalable como aplicación de escritorio

---

## 📞 SOPORTE Y CONTACTO

### Diagnóstico Rápido
```bash
# Estado completo del sistema
python -c "
from supabase_manager import SupabaseManager
from supabase_storage_manager import SupabaseStorageManager
import json

db = SupabaseManager()
storage = SupabaseStorageManager()

status = {
    'database_mode': 'Online (Supabase)' if not db.modo_offline else 'Offline (JSON)',
    'storage_available': storage.storage_available,
    'drafts_count': len(db.listar_drafts().get('drafts', [])),
    'total_quotes': db.obtener_estadisticas().get('total', 0)
}

print(json.dumps(status, indent=2))
"
```

### Recursos de Ayuda
- **Documentación técnica**: Ver `CLAUDE.md` para detalles completos
- **Tests de diagnóstico**: Usar archivos `test_*.py` para verificar componentes
- **Logs del sistema**: Revisar `/logs/` para errores y warnings
- **GitHub Issues**: Reportar problemas en el repositorio

---

## 📈 ESTADÍSTICAS DEL PROYECTO

- **Líneas de código**: ~15,000+ líneas
- **Archivos Python**: 25+ módulos
- **Templates HTML**: 4 plantillas principales
- **Tests automatizados**: 10+ suites de prueba
- **APIs**: 15+ endpoints REST
- **Tiempo de desarrollo**: 6+ meses (con mejoras continuas)
- **Arquitectura**: Triple-layer hybrid bulletproof system

---

## 🏆 LOGROS TÉCNICOS

✅ **Zero Downtime Architecture**: Sistema garantizado 24/7
✅ **Triple-Layer Fallback**: PostgreSQL → SDK REST → JSON
✅ **Auto-Save System**: Borradores cada 30 segundos
✅ **Professional PDFs**: Diseño corporativo oficial CWS
✅ **AI-Powered Text**: Claude genera texto introductorio personalizado
✅ **PDF Preview Modal**: Editar texto IA antes de generar PDF
✅ **Minor Edits**: Correcciones sin nueva revisión, con preservación de IA
✅ **Unified Storage**: Supabase Storage + Google Drive + Local
✅ **Offline-First**: 100% funcional sin internet
✅ **Smart Routing**: Failover automático inteligente
✅ **Complete Testing**: Suite comprehensiva de tests

---

**Última actualización:** Junio 18, 2026
**Versión:** 2.3.0
**Proyecto:** CWS Cotizador - Sistema Profesional de Cotizaciones
**Arquitectura:** Supabase Hybrid Triple-Layer + IA Anthropic Claude

---

**Desarrollado con ❤️ para CWS Company**
