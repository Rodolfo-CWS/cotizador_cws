"""
Definición de planes SaaS y sus features/límites.

Cada compañía (tabla public.companies.plan) tiene UNO de estos planes
(starter/pro/business). Además existe un plan virtual `internal` para las
cuentas internas del desarrollador (companies.is_internal = true) con acceso
completo y sin límites, que NO se guarda en la BD.

Los features y límites se declaran aquí (en código) para que sean fáciles de
leer y cambiar sin tocar la base de datos. Los precios son la fuente de verdad
que consumen el panel de plataforma (/admin/pricing) y el billing.

Los valores de los planes deben coincidir con el CHECK de la migración
(migrations/v7_plans_value_tiers.sql): ('starter', 'pro', 'business').
"""

# ── Identificadores de plan ──
PLAN_STARTER = 'starter'      # Gratis: formulario simple → PDF
PLAN_PRO = 'pro'              # De pago: formulario completo + desglose + Fast Quote
PLAN_BUSINESS = 'business'    # De pago: todo Pro + white-label / más usuarios
PLAN_INTERNAL = 'internal'    # Virtual: cuentas internas (is_internal) — todo sin límites

# Planes almacenables en la BD (CHECK constraint de v7).
VALID_PLANS = (PLAN_STARTER, PLAN_PRO, PLAN_BUSINESS)

# Todos los planes reconocidos por el código (incluye el virtual).
_ALL_PLANS = VALID_PLANS + (PLAN_INTERNAL,)

# Planes legacy → nuevos (migración de datos, sin romper tenants existentes).
LEGACY_PLAN_MAP = {
    'pdf': PLAN_STARTER,
    'fast_quote': PLAN_PRO,
    'full': PLAN_PRO,
}

# ── Features (capacidades) que puede incluir un plan ──
FEATURE_SIMPLE_PDF = 'simple_pdf'  # Formulario simple → PDF (cantidad × precio)
FEATURE_FAST_QUOTE = 'fast_quote'  # Estimación con IA
FEATURE_FULL_FORM = 'full_form'    # Formulario completo con desglose de materiales
FEATURE_DESGLOSE = 'desglose'      # Vista de desglose
FEATURE_STORAGE = 'storage'        # Storage de PDFs/cotizaciones

# ── Matriz plan → features ──
PLAN_FEATURES = {
    PLAN_STARTER: {
        FEATURE_SIMPLE_PDF,
        FEATURE_STORAGE,
    },
    PLAN_PRO: {
        FEATURE_SIMPLE_PDF,
        FEATURE_FAST_QUOTE,
        FEATURE_FULL_FORM,
        FEATURE_DESGLOSE,
        FEATURE_STORAGE,
    },
    PLAN_BUSINESS: {
        FEATURE_SIMPLE_PDF,
        FEATURE_FAST_QUOTE,
        FEATURE_FULL_FORM,
        FEATURE_DESGLOSE,
        FEATURE_STORAGE,
    },
    PLAN_INTERNAL: {
        FEATURE_SIMPLE_PDF,
        FEATURE_FAST_QUOTE,
        FEATURE_FULL_FORM,
        FEATURE_DESGLOSE,
        FEATURE_STORAGE,
    },
}

# ── Límites por plan. None = sin límite. ──
PLAN_LIMITS = {
    PLAN_STARTER: {
        'max_pdfs': 5,
    },
    # Cuota mensual de estimaciones Fast Quote (tabla fast_quote_usage).
    PLAN_PRO: {
        'max_estimates': 30,
        'max_users': 10,
    },
    PLAN_BUSINESS: {
        'max_estimates': 150,
        'max_users': 50,
    },
    PLAN_INTERNAL: {},   # sin límites
}

# ── Nombres legibles (UI) ──
PLAN_NAMES = {
    PLAN_STARTER: 'Starter',
    PLAN_PRO: 'Pro',
    PLAN_BUSINESS: 'Business',
    PLAN_INTERNAL: 'Interno (sin cobro)',
}

# ── Precios por plan (fuente de verdad; MXN/mes) ──
PLAN_PRICES = {
    PLAN_STARTER: {
        'nombre': 'Starter',
        'moneda': 'MXN',
        'frecuencia': 'mensual',
        'precio': 0,
    },
    PLAN_PRO: {
        'nombre': 'Pro',
        'moneda': 'MXN',
        'frecuencia': 'mensual',
        'precio': 499,
    },
    PLAN_BUSINESS: {
        'nombre': 'Business',
        'moneda': 'MXN',
        'frecuencia': 'mensual',
        'precio': 999,
    },
}

# Precio del paquete Fast Quote extra (100 estimaciones).
FASTQUOTE_PACK_PRICE = 199
FASTQUOTE_PACK_ESTIMATES = 100


def _normalize_plan(plan):
    """Mapea un plan legacy/None a su plan canónico. Desconocidos → PLAN_PRO."""
    if not plan:
        return PLAN_PRO
    if plan in LEGACY_PLAN_MAP:
        return LEGACY_PLAN_MAP[plan]
    if plan in _ALL_PLANS:
        return plan
    return PLAN_PRO


def effective_plan(company):
    """Plan efectivo de una compañía.

    Devuelve PLAN_INTERNAL si la compañía está marcada como interna
    (companies.is_internal), si no el plan normalizado. Acepta un dict de
    company (g.company) o un string de plan.
    """
    if isinstance(company, dict):
        if company.get('is_internal'):
            return PLAN_INTERNAL
        return _normalize_plan(company.get('plan'))
    return _normalize_plan(company)


def is_valid_plan(plan):
    """True si `plan` es un plan almacenable en BD (starter/pro/business)."""
    return _normalize_plan(plan) in VALID_PLANS


def has_feature(plan, feature):
    """True si el plan incluye la feature. Acepta string de plan o dict de company."""
    if isinstance(plan, dict):
        plan = effective_plan(plan)
    else:
        plan = _normalize_plan(plan)
    return feature in PLAN_FEATURES.get(plan, set())


def get_limit(plan, key):
    """Devuelve el límite `key` del plan, o None si no está definido.

    Acepta string de plan o dict de company (usa el plan efectivo).
    """
    if isinstance(plan, dict):
        plan = effective_plan(plan)
    else:
        plan = _normalize_plan(plan)
    return PLAN_LIMITS.get(plan, {}).get(key)
