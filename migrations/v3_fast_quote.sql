-- ============================================================
-- MIGRACIÓN v3: FAST QUOTE — CRITERIOS DE PRECIOS
-- ============================================================
-- Agrega la tabla fast_quote_criteria para que cada compañía
-- pueda configurar sus propios criterios de precios que la IA
-- usará como referencia al generar estimaciones rápidas.
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- Precaución: Hacer backup antes de ejecutar
-- ============================================================

-- ============================================================
-- 1. TABLA FAST_QUOTE_CRITERIA
-- ============================================================
CREATE TABLE IF NOT EXISTS public.fast_quote_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'material',
    unit VARCHAR(50) DEFAULT '',
    unit_price DECIMAL(12,2) DEFAULT 0,
    description TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger auto-update
CREATE OR REPLACE FUNCTION update_fast_quote_criteria_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_fast_quote_criteria_updated_at
    BEFORE UPDATE ON public.fast_quote_criteria
    FOR EACH ROW EXECUTE FUNCTION update_fast_quote_criteria_updated_at();

-- Índices
CREATE INDEX IF NOT EXISTS idx_fqc_company ON public.fast_quote_criteria(company_id);
CREATE INDEX IF NOT EXISTS idx_fqc_category ON public.fast_quote_criteria(category);

-- ============================================================
-- 2. ROW LEVEL SECURITY
-- ============================================================
-- Aislamiento total entre compañías usando el mismo patrón que
-- cotizaciones, drafts y pdf_storage (v2_multi_tenant.sql).
-- El middleware establece app.current_company_id al inicio de
-- cada request.
-- ============================================================
ALTER TABLE public.fast_quote_criteria ENABLE ROW LEVEL SECURITY;

CREATE POLICY company_isolation_fqc ON public.fast_quote_criteria
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );

-- ============================================================
-- 3. SEED — CRITERIOS POR DEFAULT (opcional)
-- ============================================================
-- Descomenta y ajusta el company_id para sembrar criterios
-- iniciales en tu compañía después de ejecutar la migración.
--
-- INSERT INTO public.fast_quote_criteria (company_id, name, category, unit, unit_price, description) VALUES
-- ('TU-COMPANY-ID-AQUI', 'Acero estructural A-36',      'material',      'kg',   35.00,  'Costo de acero al carbón estándar'),
-- ('TU-COMPANY-ID-AQUI', 'Acero inoxidable 304',        'material',      'kg',   85.00,  'Acero inoxidable grado alimenticio'),
-- ('TU-COMPANY-ID-AQUI', 'Aluminio 6061',               'material',      'kg',  120.00,  'Aluminio estructural'),
-- ('TU-COMPANY-ID-AQUI', 'Soldadura (mano de obra)',     'mano_de_obra',  'hora', 250.00, 'Soldador certificado'),
-- ('TU-COMPANY-ID-AQUI', 'Fabricación (mano de obra)',   'mano_de_obra',  'hora', 180.00, 'Ayudante general'),
-- ('TU-COMPANY-ID-AQUI', 'Pintura y acabado',            'mano_de_obra',  'm²',    80.00,  'Pintura esmalte o anticorrosiva'),
-- ('TU-COMPANY-ID-AQUI', 'Margen de utilidad',           'margen',        '%',    20.00,  'Margen bruto objetivo sobre costo'),
-- ('TU-COMPANY-ID-AQUI', 'Transporte local',             'transporte',    'lote', 2500.00,'Traslado dentro de la ciudad'),
-- ('TU-COMPANY-ID-AQUI', 'Instalación en sitio',         'instalacion',   'hora', 350.00,  'Técnico de instalación');
-- ============================================================
