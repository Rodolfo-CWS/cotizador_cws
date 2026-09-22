-- ============================================================
-- MIGRACIÓN v7: PLANES POR TIERS DE VALOR (starter/pro/business)
-- ============================================================
-- Reemplaza los "silos" de features (pdf / fast_quote / full) por tiers de
-- valor. El plan 'full' y 'fast_quote' se mapean a 'pro'; 'pdf' a 'starter'.
--
-- Los valores de plan deben coincidir con cotizador/plans.py (VALID_PLANS).
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- ============================================================

-- 1. Quitar el CHECK viejo (si no, el backfill a 'starter'/'pro' lo violaría).
ALTER TABLE public.companies
    DROP CONSTRAINT IF EXISTS companies_plan_check;

-- 2. Backfill: mapear planes legacy a los nuevos.
UPDATE public.companies SET plan = 'starter' WHERE plan = 'pdf';
UPDATE public.companies SET plan = 'pro'     WHERE plan IN ('fast_quote', 'full');

-- 3. Recrear el CHECK con los nuevos valores.
ALTER TABLE public.companies
    ADD CONSTRAINT companies_plan_check CHECK (plan IN ('starter', 'pro', 'business'));

-- 4. Default nuevo: toda empresa nueva arranca en Starter (freemium).
ALTER TABLE public.companies ALTER COLUMN plan SET DEFAULT 'starter';
