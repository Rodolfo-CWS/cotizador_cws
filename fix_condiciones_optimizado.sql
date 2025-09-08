-- =====================================================
-- FIX OPTIMIZADO: AGREGAR COLUMNA CONDICIONES
-- =====================================================
-- Ejecutar en: Supabase Dashboard > SQL Editor > New query
-- Este script está optimizado para evitar timeouts

-- 1. VERIFICAR SI LA COLUMNA YA EXISTE
SELECT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'cotizaciones' 
    AND column_name = 'condiciones'
    AND table_schema = 'public'
) as condiciones_existe;

-- 2. AGREGAR LA COLUMNA SOLO SI NO EXISTE (evita errores)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cotizaciones' 
        AND column_name = 'condiciones' 
        AND table_schema = 'public'
    ) THEN
        -- Agregar columna con valor por defecto
        ALTER TABLE cotizaciones ADD COLUMN condiciones JSONB DEFAULT '{}'::jsonb;
        
        -- Agregar comentario
        COMMENT ON COLUMN cotizaciones.condiciones IS 'JSON con condiciones comerciales: moneda, tipoCambio, tiempoEntrega, terminos, etc.';
        
        RAISE NOTICE 'Columna condiciones agregada exitosamente';
    ELSE
        RAISE NOTICE 'Columna condiciones ya existe';
    END IF;
END
$$;

-- 3. VERIFICAR EL RESULTADO
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'cotizaciones' 
  AND column_name = 'condiciones'
  AND table_schema = 'public';

-- 4. CONTAR REGISTROS EN LA TABLA (para verificar tamaño)
SELECT COUNT(*) as total_cotizaciones FROM cotizaciones;

-- ✅ Si ves la columna condiciones con tipo jsonb, el fix funcionó