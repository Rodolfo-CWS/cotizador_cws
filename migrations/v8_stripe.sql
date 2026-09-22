-- ============================================================
-- MIGRACIÓN v8: STRIPE — SUSCRIPCIONES
-- ============================================================
-- Columnas en public.companies para gestionar la suscripción de Stripe.
-- El plan de la empresa se sigue guardando en companies.plan; estas columnas
-- solo guardan el estado del cobro para el Customer Portal y los webhooks.
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- ============================================================

ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS stripe_customer_id    TEXT,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
    ADD COLUMN IF NOT EXISTS subscription_status   TEXT DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS trial_ends_at         TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS current_period_end    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fast_quote_pack_count INTEGER NOT NULL DEFAULT 0;
