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
from urllib.parse import urlparse, urljoin
import os
import logging


logger = logging.getLogger(__name__)

# Crear blueprint sin url_prefix — las rutas se registran con /auth/
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Alta de un correo que ya existe en auth.users. Con la protección contra
# enumeración, Supabase no lanza error: responde 200 con un usuario ficticio.
EMAIL_YA_REGISTRADO = (
    "Este correo ya está registrado. "
    "Inicia sesión o recupera tu contraseña."
)


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


# ── Helper de seguridad para redirects ──

def _is_safe_redirect_url(target):
    """Valida que una URL de redirect sea segura (mismo host, ruta interna)."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

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

            # 2b. Si no tiene perfil, intentar resolver una invitación pendiente
            if not profile:
                profile = _resolve_pending_invitation(user)

            if not profile:
                error = (
                    "Tu cuenta no está asociada a ninguna compañía. "
                    "Contacta al administrador."
                )
                return render_template('login.html', error=error)

            # 3. Guardar en sesión
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = ' '.join((profile.get('full_name') or email or '').split())
            session['user_role'] = profile.get('role', 'seller')
            session['company_id'] = profile.get('company_id')
            session.permanent = True  # sesión duradera (PERMANENT_SESSION_LIFETIME)

            logger.info(
                f"[AUTH] Login exitoso: {user.email} "
                f"(company={profile.get('company_id')}, role={profile.get('role')})"
            )

            # 4. Redirigir a la página que intentaba visitar, o al home
            next_url = session.pop('next_url', None)
            if next_url and _is_safe_redirect_url(next_url):
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
                    "redirect_to": request.host_url.rstrip('/') + '/auth/reset-password'
                })
                message = (
                    f"Si el email {email} está registrado, recibirás un enlace "
                    "para restablecer tu contraseña. Revisa tu bandeja de entrada."
                )
            except Exception as e:
                error = f"Error: {e}"

    return render_template('forgot_password.html', message=message, error=error)


@auth_bp.route('/reset-password')
def reset_password():
    """Página para establecer nueva contraseña (recibe token de Supabase en URL)."""
    return render_template('reset_password.html')


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

        # Datos de la empresa — obligatorios en el alta
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        footer_text = request.form.get('footer_text', '').strip()

        # Datos de la empresa — opcionales
        tax_id = request.form.get('tax_id', '').strip()
        company_email = request.form.get('company_email', '').strip()
        primary_color = request.form.get('primary_color', '').strip()
        secondary_color = request.form.get('secondary_color', '').strip()

        # IVA: siempre viene del select; parse seguro con default 16.00
        try:
            iva_rate = float(request.form.get('iva_rate', '16.00') or '16.00')
        except (TypeError, ValueError):
            iva_rate = 16.00

        # Registro = freemium. Toda cuenta nueva arranca en Starter; el upgrade
        # es post-login vía /billing (Stripe). Se ignora cualquier plan del form
        # para evitar que un POST forjado asigne un plan de pago.
        plan = 'starter'

        # Validaciones
        if not all([email, password, full_name, company_name, company_slug,
                    address, phone, footer_text]):
            error = "Completa los campos obligatorios"
            return render_template('register.html', error=error)

        if len(password) < 8:
            error = "La contraseña debe tener al menos 8 caracteres"
            return render_template('register.html', error=error)

        # Si hay una invitación pendiente para este email, redirigir a revisar
        # el correo (evita que un invitado cree una compañía temporal por error).
        try:
            from flask import current_app
            db = current_app.extensions.get('db_manager')
            if db and db.get_pending_invitation_by_email(email):
                error = (
                    "Este email ya tiene una invitación pendiente para unirse a "
                    "una empresa. Revisa tu correo y usa el enlace de la invitación."
                )
                return render_template('register.html', error=error)
        except Exception as e:
            logger.warning(f"[AUTH] Error verificando invitación en registro: {e}")

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

            # Alta repetida con protección contra enumeración: Supabase responde
            # 200, no crea el usuario y no cambia la contraseña. El cuerpo trae
            # identities vacío y un id que no existe en auth.users.
            if _identities_vacias(user):
                logger.info(
                    "[AUTH] Alta rechazada, correo ya registrado "
                    "(identities vacío): %s",
                    email,
                )
                error = EMAIL_YA_REGISTRADO
                return render_template('register.html', error=error)

            admin_client = get_supabase_admin_client()

            # El id ficticio del paso anterior no está en auth.users. Tampoco
            # creamos compañía si el cliente no devolvió identities.
            if not _auth_user_exists(admin_client, user.id):
                logger.info(
                    "[AUTH] Alta rechazada, el id devuelto no existe en "
                    "auth.users: %s (%s)",
                    email,
                    user.id,
                )
                error = EMAIL_YA_REGISTRADO
                return render_template('register.html', error=error)

            if _profile_exists(admin_client, user.id):
                logger.info(
                    "[AUTH] Alta rechazada, el usuario ya tiene perfil: %s",
                    email,
                )
                error = EMAIL_YA_REGISTRADO
                return render_template('register.html', error=error)

            # 2. Crear compañía (con los datos de alta obligatorios + opcionales)
            company_fields = {
                "address": address,
                "phone": phone,
                "footer_text": footer_text,
                "iva_rate": iva_rate,
            }
            if tax_id:
                company_fields["tax_id"] = tax_id
            if company_email:
                company_fields["email"] = company_email
            if primary_color:
                company_fields["primary_color"] = primary_color
            if secondary_color:
                company_fields["secondary_color"] = secondary_color

            company_id = None
            try:
                company_data = _create_company(
                    admin_client, company_name, company_slug, plan,
                    extra=company_fields
                )
                company_id = company_data['id']

                # 3. Crear perfil (admin de la compañía)
                _create_profile(
                    admin_client, user.id, company_id, full_name, 'admin'
                )

                # 4. Guardar en sesión solo si compañía y perfil quedaron creados
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['user_name'] = ' '.join(full_name.split())
                session['user_role'] = 'admin'
                session['company_id'] = company_id
            except Exception:
                logger.exception(
                    "[AUTH] Registro incompleto para %s; revirtiendo", email
                )
                _cleanup_partial_signup(
                    admin_client, company_id=company_id, user_id=user.id
                )
                raise

            # 5. Subir logo (opcional, no bloqueante). Se sube después de crear la
            #    compañía porque necesita el company_id. Un fallo aquí no borra
            #    la cuenta: el usuario ya puede entrar y subir el logo después.
            logo_file = request.files.get('logo') if request.files else None
            if logo_file and logo_file.filename:
                try:
                    from flask import current_app
                    db = current_app.extensions.get('db_manager')
                    if db:
                        logo_url = db.upload_company_logo(company_id, logo_file.read())
                        if logo_url:
                            db.update_company(company_id, {"logo_url": logo_url})
                except Exception as e:
                    logger.warning(f"[AUTH] No se pudo subir el logo (no bloqueante): {e}")

            logger.info(
                f"[AUTH] Nueva compañía registrada: {company_name} "
                f"({company_slug}) por {email}"
            )

            flash(
                "¡Cuenta creada exitosamente! Revisa o completa los datos de tu empresa.",
                "success"
            )
            return redirect(url_for('company.profile'))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AUTH] Error en registro: {error_msg}")
            error = _register_error_message(e, company_slug)

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


@auth_bp.route('/profile')
def profile():
    """Página de perfil del usuario."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Redirigir admin al panel de compañía
    if session.get('user_role') == 'admin':
        return redirect(url_for('company.profile'))
    return redirect(url_for('home'))


#
# Funciones auxiliares
#

def _get_profile(user_id: str):
    """Obtiene el perfil del usuario. Usa service key para bypassear RLS."""
    try:
        admin_client = get_supabase_admin_client()

        # 1. Obtener perfil
        resp = admin_client.table('profiles').select('*').eq('id', user_id).eq('is_active', True).execute()
        if not resp.data or len(resp.data) == 0:
            return None

        profile = resp.data[0]

        # 2. Obtener datos de la compañía
        company_id = profile.get('company_id')
        company = {}
        if company_id:
            cresp = admin_client.table('companies').select('name, slug').eq('id', company_id).eq('is_active', True).execute()
            if cresp.data and len(cresp.data) > 0:
                company = cresp.data[0]

        return {
            'id': profile['id'],
            'company_id': company_id,
            'full_name': profile.get('full_name', ''),
            'role': profile.get('role', 'seller'),
            'company_name': company.get('name', ''),
            'company_slug': company.get('slug', ''),
        }
    except Exception as e:
        logger.error(f"[AUTH] Error al obtener perfil: {e}")
        return None


def _resolve_pending_invitation(user):
    """Si el usuario tiene una invitación pendiente, crea su perfil y lo vincula.

    Se invoca desde login() cuando el usuario ya existe en Supabase Auth pero
    aún no tiene perfil. Devuelve el perfil (dict) o None si no había invitación.
    """
    try:
        from flask import current_app
        db = current_app.extensions.get('db_manager')
        if not db:
            return None

        invitation = db.get_pending_invitation_by_email(user.email)
        if not invitation:
            return None

        company_id = invitation.get('company_id')
        role = invitation.get('role', 'seller')
        full_name = (
            (user.user_metadata or {}).get('full_name')
            or user.email
            or ''
        )

        admin_client = get_supabase_admin_client()
        _create_profile(admin_client, user.id, company_id, full_name, role)
        db.accept_invitation(invitation.get('id'))

        logger.info(
            f"[AUTH] Invitación aceptada: {user.email} → "
            f"company={company_id} (role={role})"
        )
        return _get_profile(user.id)
    except Exception as e:
        logger.error(f"[AUTH] Error resolviendo invitación: {e}")
        return None


