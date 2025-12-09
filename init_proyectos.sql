-- ============================================
-- MÓDULO DE ÓRDENES DE COMPRA Y PROYECTOS
-- Script de Inicialización para Supabase
-- ============================================

-- Tabla 1: Órdenes de Compra
CREATE TABLE IF NOT EXISTS ordenes_compra (
    id SERIAL PRIMARY KEY,
    numero_oc TEXT UNIQUE NOT NULL,
    cliente TEXT NOT NULL,
    fecha_recepcion DATE NOT NULL DEFAULT CURRENT_DATE,
    monto_total DECIMAL(12,2) NOT NULL,
    moneda TEXT DEFAULT 'MXN' CHECK (moneda IN ('MXN', 'USD')),
    archivo_pdf TEXT,  -- URL del PDF en Supabase Storage
    estatus TEXT DEFAULT 'activa' CHECK (estatus IN ('activa', 'en_proceso', 'completada', 'cancelada')),
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla 2: Proyectos (vinculados a OCs)
CREATE TABLE IF NOT EXISTS proyectos (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    oc_id INTEGER NOT NULL REFERENCES ordenes_compra(id) ON DELETE CASCADE,
    fecha_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
    monto_presupuestado DECIMAL(12,2) NOT NULL,
    estatus TEXT DEFAULT 'activo' CHECK (estatus IN ('activo', 'completado', 'pausado', 'cancelado')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(oc_id)  -- Una OC = Un Proyecto
);

-- Tabla 3: Gastos del Proyecto
CREATE TABLE IF NOT EXISTS gastos_proyecto (
    id SERIAL PRIMARY KEY,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    concepto TEXT NOT NULL,
    proveedor TEXT,
    cantidad DECIMAL(10,2) NOT NULL DEFAULT 1,
    unidad TEXT DEFAULT 'pieza',
    precio_unitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
    aprobado BOOLEAN DEFAULT FALSE,
    aprobado_por TEXT,
    fecha_aprobacion TIMESTAMP WITH TIME ZONE,
    estatus_compra TEXT DEFAULT 'pendiente' CHECK (estatus_compra IN ('pendiente', 'ordenado', 'recibido', 'cancelado')),
    fecha_orden DATE,
    numero_orden TEXT,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla 4: Notificaciones In-App
CREATE TABLE IF NOT EXISTS notificaciones (
    id SERIAL PRIMARY KEY,
    usuario_destinatario TEXT NOT NULL,  -- Nombre del usuario que recibe la notificación
    tipo TEXT NOT NULL CHECK (tipo IN ('gasto_pendiente', 'gasto_aprobado', 'gasto_rechazado', 'oc_nueva', 'presupuesto_excedido', 'gasto_ordenado', 'gasto_recibido')),
    titulo TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    enlace TEXT,  -- URL para ir directamente al recurso
    leida BOOLEAN DEFAULT FALSE,
    metadata JSONB,  -- Datos adicionales (proyecto_id, gasto_id, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- ÍNDICES PARA MEJORAR PERFORMANCE
-- ============================================

-- Índices para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_ordenes_compra_cliente ON ordenes_compra(cliente);
CREATE INDEX IF NOT EXISTS idx_ordenes_compra_estatus ON ordenes_compra(estatus);
CREATE INDEX IF NOT EXISTS idx_ordenes_compra_fecha ON ordenes_compra(fecha_recepcion DESC);

CREATE INDEX IF NOT EXISTS idx_proyectos_oc_id ON proyectos(oc_id);
CREATE INDEX IF NOT EXISTS idx_proyectos_estatus ON proyectos(estatus);

CREATE INDEX IF NOT EXISTS idx_gastos_proyecto_id ON gastos_proyecto(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_gastos_aprobado ON gastos_proyecto(aprobado);
CREATE INDEX IF NOT EXISTS idx_gastos_estatus_compra ON gastos_proyecto(estatus_compra);

CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario ON notificaciones(usuario_destinatario);
CREATE INDEX IF NOT EXISTS idx_notificaciones_leida ON notificaciones(leida);
CREATE INDEX IF NOT EXISTS idx_notificaciones_fecha ON notificaciones(created_at DESC);

-- ============================================
-- FUNCIONES Y TRIGGERS
-- ============================================

-- Función: Actualizar timestamp updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger: Actualizar updated_at en ordenes_compra
CREATE TRIGGER update_ordenes_compra_updated_at
    BEFORE UPDATE ON ordenes_compra
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Actualizar updated_at en proyectos
CREATE TRIGGER update_proyectos_updated_at
    BEFORE UPDATE ON proyectos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Actualizar updated_at en gastos_proyecto
CREATE TRIGGER update_gastos_proyecto_updated_at
    BEFORE UPDATE ON gastos_proyecto
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VISTAS ÚTILES
-- ============================================

-- Vista: Resumen de Proyectos con cálculos financieros
CREATE OR REPLACE VIEW vista_resumen_proyectos AS
SELECT
    p.id,
    p.nombre,
    p.estatus,
    oc.numero_oc,
    oc.cliente,
    p.monto_presupuestado,
    COALESCE(SUM(g.subtotal) FILTER (WHERE g.aprobado = TRUE), 0) AS monto_gastado,
    p.monto_presupuestado - COALESCE(SUM(g.subtotal) FILTER (WHERE g.aprobado = TRUE), 0) AS monto_disponible,
    COUNT(g.id) AS total_gastos,
    COUNT(g.id) FILTER (WHERE g.aprobado = TRUE) AS gastos_aprobados,
    COUNT(g.id) FILTER (WHERE g.estatus_compra = 'ordenado') AS gastos_ordenados,
    COUNT(g.id) FILTER (WHERE g.estatus_compra = 'recibido') AS gastos_recibidos,
    CASE
        WHEN COUNT(g.id) = 0 THEN 0
        ELSE ROUND((COUNT(g.id) FILTER (WHERE g.estatus_compra = 'recibido')::NUMERIC / COUNT(g.id)) * 100, 1)
    END AS progreso_porcentaje,
    p.fecha_inicio,
    p.created_at
FROM proyectos p
LEFT JOIN ordenes_compra oc ON p.oc_id = oc.id
LEFT JOIN gastos_proyecto g ON p.id = g.proyecto_id
GROUP BY p.id, p.nombre, p.estatus, oc.numero_oc, oc.cliente, p.monto_presupuestado, p.fecha_inicio, p.created_at;

-- Vista: Gastos pendientes de aprobación
CREATE OR REPLACE VIEW vista_gastos_pendientes AS
SELECT
    g.id,
    g.concepto,
    g.proveedor,
    g.subtotal,
    p.nombre AS proyecto_nombre,
    oc.numero_oc,
    oc.cliente,
    g.created_at,
    EXTRACT(EPOCH FROM (NOW() - g.created_at)) / 3600 AS horas_pendiente
FROM gastos_proyecto g
INNER JOIN proyectos p ON g.proyecto_id = p.id
INNER JOIN ordenes_compra oc ON p.oc_id = oc.id
WHERE g.aprobado = FALSE
ORDER BY g.created_at ASC;

-- ============================================
-- DATOS INICIALES (OPCIONAL - PARA TESTING)
-- ============================================

-- Puedes descomentar estas líneas para crear datos de prueba:
/*
INSERT INTO ordenes_compra (numero_oc, cliente, monto_total, moneda, notas) VALUES
('BMW-2024-001', 'BMW', 150000.00, 'MXN', 'Renovación de instalaciones'),
('TESLA-2024-001', 'Tesla', 89500.00, 'MXN', 'Expansión de planta');

INSERT INTO proyectos (nombre, oc_id, monto_presupuestado) VALUES
('BMW Renovación Instalaciones', 1, 150000.00),
('Tesla Expansión Planta', 2, 89500.00);

INSERT INTO gastos_proyecto (proyecto_id, concepto, proveedor, cantidad, unidad, precio_unitario, aprobado) VALUES
(1, 'Tubería de cobre 1/2"', 'Ferretería ABC', 50, 'metros', 45.00, TRUE),
(1, 'Cable eléctrico calibre 12', 'Eléctricos del Norte', 200, 'metros', 18.50, FALSE);
*/

-- ============================================
-- COMENTARIOS EN TABLAS Y COLUMNAS
-- ============================================

COMMENT ON TABLE ordenes_compra IS 'Órdenes de compra recibidas de clientes';
COMMENT ON TABLE proyectos IS 'Proyectos vinculados automáticamente a órdenes de compra';
COMMENT ON TABLE gastos_proyecto IS 'Gastos/compras asociados a cada proyecto';
COMMENT ON TABLE notificaciones IS 'Sistema de notificaciones in-app para usuarios';

COMMENT ON COLUMN gastos_proyecto.subtotal IS 'Calculado automáticamente como cantidad * precio_unitario';
COMMENT ON COLUMN notificaciones.metadata IS 'JSON con datos adicionales según el tipo de notificación';

-- ============================================
-- PERMISOS (AJUSTAR SEGÚN TUS NECESIDADES)
-- ============================================

-- Para desarrollo local, puedes usar permisos amplios
-- En producción, ajusta según tus políticas de Row Level Security (RLS)

-- Ejemplo de políticas RLS (descomenta si usas autenticación de Supabase):
/*
ALTER TABLE ordenes_compra ENABLE ROW LEVEL SECURITY;
ALTER TABLE proyectos ENABLE ROW LEVEL SECURITY;
ALTER TABLE gastos_proyecto ENABLE ROW LEVEL SECURITY;
ALTER TABLE notificaciones ENABLE ROW LEVEL SECURITY;

-- Política: Usuarios autenticados pueden ver/editar todo
CREATE POLICY "Permitir todo a usuarios autenticados" ON ordenes_compra
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Permitir todo a usuarios autenticados" ON proyectos
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Permitir todo a usuarios autenticados" ON gastos_proyecto
    FOR ALL USING (auth.role() = 'authenticated');

-- Política: Usuarios solo ven sus propias notificaciones
CREATE POLICY "Usuarios ven solo sus notificaciones" ON notificaciones
    FOR SELECT USING (usuario_destinatario = current_setting('request.jwt.claims', true)::json->>'email');
*/

-- ============================================
-- FIN DEL SCRIPT
-- ============================================

-- Para ejecutar este script en Supabase:
-- 1. Ve a SQL Editor en tu dashboard de Supabase
-- 2. Copia y pega este script completo
-- 3. Click en "Run" o presiona Ctrl+Enter
-- 4. Verifica que todas las tablas se crearon correctamente en "Table Editor"

SELECT 'Módulo de Proyectos inicializado correctamente' AS mensaje;
