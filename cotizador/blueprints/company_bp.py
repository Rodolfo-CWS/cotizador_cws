"""
Blueprint de Administración de Compañía.

Rutas:
- GET/POST /admin/company/profile   — Perfil de la compañía
- GET/POST /admin/company/branding  — Logo y colores
- GET       /admin/company/users    — Gestión de usuarios
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app, jsonify, g
)
from cotizador.middleware import login_required, admin_required
from cotizador.plans import effective_plan, get_limit, has_feature, FEATURE_IMPORT_PDFS
import os
import hashlib
import logging

logger = logging.getLogger(__name__)

company_bp = Blueprint('company', __name__, url_prefix='/admin/company')


def _get_db():
    """Obtiene el db_manager de las extensiones de la app."""
    return current_app.extensions.get('db_manager')


def _get_company_id():
    """Obtiene el company_id de la sesión."""
    return session.get('company_id')


#
# Perfil de la compañía
#

@company_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@admin_required
def profile():
    """Editar perfil de la compañía."""
    db = _get_db()
    company_id = _get_company_id()

    if not company_id:
        flash("No se encontró tu compañía", "error")
        return redirect(url_for('home'))

    company = db.get_company_by_id(company_id)

    if request.method == 'POST':
        data = {
            "tax_id": request.form.get('tax_id', '').strip(),
            "address": request.form.get('address', '').strip(),
            "phone": request.form.get('phone', '').strip(),
            "email": request.form.get('email', '').strip(),
            "iva_rate": float(request.form.get('iva_rate', 16.00)),
            "footer_text": request.form.get('footer_text', '').strip(),
        }

        result = db.update_company(company_id, data)
        if result:
            flash("Perfil actualizado correctamente", "success")
            return redirect(url_for('company.branding'))
        else:
            flash("Error al actualizar el perfil", "error")

    return render_template('admin/company_profile.html', company=company)


#
# Branding (logo y colores)
#

@company_bp.route('/branding', methods=['GET', 'POST'])
@login_required
@admin_required
def branding():
    """Personalizar branding de la compañía."""
    db = _get_db()
    company_id = _get_company_id()

    if not company_id:
        flash("No se encontró tu compañía", "error")
        return redirect(url_for('home'))

    company = db.get_company_by_id(company_id)

    if request.method == 'POST':
        data = {
            "primary_color": request.form.get('primary_color', '#4f46e5').strip(),
            "secondary_color": request.form.get('secondary_color', '#1e293b').strip(),
        }

        # Validar colores hex
        for field, value in data.items():
            if not value.startswith('#') or len(value) not in (4, 7):
                flash(f"Color inválido para {field}: {value}", "error")
                return render_template('admin/branding.html', company=company)

        result = db.update_company(company_id, data)
        if result:
            flash("Branding actualizado correctamente", "success")
            return redirect(url_for('company.users'))
        else:
            flash("Error al actualizar branding", "error")

    return render_template('admin/branding.html', company=company)


@company_bp.route('/branding/logo', methods=['POST'])
@login_required
@admin_required
def upload_logo():
    """Subir logo de la compañía a Supabase Storage."""
    db = _get_db()
    company_id = _get_company_id()

    if 'logo' not in request.files:
        flash("No se seleccionó ningún archivo", "error")
        return redirect(url_for('company.branding'))

    file = request.files['logo']
    if file.filename == '':
        flash("No se seleccionó ningún archivo", "error")
        return redirect(url_for('company.branding'))

    try:
        file_data = file.read()
        logo_url = db.upload_company_logo(company_id, file_data)

        if not logo_url:
            flash("Error al subir el logo. Intenta de nuevo.", "error")
            return redirect(url_for('company.branding'))

        db.update_company(company_id, {"logo_url": logo_url})
        flash("Logo subido correctamente", "success")
    except Exception as e:
        logger.error(f"[COMPANY] Error subiendo logo: {e}")
        flash(f"Error al subir el logo: {e}", "error")

    return redirect(url_for('company.branding'))


#
# Gestión de Usuarios
#

@company_bp.route('/users')
@login_required
@admin_required
def users():
    """Listar usuarios de la compañía."""
    db = _get_db()
    company_id = _get_company_id()

    if not company_id:
        flash("No se encontró tu compañía", "error")
        return redirect(url_for('home'))

    profiles = db.get_profiles_by_company(company_id) or []
    invitations = db.list_invitations_by_company(company_id) or []
    active_users = db.count_active_users(company_id)

    return render_template(
        'admin/users.html',
        users=profiles,
        invitations=invitations,
        active_users=active_users,
        company=db.get_company_by_id(company_id)
    )


@company_bp.route('/users/<user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    """Desactivar un usuario (no eliminar)."""
    db = _get_db()
    company_id = _get_company_id()

    # Solo desactivar usuarios de tu misma compañía
    try:
        from supabase import create_client
        import os
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        client = create_client(url, key)

        # Verificar que el usuario pertenece a la misma compañía
        resp = client.table('profiles').select('company_id').eq('id', user_id).execute()
        if not resp.data or resp.data[0]['company_id'] != company_id:
            flash("No tienes permiso para modificar este usuario", "error")
            return redirect(url_for('company.users'))

        # Desactivar
        client.table('profiles').update({'is_active': False}).eq('id', user_id).execute()
        flash("Usuario desactivado", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")

    return redirect(url_for('company.users'))


@company_bp.route('/users/<user_id>/role', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Cambiar el rol de un usuario de la misma compañía."""
    db = _get_db()
    company_id = _get_company_id()

    role = (request.form.get('role') or '').strip()
    if role not in ('admin', 'manager', 'seller'):
        flash("Rol inválido", "error")
        return redirect(url_for('company.users'))

    # Solo cambiar el rol de usuarios de tu misma compañía.
    profiles = db.get_profiles_by_company(company_id) or []
    if not any(str(p.get('id')) == str(user_id) for p in profiles):
        flash("No tienes permiso para modificar este usuario", "error")
        return redirect(url_for('company.users'))

    if db.update_profile_role(user_id, role):
        flash("Rol actualizado correctamente", "success")
    else:
        flash("No se pudo actualizar el rol", "error")

    return redirect(url_for('company.users'))


