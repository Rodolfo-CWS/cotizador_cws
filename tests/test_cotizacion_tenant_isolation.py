"""Aislamiento de cotizaciones por compañía.

No toca Supabase. Cubre:

- sin sesión → 401 JSON en /api/ y redirect a login en páginas
- compañía A leyendo o escribiendo el folio/id de B → 404, sin el dato y sin escritura
- el dueño sigue pudiendo leer
- el id numérico de /ver no cruza de empresa
- un request sin sesión reescribe app.current_company_id al centinela
"""
import sys
import types

import pytest

if "weasyprint" not in sys.modules:
    try:
        import weasyprint  # noqa: F401
    except Exception:
        sys.modules["weasyprint"] = types.ModuleType("weasyprint")

import app as app_module
from cotizador.middleware import RLS_DENY_COMPANY_ID
from supabase_manager import SupabaseManager

COMPANY_A = "00000000-0000-0000-0000-0000000000aa"
COMPANY_B = "00000000-0000-0000-0000-0000000000bb"
FOLIO_A = "ACME-A-VEN-001-R1-PROY"
FOLIO_B = "ACME-B-VEN-001-R1-PROY"
ID_B = "42"
SECRETO_B = "CLIENTE-SECRETO-EMPRESA-B"
CLIENTE_A = "Cliente Visible A"


def _item(company, folio, cliente, id_):
    return {
        "_id": id_,
        "id": int(id_) if str(id_).isdigit() else id_,
        "numeroCotizacion": folio,
        "company_id": company,
        "datosGenerales": {
            "cliente": cliente,
            "vendedor": "Vend",
            "proyecto": "Proy",
            "numeroCotizacion": folio,
            "revision": "1",
            "tipo": "simple",
        },
        "items": [{
            "descripcion": "Pieza",
            "cantidad": 1,
            "total": 100,
            "materiales": [],
            "otrosMateriales": [],
        }],
        "condiciones": {"moneda": "MXN", "tipoCambio": "1"},
        "revision": 1,
        "textoIntroductorio": f"texto-privado-{cliente}",
    }


class FakeDB:
    def __init__(self, items):
        self.items = items
        self.writes = []
        self.modo_offline = True
        self.supabase_client = None
        self.archivo_offline = "cotizaciones_offline.json"

    def obtener_cotizacion(self, numero):
        clave = str(numero)
        for item in self.items:
            if item.get("numeroCotizacion") == clave or str(item.get("_id")) == clave:
                return {"encontrado": True, "item": item}
        return {"encontrado": False}

    def edicion_menor_cotizacion(self, numero, parche, usuario="", company_id=None):
        self.writes.append(("edicion", numero, company_id))
        return {"success": True, "numero_cotizacion": numero}

    def guardar_cotizacion(self, datos, company_id=None):
        self.writes.append(("guardar", company_id, (datos or {}).get("numeroCotizacion")))
        numero = (datos or {}).get("numeroCotizacion") or "NUEVO"
        return {
            "success": True,
            "numeroCotizacion": numero,
            "numero_cotizacion": numero,
            "id": "1",
            "campos_guardados": [],
        }

    def buscar_cotizaciones(self, query, page=1, per_page=20, company_id=None):
        # A propósito NO filtra: la ruta tiene que filtrar sola.
        return {"resultados": list(self.items), "items": list(self.items), "total": len(self.items)}

    def get_profiles_by_company(self, company_id):
        return []

    def obtener_draft(self, draft_id, company_id=None):
        return None

    def generar_numero_revision(self, numero, rev):
        return f"{numero}-R{rev}"

    def generar_numero_cotizacion(self, *args, **kwargs):
        return "GEN-001"

    def generar_numero_simple(self, company_id):
        return "SIMPLE-001"

    def contar_pdfs_mes(self, company_id):
        return 0

    def registrar_pdf_simple(self, company_id):
        return None

    def _resolve_company_code(self, company_id):
        return "COD"

    def eliminar_drafts_por_numero_cotizacion(self, numero, company_id=None):
        return {"success": True, "mensaje": "ok"}

    def _cargar_datos_offline(self):
        return {"cotizaciones": list(self.items)}


class FakePDF:
    def __init__(self, path):
        self.path = path
        self.reads = []

    def obtener_pdf(self, numero):
        self.reads.append(numero)
        return {"encontrado": True, "ruta_completa": self.path, "tipo": "local"}

    def almacenar_pdf_nuevo(self, *args, **kwargs):
        return {"success": True}

    drive_client = None