def _create_company(
    supabase_client: Client,
    name: str,
    slug: str,
    plan: str = 'starter',
    extra: dict = None
) -> dict:
    """Crea una nueva compañía usando el cliente admin (bypass RLS).

    `extra` permite inyectar campos adicionales (dirección, teléfono, IVA, footer,
    RFC, colores, email de contacto, etc.) capturados en el formulario de alta.
    """
    data = {
        "name": name,
        "slug": slug,
        "plan": plan,
        "footer_text": f"{name} | Esta cotización es válida por 30 días",
    }
    if extra:
        # El footer del formulario es obligatorio; si viniera vacío (no debería),
        # conservamos el default como red de seguridad.
        footer = extra.pop("footer_text", None)
        if footer:
            data["footer_text"] = footer
        data.update(extra)

    response = supabase_client.table('companies').insert(data).execute()

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


def _attr(obj, name, default=None):
    """Lee un campo de un modelo de Supabase o de un dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _identities_vacias(user) -> bool:
    """True si Supabase señaló un alta repetida con `identities` vacío.

    GoTrue, con confirmación de email activa, no devuelve error cuando el
    correo ya está confirmado (`user_repeated_signup`). `sanitizeUser` sustituye
    el id por uno nuevo y deja `identities` en vacío. Ese id no existe en
    auth.users y la contraseña no cambia. Un alta nueva siempre trae al menos
    una identity.
    """
    identities = _attr(user, "identities", None)
    if identities is None:
        return False
    try:
        return len(identities) == 0
    except TypeError:
        return False


def _is_auth_user_missing(exc: Exception) -> bool:
    """True solo si el admin API dijo que ese usuario no existe.

    Un 404 genérico (URL mal formada, proyecto caído) no cuenta: si no
    podemos afirmar que el id es ficticio, el alta se aborta sin decir
    que el correo ya está registrado.
    """
    code = str(getattr(exc, "code", "") or "").lower()
    if code == "user_not_found":
        return True
    message = str(exc).lower()
    return "user not found" in message or "user does not exist" in message


def _auth_user_exists(admin_client: Client, user_id) -> bool:
    """Comprueba con la service role que el id está en auth.users.

    El alta repetida devuelve un UUID que `get_user_by_id` no encuentra.
    Un fallo distinto de «no existe» se propaga: no hay que crear compañía
    si no pudimos verificar el usuario.
    """
    if not user_id:
        return False
    try:
        resp = admin_client.auth.admin.get_user_by_id(str(user_id))
    except Exception as exc:
        if _is_auth_user_missing(exc):
            return False
        raise
    found = _attr(resp, "user")
    if not found:
        return False
    return str(_attr(found, "id", "")) == str(user_id)


def _profile_exists(admin_client: Client, user_id) -> bool:
    """True si ya hay una fila en public.profiles para ese usuario."""
    resp = (
        admin_client.table("profiles")
        .select("id")
        .eq("id", str(user_id))
        .limit(1)
        .execute()
    )
    return bool(getattr(resp, "data", None))


def _cleanup_partial_signup(admin_client: Client, company_id, user_id):
    """Borra compañía, perfil y el usuario de Auth de un alta que no terminó.

    public.profiles.id no tiene FK hacia auth.users, así que un perfil a medias
    no se cae solo. También se borra el usuario de Auth creado en este intento.
    Con autoconfirm, un segundo sign_up del mismo correo responde
    «User already registered» y la persona no podría terminar el alta.
    """
    if user_id:
        try:
            admin_client.table("profiles").delete().eq("id", str(user_id)).execute()
        except Exception as exc:
            logger.error("[AUTH] No se pudo revertir el perfil %s: %s", user_id, exc)
    if company_id:
        try:
            admin_client.table("companies").delete().eq(
                "id", str(company_id)
            ).execute()
        except Exception as exc:
            logger.error(
                "[AUTH] No se pudo revertir la compañía %s: %s", company_id, exc
            )
    if user_id:
        try:
            admin_client.auth.admin.delete_user(str(user_id))
        except Exception as exc:
            logger.error(
                "[AUTH] No se pudo revertir el usuario de Auth %s: %s",
                user_id,
                exc,
            )


def _register_error_message(exc: Exception, company_slug: str) -> str:
    """Texto en español para un fallo de alta. El slug se distingue del correo."""
    error_msg = str(exc)
    low = error_msg.lower()
    # El error de Postgres por slug contiene "duplicate" y "unique". Hay que
    # mirarlo antes que cualquier texto genérico de duplicado.
    if "slug" in low and (
        "unique" in low or "duplicate" in low or "already exists" in low
    ):
        return (
            f"El identificador '{company_slug}' ya está en uso. "
            "Elige otro."
        )
    if (
        "already registered" in low
        or "user already exists" in low
        or "user_already_exists" in low
    ):
        return EMAIL_YA_REGISTRADO
    return f"Error al registrarse: {error_msg}"
