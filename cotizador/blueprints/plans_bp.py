"""
Página pública de planes (marketing/pricing), accesible sin login.

Muestra la comparativa Starter / Pro / Business más el paquete Fast Quote extra.
Los datos salen de cotizador/plans.py (PLAN_PRICES, PLAN_FEATURES, PLAN_LIMITS).
"""

from flask import Blueprint, render_template

from cotizador.plans import (
    PLAN_NAMES, PLAN_PRICES, PLAN_FEATURES, PLAN_LIMITS, VALID_PLANS,
    FEATURE_LABELS, FASTQUOTE_PACK_PRICE, FASTQUOTE_PACK_ESTIMATES,
)

plans_bp = Blueprint('plans', __name__)


def _catalog():
    catalog = []
    for plan in VALID_PLANS:
        price = PLAN_PRICES.get(plan, {})
        catalog.append({
            'id': plan,
            'name': PLAN_NAMES.get(plan, plan),
            'price': price.get('precio'),
            'currency': price.get('moneda', 'MXN'),
            'features': sorted(PLAN_FEATURES.get(plan, set())),
            'limits': PLAN_LIMITS.get(plan, {}),
        })
    return catalog


@plans_bp.route('/planes')
def index():
    return render_template(
        'planes.html',
        catalog=_catalog(),
        feature_labels=FEATURE_LABELS,
        pack_price=FASTQUOTE_PACK_PRICE,
        pack_estimates=FASTQUOTE_PACK_ESTIMATES,
    )
