"""Pruebas de endurecimiento de seguridad (RLS y rutas de debug).

No toca Supabase. Cubre:
- Las 5 rutas de debug exigen superadmin (anon → login, no-superadmin → admin login).
- /health es mínimo, sin fugas de información, y queda una sola regla.
- Los archivos de migración v14 contienen los cambios requeridos y su rollback.
"""
import os

import app as app_module
from tests.test_cotizacion_tenant_isolation import client, db, _login, COMPANY_A


DEBUG_PATHS = [
    "/debug-materiales",
    "/diagnostico-entorno",
    "/debug/sistema",
    "/debug-pdfs",
    "/debug/listar-pdfs-drive",
]


def test_debug_routes_requieren_login_y_superadmin(client):
    # Anónimo
    for path in DEBUG_PATHS:
        resp = client.get(path)
        assert resp.status_code in (301, 302), path
        assert "/auth/login" in (resp.headers.get("Location") or ""), path

    # Usuario de tenant sin superadmin
    _login(client, COMPANY_A)
    for path in DEBUG_PATHS:
        resp = client.get(path)
        assert resp.status_code in (301, 302), path
        assert "/admin/login" in (resp.headers.get("Location") or ""), path

    # Superadmin
    _login(client, COMPANY_A, superadmin=True)
    for path in DEBUG_PATHS:
        resp = client.get(path)
        # La ruta debe ejecutarse sin redirección (superadmin pasa)
        assert resp.status_code not in (301, 302), path
        assert resp.is_json, path
        # Solo /debug-materiales y /diagnostico-entorno no dependen de pdf_manager
        if path in ("/debug-materiales", "/diagnostico-entorno"):
            assert resp.status_code == 200, path
        # Para las demás, aceptamos 200 o 500 (dependencias no disponibles en test)
        else:
            assert resp.status_code in (200, 500), path


def test_health_minimo_sin_fuga(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "status" in data
    body = resp.get_data(as_text=True).lower()
    for forbidden in ("total", "url", "supabase.co", "cotizaciones"):
        assert forbidden not in body, forbidden

    # Exactamente una regla para /health
    health_rules = [rule for rule in app_module.app.url_map.iter_rules() if rule.rule == "/health"]
    assert len(health_rules) == 1


def test_migraciones_v14_y_rollback():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    mig_path = os.path.join(base_dir, "migrations", "v14_rls_hardening.sql")
    rollback_path = os.path.join(base_dir, "migrations", "v14_rls_hardening_rollback.sql")
    assert os.path.exists(mig_path)
    assert os.path.exists(rollback_path)

    with open(mig_path, "r", encoding="utf-8") as f:
        mig = f.read()
    with open(rollback_path, "r", encoding="utf-8") as f:
        rollback = f.read()

    # ENABLE ROW LEVEL SECURITY para las 5 tablas
    for table in ("cotizacion_counters", "proyectos", "ordenes_compra",
                  "gastos_proyecto", "notificaciones"):
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;" in mig, table

    # DROP de la política pública de drafts
    assert 'DROP POLICY IF EXISTS "Permitir acceso público a drafts" ON public.drafts;' in mig

    # REVOKE ALL FROM anon para las tablas y drafts
    for table in ("cotizacion_counters", "proyectos", "ordenes_compra",
                  "gastos_proyecto", "notificaciones", "drafts"):
        assert f"REVOKE ALL ON public.{table} FROM anon, authenticated;" in mig, table

    # bom_* tables
    for table in ("bom_analysis", "bom_classifications", "bom_consolidated",
                  "bom_items", "bom_pages"):
        assert f"REVOKE ALL ON public.{table} FROM anon, authenticated;" in mig, table

    # security_invoker en las 4 vistas
    for view in ("vista_resumen_proyectos", "vista_gastos_pendientes",
                 "v_bom_analysis_summary", "v_materials_ranking"):
        assert f"ALTER VIEW public.{view} SET (security_invoker = true);" in mig, view

    # Rollback re-crea la política pública de drafts
    assert 'CREATE POLICY "Permitir acceso público a drafts"' in rollback
    assert "USING (true)" in rollback
    assert "WITH CHECK (true)" in rollback
    # Rollback deshabilita RLS en las 5 tablas
    for table in ("cotizacion_counters", "proyectos", "ordenes_compra",
                  "gastos_proyecto", "notificaciones"):
        assert f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;" in rollback, table
