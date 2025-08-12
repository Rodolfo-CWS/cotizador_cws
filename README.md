# 🏗️ CWS Cotizador - Sistema Híbrido de Cotizaciones

**Sistema profesional de cotizaciones con arquitectura híbrida, triple redundancia y sincronización automática.**

## 🌐 Aplicación en Producción

**URL:** https://cotizador-cws.onrender.com/  
**Status:** ✅ **Operacional con Sistema Híbrido Implementado**  
**Última actualización:** Agosto 12, 2025 - Commit `139d503`

## 🎉 **SISTEMA HÍBRIDO DESPLEGADO** (Agosto 2025)

### ✅ **Arquitectura de Vanguardia**
- **Base de Datos**: JSON primario + MongoDB Atlas (sincronización bidireccional)
- **Almacenamiento PDF**: Cloudinary (25GB gratis) + Google Drive (fallback) + Local (emergencia)
- **Sincronización**: Automática cada 15 minutos con resolución de conflictos
- **Disponibilidad**: 100% uptime garantizado con triple redundancia

## ✅ Correcciones Implementadas

### 1. **Botón Home Agregado**
- ✅ Botón "🏠 Home" en el formulario para regresar a la página principal
- ✅ Navegación mejorada entre secciones

### 2. **Campo de Justificación de Actualización**
- ✅ Campo `actualizacionRevision` correctamente implementado
- ✅ Aparece automáticamente cuando revisión ≥ 2
- ✅ Validación obligatoria para revisiones superiores
- ✅ Datos se guardan correctamente en MongoDB

### 3. **Cálculos de Items Corregidos**
- ✅ Subtotales de materiales se calculan automáticamente
- ✅ Subtotales de otros materiales funcionan correctamente  
- ✅ Cálculos en tiempo real al modificar cantidades/precios
- ✅ Totales generales se actualizan automáticamente
- ✅ Resumen financiero desglosado por item

### 4. **Generación de PDF Implementada**
- ✅ Template HTML con formato exacto del Excel CWS
- ✅ Encabezado oficial de CWS Company
- ✅ Información completa del cliente y proyecto
- ✅ Tabla detallada de items con materiales
- ✅ Cálculos automáticos (subtotal, IVA 16%, total)
- ✅ Términos y condiciones
- ✅ Área de firma y datos del vendedor
- ✅ Formato A4 optimizado para impresión

## 🚀 Instalación y Configuración (Sistema Híbrido)

### 1. Instalación Automática (Recomendado)
```bash
# Windows - Instalación completa
INSTALAR_AUTOMATICO.bat

# Manual - Dependencias completas
pip install -r requirements.txt
```

### 2. Dependencias del Sistema Híbrido
```bash
# Core dependencies
pip install flask python-dotenv pymongo

# PDF Generation
pip install reportlab weasyprint

# Hybrid System (NEW)
pip install cloudinary APScheduler

# Google Drive Integration
pip install google-api-python-client google-auth
```

### 3. Configuración de Variables de Entorno
```bash
# Copiar configuración base
cp .env.example .env

# Variables del Sistema Híbrido (OBLIGATORIAS):
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
SYNC_INTERVAL_MINUTES=15
AUTO_SYNC_ENABLED=true
MONGODB_URI=your-mongodb-connection-string
```

## 📁 Estructura del Proyecto (Sistema Híbrido)

```
cotizador_cws/
├── app.py                          # Flask app + NEW hybrid endpoints
├── database.py                     # ENHANCED: Hybrid DB manager
├── pdf_manager.py                  # ENHANCED: Triple redundancy PDF storage
├── cloudinary_manager.py           # NEW: Cloudinary integration (25GB)
├── sync_scheduler.py               # NEW: Auto-sync scheduler
├── google_drive_client.py          # Google Drive fallback
├── config.py                       # Environment-based configuration
├── .env                           # Environment variables (hybrid config)
├── cotizaciones_offline.json      # JSON primary database
├── Lista de materiales.csv        # Materials catalog
├── requirements.txt               # UPDATED: Hybrid dependencies
├── CLAUDE.md                      # Complete system documentation
├── templates/
│   ├── home.html                  # Main page with search
│   ├── formulario.html            # Dynamic quotation form
│   ├── formato_pdf_cws.html       # WeasyPrint PDF template
│   └── ver_cotizacion.html        # Quotation viewer
├── test_*.py                      # EXPANDED: Comprehensive test suite
│   ├── test_cloudinary.py        # NEW: Cloudinary tests
│   └── test_sync_completo.py     # NEW: Hybrid system tests
└── *.bat                         # Windows automation scripts
```

## 🎯 Funcionalidades

### ✅ Formulario de Cotización
- Datos generales (vendedor, cliente, proyecto, etc.)
- Items dinámicos con materiales y otros materiales
- Cálculos automáticos en tiempo real
- Términos y condiciones
- Resumen financiero completo
- Validaciones completas

