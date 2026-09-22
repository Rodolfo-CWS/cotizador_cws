"""
Panel de plataforma (superadmin Sifra).

Acceso restringido al desarrollador y administrador de Sifra (no a los tenants),
vía la env var SUPERADMIN_EMAILS (ver cotizador/middleware.superadmin_required).

Mezcla:
- Estatus del sistema (Supabase, Storage, Scheduler, Keepalive, estadísticas globales)
- Gestión de tenants (listado de empresas, uso/cuota, plan, activar/desactivar)
- Tarifas por plan (cotizador/plans.PLAN_PRICES)
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app,
)

from cotizador.middleware import login_required, superadmin_required
from cotizador.plans import (
    PLAN_NAMES, PLAN_PRICES, PLAN_LIMITS, VALID_PLANS, get_limit, is_valid_plan,
    effective_plan, _normalize_plan,
)

platform_admin_bp = Blueprint('platform_admin', __name__, url_prefix='/admin')


def _get_db():
    return current_app.extensions.get('db_manager')


def _get_pdf_manager():
    return current_app.extensions.get('pdf_manager')


def _get_scheduler():
    return current_app.extensions.get('sync_scheduler')


@platform_admin_bp.route('/')
@login_required
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
    )


@platform_admin_bp.route('/companies')
@login_required
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
            rows.append(company)
    except Exception as e:
        flash(f"Error listando empresas: {e}", "error")

    return render_template(
        'admin/platform/companies.html',
        companies=rows,
        plan_names=PLAN_NAMES,
        plan_limits=PLAN_LIMITS,
    )


@platform_admin_bp.route('/companies/<company_id>')
@login_required
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

    return render_template(
        'admin/platform/company_detail.html',
        company=company,
        usage=usage,
        plan=plan,
        limits=limits,
        price=price,
        plan_names=PLAN_NAMES,
        valid_plans=VALID_PLANS,
        get_limit=get_limit,
    )


@platform_admin_bp.route('/companies/<company_id>/plan', methods=['POST'])
@login_required
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
@login_required
@superadmin_required
def company_activate(company_id):
    """Activa una empresa (is_active = true)."""
    db = _get_db()
    result = db.update_company(company_id, {'is_active': True})
    flash("Empresa activada" if result else "No se pudo activar la empresa",
          "success" if result else "error")
    return redirect(url_for('platform_admin.company_detail', company_id=company_id))


@platform_admin_bp.route('/companies/<company_id>/deactivate', methods=['POST'])
@login_required
@superadmin_required
def company_deactivate(company_id):
    """Desactiva una empresa (is_active = false)."""
    db = _get_db()
    result = db.update_company(company_id, {'is_active': False})
    flash("Empresa desactivada" if result else "No se pudo desactivar la empresa",
          "success" if result else "error")
    return redirect(url_for('platform_admin.company_detail', company_id=company_id))


@platform_admin_bp.route('/pricing')
@login_required
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
