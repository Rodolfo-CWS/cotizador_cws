"""Pruebas del endurecimiento de billing (webhook, créditos, filas de PG).

No tocan Stripe ni Supabase reales: la base y el SDK van mockeados.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

from cotizador.db_rows import row_scalar, row_to_dict
from cotizador.plans import (
    FASTQUOTE_PACK_ESTIMATES,
    PLAN_PRO,
    PLAN_STARTER,
    fast_quote_consumes_credit,
    fast_quote_quota_blocked,
)

ROOT = Path(__file__).resolve().parents[1]


class FakeCursor:
    def __init__(self, row, colnames=None):
        self.row = row
        if colnames is None and isinstance(row, dict):
            colnames = list(row.keys())
        self.description = [(name,) for name in (colnames or [])]
        self.sql = None
        self.params = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


class FakeConn:
    def __init__(self, cursor):
        self.closed = 0
        self._cursor = cursor
        self.commits = 0

    def cursor(self):
        return self._cursor

    def rollback(self):
        pass

    def commit(self):
        self.commits += 1


class _SigError(Exception):
    pass


class StripeHarness:
    """Módulo stripe mínimo para el webhook (sin red)."""

    SignatureVerificationError = _SigError

    def __init__(self, subscription=None, retrieve_error=None):
        self._subscription = subscription if subscription is not None else {}
        self._retrieve_error = retrieve_error

        harness = self

        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return json.loads(payload)

        class Subscription:
            @staticmethod
            def retrieve(sub_id):
                if harness._retrieve_error:
                    raise harness._retrieve_error
                return harness._subscription

        self.Webhook = Webhook
        self.Subscription = Subscription


def _company(**overrides):
    data = {
        'id': 'co_1',
        'plan': 'starter',
        'is_internal': False,
        'stripe_customer_id': 'cus_1',
        'stripe_subscription_id': 'sub_1',
        'fast_quote_pack_count': 0,
        'fast_quote_credits_remaining': 0,
    }
    data.update(overrides)
    return data


def _subscription(status='active', price='price_pro', sub_id='sub_1', plan='pro'):
    return {
        'id': sub_id,
        'status': status,
        'customer': 'cus_1',
        'metadata': {'plan': plan} if plan else {},
        'items': {
            'data': [{
                'price': {'id': price},
                'current_period_end': 1893456000,
            }]
        },
    }


def _event(event_type, obj, event_id='evt_1'):
    return {'id': event_id, 'type': event_type, 'data': {'object': obj}}


def _post_webhook(db, event, stripe, monkeypatch, claim=True,
                  by_id=None, by_sub=None, by_customer=None):
    """Dispara el webhook con Stripe, el claim y las lecturas de empresa mockeados."""
    from unittest.mock import patch

    from cotizador.blueprints.billing_bp import stripe_webhook_bp

    for key, value in {
        'STRIPE_PRICE_PRO': 'price_pro',
        'STRIPE_PRICE_BUSINESS': 'price_business',
        'STRIPE_PRICE_PRO_ANNUAL': 'price_pro_year',
        'STRIPE_PRICE_BUSINESS_ANNUAL': 'price_business_year',
    }.items():
        monkeypatch.setenv(key, value)

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.extensions['db_manager'] = db
    app.register_blueprint(stripe_webhook_bp)
    client = app.test_client()

    patches = [
        patch('cotizador.blueprints.billing_bp._stripe', return_value=stripe),
        patch('cotizador.blueprints.billing_bp._claim_stripe_event', return_value=claim),
        patch('cotizador.blueprints.billing_bp._company_by_id', return_value=by_id),
        patch('cotizador.blueprints.billing_bp._company_by_subscription', return_value=by_sub),
        patch('cotizador.blueprints.billing_bp._company_by_customer', return_value=by_customer),
        patch('cotizador.blueprints.billing_bp._release_stripe_event'),
    ]
    started = [p.start() for p in patches]
    try:
        resp = client.post(
            '/stripe/webhook',
            data=json.dumps(event),
            headers={'Stripe-Signature': 'test', 'Content-Type': 'application/json'},
        )
    finally:
        for p in patches:
            p.stop()
    release = started[-1]
    return resp, release


# ── Filas de PostgreSQL ──────────────────────────────────────────────

def test_row_to_dict_realdict_no_copia_las_llaves():
    """RealDictRow es un dict: zip(colnames, row) mapearía nombre→nombre."""
    row = {'id': 'uuid-1', 'is_internal': False, 'plan': 'pro'}
    colnames = list(row.keys())
    # El bug que se está corrigiendo: iterar el mapping produce las llaves.
    assert dict(zip(colnames, row))['is_internal'] == 'is_internal'
    mapped = row_to_dict(row, colnames)
    assert mapped['id'] == 'uuid-1'
    assert mapped['is_internal'] is False
    assert mapped['plan'] == 'pro'


def test_row_to_dict_tupla_y_lista():
    colnames = ['id', 'is_internal']
    assert row_to_dict(('uuid-1', False), colnames) == {'id': 'uuid-1', 'is_internal': False}
    assert row_to_dict(['uuid-1', True], colnames)['is_internal'] is True


def test_row_scalar_dict_y_tupla():
    assert row_scalar({'count': 7}) == 7
    assert row_scalar((7,)) == 7
    assert row_scalar(None) is None


def test_query_company_realdict_y_tupla():
    from cotizador.blueprints.billing_bp import _query_company

    cases = [
        {'id': 'uuid-1', 'is_internal': False, 'plan': 'pro'},
        ('uuid-1', False, 'pro'),
    ]
    for row in cases:
        colnames = ['id', 'is_internal', 'plan']
        cursor = FakeCursor(row, colnames=colnames)
        app = Flask(__name__)
        app.extensions['db_manager'] = SimpleNamespace(pg_connection=FakeConn(cursor))
        with app.app_context():
            got = _query_company('id = %s', ('uuid-1',))
        assert got['id'] == 'uuid-1'
        assert got['is_internal'] is False
        assert got['plan'] == 'pro'


def test_middleware_fallback_realdict(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    from cotizador.middleware import _load_company_from_db

    row = {'id': 'uuid-1', 'is_internal': False, 'plan': 'pro', 'name': 'Acme'}
    cursor = FakeCursor(row)
    manager = SimpleNamespace(pg_connection=FakeConn(cursor))
    got = _load_company_from_db(manager, 'uuid-1')
    assert got['id'] == 'uuid-1'
    assert got['is_internal'] is False
    assert got['name'] == 'Acme'


def _manager_with(cursor):
    from supabase_manager import SupabaseManager

    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.pg_connection = FakeConn(cursor)
    mgr.supabase_url = None
    return mgr


def test_update_company_devuelve_valores_reales():
    row = {'id': 'co_1', 'plan': 'pro', 'is_internal': False}
    cursor = FakeCursor(row)
    mgr = _manager_with(cursor)
    got = mgr.update_company('co_1', {'plan': 'pro'})
    assert got['id'] == 'co_1'
    assert got['plan'] == 'pro'
    assert got['is_internal'] is False
    assert mgr.pg_connection.commits == 1


def test_contar_estimaciones_lee_realdict(monkeypatch):
    """COUNT(*) con RealDictCursor no se puede leer como tupla [0]."""
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    cursor = FakeCursor({'count': 4})
    mgr = _manager_with(cursor)
    assert mgr.contar_estimaciones_fast_quote_mes('co_1') == 4


def test_get_company_by_id_pg_incluye_subscription(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    row = {'id': 'co_1', 'plan': 'pro', 'stripe_subscription_id': 'sub_real'}
    cursor = FakeCursor(row)
    mgr = _manager_with(cursor)
    got = mgr.get_company_by_id('co_1')
    assert got['stripe_subscription_id'] == 'sub_real'
    assert got['id'] == 'co_1'
    assert 'stripe_subscription_id' in cursor.sql


# ── Cuota Fast Quote ─────────────────────────────────────────────────

def test_cuota_no_cuenta_los_creditos_dos_veces():
    # Pro, base 20, 100 créditos. El bug bloqueaba alrededor del uso 70
    # (tope = base + saldo, y cada uso extra también restaba un crédito).
    # A los 70 usos se habrían gastado 50 créditos y quedarían 50.
    assert fast_quote_quota_blocked(70, 20, 50) is False
    assert fast_quote_quota_blocked(19, 20, 0) is False
    assert fast_quote_quota_blocked(20, 20, 0) is True
    assert fast_quote_quota_blocked(20, 20, 1) is False
    # 20 de base + 100 créditos = 120 estimaciones.
    assert fast_quote_quota_blocked(119, 20, 1) is False
    assert fast_quote_quota_blocked(120, 20, 0) is True
    assert fast_quote_quota_blocked(500, None, 0) is False


def test_credito_se_consume_solo_despues_de_la_base():
    assert fast_quote_consumes_credit(20, 20) is False
    assert fast_quote_consumes_credit(21, 20) is True
    assert fast_quote_consumes_credit(100, None) is False


def test_app_no_suma_creditos_al_tope():
    source = (ROOT / 'app.py').read_text(encoding='utf-8')
    assert 'fast_quote_quota_blocked' in source
    assert 'fast_quote_consumes_credit' in source
    assert 'consumir_credito_fast_quote' in source
    assert 'max_estimates + credits' not in source
    assert 'max(0, credits - 1)' not in source


def test_consumir_credito_es_atomico():
    cursor = FakeCursor({'fast_quote_credits_remaining': 4})
    mgr = _manager_with(cursor)
    assert mgr.consumir_credito_fast_quote('co_1') is True
    assert 'GREATEST' in cursor.sql
    assert 'COALESCE(fast_quote_credits_remaining, 0) - 1' in cursor.sql
    assert cursor.params == ('co_1',)


def test_consumir_credito_en_cero_no_cae_al_sdk():
    cursor = FakeCursor(None)
    mgr = _manager_with(cursor)
    mgr.supabase_url = 'https://example.supabase.co'
    assert mgr.consumir_credito_fast_quote('co_1') is False
    assert mgr.pg_connection.commits == 1


def test_acreditar_paquete_es_atomico():
    cursor = FakeCursor({
        'id': 'co_1',
        'fast_quote_pack_count': 2,
        'fast_quote_credits_remaining': 200,
    })
    mgr = _manager_with(cursor)
    got = mgr.acreditar_paquete_fast_quote('co_1', FASTQUOTE_PACK_ESTIMATES)
    assert got['id'] == 'co_1'
    assert got['fast_quote_credits_remaining'] == 200
    assert got['fast_quote_pack_count'] == 2
    assert 'COALESCE(fast_quote_pack_count, 0) + 1' in cursor.sql
    assert 'COALESCE(fast_quote_credits_remaining, 0) + %s' in cursor.sql
    assert cursor.params == (FASTQUOTE_PACK_ESTIMATES, 'co_1')


def test_migracion_v12_tiene_updates_atomicos_e_idempotentes():
    sql = (ROOT / 'migrations' / 'v12_billing_hardening.sql').read_text(encoding='utf-8')
    assert 'CREATE OR REPLACE FUNCTION public.consumir_credito_fast_quote' in sql
    assert 'CREATE OR REPLACE FUNCTION public.acreditar_paquete_fast_quote' in sql
    assert 'GREATEST' in sql
    assert 'ADD COLUMN IF NOT EXISTS fast_quote_credits_remaining' in sql
    assert 'CREATE TABLE IF NOT EXISTS public.stripe_events' in sql
    assert 'REVOKE ALL ON FUNCTION' in sql


# ── Webhook ──────────────────────────────────────────────────────────

def test_checkout_activo_asigna_plan(monkeypatch):
    calls = []

    def update_company(cid, data):
        calls.append((cid, data))
        return {'id': cid}

    db = SimpleNamespace(update_company=update_company, acreditar_paquete_fast_quote=lambda *a: None)
    stripe = StripeHarness(_subscription(status='active'))
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'plan': 'pro'},
        'customer': 'cus_1',
        'subscription': 'sub_1',
        'payment_status': 'paid',
    })
    resp, _release = _post_webhook(
        db, event, stripe, monkeypatch, by_id=_company(),
    )
    assert resp.status_code == 200
    assert calls[0][0] == 'co_1'
    assert calls[0][1]['plan'] == PLAN_PRO
    assert calls[0][1]['subscription_status'] == 'active'
    assert calls[0][1]['stripe_subscription_id'] == 'sub_1'


def test_checkout_incompleto_no_asigna_plan(monkeypatch):
    calls = []

    def update_company(cid, data):
        calls.append(data)
        return {'id': cid}

    db = SimpleNamespace(update_company=update_company)
    stripe = StripeHarness(_subscription(status='incomplete'))
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'plan': 'pro'},
        'customer': 'cus_1',
        'subscription': 'sub_1',
        'payment_status': 'unpaid',
    })
    resp, _release = _post_webhook(db, event, stripe, monkeypatch, by_id=_company())
    assert resp.status_code == 200
    assert 'plan' not in calls[0]
    assert calls[0]['subscription_status'] == 'incomplete'
    assert calls[0]['stripe_subscription_id'] == 'sub_1'


def test_checkout_plan_desconocido_cae_a_starter(monkeypatch):
    calls = []

    def update_company(cid, data):
        calls.append(data)
        return {'id': cid}

    db = SimpleNamespace(update_company=update_company)
    stripe = StripeHarness(_subscription(status='active', price='price_rara', plan='no-existe'))
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'plan': 'no-existe'},
        'customer': 'cus_1',
        'subscription': 'sub_1',
    })
    resp, _release = _post_webhook(db, event, stripe, monkeypatch, by_id=_company())
    assert resp.status_code == 200
    assert calls[0]['plan'] == PLAN_STARTER


def test_checkout_interno_no_cambia_plan(monkeypatch):
    called = []
    db = SimpleNamespace(update_company=lambda *a, **k: called.append(a) or {'id': 'co_1'})
    stripe = StripeHarness(_subscription())
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'plan': 'pro'},
        'customer': 'cus_1',
        'subscription': 'sub_1',
    })
    resp, _release = _post_webhook(
        db, event, stripe, monkeypatch, by_id=_company(is_internal=True),
    )
    assert resp.status_code == 200
    assert called == []


def test_pack_se_acredita_una_vez_y_atomico(monkeypatch):
    credited = []

    def acreditar(cid, credits):
        credited.append((cid, credits))
        return {'id': cid, 'fast_quote_credits_remaining': credits}

    db = SimpleNamespace(
        acreditar_paquete_fast_quote=acreditar,
        update_company=lambda *a, **k: (_ for _ in ()).throw(AssertionError('read-modify-write')),
    )
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'type': 'fastquote_pack'},
        'payment_status': 'paid',
    })
    resp, _release = _post_webhook(
        db, event, StripeHarness(), monkeypatch, claim=True, by_id=_company(),
    )
    assert resp.status_code == 200
    assert credited == [('co_1', FASTQUOTE_PACK_ESTIMATES)]


def test_pack_duplicado_no_se_acredita(monkeypatch):
    credited = []
    db = SimpleNamespace(
        acreditar_paquete_fast_quote=lambda *a: credited.append(a),
    )
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'type': 'fastquote_pack'},
        'payment_status': 'paid',
    })
    resp, _release = _post_webhook(
        db, event, StripeHarness(), monkeypatch, claim=False, by_id=_company(),
    )
    assert resp.status_code == 200
    assert credited == []


def test_pack_sin_pago_no_se_acredita(monkeypatch):
    credited = []
    db = SimpleNamespace(acreditar_paquete_fast_quote=lambda *a: credited.append(a))
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'type': 'fastquote_pack'},
        'payment_status': 'unpaid',
    })
    resp, _release = _post_webhook(
        db, event, StripeHarness(), monkeypatch, by_id=_company(),
    )
    assert resp.status_code == 200
    assert credited == []


def test_fallo_al_acreditar_libera_el_claim(monkeypatch):
    db = SimpleNamespace(acreditar_paquete_fast_quote=lambda *a: None)
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'type': 'fastquote_pack'},
        'payment_status': 'paid',
    })
    resp, release = _post_webhook(
        db, event, StripeHarness(), monkeypatch, claim=True, by_id=_company(),
    )
    assert resp.status_code == 500
    release.assert_called_once_with('evt_1')


def test_subscription_updated_ignora_otra_suscripcion(monkeypatch):
    called = []
    db = SimpleNamespace(update_company=lambda *a, **k: called.append(a) or {'id': 'co_1'})
    event = _event('customer.subscription.updated', {
        'id': 'sub_vieja',
        'customer': 'cus_1',
        'status': 'incomplete_expired',
        'metadata': {},
        'items': {'data': []},
    })
    resp, _release = _post_webhook(
        db, event, StripeHarness(), monkeypatch,
        by_sub=None,
        by_customer=_company(stripe_subscription_id='sub_vigente', plan='pro'),
    )
    assert resp.status_code == 200
    assert called == []


def test_subscription_updated_past_due_no_baja_a_starter(monkeypatch):
    calls = []

    def update_company(cid, data):
        calls.append(data)
        return {'id': cid}

    db = SimpleNamespace(update_company=update_company)
    event = _event('customer.subscription.updated', _subscription(status='past_due'))
    resp, _release = _post_webhook(
        db, event, StripeHarness(), monkeypatch,
        by_sub=_company(plan='pro'),
    )
    assert resp.status_code == 200
    assert calls[0]['subscription_status'] == 'past_due'
    assert calls[0]['plan'] == PLAN_PRO


def test_subscription_updated_incomplete_expired_baja_a_starter(monkeypatch):
    calls = []

    def update_company(cid, data):
        calls.append(data)
        return {'id': cid}

    db = SimpleNamespace(update_company=update_company)
    event = _event(
        'customer.subscription.updated',
        _subscription(status='incomplete_expired'),
    )
    resp, _release = _post_webhook(
        db, event, StripeHarness(), monkeypatch, by_sub=_company(plan='pro'),
    )
    assert resp.status_code == 200
    assert calls[0]['plan'] == PLAN_STARTER


def test_subscription_deleted_de_otra_sub_no_degrada(monkeypatch):
    called = []
    db = SimpleNamespace(update_company=lambda *a, **k: called.append(a) or {'id': 'co_1'})
    event = _event('customer.subscription.deleted', {'id': 'sub_vieja', 'customer': 'cus_1'})
    resp, _release = _post_webhook(
        db, event, StripeHarness(), monkeypatch,
        by_sub=_company(stripe_subscription_id='sub_vigente', plan='pro'),
    )
    assert resp.status_code == 200
    assert called == []


def test_invoice_paid_sin_subscription_responde_500(monkeypatch):
    called = []
    db = SimpleNamespace(update_company=lambda *a, **k: called.append(a) or {'id': 'co_1'})
    stripe = StripeHarness(retrieve_error=RuntimeError('stripe caído'))
    event = _event('invoice.paid', {
        'parent': {'subscription_details': {'subscription': 'sub_1'}},
        'subscription': 'sub_1',
    })
    resp, release = _post_webhook(
        db, event, stripe, monkeypatch, claim=True, by_sub=_company(plan='pro'),
    )
    assert resp.status_code == 500
    assert called == []
    release.assert_called_once_with('evt_1')


def test_invoice_paid_usa_el_status_real_y_el_plan(monkeypatch):
    calls = []

    def update_company(cid, data):
        calls.append(data)
        return {'id': cid}

    db = SimpleNamespace(update_company=update_company)
    stripe = StripeHarness(_subscription(status='trialing'))
    event = _event('invoice.paid', {
        'parent': None,
        'subscription': 'sub_1',
    })
    resp, release = _post_webhook(
        db, event, stripe, monkeypatch, by_sub=_company(),
    )
    assert resp.status_code == 200
    assert calls[0]['subscription_status'] == 'trialing'
    assert calls[0]['plan'] == PLAN_PRO
    release.assert_not_called()


def test_sin_service_key_el_webhook_no_responde_500(monkeypatch):
    """Sin PG ni service key el dedup no está, pero el evento no debe ser 500."""
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    calls = []

    def update_company(cid, data):
        calls.append(data)
        return {'id': cid}

    db = SimpleNamespace(update_company=update_company, pg_connection=None)
    stripe = StripeHarness(_subscription(status='active'))
    event = _event('checkout.session.completed', {
        'metadata': {'company_id': 'co_1', 'plan': 'pro'},
        'customer': 'cus_1',
        'subscription': 'sub_1',
    })
    # claim=None hace que _post_webhook parchee el claim. Aquí queremos el real.
    from unittest.mock import patch

    from cotizador.blueprints.billing_bp import stripe_webhook_bp

    monkeypatch.setenv('STRIPE_PRICE_PRO', 'price_pro')
    app = Flask(__name__)
    app.extensions['db_manager'] = db
    app.register_blueprint(stripe_webhook_bp)
    client = app.test_client()
    with patch('cotizador.blueprints.billing_bp._stripe', return_value=stripe), \
            patch('cotizador.blueprints.billing_bp._company_by_id', return_value=_company()):
        resp = client.post(
            '/stripe/webhook',
            data=json.dumps(event),
            headers={'Stripe-Signature': 'test', 'Content-Type': 'application/json'},
        )
    assert resp.status_code == 200
    assert calls and calls[0]['plan'] == PLAN_PRO


def _claim_app(conn):
    app = Flask(__name__)
    app.extensions['db_manager'] = SimpleNamespace(pg_connection=conn)
    return app


def test_claim_inserta_on_conflict_y_distingue_duplicado():
    from cotizador.blueprints.billing_bp import _claim_stripe_event

    cursor = FakeCursor({'id': 'evt_1'})
    app = _claim_app(FakeConn(cursor))
    with app.app_context():
        assert _claim_stripe_event('evt_1') is True
    assert 'ON CONFLICT (id) DO NOTHING' in cursor.sql
    assert 'RETURNING id' in cursor.sql

    cursor.row = None
    with app.app_context():
        assert _claim_stripe_event('evt_1') is False


def test_claim_trata_23505_como_duplicado(monkeypatch):
    from cotizador.blueprints.billing_bp import _claim_stripe_event

    class UniqueErr(Exception):
        pgcode = '23505'

    class BoomCursor(FakeCursor):
        def execute(self, sql, params=None):
            self.sql = sql
            raise UniqueErr('duplicate key value violates unique constraint')

    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    app = _claim_app(FakeConn(BoomCursor(None)))
    with app.app_context():
        assert _claim_stripe_event('evt_1') is False


def test_claim_sdk_duplicado_no_es_500(monkeypatch):
    from unittest.mock import patch

    from cotizador.blueprints.billing_bp import _BillingDBError, _claim_stripe_event

    class InsertQuery:
        def __init__(self, error):
            self.error = error

        def execute(self):
            raise self.error

    class Client:
        def __init__(self, error):
            self.error = error

        def table(self, name):
            assert name == 'stripe_events'
            return self

        def insert(self, data):
            return InsertQuery(self.error)

    app = _claim_app(None)
    duplicate = Exception("duplicate key value violates unique constraint")
    duplicate.code = '23505'
    with app.app_context(), patch(
        'cotizador.blueprints.billing_bp._stripe_admin_client',
        return_value=Client(duplicate),
    ):
        assert _claim_stripe_event('evt_1') is False

    other = RuntimeError('timeout')
    with app.app_context(), patch(
        'cotizador.blueprints.billing_bp._stripe_admin_client',
        return_value=Client(other),
    ):
        with pytest.raises(_BillingDBError):
            _claim_stripe_event('evt_2')


def test_billing_no_usa_utcnow():
    source = (ROOT / 'cotizador' / 'blueprints' / 'billing_bp.py').read_text(encoding='utf-8')
    assert 'datetime.utcnow' not in source
    assert 'datetime.now(timezone.utc)' in source


# ── Borrado de empresa ───────────────────────────────────────────────

def _admin_client(db):
    from cotizador.blueprints.platform_admin_bp import platform_admin_bp

    app = Flask(__name__)
    app.secret_key = 'test'
    app.extensions['db_manager'] = db
    app.register_blueprint(platform_admin_bp)
    return app.test_client()


def _flashes(client):
    with client.session_transaction() as sess:
        return list(sess.get('_flashes', []))


def test_borrar_empresa_avisa_si_stripe_no_cancela(monkeypatch):
    from unittest.mock import patch

    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_x')
    db = SimpleNamespace(
        get_company_by_id=lambda cid: {'id': cid, 'stripe_subscription_id': 'sub_1'},
        delete_company=lambda cid: True,
    )
    client = _admin_client(db)
    with client.session_transaction() as sess:
        sess['superadmin_ok'] = True
    with patch('stripe.Subscription.delete', side_effect=RuntimeError('stripe down')):
        resp = client.post('/admin/companies/co_1/delete')
    assert resp.status_code == 302
    warnings = [msg for cat, msg in _flashes(client) if cat == 'warning']
    assert warnings
    assert 'Stripe' in warnings[0]


def test_borrar_empresa_sin_fallo_de_stripe_no_avisa(monkeypatch):
    from unittest.mock import patch

    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_x')
    db = SimpleNamespace(
        get_company_by_id=lambda cid: {'id': cid, 'stripe_subscription_id': 'sub_1'},
        delete_company=lambda cid: True,
    )
    client = _admin_client(db)
    with client.session_transaction() as sess:
        sess['superadmin_ok'] = True
    with patch('stripe.Subscription.delete', return_value={'id': 'sub_1'}):
        resp = client.post('/admin/companies/co_1/delete')
    assert resp.status_code == 302
    flashes = _flashes(client)
    assert any(cat == 'success' for cat, _msg in flashes)
    assert not any(cat == 'warning' for cat, _msg in flashes)