class CapturingCursor:
    def __init__(self):
        self.executions = []

    def execute(self, sql, params=None):
        self.executions.append((sql, params))

    def close(self):
        pass


class FakeConn:
    def __init__(self, cursor):
        self.closed = False
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def rollback(self):
        self.rollbacks += 1

    def commit(self):
        self.commits += 1


@pytest.fixture
def db():
    items = [
        _item(COMPANY_A, FOLIO_A, CLIENTE_A, "7"),
        _item(COMPANY_B, FOLIO_B, SECRETO_B, ID_B),
    ]
    fake = FakeDB(items)
    return fake


@pytest.fixture
def client(db, monkeypatch, tmp_path):
    pdf_path = tmp_path / "cotizacion.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")
    fake_pdf = FakePDF(str(pdf_path))

    monkeypatch.setattr(app_module, "db_manager", db)
    monkeypatch.setattr(app_module, "pdf_manager", fake_pdf)
    monkeypatch.setattr(app_module, "generar_pdf_reportlab", lambda *a, **k: b"%PDF-1.4\n")
    monkeypatch.setattr(app_module, "generar_desglose_pdf_reportlab", lambda *a, **k: b"%PDF-1.4\n")
    monkeypatch.setattr(
        "cotizador.middleware._load_company_from_db",
        lambda mgr, cid: {
            "id": cid,
            "name": "Empresa",
            "plan": "pro",
            "is_active": True,
            "is_internal": False,
            "iva_rate": 16.0,
        },
    )
    app_module.app.config["SECRET_KEY"] = "test-secret"
    test_client = app_module.app.test_client()
    test_client.fake_pdf = fake_pdf
    return test_client


def _login(client, company_id):
    with client.session_transaction() as sess:
        sess["user_id"] = f"user-{company_id[-2:]}"
        sess["company_id"] = company_id
        sess["user_name"] = "Tester"
        sess["user_role"] = "admin"


def _cuerpo(resp):
    return resp.get_data(as_text=True)


PAGINAS = [
    f"/ver/{FOLIO_B}",
    f"/ver/{ID_B}",
    f"/formulario?revision={FOLIO_B}",
    f"/formulario?edicion_menor={FOLIO_B}",
    f"/cotizacion-pdf?numero={FOLIO_B}",
    f"/desglose/{FOLIO_B}",
    f"/desglose/{FOLIO_B}/pdf",
    f"/pdf/{FOLIO_B}",
    f"/local-pdf/{FOLIO_B}",
    f"/debug/test-obtener-cotizacion/{FOLIO_B}",
    f"/debug-estructura/{FOLIO_B}",
    f"/ver-datos/{FOLIO_B}",
    f"/ver-json/{FOLIO_B}",
    f"/debug-revision/{FOLIO_B}",
    f"/cotizacion-resumen/{FOLIO_B}",
]

LISTADOS = [
    "/listar",
    "/diagnostico-tabla-datos",
    f"/buscar-texto-completo/{SECRETO_B}",
    "/verificar-ultima",
    "/stats",
]

APIS_GET = [
    f"/api/cotizacion/{FOLIO_B}",
    f"/api/cotizacion/{FOLIO_B}?preparar_revision=true",
    f"/api/cotizacion/{ID_B}",
]


@pytest.mark.parametrize("path", PAGINAS + LISTADOS)
def test_pagina_sin_sesion_redirige_a_login(client, path):
    resp = client.get(path)
    assert resp.status_code in (301, 302)
    assert "/auth/login" in (resp.headers.get("Location") or "")


@pytest.mark.parametrize("path", APIS_GET)
def test_api_sin_sesion_responde_401_json(client, path):
    resp = client.get(path)
    assert resp.status_code == 401
    assert resp.is_json
    assert resp.get_json()["success"] is False


def test_escrituras_sin_sesion_responden_401(client):
    assert client.patch(
        f"/api/cotizacion/{FOLIO_B}/edicion-menor",
        json={"datosGenerales": {"proyecto": "Hack"}},
    ).status_code == 401
    assert client.post("/generar_pdf", json={"numeroCotizacion": FOLIO_B}).status_code == 401
    assert client.post("/cotizacion-pdf", json={
        "numeroCotizacion": FOLIO_B,
        "datosGenerales": {"cliente": "X", "proyecto": "P"},
        "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 1}],
    }).status_code == 401
    assert client.post("/formulario", json={
        "datosGenerales": {"cliente": "X", "numeroCotizacion": FOLIO_B, "revision": 1},
        "items": [],
    }).status_code == 401
    assert client.post("/", json={
        "datosGenerales": {"numeroCotizacion": FOLIO_B, "cliente": "X"},
    }).status_code == 401
    assert client.post("/test-revision-form", json={
        "datosGenerales": {"numeroCotizacion": FOLIO_B, "revision": 1},
    }).status_code == 401