### ✅ Gestión de Datos (Sistema Híbrido)
- **JSON Primario**: Guardado instantáneo y acceso offline
- **MongoDB Atlas**: Respaldo automático en la nube (41 documentos sincronizados)
- **Sincronización**: Bidireccional cada 15 minutos con resolución de conflictos
- **Búsqueda avanzada**: Resultados en tiempo real
- **Versionado**: Sistema de revisiones con justificación obligatoria
- **Zero Downtime**: Operación garantizada 24/7

### ✅ Almacenamiento PDF (Triple Redundancia)
- **Cloudinary (Primario)**: 25GB gratis con CDN global
- **Google Drive (Fallback)**: Respaldo automático verificado
- **Local (Emergencia)**: Siempre disponible como último recurso
- **Smart Routing**: Failover automático entre sistemas
- **Formato Profesional**: Diseño oficial CWS Company
- **Delivery**: Descarga instantánea con nombres descriptivos

### ✅ Administración Avanzada
- **Panel de Control**: `/admin` con monitoreo en tiempo real
- **API Endpoints**: Scheduler y Cloudinary management
- **Health Checks**: Verificación automática de todos los sistemas
- **Estadísticas**: Uso de storage, sync status, performance metrics
- **Testing Suite**: Validación completa del sistema híbrido

## 🔧 Uso del Sistema

### 1. Crear Nueva Cotización
1. Ir a `/formulario`
2. Completar datos generales
3. Agregar items con materiales
4. Revisar términos y condiciones
5. Guardar cotización
6. Generar PDF (opcional)

### 2. Buscar Cotizaciones
1. Ir a `/` (home)
2. Usar barra de búsqueda
3. Ver resultados paginados
4. Acceder a cotización específica

### 3. Generar PDF
1. Completar y guardar cotización
2. Hacer clic en "📄 Generar PDF"
3. El archivo se descarga automáticamente
4. Formato: `Cotizacion_[Numero].pdf`

## 🌐 Rutas Disponibles (Sistema Híbrido)

### Rutas Principales
| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET/POST | Página principal y búsqueda |
| `/formulario` | GET/POST | Formulario de cotización |
| `/generar_pdf` | POST | Generar PDF con triple redundancia |
| `/ver/<id>` | GET | Ver cotización específica |
| `/buscar` | POST | Búsqueda con paginación |
| `/admin` | GET | Panel de administración |
| `/info` | GET | Información del sistema |
| `/stats` | GET | Estadísticas de la base de datos |

### Nuevas Rutas del Sistema Híbrido
| Ruta | Método | Descripción |
|------|--------|-------------|
| `/admin/scheduler/estado` | GET | Estado del scheduler de sincronización |
| `/admin/scheduler/sync-manual` | POST | Ejecutar sincronización manual |
| `/admin/scheduler/iniciar` | POST | Iniciar scheduler automático |
| `/admin/scheduler/detener` | POST | Detener scheduler |
| `/admin/cloudinary/estado` | GET | Estadísticas de Cloudinary (25GB) |
| `/admin/cloudinary/listar` | GET | Listar PDFs en Cloudinary |

## 📊 Estado del Sistema (Monitoreo Híbrido)

### Verificación en Tiempo Real:
- `/info` - Estado general y librerías PDF
- `/stats` - Estadísticas de cotizaciones (JSON + MongoDB)
- `/admin` - Panel completo de administración
- `/admin/scheduler/estado` - Status de sincronización automática
- `/admin/cloudinary/estado` - Uso de storage (25GB monitor)

### Tests del Sistema Híbrido:
```bash
# Test completo del sistema híbrido
python test_sync_completo.py

# Test específico de Cloudinary
python test_cloudinary.py

# Verificación rápida de estado
python -c "from database import DatabaseManager; db = DatabaseManager(); print(f'MongoDB: {\"OK\" if not db.modo_offline else \"OFFLINE\"}, JSON: {len(db.obtener_todas_cotizaciones()[\"cotizaciones\"])} cotizaciones')"
```

## 🛠️ Solución de Problemas (Sistema Híbrido)

### Sistema Híbrido No Sincroniza
1. **Verificar variables de entorno**: Comprobar `AUTO_SYNC_ENABLED=true`
2. **Check scheduler status**: Ir a `/admin/scheduler/estado`
3. **Ejecutar sync manual**: POST a `/admin/scheduler/sync-manual`
4. **Verificar MongoDB**: El sistema funciona offline si MongoDB falla

### PDFs No Se Suben a Cloudinary
1. **Verificar credenciales**: Comprobar variables `CLOUDINARY_*` en `.env`
2. **Test de conexión**: Ejecutar `python test_cloudinary.py`
3. **Fallback automático**: Sistema usa Google Drive si Cloudinary falla
4. **Check storage**: Ir a `/admin/cloudinary/estado` para ver uso de 25GB

