"""
Utilidades compartidas para el cotizador CWS.
Funciones auxiliares extraídas de app.py para ser usadas por los blueprints.
"""
import json
from flask import current_app


def safe_float(value, default=0.0):
    """
    Convierte un valor a float de forma robusta, manejando strings,
    comas decimales europeas, y valores nulos.
    """
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    try:
        str_value = str(value).strip()

        if not str_value or str_value.lower() in ['', 'none', 'null', 'n/a']:
            return default

        if ',' in str_value:
            parts = str_value.split(',')
            if len(parts) == 2 and len(parts[1]) <= 3 and parts[1].isdigit():
                str_value = f"{parts[0]}.{parts[1]}"
            else:
                str_value = str_value.replace(',', '')

        cleaned = ''
        for char in str_value:
            if char.isdigit() or char in ['.', '-']:
                cleaned += char

        if not cleaned or cleaned == '-':
            return default

        result = float(cleaned)

        if abs(result) > 1e10:
            print(f"[SAFE_FLOAT] Valor muy grande detectado: {result}, usando default")
            return default

        return result

    except (ValueError, TypeError, AttributeError) as e:
        print(f"[SAFE_FLOAT] Error convirtiendo '{value}' a float: {e}")
        return default


def safe_int(value, default=0):
    """Convierte un valor a int de forma robusta"""
    return int(safe_float(value, default))


def validate_material_data(material, item_index=0, material_index=0):
    """
    Valida y limpia los datos de un material, asegurando tipos correctos.
    """
    if not isinstance(material, dict):
        print(f"[VALIDATE] Item {item_index}, Material {material_index}: No es dict válido")
        return {
            'descripcion': 'Material inválido',
            'peso': 1.0,
            'cantidad': 0.0,
            'precio': 0.0,
            'subtotal': 0.0
        }

    descripcion = material.get('descripcion') or material.get('material', 'Sin descripción')
    peso = safe_float(material.get('peso'), 1.0)
    cantidad = safe_float(material.get('cantidad'), 0.0)
    precio = safe_float(material.get('precio'), 0.0)

    if peso < 0:
        peso = 0.0
    if cantidad < 0:
        print(f"[VALIDATE] Cantidad negativa detectada: {cantidad}, corrigiendo a 0")
        cantidad = 0.0
    if precio < 0:
        print(f"[VALIDATE] Precio negativo detectado: {precio}, corrigiendo a 0")
        precio = 0.0

    subtotal = round(peso * cantidad * precio, 2)

    return {
        'descripcion': descripcion,
        'peso': peso,
        'cantidad': cantidad,
        'precio': precio,
        'subtotal': subtotal
    }


def wrap_description_text(text, max_chars_per_line=45):
    """Utility function to wrap long description text for PDF cells"""
    if not text or len(text) <= max_chars_per_line:
        return text

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line + " " + word) > max_chars_per_line and current_line:
            lines.append(current_line)
            current_line = word
        else:
            if current_line:
                current_line += " " + word
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


def is_json_request():
    """Determina si la request actual espera respuesta JSON"""
    from flask import request
    return (
        request.headers.get('Accept') == 'application/json' or
        request.headers.get('Content-Type') == 'application/json' or
        request.args.get('format') == 'json'
    )


def handle_error_response(error, item_id=None):
    """Maneja respuestas de error de forma consistente"""
    error_msg = str(error) if error else "Error desconocido"
    print(f"[ERROR] {error_msg}" + (f" (ID: {item_id})" if item_id else ""))

    if is_json_request():
        from flask import jsonify
        return jsonify({"error": error_msg}), 500
    else:
        from flask import render_template
        return render_template('error.html', error=error_msg), 500


def handle_not_found_response(item_id):
    """Maneja respuestas 404 de forma consistente"""
    msg = f"Cotización no encontrada: {item_id}"

    if is_json_request():
        from flask import jsonify
        return jsonify({"error": msg}), 404
    else:
        from flask import render_template
        return render_template('error.html', error=msg), 404


def get_managers():
    """Helper para blueprints: obtiene db_manager, pdf_manager, sync_scheduler y LISTA_MATERIALES"""
    db = current_app.extensions.get('db_manager')
    pdf = current_app.extensions.get('pdf_manager')
    sync = current_app.extensions.get('sync_scheduler')
    materiales = current_app.config.get('LISTA_MATERIALES', [])
    return db, pdf, sync, materiales