@pytest.mark.parametrize("path", PAGINAS + APIS_GET)
def test_compania_a_no_lee_folio_de_b(client, db, path):
    _login(client, COMPANY_A)
    resp = client.get(path)
    assert resp.status_code == 404, path
    assert SECRETO_B not in _cuerpo(resp)
    assert db.writes == []
    # /pdf y /local-pdf no deben abrir el archivo de la otra empresa.
    if path.startswith("/pdf/") or path.startswith("/local-pdf/"):
        assert client.fake_pdf.reads == []


@pytest.mark.parametrize("path", LISTADOS)
def test_listados_no_incluyen_otra_empresa(client, path):
    _login(client, COMPANY_A)
    resp = client.get(path)
    assert resp.status_code == 200, _cuerpo(resp)[:400]
    assert FOLIO_B not in _cuerpo(resp)
    data = resp.get_json()
    if path.startswith("/buscar-texto-completo/"):
        assert data["cotizaciones"] == []
        assert data["total_encontradas"] == 0
    if path == "/listar":
        assert CLIENTE_A in _cuerpo(resp)


def test_id_numerico_en_ver_no_cruza_empresa(client):
    _login(client, COMPANY_A)
    resp = client.get(f"/ver/{ID_B}")
    assert resp.status_code == 404
    assert SECRETO_B not in _cuerpo(resp)

    _login(client, COMPANY_B)
    resp_b = client.get(f"/ver/{ID_B}")
    assert resp_b.status_code == 200
    assert SECRETO_B in _cuerpo(resp_b)


def test_dueno_lee_por_api_y_pagina(client):
    _login(client, COMPANY_B)
    api = client.get(f"/api/cotizacion/{FOLIO_B}")
    assert api.status_code == 200
    cuerpo = api.get_json()
    assert cuerpo["success"] is True
    assert cuerpo["cotizacion"]["datosGenerales"]["cliente"] == SECRETO_B

    pagina = client.get(f"/ver/{FOLIO_B}")
    assert pagina.status_code == 200
    assert SECRETO_B in _cuerpo(pagina)

    formulario = client.get(f"/formulario?edicion_menor={FOLIO_B}")
    assert formulario.status_code == 200
    assert SECRETO_B in _cuerpo(formulario)

    resumen = client.get(f"/cotizacion-resumen/{FOLIO_B}")
    assert resumen.status_code == 200
    assert resumen.get_json()["cotizacion"]["cliente"] == SECRETO_B


def test_compania_a_no_modifica_folio_de_b(client, db):
    _login(client, COMPANY_A)
    casos = [
        client.patch(
            f"/api/cotizacion/{FOLIO_B}/edicion-menor",
            json={"datosGenerales": {"proyecto": "Hack"}},
        ),
        client.post("/generar_pdf", json={"numeroCotizacion": FOLIO_B, "textoPersonalizado": "x"}),
        client.post("/cotizacion-pdf", json={
            "numeroCotizacion": FOLIO_B,
            "datosGenerales": {"cliente": "X", "proyecto": "P", "vendedor": "T"},
            "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 10}],
        }),
        client.post("/formulario", json={
            "datosGenerales": {
                "cliente": "X",
                "numeroCotizacion": FOLIO_B,
                "revision": 1,
                "vendedor": "T",
                "proyecto": "P",
            },
            "items": [],
        }),
        client.post("/", json={
            "datosGenerales": {"numeroCotizacion": FOLIO_B, "cliente": "X", "revision": 1},
        }),
        client.post("/test-revision-form", json={
            "datosGenerales": {"numeroCotizacion": FOLIO_B, "revision": 1},
        }),
    ]
    for resp in casos:
        assert resp.status_code == 404
        assert SECRETO_B not in _cuerpo(resp)
    assert db.writes == []


