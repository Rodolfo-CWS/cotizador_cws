-- Migración: Agregar columna referencia_oc a la tabla cotizaciones
-- Fecha: 2026-01-13
-- Descripción: Agrega campo opcional para referenciar órdenes de compra

-- Agregar columna referencia_oc (opcional, puede ser NULL)
ALTER TABLE cotizaciones
ADD COLUMN IF NOT EXISTS referencia_oc TEXT;

-- Agregar comentario a la columna para documentación
COMMENT ON COLUMN cotizaciones.referencia_oc IS 'Referencia opcional a la orden de compra original (ej: OC-2025-001)';

-- Verificar que la columna fue agregada exitosamente
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'cotizaciones' AND column_name = 'referencia_oc';
