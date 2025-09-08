-- =====================================================
-- AGREGAR COLUMNA CONDICIONES FALTANTE
-- =====================================================
-- Ejecutar en: Supabase Dashboard > SQL Editor

-- Agregar la columna condiciones que falta
ALTER TABLE cotizaciones ADD COLUMN condiciones JSONB DEFAULT '{}'::jsonb;

-- Crear comentario para documentar
COMMENT ON COLUMN cotizaciones.condiciones IS 'JSON con condiciones comerciales: moneda, tipoCambio, tiempoEntrega, terminos, etc.';

-- Verificar que se agregó correctamente
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'cotizaciones' 
  AND column_name = 'condiciones'
  AND table_schema = 'public';

-- ✅ Después de esto, la aplicación debería funcionar