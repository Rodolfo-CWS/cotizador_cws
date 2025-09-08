-- =====================================================
-- ESQUEMA DE BASE DE DATOS PARA ANÁLISIS BOM
-- Sistema CWS - Análisis de PDFs con Gemini AI
-- =====================================================

-- Tabla principal de análisis BOM
-- Almacena información general de cada análisis de PDF
CREATE TABLE IF NOT EXISTS bom_analysis (
    id SERIAL PRIMARY KEY,
    numero_cotizacion VARCHAR(255),
    ruta_pdf TEXT NOT NULL,
    nombre_archivo VARCHAR(500),
    fecha_analisis TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_paginas INTEGER DEFAULT 0,
    total_items_encontrados INTEGER DEFAULT 0,
    total_items_unicos INTEGER DEFAULT 0,
    total_items_consolidados INTEGER DEFAULT 0,
    paginas_con_tablas INTEGER DEFAULT 0,
    estado_analisis VARCHAR(50) DEFAULT 'pendiente', -- pendiente, procesando, completado, error
    tiempo_procesamiento_segundos INTEGER,
    errores_analisis TEXT[],
    exito BOOLEAN DEFAULT false,
    
    -- Totales generales del BOM
    total_cantidad_items DECIMAL(15,4) DEFAULT 0,
    total_area_mm2 DECIMAL(20,4) DEFAULT 0,
    total_volumen_mm3 DECIMAL(20,4) DEFAULT 0,
    
    -- Metadatos adicionales
    tamaño_archivo_bytes BIGINT,
    gemini_model_version VARCHAR(100),
    configuracion_analisis JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Índices para búsqueda rápida
    CONSTRAINT unique_cotizacion_pdf UNIQUE(numero_cotizacion, ruta_pdf)
);

