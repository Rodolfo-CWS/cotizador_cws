# Guía de Arquitectura Supabase - CWS Cotizador

## 🏗️ Arquitectura Completa del Sistema

### 📊 **Diagrama de Arquitectura**

```
[Web Browser] → [Render.com] → [Supabase PostgreSQL] → [Cloudinary CDN]
     ↓               ↓              ↓                    ↓
[Formularios] → [Flask App] → [Base de Datos] → [PDFs (25GB)]
     ↓               ↓              ↓                    ↓  
[Validación] → [supabase_manager.py] → [Cotizaciones] → [URLs Permanentes]
     ↓               ↓              ↓                    ↓
[JSON Backup] → [Modo Offline] → [Fallback Local] → [Respaldo Local]
```

### 🔄 **Flujo de Guardado de Cotización**

```mermaid
flowchart TD
    A[Usuario crea cotización] --> B{Supabase disponible?}
    B -->|Sí| C[Guardar en PostgreSQL]
    B -->|No| D[Modo Offline - JSON]
    C --> E{PDF generado?}
    D --> E
    E -->|Sí| F{Cloudinary disponible?}
    E -->|No| I[Responder al usuario]
    F -->|Sí| G[Subir PDF a Cloudinary]
    F -->|No| H[Guardar PDF localmente]
    G --> I
    H --> I
```

## 🗄️ **Base de Datos: Supabase PostgreSQL**

### **Configuración de Conexión**

```python
# Configuración en supabase_manager.py
DATABASE_URL = "postgresql://postgres.[REF]:[PASS]@aws-1-us-east-2.pooler.supabase.com:6543/postgres"
SUPABASE_URL = "https://[REF].supabase.co"
SUPABASE_ANON_KEY = "[ANON_KEY]"
```

### **Schema Principal (cotizaciones)**

```sql
CREATE TABLE cotizaciones (
    id SERIAL PRIMARY KEY,
    numero_cotizacion VARCHAR(255) UNIQUE NOT NULL,
    datos_generales JSONB NOT NULL,    -- Cliente, vendedor, proyecto, etc.
    items JSONB NOT NULL,              -- Array de items con materiales
    revision INTEGER DEFAULT 1,
    version VARCHAR(10) DEFAULT '1.0.0',
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    timestamp BIGINT,                  -- Unix timestamp
    usuario VARCHAR(100),
    observaciones TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices para búsqueda rápida
CREATE INDEX idx_numero_cotizacion ON cotizaciones(numero_cotizacion);
CREATE INDEX idx_cliente ON cotizaciones USING GIN ((datos_generales->>'cliente') gin_trgm_ops);
CREATE INDEX idx_vendedor ON cotizaciones USING GIN ((datos_generales->>'vendedor') gin_trgm_ops);
```

### **Funcionalidades Implementadas**

- ✅ **Guardado con UPSERT**: `ON CONFLICT (numero_cotizacion) DO UPDATE`
- ✅ **Búsqueda JSONB**: Búsqueda en campos anidados con índices GIN
- ✅ **Paginación**: Soporte nativo con `LIMIT` y `OFFSET`
- ✅ **Timestamps automáticos**: `created_at` y `updated_at`
- ✅ **Fallback offline**: JSON local cuando Supabase no está disponible

## ☁️ **Almacenamiento de PDFs: Cloudinary**

### **Configuración**

```python
# Configuración en cloudinary_manager.py
CLOUDINARY_CLOUD_NAME = "dvexwdihj"
CLOUDINARY_API_KEY = "685549632198419"  
CLOUDINARY_API_SECRET = "[SECRET]"      # Requerido para subidas

# Carpetas organizadas
folder_nuevas = "cotizaciones/nuevas"
folder_antiguas = "cotizaciones/antiguas"
```

### **Flujo de Subida**

```python
# Ejemplo de subida
resultado = cloudinary.uploader.upload(
    archivo_local,
    public_id=f"cotizaciones/nuevas/{numero_cotizacion}",
    resource_type="raw",    # Para PDFs
    overwrite=True,         # Reemplazar si existe
    invalidate=True,        # Limpiar cache CDN
    tags=["cotizacion", "pdf", "cws"]
)

# URL resultante
url_pdf = resultado['secure_url']
# Ejemplo: https://res.cloudinary.com/dvexwdihj/raw/upload/cotizaciones/nuevas/BMW-CWS-CHR-001-R1-HOUSING.pdf
```

### **Beneficios de Cloudinary**

- 🆓 **25GB gratis** - Almacenamiento generoso
- 🌍 **CDN global** - Acceso rápido desde cualquier ubicación  
- 🔒 **URLs seguras** - HTTPS por defecto
- 🏷️ **Organización** - Carpetas y tags automáticos
- 📊 **Analytics** - Estadísticas de uso incluidas

## 📁 **Sistema de Respaldo Local**

### **Estructura de Archivos**

```
cotizador_cws/
├── cotizaciones_offline.json     # Base de datos JSON (fallback)
├── pdfs_cotizaciones/            # PDFs locales (temporal en Render)
│   ├── nuevas/                   # Cotizaciones nuevas
│   └── antiguas/                 # Cotizaciones antiguas
└── supabase_manager.py           # Gestor principal
```

### **JSON Offline Structure**

