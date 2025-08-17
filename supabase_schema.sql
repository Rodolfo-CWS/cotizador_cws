-- =====================================================
-- SCHEMA SUPABASE PARA CWS COTIZADOR
-- =====================================================

-- Habilitar extensiones necesarias para búsqueda de texto
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. TABLA PRINCIPAL: cotizaciones
-- Almacena todos los datos de cotizaciones con estructura optimizada
CREATE TABLE cotizaciones (
    id SERIAL PRIMARY KEY,
    numero_cotizacion VARCHAR(255) UNIQUE NOT NULL,
    
    -- Datos generales como JSONB para flexibilidad
    datos_generales JSONB NOT NULL,
    
    -- Items de la cotización
    items JSONB NOT NULL,
    
    -- Control de versiones
    revision INTEGER DEFAULT 1,
    version VARCHAR(10) DEFAULT '1.0.0',
    
    -- Timestamps
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    timestamp BIGINT,
    
    -- Metadatos adicionales
    usuario VARCHAR(100),
    observaciones TEXT,
    
    -- Control automático
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. TABLA PDFs: pdf_storage
-- Almacena PDFs como binarios + metadatos
CREATE TABLE pdf_storage (
    id SERIAL PRIMARY KEY,
    cotizacion_id INTEGER REFERENCES cotizaciones(id) ON DELETE CASCADE,
    numero_cotizacion VARCHAR(255) NOT NULL,
    
    -- Almacenamiento PDF
    pdf_data BYTEA, -- PDF como binary data
    file_size INTEGER,
    mime_type VARCHAR(100) DEFAULT 'application/pdf',
    
    -- URLs alternativas (backup)
    cloudinary_url TEXT,
    google_drive_id TEXT,
    local_path TEXT,
    
    -- Metadatos del PDF
    generator VARCHAR(50) DEFAULT 'reportlab', -- reportlab o weasyprint
    page_count INTEGER,
    
    -- Control
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. ÍNDICES PARA BÚSQUEDA RÁPIDA
-- ==========================================

-- Búsqueda por número de cotización (principal)
CREATE INDEX idx_numero_cotizacion ON cotizaciones(numero_cotizacion);

-- Búsquedas por campos de datos generales (JSONB) - Corregido para PostgreSQL
CREATE INDEX idx_cliente ON cotizaciones USING GIN ((datos_generales->>'cliente') gin_trgm_ops);
CREATE INDEX idx_vendedor ON cotizaciones USING GIN ((datos_generales->>'vendedor') gin_trgm_ops);
CREATE INDEX idx_proyecto ON cotizaciones USING GIN ((datos_generales->>'proyecto') gin_trgm_ops);
CREATE INDEX idx_atencion_a ON cotizaciones USING GIN ((datos_generales->>'atencionA') gin_trgm_ops);
CREATE INDEX idx_contacto ON cotizaciones USING GIN ((datos_generales->>'contacto') gin_trgm_ops);

-- Búsqueda por fechas
CREATE INDEX idx_fecha_creacion ON cotizaciones(fecha_creacion);
CREATE INDEX idx_timestamp ON cotizaciones(timestamp);

-- Búsqueda combinada (para filtros múltiples)
CREATE INDEX idx_revision ON cotizaciones(revision);

-- Índices para PDFs
CREATE INDEX idx_pdf_cotizacion ON pdf_storage(cotizacion_id);
CREATE INDEX idx_pdf_numero ON pdf_storage(numero_cotizacion);

-- 4. FUNCIÓN PARA AUTO-UPDATE timestamp
-- =====================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para auto-update
CREATE TRIGGER update_cotizaciones_updated_at BEFORE UPDATE ON cotizaciones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pdf_storage_updated_at BEFORE UPDATE ON pdf_storage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. POLÍTICAS RLS (Row Level Security) - OPCIONAL
-- ================================================
-- Para futuro: control de acceso por usuario/empresa

-- ALTER TABLE cotizaciones ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pdf_storage ENABLE ROW LEVEL SECURITY;

-- 6. VISTAS ÚTILES PARA REPORTES
-- ==============================

-- Vista completa de cotizaciones con PDFs
CREATE VIEW cotizaciones_completas AS
SELECT 
    c.id,
    c.numero_cotizacion,
    c.datos_generales,
    c.items,
    c.revision,
    c.fecha_creacion,
    c.timestamp,
    c.usuario,
    c.observaciones,
    -- Info del PDF asociado
    p.id as pdf_id,
    p.file_size as pdf_size,
    p.cloudinary_url,
    p.google_drive_id,
    CASE 
        WHEN p.pdf_data IS NOT NULL THEN true 
        ELSE false 
    END as tiene_pdf
FROM cotizaciones c
LEFT JOIN pdf_storage p ON c.id = p.cotizacion_id;

-- Vista de estadísticas rápidas
CREATE VIEW estadisticas_cotizaciones AS
SELECT 
    COUNT(*) as total_cotizaciones,
    COUNT(DISTINCT datos_generales->>'cliente') as total_clientes,
    COUNT(DISTINCT datos_generales->>'vendedor') as total_vendedores,
    COUNT(DISTINCT datos_generales->>'proyecto') as total_proyectos,
    SUM(CASE WHEN revision > 1 THEN 1 ELSE 0 END) as total_revisiones,
    DATE_TRUNC('month', fecha_creacion) as mes
FROM cotizaciones
GROUP BY DATE_TRUNC('month', fecha_creacion)
ORDER BY mes DESC;

-- 7. COMENTARIOS DE DOCUMENTACIÓN
-- ===============================
COMMENT ON TABLE cotizaciones IS 'Tabla principal de cotizaciones CWS con datos en formato JSONB para flexibilidad';
COMMENT ON TABLE pdf_storage IS 'Almacenamiento de PDFs con múltiples opciones de backup';

COMMENT ON COLUMN cotizaciones.datos_generales IS 'JSON con cliente, vendedor, proyecto, atencionA, contacto, fecha, etc.';
COMMENT ON COLUMN cotizaciones.items IS 'Array JSON de items con materiales, cantidades, precios, subtotales';
COMMENT ON COLUMN cotizaciones.numero_cotizacion IS 'Formato: CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO';

COMMENT ON COLUMN pdf_storage.pdf_data IS 'PDF almacenado como datos binarios (BYTEA)';
COMMENT ON COLUMN pdf_storage.cloudinary_url IS 'URL de backup en Cloudinary (25GB gratis)';
COMMENT ON COLUMN pdf_storage.google_drive_id IS 'ID del archivo en Google Drive (fallback)';