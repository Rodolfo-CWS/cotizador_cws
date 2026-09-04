-- ============================================================
-- MIGRACIÓN v5: FAST QUOTE — CUOTA MENSUAL DE ESTIMACIONES
-- ============================================================
-- Tabla que registra cada estimación de Fast Quote para poder
-- aplicar la cuota mensual del plan (companies.plan = 'fast_quote').
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fast_quote_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fast_quote_usage_company_created
    ON public.fast_quote_usage(company_id, created_at);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE public.fast_quote_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY company_isolation_fqu ON public.fast_quote_usage
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );
