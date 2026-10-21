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

from cotizador.db_rows import row_to_dict
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


def _to_dict(obj):
    """Convierte un StripeObject (o dict) a dict nativo.

    stripe-python >=15 ya no hace que StripeObject herede de dict, así que
    .get() deja de existir. Normalizamos a dict para que el webhook funcione
    igual en stripe<15 y >=15.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, 'to_dict', None)
    if callable(to_dict):
        return to_dict()
    return obj


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


def _plan_from_price(price_id):
    """Devuelve el plan correspondiente a un Price ID de Stripe, o None.

    Es la lógica inversa de `_price_id()`: compara el id contra los cuatro
    Price IDs configurados (Pro/Business × mes/año).
    """
    if not price_id:
        return None
    for plan in (PLAN_PRO, PLAN_BUSINESS):
        for interval in ('month', 'year'):
            if _price_id(plan, interval) == price_id:
                return plan
    return None


def _sub_item(sub):
    """Primer item de una suscripción (o {}): de ahí salen price.id y
    current_period_end / trial_end en versiones nuevas de stripe."""
    items = ((sub or {}).get('items') or {}).get('data') or []
    return items[0] if items else {}


def _sub_item_price_id(sub_item):
    """Price id del item, tolerando `price` como string id o como objeto."""
    price = (sub_item or {}).get('price')
    if isinstance(price, dict):
        return price.get('id')
    return price or None


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
    "fast_quote_pack_count, fast_quote_credits_remaining"
)


class _BillingDBError(Exception):
    """Fallo de base de datos en el webhook: no hay que tragar el error.

    El webhook responde 500 para que Stripe reintente, en vez de devolver 200
    y perder la activación (el lookup de empresa no debe confundirse con
    "no hay fila").
    """


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
        colnames = [d[0] for d in cur.description] if cur.description else None
        cur.close()
        if row:
            # RealDictCursor devuelve un mapping: zip(colnames, row) iteraría
            # las llaves y dejaría is_internal = 'is_internal' (siempre truthy).
            return row_to_dict(row, colnames)
    except Exception as e:
        logger.warning(f"[BILLING] Error querying company: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        raise _BillingDBError(f"Error querying company: {e}") from e
    return None


def _company_via_sdk(column, value):
    """Lectura de fallback con service key (bypassea RLS) para el webhook sin sesión."""
    db = _get_db()
    if not db:
        return None
    try:
        supabase_url = (os.getenv('SUPABASE_URL') or '').strip()
        service_key = (os.getenv('SUPABASE_SERVICE_KEY') or '').strip()
        if not (supabase_url and service_key):
            return None
        from supabase import create_client
        admin_client = create_client(supabase_url, service_key)
        resp = admin_client.table('companies').select(_COMPANY_COLS).eq(column, value).limit(1).execute()
        if getattr(resp, 'data', None):
            return resp.data[0]
    except Exception as e:
        logger.warning(f"[BILLING] Error _company_via_sdk({column}): {e}")
        raise _BillingDBError(f"Error _company_via_sdk({column}): {e}") from e
    return None


def _company_by_id(cid):
    return _query_company("id = %s", (cid,)) or _company_via_sdk('id', cid)


def _company_by_subscription(sub_id):
    return _query_company("stripe_subscription_id = %s", (sub_id,)) or _company_via_sdk('stripe_subscription_id', sub_id)


def _company_by_customer(customer_id):
    return _query_company("stripe_customer_id = %s", (customer_id,)) or _company_via_sdk('stripe_customer_id', customer_id)


def _aplicar_paquete_fast_quote(metadata, company_id):
    """Acredita un paquete Fast Quote (créditos one-time) a la cuenta.

    El incremento es atómico en SQL (``col + 100``), no un read-modify-write
    del saldo leído en Python. No-op si la empresa no existe. Si existe y el
    UPDATE falla, lanza ``_BillingDBError`` para que Stripe reintente.
    """
    if not company_id:
        return
    db = _get_db()
    if not db:
        raise _BillingDBError("db unavailable al acreditar paquete Fast Quote")
    company = _company_by_id(company_id)
    if not company:
        logger.warning(f"[BILLING] Pack Fast Quote sin empresa {company_id}")
        return
    updated = db.acreditar_paquete_fast_quote(company['id'], FASTQUOTE_PACK_ESTIMATES)
    if not updated:
        raise _BillingDBError(f"No se pudo acreditar el paquete Fast Quote a {company_id}")
    logger.info(f"[BILLING] Pack Fast Quote aplicado a {company_id}")


def _stripe_admin_client():
    """Cliente Supabase con service key (bypass RLS) para la tabla stripe_events."""
    supabase_url = (os.getenv('SUPABASE_URL') or '').strip()
    service_key = (os.getenv('SUPABASE_SERVICE_KEY') or '').strip()
    if not (supabase_url and service_key):
        return None
    from supabase import create_client
    return create_client(supabase_url, service_key)


def _is_unique_violation(exc):
    """True si el error es un duplicado de clave (SQLSTATE 23505)."""
    code = getattr(exc, 'pgcode', None) or getattr(exc, 'code', None)
    if str(code) == '23505':
        return True
    for arg in getattr(exc, 'args', ()) or ():
        if isinstance(arg, dict) and str(arg.get('code')) == '23505':
            return True
        if isinstance(arg, str) and ('23505' in arg or 'duplicate key' in arg.lower()):
            return True
    text = str(exc).lower()
    return '23505' in text or 'duplicate key' in text


def _claim_stripe_event(event_id):
    """Reclama el evento para procesarlo una sola vez.

    ``INSERT ... ON CONFLICT DO NOTHING RETURNING`` (o, en el fallback SDK, un
    INSERT cuya violación de unicidad se trata como "ya existía").

    Returns:
        True  — esta entrega insertó la fila; hay que procesar el evento.
        False — otra entrega ya lo reclamó; responder 200 sin reprocesar.
        None  — no hay dónde deduplicar (sin PG ni service key). Se procesa
                igual y NO se responde 500: sin service key el camino viejo
                fallaba el registro y Stripe reintentaba cada evento.

    Lanza ``_BillingDBError`` si había base de datos y el INSERT falló por
    algo distinto de una clave duplicada (Stripe debe reintentar).
    """
    if not event_id:
        return None

    pg_error = None
    db = _get_db()
    conn = getattr(db, 'pg_connection', None) if db else None
    if conn is not None and not getattr(conn, 'closed', 1):
        try:
            try:
                conn.rollback()
            except Exception:
                pass
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO public.stripe_events (id)
                   VALUES (%s)
                   ON CONFLICT (id) DO NOTHING
                   RETURNING id""",
                (event_id,),
            )
            row = cur.fetchone()
            conn.commit()
            cur.close()
            # RETURNING vacío = conflicto. No se acredita de nuevo.
            return row is not None
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            if _is_unique_violation(e):
                return False
            pg_error = e
            logger.warning(f"[BILLING] Claim PG falló ({event_id}): {e}")

    client = None
    try:
        client = _stripe_admin_client()
    except Exception as e:
        logger.warning(f"[BILLING] No se pudo crear cliente admin de stripe_events: {e}")
        client = None

    if client is not None:
        try:
            client.table('stripe_events').insert({'id': event_id}).execute()
            return True
        except Exception as e:
            if _is_unique_violation(e):
                return False
            logger.warning(f"[BILLING] Claim SDK falló ({event_id}): {e}")
            raise _BillingDBError(f"No se pudo registrar evento {event_id}: {e}") from e

    if pg_error is not None:
        raise _BillingDBError(
            f"No se pudo registrar evento {event_id}: {pg_error}"
        ) from pg_error

    logger.error(
        "[BILLING] Dedup de webhooks no disponible "
        "(sin conexión PG ni SUPABASE_SERVICE_KEY); "
        f"se procesa {event_id} sin idempotencia"
    )
    return None


