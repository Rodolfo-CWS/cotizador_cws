-- =====================================================================
-- v13_imported_pdfs.sql
-- Importación de cotizaciones antiguas (PDFs digitales) + búsqueda por
-- contenido. Bucket privado `imported-pdfs` + tabla `imported_pdfs` con
-- full-text (tsvector) y respaldo trigram para códigos/folios parciales.
--
-- Aplicar en Supabase SQL Editor ANTES del deploy.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent no es IMMUTABLE; wrapper para poder usarlo en columna generada / índices
CREATE OR REPLACE FUNCTION public.f_unaccent(text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
$$ SELECT public.unaccent('public.unaccent', $1) $$;

CREATE TABLE IF NOT EXISTS public.imported_pdfs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    nombre_archivo  TEXT NOT NULL,
    storage_path    TEXT NOT NULL,
    contenido_texto TEXT NOT NULL DEFAULT '',          -- truncado a ~500k caracteres en el backend
    num_paginas     INT,
    tsv             TSVECTOR GENERATED ALWAYS AS (
                        to_tsvector('spanish',
                            public.f_unaccent(coalesce(contenido_texto,'') || ' ' || coalesce(nombre_archivo,'')))
                    ) STORED,
    hash_contenido  TEXT NOT NULL,
    tamanio_bytes   BIGINT NOT NULL,
    uploaded_by     UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_imported_pdfs_company_hash UNIQUE (company_id, hash_contenido)
);

CREATE INDEX IF NOT EXISTS idx_imported_pdfs_company ON public.imported_pdfs(company_id);
CREATE INDEX IF NOT EXISTS idx_imported_pdfs_tsv     ON public.imported_pdfs USING GIN(tsv);
-- respaldo para códigos / números de parte / folios (búsqueda parcial)
CREATE INDEX IF NOT EXISTS idx_imported_pdfs_trgm    ON public.imported_pdfs
    USING GIN (public.f_unaccent(contenido_texto || ' ' || nombre_archivo) gin_trgm_ops);

ALTER TABLE public.imported_pdfs ENABLE ROW LEVEL SECURITY;

-- Mismo patrón que company_isolation_cotizaciones
DROP POLICY IF EXISTS company_isolation_imported_pdfs ON public.imported_pdfs;
CREATE POLICY company_isolation_imported_pdfs ON public.imported_pdfs
    FOR ALL
    USING (company_id = COALESCE(current_setting('app.current_company_id', true)::uuid,
                                 '00000000-0000-0000-0000-000000000000'::uuid))
    WITH CHECK (company_id = COALESCE(current_setting('app.current_company_id', true)::uuid,
                                      '00000000-0000-0000-0000-000000000000'::uuid));

-- Bucket privado para los PDFs importados (20 MB por archivo).
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('imported-pdfs', 'imported-pdfs', false, 20971520, ARRAY['application/pdf'])
ON CONFLICT (id) DO NOTHING;
