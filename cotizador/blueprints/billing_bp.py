"""
Billing (Stripe) para Sifra Cotizador.

Rutas (tenant):
- GET  /billing                         — comparativa de planes + estado de suscripción
- POST /billing/checkout                — Checkout Session (suscripción Pro/Business)
- POST /billing/checkout/fastquote-pack — Checkout Session (paquete Fast Quote, one-time)
- POST /billing/portal                  — Customer Portal (gestionar/cancelar)
- GET  /billing/success                 — redirección post-pago
- GET  /billing/cancel                  — redirección post-cancelación

Ruta pública (webhook):
- POST /stripe/webhook — verifica firma y sincroniza estado de suscripción.

Las cuentas internas (companies.is_internal) quedan fuera del cobro: la página
muestra "acceso completo sin cobro" y el webhook NO les aplica downgrade.
"""

import os
import logging
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app, jsonify, g,
)

from cotizador.middleware import login_required, admin_required
from cotizador.plans import (
    PLAN_STARTER, PLAN_PRO, PLAN_BUSINESS,
    PLAN_NAMES, PLAN_PRICES, PLAN_FEATURES, PLAN_LIMITS, VALID_PLANS,
    effective_plan, get_limit,
    FASTQUOTE_PACK_PRICE, FASTQUOTE_PACK_ESTIMATES,
    FEATURE_LABELS,
)

logger = logging.getLogger(__name__)

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')
stripe_webhook_bp = Blueprint('stripe_webhook', __name__)


def _get_db():
    return current_app.extensions.get('db_manager')


def _stripe():
    """Devuelve el módulo stripe configurado, o None si faltan claves."""
    key = (os.getenv('STRIPE_SECRET_KEY') or '').strip()
    if not key:
        return None
    import stripe
    stripe.api_key = key
    return stripe


def _int_env(name, default):
    try:
        return int((os.getenv(name) or '').strip() or default)
    except (TypeError, ValueError):
        return default


def _abs(path):
    base = (request.host_url or '').rstrip('/')
    return base + path


def _price_id(plan, interval):
    if interval == 'year':
        key = {
            PLAN_PRO: 'STRIPE_PRICE_PRO_ANNUAL',
            PLAN_BUSINESS: 'STRIPE_PRICE_BUSINESS_ANNUAL',
        }.get(plan)
    else:
        key = {
            PLAN_PRO: 'STRIPE_PRICE_PRO',
            PLAN_BUSINESS: 'STRIPE_PRICE_BUSINESS',
        }.get(plan)
    if not key:
        return None
    return (os.getenv(key) or '').strip() or None


def _is_internal():
    return bool((g.get('company') or {}).get('is_internal'))


def _plan_catalog():
    catalog = []
    for plan in VALID_PLANS:
        features = PLAN_FEATURES.get(plan, set())
        price = PLAN_PRICES.get(plan, {})
        catalog.append({
            'id': plan,
            'name': PLAN_NAMES.get(plan, plan),
            'price': price.get('precio'),
            'currency': price.get('moneda', 'MXN'),
            'features': sorted(features),
            'limits': PLAN_LIMITS.get(plan, {}),
        })
    return catalog


#
# ── Webhook helpers (consulta directa a PG, sin sesión) ──
#

_COMPANY_COLS = (
    "id, plan, is_internal, stripe_customer_id, stripe_subscription_id, "
    "fast_quote_pack_count"
)