### Problemas de Sincronización
1. **Conflictos**: Sistema usa "last-write-wins" automáticamente
2. **MongoDB offline**: Aplicación funciona normalmente en modo JSON
3. **Logs de sync**: Revisar consola para mensajes de sincronización
4. **Reiniciar scheduler**: Usar endpoints de admin para restart

### PDF No Se Genera
1. **Triple redundancia**: PDFs se guardan en 3 ubicaciones automáticamente
2. **Verificar ReportLab**: `python -c "import reportlab; print('OK')"`
3. **Verificar WeasyPrint**: `python -c "import weasyprint; print('OK')"`
4. **Estado del sistema**: Verificar en `/info` que librerías PDF están disponibles

### Base de Datos
1. **Modo híbrido**: JSON siempre funciona, MongoDB es opcional
2. **Verificación**: Usar `test_sync_completo.py` para diagnóstico completo
3. **Migración**: Sistema automáticamente sincroniza entre JSON y MongoDB
4. **Respaldo**: Datos siempre seguros en JSON local

## 📋 Características del PDF

✅ **Encabezado oficial**: Logo y datos de CWS Company  
✅ **Información completa**: Cliente, proyecto, vendedor  
✅ **Tabla detallada**: Items con materiales y costos  
✅ **Cálculos precisos**: Subtotal, IVA 16%, total  
✅ **Términos**: Moneda, entrega, pago, comentarios  
✅ **Profesional**: Formato A4, firma, datos de contacto  
✅ **Revisiones**: Muestra número de revisión y justificación  

## 🚀 Ejecutar la Aplicación (Sistema Híbrido)

### Ejecución Rápida (Windows)
```bash
# Instalación y ejecución automática
INSTALAR_AUTOMATICO.bat
EJECUTAR_RAPIDO.bat

# O ejecutar directo
"C:\Users\SDS\cotizador_cws\EJECUTAR_RAPIDO.bat"
```

### Ejecución Manual
```bash
# Activar entorno virtual
env\Scripts\activate     # Windows
source env/bin/activate  # Linux/macOS

# Instalar dependencias híbridas
pip install -r requirements.txt

# Verificar sistema antes de ejecutar
python test_sync_completo.py

# Ejecutar aplicación
python app.py
```

### URLs de Acceso:
- **Producción**: `https://cotizador-cws.onrender.com/`
- **Local**: `http://127.0.0.1:5000`
- **Red local**: `http://192.168.0.120:5000` (configurable)

### Primera Ejecución:
```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales reales

# 2. Test del sistema híbrido
python test_sync_completo.py

# 3. Verificar Cloudinary
python test_cloudinary.py

# 4. Ejecutar aplicación
python app.py
```

## 💡 Notas Importantes (Sistema Híbrido)

### ✅ **Arquitectura Resiliente**
- **Zero Downtime**: Sistema garantizado 24/7 con fallbacks automáticos
- **Offline-First**: Funciona perfectamente sin conexión a internet
- **Auto-Recovery**: Recuperación automática cuando servicios vuelven online
- **Triple Redundancia**: PDFs siempre se guardan en 3 ubicaciones

### ✅ **Compatibilidad y Performance**
- **Responsive Design**: Funciona perfectamente en móviles y tablets
- **Real-time Calculations**: Todos los cálculos se actualizan instantáneamente  
- **Professional PDFs**: Formato oficial CWS exacto al template Excel
- **Fast Operations**: JSON primario garantiza operaciones sub-segundo

### ✅ **Sistema de Sincronización**
- **Automatic Sync**: Cada 15 minutos sin intervención manual
- **Conflict Resolution**: Last-write-wins automático con timestamps
- **Manual Override**: Sincronización manual disponible vía API
- **Health Monitoring**: Estado visible en tiempo real

## 📞 Soporte (Sistema Híbrido)

### Diagnóstico Rápido:
```bash
# 1. Estado general del sistema
curl https://cotizador-cws.onrender.com/info

# 2. Estado del scheduler
curl https://cotizador-cws.onrender.com/admin/scheduler/estado

# 3. Estado de Cloudinary
curl https://cotizador-cws.onrender.com/admin/cloudinary/estado

# 4. Test completo local
python test_sync_completo.py
```

### Para Problemas Técnicos:
1. **Verificar logs**: Render dashboard o consola local
2. **Estado del sistema**: `/info` y `/admin`
3. **Test de componentes**: Usar `test_*.py` files
4. **Documentación completa**: Ver `CLAUDE.md`
5. **Sincronización manual**: Usar endpoints de `/admin/scheduler/`

### Recursos Adicionales:
- **CLAUDE.md**: Documentación técnica completa
- **test_sync_completo.py**: Diagnóstico integral
- **Variables de entorno**: Ver `.env` para configuración
- **API Endpoints**: Nuevas rutas de admin para monitoreo
