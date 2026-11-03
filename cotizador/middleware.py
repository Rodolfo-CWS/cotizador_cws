"""
Middleware multi-tenant para Sifra Cotizador SaaS.

Antes de cada request:
1. Verifica que el usuario esté autenticado (session con Supabase Auth)
2. Configura el contexto de compañía en PostgreSQL para RLS
3. Carga los datos de la compañía en g.company para templates
"""

from flask import g, session, redirect, url_for, request, flash, jsonify
from functools import wraps

from cotizador.db_rows import row_to_dict
from cotizador.plans import has_feature, effective_plan

# Centinela que no coincide con ninguna compañía. La política RLS compara
# company_id contra current_setting('app.current_company_id') y, si el GUC
# falta, cae en este mismo UUID nulo (migrations/v2_multi_tenant.sql).
RLS_DENY_COMPANY_ID = "00000000-0000-0000-0000-000000000000"


def _solicitud_quiere_json():
    """True cuando la respuesta debe ser JSON (401) y no un redirect HTML."""
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    # GET /api/... no manda Content-Type. Aun así el cliente espera JSON.
    return (request.path or "").startswith("/api/")


def init_middleware(app, supabase_manager):
    """Registra los middlewares en la app Flask."""

    @app.before_request
    def set_tenant_context():
        """Configurar el contexto de compañía antes de cada request."""
        # Inicializar valores por defecto
        g.company = None
        g.user = None

        # Rutas públicas que no requieren autenticación
        public_routes = [
            '/auth/login',
            '/auth/register',
            '/auth/logout',
            '/auth/forgot-password',
            '/auth/reset-password',
            '/auth/callback',
            '/health',
            '/static/',
            '/stripe/webhook',
            '/planes',
            '/admin/login',
            '/admin/logout',
        ]

        path = request.path.rstrip('/') or '/'
        is_static = path.startswith('/static')
        is_public = any(path.startswith(public.rstrip('/')) for public in public_routes)

        # La conexión psycopg2 es única y de larga vida. set_config(..., false)
        # es de SESIÓN: sobrevive al request. Un request sin sesión (o una ruta
        # pública como /health o el webhook) debe reescribir el GUC; si no, la
        # siguiente consulta hereda el company_id del usuario anterior.
        # is_local=true no alcanza: las rutas hacen commit/rollback por su
        # cuenta y el valor local moriría antes de la consulta. Por eso el
        # manager hace SET de sesión y COMMIT (ver set_company_context).
        # El rol de DATABASE_URL en Supabase es el owner de las tablas y no
        # tiene FORCE ROW LEVEL SECURITY, así que RLS no filtra esa conexión;
        # igual hay que limpiar el GUC para no depender de ese accidente.
        if not is_static:
            company_id = None
            if session.get('user_id') and session.get('company_id'):
                company_id = session.get('company_id')
            _sincronizar_company_rls(app, supabase_manager, company_id)

        if is_public:
            return

        # Verificar sesión de usuario (Supabase Auth)
        if 'user_id' in session and 'company_id' in session:
            g.user = {
                'id': session.get('user_id'),
                'email': session.get('user_email'),
                'name': session.get('user_name'),
                'role': session.get('user_role', 'seller'),
            }

            # Cargar datos de la compañía para templates.
            # El GUC de RLS ya quedó fijado arriba (también si no hay sesión).
            company_id = session.get('company_id')
            if company_id:
                try:
                    company = _load_company_from_db(supabase_manager, company_id)
                    g.company = company
                except Exception as e:
                    app.logger.warning(
                        f"[MIDDLEWARE] No se pudo cargar compañía {company_id}: {e}"
                    )
        else:
            # No autenticado — guardar ruta intentada para redirect post-login.
            # Solo GETs de páginas (sin extensión de archivo) para no guardar
            # requests de assets/favicon que provocarían un 404 tras el login.
            if request.method == 'GET':
                last_segment = request.path.rstrip('/').rsplit('/', 1)[-1]
                if '.' not in last_segment:
                    session['next_url'] = request.full_path
            g.user = None
            g.company = None

    @app.context_processor
    def inject_company_context():
        """Inyectar compañía, usuario y plan en todos los templates."""
        company = g.get('company')
        return {
            'company': company,
            'user': g.get('user'),
            'company_plan': effective_plan(company),
            'plan_has_feature': has_feature,
            'is_internal': bool((company or {}).get('is_internal')),
            'is_superadmin': is_superadmin(),
        }