def _release_stripe_event(event_id):
    """Borra el claim si el procesamiento falló, para que Stripe pueda reintentar.

    Mejor esfuerzo: si el DELETE falla, el reintento verá el evento como ya
    procesado y no volverá a aplicar el cambio. Se loguea como error.
    """
    if not event_id:
        return
    db = _get_db()
    conn = getattr(db, 'pg_connection', None) if db else None
    if conn is not None and not getattr(conn, 'closed', 1):
        try:
            try:
                conn.rollback()
            except Exception:
                pass
            cur = conn.cursor()
            cur.execute("DELETE FROM public.stripe_events WHERE id = %s", (event_id,))
            conn.commit()
            cur.close()
            return
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.warning(f"[BILLING] No se pudo liberar evento {event_id} por PG: {e}")

    try:
        client = _stripe_admin_client()
    except Exception:
        client = None
    if client is not None:
        try:
            client.table('stripe_events').delete().eq('id', event_id).execute()
            return
        except Exception as e:
            logger.error(
                f"[BILLING] No se pudo liberar evento {event_id}; "
                f"un reintento de Stripe no lo volverá a procesar: {e}"
            )
            return
    logger.error(
        f"[BILLING] No se pudo liberar evento {event_id}; "
        "un reintento de Stripe no lo volverá a procesar"
    )


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

    company = g.get('company') or {}
    company_id = session.get('company_id')
    email = session.get('user_email')

    # Guard: si ya hay suscripción viva, el cambio de plan va por el Customer
    # Portal (Stripe prorratea); el checkout queda solo para la primera
    # suscripción o re-suscripción tras cancelar. `incomplete` no bloquea:
    # quien falló el primer pago puede reintentar el checkout al momento.
    status = (company.get('subscription_status') or '').strip().lower()
    if status in ('active', 'trialing', 'past_due', 'unpaid'):
        flash("Ya tienes una suscripción activa; cámbiala desde el portal de facturación.", "info")
        return redirect(url_for('billing.page'))

    sub_data = {'metadata': {'company_id': company_id, 'plan': plan}}
    # Trial solo la primera vez (no al re-suscribirse tras cancelar).
    if not company.get('stripe_subscription_id'):
        trial_days = _int_env('STRIPE_TRIAL_DAYS', 14)
        if trial_days > 0:
            sub_data['trial_period_days'] = trial_days

    # customer= si ya existe; si no, customer_email=. Nunca ambos (Stripe
    # rechaza la sesión si van juntos).
    checkout_kwargs = {
        'mode': 'subscription',
        'line_items': [{'price': price_id, 'quantity': 1}],
        'subscription_data': sub_data,
        'metadata': {'company_id': company_id, 'plan': plan},
        'success_url': _abs('/billing/success?session_id={CHECKOUT_SESSION_ID}'),
        'cancel_url': _abs('/billing/cancel'),
        'allow_promotion_codes': True,
        # Idempotencia del doble clic con componente de tiempo (cambia cada
        # minuto): solo deduplica el doble clic, sin que Stripe rechace la
        # llave a las 24 h por llegar con parámetros distintos.
        'idempotency_key': (
            f"checkout:{company_id}:{plan}:{interval}:"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        ),
    }
    if company.get('stripe_customer_id'):
        checkout_kwargs['customer'] = company.get('stripe_customer_id')
    else:
        checkout_kwargs['customer_email'] = email

    try:
        checkout_session = stripe.checkout.Session.create(**checkout_kwargs)
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

    # El paquete Fast Quote es para planes Pro/Business (que tienen Fast Quote).
    if effective_plan(g.get('company')) == PLAN_STARTER:
        flash("El paquete Fast Quote es para planes Pro o Business.", "error")
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
        event = _to_dict(stripe.Webhook.construct_event(payload, sig, webhook_secret))
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    db = _get_db()
    if db is None:
        # Sin acceso a BD no podemos activar nada: 500 para que Stripe reintente.
        return jsonify({'error': 'db unavailable'}), 500

    event_id = event.get('id')
    event_type = event.get('type')
    obj = event.get('data', {}).get('object', {})

    # Reclamar el evento ANTES de procesarlo. Dos entregas concurrentes no
    # pueden pasar las dos: solo quien inserta la fila acredita el paquete.
    # False = ya procesado (200). Un error real de BD es 500 para que Stripe
    # reintente. None = no hay dedup configurado: se procesa igual, sin 500.
    claimed = None
    if event_id:
        try:
            claimed = _claim_stripe_event(event_id)
        except _BillingDBError as e:
            logger.error(f"[BILLING] No se pudo reclamar evento {event_id}: {e}")
            return jsonify({'error': 'db error'}), 500
        if claimed is False:
            return jsonify({'received': True}), 200

    try:
        if event_type == 'checkout.session.completed':
            metadata = obj.get('metadata') or {}
            company_id = metadata.get('company_id')
            company = _company_by_id(company_id) if company_id else None
            if company:
                if metadata.get('type') == 'fastquote_pack':
                    # Paquete Fast Quote: acreditar solo si el pago está
                    # confirmado (tarjeta). OXXO/offline lo acredita
                    # checkout.session.async_payment_succeeded.
                    if obj.get('payment_status') == 'paid':
                        _aplicar_paquete_fast_quote(metadata, company_id)
                elif not company.get('is_internal'):
                    # Suscripción: actualiza plan + ids de Stripe desde el
                    # precio (no de la metadata, que queda congelada).
                    sub_id = obj.get('subscription')
                    sub = {}
                    if sub_id:
                        try:
                            sub = _to_dict(stripe.Subscription.retrieve(sub_id))
                        except Exception as e:
                            logger.warning(f"[BILLING] No se pudo leer subscription {sub_id}: {e}")
                    sub_item = _sub_item(sub)
                    price_id = _sub_item_price_id(sub_item)
                    plan = _plan_from_price(price_id) or metadata.get('plan') or PLAN_STARTER
                    if plan not in VALID_PLANS:
                        plan = PLAN_STARTER
                    status = sub.get('status') or 'active'
                    updates = {
                        'stripe_customer_id': obj.get('customer'),
                        'stripe_subscription_id': obj.get('subscription'),
                        'subscription_status': status,
                    }
                    # incomplete / incomplete_expired: el cobro no se confirmó.
                    # No activar el plan; invoice.paid o subscription.updated
                    # lo harán cuando el estado sea real.
                    if status not in ('incomplete', 'incomplete_expired'):
                        updates['plan'] = plan
                        trial_end = sub_item.get('trial_end') or sub.get('trial_end')
                        if trial_end:
                            updates['trial_ends_at'] = _ts(trial_end)
                        period_end = sub_item.get('current_period_end') or sub.get('current_period_end')
                        if period_end:
                            updates['current_period_end'] = _ts(period_end)
                    if not db.update_company(company['id'], updates):
                        raise _BillingDBError("update_company falló en checkout.session.completed")

        elif event_type == 'checkout.session.async_payment_succeeded':
            # Paquete Fast Quote con medios offline (OXXO): el pago se confirma
            # después; este evento acredita el paquete.
            metadata = obj.get('metadata') or {}
            if metadata.get('type') == 'fastquote_pack':
                _aplicar_paquete_fast_quote(metadata, metadata.get('company_id'))

        elif event_type == 'customer.subscription.updated':
            sub_id = obj.get('id')
            company = _company_by_subscription(sub_id)
            if not company:
                company = _company_by_customer(obj.get('customer'))
            stored_sub = (company or {}).get('stripe_subscription_id')
            # Una sub vieja (incomplete → incomplete_expired, o la anterior a
            # un cambio de plan) no debe degradar a quien ya tiene otra sub
            # guardada. Sin id guardado sí se aplica (primera suscripción).
            if company and stored_sub and stored_sub != sub_id:
                logger.info(
                    f"[BILLING] Ignorando customer.subscription.updated {sub_id}: "
                    f"la empresa {company.get('id')} tiene stripe_subscription_id={stored_sub}"
                )
            elif company and not company.get('is_internal'):
                status = obj.get('status')
                updates = {'subscription_status': status}
                sub_item = _sub_item(obj)
                period_end = sub_item.get('current_period_end') or obj.get('current_period_end')
                if period_end:
                    updates['current_period_end'] = _ts(period_end)
                trial_end = sub_item.get('trial_end') or obj.get('trial_end')
                if trial_end:
                    updates['trial_ends_at'] = _ts(trial_end)

                # Plan derivado del precio (la metadata queda congelada si
                # cambian de plan en el portal).
                price_id = _sub_item_price_id(sub_item)
                plan = _plan_from_price(price_id) or (obj.get('metadata') or {}).get('plan')
                if plan in VALID_PLANS:
                    updates['plan'] = plan

                # Impago: past_due es gracia (Stripe reintenta); el resto baja
                # a Starter.
                if status in ('unpaid', 'paused', 'incomplete_expired'):
                    updates['plan'] = PLAN_STARTER

                if not db.update_company(company['id'], updates):
                    raise _BillingDBError("update_company falló en customer.subscription.updated")

        elif event_type == 'customer.subscription.deleted':
            sub_id = obj.get('id')
            company = _company_by_subscription(sub_id)
            if company and not company.get('is_internal'):
                # Solo degrada si es la suscripción que la empresa tiene
                # guardada (el borrado de una sub vieja/sustituida no degrada
                # a quien acaba de subir de plan).
                if company.get('stripe_subscription_id') == sub_id:
                    if not db.update_company(company['id'], {
                        'subscription_status': 'canceled',
                        'plan': PLAN_STARTER,
                    }):
                        raise _BillingDBError("update_company falló en customer.subscription.deleted")

        elif event_type == 'invoice.paid':
            # Restaura el plan tomando el estado real de la suscripción (no
            # fuerza 'active': durante el trial llega una factura de $0).
            # Si no se puede leer la suscripción, 500 para que Stripe reintente:
            # escribir 'active' sin plan dejaría el cobro a medias.
            parent = obj.get('parent') or {}
            sub_details = parent.get('subscription_details') or {}
            sub_id = sub_details.get('subscription') or obj.get('subscription')
            company = _company_by_subscription(sub_id) if sub_id else None
            if company and not company.get('is_internal'):
                try:
                    sub = _to_dict(stripe.Subscription.retrieve(sub_id))
                except Exception as e:
                    logger.warning(f"[BILLING] No se pudo leer subscription {sub_id}: {e}")
                    raise _BillingDBError(
                        f"No se pudo leer subscription {sub_id} en invoice.paid"
                    ) from e
                if not sub.get('status'):
                    raise _BillingDBError(
                        f"Subscription {sub_id} sin status en invoice.paid"
                    )
                sub_item = _sub_item(sub)
                price_id = _sub_item_price_id(sub_item)
                plan = _plan_from_price(price_id) or (sub.get('metadata') or {}).get('plan')
                updates = {'subscription_status': sub.get('status')}
                if plan in VALID_PLANS:
                    updates['plan'] = plan
                period_end = sub_item.get('current_period_end') or sub.get('current_period_end')
                if period_end:
                    updates['current_period_end'] = _ts(period_end)
                trial_end = sub_item.get('trial_end') or sub.get('trial_end')
                if trial_end:
                    updates['trial_ends_at'] = _ts(trial_end)
                if not db.update_company(company['id'], updates):
                    raise _BillingDBError("update_company falló en invoice.paid")

        elif event_type == 'invoice.payment_failed':
            # No degradar: Stripe reintenta el cobro varios días. Solo log.
            parent = obj.get('parent') or {}
            sub_details = parent.get('subscription_details') or {}
            sub_id = sub_details.get('subscription') or obj.get('subscription')
            logger.info(f"[BILLING] invoice.payment_failed para sub {sub_id}: no se degrada")

        # Otros tipos de evento se ignoran (respondemos 200). El claim ya
        # quedó registrado, así que un replay no vuelve a entrar.
    except _BillingDBError as e:
        logger.error(f"[BILLING] Error de BD procesando {event_type}: {e}")
        # Soltar el claim para que el reintento de Stripe pueda volver a
        # procesar (si no, el evento quedaría marcado y el cobro se perdería).
        if claimed is True:
            _release_stripe_event(event_id)
        return jsonify({'error': 'db error'}), 500
    except Exception as e:
        logger.exception(f"[BILLING] Error procesando {event_type}: {e}")
        if claimed is True:
            _release_stripe_event(event_id)
        return jsonify({'error': 'db error'}), 500

    return jsonify({'received': True}), 200
