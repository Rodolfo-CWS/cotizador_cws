"""Edición menor y nueva revisión en cotización simple (v5).

No toca Supabase real: `db_manager` y `pdf_manager` van mockeados. Cubre el
comportamiento server-side del flujo de revisiones/edición menor de la
cotización simple:

- Starter no puede crear revisiones (403 en GET y POST).
- GET / POST con folio de otra compañía no filtra ni escribe.
- Nueva revisión exige justificación (>= 10 chars) para R2+.
- Una segunda R2 sobre la misma R1 responde 409 sin sobrescribir.
- Edición menor conserva Vendedor/Cliente/Revisión/Fecha del original.
- /api/revision-estado exige sesión y escopa por compañía.
"""
import re
import sys
import types

import pytest

if "weasyprint" not in sys.modules:
    try:
        import weasyprint  # noqa: F401
    except Exception:
        sys.modules["weasyprint"] = types.ModuleType("weasyprint")

import app as app_module

COMPANY_A = "00000000-0000-0000-0000-0000000000aa"
COMPANY_B = "00000000-0000-0000-0000-0000000000bb"
FOLIO_A_R1 = "ACME-A-VEN-001-R1-PROY"
FOLIO_A_R2 = "ACME-A-VEN-001-R2-PROY"
FOLIO_B_R1 = "ACME-B-VEN-001-R1-PROY"


def _item(company, folio, cliente="Cliente", revision="1", fecha="2024-01-15"):
    return {
        "numeroCotizacion": folio,
        "company_id": company,
        "datosGenerales": {
            "cliente": cliente,
            "vendedor": "Vend",
            "proyecto": "Proy",
            "numeroCotizacion": folio,
            "revision": revision,
            "fecha": fecha,
            "tipo": "simple",
        },
        "items": [{
            "descripcion": "Pieza",
            "cantidad": 2,
            "precio_unitario": 50.0,
            "total": 100.0,
            "uom": "piezas",
        }],
        "condiciones": {"moneda": "MXN", "tipoCambio": "1"},
        "revision": int(revision) if str(revision).isdigit() else 1,
    }


class FakeDB:
    def __init__(self, items=None):
        self.items = list(items or [])
        # Separado de `items`: `obtener_cotizacion` lee de `items`, pero la
        # verificación de "más reciente" (buscar_cotizaciones) puede devolver
        # un subconjunto, para simular una carrera R1→R2.
        self.resultados_busqueda = list(self.items)
        self.writes = []
        self.registros_pdf = []
        self.last_guardar = None
        self.guardar_resultado = None  # override del resultado de guardar_cotizacion
        self.importados_result = {"resultados": []}
        self.modo_offline = True
        self.supabase_client = None

    def obtener_cotizacion(self, numero):
        clave = str(numero)
        for item in self.items:
            if item.get("numeroCotizacion") == clave or str(item.get("_id")) == clave:
                return {"encontrado": True, "item": item}
        return {"encontrado": False}

    def buscar_cotizaciones(self, query, page=1, per_page=20, company_id=None):
        return {"items": list(self.resultados_busqueda), "resultados": list(self.resultados_busqueda)}

    def buscar_pdfs_importados(self, query, company_id, page=1, per_page=20):
        return self.importados_result

    def contar_pdfs_importados(self, company_id):
        return 0

    def generar_numero_revision(self, numero, rev):
        return re.sub(r'-R\d+', f'-R{rev}', numero, count=1)

    def generar_numero_cotizacion(self, *args, **kwargs):
        return "GEN-001-R1-PROY"

    def generar_numero_simple(self, company_id):
        return "SIMPLE-001"

    def contar_pdfs_mes(self, company_id):
        return 0

    def registrar_pdf_simple(self, company_id):
        self.registros_pdf.append(company_id)
        return None

    def _resolve_company_code(self, company_id):
        return "COD"

    def guardar_cotizacion(self, datos, company_id=None, solo_insertar=False):
        if self.guardar_resultado is not None:
            return self.guardar_resultado
        numero = (datos or {}).get("numeroCotizacion") or "NUEVO"
        self.last_guardar = datos
        self.writes.append(("guardar", company_id, numero, solo_insertar))
        return {"success": True, "numeroCotizacion": numero, "numero_cotizacion": numero, "id": "1"}

    def obtener_draft(self, draft_id, company_id=None):
        return None

    def get_profiles_by_company(self, company_id):
        return []

    def eliminar_drafts_por_numero_cotizacion(self, numero, company_id=None):
        return {"success": True}


class FakePDF:
    def almacenar_pdf_nuevo(self, *args, **kwargs):
        return {"success": True}

    def buscar_pdfs(self, query, page=1, per_page=20):
        return {"resultados": []}


@pytest.fixture
def db():
    return FakeDB([_item(COMPANY_A, FOLIO_A_R1)])


@pytest.fixture
def client(db, monkeypatch, tmp_path):
    fake_pdf = FakePDF()
    monkeypatch.setattr(app_module, "db_manager", db)
    monkeypatch.setattr(app_module, "pdf_manager", fake_pdf)
    monkeypatch.setattr(app_module, "generar_pdf_reportlab", lambda *a, **k: b"%PDF-1.4\n")
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


def _loader(plan, is_internal=False):
    def _load(_mgr, cid):
        return {
            "id": cid,
            "name": "Empresa",
            "plan": plan,
            "is_active": True,
            "is_internal": is_internal,
            "iva_rate": 16.0,
        }
    return _load


def _body(resp):
    return resp.get_data(as_text=True)


def _post_revision(client, revision_de, actualizacion="Justificación larga y válida", cliente="Cliente"):
    return client.post("/cotizacion-pdf", json={
        "revisionDe": revision_de,
        "datosGenerales": {
            "cliente": cliente,
            "proyecto": "Proy",
            "actualizacionRevision": actualizacion,
        },
        "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 10}],
    })


# ── Starter: sin revisiones ──

def test_starter_get_revision_403(client, monkeypatch):
    monkeypatch.setattr("cotizador.middleware._load_company_from_db", _loader("starter"))
    _login(client, COMPANY_A)
    resp = client.get(f"/cotizacion-pdf?revision={FOLIO_A_R1}")
    assert resp.status_code == 403


def test_starter_post_revision_403(client, monkeypatch):
    monkeypatch.setattr("cotizador.middleware._load_company_from_db", _loader("starter"))
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_A_R1)
    assert resp.status_code == 403


# ── Aislamiento por compañía ──

def test_get_revision_de_otra_compania_404(client, db):
    db.items.append(_item(COMPANY_B, FOLIO_B_R1, cliente="Secreto B"))
    db.resultados_busqueda = list(db.items)
    _login(client, COMPANY_A)
    resp = client.get(f"/cotizacion-pdf?revision={FOLIO_B_R1}")
    assert resp.status_code == 404
    assert "Secreto B" not in _body(resp)


def test_post_nueva_revision_de_otra_compania_403(client, db):
    db.items.append(_item(COMPANY_B, FOLIO_B_R1, cliente="Secreto B"))
    db.resultados_busqueda = list(db.items)
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_B_R1)
    assert resp.status_code == 403
    assert db.writes == []


# ── Nueva revisión ──

def test_post_nueva_revision_justificacion_corta_400(client, db):
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_A_R1, actualizacion="corta")
    assert resp.status_code == 400
    assert resp.get_json().get("campo_requerido") == "actualizacionRevision"
    assert db.writes == []


def test_post_segunda_r2_sobre_r1_409(client, db):
    """R1 es la más reciente en la búsqueda, pero el folio R2 ya existe (carrera)."""
    r2 = _item(COMPANY_A, FOLIO_A_R2, revision="2")
    db.items.append(r2)
    # La verificación de "más reciente" solo ve la R1.
    db.resultados_busqueda = [_item(COMPANY_A, FOLIO_A_R1)]
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_A_R1)
    assert resp.status_code == 409
    assert db.writes == []


def test_post_nueva_revision_duplicada_por_db_409(client, db):
    """La carrera la frena la BD: guardar_cotizacion reporta colisión."""
    db.guardar_resultado = {
        "success": False,
        "tipo_error": "duplicada",
        "error": "Ya existe una cotización con ese número",
        "numero_cotizacion": FOLIO_A_R2,
    }
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_A_R1)
    assert resp.status_code == 409
    assert resp.get_json().get("error") == "Ya existe una cotización con ese número"


def test_post_nueva_revision_exitosa_no_registra_pdf(client, db):
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_A_R1)
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    assert resp.get_json()["numeroCotizacion"] == FOLIO_A_R2
    # El contador no cuenta en nueva revisión (misma cotización).
    assert db.registros_pdf == []
    # guardar_cotizacion se llamó con solo_insertar=True.
    assert db.writes and db.writes[0][3] is True


# ── Edición menor ──

