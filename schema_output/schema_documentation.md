# CWS Cotizador - Esquema de Base de Datos Unificado

**Versión:** 1.0.0  
**Generado:** 2025-08-19 13:08:34  
**Tablas:** 4

## Descripción General

Este esquema unificado está diseñado para soportar múltiples sistemas de almacenamiento:
- **Supabase PostgreSQL** (principal)
- **JSON Local** (desarrollo/offline)
- **Cloudinary** (metadatos de PDFs)
- **Google Drive** (índice de archivos)

## Características Principales

- ✅ **Compatibilidad Multi-Sistema**: Esquema único para todos los backends
- ✅ **Búsqueda Avanzada**: Índices GIN y full-text search en español
- ✅ **Integridad Referencial**: Claves foráneas y constraints
- ✅ **Auditoria Completa**: Timestamps automáticos y logs del sistema
- ✅ **Flexibilidad JSON**: Campos JSONB para datos semi-estructurados
- ✅ **Optimización**: Índices especializados para consultas frecuentes

## Tabla: `cotizaciones`

**Descripción:** Tabla principal de cotizaciones CWS

### Columnas

| Columna | Tipo | Descripción | Constraints |
|---------|------|-------------|-------------|
| `id` | uuid | ID único del registro | PK |
| `numero_cotizacion` | varchar(100) | Número único de cotización (formato: CLIENTE-CWS-VENDOR-###-R#-PROYECTO) | NOT NULL, UNIQUE, INDEX |
| `revision` | integer | Número de revisión de la cotización | NOT NULL |
| `datos_generales` | jsonb | Información general del cliente y proyecto | NOT NULL |
| `items` | jsonb | Array de items cotizados | - |
| `totales` | jsonb | Totales calculados de la cotización | - |
| `observaciones` | text | Observaciones y notas adicionales | - |
| `fecha_creacion` | timestamp with time zone | Fecha y hora de creación | NOT NULL, INDEX |
| `fecha_modificacion` | timestamp with time zone | Fecha y hora de última modificación | NOT NULL |
| `version` | varchar(10) | Versión del formato de datos | - |
| `estado` | varchar(20) | Estado de la cotización (activa, archivada, eliminada) | - |
| `timestamp` | bigint | Timestamp Unix para sincronización | - |
| `hash_contenido` | varchar(64) | Hash MD5 del contenido para detección de cambios | - |
| `sincronizado` | boolean | Indica si el registro está sincronizado | - |
| `metadata` | jsonb | Metadatos adicionales del sistema | - |

### Índices

- **idx_numero_cotizacion**: `numero_cotizacion` (UNIQUE)
- **idx_fecha_creacion**: `fecha_creacion`
- **idx_cliente_gin**: `(datos_generales->'cliente')`
- **idx_vendedor_gin**: `(datos_generales->'vendedor')`
- **idx_items_gin**: `items`
- **idx_busqueda_texto**: Índice funcional sobre `to_tsvector('spanish', coalesce(numero_cotizacion,'') || ' ' || coalesce(datos_generales->>'cliente','') || ' ' || coalesce(datos_generales->>'proyecto',''))`

## Tabla: `pdf_files`

**Descripción:** Índice de archivos PDF almacenados

### Columnas

| Columna | Tipo | Descripción | Constraints |
|---------|------|-------------|-------------|
| `id` | uuid |  | PK |
| `numero_cotizacion` | varchar(100) | Número de cotización asociado | NOT NULL, INDEX |
| `nombre_archivo` | varchar(255) | Nombre original del archivo | NOT NULL |
| `tamaño_bytes` | bigint | Tamaño del archivo en bytes | - |
| `hash_contenido` | varchar(64) | Hash SHA256 del contenido del PDF | - |
| `ubicaciones` | jsonb | URLs y metadatos de almacenamiento por proveedor | - |
| `proveedor_principal` | varchar(20) | Proveedor de almacenamiento principal | - |
| `fecha_creacion` | timestamp with time zone |  | NOT NULL |
| `fecha_subida` | timestamp with time zone | Fecha de primera subida a almacenamiento | - |
| `fecha_ultimo_acceso` | timestamp with time zone | Fecha de último acceso al archivo | - |
| `estado` | varchar(20) | Estado del archivo (disponible, procesando, error, eliminado) | - |
| `verificado` | boolean | Indica si la integridad del archivo ha sido verificada | - |
| `ultima_verificacion` | timestamp with time zone | Fecha de última verificación de integridad | - |
| `metadata` | jsonb | Metadatos adicionales del PDF | - |

### Índices

- **idx_pdf_numero_cotizacion**: `numero_cotizacion`
- **idx_pdf_fecha_creacion**: `fecha_creacion`
- **idx_pdf_hash**: `hash_contenido`
- **idx_pdf_ubicaciones_gin**: `ubicaciones`

## Tabla: `system_logs`

**Descripción:** Logs del sistema unificado

### Columnas

| Columna | Tipo | Descripción | Constraints |
|---------|------|-------------|-------------|
| `id` | uuid |  | PK |
| `timestamp` | timestamp with time zone |  | NOT NULL, INDEX |
| `nivel` | varchar(10) | Nivel del log (INFO, WARNING, ERROR, CRITICAL) | NOT NULL |
| `modulo` | varchar(50) | Módulo que generó el log | - |
| `mensaje` | text | Mensaje del log | NOT NULL |
| `contexto` | jsonb | Contexto adicional del evento | - |
| `usuario` | varchar(50) | Usuario relacionado con el evento | - |
| `ip_address` | inet | Dirección IP del origen | - |

### Índices

- **idx_logs_timestamp**: `timestamp`
- **idx_logs_nivel**: `nivel`
- **idx_logs_modulo**: `modulo`

## Tabla: `system_config`

**Descripción:** Configuración del sistema unificado

### Columnas

| Columna | Tipo | Descripción | Constraints |
|---------|------|-------------|-------------|
| `clave` | varchar(100) | Clave de configuración | PK |
| `valor` | jsonb | Valor de configuración (JSON) | NOT NULL |
| `descripcion` | text | Descripción de la configuración | - |
| `categoria` | varchar(50) | Categoría de configuración | - |
| `modificado_en` | timestamp with time zone |  | - |
| `modificado_por` | varchar(50) | Usuario que modificó la configuración | - |
