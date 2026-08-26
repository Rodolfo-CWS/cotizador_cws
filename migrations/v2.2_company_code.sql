-- ============================================================
-- MIGRACIÓN v2.2: CÓDIGO DE COMPAÑÍA + LEGACY DRIVE IMPORT
-- ============================================================
-- Agrega a public.companies:
-- - codigo: código corto usado en el folio de cotización
--           (CLIENTE-<codigo>-VENDEDOR-###-R#-PROYECTO)
-- - legacy_drive_import: flag para gatear la importación de
--           cotizaciones antiguas desde Google Drive
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- Precaución: Hacer backup antes de ejecutar
-- ============================================================

-- 1. Código corto de compañía (folio de cotización)
ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS codigo VARCHAR(50);

-- Índice único parcial: permite múltiples NULL, pero exige unicidad
-- entre los códigos asignados (evita colisiones entre tenants).
CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_codigo
    ON public.companies (codigo)
    WHERE codigo IS NOT NULL;

-- 2. Flag para importación legacy de Google Drive
ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS legacy_drive_import BOOLEAN DEFAULT false;

-- 3. Seed: CWS Company conserva su código histórico y el import legacy
UPDATE public.companies
SET codigo = 'CWS',
    legacy_drive_import = true
WHERE slug = 'cws-company';
