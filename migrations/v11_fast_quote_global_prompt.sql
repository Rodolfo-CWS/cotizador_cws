-- ============================================================
-- MIGRACIÓN v11: FAST QUOTE — CRITERIOS GLOBALES
-- ============================================================
-- Crea un singleton (una sola fila) con los criterios GLOBALES de Fast Quote,
-- iguales para todos los tenants. Se siembra copiando el prompt que hoy tiene
-- el tenant CWS (slug 'cws-company').
--
-- A partir de ahora:
--   - fast_quote_global_prompt → criterios base, los edita SOLO el superadmin
--     (panel /admin). No son visibles para los tenants.
--   - fast_quote_prompt        → "instrucciones adicionales" personales por
--     tenant, los edita el admin de cada empresa.
--
-- Ejecutar en: SQL Editor de Supabase Dashboard
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fast_quote_global_prompt (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    prompt_text TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sembrar desde el tenant CWS (solo si el singleton está vacío).
INSERT INTO public.fast_quote_global_prompt (id, prompt_text)
SELECT 1, fqp.prompt_text
FROM public.fast_quote_prompt fqp
JOIN public.companies c ON c.id = fqp.company_id
WHERE c.slug = 'cws-company'
ON CONFLICT (id) DO NOTHING;

-- Limpiar el cuadro personal de CWS: sus criterios ahora son globales.
UPDATE public.fast_quote_prompt fqp
SET prompt_text = ''
FROM public.companies c
WHERE c.id = fqp.company_id
  AND c.slug = 'cws-company';

-- RLS: sin políticas públicas; solo el service role (la app usa conexión
-- directa / service key) puede leer/escribir. Así no es visible a tenants.
ALTER TABLE public.fast_quote_global_prompt ENABLE ROW LEVEL SECURITY;
