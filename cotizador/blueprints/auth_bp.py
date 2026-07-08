"""
Blueprint de Autenticación con Supabase Auth.

Maneja:
- POST /auth/login — Login con email/password via Supabase Auth
- POST /auth/register — Registro de nuevo usuario + compañía
- GET  /auth/logout — Cerrar sesión
- GET  /auth/me — Datos del usuario actual (API)

El flujo de autenticación:
1. Usuario envía email + password
2. Flask usa Supabase Python client para verificar credenciales
3. Si es válido, busca el perfil (company_id, role) en public.profiles
4. Almacena user_id, company_id, user_role en Flask session
5. Middleware usa estos datos para RLS y templates
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from supabase import create_client, Client
import os
import logging

logger = logging.getLogger(__name__)

# Crear blueprint sin url_prefix — las rutas se registran con /auth/
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def get_supabase_auth_client() -> Client:
    """Obtiene un cliente Supabase configurado para operaciones auth."""
    from flask import current_app

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')

    if not url or not key:
        raise RuntimeError("SUPABASE_URL y SUPABASE_ANON_KEY son requeridas")

    return create_client(url, key)


def get_supabase_admin_client() -> Client:
    """Obtiene un cliente Supabase con service key (bypass RLS)."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_SERVICE_KEY es requerida para operaciones admin"
        )

    return create_client(url, key)


#
# Rutas de autenticación
#

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login con Supabase Auth."""
    # Si ya está autenticado, redirigir al home
    if 'user_id' in session:
        return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = "Email y contraseña son requeridos"
            return render_template('login.html', error=error)

        try:
            # 1. Autenticar con Supabase Auth
            supabase = get_supabase_auth_client()
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            if not auth_response or not auth_response.user:
                error = "Credenciales inválidas"
                return render_template('login.html', error=error)

            user = auth_response.user

            # 2. Buscar perfil del usuario (company_id, role)
            profile = _get_profile(user.id)

            if not profile:
                error = (
                    "Tu cuenta no está asociada a ninguna compañía. "
                    "Contacta al administrador."
                )
                return render_template('login.html', error=error)

            # 3. Guardar en sesión
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = profile.get('full_name', email)
            session['user_role'] = profile.get('role', 'seller')
            session['company_id'] = profile.get('company_id')

            logger.info(
                f"[AUTH] Login exitoso: {user.email} "
                f"(company={profile.get('company_id')}, role={profile.get('role')})"
            )

            # 4. Redirigir a la página que intentaba visitar, o al home
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            return redirect(url_for('home'))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AUTH] Error en login: {error_msg}")

            if "Invalid login credentials" in error_msg:
                error = "Email o contraseña incorrectos"
            elif "Email not confirmed" in error_msg:
                error = (
                    "Debes confirmar tu email antes de iniciar sesión. "
                    "Revisa tu bandeja de entrada."
                )
            else:
                error = f"Error al iniciar sesión: {error_msg}"

    return render_template('login.html', error=error)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Solicitar recuperación de contraseña via Supabase Auth."""
    message = None
    error = None

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if email:
            try:
                supabase = get_supabase_auth_client()
                supabase.auth.reset_password_for_email(email, {
                    "redirect_to": request.host_url.rstrip('/') + '/auth/login'
                })
                message = (
                    f"Si el email {email} está registrado, recibirás un enlace "
                    "para restablecer tu contraseña. Revisa tu bandeja de entrada."
                )
            except Exception as e:
                error = f"Error: {e}"

    return render_template('forgot_password.html', message=message, error=error)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de nuevo usuario + compañía."""
    if 'user_id' in session:
        return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        company_slug = request.form.get('company_slug', '').strip().lower()

        # Validaciones
        if not all([email, password, full_name, company_name, company_slug]):
            error = "Todos los campos son requeridos"
            return render_template('register.html', error=error)

        if len(password) < 8:
            error = "La contraseña debe tener al menos 8 caracteres"
            return render_template('register.html', error=error)

        try:
            # 1. Crear usuario en Supabase Auth
            supabase = get_supabase_auth_client()
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                    }
                }
            })

            if not auth_response or not auth_response.user:
                error = "Error al crear la cuenta"
                return render_template('register.html', error=error)

            user = auth_response.user

            # 2. Crear compañía
            admin_client = get_supabase_admin_client()
            company_data = _create_company(
                admin_client, company_name, company_slug
            )
            company_id = company_data['id']

            # 3. Crear perfil (admin de la compañía)
            _create_profile(
                admin_client, user.id, company_id, full_name, 'admin'
            )

            # 4. Guardar en sesión
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = full_name
            session['user_role'] = 'admin'
            session['company_id'] = company_id

            logger.info(
                f"[AUTH] Nueva compañía registrada: {company_name} "
                f"({company_slug}) por {email}"
            )

            flash(
                "¡Cuenta creada exitosamente! Configura el perfil de tu empresa.",
                "success"
            )
            return redirect(url_for('company.profile'))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AUTH] Error en registro: {error_msg}")

            if "already registered" in error_msg.lower() or \
               "duplicate" in error_msg.lower():
                error = "Este email ya está registrado"
            elif "slug" in error_msg.lower() and "unique" in error_msg.lower():
                error = (
                    f"El identificador '{company_slug}' ya está en uso. "
                    "Elige otro."
                )
            else:
                error = f"Error al registrarse: {error_msg}"

    return render_template('register.html', error=error)


@auth_bp.route('/logout')
def logout():
    """Cerrar sesión."""
    user_name = session.get('user_name', 'Usuario')

    # Limpiar sesión
    session.clear()

    logger.info(f"[AUTH] Logout: {user_name}")
    return redirect(url_for('auth.login'))


@auth_bp.route('/me')
def me():
    """API: Datos del usuario actual."""
    if 'user_id' not in session:
        return jsonify({"authenticated": False}), 401

    return jsonify({
        "authenticated": True,
        "user_id": session.get('user_id'),
        "email": session.get('user_email'),
        "name": session.get('user_name'),
        "role": session.get('user_role'),
        "company_id": session.get('company_id'),
    })


#
# Funciones auxiliares
#

def _get_profile(user_id: str):
    """Obtiene el perfil del usuario desde la base de datos."""
    from flask import current_app

    try:
        db_manager = current_app.extensions.get('db_manager')
        if not db_manager or not db_manager.pg_connection:
            return None

        connection = db_manager.pg_connection
        if connection.closed:
            return None

        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT p.id, p.company_id, p.full_name, p.role,
                       c.name as company_name, c.slug as company_slug
                FROM public.profiles p
                JOIN public.companies c ON c.id = p.company_id
                WHERE p.id = %s AND p.is_active = true AND c.is_active = true
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                colnames = [desc[0] for desc in cursor.description]
                return dict(zip(colnames, row))
            return None
        finally:
            cursor.close()
    except Exception as e:
        logger.error(f"[AUTH] Error al obtener perfil: {e}")
        return None


def _create_company(supabase_client: Client, name: str, slug: str) -> dict:
    """Crea una nueva compañía usando el cliente admin (bypass RLS)."""
    response = supabase_client.table('companies').insert({
        "name": name,
        "slug": slug,
        "footer_text": f"{name} | Esta cotización es válida por 30 días",
    }).execute()

    if not response.data:
        raise Exception("No se pudo crear la compañía")

    return response.data[0]


def _create_profile(
    supabase_client: Client,
    user_id: str,
    company_id: str,
    full_name: str,
    role: str
):
    """Crea un perfil de usuario vinculado a una compañía."""
    response = supabase_client.table('profiles').insert({
        "id": user_id,
        "company_id": company_id,
        "full_name": full_name,
        "role": role,
    }).execute()

    if not response.data:
        raise Exception("No se pudo crear el perfil")
