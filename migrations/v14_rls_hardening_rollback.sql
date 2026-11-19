-- ============================================================================
-- v14_rls_hardening_rollback.sql
-- Revierte los cambios de v14_rls_hardening.sql y restaura el estado exacto
-- anterior: RLS deshabilitado en las 5 tablas sin company_id, política pública
-- de drafts, privilegios completos para anon y authenticated, y vistas como
-- SECURITY DEFINER (security_invoker desactivado/eliminado).
-- ============================================================================
BEGIN;

-- 1. Deshabilitar RLS en las tablas
ALTER TABLE public.cotizacion_counters DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.proyectos DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.ordenes_compra DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.gastos_proyecto DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.notificaciones DISABLE ROW LEVEL SECURITY;

-- 2. Recrear la política pública permisiva de drafts
DROP POLICY IF EXISTS "Permitir acceso público a drafts" ON public.drafts;
CREATE POLICY "Permitir acceso público a drafts"
ON public.drafts
FOR ALL
TO public
USING (true)
WITH CHECK (true);

-- 3. Re-otorgar todos los privilegios a anon y authenticated
GRANT ALL PRIVILEGES ON public.cotizacion_counters TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.proyectos TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.ordenes_compra TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.gastos_proyecto TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.notificaciones TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.drafts TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.bom_analysis TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.bom_classifications TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.bom_consolidated TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.bom_items TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.bom_pages TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.vista_resumen_proyectos TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.vista_gastos_pendientes TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.v_bom_analysis_summary TO anon, authenticated;
GRANT ALL PRIVILEGES ON public.v_materials_ranking TO anon, authenticated;

-- 4. Restaurar las vistas a SECURITY DEFINER (eliminar security_invoker)
ALTER VIEW public.vista_resumen_proyectos RESET (security_invoker);
ALTER VIEW public.vista_gastos_pendientes RESET (security_invoker);
ALTER VIEW public.v_bom_analysis_summary RESET (security_invoker);
ALTER VIEW public.v_materials_ranking RESET (security_invoker);

COMMIT;