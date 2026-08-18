"""
Definición de planes SaaS y sus features/límites.

Cada compañía (tabla public.companies.plan) tiene UNO de estos planes.
Los features y límites se declaran aquí (en código) para que sean
fáciles de leer y cambiar sin tocar la base de datos.

Los valores de los planes deben coincidir con el CHECK de la migración
(migrations/v4_plans.sql).
"""

# ── Identificadores de plan ──
PLAN_PDF = 'pdf'                  # "Envía tu cotización en PDF" (formulario simple)
PLAN_FAST_QUOTE = 'fast_quote'    # Solo Fast Quote (IA)
PLAN_FULL = 'full'                # Todo

VALID_PLANS = (PLAN_PDF, PLAN_FAST_QUOTE, PLAN_FULL)

# ── Features (capacidades) que puede incluir un plan ──
FEATURE_SIMPLE_PDF = 'simple_pdf'  # Formulario simple → PDF (cantidad × precio)
FEATURE_FAST_QUOTE = 'fast_quote'  # Estimación con IA
FEATURE_FULL_FORM = 'full_form'    # Formulario completo con desglose de materiales
FEATURE_DESGLOSE = 'desglose'      # Vista de desglose
FEATURE_STORAGE = 'storage'        # Storage de PDFs/cotizaciones

# ── Matriz plan → features ──
PLAN_FEATURES = {
    PLAN_PDF: {
        FEATURE_SIMPLE_PDF,
        FEATURE_STORAGE,
    },
    PLAN_FAST_QUOTE: {
        FEATURE_FAST_QUOTE,
    },
    PLAN_FULL: {
        FEATURE_SIMPLE_PDF,
        FEATURE_FAST_QUOTE,
        FEATURE_FULL_FORM,
        FEATURE_DESGLOSE,
        FEATURE_STORAGE,
    },
}

# ── Límites por plan (constantes configurables). None = sin límite. ──
PLAN_LIMITS = {
    PLAN_PDF: {
        'max_pdfs': 20,
    },
    PLAN_FAST_QUOTE: {},
    PLAN_FULL: {},
}


def is_valid_plan(plan):
    """True si `plan` es uno de los planes válidos."""
    return plan in VALID_PLANS


def has_feature(plan, feature):
    """True si el plan incluye la feature.

    Si el plan es desconocido/None, se asume PLAN_FULL (compatibilidad con
    compañías existentes que, tras la migración, quedan en 'full').
    """
    if not is_valid_plan(plan):
        plan = PLAN_FULL
    return feature in PLAN_FEATURES.get(plan, set())


def get_limit(plan, key):
    """Devuelve el límite `key` del plan, o None si no está definido."""
    if not is_valid_plan(plan):
        plan = PLAN_FULL
    return PLAN_LIMITS.get(plan, {}).get(key)