def test_edicion_menor_conserva_campos_del_original(client, db):
    item = db.items[0]
    item["datosGenerales"].update(cliente="Cliente Original", vendedor="Vend Original", fecha="2024-01-15", revision="1")
    _login(client, COMPANY_A)
    resp = client.post("/cotizacion-pdf", json={
        "numeroCotizacion": FOLIO_A_R1,
        "datosGenerales": {
            "cliente": "HACK",
            "vendedor": "HACK",
            "proyecto": "Proy",
            "revision": "9",
            "fecha": "2024-12-31",
        },
        "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 10}],
    })
    assert resp.status_code == 200
    dg = db.last_guardar["datosGenerales"]
    assert dg["cliente"] == "Cliente Original"
    assert dg["vendedor"] == "Vend Original"
    assert dg["revision"] == "1"
    assert dg["fecha"] == "2024-01-15"


def test_edicion_menor_campos_vacios_siguen_vacios(client, db):
    item = db.items[0]
    item["datosGenerales"].update(cliente="", vendedor="", fecha="")
    _login(client, COMPANY_A)
    resp = client.post("/cotizacion-pdf", json={
        "numeroCotizacion": FOLIO_A_R1,
        "datosGenerales": {
            "cliente": "X",
            "vendedor": "Y",
            "proyecto": "Proy",
            "revision": "1",
            "fecha": "2024-12-31",
        },
        "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 10}],
    })
    assert resp.status_code == 200
    dg = db.last_guardar["datosGenerales"]
    assert dg["cliente"] == ""
    assert dg["vendedor"] == ""
    assert dg["fecha"] == ""


# ── GET /cotizacion-pdf?revision= ──

def test_get_revision_mas_reciente_precarga(client, db):
    _login(client, COMPANY_A)
    resp = client.get(f"/cotizacion-pdf?revision={FOLIO_A_R1}")
    assert resp.status_code == 200


def test_get_revision_no_mas_reciente_bloquea(client, db):
    db.items.append(_item(COMPANY_A, FOLIO_A_R2, revision="2"))
    db.resultados_busqueda = list(db.items)
    _login(client, COMPANY_A)
    resp = client.get(f"/cotizacion-pdf?revision={FOLIO_A_R1}")
    assert resp.status_code == 200
    assert "bloqueada" in _body(resp)


# ── /api/revision-estado ──

def test_api_revision_estado_sin_sesion_401(client):
    resp = client.get(f"/api/revision-estado?numero={FOLIO_A_R1}")
    assert resp.status_code == 401


def test_api_revision_estado_starter_403(client, monkeypatch):
    monkeypatch.setattr("cotizador.middleware._load_company_from_db", _loader("starter"))
    _login(client, COMPANY_A)
    resp = client.get(f"/api/revision-estado?numero={FOLIO_A_R1}")
    assert resp.status_code == 403


def test_api_revision_estado_otra_compania_404(client, db):
    db.items.append(_item(COMPANY_B, FOLIO_B_R1, cliente="Secreto B"))
    db.resultados_busqueda = list(db.items)
    _login(client, COMPANY_A)
    resp = client.get(f"/api/revision-estado?numero={FOLIO_B_R1}")
    assert resp.status_code == 404


def test_api_revision_estado_no_mas_reciente(client, db):
    db.items.append(_item(COMPANY_A, FOLIO_A_R2, revision="2"))
    db.resultados_busqueda = list(db.items)
    _login(client, COMPANY_A)
    resp = client.get(f"/api/revision-estado?numero={FOLIO_A_R1}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["es_mas_reciente"] is False
    assert data["revision_maxima"] == 2
    assert "historial_revisiones" not in data


# ── Validación de `modo` (BLOQUEADOR) ──

def test_post_modo_desconocido_400(client, db):
    """Un modo inventado no debe caer en la rama de 'crear' (saltándose la cuota)."""
    _login(client, COMPANY_A)
    resp = client.post("/cotizacion-pdf", json={
        "modo": "hack",
        "datosGenerales": {"cliente": "C", "proyecto": "P"},
        "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 10}],
    })
    assert resp.status_code == 400
    assert db.writes == []


# ── Starter: ?numero= NO es edición menor ──

def test_starter_get_numero_no_edicion_menor(client, monkeypatch):
    monkeypatch.setattr("cotizador.middleware._load_company_from_db", _loader("starter"))
    _login(client, COMPANY_A)
    resp = client.get(f"/cotizacion-pdf?numero={FOLIO_A_R1}")
    assert resp.status_code == 200
    # El template no marca modo de edición menor → no bloquea campos.
    assert "MODO_EDICION_MENOR = false" in _body(resp)


def test_pro_get_numero_edicion_menor(client):
    _login(client, COMPANY_A)
    resp = client.get(f"/cotizacion-pdf?numero={FOLIO_A_R1}")
    assert resp.status_code == 200
    assert "MODO_EDICION_MENOR = true" in _body(resp)


def test_starter_edicion_no_fuerza_campos(client, monkeypatch, db):
    """Starter editando desde ?numero=: envía el payload real de la pantalla.

    El modo viene como 'edicion_menor' (porque hay folio), NO 'crear', así que
    el servidor conserva el mismo folio, no registra PDF (no gasta cuota) y no
    pisa cliente/vendedor con los del original.
    """
    monkeypatch.setattr("cotizador.middleware._load_company_from_db", _loader("starter"))
    item = db.items[0]
    item["datosGenerales"].update(cliente="Cliente Original", vendedor="Vend Original")
    # Cuota llena: si el modo se interpretara como 'crear', respondería 403.
    db.contar_pdfs_mes = lambda company_id: 999999
    _login(client, COMPANY_A)
    resp = client.post("/cotizacion-pdf", json={
        "numeroCotizacion": FOLIO_A_R1,
        "modo": "edicion_menor",
        "revisionDe": "",
        "datosGenerales": {
            "cliente": "NuevoCliente",
            "vendedor": "NuevoVend",
            "proyecto": "Proy",
            "revision": "1",
        },
        "items": [{"descripcion": "a", "cantidad": 1, "precio_unitario": 10}],
    })
    assert resp.status_code == 200
    assert db.last_guardar["numeroCotizacion"] == FOLIO_A_R1
    assert db.registros_pdf == []
    dg = db.last_guardar["datosGenerales"]
    assert dg["cliente"] == "NuevoCliente"
    assert dg["vendedor"] == "NuevoVend"


# ── verificado:false y totales de R2 ──

def test_post_nueva_revision_verificado_false_500(client, db):
    """Si la búsqueda de revisiones falla (verificado false), no se escribe."""
    db.resultados_busqueda = []
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_A_R1)
    assert resp.status_code == 500
    assert db.writes == []


def test_post_nueva_revision_totales_no_cero(client, db):
    _login(client, COMPANY_A)
    resp = _post_revision(client, FOLIO_A_R1)
    assert resp.status_code == 200
    totales = db.last_guardar["totales"]
    assert totales["subtotal"] == pytest.approx(10.0)
    assert totales["total"] == pytest.approx(11.6)
    # La revisión hereda items con total no cero (no los recalculó a 0).
    assert db.last_guardar["items"][0]["total"] == pytest.approx(10.0)


def test_preparar_nueva_revision_simple_preserva_totales(client, db):
    """preparar_datos_nueva_revision no pone en 0 los totales de una simple."""
    item = db.items[0]
    item["items"] = [{"descripcion": "Pieza", "cantidad": 2, "precio_unitario": 50.0, "total": 100.0}]
    resultado = app_module.preparar_datos_nueva_revision(item)
    assert resultado is not None
    assert resultado["items"][0]["total"] == 100.0


# ── Render: Editar oculto en antigua/importada ──

def test_ver_cotizacion_editar_visible_normal(client, db):
    _login(client, COMPANY_A)
    resp = client.get(f"/ver/{FOLIO_A_R1}")
    assert resp.status_code == 200
    assert "js-editar-cotizacion" in _body(resp)


def test_ver_cotizacion_editar_oculto_antigua(client, db):
    db.items[0]["es_antigua"] = True
    _login(client, COMPANY_A)
    resp = client.get(f"/ver/{FOLIO_A_R1}")
    assert resp.status_code == 200
    assert "js-editar-cotizacion" not in _body(resp)


def test_ver_cotizacion_editar_oculto_importada(client, db):
    db.items[0]["es_importado"] = True
    _login(client, COMPANY_A)
    resp = client.get(f"/ver/{FOLIO_A_R1}")
    assert resp.status_code == 200
    assert "js-editar-cotizacion" not in _body(resp)


def test_home_importado_sin_editar(client, db):
    db.importados_result = {"resultados": [{
        "id": "imp1",
        "nombre_archivo": "IMPORTADO-001.pdf",
        "created_at": "2024-01-01",
        "snippet": "",
    }]}
    _login(client, COMPANY_A)
    resp = client.get("/")
    assert resp.status_code == 200
    body = _body(resp)
    assert "IMPORTADO-001.pdf" in body
    assert "/cotizacion-pdf?numero=IMPORTADO-001.pdf" not in body
