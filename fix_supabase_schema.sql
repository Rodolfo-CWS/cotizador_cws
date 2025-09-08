-- =====================================================
-- SCRIPT DE CORRECCIÓN: ESQUEMA SUPABASE COMPLETO
-- =====================================================
-- Este script crea TODAS las tablas necesarias para que
-- la aplicación funcione correctamente con Supabase DB
--
-- EJECUTAR EN: Supabase Dashboard > SQL Editor > New query
-- =====================================================

-- 1. TABLA PRINCIPAL: cotizaciones
-- =====================================
-- INCLUYE LA COLUMNA CONDICIONES que falta en el esquema básico

CREATE TABLE IF NOT EXISTS cotizaciones (
    id SERIAL PRIMARY KEY,
    numero_cotizacion VARCHAR(255) UNIQUE NOT NULL,
    
    -- Datos generales como JSONB para flexibilidad
    datos_generales JSONB NOT NULL,
    
    -- Items de la cotización
    items JSONB NOT NULL,
    
    -- IMPORTANTE: Columna condiciones que falta en esquema básico
    condiciones JSONB DEFAULT '{}'::jsonb,
    
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

-- 2. TABLA DE CONTADORES ATÓMICOS
-- =====================================
-- Para numeración consecutiva irrepetible

CREATE TABLE IF NOT EXISTS cotizacion_counters (
    patron VARCHAR(100) PRIMARY KEY,
    ultimo_numero INTEGER DEFAULT 0,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. TABLA PDFs: pdf_storage
-- =====================================
-- Para almacenamiento de PDFs (aunque se usa Supabase Storage ahora)

CREATE TABLE IF NOT EXISTS pdf_storage (
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
    generator VARCHAR(50) DEFAULT 'reportlab',
    page_count INTEGER,
    
    -- Control
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. ÍNDICES BÁSICOS PARA PERFORMANCE
-- ====================================

-- Búsqueda por número de cotización (principal)
CREATE INDEX IF NOT EXISTS idx_numero_cotizacion ON cotizaciones(numero_cotizacion);

-- Búsqueda por fechas
CREATE INDEX IF NOT EXISTS idx_fecha_creacion ON cotizaciones(fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_timestamp ON cotizaciones(timestamp);

-- Búsqueda combinada
CREATE INDEX IF NOT EXISTS idx_revision ON cotizaciones(revision);

-- Índices para PDFs
CREATE INDEX IF NOT EXISTS idx_pdf_cotizacion ON pdf_storage(cotizacion_id);
CREATE INDEX IF NOT EXISTS idx_pdf_numero ON pdf_storage(numero_cotizacion);

-- Índice para contadores
CREATE INDEX IF NOT EXISTS idx_cotizacion_counters_patron ON cotizacion_counters(patron);

-- 5. FUNCIÓN PARA AUTO-UPDATE timestamp
-- =====================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. TRIGGERS PARA AUTO-UPDATE
-- =============================

-- Trigger para cotizaciones
DROP TRIGGER IF EXISTS update_cotizaciones_updated_at ON cotizaciones;
CREATE TRIGGER update_cotizaciones_updated_at 
    BEFORE UPDATE ON cotizaciones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger para PDF storage
DROP TRIGGER IF EXISTS update_pdf_storage_updated_at ON pdf_storage;
CREATE TRIGGER update_pdf_storage_updated_at 
    BEFORE UPDATE ON pdf_storage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger para contadores
DROP TRIGGER IF EXISTS update_cotizacion_counters_updated_at ON cotizacion_counters;
CREATE TRIGGER update_cotizacion_counters_updated_at
    BEFORE UPDATE ON cotizacion_counters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. VISTA COMPLETA DE COTIZACIONES
-- =================================

CREATE OR REPLACE VIEW cotizaciones_completas AS
SELECT 
    c.id,
    c.numero_cotizacion,
    c.datos_generales,
    c.items,
    c.condiciones,
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

-- 8. INSERTAR PATRONES DE EJEMPLO PARA CONTADORES
-- ===============================================

INSERT INTO cotizacion_counters (patron, ultimo_numero, descripcion) 
VALUES 
    ('CLIENTE-CWS-RM', 0, 'Roberto Martinez - Patrón general'),
    ('BMWTEST-CWS-RM', 0, 'BMW Test - Patrón específico'),
    ('DEMO-CWS-XX', 0, 'Demo - Patrón genérico'),
    ('TEST-CWS-XX', 0, 'Testing - Patrón de pruebas')
ON CONFLICT (patron) DO NOTHING;

-- 9. COMENTARIOS DE DOCUMENTACIÓN
-- ===============================

COMMENT ON TABLE cotizaciones IS 'Tabla principal de cotizaciones CWS con soporte completo para condiciones';
COMMENT ON TABLE cotizacion_counters IS 'Contadores atómicos para numeración consecutiva irrepetible';
COMMENT ON TABLE pdf_storage IS 'Almacenamiento de PDFs con múltiples opciones de backup';

COMMENT ON COLUMN cotizaciones.datos_generales IS 'JSON con cliente, vendedor, proyecto, atencionA, contacto, fecha, etc.';
COMMENT ON COLUMN cotizaciones.items IS 'Array JSON de items con materiales, cantidades, precios, subtotales';
COMMENT ON COLUMN cotizaciones.condiciones IS 'JSON con condiciones comerciales: moneda, tipoCambio, tiempoEntrega, etc.';
COMMENT ON COLUMN cotizaciones.numero_cotizacion IS 'Formato: CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO';

COMMENT ON COLUMN cotizacion_counters.patron IS 'Patrón base del número: CLIENTE-CWS-INICIALES';
COMMENT ON COLUMN cotizacion_counters.ultimo_numero IS 'Último número consecutivo usado (atómico)';

-- 10. VERIFICACIÓN FINAL
-- ======================

-- Verificar que todas las tablas se crearon
SELECT 
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name IN ('cotizaciones', 'cotizacion_counters', 'pdf_storage')
ORDER BY table_name;

-- Verificar estructura de cotizaciones (incluyendo condiciones)
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'cotizaciones'
    AND table_schema = 'public'
ORDER BY ordinal_position;

-- ✅ SCRIPT COMPLETO LISTO
-- =========================
-- Después de ejecutar este script, la aplicación debería:
-- 1. Conectarse exitosamente a Supabase DB (modo_offline = False)
-- 2. Guardar cotizaciones en PostgreSQL
-- 3. Mantener funcionamiento de Supabase Storage para PDFs
-- 4. Tener numeración consecutiva garantizada