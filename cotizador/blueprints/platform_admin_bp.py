"""
Panel de plataforma (superadmin Sifra).

Acceso restringido al administrador de Sifra (no a los tenants), vía un login
propio por contraseña en /admin/login (env var SUPERADMIN_PASSWORD; ver
cotizador/middleware.superadmin_required). Es independiente del login de
Supabase Auth y del rol del tenant.

Mezcla:
- Estatus del sistema (Supabase, Storage, Scheduler, Keepalive, estadísticas globales)
- Gestión de tenants (listado de empresas, uso/cuota, plan, activar/desactivar)
- Tarifas por plan (cotizador/plans.PLAN_PRICES)
"""

import os
import secrets

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app,
    session,
)

from cotizador.middleware import superadmin_required, is_superadmin
from cotizador.plans import (
    PLAN_NAMES, PLAN_PRICES, PLAN_LIMITS, VALID_PLANS, get_limit, is_valid_plan,
    effective_plan, _normalize_plan, FASTQUOTE_PACK_PRICE,
)

platform_admin_bp = Blueprint('platform_admin', __name__, url_prefix='/admin')

# Archivos de log rotativos (rutas relativas a la raíz del proyecto, igual que
# en cotizador/__init__.py).
LOG_FILES = {
    'fallos_criticos': 'logs/cotizador_fallos_criticos.log',
    'fallos_silenciosos': 'logs/fallos_silenciosos_detectados.log',
}


def _get_db():
    return current_app.extensions.get('db_manager')


def _get_pdf_manager():
    return current_app.extensions.get('pdf_manager')


def _get_scheduler():
    return current_app.extensions.get('sync_scheduler')


def _mrr_estimado(company):
    """MRR estimado (MXN/mes) de una compañía, sin consultar Stripe.

    Suma el precio del plan (PLAN_PRICES) solo cuando la suscripción está
    activa o en trial. Las cuentas internas no facturan (0).
    """
    if company.get('is_internal') or effective_plan(company) == 'internal':
        return 0
    status = (company.get('subscription_status') or '').strip().lower()
    if status in ('active', 'trialing'):
        plan = effective_plan(company)
        return PLAN_PRICES.get(plan, {}).get('precio', 0)
    return 0


def _resumen_financiero(companies):
    """Resumen financiero estimado: MRR, ARR, desglose por plan y packs."""
    mrr = 0.0
    por_plan = {}
    pagos = 0
    packs = 0
    for c in companies:
        plan = effective_plan(c)
        m = _mrr_estimado(c)
        mrr += m
        por_plan[plan] = por_plan.get(plan, 0) + m
        if m > 0:
            pagos += 1
        packs += int(c.get('fast_quote_pack_count') or 0)
    return {
        'mrr': mrr,
        'arr': mrr * 12,
        'por_plan': por_plan,
        'pagos': pagos,
        'total': len(companies),
        'packs': packs,
        'pack_revenue': packs * FASTQUOTE_PACK_PRICE,
    }


def _read_log_tail(path, lines=200):
    """Lee las últimas `lines` líneas de un archivo de log, o '' si no existe."""
    if not path or not os.path.exists(path):
        return ''
    try:
        with open(path, 'r', errors='replace') as f:
            data = f.readlines()
        return ''.join(data[-lines:])
    except Exception:
        return ''


