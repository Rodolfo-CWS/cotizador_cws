"""Alta de empresa: correo nuevo, correo ya registrado y rollback.

No tocan Supabase. El cliente de Auth y el cliente admin van mockeados.
El caso de producción (2026-10-29) es un sign_up repetido: Supabase responde
200 con `identities` vacío y un id que no existe en auth.users.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Blueprint, Flask

from cotizador.blueprints.auth_bp import (
    EMAIL_YA_REGISTRADO,
    _auth_user_exists,
    _identities_vacias,
    _is_auth_user_missing,
    auth_bp,
)
from supabase_auth.errors import AuthApiError

ROOT = Path(__file__).resolve().parents[1]

USER_ID = "11111111-1111-4111-8111-111111111111"
FAKE_ID = "22222222-2222-4222-8222-222222222222"
COMPANY_ID = "33333333-3333-4333-8333-333333333333"
EMAIL = "ya.registrado@example.com"


def _form(**overrides):
    data = {
        "email": "nuevo@example.com",
        "password": "secret123",
        "full_name": "Ana Pérez",
        "company_name": "ACME Sa de Cv",
        "company_slug": "acme-sa-de-cv",
        "address": "Calle 1",
        "phone": "5551234567",
        "footer_text": "Valida 30 dias",
        "iva_rate": "16.00",
    }
    data.update(overrides)
    return data


class _Query:
    def __init__(self, store, table):
        self.store = store
        self.table = table
        self.op = None
        self.payload = None
        self.filters = {}

    def insert(self, data):
        self.op = "insert"
        self.payload = data
        return self

    def delete(self):
        self.op = "delete"
        return self

    def select(self, *args, **kwargs):
        self.op = "select"
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, _n):
        return self

    def execute(self):
        call = {
            "table": self.table,
            "op": self.op,
            "payload": self.payload,
            "filters": dict(self.filters),
        }
        self.store.calls.append(call)
        handler = self.store.handlers.get((self.table, self.op))
        if handler:
            return handler(call)
        if self.op == "insert" and self.table == "companies":
            row = dict(self.payload or {})
            row["id"] = COMPANY_ID
            return SimpleNamespace(data=[row])
        if self.op == "insert" and self.table == "profiles":
            return SimpleNamespace(data=[dict(self.payload or {})])
        return SimpleNamespace(data=[])


class _Store:
    def __init__(self):
        self.calls = []
        self.handlers = {}

    def table(self, name):
        return _Query(self, name)


class _AdminAuth:
    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error
        self.deleted = []

    def get_user_by_id(self, uid):
        if self.error:
            raise self.error
        return SimpleNamespace(user=self.user)

    def delete_user(self, uid, should_soft_delete=False):
        self.deleted.append(uid)


class _AdminClient:
    def __init__(self, store, admin_auth):
        self._store = store
        self.auth = SimpleNamespace(admin=admin_auth)

    def table(self, name):
        return self._store.table(name)


class _AuthClient:
    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error
        self.calls = []
        self.auth = self

    def sign_up(self, payload):
        self.calls.append(payload)
        if self.error:
            raise self.error
        return SimpleNamespace(user=self.user)


def _user(user_id, identities, email="nuevo@example.com"):
    return SimpleNamespace(id=user_id, email=email, identities=identities)


def _client(monkeypatch, *, auth_user, admin_user=None, admin_error=None,
            sign_up_error=None, forbid_admin=False):
    store = _Store()
    admin_auth = _AdminAuth(user=admin_user, error=admin_error)
    auth_client = _AuthClient(user=auth_user, error=sign_up_error)
    admin_client = _AdminClient(store, admin_auth)

    monkeypatch.setattr(
        "cotizador.blueprints.auth_bp.get_supabase_auth_client",
        lambda: auth_client,
    )

    def _admin():
        if forbid_admin:
            raise AssertionError("el alta repetida no debe usar el cliente admin")
        return admin_client

    monkeypatch.setattr(
        "cotizador.blueprints.auth_bp.get_supabase_admin_client",
        _admin,
    )

    app = Flask(__name__, template_folder=str(ROOT / "templates"))
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(auth_bp)
    # El alta redirige a company.profile. Basta el endpoint, sin el panel real.
    company = Blueprint("company", __name__, url_prefix="/admin/company")

    @company.route("/profile")
    def profile():
        return "perfil"

    app.register_blueprint(company)
    return app.test_client(), store, admin_auth, auth_client


def _ops(store):
    return [(c["table"], c["op"]) for c in store.calls]


def test_identities_vacias_es_el_alta_repetida_de_gotrue():
    """sanitizeUser deja identities en [] y un id que no está en auth.users."""
    assert _identities_vacias(_user(FAKE_ID, [])) is True
    assert _identities_vacias(_user(USER_ID, [{"provider": "email"}])) is False
    assert _identities_vacias(_user(USER_ID, None)) is False
    assert _is_auth_user_missing(
        AuthApiError("User not found", 404, "user_not_found")
    )
    assert not _is_auth_user_missing(AuthApiError("Not Found", 404, None))
    assert not _is_auth_user_missing(RuntimeError("connection reset"))


def test_auth_user_exists_exige_el_mismo_id():
    admin = _AdminClient(
        _Store(),
        _AdminAuth(user=SimpleNamespace(id=USER_ID)),
    )
    assert _auth_user_exists(admin, USER_ID) is True
    assert _auth_user_exists(admin, FAKE_ID) is False

    missing = _AdminClient(
        _Store(),
        _AdminAuth(error=AuthApiError("User not found", 404, "user_not_found")),
    )
    assert _auth_user_exists(missing, FAKE_ID) is False

    with pytest.raises(RuntimeError):
        _auth_user_exists(
            _AdminClient(_Store(), _AdminAuth(error=RuntimeError("connection reset"))),
            USER_ID,
        )


def test_registro_email_nuevo_crea_compania_y_perfil(monkeypatch):
    """Camino feliz: el id devuelto existe y se crea compañía + perfil admin."""
    client, store, admin_auth, auth_client = _client(
        monkeypatch,
        auth_user=_user(USER_ID, [{"id": "ident-1", "provider": "email"}]),
        admin_user=SimpleNamespace(id=USER_ID, email="nuevo@example.com"),
    )

    resp = client.post("/auth/register", data=_form(plan="business"))

    assert resp.status_code == 302
    assert resp.location.endswith("/admin/company/profile")
    assert len(auth_client.calls) == 1
    assert auth_client.calls[0]["email"] == "nuevo@example.com"
    assert ("companies", "insert") in _ops(store)
    assert ("profiles", "insert") in _ops(store)
    assert ("companies", "delete") not in _ops(store)
    assert ("profiles", "delete") not in _ops(store)
    assert admin_auth.deleted == []

    company = next(c for c in store.calls if c["op"] == "insert" and c["table"] == "companies")
    assert company["payload"]["name"] == "ACME Sa de Cv"
    assert company["payload"]["slug"] == "acme-sa-de-cv"
    assert company["payload"]["plan"] == "starter"
    assert company["payload"]["footer_text"] == "Valida 30 dias"
    assert company["payload"]["address"] == "Calle 1"

    profile = next(c for c in store.calls if c["op"] == "insert" and c["table"] == "profiles")
    assert profile["payload"]["id"] == USER_ID
    assert profile["payload"]["company_id"] == COMPANY_ID
    assert profile["payload"]["role"] == "admin"
    assert profile["payload"]["full_name"] == "Ana Pérez"

    with client.session_transaction() as sess:
        assert sess["user_id"] == USER_ID
        assert sess["company_id"] == COMPANY_ID
        assert sess["user_role"] == "admin"


def test_registro_email_ya_registrado_identities_vacias_no_crea_nada(monkeypatch):
    """Producción: user_repeated_signup devuelve identities [] y un id ficticio."""
    client, store, admin_auth, auth_client = _client(
        monkeypatch,
        auth_user=_user(FAKE_ID, [], email=EMAIL),
        forbid_admin=True,
    )

    resp = client.post(
        "/auth/register",
        data=_form(email=EMAIL, company_name="ACME Sa de Cv"),
    )

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert EMAIL_YA_REGISTRADO in body
    assert "error-message" in body
    assert store.calls == []
    assert admin_auth.deleted == []
    assert len(auth_client.calls) == 1
    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "company_id" not in sess


def test_fallo_al_verificar_usuario_no_crea_compania(monkeypatch):
    """Un 404 que no es «user not found» no se presenta como correo ya usado."""
    client, store, admin_auth, _auth = _client(
        monkeypatch,
        auth_user=_user(USER_ID, [{"provider": "email"}]),
        admin_error=AuthApiError("Not Found", 404, None),
    )

    resp = client.post("/auth/register", data=_form())

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Error al registrarse" in body
    assert "ya está registrado" not in body
    assert ("companies", "insert") not in _ops(store)
    assert ("profiles", "insert") not in _ops(store)
    assert admin_auth.deleted == []


def test_registro_email_ya_registrado_id_inexistente_no_crea_nada(monkeypatch):
    """Si identities no viene vacío, igual se rechaza un id que no está en auth.users."""
    client, store, admin_auth, _auth = _client(
        monkeypatch,
        auth_user=_user(
            FAKE_ID,
            [{"provider": "email", "id": "placeholder"}],
            email=EMAIL,
        ),
        admin_error=AuthApiError("User not found", 404, "user_not_found"),
    )

    resp = client.post("/auth/register", data=_form(email=EMAIL))

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert EMAIL_YA_REGISTRADO in body
    assert ("companies", "insert") not in _ops(store)
    assert ("profiles", "insert") not in _ops(store)
    assert admin_auth.deleted == []


def test_registro_usuario_con_perfil_no_crea_otra_compania(monkeypatch):
    client, store, admin_auth, _auth = _client(
        monkeypatch,
        auth_user=_user(USER_ID, [{"provider": "email"}]),
        admin_user=SimpleNamespace(id=USER_ID),
    )
    store.handlers[("profiles", "select")] = lambda _call: SimpleNamespace(
        data=[{"id": USER_ID}]
    )

    resp = client.post("/auth/register", data=_form(email=EMAIL))

    assert resp.status_code == 200
    assert EMAIL_YA_REGISTRADO in resp.get_data(as_text=True)
    assert ("companies", "insert") not in _ops(store)
    assert ("profiles", "insert") not in _ops(store)
    assert admin_auth.deleted == []


def test_registro_falla_a_mitad_revierte_compania_perfil_y_usuario(monkeypatch):
    """Si el perfil falla después de crear la compañía, no queda nada a medias."""
    client, store, admin_auth, _auth = _client(
        monkeypatch,
        auth_user=_user(USER_ID, [{"provider": "email"}]),
        admin_user=SimpleNamespace(id=USER_ID),
    )

    def _falla_perfil(_call):
        raise RuntimeError("fallo al crear el perfil")

    store.handlers[("profiles", "insert")] = _falla_perfil

    resp = client.post("/auth/register", data=_form())

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "fallo al crear el perfil" in body
    assert "ya está registrado" not in body
    assert ("companies", "insert") in _ops(store)
    assert ("profiles", "delete") in _ops(store)

    company_deletes = [
        c for c in store.calls if c["table"] == "companies" and c["op"] == "delete"
    ]
    profile_deletes = [
        c for c in store.calls if c["table"] == "profiles" and c["op"] == "delete"
    ]
    assert len(company_deletes) == 1
    assert company_deletes[0]["filters"]["id"] == COMPANY_ID
    assert len(profile_deletes) == 1
    assert profile_deletes[0]["filters"]["id"] == USER_ID
    assert admin_auth.deleted == [USER_ID]

    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "company_id" not in sess


def test_registro_slug_duplicado_no_dice_que_el_correo_existe(monkeypatch):
    """Un unique de slug no es un correo ya registrado, y no deja usuario de Auth."""
    client, store, admin_auth, _auth = _client(
        monkeypatch,
        auth_user=_user(USER_ID, [{"provider": "email"}]),
        admin_user=SimpleNamespace(id=USER_ID),
    )

    def _slug(_call):
        raise RuntimeError(
            'duplicate key value violates unique constraint "companies_slug_key"'
        )

    store.handlers[("companies", "insert")] = _slug

    resp = client.post("/auth/register", data=_form())

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "ya está en uso" in body
    assert "acme-sa-de-cv" in body
    assert "ya está registrado" not in body
    assert ("companies", "delete") not in _ops(store)
    assert ("profiles", "insert") not in _ops(store)
    assert admin_auth.deleted == [USER_ID]


def test_signup_autoconfirm_user_already_registered(monkeypatch):
    """Con autoconfirm, Supabase sí lanza 'User already registered'."""
    client, store, admin_auth, _auth = _client(
        monkeypatch,
        auth_user=None,
        sign_up_error=AuthApiError(
            "User already registered", 422, "user_already_exists"
        ),
        forbid_admin=True,
    )

    resp = client.post("/auth/register", data=_form(email=EMAIL))

    assert resp.status_code == 200
    assert EMAIL_YA_REGISTRADO in resp.get_data(as_text=True)
    assert store.calls == []
    assert admin_auth.deleted == []
