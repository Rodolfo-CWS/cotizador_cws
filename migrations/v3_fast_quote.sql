-- ============================================================
-- MIGRACIÓN v3: FAST QUOTE — PROMPT DE CRITERIOS
-- ============================================================
-- Tabla que guarda el prompt de criterios de precios por
-- compañía. El admin escribe en texto libre sus precios de
-- referencia y la IA los usa para estimar cotizaciones rápidas.
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fast_quote_prompt (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL UNIQUE REFERENCES public.companies(id) ON DELETE CASCADE,
    prompt_text TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger auto-update
CREATE OR REPLACE FUNCTION update_fast_quote_prompt_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_fast_quote_prompt_updated_at
    BEFORE UPDATE ON public.fast_quote_prompt
    FOR EACH ROW EXECUTE FUNCTION update_fast_quote_prompt_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE public.fast_quote_prompt ENABLE ROW LEVEL SECURITY;

CREATE POLICY company_isolation_fqp ON public.fast_quote_prompt
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );
