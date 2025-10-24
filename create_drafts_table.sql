-- ========================================
-- TABLA DE DRAFTS (BORRADORES) - SUPABASE
-- ========================================
-- Este script crea la tabla necesaria para el sistema de borradores
-- Ejecutar en el SQL Editor de Supabase Dashboard

-- Crear tabla de drafts
CREATE TABLE IF NOT EXISTS public.drafts (
    id TEXT PRIMARY KEY,
    vendedor TEXT NOT NULL,
    nombre TEXT NOT NULL,
    datos JSONB NOT NULL,
    timestamp BIGINT NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ultima_modificacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Crear índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_drafts_vendedor ON public.drafts(vendedor);
CREATE INDEX IF NOT EXISTS idx_drafts_timestamp ON public.drafts(timestamp);
CREATE INDEX IF NOT EXISTS idx_drafts_ultima_modificacion ON public.drafts(ultima_modificacion DESC);

-- Habilitar Row Level Security (RLS) - opcional
ALTER TABLE public.drafts ENABLE ROW LEVEL SECURITY;

-- Política de acceso público (ajustar según necesidades de seguridad)
-- NOTA: En producción, deberías crear políticas más restrictivas basadas en usuarios
CREATE POLICY "Permitir acceso público a drafts" ON public.drafts
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Comentarios de documentación
COMMENT ON TABLE public.drafts IS 'Borradores de cotizaciones pendientes de completar';
COMMENT ON COLUMN public.drafts.id IS 'Identificador único del borrador (formato: draft_timestamp)';
COMMENT ON COLUMN public.drafts.vendedor IS 'Iniciales del vendedor propietario del borrador';
COMMENT ON COLUMN public.drafts.nombre IS 'Nombre descriptivo del borrador (Cliente - Proyecto)';
COMMENT ON COLUMN public.drafts.datos IS 'Datos completos del borrador en formato JSON';
COMMENT ON COLUMN public.drafts.timestamp IS 'Timestamp en milisegundos para ordenamiento';
COMMENT ON COLUMN public.drafts.fecha_creacion IS 'Fecha y hora de creación del borrador';
COMMENT ON COLUMN public.drafts.ultima_modificacion IS 'Fecha y hora de última modificación';

-- Verificar que la tabla se creó correctamente
SELECT
    'Tabla drafts creada exitosamente' AS mensaje,
    COUNT(*) AS registros_actuales
FROM public.drafts;
