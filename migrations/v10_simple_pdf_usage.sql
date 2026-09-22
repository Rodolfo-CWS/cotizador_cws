-- ============================================================
-- MIGRACIÓN v10: SIMPLE PDF — CUOTA MENSUAL DE COTIZACIONES
-- ============================================================
-- Tabla que registra cada cotización simple creada para aplicar la cuota
-- mensual del plan Starter (companies.plan = 'starter', max_pdfs = 10).
--
-- Espejo de v5_fast_quote_usage.sql (cuota mensual de Fast Quote).
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- ============================================================

CREATE TABLE IF NOT EXISTS public.simple_pdf_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_simple_pdf_usage_company_created
    ON public.simple_pdf_usage(company_id, created_at);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE public.simple_pdf_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY company_isolation_spu ON public.simple_pdf_usage
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );
