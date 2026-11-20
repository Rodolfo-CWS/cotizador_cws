'''Tests para drafts con service_role y aislamiento de compañías.'''
import pytest
import supabase_manager
from supabase_manager import SupabaseManager

COMPANY_A = '00000000-0000-0000-0000-0000000000aa'
COMPANY_B = '00000000-0000-0000-0000-0000000000bb'

class FakeResponse:
    def __init__(self, data):
        self.data = data

class FakeTable:
    def __init__(self, name, supabase):
        self.name = name
        self.supabase = supabase
        self.operation = None
        self.payload = None
        self.filters = []
        self.order_clauses = []
        self.selected_columns = None

    def select(self, *columns):
        self.operation = 'select'
        self.selected_columns = columns
        return self

    def insert(self, payload):
        self.operation = 'insert'
        self.payload = dict(payload)
        return self

    def update(self, payload):
        self.operation = 'update'
        self.payload = dict(payload)
        return self

    def delete(self):
        self.operation = 'delete'
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def order(self, column, desc=False):
        self.order_clauses.append((column, desc))
        return self

    def _filtered(self):
        rows = list(self.supabase.drafts)
        for col, val in self.filters:
            rows = [r for r in rows if r.get(col) == val]
        if self.order_clauses:
            for col, desc in self.order_clauses:
                rows = sorted(rows, key=lambda x: x.get(col, ''), reverse=desc)
        return rows

    def execute(self):
        if self.operation == 'select':
            rows = self._filtered()
            if self.selected_columns and '*' not in self.selected_columns:
                return FakeResponse([{k: r.get(k) for k in self.selected_columns} for r in rows])
            return FakeResponse(rows)
        if self.operation == 'insert':
            if self.supabase.raise_on_insert:
                raise Exception('insert failed')
            new_row = dict(self.payload)
            for row in self.supabase.drafts:
                if row.get('id') == new_row.get('id'):
                    raise Exception('duplicate key value violates unique constraint')
            self.supabase.drafts.append(new_row)
            return FakeResponse([new_row])
        if self.operation == 'update':
            if self.supabase.raise_on_update:
                raise Exception('update failed')
            rows = self._filtered()
            if not rows:
                return FakeResponse([])
            for row in rows:
                row.update(self.payload)
            return FakeResponse(rows)
        if self.operation == 'delete':
            rows = self._filtered()
            if not rows:
                return FakeResponse([])
            ids = {r.get('id') for r in rows}
            self.supabase.drafts[:] = [r for r in self.supabase.drafts if r.get('id') not in ids]
            return FakeResponse(rows)
        return FakeResponse([])

class FakeSupabase:
    def __init__(self, drafts=None):
        self.drafts = drafts if drafts is not None else []
        self.table_calls = []
        self.create_calls = []
        self.raise_on_insert = False
        self.raise_on_update = False

    def table(self, name):
        self.table_calls.append(name)
        if name == 'drafts':
            return FakeTable(name, self)
        raise AssertionError(f'Unexpected table: {name}')

class AnonClient:
    def table(self, name):
        raise AssertionError('anon supabase_client used')

@pytest.fixture(autouse=True)
def use_tmp_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

def _make_manager(monkeypatch, fake, service_key='service-secret'):
    monkeypatch.setenv('SUPABASE_SERVICE_KEY', service_key)
    def fake_create(url, key):
        fake.create_calls.append((url, key))
        return fake
    monkeypatch.setattr(supabase_manager, 'create_client', fake_create)
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.modo_offline = False
    mgr.supabase_url = 'https://example.supabase.co'
    mgr.supabase_client = AnonClient()
    return mgr

def _draft(id_, company, numero):
    return {
        'id': id_,
        'vendedor': 'VEN',
        'nombre': 'draft',
        'datos': {'datosGenerales': {'numeroCotizacion': numero}},
        'company_id': company,
        'timestamp': 1000,
        'fecha_creacion': '2024-01-01T00:00:00',
        'ultima_modificacion': '2024-01-01T00:00:00'
    }

def test_drafts_client_created_once_with_service_key(monkeypatch):
    fake = FakeSupabase()
    mgr = _make_manager(monkeypatch, fake, service_key='service-secret')
    c1 = mgr._drafts_client()
    c2 = mgr._drafts_client()
    assert c1 is fake
    assert c2 is fake
    assert len(fake.create_calls) == 1
    assert fake.create_calls[0] == ('https://example.supabase.co', 'service-secret')
    assert mgr._drafts_service_client is fake

def test_drafts_client_without_service_key_returns_none(monkeypatch, capsys):
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.modo_offline = False
    mgr.supabase_url = 'https://example.supabase.co'
    mgr.supabase_client = AnonClient()
    result = mgr._drafts_client()
    captured = capsys.readouterr()
    assert result is None
    assert 'SUPABASE_SERVICE_KEY no configurada' in captured.out
    assert 'NO se persistirán' in captured.out

def test_drafts_client_create_exception_hides_key(monkeypatch, capsys):
    monkeypatch.setenv('SUPABASE_SERVICE_KEY', 'SUPER-SECRET-KEY')
    def fake_create(url, key):
        raise Exception(f'API error apikey={key}')
    monkeypatch.setattr(supabase_manager, 'create_client', fake_create)
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.modo_offline = False
    mgr.supabase_url = 'https://example.supabase.co'
    mgr.supabase_client = AnonClient()
    result = mgr._drafts_client()
    captured = capsys.readouterr()
    assert result is None
    assert 'SUPER-SECRET-KEY' not in captured.out