-- Tabla de items BOM individuales
-- Almacena cada item extraído de las tablas de materiales
CREATE TABLE IF NOT EXISTS bom_items (
    id SERIAL PRIMARY KEY,
    bom_analysis_id INTEGER REFERENCES bom_analysis(id) ON DELETE CASCADE,
    
    -- Información del item
    item_id VARCHAR(255) NOT NULL,
    cantidad DECIMAL(15,4) NOT NULL DEFAULT 0,
    udm VARCHAR(50), -- Unidad de medida
    descripcion TEXT,
    
    -- Dimensiones
    largo_mm DECIMAL(15,4),
    ancho_mm DECIMAL(15,4),
    espesor_mm DECIMAL(15,4),
    
    -- Clasificación y origen
    clasificacion VARCHAR(255),
    pagina_origen INTEGER NOT NULL,
    
    -- Subtotales dimensionales calculados
    area_unitaria_mm2 DECIMAL(20,4),
    area_total_mm2 DECIMAL(20,4),
    volumen_unitario_mm3 DECIMAL(20,4),
    volumen_total_mm3 DECIMAL(20,4),
    
    -- Consolidación
    key_consolidacion VARCHAR(500), -- Clave para identificar items similares
    es_consolidado BOOLEAN DEFAULT false,
    cantidad_consolidada DECIMAL(15,4) DEFAULT 0,
    ocurrencias INTEGER DEFAULT 1, -- Cuántas veces aparece este item
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de páginas analizadas
-- Detalle por página del análisis
CREATE TABLE IF NOT EXISTS bom_pages (
    id SERIAL PRIMARY KEY,
    bom_analysis_id INTEGER REFERENCES bom_analysis(id) ON DELETE CASCADE,
    numero_pagina INTEGER NOT NULL,
    tabla_detectada BOOLEAN DEFAULT false,
    items_encontrados INTEGER DEFAULT 0,
    contenido_texto_preview TEXT, -- Preview del contenido de texto
    errores_pagina TEXT[],
    tiempo_procesamiento_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_analysis_page UNIQUE(bom_analysis_id, numero_pagina)
);

-- Tabla de materiales consolidados (Grand Total)
-- Resultado final después de consolidación y suma
CREATE TABLE IF NOT EXISTS bom_consolidated (
    id SERIAL PRIMARY KEY,
    bom_analysis_id INTEGER REFERENCES bom_analysis(id) ON DELETE CASCADE,
    
    -- Información consolidada del material
    item_id VARCHAR(255) NOT NULL,
    descripcion TEXT,
    clasificacion VARCHAR(255),
    
    -- Cantidades totales
    cantidad_total DECIMAL(15,4) NOT NULL,
    udm VARCHAR(50),
    
    -- Dimensiones estándar
    largo_mm DECIMAL(15,4),
    ancho_mm DECIMAL(15,4),
    espesor_mm DECIMAL(15,4),
    
    -- Totales dimensionales
    area_total_mm2 DECIMAL(20,4),
    volumen_total_mm3 DECIMAL(20,4),
    
    -- Información de consolidación
    ocurrencias_en_pdf INTEGER DEFAULT 1,
    paginas_origen INTEGER[],
    es_material_repetido BOOLEAN DEFAULT false,
    
    -- Orden para mostrar (más repetidos primero)
    orden_importancia INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de clasificaciones de materiales
-- Para agrupar materiales por tipo
CREATE TABLE IF NOT EXISTS bom_classifications (
    id SERIAL PRIMARY KEY,
    bom_analysis_id INTEGER REFERENCES bom_analysis(id) ON DELETE CASCADE,
    nombre_clasificacion VARCHAR(255) NOT NULL,
    
    -- Totales por clasificación
    total_items INTEGER DEFAULT 0,
    total_cantidad DECIMAL(15,4) DEFAULT 0,
    total_area_mm2 DECIMAL(20,4) DEFAULT 0,
    total_volumen_mm3 DECIMAL(20,4) DEFAULT 0,
    
    -- Porcentajes del total
    porcentaje_items DECIMAL(5,2) DEFAULT 0,
    porcentaje_cantidad DECIMAL(5,2) DEFAULT 0,
    porcentaje_area DECIMAL(5,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_analysis_classification UNIQUE(bom_analysis_id, nombre_clasificacion)
);

-- =====================================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- =====================================================

-- Índices para bom_analysis
CREATE INDEX IF NOT EXISTS idx_bom_analysis_cotizacion ON bom_analysis(numero_cotizacion);
CREATE INDEX IF NOT EXISTS idx_bom_analysis_fecha ON bom_analysis(fecha_analisis);
CREATE INDEX IF NOT EXISTS idx_bom_analysis_estado ON bom_analysis(estado_analisis);

-- Índices para bom_items
CREATE INDEX IF NOT EXISTS idx_bom_items_analysis ON bom_items(bom_analysis_id);
CREATE INDEX IF NOT EXISTS idx_bom_items_item_id ON bom_items(item_id);
CREATE INDEX IF NOT EXISTS idx_bom_items_clasificacion ON bom_items(clasificacion);
CREATE INDEX IF NOT EXISTS idx_bom_items_consolidacion ON bom_items(key_consolidacion);

-- Índices para bom_consolidated
CREATE INDEX IF NOT EXISTS idx_bom_consolidated_analysis ON bom_consolidated(bom_analysis_id);
CREATE INDEX IF NOT EXISTS idx_bom_consolidated_clasificacion ON bom_consolidated(clasificacion);
CREATE INDEX IF NOT EXISTS idx_bom_consolidated_importancia ON bom_consolidated(orden_importancia);

-- =====================================================
-- FUNCIONES Y TRIGGERS
-- =====================================================

-- Función para actualizar timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para actualizar timestamps
CREATE TRIGGER update_bom_analysis_updated_at 
    BEFORE UPDATE ON bom_analysis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bom_items_updated_at 
    BEFORE UPDATE ON bom_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bom_consolidated_updated_at 
    BEFORE UPDATE ON bom_consolidated
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- POLÍTICAS DE SEGURIDAD (RLS)
-- =====================================================

-- Habilitar RLS en las tablas
ALTER TABLE bom_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE bom_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE bom_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE bom_consolidated ENABLE ROW LEVEL SECURITY;
ALTER TABLE bom_classifications ENABLE ROW LEVEL SECURITY;

-- Política básica: permitir todo por ahora (ajustar según necesidades)
CREATE POLICY "Allow all operations" ON bom_analysis FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON bom_items FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON bom_pages FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON bom_consolidated FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON bom_classifications FOR ALL USING (true);

-- =====================================================
-- VISTAS ÚTILES
-- =====================================================

-- Vista resumen de análisis BOM
CREATE OR REPLACE VIEW v_bom_analysis_summary AS
SELECT 
    ba.id,
    ba.numero_cotizacion,
    ba.nombre_archivo,
    ba.fecha_analisis,
    ba.estado_analisis,
    ba.total_paginas,
    ba.total_items_encontrados,
    ba.total_items_consolidados,
    ba.total_cantidad_items,
    ba.total_area_mm2,
    ba.total_volumen_mm3,
    ba.exito,
    COUNT(DISTINCT bc.id) as materiales_consolidados,
    COUNT(DISTINCT bcl.id) as clasificaciones
FROM bom_analysis ba
LEFT JOIN bom_consolidated bc ON ba.id = bc.bom_analysis_id
LEFT JOIN bom_classifications bcl ON ba.id = bcl.bom_analysis_id
GROUP BY ba.id, ba.numero_cotizacion, ba.nombre_archivo, ba.fecha_analisis, 
         ba.estado_analisis, ba.total_paginas, ba.total_items_encontrados, 
         ba.total_items_consolidados, ba.total_cantidad_items, 
         ba.total_area_mm2, ba.total_volumen_mm3, ba.exito;

-- Vista de materiales más utilizados
CREATE OR REPLACE VIEW v_materials_ranking AS
SELECT 
    item_id,
    descripcion,
    clasificacion,
    SUM(cantidad_total) as cantidad_total_global,
    SUM(area_total_mm2) as area_total_global,
    COUNT(DISTINCT bom_analysis_id) as apariciones_en_cotizaciones,
    AVG(ocurrencias_en_pdf) as promedio_repeticiones_por_pdf
FROM bom_consolidated
GROUP BY item_id, descripcion, clasificacion
ORDER BY cantidad_total_global DESC, apariciones_en_cotizaciones DESC;

-- =====================================================
-- COMENTARIOS DE DOCUMENTACIÓN
-- =====================================================

COMMENT ON TABLE bom_analysis IS 'Análisis principal de PDFs con información BOM extraída por Gemini AI';
COMMENT ON TABLE bom_items IS 'Items individuales extraídos de las tablas de materiales en cada página';
COMMENT ON TABLE bom_pages IS 'Información detallada del análisis por página';
COMMENT ON TABLE bom_consolidated IS 'Materiales consolidados después del proceso de suma y clasificación';
COMMENT ON TABLE bom_classifications IS 'Agrupación de materiales por tipo/clasificación';

COMMENT ON COLUMN bom_analysis.estado_analisis IS 'Estados: pendiente, procesando, completado, error';
COMMENT ON COLUMN bom_items.key_consolidacion IS 'Clave única para identificar materiales similares';
COMMENT ON COLUMN bom_consolidated.orden_importancia IS 'Orden de importancia (materiales más repetidos tienen mayor valor)';

-- =====================================================
-- DATOS INICIALES DE PRUEBA (OPCIONAL)
-- =====================================================

-- Las clasificaciones comunes se crearán cuando se hagan análisis reales
-- No se insertan datos de ejemplo para evitar errores de foreign key

-- =====================================================
-- FINALIZACIÓN
-- =====================================================

-- Mensaje de confirmación
DO $$
BEGIN
    RAISE NOTICE 'Esquema BOM creado exitosamente';
    RAISE NOTICE 'Tablas: bom_analysis, bom_items, bom_pages, bom_consolidated, bom_classifications';
    RAISE NOTICE 'Vistas: v_bom_analysis_summary, v_materials_ranking';
    RAISE NOTICE 'Configuración RLS: Activada con política permisiva';
END
$$;