@platform_admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login simple del panel de Sifra (solo contraseña, sin Supabase Auth)."""
    if is_superadmin():
        return redirect(url_for('platform_admin.dashboard'))

    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        expected = os.getenv('SUPERADMIN_PASSWORD', '')
        if expected and secrets.compare_digest(password, expected):
            session['superadmin_ok'] = True
            session.permanent = True
            return redirect(url_for('platform_admin.dashboard'))
        error = "Contraseña incorrecta"

    return render_template('admin/platform/login.html', error=error)


@platform_admin_bp.route('/logout')
def logout():
    """Cierra la sesión de superadmin."""
    session.pop('superadmin_ok', None)
    return redirect(url_for('platform_admin.login'))


@platform_admin_bp.route('/')
@superadmin_required
def dashboard():
    """Estatus del sistema + resumen de empresas."""
    db = _get_db()
    pdf_manager = _get_pdf_manager()
    scheduler = _get_scheduler()

    stats = {}
    try:
        stats = db.obtener_estadisticas() or {}
    except Exception as e:
        stats = {'error': str(e)}

    health = {}
    try:
        health = db.health_check() or {}
    except Exception as e:
        health = {'error': str(e)}

    storage_stats = {}
    if pdf_manager is not None and getattr(pdf_manager, 'supabase_storage', None) is not None:
        try:
            storage_stats = pdf_manager.supabase_storage.obtener_estadisticas() or {}
        except Exception as e:
            storage_stats = {'error': str(e)}

    scheduler_state = {}
    if scheduler is not None:
        try:
            scheduler_state = scheduler.obtener_estado() or {}
        except Exception as e:
            scheduler_state = {'error': str(e)}

    keepalive = {}
    try:
        from render_keepalive import get_keepalive_instance
        instance = get_keepalive_instance()
        if instance is not None:
            keepalive = instance.get_stats() or {}
    except Exception as e:
        keepalive = {'error': str(e)}

    companies = []
    summary = {'total': 0, 'activas': 0, 'por_plan': {}}
    try:
        companies = db.list_companies() or []
        summary['total'] = len(companies)
        for c in companies:
            if c.get('is_active'):
                summary['activas'] += 1
            plan = effective_plan(c)
            summary['por_plan'][plan] = summary['por_plan'].get(plan, 0) + 1
    except Exception as e:
        companies = []

    return render_template(
        'admin/platform/dashboard.html',
        stats=stats,
        health=health,
        storage_stats=storage_stats,
        scheduler_state=scheduler_state,
        keepalive=keepalive,
        companies=companies,
        summary=summary,
        financiero=_resumen_financiero(companies),
        plan_prices=PLAN_PRICES,
        plan_names=PLAN_NAMES,
    )


@platform_admin_bp.route('/companies')
@superadmin_required
def companies():
    """Listado de empresas con uso compacto."""
    db = _get_db()
    rows = []
    try:
        for company in (db.list_companies() or []):
            usage = {}
            try:
                usage = db.get_company_usage(company.get('id')) or {}
            except Exception:
                usage = {}
            company['usage'] = usage
            company['mrr'] = _mrr_estimado(company)
            rows.append(company)
    except Exception as e:
        flash(f"Error listando empresas: {e}", "error")

    return render_template(
        'admin/platform/companies.html',
        companies=rows,
        plan_names=PLAN_NAMES,
        plan_prices=PLAN_PRICES,
        plan_limits=PLAN_LIMITS,
    )


@platform_admin_bp.route('/companies/<company_id>')
@superadmin_required
def company_detail(company_id):
    """Detalle de una empresa: uso vs límites y acciones."""
    db = _get_db()
    company = db.get_company_by_id(company_id)
    if not company:
        flash("Empresa no encontrada", "error")
        return redirect(url_for('platform_admin.companies'))

    usage = {}
    try:
        usage = db.get_company_usage(company_id) or {}
    except Exception:
        usage = {}

    plan = effective_plan(company)
    limits = PLAN_LIMITS.get(plan, {})
    price = PLAN_PRICES.get(plan, {})

    users = []
    try:
        users = db.list_users_with_email(company_id) or []
    except Exception:
        users = []

    return render_template(
        'admin/platform/company_detail.html',
        company=company,
        usage=usage,
        plan=plan,
        limits=limits,
        price=price,
        mrr=_mrr_estimado(company),
        users=users,
        plan_names=PLAN_NAMES,
        valid_plans=VALID_PLANS,
        get_limit=get_limit,
    )


@platform_admin_bp.route('/companies/<company_id>/plan', methods=['POST'])
@superadmin_required
def company_change_plan(company_id):
    """Cambia el plan de una empresa."""
    db = _get_db()
    plan = (request.form.get('plan') or '').strip()
    if not is_valid_plan(plan):
        flash("Plan inválido", "error")
        return redirect(url_for('platform_admin.company_detail', company_id=company_id))

    # Normalizar a canonical (legacy 'pdf'/'fast_quote'/'full' → nuevo tier).
    plan = _normalize_plan(plan)
    result = db.update_company(company_id, {'plan': plan})
    if result:
        flash(f"Plan actualizado a {PLAN_NAMES.get(plan, plan)}", "success")
    else:
        flash("No se pudo actualizar el plan", "error")
    return redirect(url_for('platform_admin.company_detail', company_id=company_id))


@platform_admin_bp.route('/companies/<company_id>/activate', methods=['POST'])
@superadmin_required
def company_activate(company_id):
    """Activa una empresa (is_active = true)."""
    db = _get_db()
    result = db.update_company(company_id, {'is_active': True})
    flash("Empresa activada" if result else "No se pudo activar la empresa",
          "success" if result else "error")
    return redirect(url_for('platform_admin.company_detail', company_id=company_id))


@platform_admin_bp.route('/companies/<company_id>/deactivate', methods=['POST'])
@superadmin_required
def company_deactivate(company_id):
    """Desactiva una empresa (is_active = false)."""
    db = _get_db()
    result = db.update_company(company_id, {'is_active': False})
    flash("Empresa desactivada" if result else "No se pudo desactivar la empresa",
          "success" if result else "error")
    return redirect(url_for('platform_admin.company_detail', company_id=company_id))


@platform_admin_bp.route('/companies/<company_id>/delete', methods=['POST'])
@superadmin_required
def company_delete(company_id):
    """Elimina definitivamente una empresa y todos sus datos."""
    db = _get_db()
    result = db.delete_company(company_id)
    if result:
        flash("Empresa eliminada definitivamente", "success")
        return redirect(url_for('platform_admin.companies'))
    flash("No se pudo eliminar la empresa", "error")
    return redirect(url_for('platform_admin.company_detail', company_id=company_id))


@platform_admin_bp.route('/companies/<company_id>/users/<user_id>/delete', methods=['POST'])
@superadmin_required
def company_user_delete(company_id, user_id):
    """Elimina definitivamente un usuario (de cualquier tenant)."""
    db = _get_db()
    result = db.delete_user(user_id)
    flash("Usuario eliminado definitivamente" if result else "No se pudo eliminar el usuario",
          "success" if result else "error")
    return redirect(url_for('platform_admin.company_detail', company_id=company_id))


@platform_admin_bp.route('/pricing')
@superadmin_required
def pricing():
    """Tarifas y límites por plan."""
    return render_template(
        'admin/platform/pricing.html',
        plan_names=PLAN_NAMES,
        plan_prices=PLAN_PRICES,
        plan_limits=PLAN_LIMITS,
        valid_plans=VALID_PLANS,
    )


@platform_admin_bp.route('/finanzas')
@superadmin_required
def finanzas():
    """Resumen financiero estimado (MRR/ARR por plan, sin Stripe)."""
    db = _get_db()
    companies = db.list_companies() or []
    financiero = _resumen_financiero(companies)
    for c in companies:
        c['mrr'] = _mrr_estimado(c)
    companies.sort(key=lambda c: c.get('mrr', 0), reverse=True)
    return render_template(
        'admin/platform/finanzas.html',
        financiero=financiero,
        companies=companies,
        plan_names=PLAN_NAMES,
        plan_prices=PLAN_PRICES,
        pack_price=FASTQUOTE_PACK_PRICE,
    )


@platform_admin_bp.route('/logs')
@superadmin_required
def logs():
    """Logs de fallos (archivo) + métricas de performance del SaaS."""
    db = _get_db()
    pdf_manager = _get_pdf_manager()
    scheduler = _get_scheduler()

    log_fallos = _read_log_tail(LOG_FILES['fallos_criticos'])
    log_silenciosos = _read_log_tail(LOG_FILES['fallos_silenciosos'])

    health = {}
    try:
        health = db.health_check() or {}
    except Exception as e:
        health = {'error': str(e)}

    storage_stats = {}
    if pdf_manager is not None and getattr(pdf_manager, 'supabase_storage', None) is not None:
        try:
            storage_stats = pdf_manager.supabase_storage.obtener_estadisticas() or {}
        except Exception as e:
            storage_stats = {'error': str(e)}

    scheduler_state = {}
    if scheduler is not None:
        try:
            scheduler_state = scheduler.obtener_estado() or {}
        except Exception as e:
            scheduler_state = {'error': str(e)}

    keepalive = {}
    try:
        from render_keepalive import get_keepalive_instance
        instance = get_keepalive_instance()
        if instance is not None:
            keepalive = instance.get_stats() or {}
    except Exception as e:
        keepalive = {'error': str(e)}

    return render_template(
        'admin/platform/logs.html',
        log_fallos=log_fallos,
        log_silenciosos=log_silenciosos,
        health=health,
        storage_stats=storage_stats,
        scheduler_state=scheduler_state,
        keepalive=keepalive,
    )


@platform_admin_bp.route('/fast-quote', methods=['GET', 'POST'])
@superadmin_required
def fast_quote_global():
    """Criterios GLOBALES de Fast Quote (singleton). No visibles para tenants."""
    db = _get_db()

    if request.method == 'POST':
        prompt_text = request.form.get('prompt_text', '').strip()
        try:
            result = db.save_fast_quote_global_prompt(prompt_text)
            flash("Criterios globales guardados", "success" if result else "error")
        except Exception as e:
            flash(f"Error guardando: {e}", "error")
        return redirect(url_for('platform_admin.fast_quote_global'))

    prompt_text = db.get_fast_quote_global_prompt() or ''
    return render_template('admin/platform/fast_quote_global.html', prompt_text=prompt_text)