@company_bp.route('/users/invite', methods=['POST'])
@login_required
@admin_required
def invite_user():
    """Invitar a un nuevo usuario por email a unirse a la compañía."""
    db = _get_db()
    company_id = _get_company_id()

    if not company_id:
        flash("No se encontró tu compañía", "error")
        return redirect(url_for('company.users'))

    email = request.form.get('email', '').strip().lower()
    role = request.form.get('role', 'seller').strip()

    if not email or '@' not in email:
        flash("Ingresa un email válido", "error")
        return redirect(url_for('company.users'))

    if role not in ('admin', 'manager', 'seller'):
        role = 'seller'

    company = db.get_company_by_id(company_id) or {}
    # El límite de asientos se lee del plan (no de la columna suelta companies.max_users).
    # None (cuenta interna) = sin límite.
    max_users = get_limit(effective_plan(company), 'max_users')

    # Límite de asientos: usuarios activos + invitaciones pendientes
    active_users = db.count_active_users(company_id)
    pending_invites = len(db.list_invitations_by_company(company_id))
    if max_users is not None and active_users + pending_invites >= max_users:
        flash(
            f"Límite de usuarios alcanzado ({max_users}). "
            "Actualiza tu plan o libera un asiento.",
            "error"
        )
        return redirect(url_for('company.users'))

    # Evitar duplicar una invitación activa para el mismo email
    existing = db.get_pending_invitation_by_email(email)
    if existing and str(existing.get('company_id')) == str(company_id):
        flash("Este email ya tiene una invitación pendiente", "error")
        return redirect(url_for('company.users'))

    invitation = db.create_invitation(
        company_id, email, role, invited_by=session.get('user_id')
    )
    if not invitation:
        flash("No se pudo crear la invitación. Intenta de nuevo.", "error")
        return redirect(url_for('company.users'))

    # Enviar email de invitación vía Supabase Auth
    try:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        client = create_client(url, key)
        # Tras aceptar, el usuario debe definir su contraseña; reutilizamos la
        # página de reset (ya pública y con el flujo updateUser listo).
        redirect_to = request.host_url.rstrip('/') + '/auth/reset-password?invite=1'
        data = {
            "company_name": company.get('name', ''),
            "inviter_name": session.get('user_name', ''),
        }
        _admin_invite_user(client, email, redirect_to, data)
        flash(f"Invitación enviada a {email} (rol: {role})", "success")
    except Exception as e:
        error_msg = str(e).lower()
        if 'already registered' in error_msg or 'already exists' in error_msg:
            # El usuario ya tiene cuenta en auth.users; la invitación queda
            # pendiente y se vinculará automáticamente en su próximo login.
            flash(
                f"{email} ya tiene cuenta. Se vinculará automáticamente "
                "cuando inicie sesión.",
                "success"
            )
        else:
            # No dejar una invitación colgando si el email no se pudo enviar
            db.revoke_invitation(invitation.get('id'))
            flash(f"Error al enviar la invitación: {e}", "error")

    return redirect(url_for('company.users'))


