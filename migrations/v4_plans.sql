-- v4_plans.sql
-- SaaS: planes por compañía (self-service, sin pagos todavía).
-- Añade la columna companies.plan (identificador del plan).
-- El marcador de cotización simple se guarda en datos_generales.tipo (jsonb),
-- no necesita columna dedicada.

ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'full'
    CONSTRAINT companies_plan_check CHECK (plan IN ('pdf', 'fast_quote', 'full'));

CREATE INDEX IF NOT EXISTS idx_companies_plan ON public.companies(plan);
