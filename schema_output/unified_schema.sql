-- ========================================
-- CWS COTIZADOR - ESQUEMA UNIFICADO
-- Versión: 1.0.0
-- Generado: 2025-08-19T13:08:34.492393
-- ========================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===== TABLAS =====
-- Tabla: cotizaciones
-- Tabla principal de cotizaciones CWS
CREATE TABLE IF NOT EXISTS cotizaciones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  numero_cotizacion varchar(100) NOT NULL UNIQUE,
  revision integer NOT NULL DEFAULT 1,
  datos_generales jsonb NOT NULL,
  items jsonb DEFAULT [],
  totales jsonb,
  observaciones text,
  fecha_creacion timestamp with time zone NOT NULL DEFAULT now(),
  fecha_modificacion timestamp with time zone NOT NULL DEFAULT now(),
  version varchar(10) DEFAULT '1.0',
  estado varchar(20) DEFAULT 'activa',
  timestamp bigint,
  hash_contenido varchar(64),
  sincronizado boolean DEFAULT true,
  metadata jsonb DEFAULT {}
,
  CONSTRAINT chk_revision_positiva CHECK (revision > 0)
,
  CONSTRAINT chk_estado_valido CHECK (estado IN ('activa', 'archivada', 'eliminada'))
);

-- Tabla: pdf_files
-- Índice de archivos PDF almacenados
CREATE TABLE IF NOT EXISTS pdf_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  numero_cotizacion varchar(100) NOT NULL,
  nombre_archivo varchar(255) NOT NULL,
  tamaño_bytes bigint,
  hash_contenido varchar(64),
  ubicaciones jsonb DEFAULT {},
  proveedor_principal varchar(20) DEFAULT 'cloudinary',
  fecha_creacion timestamp with time zone NOT NULL DEFAULT now(),
  fecha_subida timestamp with time zone,
  fecha_ultimo_acceso timestamp with time zone,
  estado varchar(20) DEFAULT 'disponible',
  verificado boolean DEFAULT false,
  ultima_verificacion timestamp with time zone,
  metadata jsonb DEFAULT {}
);

-- Tabla: system_logs
-- Logs del sistema unificado
CREATE TABLE IF NOT EXISTS system_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp timestamp with time zone NOT NULL DEFAULT now(),
  nivel varchar(10) NOT NULL,
  modulo varchar(50),
  mensaje text NOT NULL,
  contexto jsonb DEFAULT {},
  usuario varchar(50),
  ip_address inet
);

-- Tabla: system_config
-- Configuración del sistema unificado
CREATE TABLE IF NOT EXISTS system_config (
  clave varchar(100) PRIMARY KEY,
  valor jsonb NOT NULL,
  descripcion text,
  categoria varchar(50),
  modificado_en timestamp with time zone DEFAULT now(),
  modificado_por varchar(50)
);

-- ===== ÍNDICES =====
-- Índices para cotizaciones
CREATE UNIQUE INDEX IF NOT EXISTS idx_numero_cotizacion ON cotizaciones (numero_cotizacion);
CREATE INDEX IF NOT EXISTS idx_fecha_creacion ON cotizaciones USING btree (fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_cliente_gin ON cotizaciones USING gin ((datos_generales->'cliente'));
CREATE INDEX IF NOT EXISTS idx_vendedor_gin ON cotizaciones USING gin ((datos_generales->'vendedor'));
CREATE INDEX IF NOT EXISTS idx_items_gin ON cotizaciones USING gin (items);
CREATE INDEX IF NOT EXISTS idx_busqueda_texto ON cotizaciones USING gin (to_tsvector('spanish', coalesce(numero_cotizacion,'') || ' ' || coalesce(datos_generales->>'cliente','') || ' ' || coalesce(datos_generales->>'proyecto','')));

-- Índices para pdf_files
CREATE INDEX IF NOT EXISTS idx_pdf_numero_cotizacion ON pdf_files (numero_cotizacion);
CREATE INDEX IF NOT EXISTS idx_pdf_fecha_creacion ON pdf_files (fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_pdf_hash ON pdf_files (hash_contenido);
CREATE INDEX IF NOT EXISTS idx_pdf_ubicaciones_gin ON pdf_files USING gin (ubicaciones);

-- Índices para system_logs
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_nivel ON system_logs (nivel);
CREATE INDEX IF NOT EXISTS idx_logs_modulo ON system_logs (modulo);

-- ===== CLAVES FORÁNEAS =====
-- FK para pdf_files
ALTER TABLE pdf_files ADD CONSTRAINT fk_pdf_cotizacion FOREIGN KEY (numero_cotizacion) REFERENCES cotizaciones (numero_cotizacion) ON DELETE CASCADE;

-- ===== CONFIGURACIÓN INICIAL =====
INSERT INTO system_config (clave, valor, descripcion, categoria) VALUES
('schema_version', '"1.0.0"', 'Versión actual del esquema', 'sistema'),
('created_at', '"2025-08-19T13:08:34.492393"', 'Fecha de creación del esquema', 'sistema'),
('auto_vacuum', 'true', 'Habilitar auto-vacuum', 'performance'),
('search_language', '"spanish"', 'Idioma para búsqueda full-text', 'search')
ON CONFLICT (clave) DO UPDATE SET 
  valor = EXCLUDED.valor,
  modificado_en = now();

-- ===== FUNCIONES AUXILIARES =====

-- Función para actualizar fecha_modificacion automáticamente
CREATE OR REPLACE FUNCTION actualizar_fecha_modificacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_modificacion = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar fecha_modificacion en cotizaciones
DROP TRIGGER IF EXISTS trigger_actualizar_fecha_modificacion ON cotizaciones;
CREATE TRIGGER trigger_actualizar_fecha_modificacion
    BEFORE UPDATE ON cotizaciones
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_modificacion();

-- Función para búsqueda full-text
CREATE OR REPLACE FUNCTION buscar_cotizaciones(termino text, limite integer DEFAULT 20)
RETURNS TABLE(
    numero_cotizacion varchar,
    cliente text,
    proyecto text,
    fecha_creacion timestamp with time zone,
    ranking real
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.numero_cotizacion,
        c.datos_generales->>'cliente' as cliente,
        c.datos_generales->>'proyecto' as proyecto,
        c.fecha_creacion,
        ts_rank(to_tsvector('spanish', 
            coalesce(c.numero_cotizacion,'') || ' ' || 
            coalesce(c.datos_generales->>'cliente','') || ' ' ||
            coalesce(c.datos_generales->>'proyecto','')
        ), plainto_tsquery('spanish', termino)) as ranking
    FROM cotizaciones c
    WHERE to_tsvector('spanish', 
        coalesce(c.numero_cotizacion,'') || ' ' || 
        coalesce(c.datos_generales->>'cliente','') || ' ' ||
        coalesce(c.datos_generales->>'proyecto','')
    ) @@ plainto_tsquery('spanish', termino)
    AND c.estado = 'activa'
    ORDER BY ranking DESC
    LIMIT limite;
END;
$$ LANGUAGE plpgsql;