@company_bp.route('/users/<invitation_id>/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_invitation(invitation_id):
    """Revocar una invitación pendiente."""
    db = _get_db()
    company_id = _get_company_id()

    try:
        pending = db.list_invitations_by_company(company_id)
        if not any(str(i.get('id')) == str(invitation_id) for i in pending):
            flash("No tienes permiso para revocar esta invitación", "error")
            return redirect(url_for('company.users'))

        if db.revoke_invitation(invitation_id):
            flash("Invitación revocada", "success")
        else:
            flash("No se pudo revocar la invitación", "error")
    except Exception as e:
        flash(f"Error: {e}", "error")

    return redirect(url_for('company.users'))


@company_bp.route('/users/<invitation_id>/resend', methods=['POST'])
@login_required
@admin_required
def resend_invitation(invitation_id):
    """Reenviar el email de una invitación pendiente."""
    db = _get_db()
    company_id = _get_company_id()

    invitation = None
    for inv in (db.list_invitations_by_company(company_id) or []):
        if str(inv.get('id')) == str(invitation_id):
            invitation = inv
            break

    if not invitation:
        flash("No tienes permiso para reenviar esta invitación", "error")
        return redirect(url_for('company.users'))

    email = invitation.get('email')
    role = invitation.get('role', 'seller')
    company = db.get_company_by_id(company_id) or {}

    try:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        client = create_client(url, key)
        redirect_to = request.host_url.rstrip('/') + '/auth/reset-password?invite=1'
        data = {
            "company_name": company.get('name', ''),
            "inviter_name": session.get('user_name', ''),
        }
        _admin_invite_user(client, email, redirect_to, data)
        flash(f"Invitación reenviada a {email} (rol: {role})", "success")
    except Exception as e:
        error_msg = str(e).lower()
        if 'already registered' in error_msg or 'already exists' in error_msg:
            flash(f"{email} ya tiene cuenta. Se vinculará automáticamente al iniciar sesión.", "success")
        else:
            flash(f"Error al reenviar la invitación: {e}", "error")

    return redirect(url_for('company.users'))


def _admin_invite_user(client, email, redirect_to, data=None):
    """Envía invitación vía Supabase Auth, tolerando firmas de versión distintas."""
    options = {"redirect_to": redirect_to}
    if data:
        options["data"] = data
    try:
        # Firma moderna: invite_user_by_email(email, options)
        client.auth.admin.invite_user_by_email(email, options)
    except TypeError:
        # Firma antigua: invite_user_by_email(email, redirect_to=..., data=...)
        client.auth.admin.invite_user_by_email(
            email, redirect_to=redirect_to, data=data
        )


#
# Criterios Fast Quote
#

@company_bp.route('/fast-quote-criteria', methods=['GET', 'POST'])
@login_required
@admin_required
def fast_quote_criteria():
    """Configurar las instrucciones adicionales personales para Fast Quote.

    Los criterios base son globales (tabla fast_quote_global_prompt, editados por
    el superadmin); aquí el admin solo escribe la personalización de su empresa.
    """
    db = _get_db()
    company_id = _get_company_id()

    if not company_id:
        flash("No se encontró tu compañía", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        prompt_text = request.form.get('prompt_text', '').strip()

        try:
            result = db.save_fast_quote_prompt(company_id, prompt_text)
            if result:
                flash("Instrucciones guardadas correctamente ✅", "success")
            else:
                flash("Error al guardar. Verifica la conexión a la base de datos.", "error")
        except Exception as e:
            logger.error(f"[FAST_QUOTE_PROMPT] Error: {e}")
            flash(f"Error inesperado: {e}", "error")

        return redirect(url_for('company.fast_quote_criteria'))

    # GET: mostrar instrucciones actuales
    company = db.get_company_by_id(company_id)
    prompt_text = db.get_fast_quote_prompt(company_id)

    return render_template(
        'admin/fast_quote_criteria.html',
        company=company,
        prompt_text=prompt_text,
        updated_at=None  # Se podría obtener de la DB si se necesita
    )


#
# Importar cotizaciones antiguas (PDFs digitales)
#

# Topes de subida (protección del endpoint; el frontend sube de 1 en 1 o 2 en 2).
MAX_ARCHIVOS_POR_SUBIDA = 10
MAX_BYTES_ARCHIVO = 20 * 1024 * 1024      # 20 MB
MAX_CARACTERES_TEXTO = 500_000            # el tsvector tiene límite de 1 MB
MIN_CARACTERES_POR_PAGINA = 50            # rechaza PDFs escaneados

_storage_manager = None


def _get_storage():
    """Instancia perezosa de SupabaseStorageManager (bucket privado imported-pdfs)."""
    global _storage_manager
    if _storage_manager is None:
        from supabase_storage_manager import SupabaseStorageManager
        _storage_manager = SupabaseStorageManager()
    return _storage_manager


def _extraer_texto_pdf(file_bytes):
    """Extrae texto de un PDF con pypdf. Devuelve (texto, num_paginas, error)."""
    import io
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", None, "pypdf no está instalado"
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        num_paginas = len(reader.pages)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                pass
        partes = []
        for page in reader.pages:
            try:
                partes.append(page.extract_text() or "")
            except Exception:
                partes.append("")
        return "\n".join(partes), num_paginas, None
    except Exception as e:
        return "", None, f"No se pudo leer el PDF: {e}"


@company_bp.route('/importar-pdfs', methods=['GET', 'POST'])
@login_required
@admin_required
def importar_pdfs():
    """Pantalla de importación de cotizaciones antiguas (solo admin)."""
    db = _get_db()
    company_id = _get_company_id()

    if not company_id:
        flash("No se encontró tu compañía", "error")
        return redirect(url_for('home'))

    company = db.get_company_by_id(company_id) or {}
    plan = effective_plan(company)
    plan_has_import = has_feature(plan, FEATURE_IMPORT_PDFS)
    max_imported = get_limit(plan, 'max_imported_pdfs')

    if request.method == 'GET':
        pdfs = db.listar_pdfs_importados(company_id) if plan_has_import else []
        total_importados = db.contar_pdfs_importados(company_id)
        return render_template(
            'admin/import_pdfs.html',
            company=company,
            pdfs=pdfs,
            total_importados=total_importados,
            max_imported_pdfs=max_imported,
            plan_has_import=plan_has_import,
        )

    # ── POST: procesar archivos ──
    if not plan_has_import:
        return jsonify({"success": False, "error": "Tu plan no incluye la importación de PDFs"}), 403

    files = request.files.getlist('files')
    if not files or all(not f or not f.filename for f in files):
        return jsonify({"success": False, "error": "No se recibieron archivos"}), 400
    if len(files) > MAX_ARCHIVOS_POR_SUBIDA:
        return jsonify({"success": False, "error": f"Máximo {MAX_ARCHIVOS_POR_SUBIDA} archivos por subida"}), 400

    uploaded_by = session.get('user_id')
    storage = _get_storage()
    contar_actual = db.contar_pdfs_importados(company_id)

    resultados = []
    importados = duplicados = rechazados = 0

    for f in files:
        nombre = f.filename or 'sin-nombre.pdf'
        item = {"nombre": nombre, "estado": "rechazado", "motivo": ""}
        try:
            # Validación básica: extensión + tamaño
            if not nombre.lower().endswith('.pdf'):
                item["motivo"] = "no es PDF"
            elif f.content_length is not None and f.content_length > MAX_BYTES_ARCHIVO:
                item["motivo"] = "excede 20 MB"
            else:
                file_bytes = f.read()
                if len(file_bytes) > MAX_BYTES_ARCHIVO:
                    item["motivo"] = "excede 20 MB"
                elif not file_bytes.startswith(b'%PDF'):
                    item["motivo"] = "no es un PDF válido"
                else:
                    # Límite del plan
                    if max_imported is not None and contar_actual >= max_imported:
                        item["motivo"] = "límite del plan alcanzado"
                    else:
                        hash_contenido = hashlib.sha256(file_bytes).hexdigest()

                        if db.existe_hash_pdf_importado(company_id, hash_contenido):
                            item["estado"] = "duplicado"
                            item["motivo"] = "ya estaba importado"
                            duplicados += 1
                            resultados.append(item)
                            continue

                        texto, num_paginas, err = _extraer_texto_pdf(file_bytes)
                        if err:
                            item["motivo"] = err
                        else:
                            import re as _re
                            caracteres_utiles = len(_re.sub(r'\s', '', texto or ''))
                            promedio = caracteres_utiles / num_paginas if num_paginas else 0
                            if promedio < MIN_CARACTERES_POR_PAGINA:
                                item["motivo"] = "Este PDF parece escaneado; solo se aceptan PDFs digitales"
                            else:
                                texto_truncado = (texto or '')[:MAX_CARACTERES_TEXTO]
                                storage_path = f"{company_id}/antiguas/{hash_contenido}.pdf"
                                subido = storage.subir_pdf_importado(company_id, hash_contenido, file_bytes)
                                if 'error' in subido:
                                    item["motivo"] = subido.get('error')
                                else:
                                    storage_path = subido.get('storage_path') or storage_path
                                    insertado = db.insertar_pdf_importado(
                                        company_id, nombre, storage_path, texto_truncado,
                                        num_paginas, hash_contenido, len(file_bytes), uploaded_by
                                    )
                                    if insertado.get('duplicado'):
                                        item["estado"] = "duplicado"
                                        item["motivo"] = "ya estaba importado"
                                        duplicados += 1
                                        storage.eliminar_objeto_importado(storage_path)
                                    elif insertado.get('success'):
                                        item["estado"] = "importado"
                                        importados += 1
                                        contar_actual += 1
                                    else:
                                        item["motivo"] = insertado.get('error') or "no se pudo guardar"
                                        storage.eliminar_objeto_importado(storage_path)
        except Exception as e:
            logger.error(f"[IMPORT_PDFS] Error procesando {nombre}: {e}")
            item["motivo"] = f"error interno: {e}"

        if item["estado"] == "rechazado":
            rechazados += 1
        resultados.append(item)

    return jsonify({
        "success": True,
        "resultados": resultados,
        "resumen": {"importados": importados, "duplicados": duplicados, "rechazados": rechazados},
    })


@company_bp.route('/importar-pdfs/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_pdfs_importados():
    """Elimina uno o varios PDFs importados (fila + objeto en Storage)."""
    db = _get_db()
    company_id = _get_company_id()
    datos = request.get_json(silent=True) or {}
    ids = datos.get('ids') or []

    if not ids:
        return jsonify({"success": False, "error": "No se indicaron PDFs"}), 400

    eliminados = 0
    for pdf_id in ids:
        if db.eliminar_pdf_importado(str(pdf_id), company_id).get('success'):
            eliminados += 1

    return jsonify({"success": True, "eliminados": eliminados})
