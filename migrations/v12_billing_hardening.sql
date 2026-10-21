-- ============================================================
-- MIGRACIÓN v12: ENDURECIMIENTO DEL BILLING DE STRIPE
-- ============================================================
-- Prepara el billing para cobrar a clientes reales:
--   1. Créditos one-time del paquete Fast Quote (se gastan, no son mensuales).
--   2. Tabla de eventos del webhook (deduplicación / idempotencia).
--   3. Índices únicos sobre los ids de Stripe (evita duplicados + acelera lookups).
--
-- Aditiva y segura: la columna nueva tiene default 0 y hoy ninguna empresa
-- tiene ids de Stripe guardados, así que los índices parciales no fallan.
--
-- Ejecutar en: SQL Editor de Supabase Dashboard, ANTES del deploy.
-- ============================================================

-- Créditos one-time del paquete Fast Quote
ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS fast_quote_credits_remaining INTEGER NOT NULL DEFAULT 0;

-- Deduplicación de eventos del webhook (idempotencia)
CREATE TABLE IF NOT EXISTS public.stripe_events (
    id           TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.stripe_events ENABLE ROW LEVEL SECURITY;

-- Índices únicos para ids de Stripe (evita duplicados + acelera lookups)
CREATE UNIQUE INDEX IF NOT EXISTS companies_stripe_customer_id_uniq
    ON public.companies (stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS companies_stripe_subscription_id_uniq
    ON public.companies (stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;