```json
{
  "cotizaciones": [
    {
      "numeroCotizacion": "BMW-CWS-CHR-001-R1-HOUSING",
      "datosGenerales": {
        "cliente": "BMW",
        "vendedor": "CHRIS MORALES", 
        "proyecto": "HOUSING",
        "fecha": "2025-08-19",
        "atencionA": "Roberto Gomes",
        "contacto": "fdfdfd@gmail.com"
      },
      "items": [
        {
          "descripcion": "Item 1",
          "cantidad": 1,
          "precio": 100,
          "subtotal": 100
        }
      ],
      "timestamp": 1692467022000,
      "fechaCreacion": "2025-08-19T16:23:42.000Z"
    }
  ]
}
```

## 🔄 **Modo Híbrido: Online/Offline**

### **Detección Automática**

```python
def _inicializar_conexion(self):
    """Detecta automáticamente disponibilidad de Supabase"""
    try:
        # Test de conectividad
        self.pg_connection = psycopg2.connect(self.database_url)
        cursor = self.pg_connection.cursor()
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()
        
        if result['test'] == 1:
            self.modo_offline = False  # ONLINE
            print("[SUPABASE] Conectado exitosamente")
        else:
            raise Exception("Test falló")
            
    except Exception as e:
        self.modo_offline = True  # OFFLINE  
        print(f"[SUPABASE] Activando modo offline: {e}")
```

### **Operaciones por Modo**

| Operación | Modo Online (Supabase) | Modo Offline (JSON) |
|-----------|------------------------|---------------------|
| **Guardar** | PostgreSQL + JSON backup | Solo JSON |
| **Buscar** | SQL queries con índices | Búsqueda en memoria |
| **PDFs** | Cloudinary + local backup | Solo local |
| **Persistencia** | ✅ Permanente | ⚠️ Temporal (Render) |

## 🛠️ **APIs y Endpoints**

### **Principales Rutas**

```python
# Crear cotización
POST /formulario
# Datos: JSON con datosGenerales + items
# Respuesta: {success, numeroCotizacion, pdf_generado}

# Buscar cotizaciones  
POST /buscar
# Datos: {query, page, per_page}
# Respuesta: {resultados, total, pages}

# Servir PDF (múltiples opciones)
GET /pdf/<numero>              # Ruta principal
GET /local-pdf/<numero>        # Archivos locales (Render)

# Administración
GET /admin/supabase/estado     # Estado de conexión
GET /admin/cloudinary/estado   # Estadísticas de almacenamiento
```

### **Respuestas Típicas**

```json
// Guardado exitoso
{
  "success": true,
  "mensaje": "Cotización guardada correctamente", 
  "numeroCotizacion": "BMW-CWS-CHR-001-R1-HOUSING",
  "pdf_generado": true,
  "pdf_info": {
    "ruta_local": "pdfs_cotizaciones/nuevas/BMW-CWS-CHR-001-R1-HOUSING.pdf",
    "cloudinary_url": "https://res.cloudinary.com/dvexwdihj/raw/upload/..."
  }
}

// Búsqueda
{
  "resultados": [...],
  "total": 25,
  "page": 1, 
  "per_page": 20,
  "pages": 2,
  "modo": "online"
}
```

## 🔧 **Configuración y Deployment**

### **Variables de Entorno Render**

```bash
# Supabase (Principal)
DATABASE_URL=postgresql://postgres.[REF]:[PASS]@aws-1-us-east-2.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_ANON_KEY=[ANON_KEY]

# Cloudinary (PDFs)  
CLOUDINARY_CLOUD_NAME=dvexwdihj
CLOUDINARY_API_KEY=685549632198419
CLOUDINARY_API_SECRET=[SECRET]

# Sistema
FLASK_ENV=production
APP_VERSION=2.1.0
```

### **Script de Verificación**

```bash
# Verificar configuración completa
python configure_permanent_storage.py

# Test específicos
python test_simple_supabase.py     # Conectividad Supabase
python test_cloudinary.py          # Almacenamiento Cloudinary
```

## 🚀 **Beneficios del Sistema Actual**

### ✅ **Ventajas Técnicas**

- **Permanencia**: Datos y PDFs persisten indefinidamente
- **Escalabilidad**: PostgreSQL maneja miles de cotizaciones
- **Performance**: Índices GIN para búsquedas rápidas en JSONB
- **CDN Global**: PDFs se sirven desde Cloudinary CDN
- **Costo $0**: Ambos servicios en tier gratuito
- **Resilencia**: Fallback automático a modo offline

### ✅ **Ventajas Operacionales**

- **Cero Configuración**: Sistema funciona out-of-the-box
- **Auto-Deployment**: GitHub → Render automático
- **Monitoreo**: Logs estructurados para debugging
- **Backup Múltiple**: JSON + PostgreSQL + PDFs locales
- **Compatibilidad**: API idéntica para online/offline

## 📋 **Próximas Mejoras Planificadas**

### 🔄 **Funcionalidades**
- [ ] Panel de administración Supabase
- [ ] Sync bidireccional JSON ↔ PostgreSQL
- [ ] Compresión automática de PDFs
- [ ] Notificaciones por email

### 🏗️ **Arquitectura**
- [ ] Cache Redis para búsquedas
- [ ] WebSockets para updates en tiempo real
- [ ] API REST completa
- [ ] Multi-tenant support

---

**Última actualización**: Agosto 19, 2025  
**Versión del sistema**: 2.1.0  
**Estado**: ✅ Producción - Totalmente operacional