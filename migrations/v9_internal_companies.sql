-- ============================================================
-- MIGRACIÓN v9: COMPAÑÍAS INTERNAS (sin cobro)
-- ============================================================
-- Marca las cuentas internas del desarrollador (CWS y Randulfo's) para que
-- tengan acceso completo a todas las features sin pago ni límites.
--
-- El flag lo consume cotizador/plans.effective_plan() → plan virtual 'internal'.
-- El billing y los webhooks de Stripe omiten el downgrade de estas cuentas.
--
-- IMPORTANTE: ajustar los slugs/nombres a los reales en Supabase si difieren.
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- ============================================================

ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS is_internal BOOLEAN NOT NULL DEFAULT false;

-- Respaldar con name ILIKE en caso de que el slug no coincida exactamente.
UPDATE public.companies
SET is_internal = true
WHERE slug IN ('cws-company', 'randulfos')
   OR name ILIKE '%cws%'
   OR name ILIKE '%randulfo%';