def test_dueno_puede_corregir_y_guardar(client, db):
    _login(client, COMPANY_B)
    resp = client.patch(
        f"/api/cotizacion/{FOLIO_B}/edicion-menor",
        json={"datosGenerales": {"proyecto": "Ajuste"}},
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    assert db.writes and db.writes[0][0] == "edicion"
    assert db.writes[0][2] == COMPANY_B

    pdf = client.post("/cotizacion-pdf", json={
        "numeroCotizacion": FOLIO_B,
        "datosGenerales": {"cliente": SECRETO_B, "proyecto": "Proy", "vendedor": "Vend"},
        "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 10}],
    })
    assert pdf.status_code == 200
    assert pdf.get_json()["success"] is True
    assert any(w[0] == "guardar" and w[1] == COMPANY_B for w in db.writes)


def test_rutas_publicas_siguen_abiertas(client):
    salud = client.get("/health")
    assert salud.status_code == 200
    assert client.get("/planes").status_code == 200
    assert client.get("/auth/login").status_code == 200
    # El panel de plataforma no pasa a exigir el login de tenant.
    admin = client.get("/admin/pdfs")
    assert admin.status_code in (301, 302)
    assert "/admin/login" in (admin.headers.get("Location") or "")


def test_request_sin_sesion_limpia_company_id_de_rls():
    """set_config de sesión no debe quedar con la compañía del request anterior."""
    manager = app_module.app.extensions["db_manager"]
    anterior = manager.pg_connection
    cursor = CapturingCursor()
    conn = FakeConn(cursor)
    manager.pg_connection = conn
    client = app_module.app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["user_id"] = "user-a"
            sess["company_id"] = COMPANY_A
        client.get("/planes")
        sets = [p for sql, p in cursor.executions if "set_config" in sql]
        assert sets, cursor.executions
        assert sets[-1][0] == COMPANY_A
        assert all("false" in sql and ", true)" not in sql for sql, _ in cursor.executions if "set_config" in sql)
        assert conn.commits >= 1

        cursor.executions.clear()
        with client.session_transaction() as sess:
            sess.clear()
        client.get("/health")
        sets = [p for sql, p in cursor.executions if "set_config" in sql]
        assert sets, cursor.executions
        assert sets[-1][0] == RLS_DENY_COMPANY_ID
        assert COMPANY_A not in (sets[-1] or [])
    finally:
        manager.pg_connection = anterior


def test_guardar_cotizacion_no_reescribe_folio_ajeno():
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.supabase_client = object()
    mgr.postgresql_disponible = False
    mgr.modo_offline = True
    wrote = []
    mgr.obtener_cotizacion = lambda numero: {
        "encontrado": True,
        "item": {"company_id": COMPANY_B, "numeroCotizacion": numero, "datosGenerales": {}},
    }
    mgr._guardar_cotizacion_offline = lambda datos: wrote.append(datos) or {"success": True}
    mgr._guardar_cotizacion_sdk = lambda datos: wrote.append(("sdk", datos)) or {"success": True}

    resultado = mgr.guardar_cotizacion(
        {
            "numeroCotizacion": FOLIO_B,
            "datosGenerales": {"numeroCotizacion": FOLIO_B, "revision": "1", "cliente": "X"},
            "items": [],
        },
        company_id=COMPANY_A,
    )
    assert resultado["success"] is False
    assert resultado.get("tipo_error") == "no_encontrada"
    assert wrote == []


def test_edicion_menor_no_parchea_folio_ajeno():
    mgr = SupabaseManager.__new__(SupabaseManager)
    item = {
        "company_id": COMPANY_B,
        "numeroCotizacion": FOLIO_B,
        "datosGenerales": {"proyecto": "Original"},
        "condiciones": {},
        "items": [],
    }
    mgr.obtener_cotizacion = lambda numero: {"encontrado": True, "item": item}
    called = []
    mgr.guardar_cotizacion = lambda *a, **k: called.append(True) or {"success": True}

    resultado = mgr.edicion_menor_cotizacion(
        FOLIO_B, {"datosGenerales": {"proyecto": "Hack"}}, "intruso", company_id=COMPANY_A,
    )
    assert resultado["success"] is False
    assert called == []
    assert item["datosGenerales"]["proyecto"] == "Original"


def test_set_company_context_confirma_el_set_de_sesion():
    cursor = CapturingCursor()
    conn = FakeConn(cursor)
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.pg_connection = conn

    assert mgr.set_company_context(None) is True
    sql, params = cursor.executions[-1]
    assert "set_config" in sql
    assert ", false)" in sql
    assert params == (RLS_DENY_COMPANY_ID,)
    assert conn.commits == 1

    assert mgr.set_company_context(COMPANY_A) is True
    assert cursor.executions[-1][1] == (COMPANY_A,)
    assert conn.commits == 2
