-- ============================================================================
-- v14_rls_hardening.sql
-- Endurecimiento de seguridad RLS y revocación de privilegios públicos.
--
-- Qué hace:
--   1. Activa RLS en tablas que aún estaban deshabilitadas y no contienen
--      company_id (por lo que no pueden tener políticas por compañía).
--   2. Elimina la política pública permisiva de drafts.
--   3. Revoca todos los privilegios de los roles anon y authenticated sobre
--      tablas sensibles y vistas de análisis.
--   4. Fuerza security_invoker=true en vistas SECURITY DEFINER para que
--      respeten los permisos del invocador en lugar de los del dueño.
--
-- Por qué la app sigue funcionando:
--   - La app usa DATABASE_URL con rol postgres (owner, bypassrls=true) para el
--     acceso directo a la base de datos.
--   - El cliente supabase-py con anon key solo se usa como fallback para
--     cotizaciones y drafts; este fallback quedará denegado para drafts
--     (pero ya estaba efectivamente denegado por company_isolation_cotizaciones).
--   - Las operaciones del navegador solo usan la anon key para Auth, nunca para tablas.
--
-- Importante: probar primero en una rama de Supabase o staging.
-- Nota: esta migración solo elimina el acceso de anon/authenticated
-- (PostgREST/GraphQL con la llave pública). RLS NO se aplica a la app
-- porque se conecta como postgres (bypassrls); el aislamiento de tenants
-- en la app sigue estando en el código.
-- ============================================================================
BEGIN;

-- 1. Activar RLS en tablas sin company_id (sin políticas → denegar anon/authenticated)
ALTER TABLE public.cotizacion_counters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proyectos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ordenes_compra ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gastos_proyecto ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notificaciones ENABLE ROW LEVEL SECURITY;

-- 2. Eliminar política pública permisiva en drafts
DROP POLICY IF EXISTS "Permitir acceso público a drafts" ON public.drafts;

-- 3. Revocar todos los privilegios a anon y authenticated
REVOKE ALL ON public.cotizacion_counters FROM anon, authenticated;
REVOKE ALL ON public.proyectos FROM anon, authenticated;
REVOKE ALL ON public.ordenes_compra FROM anon, authenticated;
REVOKE ALL ON public.gastos_proyecto FROM anon, authenticated;
REVOKE ALL ON public.notificaciones FROM anon, authenticated;
REVOKE ALL ON public.drafts FROM anon, authenticated;

REVOKE ALL ON public.bom_analysis FROM anon, authenticated;
REVOKE ALL ON public.bom_classifications FROM anon, authenticated;
REVOKE ALL ON public.bom_consolidated FROM anon, authenticated;
REVOKE ALL ON public.bom_items FROM anon, authenticated;
REVOKE ALL ON public.bom_pages FROM anon, authenticated;

REVOKE ALL ON public.vista_resumen_proyectos FROM anon, authenticated;
REVOKE ALL ON public.vista_gastos_pendientes FROM anon, authenticated;
REVOKE ALL ON public.v_bom_analysis_summary FROM anon, authenticated;
REVOKE ALL ON public.v_materials_ranking FROM anon, authenticated;

-- 4. Forzar security_invoker en las vistas
ALTER VIEW public.vista_resumen_proyectos SET (security_invoker = true);
ALTER VIEW public.vista_gastos_pendientes SET (security_invoker = true);
ALTER VIEW public.v_bom_analysis_summary SET (security_invoker = true);
ALTER VIEW public.v_materials_ranking SET (security_invoker = true);

-- 5. Garantizar que postgres y service_role conservan sus privilegios (owner/bypass)
GRANT ALL PRIVILEGES ON public.cotizacion_counters TO service_role;
GRANT ALL PRIVILEGES ON public.proyectos TO service_role;
GRANT ALL PRIVILEGES ON public.ordenes_compra TO service_role;
GRANT ALL PRIVILEGES ON public.gastos_proyecto TO service_role;
GRANT ALL PRIVILEGES ON public.notificaciones TO service_role;
GRANT ALL PRIVILEGES ON public.drafts TO service_role;
GRANT ALL PRIVILEGES ON public.bom_analysis TO service_role;
GRANT ALL PRIVILEGES ON public.bom_classifications TO service_role;
GRANT ALL PRIVILEGES ON public.bom_consolidated TO service_role;
GRANT ALL PRIVILEGES ON public.bom_items TO service_role;
GRANT ALL PRIVILEGES ON public.bom_pages TO service_role;
GRANT ALL PRIVILEGES ON public.vista_resumen_proyectos TO service_role;
GRANT ALL PRIVILEGES ON public.vista_gastos_pendientes TO service_role;
GRANT ALL PRIVILEGES ON public.v_bom_analysis_summary TO service_role;
GRANT ALL PRIVILEGES ON public.v_materials_ranking TO service_role;

-- ============================================================================
-- Verificación (ejecutar manualmente después de aplicar)
-- ============================================================================
-- SELECT relname, relrowsecurity FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relname IN (
--   'cotizacion_counters','proyectos','ordenes_compra','gastos_proyecto','notificaciones'
-- );
-- SELECT grantee, table_name, privilege_type 
-- FROM information_schema.role_table_grants 
-- WHERE table_schema = 'public' 
--   AND table_name IN (
--     'cotizacion_counters','proyectos','ordenes_compra','gastos_proyecto','notificaciones',
--     'drafts','bom_analysis','bom_classifications','bom_consolidated','bom_items','bom_pages',
--     'vista_resumen_proyectos','vista_gastos_pendientes','v_bom_analysis_summary','v_materials_ranking'
--   )
--   AND grantee IN ('anon','authenticated')
-- ORDER BY table_name, grantee, privilege_type;
-- SELECT policyname, cmd, roles, qual, with_check 
-- FROM pg_policies 
-- WHERE schemaname = 'public' AND tablename = 'drafts';
-- SELECT c.relname, c.reloptions 
-- FROM pg_class c 
-- WHERE c.relkind = 'v' AND c.relnamespace = 'public'::regnamespace 
--   AND c.relname IN ('vista_resumen_proyectos','vista_gastos_pendientes','v_bom_analysis_summary','v_materials_ranking');

COMMIT;