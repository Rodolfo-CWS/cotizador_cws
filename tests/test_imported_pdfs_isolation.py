"""Pruebas de aislamiento multi-tenant para imported_pdfs.

No tocan Supabase ni PostgreSQL reales: la conexión y el SDK van mockeados.
El objetivo es garantizar que toda consulta a `imported_pdfs` va escopada por
`company_id`, de modo que un tenant jamás vea los PDFs importados de otro.
"""
import sys
import types

import pytest

from supabase_manager import SupabaseManager

COMPANY_A = "00000000-0000-0000-0000-0000000000aa"
COMPANY_B = "00000000-0000-0000-0000-0000000000bb"


class CapturingCursor:
    """Cursor falso que registra cada (sql, params) y devuelve datos por turno."""

    def __init__(self, fetchone_result, fetchall_result):
        self.executions = []
        self._fetchone = fetchone_result
        self._fetchall = fetchall_result
        self.closed = False

    def execute(self, sql, params=None):
        self.executions.append((sql, params))

    def fetchone(self):
        return self._fetchone

    def fetchall(self):
        return self._fetchall

    def close(self):
        self.closed = True


class FakeConn:
    def __init__(self, cursor):
        self.closed = False
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def rollback(self):
        pass

    def commit(self):
        pass


def _manager_with(cursor):
    """Crea un SupabaseManager sin __init__ (sin red) y le inyecta una conexión PG."""
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.pg_connection = FakeConn(cursor)
    mgr.modo_offline = False
    mgr.supabase_client = None
    mgr.supabase_url = None
    return mgr


def _assert_scoped(executions, expected_company, forbidden_company):
    """Toda query debe escopar por expected_company y jamás por forbidden_company.

    Además verifica la POSICIÓN: el %s que sigue a "company_id = " debe recibir
    expected_company. No basta con que aparezca en algún lugar de la lista, porque
    un company_id mal colocado (p. ej. en el slot del texto buscado) no lo detecta.
    """
    import re as _re
    assert executions, "se esperaba al menos una ejecución SQL"
    for sql, params in executions:
        assert expected_company in params, f"falta company_id en {params!r}"
        assert forbidden_company not in params, f"fuga de company_id en {params!r}"
        m = _re.search(r'company_id\s*=\s*%s', sql)
        if m:
            slot = sql[:m.start()].count('%s')
            assert params[slot] == expected_company, (
                f"company_id fuera de lugar: la posición {slot} recibió {params[slot]!r}"
            )


def test_listar_pdfs_importados_esta_escopado():
    row = {
        'id': 'aaaaaaaa-1111-2222-3333-444444444444',
        'nombre_archivo': 'cotizacion.pdf',
        'num_paginas': 2,
        'tamanio_bytes': 12345,
        'created_at': None,
        'uploaded_by': None,
        'uploaded_by_name': None,
    }
    cursor = CapturingCursor(None, [row])
    mgr = _manager_with(cursor)

    resultado = mgr.listar_pdfs_importados(COMPANY_A)

    assert resultado[0]['id'] == row['id']
    _assert_scoped(cursor.executions, COMPANY_A, COMPANY_B)


def test_buscar_pdfs_importados_esta_escopado():
    row = {
        'id': 'bbbbbbbb-1111-2222-3333-444444444444',
        'nombre_archivo': 'bomba hidraulica.pdf',
        'num_paginas': 3,
        'tamanio_bytes': 999,
        'created_at': None,
        'snippet': '<b>bomba</b> hidraulica',
    }
    cursor = CapturingCursor({'total': 1}, [row])
    mgr = _manager_with(cursor)

    resultado = mgr.buscar_pdfs_importados("bomba", COMPANY_A, page=1, per_page=20)

    assert resultado['total'] == 1
    assert resultado['resultados'][0]['id'] == row['id']
    # El snippet se limpia: sin etiquetas HTML.
    assert '<b>' not in resultado['resultados'][0]['snippet']
    # count + search, ambos escopados.
    _assert_scoped(cursor.executions, COMPANY_A, COMPANY_B)


def test_buscar_pdfs_importados_usa_trigram_para_codigos():
    row = {
        'id': 'cccccccc-1111-2222-3333-444444444444',
        'nombre_archivo': 'parte-AB123.pdf',
        'num_paginas': 1,
        'tamanio_bytes': 500,
        'created_at': None,
        'snippet': 'parte-AB123',
    }
    cursor = CapturingCursor({'total': 1}, [row])
    mgr = _manager_with(cursor)

    resultado = mgr.buscar_pdfs_importados("AB123", COMPANY_A)

    assert resultado['total'] == 1
    # La consulta "parece código" → usa trigram (ILIKE en el SQL).
    assert any('ILIKE' in sql for sql, _ in cursor.executions)
    _assert_scoped(cursor.executions, COMPANY_A, COMPANY_B)


def test_buscar_pdfs_importados_vacio_lista_todas():
    """Sin texto de búsqueda debe hacer un listado simple (escopado), sin full-text."""
    row = {
        'id': 'dddddddd-1111-2222-3333-444444444444',
        'nombre_archivo': 'otra.pdf',
        'num_paginas': 1,
        'tamanio_bytes': 100,
        'created_at': None,
        'uploaded_by': None,
        'uploaded_by_name': None,
    }
    cursor = CapturingCursor(None, [row])
    mgr = _manager_with(cursor)

    resultado = mgr.buscar_pdfs_importados("", COMPANY_A)

    assert resultado['total'] == 1
    assert resultado['resultados'][0]['id'] == row['id']
    assert resultado['resultados'][0]['snippet'] == ''
    _assert_scoped(cursor.executions, COMPANY_A, COMPANY_B)


def test_ruta_ver_devuelve_404_si_el_pdf_es_de_otra_empresa(monkeypatch):
    """/pdfs-importados/<id>/ver con id de otra empresa → 404 (sin firmar URL)."""
    # En entornos sin las librerías de sistema de WeasyPrint (pango/gobject/cairo),
    # `import weasyprint` lanza OSError (no ImportError). Instalamos un stub para
    # que el import de la app no falle (mismo patrón que test_revision_folio_source.py).
    if "weasyprint" not in sys.modules:
        try:
            import weasyprint  # noqa: F401
        except Exception:
            sys.modules["weasyprint"] = types.ModuleType("weasyprint")

    import app as app_module

    class FakeDB:
        def obtener_pdf_importado_storage_path(self, pdf_id, company_id):
            # El id existe, pero pertenece a otra empresa: la consulta escopada
            # por company_id no devuelve fila → None.
            return None

    monkeypatch.setattr(app_module, "db_manager", FakeDB())

    app_module.app.config["SECRET_KEY"] = "test-secret"
    client = app_module.app.test_client()

    with client.session_transaction() as sess:
        sess["user_id"] = "user-a"
        sess["company_id"] = COMPANY_A

    resp = client.get("/pdfs-importados/aaaaaaaa-1111-2222-3333-444444444444/ver")
    assert resp.status_code == 404
