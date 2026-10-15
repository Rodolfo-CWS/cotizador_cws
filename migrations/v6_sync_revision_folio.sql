-- =============================================================================
-- MIGRACIÓN v6: Sincronizar `revision` con el FOLIO (-R#-)
-- =============================================================================
-- Problema: la revisión se guardaba desde el campo `datosGenerales.revision`,
-- que históricamente se desincroniza del folio `numero_cotizacion` (p. ej. la
-- R2 de BMW-CWS-FM-019 quedó con revision=1). Esto crea una "doble fuente de
-- verdad": el folio dice R2 pero la columna/campo dicen 1.
--
-- Fuente de verdad: `numero_cotizacion` (formato CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO).
--
-- CÓMO USAR (en el SQL Editor de Supabase):
--   1) Corre SOLO el bloque "PASO 1 (PREVIEW)" para ver las filas afectadas.
--   2) Si se ve correcto, corre los PASOS 2 y 3 (UPDATE).
--   3) Corre el "PASO 4 (VERIFICACIÓN)" para confirmar que ya no hay desincronía.
-- Es idempotente: solo toca filas donde revision difiere del folio.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PASO 1 (PREVIEW): filas desincronizadas — NO modifica nada.
-- -----------------------------------------------------------------------------
SELECT
    id,
    numero_cotizacion,
    revision                                                        AS rev_columna,
    datos_generales->>'revision'                                    AS rev_campo,
    substring(numero_cotizacion from '-R([0-9]+)(-|$)')             AS rev_folio
FROM cotizaciones
WHERE numero_cotizacion ~ '-R[0-9]+(-|$)'
  AND (
        revision IS DISTINCT FROM (substring(numero_cotizacion from '-R([0-9]+)(-|$)'))::int
     OR datos_generales->>'revision' IS DISTINCT FROM substring(numero_cotizacion from '-R([0-9]+)(-|$)')
      )
ORDER BY id;

-- -----------------------------------------------------------------------------
-- PASO 2 (UPDATE): corregir la COLUMNA `revision` (integer).
-- -----------------------------------------------------------------------------
UPDATE cotizaciones
SET revision    = (substring(numero_cotizacion from '-R([0-9]+)(-|$)'))::int,
    updated_at  = NOW()
WHERE numero_cotizacion ~ '-R[0-9]+(-|$)'
  AND revision IS DISTINCT FROM (substring(numero_cotizacion from '-R([0-9]+)(-|$)'))::int;

-- -----------------------------------------------------------------------------
-- PASO 3 (UPDATE): corregir el CAMPO `datos_generales.revision` (JSONB, texto).
-- Se guarda como texto para coincidir con el formato que escribe la app.
-- -----------------------------------------------------------------------------
UPDATE cotizaciones
SET datos_generales = jsonb_set(
        datos_generales,
        '{revision}',
        to_jsonb(substring(numero_cotizacion from '-R([0-9]+)(-|$)')),
        false
      ),
    updated_at = NOW()
WHERE numero_cotizacion ~ '-R[0-9]+(-|$)'
  AND datos_generales->>'revision' IS DISTINCT FROM substring(numero_cotizacion from '-R([0-9]+)(-|$)');

-- -----------------------------------------------------------------------------
-- PASO 4 (VERIFICACIÓN): debe devolver 0 filas si todo quedó sincronizado.
-- -----------------------------------------------------------------------------
SELECT
    id,
    numero_cotizacion,
    revision                                     AS rev_columna,
    datos_generales->>'revision'                 AS rev_campo,
    substring(numero_cotizacion from '-R([0-9]+)(-|$)') AS rev_folio
FROM cotizaciones
WHERE numero_cotizacion ~ '-R[0-9]+(-|$)'
  AND (
        revision IS DISTINCT FROM (substring(numero_cotizacion from '-R([0-9]+)(-|$)'))::int
     OR datos_generales->>'revision' IS DISTINCT FROM substring(numero_cotizacion from '-R([0-9]+)(-|$)')
      )
ORDER BY id;
