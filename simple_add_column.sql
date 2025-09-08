-- MÉTODO SIMPLE Y DIRECTO
-- Ejecutar línea por línea en Supabase Dashboard

-- 1. Verificar columnas actuales
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'cotizaciones' AND table_schema = 'public' 
ORDER BY column_name;

-- 2. Agregar columna (ejecutar solo esta línea)
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS condiciones JSONB DEFAULT '{}';

-- 3. Verificar que se agregó
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'cotizaciones' AND column_name = 'condiciones';