def _query_company(where_sql, params):
    db = _get_db()
    if not db:
        return None
    conn = getattr(db, 'pg_connection', None)
    if conn is None or conn.closed:
        return None
    try:
        conn.rollback()
    except Exception:
        pass
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT {_COMPANY_COLS} FROM public.companies WHERE {where_sql} LIMIT 1",
            params,
        )
        row = cur.fetchone()
        colnames = [d[0] for d in cur.description]
        cur.close()
        if row:
            return dict(zip(colnames, row))
    except Exception as e:
        logger.warning(f"[BILLING] Error querying company: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    return None


def _company_by_id(cid):
    return _query_company("id = %s", (cid,))


def _company_by_subscription(sub_id):
    return _query_company("stripe_subscription_id = %s", (sub_id,))


def _company_by_customer(customer_id):
    return _query_company("stripe_customer_id = %s", (customer_id,))


def _ts(epoch):
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


#
# ── Página de billing ──
#

@billing_bp.route('/', methods=['GET'])
@login_required
@admin_required
def page():
    company = g.get('company') or {}
    current_plan = effective_plan(company)
    stripe_enabled = _stripe() is not None and bool(
        _price_id(PLAN_PRO, 'month') or _price_id(PLAN_PRO, 'year')
    )
    annual_enabled = bool(_price_id(PLAN_PRO, 'year') or _price_id(PLAN_BUSINESS, 'year'))
    pack_enabled = bool((os.getenv('STRIPE_PRICE_FASTQUOTE_PACK') or '').strip())
    status = company.get('subscription_status') or 'none'
    return render_template(
        'billing.html',
        catalog=_plan_catalog(),
        current_plan=current_plan,
        plan_names=PLAN_NAMES,
        feature_labels=FEATURE_LABELS,
        is_internal=_is_internal(),
        stripe_enabled=stripe_enabled,
        annual_enabled=annual_enabled,
        pack_enabled=pack_enabled,
        subscription_status=status,
        trial_ends_at=company.get('trial_ends_at'),
        current_period_end=company.get('current_period_end'),
        has_customer=bool(company.get('stripe_customer_id')),
        fastquote_pack_price=FASTQUOTE_PACK_PRICE,
        fastquote_pack_estimates=FASTQUOTE_PACK_ESTIMATES,
    )


@billing_bp.route('/checkout', methods=['POST'])
@login_required
@admin_required
def checkout():
    if _is_internal():
        flash("Tu cuenta es interna: tiene acceso completo sin cobro.", "info")
        return redirect(url_for('billing.page'))

    stripe = _stripe()
    if not stripe:
        flash("El cobro no está configurado (faltan claves de Stripe).", "error")
        return redirect(url_for('billing.page'))

    plan = (request.form.get('plan') or '').strip()
    interval = (request.form.get('interval') or 'month').strip()
    if plan not in (PLAN_PRO, PLAN_BUSINESS):
        flash("Plan inválido.", "error")
        return redirect(url_for('billing.page'))

    price_id = _price_id(plan, interval)
    if not price_id:
        flash("No hay precio configurado para ese plan/frecuencia.", "error")
        return redirect(url_for('billing.page'))

    company_id = session.get('company_id')
    email = session.get('user_email')
    trial_days = _int_env('STRIPE_TRIAL_DAYS', 14)

    sub_data = {'metadata': {'company_id': company_id, 'plan': plan}}
    if trial_days > 0:
        sub_data['trial_period_days'] = trial_days

    try:
        checkout_session = stripe.checkout.Session.create(
            mode='subscription',
            customer_email=email,
            line_items=[{'price': price_id, 'quantity': 1}],
            subscription_data=sub_data,
            metadata={'company_id': company_id, 'plan': plan},
            success_url=_abs('/billing/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=_abs('/billing/cancel'),
            allow_promotion_codes=True,
        )
    except Exception as e:
        logger.error(f"[BILLING] Error creando checkout: {e}")
        flash("No se pudo iniciar el pago. Intenta de nuevo.", "error")
        return redirect(url_for('billing.page'))

    return redirect(checkout_session.url)


@billing_bp.route('/checkout/fastquote-pack', methods=['POST'])
@login_required
@admin_required
def checkout_pack():
    if _is_internal():
        flash("Tu cuenta es interna: no requiere paquetes extra.", "info")
        return redirect(url_for('billing.page'))

    stripe = _stripe()
    if not stripe:
        flash("El cobro no está configurado (faltan claves de Stripe).", "error")
        return redirect(url_for('billing.page'))

    price_id = (os.getenv('STRIPE_PRICE_FASTQUOTE_PACK') or '').strip()
    if not price_id:
        flash("No hay precio configurado para el paquete Fast Quote.", "error")
        return redirect(url_for('billing.page'))

    company_id = session.get('company_id')
    email = session.get('user_email')

    try:
        checkout_session = stripe.checkout.Session.create(
            mode='payment',
            customer_email=email,
            line_items=[{'price': price_id, 'quantity': 1}],
            metadata={'company_id': company_id, 'type': 'fastquote_pack'},
            success_url=_abs('/billing/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=_abs('/billing/cancel'),
        )
    except Exception as e:
        logger.error(f"[BILLING] Error creando checkout pack: {e}")
        flash("No se pudo iniciar el pago. Intenta de nuevo.", "error")
        return redirect(url_for('billing.page'))

    return redirect(checkout_session.url)


@billing_bp.route('/portal', methods=['POST'])
@login_required
@admin_required
def portal():
    stripe = _stripe()
    company = g.get('company') or {}
    customer_id = company.get('stripe_customer_id')

    if not stripe or not customer_id:
        flash("No hay una suscripción activa para gestionar.", "error")
        return redirect(url_for('billing.page'))

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=_abs('/billing'),
        )
    except Exception as e:
        logger.error(f"[BILLING] Error creando portal: {e}")
        flash("No se pudo abrir el portal de suscripción.", "error")
        return redirect(url_for('billing.page'))

    return redirect(portal_session.url)


@billing_bp.route('/success', methods=['GET'])
@login_required
def success():
    flash("Pago confirmado. ¡Gracias por suscribirte!", "success")
    return redirect(url_for('billing.page'))


@billing_bp.route('/cancel', methods=['GET'])
@login_required
def cancel():
    flash("Se canceló el pago. Puedes reintentarlo cuando quieras.", "info")
    return redirect(url_for('billing.page'))


#
# ── Webhook público de Stripe ──
#

@stripe_webhook_bp.route('/stripe/webhook', methods=['POST'])
def webhook():
    stripe = _stripe()
    if not stripe:
        return jsonify({'error': 'not configured'}), 503

    webhook_secret = (os.getenv('STRIPE_WEBHOOK_SECRET') or '').strip()
    payload = request.get_data(as_text=True)
    sig = request.headers.get('Stripe-Signature', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    db = _get_db()
    event_type = event['type']
    obj = event['data']['object']

    if event_type == 'checkout.session.completed':
        metadata = obj.get('metadata') or {}
        company_id = metadata.get('company_id')
        company = _company_by_id(company_id) if company_id else None
        if not company:
            return jsonify({'received': True}), 200

        # Paquete Fast Quote (one-time): suma un paquete a la cuenta.
        if metadata.get('type') == 'fastquote_pack':
            current = int(company.get('fast_quote_pack_count') or 0)
            db.update_company(company['id'], {'fast_quote_pack_count': current + 1})
            logger.info(f"[BILLING] Pack Fast Quote aplicado a {company_id}")
            return jsonify({'received': True}), 200

        # Suscripción: actualiza plan + ids de Stripe.
        if company.get('is_internal'):
            return jsonify({'received': True}), 200

        plan = metadata.get('plan')
        if plan not in VALID_PLANS:
            plan = PLAN_PRO
        db.update_company(company['id'], {
            'plan': plan,
            'stripe_customer_id': obj.get('customer'),
            'stripe_subscription_id': obj.get('subscription'),
            'subscription_status': 'active',
        })
        return jsonify({'received': True}), 200

    if event_type == 'customer.subscription.updated':
        sub_id = obj.get('id')
        company = _company_by_subscription(sub_id)
        if not company:
            company = _company_by_customer(obj.get('customer'))
        if not company or company.get('is_internal'):
            return jsonify({'received': True}), 200

        updates = {'subscription_status': obj.get('status')}
        if obj.get('current_period_end'):
            updates['current_period_end'] = _ts(obj['current_period_end'])
        if obj.get('trial_end'):
            updates['trial_ends_at'] = _ts(obj['trial_end'])

        meta_plan = (obj.get('metadata') or {}).get('plan')
        if meta_plan in VALID_PLANS:
            updates['plan'] = meta_plan

        db.update_company(company['id'], updates)
        return jsonify({'received': True}), 200

    if event_type == 'customer.subscription.deleted':
        sub_id = obj.get('id')
        company = _company_by_subscription(sub_id)
        if not company or company.get('is_internal'):
            return jsonify({'received': True}), 200

        # Downgrade a Starter: revoca features de pago pero conserva la data.
        db.update_company(company['id'], {
            'subscription_status': 'canceled',
            'plan': PLAN_STARTER,
        })
        return jsonify({'received': True}), 200

    return jsonify({'received': True}), 200
