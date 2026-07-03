-- ============================================================
-- MIGRACIÓN v2.1: TABLA DE PERFILES (USER PROFILES)
-- ============================================================
-- Vincula los usuarios de Supabase Auth (auth.users) con
-- las compañías (public.companies) y asigna roles.
--
-- PREREQUISITO: Haber ejecutado v2_multi_tenant.sql primero
-- ============================================================

-- ============================================================
-- 1. TABLA PROFILES
-- ============================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY,  -- Mismo ID que auth.users (Supabase Auth)
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'seller'
        CHECK (role IN ('admin', 'manager', 'seller')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_profiles_company ON public.profiles(company_id);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);

-- Trigger auto-update
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 2. RLS: Cada usuario solo puede leer perfiles de su compañía
-- ============================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY company_isolation_profiles ON public.profiles
    FOR SELECT
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );

-- Solo admins pueden insertar/actualizar/eliminar (se controla desde la app)
CREATE POLICY profiles_insert_admin ON public.profiles
    FOR INSERT WITH CHECK (true);  -- Permitido desde backend con service key

-- ============================================================
-- 3. SEED: Perfiles para usuarios existentes de CWS Company
-- ============================================================
-- NOTA: Estos perfiles se crean manualmente DESPUÉS de que los
-- usuarios se registren en Supabase Auth. Los IDs de abajo son
-- placeholders — deben reemplazarse con los UUIDs reales de
-- auth.users después del registro.
--
-- Para crear los perfiles manualmente después del registro:
--
-- SELECT id FROM public.companies WHERE slug = 'cws-company';
-- (Usar ese UUID como company_id)
--
-- INSERT INTO public.profiles (id, company_id, full_name, role)
-- VALUES
--   ('<uuid-de-rodolfo-en-auth.users>', '<cws-company-id>', 'Rodolfo Moreno', 'admin'),
--   ('<uuid-de-francisco-en-auth.users>', '<cws-company-id>', 'Francisco Moreno', 'manager'),
--   ...
-- ============================================================

-- ============================================================
-- 4. FUNCIÓN AUXILIAR: Obtener perfil por ID de usuario
-- ============================================================
CREATE OR REPLACE FUNCTION get_user_profile(user_uuid UUID)
RETURNS TABLE(
    user_id UUID,
    company_id UUID,
    company_name VARCHAR,
    company_slug VARCHAR,
    full_name VARCHAR,
    role VARCHAR,
    logo_url TEXT,
    primary_color VARCHAR,
    secondary_color VARCHAR,
    footer_text TEXT,
    iva_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS user_id,
        c.id AS company_id,
        c.name AS company_name,
        c.slug AS company_slug,
        p.full_name,
        p.role,
        c.logo_url,
        c.primary_color,
        c.secondary_color,
        c.footer_text,
        c.iva_rate
    FROM public.profiles p
    JOIN public.companies c ON c.id = p.company_id
    WHERE p.id = user_uuid
      AND p.is_active = true
      AND c.is_active = true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Verificación
SELECT 'Migración v2.1 completada' AS mensaje,
       (SELECT COUNT(*) FROM public.profiles) AS total_profiles;
