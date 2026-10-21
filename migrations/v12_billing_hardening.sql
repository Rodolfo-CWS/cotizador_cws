-- ============================================================
-- MIGRACIÓN v12: ENDURECIMIENTO DEL BILLING DE STRIPE
-- ============================================================
-- Prepara el billing para cobrar a clientes reales:
--   1. Créditos one-time del paquete Fast Quote (se gastan, no son mensuales).
--   2. Tabla de eventos del webhook (deduplicación / idempotencia).
--   3. Índices únicos sobre los ids de Stripe (evita duplicados + acelera lookups).
--   4. Funciones para sumar/restar créditos en un solo UPDATE (el SDK las llama
--      por RPC cuando PostgreSQL directo no está disponible).
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

-- Incrementos atómicos de créditos Fast Quote.
-- El webhook y el consumo de cuota los llaman por RPC cuando PostgreSQL
-- directo no está disponible (el SDK no puede hacer col = col + 1).
-- SECURITY INVOKER: mismo permiso que un UPDATE directo sobre companies.
CREATE OR REPLACE FUNCTION public.consumir_credito_fast_quote(p_company_id UUID)
RETURNS INTEGER
LANGUAGE sql
AS $$
    UPDATE public.companies
    SET fast_quote_credits_remaining = GREATEST(
        COALESCE(fast_quote_credits_remaining, 0) - 1, 0
    )
    WHERE id = p_company_id
      AND COALESCE(fast_quote_credits_remaining, 0) > 0
    RETURNING fast_quote_credits_remaining;
$$;

CREATE OR REPLACE FUNCTION public.acreditar_paquete_fast_quote(
    p_company_id UUID,
    p_credits INTEGER
)
RETURNS TABLE (
    id UUID,
    fast_quote_pack_count INTEGER,
    fast_quote_credits_remaining INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    UPDATE public.companies AS c
    SET fast_quote_pack_count = COALESCE(c.fast_quote_pack_count, 0) + 1,
        fast_quote_credits_remaining =
            COALESCE(c.fast_quote_credits_remaining, 0) + COALESCE(p_credits, 0)
    WHERE c.id = p_company_id
    RETURNING c.id, c.fast_quote_pack_count, c.fast_quote_credits_remaining;
END;
$$;

-- Solo el service role (webhook / backend) puede ejecutarlas. El rol de
-- DATABASE_URL es owner y sigue pudiendo llamarlas. anon/authenticated no.
DO $$
DECLARE
    fn text;
BEGIN
    FOREACH fn IN ARRAY ARRAY[
        'public.consumir_credito_fast_quote(UUID)',
        'public.acreditar_paquete_fast_quote(UUID, INTEGER)'
    ]
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', fn);
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', fn);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', fn);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', fn);
        END IF;
    END LOOP;
END $$;
