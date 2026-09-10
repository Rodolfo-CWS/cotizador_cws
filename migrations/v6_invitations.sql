-- ============================================================
-- MIGRACIÓN v6: INVITACIONES (ONBOARDING AUTOSERVICIO)
-- ============================================================
-- Permite que el admin de una compañía invite nuevos usuarios por
-- email a unirse a su empresa, en lugar de que cada registro cree
-- una compañía nueva.
--
-- Flujo:
--   1. Admin invita (email + rol) → se inserta una fila en
--      public.invitations + se envía email vía Supabase Auth.
--   2. El usuario confirma/setea contraseña vía el link del email.
--   3. En su primer login, la app detecta la invitación pendiente y
--      crea su public.profiles vinculado a la compañía.
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- Precaución: Hacer backup antes de ejecutar
-- ============================================================

-- 1. Tabla de invitaciones
CREATE TABLE IF NOT EXISTS public.invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,                -- Supabase normaliza emails a minúsculas
    role VARCHAR(50) NOT NULL DEFAULT 'seller'
        CHECK (role IN ('admin', 'manager', 'seller')),
    invited_by UUID REFERENCES public.profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                     -- NULL = no expira
    accepted_at TIMESTAMPTZ,                    -- se setea al vincular el perfil
    revoked_at TIMESTAMPTZ                      -- admin cancela la invitación
);

-- 2. Solo una invitación ACTIVA por (empresa, email)
CREATE UNIQUE INDEX IF NOT EXISTS idx_invitations_active
    ON public.invitations (company_id, email)
    WHERE accepted_at IS NULL AND revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_invitations_company
    ON public.invitations (company_id);

-- 3. RLS: aislamiento por compañía (defensa en profundidad; la app
--    accede con service key, igual que public.profiles)
ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY company_isolation_invitations ON public.invitations
    FOR ALL
    USING (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    )
    WITH CHECK (
        company_id = COALESCE(
            current_setting('app.current_company_id', true)::UUID,
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );

-- 4. Verificación
SELECT 'Migración v6 completada' AS mensaje,
       (SELECT COUNT(*) FROM public.invitations) AS total_invitaciones;
