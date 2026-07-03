-- ============================================================
-- MIGRACIÓN v2: MULTI-TENANT SAAS
-- ============================================================
-- Agrega soporte para múltiples compañías (tenants) con:
-- - Tabla companies (datos + branding por compañía)
-- - company_id en todas las tablas existentes
-- - Row Level Security para aislamiento total entre compañías
-- - Seed de CWS Company como compañía default
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- Precaución: Hacer backup antes de ejecutar
-- ============================================================

-- ============================================================
-- 1. TABLA COMPANIES
-- ============================================================
CREATE TABLE IF NOT EXISTS public.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    tax_id VARCHAR(50),
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    logo_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#4f46e5',
    secondary_color VARCHAR(7) DEFAULT '#1e293b',
    footer_text TEXT,
    iva_rate DECIMAL(5,2) DEFAULT 16.00,
    is_active BOOLEAN DEFAULT true,
    max_users INTEGER DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger auto-update
CREATE OR REPLACE FUNCTION update_companies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON public.companies
    FOR EACH ROW EXECUTE FUNCTION update_companies_updated_at();

-- ============================================================
-- 2. AGREGAR company_id A TABLAS EXISTENTES
-- ============================================================

-- cotizaciones
ALTER TABLE public.cotizaciones
    ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES public.companies(id);

-- pdf_storage
ALTER TABLE public.pdf_storage
    ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES public.companies(id);

-- drafts
ALTER TABLE public.drafts
    ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES public.companies(id);

-- Índices para company_id
CREATE INDEX IF NOT EXISTS idx_cotizaciones_company ON public.cotizaciones(company_id);
CREATE INDEX IF NOT EXISTS idx_pdf_storage_company ON public.pdf_storage(company_id);
CREATE INDEX IF NOT EXISTS idx_drafts_company ON public.drafts(company_id);

-- ============================================================
-- 3. SEED: CWS COMPANY (compañía default para datos existentes)
-- ============================================================
INSERT INTO public.companies (name, slug, tax_id, address, phone, email, primary_color, secondary_color, footer_text, iva_rate)
VALUES (
    'CWS Company SA de CV',
    'cws-company',
    'CWSCOMPANY123',
    'Puerta de los monos 250, 78421 Villa de Pozos, SLP, Mexico',
    '+52 444 123 4567',
    'info@cwscompany.com',
    '#1e293b',
    '#0f172a',
    'CWS Company SA de CV | Puerta de los monos 250, 78421 Villa de Pozos, SLP, Mexico | Esta cotizacion es valida por 30 dias a partir de la fecha de emision | Gracias por confiar en CWS Company!',
    16.00
) ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- 4. ASIGNAR company_id A DATOS EXISTENTES
-- ============================================================
DO $$
DECLARE
    cws_id UUID;
BEGIN
    SELECT id INTO cws_id FROM public.companies WHERE slug = 'cws-company';

    IF cws_id IS NOT NULL THEN
        -- Asignar a cotizaciones existentes
        UPDATE public.cotizaciones
        SET company_id = cws_id
        WHERE company_id IS NULL;

        -- Asignar a pdf_storage existente
        UPDATE public.pdf_storage
        SET company_id = cws_id
        WHERE company_id IS NULL;

        -- Asignar a drafts existentes
        UPDATE public.drafts
        SET company_id = cws_id
        WHERE company_id IS NULL;

        RAISE NOTICE '✅ Datos existentes migrados a CWS Company (id: %)', cws_id;
    ELSE
        RAISE NOTICE '⚠️  CWS Company no encontrada - no se migraron datos';
    END IF;
END $$;

-- ============================================================
-- 5. ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Habilitar RLS
ALTER TABLE public.cotizaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pdf_storage ENABLE ROW LEVEL SECURITY;

-- Drafts ya tiene RLS habilitado, pero la política actual permite todo
-- La reemplazamos por la política correcta
DROP POLICY IF EXISTS "Permitir acceso público a drafts" ON public.drafts;
ALTER TABLE public.drafts ENABLE ROW LEVEL SECURITY;

-- Políticas de aislamiento por compañía
-- Usan current_setting('app.current_company_id') que se configura desde Flask
-- Si la variable no está configurada (ej. consola SQL directa), se usa COALESCE para
-- no devolver nada (seguridad por defecto)

CREATE POLICY company_isolation_cotizaciones ON public.cotizaciones
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );

CREATE POLICY company_isolation_pdf_storage ON public.pdf_storage
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );

CREATE POLICY company_isolation_drafts ON public.drafts
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );

-- ============================================================
-- 6. FUNCIÓN AUXILIAR: configurar company_id en PostgreSQL
-- ============================================================
CREATE OR REPLACE FUNCTION set_company_context(company_uuid UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_company_id', company_uuid::text, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- 7. VERIFICACIÓN
-- ============================================================
SELECT
    'Migración v2 completada' AS mensaje,
    (SELECT COUNT(*) FROM public.companies) AS total_companies,
    (SELECT COUNT(*) FROM public.cotizaciones WHERE company_id IS NOT NULL) AS cotizaciones_con_company,
    (SELECT COUNT(*) FROM public.cotizaciones WHERE company_id IS NULL) AS cotizaciones_sin_company,
    (SELECT COUNT(*) FROM public.drafts WHERE company_id IS NOT NULL) AS drafts_con_company;
