"""
Blueprint de Administración de Compañía.

Rutas:
- GET/POST /admin/company/profile   — Perfil de la compañía
- GET/POST /admin/company/branding  — Logo y colores
- GET       /admin/company/users    — Gestión de usuarios
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app, jsonify
)
from cotizador.middleware import login_required, admin_required
import os
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
            company = db.get_company_by_id(company_id)
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
        # Usar cliente Supabase con service key para bypass RLS
        from supabase import create_client
        import os
        supabase_url = os.getenv('SUPABASE_URL')
        service_key = os.getenv('SUPABASE_SERVICE_KEY')

        if not supabase_url or not service_key:
            flash("Error: Configuración de Supabase incompleta", "error")
            return redirect(url_for('company.branding'))

        admin_client = create_client(supabase_url, service_key)

        file_data = file.read()
        file_path = f"company-assets/{company_id}/logo.png"

        # Subir a bucket company-assets (debe existir en Supabase Storage)
        bucket = admin_client.storage.from_('company-assets')
        bucket.upload(
            path=file_path,
            file=file_data,
            file_options={"content-type": "image/png", "upsert": "true"}
        )

        # Obtener URL pública
        logo_url = bucket.get_public_url(file_path)

        # Actualizar company con la URL
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

    return render_template(
        'admin/users.html',
        users=profiles,
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


#
# Criterios Fast Quote
#

@company_bp.route('/fast-quote-criteria', methods=['GET', 'POST'])
@login_required
@admin_required
def fast_quote_criteria():
    """Configurar criterios de precios para estimaciones con IA."""
    db = _get_db()
    company_id = _get_company_id()

    if not company_id:
        flash("No se encontró tu compañía", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        action = request.form.get('action', '').strip()
        criteria_id = request.form.get('criteria_id', '').strip()

        try:
            if action == 'add':
                data = {
                    "name": request.form.get('name', '').strip(),
                    "category": request.form.get('category', 'material').strip(),
                    "unit": request.form.get('unit', '').strip(),
                    "unit_price": float(request.form.get('unit_price', 0)),
                    "description": request.form.get('description', '').strip(),
                }

                if not data['name']:
                    flash("El nombre del criterio es obligatorio", "error")
                elif data['unit_price'] <= 0:
                    flash("El precio unitario debe ser mayor a 0", "error")
                else:
                    result = db.add_fast_quote_criteria(company_id, data)
                    if result:
                        flash(f"Criterio «{data['name']}» agregado correctamente", "success")
                    else:
                        flash("Error al agregar el criterio. Verifica la conexión a la base de datos.", "error")

            elif action == 'delete' and criteria_id:
                result = db.delete_fast_quote_criteria(criteria_id)
                if result:
                    flash("Criterio eliminado correctamente", "success")
                else:
                    flash("Error al eliminar el criterio", "error")

            elif action == 'toggle' and criteria_id:
                # Obtener estado actual
                all_criteria = db._get_all_fast_quote_criteria_admin(company_id)
                current = next((c for c in all_criteria if c['id'] == criteria_id), None)
                if current:
                    new_state = not current.get('is_active', True)
                    result = db.update_fast_quote_criteria(criteria_id, {"is_active": new_state})
                    if result:
                        estado = "activado" if new_state else "desactivado"
                        flash(f"Criterio {estado} correctamente", "success")
                    else:
                        flash("Error al cambiar el estado del criterio", "error")

        except ValueError as e:
            flash(f"Datos inválidos: {e}", "error")
        except Exception as e:
            logger.error(f"[FAST_QUOTE_CRITERIA] Error: {e}")
            flash(f"Error inesperado: {e}", "error")

        return redirect(url_for('company.fast_quote_criteria'))

    # GET: mostrar criterios
    company = db.get_company_by_id(company_id)
    criteria = db._get_all_fast_quote_criteria_admin(company_id)

    return render_template(
        'admin/fast_quote_criteria.html',
        company=company,
        criteria=criteria
    )