def _sincronizar_company_rls(app, supabase_manager, company_id):
    """Deja app.current_company_id en la compañía de la sesión, o en el centinela."""
    conn = getattr(supabase_manager, "pg_connection", None)
    if not conn or getattr(conn, "closed", True):
        try:
            supabase_manager._inicializar_conexion()
        except Exception as e:
            app.logger.warning(f"[MIDDLEWARE] Reconectando PG: {e}")
            return
        conn = getattr(supabase_manager, "pg_connection", None)
        if not conn or getattr(conn, "closed", True):
            return
    if not supabase_manager.set_company_context(company_id):
        app.logger.warning("[MIDDLEWARE] No se pudo fijar app.current_company_id")


def _load_company_from_db(supabase_manager, company_id):
    """Carga los datos de la compañía usando SDK con service key (bypass RLS)."""
    import os
    from supabase import create_client

    try:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        if url and key:
            client = create_client(url, key)
            resp = client.table('companies').select('*').eq('id', company_id).eq('is_active', True).execute()
            if resp.data:
                return resp.data[0]
    except Exception as e:
        pass

    # Fallback: PostgreSQL directo
    try:
        connection = supabase_manager.pg_connection
        if connection and not connection.closed:
            try:
                connection.rollback()
            except:
                pass
            cursor = connection.cursor()
            cursor.execute(
                """SELECT id, name, slug, tax_id, address, phone, email,
                   logo_url, primary_color, secondary_color, footer_text,
                   iva_rate, is_active, plan, codigo, legacy_drive_import,
                   is_internal, stripe_customer_id, stripe_subscription_id,
                   subscription_status, trial_ends_at, current_period_end,
                   fast_quote_pack_count, fast_quote_credits_remaining
                FROM public.companies WHERE id = %s AND is_active = true""",
                (company_id,)
            )
            row = cursor.fetchone()
            colnames = [desc[0] for desc in cursor.description] if cursor.description else None
            cursor.close()
            if row:
                # Misma trampa que en el webhook: con RealDictCursor, zip
                # copia los nombres de columna y is_internal queda truthy.
                return row_to_dict(row, colnames)
    except Exception:
        pass

    return None


def login_required(f):
    """Decorador: requiere autenticación con Supabase Auth."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Peticiones AJAX/JSON y toda ruta /api/: 401 JSON, no un redirect
            # HTML, para que el frontend detecte la sesión expirada.
            if _solicitud_quiere_json():
                return jsonify({"success": False, "error": "Sesión expirada"}), 401
            # Guardar URL actual (relativa) para redirigir después del login
            if request.method == 'GET':
                session['next_url'] = request.full_path
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def company_required(f):
    """Decorador: requiere que el usuario pertenezca a una compañía."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_id' not in session:
            return redirect(url_for('auth.register_company'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(role):
    """Decorador: requiere un rol específico (admin, manager, seller)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_role') != role:
                from flask import render_template
                return render_template(
                    'error.html',
                    error="No tienes permisos para acceder a esta página"
                ), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorador: requiere rol de admin."""
    return role_required('admin')(f)


def is_superadmin():
    """True si la sesión actual pasó el login de superadmin (/admin/login).

    El panel de plataforma (/admin) es de uso exclusivo del administrador de
    Sifra. Se accede con una contraseña propia (env var SUPERADMIN_PASSWORD),
    independiente del login de Supabase Auth y del rol del tenant.
    """
    return session.get('superadmin_ok') is True


def superadmin_required(f):
    """Decorador: requiere sesión de superadmin (login por contraseña)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_superadmin():
            return redirect(url_for('platform_admin.login'))
        return f(*args, **kwargs)
    return decorated_function


def plan_required(*features):
    """Decorador: requiere que el plan de la compañía incluya las features dadas.

    Se usa después de @login_required. Si el plan no incluye alguna feature,
    muestra un mensaje y redirige al home.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            plan = effective_plan(g.get('company'))
            if not all(has_feature(plan, feature) for feature in features):
                flash(
                    "Tu plan no incluye esta función. "
                    "Actualiza tu plan desde la página de suscripción.",
                    "error"
                )
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
