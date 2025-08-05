# 🏗️ CWS Cotizador - Sistema de Cotizaciones

Sistema completo de cotizaciones para CWS Company con generación de PDFs en formato oficial.

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

## 🚀 Instalación y Configuración

### 1. Dependencias básicas
```bash
pip install flask python-dotenv pymongo
```

### 2. Para habilitar PDF (WeasyPrint)
```bash
# Instalación básica
pip install weasyprint

# Si hay problemas en Windows
pip install --only-binary=all weasyprint

# O usando conda
conda install -c conda-forge weasyprint
```

### 3. Configuración
```bash
# Copiar archivo de configuración
cp .env.example .env

# Editar variables de entorno según necesidad
```

## 📁 Estructura del Proyecto

```
cotizador_cws/
├── app.py                          # Aplicación principal Flask
├── database.py                     # Gestor de base de datos
├── config.py                       # Configuraciones
├── .env                           # Variables de entorno
├── INSTRUCCIONES_PDF.md           # Guía para instalar WeasyPrint
├── README.md                      # Este archivo
├── templates/
│   ├── home.html                  # Página principal
│   ├── formulario.html            # Formulario de cotización
│   ├── formato_pdf_cws.html       # Template para PDF oficial
│   └── ver_cotizacion.html        # Vista de cotización
└── requirements.txt               # Dependencias Python
```

## 🎯 Funcionalidades

### ✅ Formulario de Cotización
- Datos generales (vendedor, cliente, proyecto, etc.)
- Items dinámicos con materiales y otros materiales
- Cálculos automáticos en tiempo real
- Términos y condiciones
- Resumen financiero completo
- Validaciones completas

### ✅ Gestión de Datos
- Guardado en MongoDB o archivo JSON offline
- Búsqueda avanzada de cotizaciones
- Versionado con justificación de cambios
- Respaldo automático de datos

### ✅ Generación de PDF
- Formato oficial CWS Company
- Diseño basado en template Excel proporcionado
- Descarga automática del archivo
- Nombres descriptivos (Cotizacion_[Numero].pdf)

### ✅ Administración
- Panel de administración (/admin)
- Migración de datos offline ↔ MongoDB
- Estadísticas del sistema
- Verificación de estado

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

## 🌐 Rutas Disponibles

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET/POST | Página principal y búsqueda |
| `/formulario` | GET/POST | Formulario de cotización |
| `/generar_pdf` | POST | Generar PDF de cotización |
| `/ver/<id>` | GET | Ver cotización específica |
| `/buscar` | POST | Búsqueda con paginación |
| `/admin` | GET | Panel de administración |
| `/info` | GET | Información del sistema |
| `/stats` | GET | Estadísticas de la base de datos |

## 📊 Estado del Sistema

Verifica el estado en tiempo real:
- `/info` - Información general y estado de WeasyPrint
- `/stats` - Estadísticas de cotizaciones
- `/admin` - Panel completo de administración

## 🛠️ Solución de Problemas

### PDF no se genera
1. Verificar que WeasyPrint está instalado: `python -c "import weasyprint"`
2. Instalar dependencias según SO (ver INSTRUCCIONES_PDF.md)
3. Reiniciar servidor Flask
4. Verificar en `/info` que `weasyprint_disponible: true`

### Errores de cálculo
1. Verificar que JavaScript está habilitado
2. Revisar consola del navegador para errores
3. Asegurar que todos los campos numéricos tienen valores válidos

### Problemas de base de datos
1. Verificar conexión MongoDB en variables de entorno
2. El sistema funciona offline con archivo JSON como respaldo
3. Usar `/admin` para migrar datos entre sistemas

## 📋 Características del PDF

✅ **Encabezado oficial**: Logo y datos de CWS Company  
✅ **Información completa**: Cliente, proyecto, vendedor  
✅ **Tabla detallada**: Items con materiales y costos  
✅ **Cálculos precisos**: Subtotal, IVA 16%, total  
✅ **Términos**: Moneda, entrega, pago, comentarios  
✅ **Profesional**: Formato A4, firma, datos de contacto  
✅ **Revisiones**: Muestra número de revisión y justificación  

## 🚀 Ejecutar la Aplicación

```bash
# Activar entorno virtual (opcional pero recomendado)
python -m venv env
source env/bin/activate  # Linux/macOS
# o
env\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python app.py
```

La aplicación estará disponible en: `http://127.0.0.1:5000`

## 💡 Notas Importantes

- El sistema funciona sin WeasyPrint (solo se deshabilita la generación de PDF)
- Los datos se guardan automáticamente en MongoDB o archivo JSON
- El formato PDF replica exactamente el template Excel proporcionado
- Todos los cálculos se realizan en tiempo real
- El sistema es responsivo y funciona en móviles

## 📞 Soporte

Para problemas técnicos:
1. Revisar logs del servidor
2. Verificar `/info` para estado del sistema
3. Consultar INSTRUCCIONES_PDF.md para problemas de PDF
4. Usar `/admin` para diagnósticos de base de datos