def test_company_isolation_drafts(monkeypatch):
    fake = FakeSupabase(drafts=[_draft('draft_a', COMPANY_A, 'COT-A'), _draft('draft_b', COMPANY_B, 'COT-B')])
    mgr = _make_manager(monkeypatch, fake)

    lista = mgr.listar_drafts(company_id=COMPANY_A)
    assert [d['id'] for d in lista] == ['draft_a']

    assert mgr.obtener_draft('draft_b', company_id=COMPANY_A) is None

    res_del = mgr.eliminar_draft('draft_b', company_id=COMPANY_A)
    assert res_del['success'] is True
    assert fake.drafts[1]['company_id'] == COMPANY_B

    res_num = mgr.eliminar_drafts_por_numero_cotizacion('COT-B', company_id=COMPANY_A)
    assert res_num['success'] is True
    assert fake.drafts[1]['company_id'] == COMPANY_B

    res_guardar = mgr.guardar_draft({
        'draft_id': 'draft_b',
        'company_id': COMPANY_A,
        'datos': {'datosGenerales': {'cliente': 'X'}}
    })
    assert res_guardar['success'] is True
    assert res_guardar['persistido'] is False
    assert fake.drafts[1]['company_id'] == COMPANY_B

def test_falsy_company_id_never_uses_supabase(monkeypatch):
    fake = FakeSupabase()
    mgr = _make_manager(monkeypatch, fake)

    assert mgr.listar_drafts(company_id=None) == []
    assert mgr.obtener_draft('draft_a', company_id=None) is None
    assert mgr.eliminar_draft('draft_a', company_id=None) == {'success': False, 'error': 'company_id requerido'}
    assert mgr.guardar_draft({'draft_id': 'draft_a', 'company_id': None, 'datos': {}}) == {'success': False, 'error': 'company_id requerido'}
    assert mgr.eliminar_drafts_por_numero_cotizacion('COT-A', company_id='') == {'success': False, 'error': 'company_id requerido'}
    assert fake.table_calls == []

def test_guardar_draft_persistido_true(monkeypatch):
    fake = FakeSupabase()
    mgr = _make_manager(monkeypatch, fake)
    result = mgr.guardar_draft({
        'draft_id': 'draft-1',
        'company_id': COMPANY_A,
        'datos': {'datosGenerales': {'cliente': 'Cliente', 'proyecto': 'Proyecto'}}
    })
    assert result['success'] is True
    assert result['persistido'] is True
    assert 'advertencia' not in result
    assert len(fake.drafts) == 1
    assert fake.drafts[0]['id'] == 'draft-1'

def test_guardar_draft_persistido_false_and_advertencia(monkeypatch, capsys):
    fake = FakeSupabase()
    fake.raise_on_insert = True
    mgr = _make_manager(monkeypatch, fake)
    result = mgr.guardar_draft({
        'draft_id': 'draft-1',
        'company_id': COMPANY_A,
        'datos': {'datosGenerales': {'cliente': 'Cliente'}}
    })
    captured = capsys.readouterr()
    assert result['success'] is True
    assert result['persistido'] is False
    assert result['advertencia'] == 'El borrador solo se guardó localmente en el servidor y puede perderse. Avisa al administrador.'
    assert '[DRAFT] ❌ ERROR CRITICO' in captured.out
    assert len(fake.drafts) == 0

def test_guardar_draft_update_own_company(monkeypatch):
    draft = _draft('draft_a', COMPANY_A, 'COT-A')
    fake = FakeSupabase(drafts=[draft])
    mgr = _make_manager(monkeypatch, fake)
    result = mgr.guardar_draft({
        'draft_id': 'draft_a',
        'company_id': COMPANY_A,
        'datos': {'datosGenerales': {'cliente': 'Nuevo Cliente'}}
    })
    assert result['persistido'] is True
    assert fake.drafts[0]['datos']['datosGenerales']['cliente'] == 'Nuevo Cliente'
    assert fake.drafts[0]['company_id'] == COMPANY_A


def test_sin_service_key_no_usa_anon_y_respaldo_json_aisla_companias(monkeypatch, capsys):
    """Sin llave service: jamás se usa el cliente anon; el respaldo JSON sigue aislado por compañía."""
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.modo_offline = False
    mgr.supabase_url = 'https://example.supabase.co'
    mgr.supabase_client = AnonClient()  # lanza AssertionError si se usa

    res_a = mgr.guardar_draft({'draft_id': 'draft_a', 'company_id': COMPANY_A,
                               'datos': {'datosGenerales': {'cliente': 'A'}}})
    res_b = mgr.guardar_draft({'draft_id': 'draft_b', 'company_id': COMPANY_B,
                               'datos': {'datosGenerales': {'cliente': 'B'}}})
    assert res_a['persistido'] is False and res_b['persistido'] is False
    assert 'ERROR CRITICO' in capsys.readouterr().out

    assert [d['id'] for d in mgr.listar_drafts(company_id=COMPANY_A)] == ['draft_a']
    assert mgr.obtener_draft('draft_b', company_id=COMPANY_A) is None
    assert mgr.obtener_draft('draft_a', company_id=COMPANY_A)['id'] == 'draft_a'
    mgr.eliminar_draft('draft_b', company_id=COMPANY_A)
    assert mgr.obtener_draft('draft_b', company_id=COMPANY_B) is not None


def test_eliminar_por_numero_solo_borra_la_propia_compania(monkeypatch):
    fake = FakeSupabase(drafts=[_draft('draft_a', COMPANY_A, 'COT-1'), _draft('draft_b', COMPANY_B, 'COT-1')])
    mgr = _make_manager(monkeypatch, fake)
    res = mgr.eliminar_drafts_por_numero_cotizacion('COT-1', company_id=COMPANY_A)
    assert res['success'] is True
    assert [d['id'] for d in fake.drafts] == ['draft_b']
