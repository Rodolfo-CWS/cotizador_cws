"""
Middleware multi-tenant para CWS Cotizador SaaS.

Antes de cada request:
1. Verifica que el usuario esté autenticado (session con Supabase Auth)
2. Configura el contexto de compañía en PostgreSQL para RLS
3. Carga los datos de la compañía en g.company para templates
"""

from flask import g, session, redirect, url_for, request, flash
from functools import wraps

from cotizador.plans import has_feature, PLAN_FULL


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
        ]

        # Saltar middleware para rutas públicas
        path = request.path.rstrip('/') or '/'
        for public in public_routes:
            if path.startswith(public.rstrip('/')):
                return

        # Health check de la conexión PostgreSQL (se muere tras inactividad larga)
        try:
            conn = supabase_manager.pg_connection
            if conn and not conn.closed:
                try:
                    conn.rollback()
                except:
                    pass
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
            else:
                app.logger.warning("[MIDDLEWARE] Conexion PG cerrada, reconectando...")
                supabase_manager._inicializar_conexion()
        except Exception as e:
            app.logger.warning(f"[MIDDLEWARE] Reconectando PG: {e}")
            try:
                supabase_manager._inicializar_conexion()
            except:
                pass

        # Verificar sesión de usuario (Supabase Auth)
        if 'user_id' in session and 'company_id' in session:
            g.user = {
                'id': session.get('user_id'),
                'email': session.get('user_email'),
                'name': session.get('user_name'),
                'role': session.get('user_role', 'seller'),
            }

            # Configurar PostgreSQL para RLS
            company_id = session.get('company_id')
            if company_id:
                try:
                    connection = supabase_manager.pg_connection
                    if connection and not connection.closed:
                        # Rollback cualquier transacción fallida antes de seguir
                        try:
                            connection.rollback()
                        except:
                            pass
                        cursor = connection.cursor()
                        cursor.execute(
                            "SELECT set_config('app.current_company_id', %s, false)",
                            (company_id,)
                        )
                        cursor.close()
                except Exception as e:
                    app.logger.warning(
                        f"[MIDDLEWARE] No se pudo configurar RLS: {e}"
                    )
                    # Intentar reconectar si la conexión está muerta
                    try:
                        supabase_manager._inicializar_conexion()
                    except:
                        pass

                # Cargar datos de la compañía para templates
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
        return {
            'company': g.get('company'),
            'user': g.get('user'),
            'company_plan': (g.get('company') or {}).get('plan', PLAN_FULL),
            'plan_has_feature': has_feature,
        }


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
                   iva_rate, is_active, plan
                FROM public.companies WHERE id = %s AND is_active = true""",
                (company_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            if row:
                colnames = [desc[0] for desc in cursor.description]
                return dict(zip(colnames, row))
    except Exception:
        pass

    return None


def login_required(f):
    """Decorador: requiere autenticación con Supabase Auth."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
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


def plan_required(*features):
    """Decorador: requiere que el plan de la compañía incluya las features dadas.

    Se usa después de @login_required. Si el plan no incluye alguna feature,
    muestra un mensaje y redirige al home.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            plan = (g.get('company') or {}).get('plan', PLAN_FULL)
            if not all(has_feature(plan, feature) for feature in features):
                flash(
                    "Tu plan no incluye esta función. "
                    "Actualiza tu plan o contacta a soporte.",
                    "error"
                )
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
