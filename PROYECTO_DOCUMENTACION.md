# Cotizador CWS - Proyecto Claude Code

## Información del Proyecto
- **Nombre**: Cotizador CWS
- **Ubicación**: `C:\Users\SDS\cotizador_cws`
- **Tipo**: Aplicación web Flask para sistema de cotizaciones
- **Estado**: En desarrollo activo

## Descripción
Sistema completo de cotizaciones para CWS Company con:
- Formulario dinámico de cotizaciones con numeración automática
- Generación y almacenamiento automático de PDFs en formato profesional
- Base de datos MongoDB con sincronización automática
- Sistema de búsqueda y gestión de PDFs integrado con Google Drive
- Panel de administración completo
- Búsqueda avanzada de cotizaciones y PDFs
- Cálculos automáticos en tiempo real
- Sistema de revisiones con justificación obligatoria

## Comandos Principales

### Desarrollo
```bash
# Cambiar al directorio del proyecto
cd C:\Users\SDS\cotizador_cws

# Activar entorno virtual
env\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python app.py
```

### Ejecución Rápida
```bash
# Ejecutar directamente con batch files incluidos
EJECUTAR_RAPIDO.bat
# o
EJECUTAR_EN_RED.bat
```

### Testing y Validación
```bash
# Verificar estado del sistema
python -c "import weasyprint; print('WeasyPrint OK')"

# Verificar dependencias
pip check

# Probar importaciones principales
python -c "import flask, pymongo; print('Dependencias OK')"
```

## Estructura Técnica
- **Frontend**: HTML/CSS/JavaScript (templates Jinja2)
- **Backend**: Python Flask
- **Base de Datos**: MongoDB con respaldo automático a JSON offline
- **PDF**: ReportLab (principal) + WeasyPrint (fallback)
- **Almacenamiento**: Google Drive + carpetas locales para PDFs
- **Archivos principales**:
  - `app.py` - Aplicación principal con generación automática de números
  - `database.py` - Gestor de BD con sincronización automática
  - `config.py` - Configuraciones del sistema
  - `pdf_manager.py` - Gestión completa de PDFs y almacenamiento
  - `google_drive_client.py` - Cliente para integración con Google Drive

## URLs de la Aplicación
- Home: `http://127.0.0.1:5000/`
- Formulario: `http://127.0.0.1:5000/formulario`
- Admin: `http://127.0.0.1:5000/admin`
- Info Sistema: `http://127.0.0.1:5000/info`

## Funcionalidades Implementadas

### ✅ Sistema de Numeración Automática
- **Formato**: Cliente-CWS-VendedorIniciales-###-R#-Proyecto
- **Generación automática** basada en datos del formulario
- **Campo deshabilitado** para evitar edición manual
- **Consecutivo automático** por vendedor y cliente

### ✅ Sistema de Revisiones Avanzado
- **Revisión automática** R1, R2, R3, etc.
- **Justificación obligatoria** para revisiones ≥ R2
- **Preservación de datos** originales al crear nueva revisión
- **Historial completo** de todas las versiones

### ✅ Generación y Gestión de PDFs
- **Formato profesional** con ReportLab
- **Diseño corporativo** CWS con logo y colores oficiales
- **Almacenamiento automático** en Google Drive y carpetas locales
- **Índice MongoDB** para búsquedas rápidas
- **Fallback a WeasyPrint** para compatibilidad

### ✅ Sistema de Búsqueda Integrado
- **Búsqueda de cotizaciones** en tiempo real
- **Búsqueda de PDFs** en múltiples fuentes (MongoDB, Google Drive, local)
- **Filtros avanzados** por cliente, vendedor, proyecto, fecha
- **Modo offline** con búsqueda en archivos locales

### ✅ Base de Datos Híbrida
- **MongoDB principal** con conexión automática
- **Respaldo automático** a JSON offline
- **Sincronización bidireccional** entre online/offline
- **Tolerancia a fallos** - funciona sin conexión

### ✅ Funcionalidades Básicas
- Formulario de cotización con items dinámicos  
- Cálculos automáticos en tiempo real  
- Panel de administración completo
- Validaciones de datos robustas
- Interfaz responsiva y profesional

## Configuración de Entorno
El proyecto incluye múltiples archivos batch para diferentes casos de uso:
- Instalación automática
- Ejecución en red local
- Configuración de accesos directos
- Diagnósticos de red
- Deploy a servicios cloud (Heroku, Railway, Render)

## 🚀 Avances Recientes (Agosto 2025)

### Correcciones Críticas Realizadas
1. **Problema de MongoDB**: Solucionado error de codificación de caracteres que causaba desconexión automática
2. **Almacenamiento de PDFs**: Implementado almacenamiento automático al generar PDFs
3. **Búsqueda de PDFs**: Corregido sistema de búsqueda con validación correcta de colecciones MongoDB
4. **Formato PDF Profesional**: Rediseñado completamente con ReportLab para apariencia corporativa

### Mejoras de Formato PDF
- **Encabezado profesional** con logo CWS, información de empresa y datos de cotización
- **Información del cliente** en formato de tarjeta con diseño elegante
- **Proyecto destacado** con fondo azul corporativo
- **Texto introductorio** profesional con formato justificado
- **Tabla de items mejorada** con numeración, colores alternados y precios destacados
- **Totales profesionales** con caja de resumen financial
- **Pie de página completo** con saludo, vendedor y footer corporativo

### Correcciones Técnicas
- **Emojis eliminados**: Reemplazados todos los emojis problemáticos con prefijos ASCII
- **Validación MongoDB**: Corregido uso de `is None` en lugar de `not collection`
- **Encoding fixes**: Solucionados problemas de codificación en múltiples archivos
- **Error handling**: Mejorado manejo de errores en todo el sistema

### Commits Principales
- `2609b58`: Fix MongoDB connection issues caused by emoji encoding
- `4e1a3c6`: Implement complete PDF storage and professional formatting system

## 🔧 Estado Actual del Sistema

### ✅ Completamente Funcional
- Numeración automática de cotizaciones
- Generación y almacenamiento automático de PDFs
- Sistema de búsqueda integrado (cotizaciones + PDFs)
- Base de datos híbrida (MongoDB + offline)
- Formato PDF profesional

### 🔍 Ubicación de PDFs
- **Google Drive**: `G:\Mi unidad\CWS\CWS_Cotizaciones_PDF\nuevas\`
- **Búsquedas**: Disponibles inmediatamente después de generar
- **Formato**: Profesional con diseño corporativo CWS

## 📋 Próximos Desarrollos
- Optimizaciones adicionales de rendimiento
- Mejoras en la interfaz de usuario basadas en feedback
- Integración completa con Google Drive API (con credenciales)
- Funcionalidades adicionales según requerimientos específicos
- Testing automatizado completo