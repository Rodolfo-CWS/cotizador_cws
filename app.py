"""
CWS Cotizador - Archivo principal (wrapper thin).
La inicialización se delega al paquete cotizador/ (factory pattern).
Todas las rutas se preservan aquí para backward compatibility.
"""
# ── Imports del paquete cotizador ──
from cotizador import (
    create_app, REPORTLAB_AVAILABLE, WEASYPRINT_AVAILABLE,
    safe_float, safe_int, validate_material_data,
    wrap_description_text, generar_pdf_reportlab
)

# ── Imports estándar usados por las rutas ──
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import io
import datetime
import atexit
import os
import json
import csv
import logging
import base64
import uuid
from pathlib import Path
from logging.handlers import RotatingFileHandler
import copy
from dotenv import load_dotenv
    
# Crear instancia de Render Keepalive (solo en producción)
try:
    from render_keepalive import init_keepalive, get_keepalive_instance

    # Inicializar keepalive - se activa automáticamente solo en Render
    keepalive = init_keepalive()
    print("Render Keepalive inicializado exitosamente")

    # Mostrar estadísticas si está activo
    if keepalive.is_running:
        stats = keepalive.get_stats()
        print(f"Keepalive activo - {stats['schedule']}")
    else:
        print("Keepalive en standby - Solo se activa en producción (Render)")

except Exception as e:
    print(f"Error inicializando Render Keepalive: {e}")
    keepalive = None

# ===========================================
# FUNCIONES AUXILIARES PARA CONVERSIÓN ROBUSTA
# ===========================================

def safe_float(value, default=0.0):
    """
    Convierte un valor a float de forma robusta, manejando strings, 
    comas decimales europeas, y valores nulos.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla
    
    Returns:
        float: Valor convertido o default
    """
    if value is None:
        return default
    
    # Si ya es un número, devolverlo
    if isinstance(value, (int, float)):
        return float(value)
    
    # Convertir a string para procesamiento
    try:
        str_value = str(value).strip()
        
        # Manejar valores vacíos
        if not str_value or str_value.lower() in ['', 'none', 'null', 'n/a']:
            return default
        
        # Reemplazar comas por puntos (formato europeo vs americano)
        # Pero solo si hay una sola coma y está seguida de 1-3 dígitos
        if ',' in str_value:
            parts = str_value.split(',')
            if len(parts) == 2 and len(parts[1]) <= 3 and parts[1].isdigit():
                # Es formato europeo: 123,45 -> 123.45
                str_value = f"{parts[0]}.{parts[1]}"
            else:
                # Múltiples comas, probablemente separadores de miles: 1,234,567
                str_value = str_value.replace(',', '')
        
        # Remover caracteres no numéricos excepto punto y signo menos
        cleaned = ''
        for char in str_value:
            if char.isdigit() or char in ['.', '-']:
                cleaned += char
        
        if not cleaned or cleaned == '-':
            return default
        
        result = float(cleaned)
        
        # Validar que el resultado es razonable
        if abs(result) > 1e10:  # Muy grande
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
    Valida y limpia los datos de un material, asegurando tipos correctos
    
    Args:
        material: Diccionario con datos del material
        item_index: Índice del item (para logging)
        material_index: Índice del material (para logging)
    
    Returns:
        dict: Material validado y limpio
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
    
    # Obtener descripción
    descripcion = material.get('descripcion') or material.get('material', 'Sin descripción')
    
    # Convertir valores numéricos con validación
    peso = safe_float(material.get('peso'), 1.0)
    cantidad = safe_float(material.get('cantidad'), 0.0)
    precio = safe_float(material.get('precio'), 0.0)
    
    # Validaciones específicas - CONSERVAR VALORES ORIGINALES EN REVISIONES
    if peso < 0:
        peso = 0.0  # Solo corregir valores negativos, no cambiar valores válidos
        
    if cantidad < 0:
        print(f"[VALIDATE] Cantidad negativa detectada: {cantidad}, corrigiendo a 0")
        cantidad = 0.0
        
    if precio < 0:
        print(f"[VALIDATE] Precio negativo detectado: {precio}, corrigiendo a 0")
        precio = 0.0
    
    # Calcular subtotal
    subtotal = round(peso * cantidad * precio, 2)
    
    # Log de conversión para debugging
    print(f"[VALIDATE] Item {item_index}, Material {material_index}: {descripcion}")
    print(f"   Peso: {material.get('peso')} -> {peso}")
    print(f"   Cantidad: {material.get('cantidad')} -> {cantidad}")
    print(f"   Precio: {material.get('precio')} -> {precio}")
    print(f"   Subtotal calculado: {subtotal}")
    
    return {
        'descripcion': descripcion,
        'peso': peso,
        'cantidad': cantidad,
        'precio': precio,
        'subtotal': subtotal
    }

# ===========================================
# CARGA DE MATERIALES DESDE CSV
# ===========================================

# Cargar lista de materiales desde CSV
def cargar_materiales_csv():
    """Carga la lista de materiales desde el archivo CSV con manejo robusto para producción"""
    materiales = []
    
    # Detectar entorno
    es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
    print(f"[MATERIALES] Entorno Render detectado: {bool(es_render)}")
    print(f"[MATERIALES] Directorio actual: {os.getcwd()}")
    print(f"[MATERIALES] __file__ path: {__file__}")
    
    try:
        # Intentar múltiples rutas posibles
        rutas_posibles = [
            os.path.join(os.path.dirname(__file__), 'Lista de materiales.csv'),
            os.path.join(os.getcwd(), 'Lista de materiales.csv'),
            './Lista de materiales.csv',
            'Lista de materiales.csv'
        ]
        
        archivo_encontrado = None
        for ruta_csv in rutas_posibles:
            print(f"[MATERIALES] Intentando cargar CSV desde: {ruta_csv}")
            if os.path.exists(ruta_csv):
                archivo_encontrado = ruta_csv
                print(f"[MATERIALES] Archivo CSV encontrado en: {ruta_csv}")
                break
            else:
                print(f"[MATERIALES] No encontrado en: {ruta_csv}")
        
        if not archivo_encontrado:
            raise FileNotFoundError("No se encontró el archivo 'Lista de materiales.csv' en ninguna ubicación")
        
        # Cargar el CSV
        print(f"[MATERIALES] Cargando CSV desde: {archivo_encontrado}")
        with open(archivo_encontrado, 'r', encoding='utf-8-sig') as archivo:
            contenido = archivo.read()
            print(f"[MATERIALES] Tamaño del archivo: {len(contenido)} caracteres")
            print(f"[MATERIALES] Primeras 200 caracteres: {contenido[:200]}")
            
            # Resetear puntero del archivo
            archivo.seek(0)
            reader = csv.DictReader(archivo)
            
            # Verificar headers
            headers = reader.fieldnames
            print(f"[MATERIALES] Headers encontrados: {headers}")
            
            for i, fila in enumerate(reader):
                try:
                    # Limpiar los headers que pueden tener espacios
                    headers_limpios = {k.strip() if k else f'col_{i}': v for k, v in fila.items()}
                    
                    # Buscar columnas por diferentes nombres posibles
                    descripcion = (
                        headers_limpios.get('Tipo de material') or
                        headers_limpios.get('tipo_material') or 
                        headers_limpios.get('material') or
                        headers_limpios.get('descripcion') or
                        f'Material {i+1}'
                    )
                    
                    peso_str = (
                        headers_limpios.get('Peso') or
                        headers_limpios.get('peso') or
                        headers_limpios.get('weight') or
                        '1.0'
                    )
                    
                    uom = (
                        headers_limpios.get('Ref de Peso') or
                        headers_limpios.get('uom') or
                        headers_limpios.get('unidad') or
                        'kg/m2'
                    )
                    
                    # Convertir peso manejando errores
                    try:
                        peso = float(str(peso_str).replace(',', '.'))
                    except (ValueError, TypeError):
                        peso = 1.0
                    
                    material = {
                        'descripcion': str(descripcion).strip(),
                        'peso': peso,
                        'uom': str(uom).strip()
                    }
                    materiales.append(material)
                    
                except Exception as fila_error:
                    print(f"[MATERIALES] Error procesando fila {i+1}: {fila_error}")
                    continue
                    
        print(f"[MATERIALES] Cargados {len(materiales)} materiales desde CSV")
        
        # Mostrar algunos ejemplos
        if materiales:
            print(f"[MATERIALES] Ejemplos cargados:")
            for i, mat in enumerate(materiales[:3]):
                print(f"  {i+1}. {mat['descripcion']} - {mat['peso']} {mat['uom']}")
        
    except Exception as e:
        print(f"[MATERIALES] Error cargando materiales: {e}")
        print(f"[MATERIALES] Tipo de error: {type(e).__name__}")
        
        # Lista archivos del directorio para debug
        try:
            archivos = os.listdir(os.path.dirname(__file__) or '.')
            print(f"[MATERIALES] Archivos en directorio: {archivos}")
        except:
            pass
        
        # Materiales por defecto si falla la carga
        materiales = [
            {'descripcion': 'Acero estructural', 'peso': 7850.0, 'uom': 'kg/m3'},
            {'descripcion': 'Concreto armado', 'peso': 2400.0, 'uom': 'kg/m3'},
            {'descripcion': 'Lamina galvanizada', 'peso': 7.85, 'uom': 'kg/m2'},
            {'descripcion': 'Perfil IPR', 'peso': 1.0, 'uom': 'kg/ml'},
            {'descripcion': 'Tubo estructural', 'peso': 1.0, 'uom': 'kg/ml'},
            {'descripcion': 'Material personalizado', 'peso': 1.0, 'uom': 'Especificar'}
        ]
        print(f"[MATERIALES] Usando {len(materiales)} materiales por defecto")
    
    return materiales

# Cargar materiales al iniciar la aplicación

def wrap_description_text(text, max_chars_per_line=35):
    """Utility function to wrap long description text for PDF cells"""
    if not text or len(text) <= max_chars_per_line:
        return text

    # Split text into words
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        # If adding this word would exceed the limit, start a new line
        if len(current_line + " " + word) > max_chars_per_line and current_line:
            lines.append(current_line)
            current_line = word
        else:
            if current_line:
                current_line += " " + word
            else:
                current_line = word

    # Add the last line if it has content
    if current_line:
        lines.append(current_line)

    # Join lines with line breaks
    return "<br/>".join(lines)


import re as _re
from html import unescape as _html_unescape

def html_to_reportlab_markup(html_str):
    """Convert contenteditable HTML to ReportLab Paragraph XML markup."""
    if not html_str:
        return ''
    if '<' not in html_str:
        return wrap_description_text(html_str)

    def replace_ul(m):
        lis = _re.findall(r'<li[^>]*>(.*?)</li>', m.group(0), _re.DOTALL | _re.IGNORECASE)
        rows = []
        for li in lis:
            text = _re.sub(r'<[^>]+>', '', li).strip()
            if text:
                rows.append(f'• {text}')
        return '<br/>'.join(rows)

    result = _re.sub(r'<ul[^>]*>.*?</ul>', replace_ul, html_str, flags=_re.DOTALL | _re.IGNORECASE)
    result = _re.sub(r'<strong[^>]*>', '<b>', result, flags=_re.IGNORECASE)
    result = _re.sub(r'</strong>', '</b>', result, flags=_re.IGNORECASE)
    result = _re.sub(r'<em[^>]*>', '<i>', result, flags=_re.IGNORECASE)
    result = _re.sub(r'</em>', '</i>', result, flags=_re.IGNORECASE)
    result = _re.sub(r'<br\s*/?>', '<br/>', result, flags=_re.IGNORECASE)
    # Convert <div> blocks to line breaks (Chrome wraps paragraphs in divs)
    result = _re.sub(r'<div[^>]*>', '<br/>', result, flags=_re.IGNORECASE)
    result = _re.sub(r'</div>', '', result, flags=_re.IGNORECASE)
    result = _re.sub(r'</(p)>', '<br/>', result, flags=_re.IGNORECASE)
    # Remove remaining tags except b, i, u, br
    result = _re.sub(r'<(?!/?(?:b|i|u|br)(?:\s|/?>))[^>]+>', '', result, flags=_re.IGNORECASE)
    result = _html_unescape(result)
    result = _re.sub(r'(<br/>)+', '<br/>', result)
    # Strip leading/trailing <br/> as substrings (not char-by-char)
    result = result.strip()
    result = _re.sub(r'^(<br/>)+', '', result)
    result = _re.sub(r'(<br/>)+$', '', result)
    result = result.strip()
    return result or ''


# ── Crear app vía factory ──
app = create_app()
db_manager = app.extensions['db_manager']
pdf_manager = app.extensions['pdf_manager']
sync_scheduler = app.extensions.get('sync_scheduler')
LISTA_MATERIALES = app.config.get('LISTA_MATERIALES', [])

def verificar_revision_mas_reciente(numero_cotizacion, db_manager):
    """
    Verifica si una cotización es la revisión más reciente
    Retorna dict con:
    - es_mas_reciente: bool
    - revision_actual: int
    - revision_maxima: int
    - numero_ultima_revision: str
    """
    try:
        print(f"\n[VERIFICAR_REVISION] ========== INICIO VERIFICACIÓN ==========")
        print(f"[VERIFICAR_REVISION] Número cotización a verificar: {numero_cotizacion}")

        # Extraer el número base y revisión actual
        # Formato típico: CLIENTE-CWS-VENDOR-###-R#-PROYECTO
        partes = numero_cotizacion.split('-')
        print(f"[VERIFICAR_REVISION] Partes del número: {partes}")

        revision_actual = 1
        indice_revision = -1

        for i, parte in enumerate(partes):
            if parte.startswith('R') and len(parte) > 1:
                try:
                    revision_actual = int(parte[1:])
                    indice_revision = i
                    print(f"[VERIFICAR_REVISION] Encontrada revisión R{revision_actual} en índice {i}")
                    break
                except ValueError:
                    print(f"[VERIFICAR_REVISION] Parte '{parte}' parece revisión pero no es número válido")
                    continue

        if indice_revision == -1:
            print(f"[VERIFICAR_REVISION] ⚠️ No se encontró revisión en formato R# - Asumiendo es la más reciente")
            return {
                'es_mas_reciente': True,
                'revision_actual': 1,
                'revision_maxima': 1,
                'numero_ultima_revision': numero_cotizacion
            }

        # Construir patrón base (sin R#)
        # Ejemplo: BMW-CWS-RAE-001-R2-PROYECTO -> BMW-CWS-RAE-001-PROYECTO
        patron_base = '-'.join(partes[:indice_revision] + partes[indice_revision+1:])

        # También crear versión simplificada para búsqueda más amplia
        # Buscar por las primeras 4 partes (CLIENTE-CWS-VENDOR-###)
        patron_busqueda = '-'.join(partes[:min(4, len(partes))])

        print(f"[VERIFICAR_REVISION] Patrón base: {patron_base}")
        print(f"[VERIFICAR_REVISION] Patrón búsqueda: {patron_busqueda}")
        print(f"[VERIFICAR_REVISION] Revisión actual: R{revision_actual}")

        # Buscar todas las cotizaciones relacionadas usando el patrón de búsqueda
        print(f"[VERIFICAR_REVISION] Buscando cotizaciones con patrón: '{patron_busqueda}'")
        resultado = db_manager.buscar_cotizaciones(patron_busqueda, page=1, per_page=100)

        # IMPORTANTE: La API puede retornar 'items' o 'resultados' dependiendo del manager
        items_encontrados = resultado.get('items') or resultado.get('resultados') or []

        if not items_encontrados:
            print(f"[VERIFICAR_REVISION] ⚠️ No se encontraron items en la búsqueda")
            print(f"[VERIFICAR_REVISION] Keys en resultado: {resultado.keys()}")
            print(f"[VERIFICAR_REVISION] Resultado completo: {resultado}")
            return {
                'es_mas_reciente': True,
                'revision_actual': revision_actual,
                'revision_maxima': revision_actual,
                'numero_ultima_revision': numero_cotizacion
            }

        print(f"[VERIFICAR_REVISION] Se encontraron {len(items_encontrados)} cotizaciones")

        # Buscar revisión máxima en las cotizaciones encontradas
        revision_maxima = revision_actual
        numero_ultima_revision = numero_cotizacion
        revisiones_encontradas = []

        for item in items_encontrados:
            num_cotiz = item.get('numeroCotizacion', '')
            print(f"[VERIFICAR_REVISION] Analizando cotización: {num_cotiz}")

            # Verificar que pertenezca a la misma familia (mismo patrón base)
            # Debe contener las partes principales
            if patron_busqueda not in num_cotiz:
                print(f"[VERIFICAR_REVISION]   → Descartada (patrón no coincide)")
                continue

            # Extraer revisión de esta cotización
            partes_item = num_cotiz.split('-')
            for parte in partes_item:
                if parte.startswith('R') and len(parte) > 1:
                    try:
                        rev = int(parte[1:])

                        # Extraer justificación de actualización
                        datos_generales = item.get('datosGenerales', {})
                        justificacion = datos_generales.get('actualizacionRevision', '')

                        # Extraer fecha si está disponible
                        fecha_creacion = item.get('fechaCreacion', '')
                        if not fecha_creacion:
                            fecha_creacion = datos_generales.get('fecha', '')

                        revisiones_encontradas.append({
                            'numero': num_cotiz,
                            'revision': rev,
                            'justificacion': justificacion,
                            'fecha': fecha_creacion
                        })
                        print(f"[VERIFICAR_REVISION]   → Revisión encontrada: R{rev}")
                        if justificacion:
                            print(f"[VERIFICAR_REVISION]   → Justificación: {justificacion[:50]}...")

                        if rev > revision_maxima:
                            revision_maxima = rev
                            numero_ultima_revision = num_cotiz
                            print(f"[VERIFICAR_REVISION]   → ¡Nueva revisión máxima! R{rev}")
                        break
                    except ValueError:
                        continue

        # Ordenar revisiones de más reciente a más antigua
        revisiones_encontradas.sort(key=lambda x: x['revision'], reverse=True)

        es_mas_reciente = (revision_actual >= revision_maxima)

        print(f"\n[VERIFICAR_REVISION] ========== RESULTADO ==========")
        print(f"[VERIFICAR_REVISION] Revisiones encontradas: {len(revisiones_encontradas)}")
        print(f"[VERIFICAR_REVISION] Revisión actual: R{revision_actual}")
        print(f"[VERIFICAR_REVISION] Revisión máxima: R{revision_maxima}")
        print(f"[VERIFICAR_REVISION] ¿Es la más reciente?: {es_mas_reciente}")
        print(f"[VERIFICAR_REVISION] Última revisión: {numero_ultima_revision}")
        print(f"[VERIFICAR_REVISION] ========== FIN VERIFICACIÓN ==========\n")

        return {
            'es_mas_reciente': es_mas_reciente,
            'revision_actual': revision_actual,
            'revision_maxima': revision_maxima,
            'numero_ultima_revision': numero_ultima_revision,
            'historial_revisiones': revisiones_encontradas
        }

    except Exception as e:
        print(f"[VERIFICAR_REVISION] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        # En caso de error, permitir la revisión para no bloquear el sistema
        print(f"[VERIFICAR_REVISION] Por seguridad, permitiendo la revisión")
        return {
            'es_mas_reciente': True,
            'revision_actual': 1,
            'revision_maxima': 1,
            'numero_ultima_revision': numero_cotizacion
        }

def _safe_for_json(obj):
    """Convierte recursivamente objetos no JSON-serializables (Decimal, datetime, etc.)
    a tipos nativos de Python que Jinja2's tojson y json.dumps pueden serializar."""
    import math
    from decimal import Decimal
    import datetime as dt
    if isinstance(obj, dict):
        return {k: _safe_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_for_json(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, bytes):
        return obj.hex()
    return obj

def preparar_datos_nueva_revision(cotizacion_original):
    """Prepara los datos de una cotización para crear una nueva revisión"""
    try:
        import copy

        # Copiar datos originales
        datos = copy.deepcopy(cotizacion_original)
        
        # Incrementar revisión
        revision_actual = datos.get('datosGenerales', {}).get('revision', '1')
        try:
            nueva_revision = str(int(revision_actual) + 1)
        except (ValueError, TypeError):
            nueva_revision = '2'
        
        # Actualizar datos generales
        if 'datosGenerales' not in datos:
            datos['datosGenerales'] = {}

        datos['datosGenerales']['revision'] = nueva_revision
        datos['datosGenerales']['fecha'] = datetime.datetime.now().strftime('%Y-%m-%d')

        # Preservar texto introductorio de la revisión anterior (si existe)
        texto_anterior = datos.get('textoIntroductorio') or datos.get('datosGenerales', {}).get('textoIntroductorio', '')
        if texto_anterior:
            datos['datosGenerales']['textoIntroductorio'] = texto_anterior
        
        # Generar nuevo número de cotización con revisión usando el sistema automático
        numero_original = datos['datosGenerales'].get('numeroCotizacion', '')
        print(f"[REVISION] Número original: '{numero_original}' -> Nueva revisión: {nueva_revision}")
        
        if numero_original:
            # Usar la función del DatabaseManager para generar el número de revisión
            nuevo_numero = db_manager.generar_numero_revision(numero_original, nueva_revision)
            
            # FIX ISSUE #1: Poner el número en AMBOS lugares para asegurar que se use
            datos['datosGenerales']['numeroCotizacion'] = nuevo_numero
            datos['numeroCotizacion'] = nuevo_numero  # NIVEL RAÍZ también
            
            print(f"[REVISION] Número actualizado: '{nuevo_numero}'")
            print(f"[REVISION] FIX ISSUE #1: Número puesto en datosGenerales Y nivel raíz")
        else:
            # Si no hay número original, generar uno nuevo completo
            cliente = datos['datosGenerales'].get('cliente', '')
            vendedor = datos['datosGenerales'].get('vendedor', '')
            proyecto = datos['datosGenerales'].get('proyecto', '')
            print(f"[REVISION] Generando número nuevo para: Cliente='{cliente}', Vendedor='{vendedor}', Proyecto='{proyecto}'")
            nuevo_numero = db_manager.generar_numero_cotizacion(cliente, vendedor, proyecto, int(nueva_revision))
            datos['datosGenerales']['numeroCotizacion'] = nuevo_numero
            print(f"[REVISION] Número generado: '{nuevo_numero}'")
        
        # NUEVO: Recalcular subtotales de materiales para asegurar consistencia
        if 'items' in datos:
            print("[REVISION] Recalculando subtotales de materiales...")
            for i, item in enumerate(datos['items']):
                print(f"  Procesando item {i+1}: {item.get('descripcion', 'Sin descripción')}")
                
                if 'materiales' in item and isinstance(item['materiales'], list):
                    for j, material in enumerate(item['materiales']):
                        # Validar que el material tenga los campos necesarios
                        if not material or not isinstance(material, dict):
                            print(f"    Material {j+1}: Estructura inválida, saltando")
                            continue
                        
                        # MEJORADO: Usar validación robusta de datos de material
                        material_validado = validate_material_data(material, i, j)
                        
                        # Actualizar el material con los datos validados
                        material.update(material_validado)
                        
                        print(f"    Material {j+1} validado y recalculado: {material_validado['descripcion']} = {material_validado['peso']} * {material_validado['cantidad']} * {material_validado['precio']} = {material_validado['subtotal']}")
                
                # MEJORADO: Recalcular total del item con conversión robusta
                try:
                    materiales_list = item.get('materiales', [])
                    if isinstance(materiales_list, list):
                        total_materiales = sum(safe_float(m.get('subtotal', 0)) for m in materiales_list if isinstance(m, dict))
                    else:
                        total_materiales = 0.0

                    # Sumar correctamente los otros materiales (campo 'otrosMateriales', no 'otros')
                    otros_materiales_list = item.get('otrosMateriales', [])
                    if isinstance(otros_materiales_list, list):
                        total_otros = sum(safe_float(m.get('subtotal', 0)) for m in otros_materiales_list if isinstance(m, dict))
                    else:
                        total_otros = 0.0

                    transporte  = safe_float(item.get('transporte', 0))
                    instalacion = safe_float(item.get('instalacion', 0))
                    seguridad   = safe_float(item.get('seguridad', 0))
                    descuento   = safe_float(item.get('descuento', 0))
                    cant_raw    = safe_float(item.get('cantidad', 1))
                    cantidad    = cant_raw if cant_raw > 0 else 1

                    subtotal_base     = total_materiales + total_otros + transporte + instalacion
                    aumento_seguridad = subtotal_base * (seguridad / 100)
                    subtotal_con_seg  = subtotal_base + aumento_seguridad
                    reduccion_desc    = subtotal_con_seg * (descuento / 100)
                    costo_unidad      = subtotal_con_seg - reduccion_desc
                    total_item        = costo_unidad * cantidad

                    item['costoUnidad'] = round(costo_unidad, 2)
                    item['total']       = round(total_item, 2)

                    print(f"  [RECALC] Item total: {item.get('descripcion', 'Sin desc')} = "
                          f"(mats={total_materiales} + otros={total_otros} + transp={transporte} + inst={instalacion}) "
                          f"* (1+seg{seguridad}%) * (1-desc{descuento}%) * cant{cantidad} = {total_item}")
                except Exception as e:
                    print(f"  [ERROR] Error calculando total del item: {e}")
                    item['total'] = 0.0
        
        # Limpiar campos que no deben copiarse
        campos_a_limpiar = ['_id', 'fechaCreacion', 'timestamp', 'version']
        for campo in campos_a_limpiar:
            datos.pop(campo, None)
        
        # Agregar campo de actualización
        datos['datosGenerales']['actualizacionRevision'] = f"Revisión {nueva_revision} basada en cotización original"
        
        print(f"[OK] Datos preparados para nueva revisión: {nuevo_numero}")
        return _safe_for_json(datos)
        
    except Exception as e:
        print(f"[ERROR] Error preparando nueva revisión: {e}")
        import traceback
        traceback.print_exc()
        return None

# Registrar cierre de conexión al salir
atexit.register(db_manager.cerrar_conexion)

# ============================================
# PROCESAMIENTO DE IMAGEN DE REFERENCIA
# ============================================

def procesar_imagen_referencia(datos, numero_cotizacion):
    """
    Procesa una imagen de referencia enviada como base64 desde el formulario.

    Extrae, valida, guarda en Supabase Storage (o local como fallback) y
    retorna un dict con {url, nombre, tamano_bytes, mime_type} para almacenar en datos_generales.

    Args:
        datos: Dict completo de la cotizacion recibido del formulario
        numero_cotizacion: Numero de cotizacion para nombrar el archivo

    Returns:
        dict con {url, nombre, tamano_bytes, mime_type} o None si no hay imagen o error
    """
    img_data = datos.get('imagenReferencia')
    if not img_data:
        return None

    # Si tiene flag conservar, retornar referencia existente sin cambios
    if img_data.get('conservar'):
        datos_generales = datos.get('datosGenerales', {})
        existente = datos_generales.get('imagenReferencia')
        if existente:
            print(f"[IMAGEN] Conservando imagen existente: {existente.get('url', 'sin URL')}")
            return existente
        return None

    base64_str = img_data.get('base64', '')
    if not base64_str:
        print("[IMAGEN] No se recibio base64 — ignorando")
        return None

    # Validar y decodificar base64
    try:
        # Formato esperado: "data:image/jpeg;base64,/9j/4AAQ..."
        if ',' in base64_str:
            header, encoded = base64_str.split(',', 1)
        else:
            encoded = base64_str

        image_bytes = base64.b64decode(encoded)
    except Exception as e:
        print(f"[IMAGEN] Error decodificando base64: {e}")
        return None

    # Validar tamano (max 5 MB)
    max_size = 5 * 1024 * 1024
    if len(image_bytes) > max_size:
        print(f"[IMAGEN] Imagen demasiado grande: {len(image_bytes)} bytes (max {max_size})")
        return None

    # Validar tipo MIME
    mime_type = img_data.get('mime_type', 'image/jpeg')
    allowed_types = ['image/jpeg', 'image/png']
    if mime_type not in allowed_types:
        print(f"[IMAGEN] Tipo MIME no soportado: {mime_type}")
        return None

    # Determinar extension del archivo
    extension_map = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/jpg': '.jpg'
    }
    extension = extension_map.get(mime_type, '.jpg')

    # Generar nombre de archivo unico
    nombre_archivo = f"REF_{numero_cotizacion}_{uuid.uuid4().hex[:8]}{extension}"
    storage_path = f"imagenes_referencia/{nombre_archivo}"

    url = None

    # Intentar guardar en Supabase Storage
    try:
        from supabase_storage_manager import SupabaseStorageManager
        storage_manager = SupabaseStorageManager()

        if storage_manager and storage_manager.is_available():
            resultado = storage_manager.subir_archivo(
                file_bytes=image_bytes,
                storage_path=storage_path,
                content_type=mime_type
            )
            if not resultado.get('error'):
                url = resultado.get('url', '')
                if url and url.endswith('?'):
                    url = url[:-1]
                print(f"[IMAGEN] Subida exitosa a Supabase Storage: {url}")
    except ImportError:
        print("[IMAGEN] SupabaseStorageManager no disponible — guardando localmente")
    except Exception as e:
        print(f"[IMAGEN] Error subiendo a Supabase Storage: {e}")

    # Fallback: guardar localmente
    if not url:
        try:
            local_images_dir = Path("static/imagenes_referencia")
            local_images_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_images_dir / nombre_archivo
            local_path.write_bytes(image_bytes)
            url = f"static/imagenes_referencia/{nombre_archivo}"
            print(f"[IMAGEN] Guardada localmente: {local_path}")
        except Exception as e:
            print(f"[IMAGEN] Error en fallback local: {e}")
            return None

    print(f"[IMAGEN] Procesada: {url}")
    return {
        "url": url,
        "nombre": img_data.get('nombre', nombre_archivo),
        "tamano_bytes": len(image_bytes),
        "mime_type": mime_type
    }

# ============================================
# FILTROS PARA TEMPLATES
# ============================================

@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    """Convierte timestamp a fecha legible"""
    try:
        if isinstance(timestamp, str):
            # Si es string ISO, convertir directamente
            return datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
        elif isinstance(timestamp, (int, float)):
            # Si es timestamp numérico
            return datetime.datetime.fromtimestamp(timestamp / 1000).strftime('%d/%m/%Y %H:%M')
        else:
            return 'N/A'
    except:
        return 'N/A'

# ============================================
# AUTENTICACIÓN Y SESSION MANAGEMENT
# ============================================

from functools import wraps

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'vendedor' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    """Página de login"""
    if request.method == "POST":
        vendedor = request.form.get('vendedor')
        if vendedor:
            session['vendedor'] = vendedor
            print(f"Usuario autenticado: {vendedor}")
            return redirect(url_for('home'))
        else:
            return render_template("login.html", error="Por favor selecciona tu nombre")

    # Si ya está autenticado, redirigir al home
    if 'vendedor' in session:
        return redirect(url_for('home'))

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Cerrar sesión"""
    vendedor = session.get('vendedor', 'Usuario')
    session.pop('vendedor', None)
    print(f"Usuario cerró sesión: {vendedor}")
    return redirect(url_for('login'))

# ============================================
# HEALTH CHECK ENDPOINT (para Render Keepalive)
# ============================================

@app.route("/health", methods=["GET"])
def health_check():
    """
    Endpoint de health check para mantener Render activo.

    No requiere autenticación para permitir pings automáticos.
    Devuelve estado del sistema y métricas básicas.
    """
    try:
        # Obtener estadísticas básicas
        stats = db_manager.obtener_estadisticas()

        # Construir respuesta con estado del sistema
        response = {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': {
                'mode': 'offline' if db_manager.modo_offline else 'online',
                'type': 'JSON local' if db_manager.modo_offline else 'Supabase PostgreSQL',
                'total_quotations': stats.get('total', 0)
            },
            'services': {
                'pdf_generation': REPORTLAB_AVAILABLE or WEASYPRINT_AVAILABLE,
                'pdf_manager': pdf_manager is not None
            }
        }

        return jsonify(response), 200

    except Exception as e:
        # Incluso si hay error, devolver 200 para mantener Render despierto
        return jsonify({
            'status': 'degraded',
            'timestamp': datetime.datetime.now().isoformat(),
            'error': str(e)
        }), 200

@app.route("/admin/keepalive/stats", methods=["GET"])
@login_required
def keepalive_stats():
    """
    Endpoint administrativo para ver estadísticas del keepalive.

    Requiere autenticación. Devuelve información detallada del scheduler.
    """
    try:
        from render_keepalive import get_keepalive_instance

        keepalive = get_keepalive_instance()
        stats = keepalive.get_stats()

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'keepalive_available': False
        }), 500

# ============================================
# RUTAS PRINCIPALES
# ============================================

@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    """Página principal - Vista de tabla Excel con todas las cotizaciones paginadas"""
    if request.method == "POST":
        try:
            datos = request.get_json()
            print("Nueva cotizacion recibida")

            # Guardar TODOS los datos usando el DatabaseManager
            resultado = db_manager.guardar_cotizacion(datos)

            if resultado["success"]:
                return jsonify({
                    "mensaje": "Cotización guardada correctamente",
                    "id": resultado["id"],
                    "numeroCotizacion": resultado["numeroCotizacion"],
                    "campos_guardados": resultado["campos_guardados"]
                })
            else:
                # ❌ LOG CRÍTICO: Error en guardado
                error_msg = resultado.get("error", "Error desconocido")
                logging.error(f"ERROR_GUARDADO: {error_msg}")

                # Log específico para diferentes tipos de error
                if resultado.get("tipo_error") == "fallo_silencioso":
                    critical_logger = logging.getLogger('FALLOS_CRITICOS')
                    critical_logger.error(f"FALLO_SILENCIOSO_CRÍTICO: {error_msg}")

                return jsonify({"error": error_msg}), 500

        except Exception as e:
            print(f"Error en ruta principal: {e}")
            return jsonify({"error": "Error del servidor"}), 500

    # GET: Mostrar tabla completa con paginación y filtros
    try:
        # PAGINACIÓN: Obtener página actual (default 1) y tamaño de página
        page = request.args.get('page', 1, type=int)
        page_size = 50  # 50 registros por página

        # BÚSQUEDA RÁPIDA: Obtener query general
        query_general = request.args.get('q', '').strip()

        # FILTROS: Obtener parámetros de filtro desde URL
        filtro_numero = request.args.get('numero', '').strip()
        filtro_cliente = request.args.get('cliente', '').strip()
        filtro_vendedor = request.args.get('vendedor', '').strip()
        filtro_proyecto = request.args.get('proyecto', '').strip()
        filtro_fecha_desde = request.args.get('fecha_desde', '').strip()
        filtro_fecha_hasta = request.args.get('fecha_hasta', '').strip()
        filtro_revision = request.args.get('revision', '').strip()
        filtro_moneda = request.args.get('moneda', '').strip()
        filtro_tipo = request.args.get('tipo', '').strip()

        print(f"[HOME] Obteniendo todas las cotizaciones (página {page})...")
        if query_general:
            print(f"[HOME] Búsqueda rápida: '{query_general}'")

        # Obtener todas las cotizaciones de la base de datos
        resultado_db = db_manager.buscar_cotizaciones("", 1, 10000)  # Query vacía = todas

        # Obtener todos los PDFs (incluye Google Drive antiguas)
        resultado_pdfs = pdf_manager.buscar_pdfs("", 1, 10000) if pdf_manager else {"resultados": []}

        cotizaciones = []
        numeros_vistos = set()  # Para evitar duplicados entre BD y PDFs

        if not resultado_db.get("error"):
            cotizaciones_raw = resultado_db.get("resultados", [])
            print(f"[HOME] Encontradas {len(cotizaciones_raw)} cotizaciones de BD")

            # Transformar datos para tabla compacta
            for idx, cot in enumerate(cotizaciones_raw):
                datos_gen = cot.get('datosGenerales', {})

                # EXTRACCIÓN ROBUSTA DE FECHA
                fecha = 'N/A'
                if isinstance(datos_gen, dict):
                    fecha = datos_gen.get('fecha') or datos_gen.get('Fecha')
                if not fecha or fecha == 'N/A':
                    fecha = cot.get('fecha') or cot.get('fechaCreacion') or cot.get('timestamp')
                    if fecha and isinstance(fecha, (int, float)):
                        from datetime import datetime
                        try:
                            fecha = datetime.fromtimestamp(fecha/1000 if fecha > 10000000000 else fecha).strftime('%Y-%m-%d')
                        except:
                            fecha = 'N/A'
                if not fecha:
                    fecha = 'N/A'

                # CÁLCULO DEL TOTAL
                total_calculado = 0.0
                items = cot.get('items', [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            if 'total' in item and item['total']:
                                total_calculado += safe_float(item.get('total', 0))
                            elif 'subtotal' in item and item['subtotal']:
                                total_calculado += safe_float(item.get('subtotal', 0))
                            elif 'precio_unitario' in item:
                                precio = safe_float(item.get('precio_unitario', 0))
                                cantidad = safe_float(item.get('cantidad', 1))
                                total_calculado += precio * cantidad

                # Obtener moneda
                condiciones = cot.get('condiciones', {})
                if not condiciones or not isinstance(condiciones, dict):
                    condiciones = datos_gen.get('condiciones', {})
                moneda = condiciones.get('moneda', 'MXN') if isinstance(condiciones, dict) else 'MXN'

                # EXTRACCIÓN DE REVISIÓN
                revision = None
                import re
                numero_cot = cot.get('numeroCotizacion', '')
                if numero_cot and isinstance(numero_cot, str):
                    match = re.search(r'-R(\d+)-', numero_cot)
                    if match:
                        revision = int(match.group(1))
                if not revision and 'revision' in cot:
                    try:
                        revision = int(cot.get('revision'))
                    except:
                        pass
                if not revision:
                    revision = 1

                numeros_vistos.add(numero_cot)

                cotizaciones.append({
                    "numero": numero_cot,
                    "cliente": datos_gen.get('cliente', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                    "vendedor": datos_gen.get('vendedor', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                    "proyecto": datos_gen.get('proyecto', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                    "fecha": fecha,
                    "revision": revision,
                    "total": total_calculado,
                    "moneda": moneda,
                    "_id": cot.get('_id', ''),
                    "tiene_desglose": True,
                    "es_antigua": False
                })
        else:
            print(f"[HOME] Error: {resultado_db.get('error')}")

        # AGREGAR COTIZACIONES ANTIGUAS DE GOOGLE DRIVE (que no están en BD)
        if not resultado_pdfs.get("error"):
            pdfs_antiguos = resultado_pdfs.get("resultados", [])
            print(f"[HOME] Encontrados {len(pdfs_antiguos)} PDFs totales")

            for pdf in pdfs_antiguos:
                numero_pdf = pdf.get('numero_cotizacion', 'N/A')

                # Solo agregar si no está ya en la lista (evitar duplicados)
                if numero_pdf not in numeros_vistos and numero_pdf != 'N/A':
                    # Extraer metadatos del nombre (formato: CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO)
                    import re
                    nombre_partes = numero_pdf.split('-')

                    cliente = nombre_partes[0] if len(nombre_partes) > 0 else 'N/A'
                    vendedor = nombre_partes[2] if len(nombre_partes) > 2 else 'N/A'
                    proyecto = '-'.join(nombre_partes[5:]) if len(nombre_partes) > 5 else 'N/A'

                    # Extraer revisión
                    match_revision = re.search(r'-R(\d+)-', numero_pdf)
                    revision = int(match_revision.group(1)) if match_revision else 1

                    # Fecha de modificación del archivo
                    fecha_pdf = pdf.get('fecha_creacion', pdf.get('fecha_modificacion', 'N/A'))

                    cotizaciones.append({
                        "numero": numero_pdf,
                        "cliente": cliente,
                        "vendedor": vendedor,
                        "proyecto": proyecto,
                        "fecha": fecha_pdf,
                        "revision": revision,
                        "total": 0,  # No hay datos de total en PDFs antiguos
                        "moneda": "N/A",
                        "_id": '',
                        "tiene_desglose": False,  # PDFs antiguos NO tienen desglose
                        "es_antigua": True  # Marcar como antigua
                    })

            print(f"[HOME] Total final: {len(cotizaciones)} cotizaciones (BD + antiguas)")

        # APLICAR BÚSQUEDA RÁPIDA (busca en todos los campos)
        if query_general:
            cotizaciones_busqueda = []
            query_lower = query_general.lower()
            for cot in cotizaciones:
                # Buscar en número, cliente, vendedor y proyecto
                if (query_lower in cot.get('numero', '').lower() or
                    query_lower in cot.get('cliente', '').lower() or
                    query_lower in cot.get('vendedor', '').lower() or
                    query_lower in cot.get('proyecto', '').lower()):
                    cotizaciones_busqueda.append(cot)

            cotizaciones = cotizaciones_busqueda
            print(f"[HOME] Después de búsqueda rápida: {len(cotizaciones)} cotizaciones")

        # APLICAR FILTROS AVANZADOS antes de paginación
        if any([filtro_numero, filtro_cliente, filtro_vendedor, filtro_proyecto,
                filtro_fecha_desde, filtro_fecha_hasta, filtro_revision, filtro_moneda, filtro_tipo]):

            cotizaciones_filtradas = []
            for cot in cotizaciones:
                cumple_filtros = True

                if filtro_numero and filtro_numero.lower() not in cot.get('numero', '').lower():
                    cumple_filtros = False
                if filtro_cliente and cumple_filtros and filtro_cliente.lower() not in cot.get('cliente', '').lower():
                    cumple_filtros = False
                if filtro_vendedor and cumple_filtros and filtro_vendedor.lower() not in cot.get('vendedor', '').lower():
                    cumple_filtros = False
                if filtro_proyecto and cumple_filtros and filtro_proyecto.lower() not in cot.get('proyecto', '').lower():
                    cumple_filtros = False

                if cumple_filtros:
                    cotizaciones_filtradas.append(cot)

            cotizaciones = cotizaciones_filtradas
            print(f"[HOME] Después de filtros avanzados: {len(cotizaciones)} cotizaciones")

        # APLICAR PAGINACIÓN
        total_cotizaciones = len(cotizaciones)
        total_pages = (total_cotizaciones + page_size - 1) // page_size

        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages

        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        cotizaciones_pagina = cotizaciones[start_index:end_index]

        print(f"[HOME] Mostrando {len(cotizaciones_pagina)} de {total_cotizaciones} (página {page}/{total_pages})")

        return render_template(
            "home.html",
            cotizaciones=cotizaciones_pagina,
            vendedor=session.get('vendedor'),
            page=page,
            total_pages=total_pages,
            total_cotizaciones=total_cotizaciones,
            page_size=page_size,
            # Filtros actuales para repoblar el formulario
            filtro_numero=filtro_numero,
            filtro_cliente=filtro_cliente,
            filtro_vendedor=filtro_vendedor,
            filtro_proyecto=filtro_proyecto,
            filtro_fecha_desde=filtro_fecha_desde,
            filtro_fecha_hasta=filtro_fecha_hasta,
            filtro_revision=filtro_revision,
            filtro_moneda=filtro_moneda,
            filtro_tipo=filtro_tipo
        )

    except Exception as e:
        print(f"[HOME] Error: {e}")
        import traceback
        traceback.print_exc()
        return render_template("home.html",
                             vendedor=session.get('vendedor', ''),
                             cotizaciones=[],
                             page=1,
                             total_pages=0,
                             total_cotizaciones=0,
                             page_size=50,
                             error=str(e))

@app.route("/formulario", methods=["GET", "POST"])
@login_required
def formulario():
    """Formulario de cotización"""
    if request.method == "POST":
        try:
            datos = request.get_json()
            print("[FORM] FORMULARIO: Datos del formulario recibidos")
            print(f"[FORM] FORMULARIO: Cliente='{datos.get('datosGenerales', {}).get('cliente', 'N/A')}' | Items={len(datos.get('items', []))}")
            
            # DEBUG ISSUE #1: Mostrar exactamente qué números llegan
            print(f"[ISSUE1_DEBUG] ======= DEBUGGING ISSUE #1 =======")
            print(f"[ISSUE1_DEBUG] datos['numeroCotizacion']: '{datos.get('numeroCotizacion', 'NO_ENCONTRADO')}'")
            print(f"[ISSUE1_DEBUG] datos['numeroCotizacionHidden']: '{datos.get('numeroCotizacionHidden', 'NO_ENCONTRADO')}'")
            datos_generales = datos.get('datosGenerales', {})
            print(f"[ISSUE1_DEBUG] datosGenerales['numeroCotizacion']: '{datos_generales.get('numeroCotizacion', 'NO_ENCONTRADO')}'")
            print(f"[ISSUE1_DEBUG] datosGenerales['revision']: '{datos_generales.get('revision', 'NO_ENCONTRADO')}'")
            print(f"[ISSUE1_DEBUG] ======= FIN DEBUG ISSUE #1 =======")
            
            # DEBUG: Diagnóstico completo de condiciones recibidas
            print(f"[FORM_DEBUG] ======= DIAGNÓSTICO FORMULARIO =======")
            condiciones_recibidas = datos.get('condiciones', {})
            print(f"[FORM_DEBUG] CONDICIONES COMPLETAS: {condiciones_recibidas}")
            print(f"[FORM_DEBUG] MONEDA RECIBIDA: '{condiciones_recibidas.get('moneda', 'NO_ENCONTRADO')}'")
            print(f"[FORM_DEBUG] TIPO_CAMBIO RECIBIDO: '{condiciones_recibidas.get('tipoCambio', 'NO_ENCONTRADO')}'")
            print(f"[FORM_DEBUG] TIEMPO_ENTREGA: '{condiciones_recibidas.get('tiempoEntrega', 'NO_ENCONTRADO')}'")
            print(f"[FORM_DEBUG] ENTREGAR_EN: '{condiciones_recibidas.get('entregaEn', 'NO_ENCONTRADO')}'")
            print(f"[FORM_DEBUG] CONDICIONES_PAGO: '{condiciones_recibidas.get('condicionesPago', 'NO_ENCONTRADO')}'")
            print(f"[FORM_DEBUG] COMENTARIOS_ADICIONALES: '{condiciones_recibidas.get('comentariosAdicionales', 'NO_ENCONTRADO')}'")
            print(f"[FORM_DEBUG] ======= FIN DIAGNÓSTICO FORMULARIO =======")
            
            # VALIDACIÓN MEJORADA PARA REVISIONES con logging detallado
            datos_generales = datos.get('datosGenerales', {})
            revision = safe_int(datos_generales.get('revision', 1))
            numero_cotizacion = datos_generales.get('numeroCotizacion', 'N/A')
            
            print(f"[REVISION_DEBUG] ======= ANÁLISIS DE REVISIÓN =======")
            print(f"[REVISION_DEBUG] Número cotización: '{numero_cotizacion}'")
            print(f"[REVISION_DEBUG] Revisión detectada: {revision}")
            print(f"[REVISION_DEBUG] Es revisión (>=2): {revision >= 2}")
            
            if revision >= 2:
                actualizacion_revision = datos_generales.get('actualizacionRevision', '').strip()
                print(f"[REVISION_DEBUG] Justificación presente: {bool(actualizacion_revision)}")
                print(f"[REVISION_DEBUG] Longitud justificación: {len(actualizacion_revision)}")
                print(f"[REVISION_DEBUG] Justificación válida (>=10 chars): {len(actualizacion_revision) >= 10}")
                
                if not actualizacion_revision or len(actualizacion_revision) < 10:
                    error_msg = f"Justificación requerida para revisión R{revision}. Mínimo 10 caracteres (actual: {len(actualizacion_revision)})."
                    print(f"[VALIDATION ERROR] {error_msg}")
                    print(f"[REVISION_DEBUG] ======= FIN ANÁLISIS DE REVISIÓN (ERROR) =======")
                    return jsonify({
                        "error": error_msg,
                        "campo_requerido": "actualizacionRevision",
                        "revision": revision,
                        "numero_cotizacion": numero_cotizacion,
                        "longitud_actual": len(actualizacion_revision),
                        "justificacion_recibida": actualizacion_revision[:50] + "..." if len(actualizacion_revision) > 50 else actualizacion_revision
                    }), 400
                else:
                    print(f"[REVISION_DEBUG] ✅ Validación de justificación EXITOSA para R{revision}")
            
            print(f"[REVISION_DEBUG] ======= FIN ANÁLISIS DE REVISIÓN (OK) =======")
            
            # Función auxiliar para extraer número de cotización de manera robusta
            def extraer_numero_cotizacion(datos):
                """Extrae número de cotización con múltiples fallbacks"""
                candidatos = [
                    datos.get('datosGenerales', {}).get('numeroCotizacion'),
                    datos.get('numeroCotizacionHidden'),
                    datos.get('numeroCotizacion')
                ]
                
                for i, candidato in enumerate(candidatos):
                    if candidato and str(candidato).strip():
                        print(f"[NUMERO_DEBUG] Número encontrado en posición {i}: '{candidato}'")
                        return str(candidato).strip()
                
                print(f"[NUMERO_DEBUG] ❌ NO se encontró número de cotización en ningún lugar")
                return None
            
            # Extraer y validar número de cotización
            numero_final = extraer_numero_cotizacion(datos)
            if numero_final:
                print(f"[NUMERO_DEBUG] ✅ Número de cotización confirmado: '{numero_final}'")
                # Asegurar que esté en todos los lugares necesarios
                datos['numeroCotizacion'] = numero_final
                if 'datosGenerales' not in datos:
                    datos['datosGenerales'] = {}
                datos['datosGenerales']['numeroCotizacion'] = numero_final
            else:
                print(f"[NUMERO_DEBUG] ⚠️ Procediendo sin número - será generado automáticamente")
            
            # Procesar imagen de referencia (si fue enviada)
            img_ref_resultado = procesar_imagen_referencia(datos, numero_final or 'nueva')
            if img_ref_resultado:
                if 'datosGenerales' not in datos:
                    datos['datosGenerales'] = {}
                datos['datosGenerales']['imagenReferencia'] = img_ref_resultado
                # Remover base64 crudo del payload antes de guardar en BD
                datos.pop('imagenReferencia', None)
                print(f"[FORM] Imagen de referencia procesada: {img_ref_resultado.get('url', 'sin URL')}")

            # Guardar usando DatabaseManager con manejo robusto de errores
            print("[FORM] FORMULARIO: Llamando a guardar_cotizacion...")
            resultado = db_manager.guardar_cotizacion(datos)
            print(f"[FORM] FORMULARIO: Resultado guardado = {json.dumps(resultado, indent=2, ensure_ascii=False)}")
            
            # Análisis detallado del resultado
            print(f"[GUARDAR_DEBUG] ===== ANÁLISIS DE RESULTADO DE GUARDADO =====")
            print(f"[GUARDAR_DEBUG] Success: {resultado.get('success', False)}")
            print(f"[GUARDAR_DEBUG] Error: {resultado.get('error', 'N/A')}")
            print(f"[GUARDAR_DEBUG] Numero cotización: {resultado.get('numeroCotizacion') or resultado.get('numero_cotizacion', 'N/A')}")
            print(f"[GUARDAR_DEBUG] Tipo error: {resultado.get('tipo_error', 'N/A')}")
            print(f"[GUARDAR_DEBUG] ID generado: {resultado.get('id', 'N/A')}")
            print(f"[GUARDAR_DEBUG] ===== FIN ANÁLISIS DE RESULTADO =====")
            
            if resultado.get("success", False):
                numero_cotizacion = resultado.get('numero_cotizacion') or resultado.get('numeroCotizacion')
                print(f"[OK] FORMULARIO: Guardado exitoso - Numero: {numero_cotizacion}")
                
                # ✅ LOG CRÍTICO: Cotización guardada exitosamente
                logging.info(f"COTIZACION_GUARDADA: {numero_cotizacion} - Cliente: {datos.get('datosGenerales', {}).get('cliente', 'N/A')}")

                # ✅ ELIMINAR DRAFTS ASOCIADOS - Prevenir duplicados después de guardar
                try:
                    if numero_cotizacion:
                        print(f"[DRAFT] Intentando eliminar drafts asociados a: {numero_cotizacion}")
                        resultado_limpieza = db_manager.eliminar_drafts_por_numero_cotizacion(numero_cotizacion)
                        if resultado_limpieza.get('success'):
                            print(f"[DRAFT] ✅ {resultado_limpieza.get('mensaje')}")
                        else:
                            print(f"[DRAFT] ⚠️ No se pudieron eliminar drafts: {resultado_limpieza.get('error')}")
                except Exception as draft_error:
                    print(f"[DRAFT] ❌ Error limpiando drafts (no crítico): {draft_error}")
                    # No bloquear el guardado por errores en drafts

                # Verificar si es un fallo silencioso detectado
                if resultado.get("tipo_error") == "fallo_silencioso":
                    critical_logger = logging.getLogger('FALLOS_CRITICOS')
                    critical_logger.error(f"FALLO_SILENCIOSO_DETECTADO: {numero_cotizacion} - {resultado.get('error', 'Error desconocido')}")
                    
                    return jsonify({
                        "error": "Error crítico en guardado - datos no persistieron",
                        "tipo_error": "fallo_silencioso",
                        "numero_cotizacion": numero_cotizacion
                    }), 500
                
                # ✅ COTIZACIÓN GUARDADA EXITOSAMENTE - PDF EN SEGUNDO PLANO
                # Separar completamente el guardado de la generación de PDF
                # La cotización YA ESTÁ GUARDADA, PDF es secundario
                
                respuesta_base = {
                    "success": True,
                    "mensaje": "Cotización guardada correctamente",
                    "numeroCotizacion": numero_cotizacion,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                # Agregar ID solo si existe (modo online)
                if "id" in resultado:
                    respuesta_base["id"] = resultado["id"]
                
                # INTENTAR generar PDF (OPCIONAL - no afecta éxito del guardado)
                try:
                    print(f"[PDF] FORMULARIO: ⏳ Iniciando generación de PDF (no crítica) para {numero_cotizacion}")
                    
                    if pdf_manager and (WEASYPRINT_AVAILABLE or REPORTLAB_AVAILABLE):
                        # Intentar generar PDF de manera no bloqueante
                        def generar_pdf_asincrono():
                            try:
                                cotizacion_busqueda = db_manager.obtener_cotizacion(numero_cotizacion)
                                if cotizacion_busqueda["encontrado"]:
                                    cotizacion = cotizacion_busqueda["item"]
                                    pdf_data = generar_pdf_reportlab(cotizacion)
                                    resultado_almacenamiento = pdf_manager.almacenar_pdf_nuevo(pdf_data, cotizacion)
                                    print(f"[PDF] ✅ PDF generado exitosamente en segundo plano: {numero_cotizacion}")
                                    return resultado_almacenamiento
                                else:
                                    print(f"[PDF] ⚠️ No se encontró cotización para PDF: {numero_cotizacion}")
                                    return None
                            except Exception as e:
                                print(f"[PDF] ❌ Error en generación asíncrona: {e}")
                                return None
                        
                        # Generar PDF con manejo simple de tiempo (compatible Windows)
                        import time
                        
                        try:
                            inicio_pdf = time.time()
                            print(f"[PDF] Iniciando generación a las {time.strftime('%H:%M:%S')}")
                            
                            pdf_resultado = generar_pdf_asincrono()
                            tiempo_transcurrido = time.time() - inicio_pdf
                            
                            print(f"[PDF] Generación completada en {tiempo_transcurrido:.2f} segundos")
                            
                            if pdf_resultado:
                                respuesta_base["pdf_generado"] = True
                                respuesta_base["pdf_info"] = {
                                    "ruta_local": pdf_resultado.get("ruta_local"),
                                    "google_drive": pdf_resultado.get("google_drive", {}),
                                    "mensaje": "PDF generado automáticamente",
                                    "tiempo_generacion": f"{tiempo_transcurrido:.2f}s"
                                }
                                print(f"[PDF] ✅ PDF incluido en respuesta exitosamente")
                            else:
                                respuesta_base["pdf_generado"] = False
                                respuesta_base["pdf_mensaje"] = "PDF se generará por demanda - cotización guardada exitosamente"
                                
                        except Exception as pdf_gen_error:
                            tiempo_transcurrido = time.time() - inicio_pdf
                            print(f"[PDF] ❌ Error después de {tiempo_transcurrido:.2f}s: {pdf_gen_error}")
                            respuesta_base["pdf_generado"] = False
                            respuesta_base["pdf_mensaje"] = f"PDF se generará por demanda (error de generación) - cotización guardada exitosamente"
                            
                    else:
                        print(f"[PDF] ⚠️ Generadores de PDF no disponibles")
                        respuesta_base["pdf_generado"] = False
                        respuesta_base["pdf_mensaje"] = "PDF se generará por demanda - cotización guardada exitosamente"
                        
                except Exception as pdf_error:
                    # CRÍTICO: Los errores de PDF NO deben afectar el éxito del guardado
                    print(f"[PDF] ❌ Error en PDF (NO CRÍTICO): {pdf_error}")
                    respuesta_base["pdf_generado"] = False
                    respuesta_base["pdf_mensaje"] = f"PDF se generará por demanda (error: {str(pdf_error)[:50]}) - cotización guardada exitosamente"
                
                # Agregar información adicional
                respuesta_base["revision"] = datos.get('datosGenerales', {}).get('revision', '1')
                respuesta_base["cliente"] = datos.get('datosGenerales', {}).get('cliente', 'N/A')
                
                print(f"[SUCCESS] FORMULARIO: ✅ Respuesta completa preparada para {numero_cotizacion}")
                respuesta = respuesta_base
                
                return jsonify(respuesta)
            else:
                # Manejo detallado de errores de guardado
                error_detalle = resultado.get('error', 'Error desconocido')
                tipo_error = resultado.get('tipo_error', 'general')
                
                print(f"[ERROR] FORMULARIO: ===== ERROR DE GUARDADO =====")
                print(f"[ERROR] FORMULARIO: Tipo: {tipo_error}")
                print(f"[ERROR] FORMULARIO: Detalle: {error_detalle}")
                print(f"[ERROR] FORMULARIO: Resultado completo: {json.dumps(resultado, indent=2, ensure_ascii=False)}")
                print(f"[ERROR] FORMULARIO: ===== FIN ERROR DE GUARDADO =====")
                
                # Log crítico para seguimiento
                logging.error(f"ERROR_GUARDADO_COTIZACION: {error_detalle} - Tipo: {tipo_error} - Cliente: {datos.get('datosGenerales', {}).get('cliente', 'N/A')}")
                
                # Respuesta específica según tipo de error
                if tipo_error == "validacion":
                    status_code = 400
                    error_usuario = f"Error de validación: {error_detalle}"
                elif tipo_error == "fallo_silencioso":
                    status_code = 500
                    error_usuario = "Error crítico en el sistema - datos no se guardaron correctamente"
                elif tipo_error == "conectividad":
                    status_code = 503
                    error_usuario = "Error de conectividad - inténtelo nuevamente"
                elif "Issue #1" in error_detalle:
                    status_code = 500
                    error_usuario = "Error en sistema de revisiones - número de cotización faltante"
                else:
                    status_code = 500
                    error_usuario = "Error interno del servidor"
                
                return jsonify({
                    "success": False,
                    "error": error_usuario,
                    "detalle_tecnico": error_detalle,
                    "tipo_error": tipo_error,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "numero_cotizacion": datos.get('datosGenerales', {}).get('numeroCotizacion', 'N/A'),
                    "revision": datos.get('datosGenerales', {}).get('revision', 'N/A')
                }), status_code
                
        except Exception as e:
            print(f"[CRITICAL] FORMULARIO: ERROR CRITICO - {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": "Error del servidor",
                "detalle": str(e)
            }), 500
    
    # ===== DIAGNÓSTICO GET =====
    print(f"[FORM_GET] ===== INICIO GET formulario =====")
    print(f"[FORM_GET] Query params recibidos: {dict(request.args)}")
    print(f"[FORM_GET] edicion_menor = {request.args.get('edicion_menor', 'NO_PRESENTE')!r}")
    print(f"[FORM_GET] revision = {request.args.get('revision', 'NO_PRESENTE')!r}")
    # ===== FIN DIAGNÓSTICO =====

    # Verificar si es edición menor (corrección sin nueva revisión)
    edicion_menor_id = request.args.get('edicion_menor')
    modo_edicion_menor = False
    datos_edicion_menor = None

    if edicion_menor_id:
        print(f"[EDICION_MENOR] Cargando formulario para edición menor: '{edicion_menor_id}'")
        resultado_em = db_manager.obtener_cotizacion(edicion_menor_id)
        if resultado_em.get('encontrado'):
            datos_edicion_menor = resultado_em['item']
            datos_edicion_menor = _safe_for_json(datos_edicion_menor)
            modo_edicion_menor = True
            print(f"[EDICION_MENOR] Cotización cargada para edición menor: {edicion_menor_id}")
        else:
            print(f"[EDICION_MENOR] Cotización no encontrada: '{edicion_menor_id}'")

    # Verificar si es una nueva revisión
    revision_id = request.args.get('revision')
    datos_precargados = None
    info_bloqueo_revision = None

    if revision_id:
        print(f"[REVISION] Solicitando nueva revisión de: '{revision_id}'")
        # Cargar datos de la cotización original para nueva revisión
        resultado = db_manager.obtener_cotizacion(revision_id)
        if resultado.get('encontrado'):
            cotizacion_original = resultado['item']
            numero_cotizacion = cotizacion_original.get('numeroCotizacion', '')
            print(f"[REVISION] Cotización original encontrada: {numero_cotizacion}")

            # Verificar si es la revisión más reciente
            info_revision = verificar_revision_mas_reciente(numero_cotizacion, db_manager)

            if info_revision['es_mas_reciente']:
                # Es la más reciente, permitir crear nueva revisión
                datos_precargados = preparar_datos_nueva_revision(cotizacion_original)
                print(f"[REVISION] ✅ Es la más reciente - Nueva revisión: {datos_precargados.get('datosGenerales', {}).get('revision', 'N/A')}")
            else:
                # NO es la más reciente, bloquear y mostrar advertencia
                print(f"[REVISION] ⚠️ BLOQUEADA - No es la más reciente")
                print(f"[REVISION] Revisión actual: R{info_revision['revision_actual']}")
                print(f"[REVISION] Última revisión: R{info_revision['revision_maxima']} ({info_revision['numero_ultima_revision']})")

                info_bloqueo_revision = {
                    'bloqueada': True,
                    'numero_actual': numero_cotizacion,
                    'revision_actual': info_revision['revision_actual'],
                    'revision_maxima': info_revision['revision_maxima'],
                    'numero_ultima_revision': info_revision['numero_ultima_revision'],
                    'historial': info_revision.get('historial_revisiones', [])
                }
        else:
            print(f"[REVISION] ⚠️ Cotización original no encontrada para: '{revision_id}'")

    print(f"[FORM_GET] ===== RENDERIZANDO TEMPLATE =====")
    print(f"[FORM_GET] modo_edicion_menor={modo_edicion_menor!r} | datos_edicion_menor presente={datos_edicion_menor is not None}")
    print(f"[FORM_GET] datos_precargados presente={datos_precargados is not None} | info_bloqueo_revision presente={info_bloqueo_revision is not None}")
    if datos_edicion_menor:
        print(f"[FORM_GET] datos_edicion_menor keys: {list(datos_edicion_menor.keys())[:10]}")
    if datos_precargados:
        print(f"[FORM_GET] datos_precargados keys: {list(datos_precargados.keys())[:10]}")
    print(f"[FORM_GET] ===== FIN RENDERIZANDO =====")

    return render_template("formulario.html",
                         materiales=LISTA_MATERIALES,
                         datos_precargados=datos_precargados,
                         info_bloqueo_revision=info_bloqueo_revision,
                         vendedor_sesion=session.get('vendedor', ''),
                         modo_edicion_menor=modo_edicion_menor,
                         datos_edicion_menor=datos_edicion_menor)


@app.route("/debug/test-obtener-cotizacion/<path:item_id>")
@login_required
def debug_test_obtener_cotizacion(item_id):
    """Endpoint de diagnóstico: prueba obtener_cotizacion() directamente."""
    from urllib.parse import unquote
    item_id = unquote(item_id)
    resultado = db_manager.obtener_cotizacion(item_id)
    encontrado = resultado.get('encontrado', False)
    response = {
        "id_buscado": item_id,
        "encontrado": encontrado,
        "error": resultado.get('error'),
    }
    if encontrado:
        item = resultado['item']
        response["keys_en_item"] = list(item.keys())
        response["numeroCotizacion"] = item.get('numeroCotizacion')
        response["tiene_datosGenerales"] = 'datosGenerales' in item
        response["tiene_condiciones"] = 'condiciones' in item
        response["cantidad_items"] = len(item.get('items', []))
        # Probar _safe_for_json
        try:
            safe = _safe_for_json(item)
            import json
            json.dumps(safe)  # validar serialización
            response["_safe_for_json_ok"] = True
        except Exception as e:
            response["_safe_for_json_ok"] = False
            response["_safe_for_json_error"] = str(e)
        # Probar preparar_datos_nueva_revision
        try:
            preparado = preparar_datos_nueva_revision(item)
            response["preparar_revision_ok"] = preparado is not None
            if preparado:
                response["preparado_keys"] = list(preparado.keys())
                response["preparado_revision"] = preparado.get('datosGenerales', {}).get('revision')
        except Exception as e:
            response["preparar_revision_ok"] = False
            response["preparar_revision_error"] = str(e)
    return jsonify(response)


@app.route("/debug-materiales")
def debug_materiales():
    """Ruta de debug para verificar materiales"""
    return jsonify({
        "total": len(LISTA_MATERIALES),
        "primeros_5": LISTA_MATERIALES[:5],
        "ultimos_5": LISTA_MATERIALES[-5:] if len(LISTA_MATERIALES) > 5 else LISTA_MATERIALES
    })

@app.route("/admin/sincronizacion")
def admin_sincronizacion():
    """Panel administrativo de sincronización"""
    estado = db_manager.obtener_estado_sincronizacion()
    return jsonify(estado)

@app.route("/admin/forzar-sincronizacion", methods=["POST"])
def admin_forzar_sincronizacion():
    """Fuerza sincronización manual"""
    resultado = db_manager.forzar_sincronizacion()
    return jsonify(resultado)

# ========================================
# ENDPOINTS DE GESTIÓN DE DRAFTS
# ========================================

@app.route("/api/draft/save", methods=["POST"])
def guardar_draft():
    """
    Guarda o actualiza un draft (borrador) de cotización

    Body JSON:
        {
            "vendedor": "RCWS",
            "datos": {
                "datosGenerales": {...},
                "items": [...],
                "condiciones": {...}
            },
            "draft_id": "draft_123" (opcional, para actualizar)
        }

    Returns:
        {
            "success": true,
            "draft_id": "draft_1234567890",
            "timestamp": 1234567890,
            "nombre": "Cliente X - Proyecto Y"
        }
    """
    try:
        datos = request.get_json()

        if not datos:
            return jsonify({"success": False, "error": "No se recibieron datos"}), 400

        # Validar que tenga vendedor y datos
        if not datos.get('vendedor'):
            return jsonify({"success": False, "error": "Campo 'vendedor' requerido"}), 400

        if not datos.get('datos'):
            return jsonify({"success": False, "error": "Campo 'datos' requerido"}), 400

        # Guardar draft
        resultado = db_manager.guardar_draft(datos)

        if resultado.get('success'):
            print(f"[API] Draft guardado exitosamente: {resultado.get('draft_id')}")
            return jsonify(resultado), 200
        else:
            print(f"[API] Error guardando draft: {resultado.get('error')}")
            return jsonify(resultado), 500

    except Exception as e:
        error_msg = str(e)
        print(f"[API] Excepción guardando draft: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/draft/list", methods=["GET"])
def listar_drafts():
    """
    Lista todos los drafts, opcionalmente filtrados por vendedor

    Query params:
        vendedor (opcional): Iniciales del vendedor para filtrar

    Returns:
        {
            "success": true,
            "drafts": [
                {
                    "id": "draft_123",
                    "vendedor": "RCWS",
                    "nombre": "Cliente X - Proyecto Y",
                    "timestamp": 1234567890,
                    "fecha_creacion": "2025-10-24T10:30:00",
                    "ultima_modificacion": "2025-10-24T11:00:00"
                }
            ],
            "total": 1
        }
    """
    try:
        vendedor = request.args.get('vendedor')

        drafts = db_manager.listar_drafts(vendedor)

        print(f"[API] Listando drafts - Vendedor: {vendedor or 'Todos'} - Total: {len(drafts)}")

        return jsonify({
            "success": True,
            "drafts": drafts,
            "total": len(drafts)
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error listando drafts: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/draft/load/<draft_id>", methods=["GET"])
def cargar_draft(draft_id):
    """
    Obtiene los datos completos de un draft específico

    Args:
        draft_id: ID del draft a cargar

    Returns:
        {
            "success": true,
            "draft": {
                "id": "draft_123",
                "vendedor": "RCWS",
                "nombre": "Cliente X - Proyecto Y",
                "datos": {
                    "datosGenerales": {...},
                    "items": [...],
                    "condiciones": {...}
                },
                "timestamp": 1234567890,
                "fecha_creacion": "2025-10-24T10:30:00",
                "ultima_modificacion": "2025-10-24T11:00:00"
            }
        }
    """
    try:
        draft = db_manager.obtener_draft(draft_id)

        if draft:
            print(f"[API] Draft cargado: {draft_id}")
            return jsonify({
                "success": True,
                "draft": draft
            }), 200
        else:
            print(f"[API] Draft no encontrado: {draft_id}")
            return jsonify({
                "success": False,
                "error": f"Draft {draft_id} no encontrado"
            }), 404

    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error cargando draft: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/draft/debug/<draft_id>", methods=["GET"])
def debug_draft(draft_id):
    """
    Diagnóstico: devuelve estructura detallada de un draft para verificar integridad.

    Returns:
        {
            "success": true,
            "debug": {
                "draft_id": "...",
                "nombre": "...",
                "total_items": N,
                "items_detalle": [
                    {
                        "index": 0,
                        "descripcion_len": N,
                        "materiales_count": N,
                        "materiales_detalle": [...],
                        "otros_materiales_count": N,
                        "otros_materiales_detalle": [...]
                    }
                ],
                "raw_keys": [...],
                "data_integridad": {...}
            }
        }
    """
    try:
        draft = db_manager.obtener_draft(draft_id)

        if not draft:
            return jsonify({
                "success": False,
                "error": f"Draft {draft_id} no encontrado"
            }), 404

        datos = draft.get('datos', {})
        items = datos.get('items', [])
        datos_generales = datos.get('datosGenerales', {})
        condiciones = datos.get('condiciones', {})

        items_detalle = []
        total_materiales = 0
        total_otros = 0

        for i, item in enumerate(items):
            mats = item.get('materiales', [])
            otros = item.get('otrosMateriales', [])
            total_materiales += len(mats)
            total_otros += len(otros)

            items_detalle.append({
                "index": i,
                "descripcion_preview": (item.get('descripcion') or '')[:80],
                "descripcion_len": len(item.get('descripcion') or ''),
                "cantidad": item.get('cantidad'),
                "uom": item.get('uom'),
                "materiales_count": len(mats),
                "materiales_detalle": [
                    {
                        "material": m.get('material') or m.get('descripcion') or 'N/A',
                        "cantidad": m.get('cantidad'),
                        "precio": m.get('precio'),
                        "unidad": m.get('unidad'),
                        "subtotal": m.get('subtotal')
                    } for m in mats
                ],
                "otros_materiales_count": len(otros),
                "otros_materiales_detalle": [
                    {
                        "descripcion": o.get('descripcion') or 'N/A',
                        "cantidad": o.get('cantidad'),
                        "precio": o.get('precio'),
                        "subtotal": o.get('subtotal')
                    } for o in otros
                ]
            })

        import hashlib, json
        datos_hash = hashlib.md5(
            json.dumps(datos, sort_keys=True, default=str).encode('utf-8')
        ).hexdigest()

        return jsonify({
            "success": True,
            "debug": {
                "draft_id": draft_id,
                "nombre": draft.get('nombre', 'N/A'),
                "vendedor": draft.get('vendedor', 'N/A'),
                "timestamp": draft.get('timestamp'),
                "total_items": len(items),
                "total_materiales": total_materiales,
                "total_otros_materiales": total_otros,
                "datos_generales_keys": list(datos_generales.keys()) if datos_generales else [],
                "condiciones_keys": list(condiciones.keys()) if condiciones else [],
                "items_detalle": items_detalle,
                "raw_keys": list(datos.keys()),
                "data_integridad": {
                    "hash_md5": datos_hash,
                    "datos_size_bytes": len(json.dumps(datos, default=str))
                }
            }
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"[API] Error en debug draft: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/draft/delete/<draft_id>", methods=["DELETE"])
def eliminar_draft(draft_id):
    """
    Elimina un draft

    Args:
        draft_id: ID del draft a eliminar

    Returns:
        {
            "success": true,
            "mensaje": "Draft eliminado"
        }
    """
    try:
        resultado = db_manager.eliminar_draft(draft_id)

        if resultado.get('success'):
            print(f"[API] Draft eliminado: {draft_id}")
            return jsonify(resultado), 200
        else:
            print(f"[API] Error eliminando draft: {resultado.get('error')}")
            return jsonify(resultado), 500

    except Exception as e:
        error_msg = str(e)
        print(f"[API] Excepción eliminando draft: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500

# ========================================
# EDICIÓN MENOR (sin nueva revisión)
# ========================================

@app.route("/api/cotizacion/<path:numero_cotizacion>", methods=["GET"])
def obtener_cotizacion_api(numero_cotizacion):
    """
    Devuelve los datos de una cotización en formato JSON.
    Usado como fallback cuando el template no puede inyectar los datos directamente.
    Soporta ?preparar_revision=true para el flujo de Nueva Revisión.
    """
    try:
        import time
        t0 = time.time()
        from urllib.parse import unquote
        numero_cotizacion = unquote(numero_cotizacion)
        preparar_revision = request.args.get('preparar_revision', '').lower() == 'true'
        print(f"[API_COTIZACION] Buscando: {numero_cotizacion!r} | preparar_revision={preparar_revision}")

        resultado = db_manager.obtener_cotizacion(numero_cotizacion)
        print(f"[API_COTIZACION] Resultado: encontrado={resultado.get('encontrado')} | keys={list(resultado.keys())}")
        if resultado.get('encontrado'):
            cotizacion = resultado['item']
            if preparar_revision:
                # Verificar que sea la revisión más reciente
                nc = cotizacion.get('numeroCotizacion', '')
                info_revision = verificar_revision_mas_reciente(nc, db_manager)
                if not info_revision.get('es_mas_reciente'):
                    return jsonify({
                        "success": False,
                        "error": "No es la revisión más reciente",
                        "bloqueada": True,
                        "info": info_revision
                    }), 409
                # Preparar datos para nueva revisión
                cotizacion = preparar_datos_nueva_revision(cotizacion)
                if cotizacion is None:
                    return jsonify({"success": False, "error": "Error al preparar revisión"}), 500
            nc_api = cotizacion.get("numeroCotizacion", "?"); rev_api = cotizacion.get("datosGenerales",{}).get("revision","?"); print(f"[API_COTIZACION] [OK] Exito en {time.time()-t0:.3f}s | num={nc_api} | rev={rev_api}")
            return jsonify({"success": True, "cotizacion": cotizacion}), 200
        else:
            print(f"[API_COTIZACION] ❌ No encontrada: {numero_cotizacion!r} en {time.time()-t0:.3f}s")
            return jsonify({"success": False, "error": f"Cotización '{numero_cotizacion}' no encontrada"}), 404
    except Exception as e:
        import traceback
        print(f"[API_COTIZACION] [ERROR] {type(e).__name__}: {e} en {time.time()-t0:.3f}s")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/cotizacion/<path:numero_cotizacion>/edicion-menor", methods=["PATCH"])
def edicion_menor(numero_cotizacion):
    """
    Corrige campos de texto (typos, ortografía) sin generar nueva revisión.
    Solo acepta: datosGenerales.atencionA/contacto,
                 condiciones.tiempoEntrega/entregaEn/comentarios,
                 items[].descripcion/notas,
                 imagenReferencia (opcional, para agregar/quitar/actualizar imagen)
    """
    try:
        parche = request.get_json()
        if not parche:
            return jsonify({"success": False, "error": "No se recibieron datos"}), 400

        # Procesar imagen de referencia en el parche (si fue enviada)
        if 'imagenReferencia' in parche:
            img_raw = parche.pop('imagenReferencia')
            if img_raw is not None and not (isinstance(img_raw, dict) and img_raw.get('conservar')):
                # Nueva imagen: procesar base64 y subir
                datos_temp = {
                    'imagenReferencia': img_raw,
                    'datosGenerales': {}
                }
                img_resultado = procesar_imagen_referencia(datos_temp, numero_cotizacion)
                parche['imagenReferenciaProcesada'] = img_resultado  # dict o None
            elif img_raw is not None and isinstance(img_raw, dict) and img_raw.get('conservar'):
                # Imagen no modificada — no hacer nada (se preserva la existente)
                pass
            else:
                # img_raw es None → el usuario eliminó la imagen explícitamente
                parche['imagenReferenciaProcesada'] = None

        usuario = session.get('vendedor', 'desconocido')
        resultado = db_manager.edicion_menor_cotizacion(numero_cotizacion, parche, usuario)

        if resultado.get('success'):
            print(f"[EDICION_MENOR] Corrección guardada: {numero_cotizacion}")
            return jsonify({
                "success": True,
                "numero_cotizacion": numero_cotizacion,
                "mensaje": "Corrección guardada correctamente"
            }), 200
        else:
            return jsonify(resultado), 400

    except Exception as e:
        print(f"[EDICION_MENOR] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/diagnostico-completo")
def diagnostico_completo():
    """Diagnóstico completo del sistema para debugging de producción"""
    import sys
    
    es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
    entorno = "RENDER" if es_render else "LOCAL"
    
    diagnostico = {
        "timestamp": datetime.datetime.now().isoformat(),
        "entorno": entorno,
        "sistema": {
            "es_render": bool(es_render),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "working_directory": os.getcwd(),
            "flask_debug": app.config.get('DEBUG'),
            "app_version": os.getenv('APP_VERSION', '1.0.0')
        },
        "supabase": {
            "estado": "offline" if db_manager.modo_offline else "online",
            "url_configurada": bool(os.getenv('SUPABASE_URL')),
            "database_url_configurada": bool(os.getenv('DATABASE_URL')),
            "service_key_configurada": bool(os.getenv('SUPABASE_SERVICE_KEY'))
        },
        "google_drive": {
            "disponible": bool(pdf_manager and pdf_manager.drive_client and pdf_manager.drive_client.is_available()),
            "credenciales_configuradas": bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')),
            "carpeta_nuevas": os.getenv('GOOGLE_DRIVE_FOLDER_NUEVAS'),
            "carpeta_antiguas": os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS')
        },
        "materiales": {
            "total_cargados": len(LISTA_MATERIALES),
            "archivo_csv_existe": os.path.exists(os.path.join(os.getcwd(), 'Lista de materiales.csv'))
        },
        "pdf": {
            "reportlab_disponible": REPORTLAB_AVAILABLE,
            "weasyprint_disponible": WEASYPRINT_AVAILABLE,
            "pdf_manager_inicializado": pdf_manager is not None
        }
    }
    
    # Tests adicionales si están disponibles
    if not db_manager.modo_offline:
        try:
            # Test rápido de Supabase PostgreSQL
            stats = db_manager.obtener_estadisticas()
            diagnostico["supabase"]["test_conexion"] = "exitoso"
            diagnostico["supabase"]["total_cotizaciones"] = stats.get('total_cotizaciones', 0)
            diagnostico["supabase"]["fuente"] = stats.get('fuente', 'desconocida')
        except Exception as e:
            diagnostico["supabase"]["test_conexion"] = f"fallo: {str(e)[:100]}"
    
    if pdf_manager and pdf_manager.drive_client and pdf_manager.drive_client.is_available():
        try:
            # Test rápido de Google Drive
            about_info = pdf_manager.drive_client.service.about().get(fields='user').execute()
            diagnostico["google_drive"]["test_api"] = "exitoso"
            diagnostico["google_drive"]["email_servicio"] = about_info.get('user', {}).get('emailAddress', 'N/A')
        except Exception as e:
            diagnostico["google_drive"]["test_api"] = f"fallo: {str(e)[:100]}"
    
    return jsonify(diagnostico)

@app.route("/diagnostico-entorno")
def diagnostico_entorno():
    """Diagnóstico de variables de entorno para Render (mantenido por compatibilidad)"""
    es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
    return jsonify({
        'render_detected': bool(es_render),
        'supabase_url_set': bool(os.getenv('SUPABASE_URL')),
        'database_url_set': bool(os.getenv('DATABASE_URL')),
        'google_credentials_set': bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')),
        'entorno': 'RENDER' if es_render else 'LOCAL'
    })

# ============================================
# RUTAS DE BÚSQUEDA Y CONSULTA
# ============================================

@app.route("/buscar", methods=["POST"])
def buscar():
    """Buscar cotizaciones con paginación - BÚSQUEDA UNIFICADA"""
    try:
        datos = request.get_json()
        query = datos.get("query", "")
        page = datos.get("page", 1)
        per_page = datos.get("per_page", int(os.getenv('DEFAULT_PAGE_SIZE', '20')))
        
        print(f"[BÚSQUEDA UNIFICADA] Query: '{query}' (página {page})")
        print(f"[BÚSQUEDA UNIFICADA] Estado DB: modo_offline={db_manager.modo_offline}")
        
        # PASO 1: Buscar en Supabase/JSON local (cotizaciones con desglose)
        resultados_cotizaciones = []
        try:
            print(f"[DB] Iniciando búsqueda en {'Supabase' if not db_manager.modo_offline else 'JSON local'}...")
            resultado_db = db_manager.buscar_cotizaciones(query, 1, 1000)  # Obtener todas
            print(f"[DB] Resultado de búsqueda: {type(resultado_db)} - {list(resultado_db.keys()) if isinstance(resultado_db, dict) else 'No es dict'}")
            
            if not resultado_db.get("error"):
                cotizaciones = resultado_db.get("resultados", [])
                print(f"[DB] Encontradas {len(cotizaciones)} cotizaciones en base de datos")
                
                if len(cotizaciones) > 0:
                    print(f"[DB] Primera cotización: {list(cotizaciones[0].keys()) if cotizaciones[0] else 'Vacía'}")
                    if 'datosGenerales' in cotizaciones[0]:
                        print(f"[DB] datosGenerales keys: {list(cotizaciones[0]['datosGenerales'].keys())}")
                else:
                    print(f"[DB] ⚠️ No se encontraron cotizaciones para query: '{query}'")
                
                for cot in cotizaciones:
                    datos_gen = cot.get('datosGenerales', {})
                    resultados_cotizaciones.append({
                        "numero_cotizacion": cot.get('numeroCotizacion', 'N/A'),
                        "cliente": datos_gen.get('cliente', 'N/A'),
                        "vendedor": datos_gen.get('vendedor', 'N/A'),
                        "proyecto": datos_gen.get('proyecto', 'N/A'),
                        "fecha_creacion": cot.get('fechaCreacion', 'N/A'),
                        "tipo": "cotizacion",
                        "tiene_desglose": True,
                        "fuente": "supabase" if not db_manager.modo_offline else "json_local",
                        "revision": cot.get('revision', 1),
                        "_id": cot.get('_id')
                    })
            else:
                print(f"[DB] Error en búsqueda de cotizaciones: {resultado_db.get('error')}")
        except Exception as e:
            print(f"[DB] Error buscando cotizaciones: {e}")
        
        # PASO 2: Buscar en PDFs (Supabase Storage + Google Drive + Local)
        resultados_pdfs = []
        try:
            if pdf_manager:
                print(f"[PDF] Iniciando búsqueda de PDFs...")
                resultado_pdfs = pdf_manager.buscar_pdfs(query, 1, 1000)  # Obtener todos
                print(f"[PDF] Resultado PDFs: {type(resultado_pdfs)} - {list(resultado_pdfs.keys()) if isinstance(resultado_pdfs, dict) else 'No es dict'}")
                
                if not resultado_pdfs.get("error"):
                    pdfs = resultado_pdfs.get("resultados", [])
                    print(f"[PDF] Encontrados {len(pdfs)} PDFs")
                    
                    for pdf in pdfs:
                        resultados_pdfs.append({
                            "numero_cotizacion": pdf.get('numero_cotizacion', 'N/A'),
                            "cliente": pdf.get('cliente', 'N/A'),
                            "vendedor": pdf.get('vendedor', 'N/A'),
                            "proyecto": pdf.get('proyecto', 'N/A'),
                            "fecha_creacion": pdf.get('fecha_creacion', 'N/A'),
                            "tipo": pdf.get('tipo', 'pdf'),
                            "tiene_desglose": pdf.get('tiene_desglose', False),
                            "fuente": pdf.get('tipo', 'pdf_manager'),
                            "revision": pdf.get('revision', 1)
                        })
                else:
                    print(f"[PDF] Error en búsqueda de PDFs: {resultado_pdfs.get('error')}")
            else:
                print(f"[PDF] ⚠️ PDFManager no disponible - saltando búsqueda de PDFs")
        except Exception as e:
            print(f"[PDF] Error buscando PDFs: {e}")
            import traceback
            traceback.print_exc()
        
        # PASO 3: Combinar y deduplicar resultados
        resultados_combinados = {}
        
        print(f"[COMBINAR] Cotizaciones DB: {len(resultados_cotizaciones)}, PDFs: {len(resultados_pdfs)}")
        
        # Añadir cotizaciones (prioridad alta - tienen desglose)
        for cot in resultados_cotizaciones:
            numero = cot['numero_cotizacion']
            resultados_combinados[numero] = cot
            print(f"[COMBINAR] Agregada cotización: {numero}")
        
        # Añadir PDFs solo si no existe cotización con desglose
        for pdf in resultados_pdfs:
            numero = pdf['numero_cotizacion']
            if numero not in resultados_combinados:
                resultados_combinados[numero] = pdf
                print(f"[COMBINAR] Agregado PDF: {numero}")
            else:
                # Si ya existe cotización, marcar que tiene PDF
                resultados_combinados[numero]['tiene_pdf'] = True
                print(f"[COMBINAR] PDF {numero} ya existe como cotización - marcando tiene_pdf=True")
        
        # Convertir a lista y ordenar por relevancia
        resultados_finales = list(resultados_combinados.values())
        
        # Aplicar filtros de búsqueda si hay query
        if query.strip():
            resultados_filtrados = []
            query_lower = query.lower()
            for res in resultados_finales:
                # Buscar en múltiples campos
                texto_busqueda = f"{res.get('numero_cotizacion', '')} {res.get('cliente', '')} {res.get('vendedor', '')} {res.get('proyecto', '')}".lower()
                if query_lower in texto_busqueda:
                    resultados_filtrados.append(res)
            resultados_finales = resultados_filtrados
        
        # Paginación
        total = len(resultados_finales)
        start = (page - 1) * per_page
        end = start + per_page
        resultados_paginados = resultados_finales[start:end]
        
        print(f"[UNIFICADA] Total: {total}, Página: {len(resultados_paginados)} resultados")
        
        # Debug: mostrar estructura de respuesta
        if len(resultados_paginados) > 0:
            print(f"[UNIFICADA] Primer resultado enviado al frontend:")
            primer_resultado = resultados_paginados[0]
            for key, value in primer_resultado.items():
                print(f"   {key}: {value}")
        
        respuesta = {
            "resultados": resultados_paginados,
            "total": total,
            "pagina": page,
            "por_pagina": per_page,
            "total_paginas": (total + per_page - 1) // per_page,
            "modo": "busqueda_unificada"
        }
        
        print(f"[UNIFICADA] Enviando respuesta con {len(resultados_paginados)} resultados")
        return jsonify(respuesta)

    except Exception as e:
        print(f"[UNIFICADA] Error en búsqueda: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error en búsqueda unificada"}), 500

@app.route("/todas-cotizaciones")
def todas_cotizaciones():
    """Vista de tabla Excel-style con todas las cotizaciones"""
    if 'vendedor' not in session:
        return redirect(url_for('login'))

    # MODO DEBUG: Devolver JSON crudo si se accede con ?debug=1
    debug_mode = request.args.get('debug') == '1'

    # PAGINACIÓN: Obtener página actual (default 1) y tamaño de página
    page = request.args.get('page', 1, type=int)
    page_size = 50  # 50 registros por página

    # FILTROS: Obtener parámetros de filtro desde URL
    filtro_numero = request.args.get('numero', '').strip()
    filtro_cliente = request.args.get('cliente', '').strip()
    filtro_vendedor = request.args.get('vendedor', '').strip()
    filtro_proyecto = request.args.get('proyecto', '').strip()
    filtro_fecha_desde = request.args.get('fecha_desde', '').strip()
    filtro_fecha_hasta = request.args.get('fecha_hasta', '').strip()
    filtro_revision = request.args.get('revision', '').strip()
    filtro_moneda = request.args.get('moneda', '').strip()
    filtro_tipo = request.args.get('tipo', '').strip()

    # Log de filtros activos
    filtros_activos = []
    if filtro_numero: filtros_activos.append(f"numero={filtro_numero}")
    if filtro_cliente: filtros_activos.append(f"cliente={filtro_cliente}")
    if filtro_vendedor: filtros_activos.append(f"vendedor={filtro_vendedor}")
    if filtro_proyecto: filtros_activos.append(f"proyecto={filtro_proyecto}")
    if filtro_fecha_desde: filtros_activos.append(f"fecha_desde={filtro_fecha_desde}")
    if filtro_fecha_hasta: filtros_activos.append(f"fecha_hasta={filtro_fecha_hasta}")
    if filtro_revision: filtros_activos.append(f"revision={filtro_revision}")
    if filtro_moneda: filtros_activos.append(f"moneda={filtro_moneda}")
    if filtro_tipo: filtros_activos.append(f"tipo={filtro_tipo}")

    if filtros_activos:
        print(f"[TODAS-COTIZACIONES] Filtros activos: {', '.join(filtros_activos)}")

    try:
        print(f"[TODAS-COTIZACIONES] Obteniendo todas las cotizaciones (página {page})...")

        # Obtener todas las cotizaciones de la base de datos
        resultado_db = db_manager.buscar_cotizaciones("", 1, 10000)  # Query vacía = todas

        # Obtener todos los PDFs (incluye Google Drive antiguas)
        resultado_pdfs = pdf_manager.buscar_pdfs("", 1, 10000) if pdf_manager else {"resultados": []}

        if debug_mode:
            # MODO DEBUG: Devolver JSON crudo de las primeras 3 cotizaciones
            if resultado_db.get("error"):
                return jsonify({
                    "error": True,
                    "mensaje": str(resultado_db.get("error")),
                    "modo_conexion": "Offline (JSON)" if db_manager.modo_offline else "Online (Supabase)"
                })

            cotizaciones_raw = resultado_db.get("resultados", [])
            debug_data = {
                "modo_conexion": "Offline (JSON)" if db_manager.modo_offline else "Online (Supabase)",
                "total_encontradas": len(cotizaciones_raw),
                "primeras_3_crudas": []
            }

            for idx, cot in enumerate(cotizaciones_raw[:3]):
                # Convertir a formato serializable
                cot_serializable = {}
                for key, value in cot.items():
                    try:
                        # Intentar serializar a JSON para verificar
                        json.dumps(value)
                        cot_serializable[key] = value
                    except:
                        # Si falla, convertir a string
                        cot_serializable[key] = str(value)

                debug_data["primeras_3_crudas"].append(cot_serializable)

            return jsonify(debug_data)

        cotizaciones = []
        numeros_vistos = set()  # Para evitar duplicados entre BD y PDFs

        if not resultado_db.get("error"):
            cotizaciones_raw = resultado_db.get("resultados", [])
            print(f"[TODAS-COTIZACIONES] Encontradas {len(cotizaciones_raw)} cotizaciones de BD")

            # DEBUG: Mostrar estructura de primera cotización
            if len(cotizaciones_raw) > 0:
                primera = cotizaciones_raw[0]
                print(f"[DEBUG] === ESTRUCTURA DE PRIMERA COTIZACIÓN ===")
                print(f"[DEBUG] Keys en raíz: {list(primera.keys())}")
                print(f"[DEBUG] numeroCotizacion: {primera.get('numeroCotizacion', 'NO ENCONTRADO')}")
                print(f"[DEBUG] datosGenerales presente: {'datosGenerales' in primera}")
                if 'datosGenerales' in primera:
                    dg = primera['datosGenerales']
                    print(f"[DEBUG] datosGenerales type: {type(dg)}")
                    if isinstance(dg, dict):
                        print(f"[DEBUG] datosGenerales keys: {list(dg.keys())}")
                        print(f"[DEBUG] datosGenerales.fecha: '{dg.get('fecha', 'NO ENCONTRADO')}'")
                        print(f"[DEBUG] datosGenerales.cliente: '{dg.get('cliente', 'NO ENCONTRADO')}'")
                    else:
                        print(f"[DEBUG] datosGenerales NO ES DICT: {dg}")
                print(f"[DEBUG] items presente: {'items' in primera}")
                if 'items' in primera:
                    items = primera['items']
                    print(f"[DEBUG] Total items: {len(items) if isinstance(items, list) else 'NO ES LISTA'}")
                    if isinstance(items, list) and len(items) > 0:
                        print(f"[DEBUG] Primer item keys: {list(items[0].keys()) if isinstance(items[0], dict) else 'NO ES DICT'}")
                        print(f"[DEBUG] Primer item completo: {items[0]}")
                print(f"[DEBUG] condiciones presente: {'condiciones' in primera}")
                if 'condiciones' in primera:
                    print(f"[DEBUG] condiciones: {primera['condiciones']}")
                print(f"[DEBUG] === FIN ESTRUCTURA ===")

            # Transformar datos para tabla compacta
            for idx, cot in enumerate(cotizaciones_raw):
                datos_gen = cot.get('datosGenerales', {})

                # EXTRACCIÓN ROBUSTA DE FECHA - intentar múltiples ubicaciones
                fecha = 'N/A'
                if isinstance(datos_gen, dict):
                    fecha = datos_gen.get('fecha') or datos_gen.get('Fecha')
                if not fecha or fecha == 'N/A':
                    # Intentar en raíz
                    fecha = cot.get('fecha') or cot.get('fechaCreacion') or cot.get('timestamp')
                    if fecha and isinstance(fecha, (int, float)):
                        # Si es timestamp, convertir a fecha
                        from datetime import datetime
                        try:
                            fecha = datetime.fromtimestamp(fecha/1000 if fecha > 10000000000 else fecha).strftime('%Y-%m-%d')
                        except:
                            fecha = 'N/A'
                if not fecha:
                    fecha = 'N/A'

                # CÁLCULO ROBUSTODEL TOTAL - probar todas las variantes posibles
                total_calculado = 0.0
                items = cot.get('items', [])

                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            # Opción 1: campo 'total' directo en el item
                            if 'total' in item and item['total']:
                                total_calculado += safe_float(item.get('total', 0))
                            # Opción 2: campo 'subtotal'
                            elif 'subtotal' in item and item['subtotal']:
                                total_calculado += safe_float(item.get('subtotal', 0))
                            # Opción 3: calcular de precio_unitario * cantidad
                            elif 'precio_unitario' in item:
                                precio = safe_float(item.get('precio_unitario', 0))
                                cantidad = safe_float(item.get('cantidad', 1))
                                total_calculado += precio * cantidad
                            # Opción 4: calcular de precio * cantidad
                            elif 'precio' in item:
                                precio = safe_float(item.get('precio', 0))
                                cantidad = safe_float(item.get('cantidad', 1))
                                total_calculado += precio * cantidad
                            # Opción 5: costoUnidad * cantidad
                            elif 'costoUnidad' in item:
                                costo = safe_float(item.get('costoUnidad', 0))
                                cantidad = safe_float(item.get('cantidad', 1))
                                total_calculado += costo * cantidad

                # Obtener moneda de condiciones o datosGenerales
                condiciones = cot.get('condiciones', {})
                if not condiciones or not isinstance(condiciones, dict):
                    condiciones = datos_gen.get('condiciones', {})
                moneda = condiciones.get('moneda', 'MXN') if isinstance(condiciones, dict) else 'MXN'

                # EXTRACCIÓN ROBUSTA DE REVISIÓN - intentar múltiples ubicaciones
                revision = None
                import re

                # Intento 1 (PRIORITARIO): Extraer del número de cotización (formato: ...-R##-...)
                # Este es el más confiable porque R10, R2, etc. están en el número
                numero_cot = cot.get('numeroCotizacion', '')
                if numero_cot and isinstance(numero_cot, str):
                    match = re.search(r'-R(\d+)-', numero_cot)
                    if match:
                        revision = int(match.group(1))

                # Intento 2: Campo revision en raíz (solo si no se encontró en número)
                if not revision and 'revision' in cot:
                    try:
                        revision = int(cot.get('revision'))
                    except:
                        pass

                # Intento 3: Campo revision en datosGenerales (solo si no se encontró)
                if not revision and isinstance(datos_gen, dict) and 'revision' in datos_gen:
                    try:
                        revision = int(datos_gen.get('revision'))
                    except:
                        pass

                # Default a 1 si no se encontró
                if not revision:
                    revision = 1

                numero_cot = cot.get('numeroCotizacion', 'N/A')
                numeros_vistos.add(numero_cot)  # Marcar como visto

                cotizaciones.append({
                    "numero": numero_cot,
                    "cliente": datos_gen.get('cliente', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                    "vendedor": datos_gen.get('vendedor', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                    "proyecto": datos_gen.get('proyecto', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                    "fecha": fecha,
                    "revision": revision,
                    "total": total_calculado,
                    "moneda": moneda,
                    "_id": cot.get('_id', ''),
                    "tiene_desglose": True,  # Cotizaciones de BD tienen desglose
                    "es_antigua": False
                })
        else:
            print(f"[TODAS-COTIZACIONES] Error: {resultado_db.get('error')}")

        # AGREGAR COTIZACIONES ANTIGUAS DE GOOGLE DRIVE (que no están en BD)
        if not resultado_pdfs.get("error"):
            pdfs_antiguos = resultado_pdfs.get("resultados", [])
            print(f"[TODAS-COTIZACIONES] Encontrados {len(pdfs_antiguos)} PDFs totales")

            for pdf in pdfs_antiguos:
                numero_pdf = pdf.get('numero_cotizacion', 'N/A')

                # Solo agregar si no está ya en la lista (evitar duplicados)
                if numero_pdf not in numeros_vistos and numero_pdf != 'N/A':
                    # Extraer metadatos del nombre (formato: CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO)
                    import re
                    nombre_partes = numero_pdf.split('-')

                    cliente = nombre_partes[0] if len(nombre_partes) > 0 else 'N/A'
                    vendedor = nombre_partes[3] if len(nombre_partes) > 3 else 'N/A'
                    proyecto = '-'.join(nombre_partes[6:]) if len(nombre_partes) > 6 else 'N/A'

                    # Extraer revisión
                    match_revision = re.search(r'-R(\d+)-', numero_pdf)
                    revision = int(match_revision.group(1)) if match_revision else 1

                    # Fecha de modificación del archivo
                    fecha_pdf = pdf.get('fecha_creacion', pdf.get('fecha_modificacion', 'N/A'))

                    cotizaciones.append({
                        "numero": numero_pdf,
                        "cliente": cliente,
                        "vendedor": vendedor,
                        "proyecto": proyecto,
                        "fecha": fecha_pdf,
                        "revision": revision,
                        "total": 0,  # No hay datos de total en PDFs antiguos
                        "moneda": "N/A",
                        "_id": '',
                        "tiene_desglose": False,  # PDFs antiguos NO tienen desglose
                        "es_antigua": True  # Marcar como antigua
                    })

            print(f"[TODAS-COTIZACIONES] Total final: {len(cotizaciones)} cotizaciones (BD + antiguas)")

        # APLICAR FILTROS antes de paginación
        if any([filtro_numero, filtro_cliente, filtro_vendedor, filtro_proyecto,
                filtro_fecha_desde, filtro_fecha_hasta, filtro_revision, filtro_moneda, filtro_tipo]):

            cotizaciones_filtradas = []

            for cot in cotizaciones:
                # Aplicar cada filtro
                cumple_filtros = True

                # Filtro por número (búsqueda parcial, case-insensitive)
                if filtro_numero:
                    if filtro_numero.lower() not in cot.get('numero', '').lower():
                        cumple_filtros = False

                # Filtro por cliente (búsqueda parcial, case-insensitive)
                if filtro_cliente and cumple_filtros:
                    if filtro_cliente.lower() not in cot.get('cliente', '').lower():
                        cumple_filtros = False

                # Filtro por vendedor (búsqueda parcial, case-insensitive)
                if filtro_vendedor and cumple_filtros:
                    if filtro_vendedor.lower() not in cot.get('vendedor', '').lower():
                        cumple_filtros = False

                # Filtro por proyecto (búsqueda parcial, case-insensitive)
                if filtro_proyecto and cumple_filtros:
                    if filtro_proyecto.lower() not in cot.get('proyecto', '').lower():
                        cumple_filtros = False

                # Filtro por fecha desde
                if filtro_fecha_desde and cumple_filtros:
                    fecha_cot = cot.get('fecha', 'N/A')
                    if fecha_cot != 'N/A':
                        try:
                            from datetime import datetime
                            # Intentar parsear la fecha de la cotización
                            if len(fecha_cot) == 10:  # Formato YYYY-MM-DD
                                fecha_cot_dt = datetime.strptime(fecha_cot, '%Y-%m-%d')
                            else:
                                fecha_cot_dt = datetime.strptime(fecha_cot[:10], '%Y-%m-%d')

                            fecha_desde_dt = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')

                            if fecha_cot_dt < fecha_desde_dt:
                                cumple_filtros = False
                        except:
                            # Si no se puede parsear, no cumple el filtro
                            cumple_filtros = False

                # Filtro por fecha hasta
                if filtro_fecha_hasta and cumple_filtros:
                    fecha_cot = cot.get('fecha', 'N/A')
                    if fecha_cot != 'N/A':
                        try:
                            from datetime import datetime
                            # Intentar parsear la fecha de la cotización
                            if len(fecha_cot) == 10:  # Formato YYYY-MM-DD
                                fecha_cot_dt = datetime.strptime(fecha_cot, '%Y-%m-%d')
                            else:
                                fecha_cot_dt = datetime.strptime(fecha_cot[:10], '%Y-%m-%d')

                            fecha_hasta_dt = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')

                            if fecha_cot_dt > fecha_hasta_dt:
                                cumple_filtros = False
                        except:
                            # Si no se puede parsear, no cumple el filtro
                            cumple_filtros = False

                # Filtro por revisión
                if filtro_revision and cumple_filtros:
                    revision_cot = cot.get('revision', 1)

                    if filtro_revision == '5+':
                        if revision_cot < 5:
                            cumple_filtros = False
                    else:
                        try:
                            if int(revision_cot) != int(filtro_revision):
                                cumple_filtros = False
                        except:
                            cumple_filtros = False

                # Filtro por moneda
                if filtro_moneda and cumple_filtros:
                    moneda_cot = cot.get('moneda', 'N/A')
                    if moneda_cot != filtro_moneda:
                        cumple_filtros = False

                # Filtro por tipo (nueva/antigua)
                if filtro_tipo and cumple_filtros:
                    es_antigua = cot.get('es_antigua', False)

                    if filtro_tipo == 'nueva' and es_antigua:
                        cumple_filtros = False
                    elif filtro_tipo == 'antigua' and not es_antigua:
                        cumple_filtros = False

                # Si cumple todos los filtros, agregar a resultados
                if cumple_filtros:
                    cotizaciones_filtradas.append(cot)

            # Reemplazar cotizaciones con las filtradas
            cotizaciones = cotizaciones_filtradas
            print(f"[TODAS-COTIZACIONES] Después de filtros: {len(cotizaciones)} cotizaciones")

        # APLICAR PAGINACIÓN
        total_cotizaciones = len(cotizaciones)
        total_pages = (total_cotizaciones + page_size - 1) // page_size  # Redondeo hacia arriba

        # Validar página solicitada
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages

        # Calcular índices para el slice
        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        # Obtener cotizaciones de la página actual
        cotizaciones_pagina = cotizaciones[start_index:end_index]

        print(f"[TODAS-COTIZACIONES] Mostrando {len(cotizaciones_pagina)} de {total_cotizaciones} (página {page}/{total_pages})")

        return render_template(
            "todas_cotizaciones.html",
            cotizaciones=cotizaciones_pagina,
            vendedor=session.get('vendedor'),
            # Información de paginación
            page=page,
            total_pages=total_pages,
            total_cotizaciones=total_cotizaciones,
            page_size=page_size
        )

    except Exception as e:
        print(f"[TODAS-COTIZACIONES] Error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error al cargar cotizaciones: {str(e)}", 500

@app.route("/diagnostico-tabla-datos")
def diagnostico_tabla_datos():
    """Diagnóstico de datos de tabla sin requerimiento de login - Para debugging"""
    import traceback
    import json

    try:
        # Obtener cotizaciones
        resultado_db = db_manager.buscar_cotizaciones("", 1, 10000)

        if resultado_db.get("error"):
            return jsonify({
                "error": True,
                "mensaje": str(resultado_db.get("error")),
                "modo_conexion": "Offline (JSON)" if db_manager.modo_offline else "Online (Supabase)"
            })

        cotizaciones_raw = resultado_db.get("resultados", [])

        # Analizar primeras 3 cotizaciones
        analisis = []
        for idx, cot in enumerate(cotizaciones_raw[:3]):
            datos_gen = cot.get('datosGenerales', {})
            items = cot.get('items', [])

            # Calcular total
            total_calc = 0.0
            items_info = []
            for item in items[:3]:
                if isinstance(item, dict):
                    subtotal = safe_float(item.get('subtotal', 0))
                    precio = safe_float(item.get('precio_unitario') or item.get('precio', 0))
                    cantidad = safe_float(item.get('cantidad', 0))

                    if subtotal:
                        total_calc += subtotal
                        items_info.append(f"subtotal:{subtotal}")
                    else:
                        item_total = precio * cantidad
                        total_calc += item_total
                        items_info.append(f"precio:{precio}*cant:{cantidad}={item_total}")

            analisis.append({
                "numero": cot.get('numeroCotizacion', 'N/A'),
                "fecha": datos_gen.get('fecha', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                "cliente": datos_gen.get('cliente', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                "vendedor": datos_gen.get('vendedor', 'N/A') if isinstance(datos_gen, dict) else 'N/A',
                "total_items": len(items),
                "total_calculado": total_calc,
                "items_ejemplo": items_info,
                "keys_raiz": list(cot.keys()),
                "keys_datosGenerales": list(datos_gen.keys()) if isinstance(datos_gen, dict) else "NO_ES_DICT"
            })

        return jsonify({
            "success": True,
            "modo_conexion": "Offline (JSON)" if db_manager.modo_offline else "Online (Supabase)",
            "total_cotizaciones": len(cotizaciones_raw),
            "primeras_3": analisis
        })

    except Exception as e:
        return jsonify({
            "error": True,
            "mensaje": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route("/debug-tabla-cotizaciones")
def debug_tabla_cotizaciones():
    """Página de diagnóstico para ver estructura de datos - Accesible desde móvil"""
    if 'vendedor' not in session:
        return redirect(url_for('login'))

    import traceback

    try:
        # Obtener cotizaciones
        resultado_db = db_manager.buscar_cotizaciones("", 1, 10000)

        debug_info = {
            "total_encontradas": 0,
            "tiene_error": False,
            "error_mensaje": None,
            "modo_conexion": "Offline (JSON)" if db_manager.modo_offline else "Online (Supabase)",
            "ejemplos": []
        }

        if resultado_db.get("error"):
            debug_info["tiene_error"] = True
            debug_info["error_mensaje"] = str(resultado_db.get("error"))
        else:
            cotizaciones_raw = resultado_db.get("resultados", [])
            debug_info["total_encontradas"] = len(cotizaciones_raw)

            # Tomar las primeras 3 cotizaciones como ejemplo
            for idx, cot in enumerate(cotizaciones_raw[:3]):
                try:
                    datos_gen = cot.get('datosGenerales', {})
                    items = cot.get('items', [])

                    # Analizar items
                    items_analisis = []
                    total_calculado = 0.0
                    for item_idx, item in enumerate(items[:3]):  # Solo primeros 3 items
                        try:
                            if isinstance(item, dict):
                                subtotal = item.get('subtotal', 0)
                                precio = item.get('precio_unitario') or item.get('precio', 0)
                                cantidad = item.get('cantidad', 0)

                                if subtotal:
                                    item_total = safe_float(subtotal)
                                else:
                                    item_total = safe_float(precio) * safe_float(cantidad)

                                total_calculado += item_total

                                items_analisis.append({
                                    "index": item_idx,
                                    "keys": list(item.keys()),
                                    "subtotal": str(subtotal),
                                    "precio": str(precio),
                                    "cantidad": str(cantidad),
                                    "calculado": float(item_total)
                                })
                        except Exception as item_error:
                            items_analisis.append({
                                "index": item_idx,
                                "error": str(item_error)
                            })

                    ejemplo = {
                        "index": idx,
                        "numero_cotizacion": str(cot.get('numeroCotizacion', 'N/A')),
                        "keys_raiz": [str(k) for k in cot.keys()],
                        "datosGenerales": {
                            "es_dict": isinstance(datos_gen, dict),
                            "keys": [str(k) for k in datos_gen.keys()] if isinstance(datos_gen, dict) else "NO ES DICT",
                            "fecha": str(datos_gen.get('fecha', 'N/A')) if isinstance(datos_gen, dict) else "N/A",
                            "cliente": str(datos_gen.get('cliente', 'N/A')) if isinstance(datos_gen, dict) else "N/A",
                            "vendedor": str(datos_gen.get('vendedor', 'N/A')) if isinstance(datos_gen, dict) else "N/A"
                        },
                        "items": {
                            "total_items": len(items),
                            "es_lista": isinstance(items, list),
                            "items_analizados": items_analisis,
                            "total_calculado": float(total_calculado)
                        },
                        "condiciones": {
                            "existe": 'condiciones' in cot,
                            "contenido": str(cot.get('condiciones', 'NO EXISTE'))
                        }
                    }

                    debug_info["ejemplos"].append(ejemplo)
                except Exception as cot_error:
                    debug_info["ejemplos"].append({
                        "index": idx,
                        "error": str(cot_error)
                    })

        # Renderizar template de diagnóstico
        return render_template("debug_tabla.html", debug=debug_info)

    except Exception as e:
        error_trace = traceback.format_exc()
        return f"""
        <html>
        <head><title>Error de Diagnóstico</title></head>
        <body style="font-family: monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4;">
            <h1 style="color: #f48771;">❌ Error en Diagnóstico</h1>
            <h2>Error:</h2>
            <pre style="background: #252526; padding: 15px; border-radius: 5px;">{str(e)}</pre>
            <h2>Stack Trace:</h2>
            <pre style="background: #252526; padding: 15px; border-radius: 5px;">{error_trace}</pre>
            <a href="/todas-cotizaciones" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #0e639c; color: white; text-decoration: none; border-radius: 4px;">← Volver</a>
        </body>
        </html>
        """, 500

@app.route("/ver/<path:item_id>")
def ver_item(item_id):
    """Ver cotización específica (acepta caracteres especiales)"""
    try:
        # Decodificar URL para manejar caracteres especiales
        from urllib.parse import unquote
        item_id = unquote(item_id)
        
        print(f"Viendo cotizacion: '{item_id}'")
        
        resultado = db_manager.obtener_cotizacion(item_id)
        
        if "error" in resultado:
            return handle_error_response(resultado["error"], item_id)
        
        if not resultado["encontrado"]:
            return handle_not_found_response(item_id)
        
        # Respuesta según el tipo de petición
        if is_json_request():
            return jsonify(resultado)
        else:
            from flask import render_template
            return render_template("ver_cotizacion.html", cotizacion=resultado["item"])
            
    except Exception as e:
        print(f"Error al ver cotizacion: {e}")
        import traceback
        traceback.print_exc()
        return handle_error_response(str(e), item_id)

@app.route("/listar")
def listar_cotizaciones():
    """Listar todas las cotizaciones recientes con paginación"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", int(os.getenv('DEFAULT_PAGE_SIZE', '20')), type=int)
        
        # Limitar per_page al máximo configurado
        max_per_page = int(os.getenv('MAX_RESULTS_PER_PAGE', '50'))
        per_page = min(per_page, max_per_page)
        
        resultado = db_manager.obtener_todas_cotizaciones(page, per_page)
        
        if "error" in resultado:
            return jsonify({"error": resultado["error"]}), 500
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"Error al listar: {e}")
        return jsonify({"error": "Error del servidor"}), 500
    
    

# ============================================
# GENERACIÓN DE TEXTO IA
# ============================================

@app.route("/api/generar-texto-ia", methods=["POST"])
def generar_texto_ia():
    """
    Genera texto introductorio personalizado usando Claude AI.

    Body JSON:
        {
            "numeroCotizacion": "(opcional) para buscar texto guardado previamente",
            "datosGenerales": {...},
            "items": [...],
            "condiciones": {...},
            "revision": "1",
            "cambiosRevision": "(opcional) descripción de cambios vs rev anterior"
        }

    Returns:
        {
            "success": true,
            "texto": "texto generado en formato HTML simple",
            "fuente": "ia" | "generico",
            "textoGuardado": "texto previamente guardado en BD (opcional, para fallback)"
        }
    """
    try:
        datos = request.get_json()
        if not datos:
            return jsonify({"success": False, "error": "No se recibieron datos"}), 400

        # Buscar texto guardado previamente en la cotización
        texto_guardado = None
        numero_cotizacion = datos.get('numeroCotizacion', '').strip()
        if numero_cotizacion:
            try:
                resultado_bd = db_manager.obtener_cotizacion(numero_cotizacion)
                if resultado_bd.get('encontrado'):
                    item = resultado_bd['item']
                    texto_guardado = (
                        item.get('datosGenerales', {}).get('textoIntroductorio', '') or
                        item.get('textoIntroductorio', '') or
                        None
                    )
                    if texto_guardado:
                        print(f"[IA] Texto guardado encontrado en BD ({len(texto_guardado)} chars)")
            except Exception as e:
                print(f"[IA] Error buscando texto guardado: {e}")

        # Intentar usar Claude si está configurado
        api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
        # Solo usar IA si la API key está configurada y no es placeholder
        if api_key and not api_key.endswith('...') and api_key.startswith('sk-ant-'):
            import anthropic

            datos_generales = datos.get('datosGenerales', {})
            items = datos.get('items', [])
            condiciones = datos.get('condiciones', {})
            revision = datos.get('revision', '1')
            cambios = datos.get('cambiosRevision', '')

            cliente = datos_generales.get('cliente', 'Cliente')
            proyecto = datos_generales.get('proyecto', 'su proyecto')
            vendedor = datos_generales.get('vendedor', 'CWS Company')

            # Construir resumen de items
            items_resumen = ""
            for i, item in enumerate(items[:10]):  # max 10 items para no exceder tokens
                desc = (item.get('descripcion') or 'Sin descripción')[:100]
                precio = item.get('total') or item.get('totalItem') or 'N/A'
                uom = item.get('uom', '')
                cant = item.get('cantidad', '')
                items_resumen += f"- Item {i+1}: {desc} | {cant} {uom} | ${precio}\n"

            moneda = condiciones.get('moneda', 'MXN')

            # System prompt
            system_prompt = (
                "Eres un cotizador profesional mexicano. Generas textos introductorios "
                "para PDFs de cotizaciones. Sé MUY conciso — escribe 30% más breve de lo "
                "que normalmente harías. Profesional y cálido. "
                "Escribe en español formal. NO uses markdown. "
                "Formato: texto plano con saltos de línea simples. "
                "Máximo 2 párrafos breves. Ve directo al punto, sin rodeos."
            )

            # User prompt
            user_prompt = f"""Genera el texto introductorio para un PDF de cotización con estos datos:

Cliente: {cliente}
Proyecto: {proyecto}
Vendedor: {vendedor}
Moneda: {moneda}
Revisión: R{revision}

Resumen de ítems cotizados:
{items_resumen if items_resumen else 'No se especificaron ítems'}"""

            if cambios and revision != '1':
                user_prompt += f"\nCambios respecto a revisión anterior:\n{cambios}\nExplica estos cambios de forma profesional.\n"

            user_prompt += "\nEscribe un texto introductorio de 1-2 párrafos breves (30% más corto de lo habitual) que presente la cotización. Ve directo al punto."

            try:
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=400,
                    temperature=0.7,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                texto_generado = message.content[0].text
                print(f"[IA] Texto generado: {len(texto_generado)} caracteres")

                return jsonify({
                    "success": True,
                    "texto": texto_generado,
                    "fuente": "ia",
                    "textoGuardado": texto_guardado or texto_generado
                }), 200

            except Exception as ia_error:
                print(f"[IA] Error llamando a Claude: {str(ia_error)}")
                # Fallback a texto genérico
        else:
            print("[IA] ANTHROPIC_API_KEY no configurada - usando texto genérico")

        # Texto genérico (fallback)
        datos_generales = datos.get('datosGenerales', {})
        cliente = datos_generales.get('cliente', 'Cliente')
        proyecto = datos_generales.get('proyecto', 'su proyecto')

        texto_generico = (
            f"Estimado {cliente},\n\n"
            f"CWS Company presenta esta propuesta económica "
            f"para {proyecto}, "
            f"equilibrando calidad, funcionalidad y costo.\n\n"
            f"Quedamos a la espera de su respuesta."
        )

        return jsonify({
            "success": True,
            "texto": texto_generico,
            "fuente": "generico",
            "textoGuardado": texto_guardado or None
        }), 200

    except Exception as e:
        error_msg = str(e)
        print(f"[IA] Error en generar-texto-ia: {error_msg}")
        return jsonify({"success": False, "error": error_msg, "textoGuardado": None}), 500


# ============================================
# GENERACIÓN DE PDF
# ============================================

@app.route("/generar_pdf", methods=["POST"])
def generar_pdf():
    """Genera PDF de la cotización usando el formato CWS oficial"""
    # Verificar si hay generadores de PDF disponibles
    if not WEASYPRINT_AVAILABLE and not REPORTLAB_AVAILABLE:
        return jsonify({
            "error": "Ningún generador de PDF disponible",
            "mensaje": "Para habilitar la generación de PDF, instala ReportLab o WeasyPrint",
            "solucion": "Ejecuta: pip install reportlab"
        }), 503
    
    try:
        datos = request.get_json()
        numero_cotizacion = datos.get('numeroCotizacion')
        texto_personalizado = datos.get('textoPersonalizado', None)

        if not numero_cotizacion:
            return jsonify({"error": "Número de cotización requerido"}), 400

        # Buscar la cotización en la base de datos
        resultado = db_manager.obtener_cotizacion(numero_cotizacion)
        
        if not resultado["encontrado"]:
            mensaje_detallado = resultado.get("mensaje", "Sin detalles")
            return jsonify({
                "error": f"Cotización '{numero_cotizacion}' no encontrada",
                "detalle": mensaje_detallado,
                "numero_buscado": numero_cotizacion,
                "modo_busqueda": resultado.get("modo", "desconocido")
            }), 404
        
        cotizacion = resultado["item"]
        
        # Extraer datos para el template
        datos_generales = cotizacion.get('datosGenerales', {})
        items = cotizacion.get('items', [])
        condiciones = cotizacion.get('condiciones', {})
        
        # Calcular totales
        subtotal = sum(float(item.get('total', 0)) for item in items)
        iva = subtotal * 0.16
        total = subtotal + iva
        
        # Preparar datos para el template
        template_data = {
            # Datos generales
            'numeroCotizacion': numero_cotizacion,
            'fechaActual': datetime.datetime.now().strftime('%Y-%m-%d'),
            'cliente': datos_generales.get('cliente', ''),
            'atencionA': datos_generales.get('atencionA', ''),
            'contacto': datos_generales.get('contacto', ''),
            'proyecto': datos_generales.get('proyecto', ''),
            'vendedor': datos_generales.get('vendedor', ''),
            'revision': datos_generales.get('revision', '1'),
            'actualizacionRevision': datos_generales.get('actualizacionRevision', ''),
            
            # Items
            'items': items,
            
            # Condiciones
            'moneda': condiciones.get('moneda', 'MXN'),
            'tipoCambio': condiciones.get('tipoCambio', ''),
            'tiempoEntrega': condiciones.get('tiempoEntrega', ''),
            'entregaEn': condiciones.get('entregaEn', ''),
            'terminos': condiciones.get('terminos') or condiciones.get('condicionesPago', ''),
            'comentarios': condiciones.get('comentarios') or condiciones.get('comentariosAdicionales', ''),
            
            # Totales
            'subtotal': f"{subtotal:.2f}",
            'iva': f"{iva:.2f}",
            'total': f"{total:.2f}",
            
            # Logo path for PDF (solo para WeasyPrint)
            'logo_path': 'static/logo.png'
        }
        
        print(f"Generando PDF para: {numero_cotizacion}")
        print(f"Items count: {len(items)}")
        print(f"Cliente: {datos_generales.get('cliente', 'No encontrado')}")
        
        # Intentar con ReportLab primero (más estable)
        if REPORTLAB_AVAILABLE:
            print("Generando PDF con ReportLab")
            pdf_data = generar_pdf_reportlab(cotizacion, texto_personalizado=texto_personalizado)
            pdf_buffer = io.BytesIO(pdf_data)
            
        elif WEASYPRINT_AVAILABLE:
            print("Generando PDF con WeasyPrint (fallback)")
            # Lógica WeasyPrint como fallback
            import tempfile
            
            html_content = render_template('formato_pdf_cws.html', **template_data)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_html_path = f.name
            
            html_obj = weasyprint.HTML(filename=temp_html_path)
            pdf_file = html_obj.write_pdf()
            os.unlink(temp_html_path)
            
            pdf_buffer = io.BytesIO(pdf_file)
        else:
            raise Exception("Ningún generador de PDF disponible")
        
        pdf_buffer.seek(0)
        filename = f"{numero_cotizacion.replace('/', '_').replace('-', '_')}.pdf"
        
        print(f"PDF generado exitosamente: {filename}")
        
        # IMPORTANTE: Almacenar el PDF en el sistema antes de enviarlo
        if pdf_manager:
            try:
                pdf_content = pdf_buffer.getvalue()  # Obtener contenido binario
                resultado_almacenamiento = pdf_manager.almacenar_pdf_nuevo(
                    pdf_content=pdf_content,
                    cotizacion_data=cotizacion
                )
                
                if resultado_almacenamiento.get("success"):
                    print(f"PDF almacenado exitosamente: {resultado_almacenamiento.get('mensaje')}")
                    print(f"Ruta: {resultado_almacenamiento.get('ruta')}")
                else:
                    print(f"Error almacenando PDF: {resultado_almacenamiento.get('error')}")
                    
            except Exception as e:
                print(f"Error en almacenamiento de PDF: {e}")
                # No fallar la descarga por error de almacenamiento

        # Guardar texto introductorio en la cotización para futuras referencias
        if texto_personalizado and texto_personalizado.strip():
            try:
                if 'datosGenerales' not in cotizacion:
                    cotizacion['datosGenerales'] = {}
                cotizacion['datosGenerales']['textoIntroductorio'] = texto_personalizado
                cotizacion['textoIntroductorio'] = texto_personalizado
                resultado_texto = db_manager.guardar_cotizacion(cotizacion)
                if resultado_texto.get('success'):
                    print(f"Texto introductorio guardado en cotización ({len(texto_personalizado)} chars)")
                else:
                    print(f"Error guardando texto introductorio: {resultado_texto.get('error')}")
            except Exception as e:
                print(f"Error guardando texto introductorio: {e}")

        # Regresar el buffer al inicio para la descarga
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Error generando PDF",
            "detalle": str(e)
        }), 500

# ============================================
# RUTAS PARA GESTIÓN DE PDFs
# ============================================

@app.route("/buscar_pdfs", methods=["POST"])
def buscar_pdfs():
    """Buscar PDFs almacenados (resultado principal de búsqueda)"""
    try:
        datos = request.get_json()
        query = datos.get("query", "")
        page = datos.get("page", 1)
        per_page = datos.get("per_page", int(os.getenv('DEFAULT_PAGE_SIZE', '20')))
        
        print(f"Buscando PDFs: '{query}' (pagina {page})")
        
        # Buscar PDFs usando el PDF Manager
        resultado = pdf_manager.buscar_pdfs(query, page, per_page)
        
        if "error" in resultado:
            return jsonify({"error": resultado["error"]}), 500
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"Error en búsqueda de PDFs: {e}")
        return jsonify({"error": "Error al buscar PDFs"}), 500

@app.route("/pdf/<path:numero_cotizacion>")
def servir_pdf(numero_cotizacion):
    """Servir PDF almacenado para visualización"""
    try:
        from urllib.parse import unquote
        numero_original = numero_cotizacion
        numero_cotizacion = unquote(numero_cotizacion)

        # BUGFIX: Eliminar trailing slash que causa problemas con nombres de archivo
        numero_cotizacion = numero_cotizacion.rstrip('/')

        print(f"PDF: Sirviendo PDF:")
        print(f"   URL original: '{numero_original}'")
        print(f"   Después de unquote: '{numero_cotizacion}'")
        
        # Si tiene espacios, intentar reemplazar con guiones
        if ' ' in numero_cotizacion:
            numero_alternativo = numero_cotizacion.replace(' ', '-')
            print(f"   Variación con guiones: '{numero_alternativo}'")
        else:
            numero_alternativo = None
        
        # Obtener información del PDF - intentar versión principal primero
        resultado = pdf_manager.obtener_pdf(numero_cotizacion)
        
        # Si no lo encuentra y hay una versión alternativa, intentar con esa
        if not resultado.get("encontrado", False) and numero_alternativo:
            print(f"   No encontrado con espacios, intentando con guiones...")
            resultado = pdf_manager.obtener_pdf(numero_alternativo)
            if resultado.get("encontrado", False):
                numero_cotizacion = numero_alternativo  # Usar la versión que funcionó
        
        # Verificar si el PDF fue encontrado. Si no, intentar regenerar al vuelo.
        # IMPORTANTE: verificar "encontrado" ANTES de "error" porque _obtener_pdf_offline
        # devuelve {"encontrado": False, "error": "no encontrado..."} para ausencia normal
        # (no es un fallo de sistema). El bloque de regeneración al vuelo debe ser alcanzable.
        if not resultado.get("encontrado", False):
            # PDF no existe en Storage — intentar generarlo al vuelo desde la cotización
            print(f"PDF: No encontrado en Storage, intentando generar al vuelo para '{numero_cotizacion}'")
            if not (REPORTLAB_AVAILABLE or WEASYPRINT_AVAILABLE):
                return jsonify({"error": f"PDF '{numero_cotizacion}' no encontrado y no hay generador disponible"}), 404

            cot_resultado = db_manager.obtener_cotizacion(numero_cotizacion)
            if not cot_resultado.get('encontrado'):
                return jsonify({"error": f"PDF '{numero_cotizacion}' no encontrado en Storage ni en base de datos"}), 404

            cotizacion = cot_resultado["item"]
            try:
                pdf_data = generar_pdf_reportlab(cotizacion) if REPORTLAB_AVAILABLE else None
                if pdf_data is None:
                    return jsonify({"error": "Error generando PDF al vuelo"}), 500

                # Almacenar en Storage para futuras solicitudes
                if pdf_manager:
                    try:
                        pdf_manager.almacenar_pdf_nuevo(pdf_content=pdf_data, cotizacion_data=cotizacion)
                    except Exception as store_err:
                        print(f"PDF: Advertencia — no se pudo almacenar en Storage: {store_err}")

                from io import BytesIO
                buf = BytesIO(pdf_data)
                buf.seek(0)
                return send_file(buf, mimetype='application/pdf', as_attachment=False,
                                 download_name=f"{numero_cotizacion}.pdf")
            except Exception as gen_err:
                print(f"PDF: Error generando PDF al vuelo: {gen_err}")
                return jsonify({"error": f"Error generando PDF: {str(gen_err)}"}), 500
        
        # Servir el archivo PDF
        ruta_completa = resultado["ruta_completa"]
        tipo_fuente = resultado.get("tipo", "local")
        
        # Si es un PDF de Supabase Storage, descargar y servir en lugar de redirigir
        if (tipo_fuente in ["supabase_storage"] or 
            ruta_completa.startswith("https://")):
            
            fuente_nombre = {
                "supabase_storage": "Supabase Storage",
                # Cloudinary eliminado
            }.get(tipo_fuente, "URL directa")
            
            print(f"PDF: Sirviendo PDF de {fuente_nombre}: {numero_cotizacion}")
            print(f"   URL: {ruta_completa}")
            
            # Verificar que la URL no esté vacía
            if not ruta_completa or ruta_completa.strip() == "":
                print(f"ERROR: URL vacía para PDF {numero_cotizacion}")
                return jsonify({"error": "URL del PDF no disponible"}), 500
            
            # SOLUCIÓN: Descargar desde Supabase y servir directamente
            try:
                import requests
                from io import BytesIO
                
                print(f"   Descargando PDF desde: {ruta_completa}")
                response = requests.get(ruta_completa, timeout=30)
                
                if response.status_code == 200:
                    print(f"   PDF descargado exitosamente ({len(response.content)} bytes)")
                    
                    # Verificar que es un PDF válido
                    if response.content.startswith(b'%PDF'):
                        pdf_buffer = BytesIO(response.content)
                        pdf_buffer.seek(0)
                        
                        return send_file(
                            pdf_buffer,
                            mimetype='application/pdf',
                            as_attachment=False,
                            download_name=f"{numero_cotizacion}.pdf"
                        )
                    else:
                        print(f"ERROR: Contenido descargado no es un PDF válido")
                        return jsonify({"error": "Archivo descargado no es un PDF válido"}), 500
                else:
                    print(f"ERROR: Descarga falló con código {response.status_code}")
                    return jsonify({"error": f"Error descargando PDF (código {response.status_code})"}), 500
                    
            except Exception as download_error:
                print(f"ERROR: Excepción descargando PDF: {download_error}")
                return jsonify({"error": f"Error descargando PDF: {str(download_error)}"}), 500
        
        # Si es un PDF de Google Drive, descargar y servir
        elif ruta_completa.startswith("gdrive://"):
            drive_id = resultado.get("drive_id")
            if not drive_id:
                return jsonify({"error": "ID de Google Drive no encontrado"}), 500
            
            print(f"PDF: Sirviendo PDF desde Google Drive: {numero_cotizacion} (ID: {drive_id})")
            
            # Descargar PDF desde Google Drive usando ID (más eficiente)
            if drive_id:
                contenido_pdf = pdf_manager.drive_client.obtener_pdf_por_id(drive_id, numero_cotizacion)
            else:
                # Fallback: buscar por nombre
                contenido_pdf = pdf_manager.drive_client.obtener_pdf(numero_cotizacion)
            
            if not contenido_pdf:
                return jsonify({
                    "error": "No se pudo descargar PDF desde Google Drive",
                    "drive_id": drive_id,
                    "numero_cotizacion": numero_cotizacion
                }), 500
            
            # Crear buffer con el contenido
            from io import BytesIO
            pdf_buffer = BytesIO(contenido_pdf)
            pdf_buffer.seek(0)
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f"{numero_cotizacion}.pdf"
            )
        
        # Si es un archivo local
        else:
            return send_file(
                ruta_completa,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f"{numero_cotizacion}.pdf"
            )
        
    except Exception as e:
        print(f"Error sirviendo PDF: {e}")
        return jsonify({"error": f"Error sirviendo PDF: {str(e)}"}), 500

@app.route("/desglose/<path:numero_cotizacion>")
def ver_desglose(numero_cotizacion):
    """Ver desglose detallado de cotización - MANEJO INTELIGENTE"""
    try:
        from urllib.parse import unquote
        numero_cotizacion = unquote(numero_cotizacion)
        
        print(f"[DESGLOSE] Viendo: '{numero_cotizacion}'")
        
        # PASO 1: Intentar obtener cotización completa (con datos de desglose)
        resultado_cotizacion = db_manager.obtener_cotizacion(numero_cotizacion)
        
        if resultado_cotizacion.get("encontrado"):
            # Tenemos datos completos - mostrar desglose normal
            cotizacion = resultado_cotizacion["item"]
            print(f"[DESGLOSE] Cotización encontrada en DB - mostrando desglose completo")

            # Asegurar que la cotización tenga numeroCotizacion para el botón Nueva Revisión
            if not cotizacion.get('numeroCotizacion'):
                cotizacion['numeroCotizacion'] = numero_cotizacion
                print(f"[DESGLOSE] Añadido numeroCotizacion faltante: {numero_cotizacion}")

            # Asegurar que exista datosGenerales (evitar errores de template)
            if not cotizacion.get('datosGenerales'):
                cotizacion['datosGenerales'] = {}
                print(f"[DESGLOSE] Inicializado datosGenerales vacío")

            # Asegurar que exista condiciones (evitar errores de template)
            if not cotizacion.get('condiciones'):
                cotizacion['condiciones'] = {'moneda': 'MXN'}
                print(f"[DESGLOSE] Inicializado condiciones con valores por defecto")

            # CALCULAR TOTALES para asegurar que se muestren correctamente
            if cotizacion.get('items') and isinstance(cotizacion['items'], list):
                subtotal_calculado = 0.0
                for item in cotizacion['items']:
                    try:
                        # Asegurar que item es un diccionario
                        if not isinstance(item, dict):
                            print(f"[DESGLOSE] ADVERTENCIA: Item no es diccionario, saltando")
                            continue

                        # Calcular total del item si no existe
                        if not item.get('total') and not item.get('subtotal'):
                            # Intentar obtener precio de cualquier campo
                            precio_raw = item.get('precio_unitario') or item.get('precio') or item.get('costoUnidad') or 0
                            cantidad_raw = item.get('cantidad') or 0

                            # Convertir a float de manera segura
                            precio = float(precio_raw) if precio_raw else 0.0
                            cantidad = float(cantidad_raw) if cantidad_raw else 0.0

                            item['total'] = float(precio * cantidad)
                            print(f"[DESGLOSE] Item '{item.get('descripcion', 'N/A')}': calculado total = {item['total']}")

                        # Sumar al subtotal general - convertir a float de manera segura
                        total_raw = item.get('total') or item.get('subtotal') or 0
                        item_total = float(total_raw) if total_raw else 0.0
                        subtotal_calculado += item_total
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"[DESGLOSE] ERROR calculando item '{item.get('descripcion', 'N/A') if isinstance(item, dict) else 'UNKNOWN'}': {e}")
                        continue

                # Agregar totales calculados a la cotización como floats
                cotizacion['subtotal_calculado'] = float(subtotal_calculado)
                cotizacion['iva_calculado'] = float(subtotal_calculado * 0.16)
                cotizacion['total_calculado'] = float(subtotal_calculado * 1.16)
                print(f"[DESGLOSE] Totales calculados - Subtotal: {cotizacion['subtotal_calculado']}, IVA: {cotizacion['iva_calculado']}, Total: {cotizacion['total_calculado']}")
            else:
                # No hay items o no es lista válida - inicializar totales en 0
                cotizacion['subtotal_calculado'] = 0.0
                cotizacion['iva_calculado'] = 0.0
                cotizacion['total_calculado'] = 0.0
                if not cotizacion.get('items'):
                    cotizacion['items'] = []
                print(f"[DESGLOSE] No hay items válidos, totales en 0")

            print(f"[DESGLOSE] Cotización con numeroCotizacion: {cotizacion.get('numeroCotizacion', 'N/A')}")
            from flask import render_template
            return render_template("ver_cotizacion.html", cotizacion=cotizacion)
        
        # PASO 2: No hay datos completos, verificar si existe PDF
        print(f"[DESGLOSE] Cotización no en DB, verificando PDF...")
        resultado_pdf = pdf_manager.obtener_pdf(numero_cotizacion)
        
        if resultado_pdf.get("encontrado"):
            registro_pdf = resultado_pdf.get("registro", {})
            tiene_desglose = registro_pdf.get("tiene_desglose", False)
            
            if tiene_desglose:
                # PDF de cotización generada por la app, pero datos perdidos
                print(f"[DESGLOSE] PDF encontrado (nueva cotización) - datos perdidos en contenedor")
                return render_template_string("""
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Datos de Cotización No Disponibles - CWS</title>
                    <style>
                        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                               background: #f8f9fa; margin: 0; padding: 20px; }
                        .container { max-width: 600px; margin: 50px auto; background: white; 
                                   border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 30px; }
                        .header { text-align: center; margin-bottom: 30px; }
                        .logo { color: #2C5282; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
                        .mensaje { background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; 
                                 border-radius: 8px; margin: 20px 0; }
                        .info { background: #e3f2fd; border: 1px solid #bbdefb; padding: 15px; 
                              border-radius: 8px; margin: 15px 0; }
                        .buttons { display: flex; gap: 15px; justify-content: center; margin-top: 30px; }
                        .btn { padding: 12px 24px; border-radius: 8px; text-decoration: none; 
                             font-weight: 500; transition: transform 0.2s; }
                        .btn:hover { transform: translateY(-1px); }
                        .btn-primary { background: #2C5282; color: white; }
                        .btn-secondary { background: #718096; color: white; }
                        .btn-outline { border: 2px solid #2C5282; color: #2C5282; background: white; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="logo">🏢 CWS Company</div>
                            <h1>Datos de Cotización No Disponibles</h1>
                        </div>
                        
                        <div class="mensaje">
                            <h3>📋 Cotización Generada Correctamente</h3>
                            <p>La cotización <strong>{{ numero }}</strong> fue creada exitosamente y el PDF se generó correctamente.</p>
                        </div>
                        
                        <div class="info">
                            <h4>ℹ️ ¿Por qué no puedo ver el desglose?</h4>
                            <p>Los datos detallados de esta cotización no están disponibles temporalmente debido a que se creó durante un reinicio del servidor.</p>
                            <p>El PDF con toda la información está disponible y se puede descargar.</p>
                        </div>
                        
                        <div class="buttons">
                            <a href="/pdf/{{ numero }}" target="_blank" class="btn btn-primary">
                                📄 Ver PDF Completo
                            </a>
                            <a href="/" class="btn btn-outline">
                                🏠 Volver al Inicio  
                            </a>
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px; color: #718096; font-size: 12px;">
                            <p>Si necesitas el desglose detallado, puedes recrear la cotización o contactar al administrador.</p>
                        </div>
                    </div>
                </body>
                </html>
                """, numero=numero_cotizacion)
            else:
                # PDF histórico sin desglose
                print(f"[DESGLOSE] PDF histórico encontrado - sin desglose")
                return render_template_string("""
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Desglose No Disponible - CWS</title>
                    <style>
                        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                               background: #f8f9fa; margin: 0; padding: 20px; }
                        .container { max-width: 500px; margin: 50px auto; background: white; 
                                   border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 30px; }
                        .header { text-align: center; margin-bottom: 30px; }
                        .logo { color: #2C5282; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
                        .mensaje { background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; 
                                 border-radius: 8px; margin: 20px 0; }
                        .buttons { display: flex; gap: 15px; justify-content: center; margin-top: 30px; }
                        .btn { padding: 12px 24px; border-radius: 8px; text-decoration: none; 
                             font-weight: 500; transition: transform 0.2s; }
                        .btn:hover { transform: translateY(-1px); }
                        .btn-primary { background: #2C5282; color: white; }
                        .btn-outline { border: 2px solid #2C5282; color: #2C5282; background: white; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="logo">🏢 CWS Company</div>
                            <h1>PDF Histórico</h1>
                        </div>
                        
                        <div class="mensaje">
                            <h3>📁 Archivo Histórico</h3>
                            <p>Este es un PDF histórico importado manualmente.</p>
                            <p>El desglose detallado no está disponible.</p>
                            <p><strong>Número:</strong> {{ numero }}</p>
                        </div>
                        
                        <div class="buttons">
                            <a href="/pdf/{{ numero }}" target="_blank" class="btn btn-primary">
                                📄 Ver PDF
                            </a>
                            <a href="/" class="btn btn-outline">
                                🏠 Volver al Inicio
                            </a>
                        </div>
                    </div>
                </body>
                </html>
                """, numero=numero_cotizacion)
        
        # PASO 3: No existe ni cotización ni PDF
        print(f"[DESGLOSE] Cotización '{numero_cotizacion}' no encontrada en ninguna fuente")
        return render_template_string("""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Cotización No Encontrada - CWS</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                       background: #f8f9fa; margin: 0; padding: 20px; }
                .container { max-width: 500px; margin: 50px auto; background: white; 
                           border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 30px; }
                .header { text-align: center; margin-bottom: 30px; }
                .logo { color: #2C5282; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
                .mensaje { background: #fef2f2; border: 1px solid #fecaca; padding: 20px; 
                         border-radius: 8px; margin: 20px 0; color: #dc2626; }
                .btn { display: inline-block; padding: 12px 24px; border-radius: 8px; 
                     text-decoration: none; font-weight: 500; margin-top: 20px;
                     border: 2px solid #2C5282; color: #2C5282; background: white; }
                .btn:hover { background: #2C5282; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏢 CWS Company</div>
                    <h1>Cotización No Encontrada</h1>
                </div>
                
                <div class="mensaje">
                    <h3>❌ No Encontrada</h3>
                    <p>La cotización <strong>{{ numero }}</strong> no fue encontrada en el sistema.</p>
                    <p>Verifica que el número sea correcto.</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="/" class="btn">🏠 Volver al Inicio</a>
                </div>
            </div>
        </body>
        </html>
        """, numero=numero_cotizacion), 404
        
    except Exception as e:
        print(f"[DESGLOSE] ERROR CRÍTICO procesando '{numero_cotizacion}': {e}")
        import traceback
        traceback.print_exc()

        # Retornar página de error amigable
        from flask import render_template_string
        return render_template_string("""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error - CWS Cotizador</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f8f9fa;
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    max-width: 600px;
                    margin: 50px auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    padding: 40px;
                }
                .error-icon {
                    font-size: 64px;
                    text-align: center;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #dc3545;
                    text-align: center;
                    margin-bottom: 20px;
                }
                .error-message {
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .error-details {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    font-family: monospace;
                    font-size: 12px;
                    overflow-x: auto;
                }
                .buttons {
                    text-align: center;
                    margin-top: 30px;
                }
                .btn {
                    display: inline-block;
                    padding: 12px 24px;
                    margin: 0 8px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 500;
                    transition: all 0.2s;
                }
                .btn-primary {
                    background: #4f46e5;
                    color: white;
                }
                .btn-primary:hover {
                    background: #4338ca;
                }
                .btn-secondary {
                    background: #6c757d;
                    color: white;
                }
                .btn-secondary:hover {
                    background: #5a6268;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">⚠️</div>
                <h1>Error al Cargar Desglose</h1>

                <div class="error-message">
                    <p><strong>Cotización:</strong> {{ numero }}</p>
                    <p>No se pudo cargar el desglose de esta cotización debido a un error técnico.</p>
                </div>

                <div class="error-details">
                    <strong>Detalles técnicos:</strong><br>
                    {{ error_msg }}
                </div>

                <div class="buttons">
                    <a href="/" class="btn btn-primary">🏠 Volver al Inicio</a>
                    <a href="/pdf/{{ numero }}" class="btn btn-secondary" target="_blank">📄 Ver PDF</a>
                </div>

                <p style="text-align: center; margin-top: 30px; color: #6c757d; font-size: 13px;">
                    El error ha sido registrado y será revisado.
                </p>
            </div>
        </body>
        </html>
        """, numero=numero_cotizacion, error_msg=str(e)), 500

# ============================================
# RUTA DE INFORMACIÓN DEL SISTEMA
# ============================================

@app.route("/admin")
def panel_admin():
    """Panel de administración para migración y sincronización"""
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CWS - Panel de Administración</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f8f9fa;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }}
            .section {{
                margin: 20px 0;
                padding: 20px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: #fafafa;
            }}
            .section h3 {{
                color: #007bff;
                margin-top: 0;
            }}
            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                margin: 5px;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }}
            .btn-primary {{ background: #007bff; color: white; }}
            .btn-success {{ background: #28a745; color: white; }}
            .btn-warning {{ background: #ffc107; color: #212529; }}
            .btn-danger {{ background: #dc3545; color: white; }}
            .btn-secondary {{ background: #6c757d; color: white; }}
            .btn:hover {{ opacity: 0.9; transform: translateY(-2px); }}
            .btn:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; }}
            .status {{
                padding: 15px;
                border-radius: 6px;
                margin: 10px 0;
                font-weight: bold;
            }}
            .status.online {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .status.offline {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .status.hybrid {{ background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }}
            .result {{
                margin: 15px 0;
                padding: 15px;
                border-radius: 6px;
                font-family: monospace;
                white-space: pre-wrap;
                overflow-x: auto;
            }}
            .result.success {{ background: #d4edda; color: #155724; }}
            .result.error {{ background: #f8d7da; color: #721c24; }}
            .result.info {{ background: #cce7ff; color: #004085; }}
            .warning {{
                background: #fff3cd;
                color: #856404;
                padding: 15px;
                border-radius: 6px;
                margin: 10px 0;
                border-left: 4px solid #ffc107;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 CWS - Panel de Administración</h1>
            
            <div class="section">
                <h3>Estado del Sistema</h3>
                <button class="btn btn-primary" onclick="verificarEstado()">Verificar Estado</button>
                <div id="estado-sistema"></div>
            </div>
            
            <div class="section">
                <h3>Migracion de Datos</h3>
                <div class="warning">
                    <strong>Atencion:</strong> La migracion movera todas las cotizaciones del archivo offline a MongoDB. 
                    Se creará un respaldo automático antes de la migración.
                </div>
                <button class="btn btn-success" onclick="migrarAMongoDB()">Migrar Offline -> MongoDB</button>
                <button class="btn btn-warning" onclick="sincronizarOffline()">Sincronizar MongoDB -> Offline</button>
                <div id="resultado-migracion"></div>
            </div>
            
            <div class="section">
                <h3>Estadisticas</h3>
                <button class="btn btn-primary" onclick="verEstadisticas()">Ver Estadisticas Detalladas</button>
                <div id="estadisticas"></div>
            </div>
            
            <div class="section">
                <h3>🔧 Herramientas de Diagnóstico</h3>
                <a href="/admin/pdfs" class="btn btn-warning">📄 Administrar PDFs</a>
                <a href="/admin/actualizar-timestamps" class="btn btn-secondary">Actualizar Timestamps</a>
                <a href="/verificar-ultima" class="btn btn-secondary">Verificar Ultima Cotizacion</a>
                <a href="/" class="btn btn-primary">🏠 Volver al Home</a>
            </div>
        </div>
        
        <script>
            function mostrarResultado(elementId, data, tipo = 'info') {{
                const elemento = document.getElementById(elementId);
                elemento.innerHTML = `<div class="result ${{tipo}}">${{JSON.stringify(data, null, 2)}}</div>`;
            }}
            
            function mostrarError(elementId, error) {{
                const elemento = document.getElementById(elementId);
                elemento.innerHTML = `<div class="result error">Error: ${{error}}</div>`;
            }}
            
            async function verificarEstado() {{
                try {{
                    const response = await fetch('/stats');
                    const data = await response.json();
                    
                    let estadoHtml = `<div class="status ${{data.modo.toLowerCase()}}">`;
                    estadoHtml += `<strong>Modo:</strong> ${{data.modo}}<br>`;
                    estadoHtml += `<strong>Total Cotizaciones:</strong> ${{data.total_cotizaciones}}<br>`;
                    estadoHtml += `<strong>Clientes Únicos:</strong> ${{data.clientes_unicos}}<br>`;
                    estadoHtml += `<strong>Vendedores Únicos:</strong> ${{data.vendedores_unicos}}`;
                    estadoHtml += `</div>`;
                    
                    document.getElementById('estado-sistema').innerHTML = estadoHtml;
                }} catch (error) {{
                    mostrarError('estado-sistema', error.message);
                }}
            }}
            
            async function migrarAMongoDB() {{
                if (!confirm('¿Estás seguro de migrar todas las cotizaciones offline a MongoDB?')) {{
                    return;
                }}
                
                try {{
                    const response = await fetch('/admin/migrar-a-mongodb');
                    const data = await response.json();
                    
                    if (data.exito) {{
                        mostrarResultado('resultado-migracion', data, 'success');
                    }} else {{
                        mostrarResultado('resultado-migracion', data, 'error');
                    }}
                }} catch (error) {{
                    mostrarError('resultado-migracion', error.message);
                }}
            }}
            
            async function sincronizarOffline() {{
                try {{
                    const response = await fetch('/admin/sincronizar-offline');
                    const data = await response.json();
                    
                    if (data.exito) {{
                        mostrarResultado('resultado-migracion', data, 'success');
                    }} else {{
                        mostrarResultado('resultado-migracion', data, 'error');
                    }}
                }} catch (error) {{
                    mostrarError('resultado-migracion', error.message);
                }}
            }}
            
            async function verEstadisticas() {{
                try {{
                    const response = await fetch('/stats');
                    const data = await response.json();
                    mostrarResultado('estadisticas', data, 'info');
                }} catch (error) {{
                    mostrarError('estadisticas', error.message);
                }}
            }}
            
            // Verificar estado al cargar
            document.addEventListener('DOMContentLoaded', verificarEstado);
        </script>
    </body>
    </html>
    """

@app.route("/admin/migrar-a-mongodb")
def migrar_a_mongodb():
    """Ruta obsoleta - MongoDB fue reemplazado por Supabase PostgreSQL en Septiembre 2025"""
    return jsonify({
        "error": "MongoDB ya no está disponible",
        "mensaje": "El sistema migró completamente a Supabase PostgreSQL. "
                   "Todas las cotizaciones se guardan directamente en Supabase "
                   "con respaldo JSON offline. No se requiere migración.",
        "estado": "migracion_completada",
        "fecha_migracion": "2025-09-08",
        "nueva_arquitectura": "Supabase PostgreSQL + SDK REST + JSON offline"
    }), 410  # Gone

@app.route("/admin/sincronizar-offline")
def sincronizar_offline():
    """Sincroniza PostgreSQL → archivo offline como respaldo"""
    try:
        if db_manager.modo_offline:
            return jsonify({
                "error": "En modo offline, no se puede sincronizar desde la base de datos"
            }), 503

        # Obtener todas las cotizaciones (prioridad: PostgreSQL directo → SDK REST → offline JSON)
        cotizaciones_supabase = []
        try:
            if hasattr(db_manager, 'pg_connection') and db_manager.pg_connection:
                cursor = db_manager.pg_connection.cursor()
                cursor.execute(
                    "SELECT numero_cotizacion, datos_generales, items, condiciones, "
                    "revision, version, fecha_creacion, timestamp, usuario, observaciones, created_at "
                    "FROM cotizaciones ORDER BY created_at DESC;"
                )
                rows = cursor.fetchall()
                for row in rows:
                    cot_data = {
                        "numeroCotizacion": row["numero_cotizacion"],
                        "datosGenerales": row["datos_generales"],
                        "items": row["items"],
                        "condiciones": row["condiciones"],
                        "revision": row["revision"],
                        "version": row["version"],
                        "fechaCreacion": str(row["fecha_creacion"]) if row["fecha_creacion"] else None,
                        "timestamp": row["timestamp"],
                        "usuario": row["usuario"],
                        "observaciones": row["observaciones"],
                        "created_at": str(row["created_at"]) if row["created_at"] else None
                    }
                    cotizaciones_supabase.append(cot_data)
                cursor.close()
        except Exception as e:
            # Fallback: intentar via SDK REST (solo columnas básicas)
            try:
                resp = db_manager.supabase_client.table('cotizaciones') \
                    .select('numero_cotizacion, datos_generales, items, condiciones, revision, version, fecha_creacion, timestamp') \
                    .order('created_at', desc=True) \
                    .limit(1000) \
                    .execute()
                cotizaciones_supabase = resp.data if resp.data else []
            except Exception as e2:
                # Último recurso: datos ya guardados en JSON offline
                datos_offline = db_manager._cargar_datos_offline()
                cotizaciones_supabase = datos_offline.get("cotizaciones", [])
                if not cotizaciones_supabase:
                    return jsonify({
                        "error": f"No se pudo obtener cotizaciones. PG: {str(e)[:100]}, SDK: {str(e2)[:100]}"
                    }), 500

        # Crear estructura offline
        datos_offline = {
            "cotizaciones": cotizaciones_supabase,
            "metadata": {
                "sincronizado_desde_supabase": datetime.datetime.now().isoformat(),
                "total_cotizaciones": len(cotizaciones_supabase),
                "version": os.getenv('APP_VERSION', '1.0.0'),
                "modo": "respaldo_supabase"
            }
        }

        # Guardar archivo offline actualizado
        if db_manager._guardar_datos_offline(datos_offline):
            return jsonify({
                "exito": True,
                "total_sincronizadas": len(cotizaciones_supabase),
                "archivo": getattr(db_manager, 'archivo_offline', 'cotizaciones_offline.json'),
                "mensaje": f"{len(cotizaciones_supabase)} cotizaciones sincronizadas a archivo offline"
            })
        else:
            return jsonify({
                "error": "Error guardando archivo offline"
            }), 500

    except Exception as e:
        return jsonify({
            "error": f"Error durante sincronización: {str(e)}"
        }), 500

# ============================================
# RUTAS DE ADMINISTRACIÓN DE PDFs
# ============================================

@app.route("/admin/pdfs")
def admin_pdfs():
    """Panel de administración de PDFs"""
    try:
        # Obtener estadísticas de PDFs
        stats_pdfs = pdf_manager.listar_todos_pdfs()
        
        if "error" in stats_pdfs:
            stats_info = {"error": stats_pdfs["error"]}
        else:
            stats_info = stats_pdfs.get("estadisticas", {})
        
        # Verificar integridad
        integridad = pdf_manager.verificar_integridad()
        
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>CWS - Administración de PDFs</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; margin: 0; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
                .section {{ margin: 20px 0; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa; }}
                .section h3 {{ color: #007bff; margin-top: 0; }}
                .btn {{ padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin: 5px; transition: all 0.3s ease; text-decoration: none; display: inline-block; }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-success {{ background: #28a745; color: white; }}
                .btn-warning {{ background: #ffc107; color: #212529; }}
                .btn-danger {{ background: #dc3545; color: white; }}
                .btn-secondary {{ background: #6c757d; color: white; }}
                .btn:hover {{ opacity: 0.9; transform: translateY(-2px); }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #e8f4fd; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .stat-label {{ color: #666; margin-top: 10px; }}
                .result {{ margin: 15px 0; padding: 15px; border-radius: 6px; font-family: monospace; white-space: pre-wrap; overflow-x: auto; }}
                .result.success {{ background: #d4edda; color: #155724; }}
                .result.error {{ background: #f8d7da; color: #721c24; }}
                .result.info {{ background: #cce7ff; color: #004085; }}
                .upload-area {{ border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; border-radius: 8px; }}
                .upload-area:hover {{ border-color: #007bff; background: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📄 CWS - Administración de PDFs</h1>
                
                <div class="section">
                    <h3>📊 Estadísticas de PDFs</h3>
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-number">{stats_info.get('total', '?')}</div>
                            <div class="stat-label">Total PDFs</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{stats_info.get('nuevos', '?')}</div>
                            <div class="stat-label">PDFs Nuevos</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{stats_info.get('antiguos', '?')}</div>
                            <div class="stat-label">PDFs Históricos</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{integridad.get('archivos_encontrados', '?')}</div>
                            <div class="stat-label">Archivos OK</div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h3>🔧 Herramientas de Administración</h3>
                    <button class="btn btn-primary" onclick="verTodosPDFs()">📋 Listar Todos los PDFs</button>
                    <button class="btn btn-success" onclick="verificarIntegridad()">🔍 Verificar Integridad</button>
                    <button class="btn btn-danger" onclick="actualizarRutas()">🔄 Actualizar Rutas de PDFs</button>
                    <button class="btn btn-warning" onclick="escanearPDFs()">🔍 Escanear PDFs Existentes</button>
                    <button class="btn btn-warning" onclick="mostrarFormularioImportar()">📥 Importar PDFs Antiguos</button>
                    <a href="/admin" class="btn btn-secondary">🔙 Panel Principal</a>
                    <a href="/" class="btn btn-primary">🏠 Inicio</a>
                </div>
                
                <div class="section" id="importar-section" style="display: none;">
                    <h3>📥 Importar PDFs Antiguos</h3>
                    <div class="upload-area" onclick="document.getElementById('file-input').click()">
                        <p>Click aquí para seleccionar PDFs antiguos</p>
                        <p style="font-size: 12px; color: #666;">Selecciona múltiples archivos PDF para importar</p>
                        <input type="file" id="file-input" multiple accept=".pdf" style="display: none;" onchange="procesarArchivos()">
                    </div>
                    <div id="archivos-seleccionados"></div>
                    <button class="btn btn-success" onclick="importarPDFs()" id="btn-importar" style="display: none;">Importar PDFs Seleccionados</button>
                </div>
                
                <div class="section">
                    <h3>📋 Resultados</h3>
                    <div id="resultados"></div>
                </div>
            </div>
            
            <script>
                let archivosSeleccionados = [];
                
                function mostrarResultado(data, tipo = 'info') {{
                    const elemento = document.getElementById('resultados');
                    elemento.innerHTML = `<div class="result ${{tipo}}">${{JSON.stringify(data, null, 2)}}</div>`;
                }}
                
                function mostrarError(error) {{
                    const elemento = document.getElementById('resultados');
                    elemento.innerHTML = `<div class="result error">Error: ${{error}}</div>`;
                }}
                
                async function verTodosPDFs() {{
                    try {{
                        const response = await fetch('/admin/listar-pdfs');
                        const data = await response.json();
                        
                        if (data.error) {{
                            mostrarError(data.error);
                        }} else {{
                            mostrarResultado(data, 'info');
                        }}
                    }} catch (error) {{
                        mostrarError(error.message);
                    }}
                }}
                
                async function verificarIntegridad() {{
                    try {{
                        const response = await fetch('/admin/verificar-integridad-pdfs');
                        const data = await response.json();
                        
                        if (data.error) {{
                            mostrarError(data.error);
                        }} else {{
                            mostrarResultado(data, data.archivos_faltantes.length > 0 ? 'error' : 'success');
                        }}
                    }} catch (error) {{
                        mostrarError(error.message);
                    }}
                }}
                
                async function actualizarRutas() {{
                    if (!confirm('¿Actualizar las rutas de los PDFs existentes a la nueva ubicación?')) {{
                        return;
                    }}
                    
                    try {{
                        mostrarResultado('Actualizando rutas de PDFs...', 'info');
                        const response = await fetch('/admin/actualizar-rutas-pdf');
                        const data = await response.json();
                        
                        if (data.error) {{
                            mostrarError(data.error);
                        }} else {{
                            mostrarResultado(data, 'success');
                        }}
                    }} catch (error) {{
                        mostrarError(error.message);
                    }}
                }}
                
                async function escanearPDFs() {{
                    if (!confirm('¿Escanear las carpetas de PDFs y registrar archivos no indexados?')) {{
                        return;
                    }}
                    
                    try {{
                        mostrarResultado('Escaneando carpetas de PDFs...', 'info');
                        const response = await fetch('/admin/escanear-pdfs-existentes');
                        const data = await response.json();
                        
                        if (data.error) {{
                            mostrarError(data.error);
                        }} else {{
                            mostrarResultado(data, 'success');
                        }}
                    }} catch (error) {{
                        mostrarError(error.message);
                    }}
                }}
                
                function mostrarFormularioImportar() {{
                    const section = document.getElementById('importar-section');
                    section.style.display = section.style.display === 'none' ? 'block' : 'none';
                }}
                
                function procesarArchivos() {{
                    const input = document.getElementById('file-input');
                    const archivos = Array.from(input.files);
                    
                    if (archivos.length === 0) return;
                    
                    archivosSeleccionados = archivos;
                    
                    let html = '<h4>Archivos seleccionados:</h4><ul>';
                    archivos.forEach((archivo, index) => {{
                        html += `<li>${{archivo.name}} (${{(archivo.size / 1024 / 1024).toFixed(2)}} MB)</li>`;
                    }});
                    html += '</ul>';
                    
                    document.getElementById('archivos-seleccionados').innerHTML = html;
                    document.getElementById('btn-importar').style.display = 'block';
                }}
                
                async function importarPDFs() {{
                    if (archivosSeleccionados.length === 0) {{
                        alert('No hay archivos seleccionados');
                        return;
                    }}
                    
                    mostrarResultado('Importando PDFs...', 'info');
                    const btnImportar = document.getElementById('btn-importar');
                    btnImportar.disabled = true;
                    btnImportar.textContent = 'Importando...';
                    
                    try {{
                        for (let i = 0; i < archivosSeleccionados.length; i++) {{
                            const archivo = archivosSeleccionados[i];
                            const formData = new FormData();
                            formData.append('pdf', archivo);
                            
                            // Extraer metadatos del nombre del archivo
                            const nombre = archivo.name.replace('.pdf', '');
                            formData.append('numero_cotizacion', nombre);
                            formData.append('cliente', 'Importado');
                            formData.append('fecha', new Date().toISOString().split('T')[0]);
                            
                            const response = await fetch('/admin/importar-pdf', {{
                                method: 'POST',
                                body: formData
                            }});
                            
                            const result = await response.json();
                            console.log(`Archivo ${{i+1}}/${{archivosSeleccionados.length}}: ${{result.success ? 'OK' : 'Error'}}`);
                        }}
                        
                        mostrarResultado('Todos los PDFs han sido procesados. Revisa los logs para detalles.', 'success');
                        
                        // Limpiar formulario
                        document.getElementById('file-input').value = '';
                        document.getElementById('archivos-seleccionados').innerHTML = '';
                        document.getElementById('btn-importar').style.display = 'none';
                        archivosSeleccionados = [];
                        
                    }} catch (error) {{
                        mostrarError(error.message);
                    }} finally {{
                        btnImportar.disabled = false;
                        btnImportar.textContent = 'Importar PDFs Seleccionados';
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"Error en panel de PDFs: {str(e)}", 500

@app.route("/admin/listar-pdfs")
def admin_listar_pdfs():
    """Lista todos los PDFs para administración"""
    try:
        resultado = pdf_manager.listar_todos_pdfs()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/verificar-integridad-pdfs")
def admin_verificar_integridad():
    """Verifica integridad del sistema de PDFs"""
    try:
        resultado = pdf_manager.verificar_integridad()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/importar-pdf", methods=["POST"])
def admin_importar_pdf():
    """Importa un PDF antiguo al sistema"""
    try:
        if 'pdf' not in request.files:
            return jsonify({"success": False, "error": "No se envió archivo PDF"}), 400
        
        archivo = request.files['pdf']
        if archivo.filename == '':
            return jsonify({"success": False, "error": "Nombre de archivo vacío"}), 400
        
        # Extraer metadatos del formulario
        metadata = {
            'numero_cotizacion': request.form.get('numero_cotizacion', archivo.filename.replace('.pdf', '')),
            'cliente': request.form.get('cliente', ''),
            'vendedor': request.form.get('vendedor', ''),
            'proyecto': request.form.get('proyecto', ''),
            'fecha': request.form.get('fecha', datetime.datetime.now().strftime('%Y-%m-%d'))
        }
        
        # Guardar archivo temporalmente
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            archivo.save(temp_file.name)
            
            # Importar usando PDF Manager
            resultado = pdf_manager.importar_pdf_antiguo(temp_file.name, metadata)
            
            # Limpiar archivo temporal
            os.unlink(temp_file.name)
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/admin/normalizar-terminos")
@login_required
def admin_normalizar_terminos():
    """
    Migración única: normaliza las keys de términos y condiciones en todas las cotizaciones.
    Copia condicionesPago → terminos y comentariosAdicionales → comentarios
    cuando la key destino está vacía. Bidireccional e idempotente.
    """
    resultado = {
        "total_escaneadas": 0,
        "total_con_condiciones": 0,
        "fix_condicionesPago_a_terminos": 0,
        "fix_comentariosAdicionales_a_comentarios": 0,
        "fix_terminos_a_condicionesPago": 0,
        "fix_comentarios_a_comentariosAdicionales": 0,
        "actualizadas": 0,
        "errores": 0,
        "detalle": []
    }

    try:
        # Leer todas las cotizaciones vía SDK
        response = db_manager.supabase_client.table('cotizaciones').select('*').execute()
        if not response.data:
            return "<h2>No se encontraron cotizaciones</h2>", 200

        resultado["total_escaneadas"] = len(response.data)

        for row in response.data:
            row_id = row['id']
            numero = row.get('numero_cotizacion', f'id:{row_id}')
            dg = row.get('datos_generales') or {}
            condiciones = dg.get('condiciones') if isinstance(dg, dict) else None

            if not isinstance(condiciones, dict):
                continue

            resultado["total_con_condiciones"] += 1
            cambios = []

            # Bidireccional: copiar key con valor → key vacía
            if condiciones.get('condicionesPago') and not condiciones.get('terminos'):
                condiciones['terminos'] = condiciones['condicionesPago']
                cambios.append('condicionesPago → terminos')
                resultado["fix_condicionesPago_a_terminos"] += 1
            if condiciones.get('terminos') and not condiciones.get('condicionesPago'):
                condiciones['condicionesPago'] = condiciones['terminos']
                cambios.append('terminos → condicionesPago')
                resultado["fix_terminos_a_condicionesPago"] += 1
            if condiciones.get('comentariosAdicionales') and not condiciones.get('comentarios'):
                condiciones['comentarios'] = condiciones['comentariosAdicionales']
                cambios.append('comentariosAdicionales → comentarios')
                resultado["fix_comentariosAdicionales_a_comentarios"] += 1
            if condiciones.get('comentarios') and not condiciones.get('comentariosAdicionales'):
                condiciones['comentariosAdicionales'] = condiciones['comentarios']
                cambios.append('comentarios → comentariosAdicionales')
                resultado["fix_comentarios_a_comentariosAdicionales"] += 1

            if cambios:
                try:
                    dg['condiciones'] = condiciones
                    db_manager.supabase_client.table('cotizaciones') \
                        .update({'datos_generales': dg}) \
                        .eq('id', row_id) \
                        .execute()
                    resultado["actualizadas"] += 1
                    resultado["detalle"].append({
                        "id": row_id,
                        "numero": str(numero),
                        "cambios": cambios
                    })
                except Exception as e:
                    resultado["errores"] += 1
                    resultado["detalle"].append({
                        "id": row_id,
                        "numero": str(numero),
                        "error": str(e)
                    })

        # Renderizar reporte HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Normalización T&C — Resultados</title>
        <style>
            body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
            .card {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); padding: 20px; margin-bottom: 20px; }}
            .stat {{ display: inline-block; min-width: 80px; font-size: 28px; font-weight: 700; text-align: center; }}
            .stat-label {{ font-size: 13px; color: #666; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }}
            th {{ background: #f9fafb; font-weight: 600; }}
            .ok {{ color: #16a34a; }} .err {{ color: #dc2626; }}
        </style></head>
        <body>
        <h1>Normalización de Términos y Condiciones</h1>
        <div class="card">
            <p><strong>Ejecución completada.</strong> Esta migración es idempotente — puede ejecutarse múltiples veces sin riesgo.</p>
        </div>
        <div class="card">
            <div style="display:flex; gap:24px; flex-wrap:wrap;">
                <div><div class="stat">{resultado["total_escaneadas"]}</div><div class="stat-label">Cotizaciones escaneadas</div></div>
                <div><div class="stat">{resultado["total_con_condiciones"]}</div><div class="stat-label">Con condiciones</div></div>
                <div><div class="stat" style="color:#2563eb">{resultado["actualizadas"]}</div><div class="stat-label">Actualizadas</div></div>
                <div><div class="stat" style="color:#dc2626">{resultado["errores"]}</div><div class="stat-label">Errores</div></div>
            </div>
        </div>
        <div class="card">
            <h3>Desglose de fixes aplicados</h3>
            <table>
                <tr><td>condicionesPago → terminos</td><td class="ok"><strong>{resultado["fix_condicionesPago_a_terminos"]}</strong></td></tr>
                <tr><td>comentariosAdicionales → comentarios</td><td class="ok"><strong>{resultado["fix_comentariosAdicionales_a_comentarios"]}</strong></td></tr>
                <tr><td>terminos → condicionesPago</td><td><strong>{resultado["fix_terminos_a_condicionesPago"]}</strong></td></tr>
                <tr><td>comentarios → comentariosAdicionales</td><td><strong>{resultado["fix_comentarios_a_comentariosAdicionales"]}</strong></td></tr>
            </table>
        </div>"""

        if resultado["detalle"]:
            html += """
        <div class="card">
            <h3>Cotizaciones actualizadas</h3>
            <table>
                <tr><th>ID</th><th>Número Cotización</th><th>Cambios</th></tr>"""
            for d in resultado["detalle"]:
                cambios_str = ', '.join(d.get('cambios', []))
                error_str = d.get('error', '')
                if error_str:
                    html += f'<tr><td>{d["id"]}</td><td>{d["numero"]}</td><td class="err">ERROR: {error_str}</td></tr>'
                else:
                    html += f'<tr><td>{d["id"]}</td><td>{d["numero"]}</td><td class="ok">{cambios_str}</td></tr>'
            html += "</table></div>"

        html += '<p style="margin-top:24px;color:#666;font-size:13px;">Segunda ejecución debe reportar 0 actualizaciones (idempotente).</p></body></html>'
        return html

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<h2>Error</h2><pre>{escape(str(e))}</pre>", 500


@app.route("/admin/actualizar-rutas-pdf")
def actualizar_rutas_pdf():
    """Actualiza las rutas de PDFs existentes a la nueva ubicación"""
    try:
        if db_manager.modo_offline:
            return jsonify({"error": "No disponible en modo offline"}), 400
        
        # Buscar todos los registros de PDF con rutas antiguas
        filtro = {
            "$or": [
                {"ruta_completa": {"$regex": "C:\\\\Users\\\\.*\\\\Google Drive"}},
                {"ruta_completa": {"$regex": "C:/Users/.*/Google Drive"}}
            ]
        }
        
        registros_antiguos = list(pdf_manager.pdf_collection.find(filtro))
        actualizados = 0
        errores = []
        
        for registro in registros_antiguos:
            try:
                numero_cotizacion = registro.get("numero_cotizacion")
                ruta_antigua = registro.get("ruta_completa", "")
                
                # Construir nueva ruta
                nombre_archivo = registro.get("nombre_archivo", "")
                tipo = registro.get("tipo", "nueva")
                
                if tipo == "nueva":
                    nueva_ruta = pdf_manager.nuevas_path / nombre_archivo
                else:
                    nueva_ruta = pdf_manager.antiguas_path / nombre_archivo
                
                # Actualizar registro en MongoDB
                pdf_manager.pdf_collection.update_one(
                    {"_id": registro["_id"]},
                    {
                        "$set": {
                            "ruta_completa": str(nueva_ruta.absolute()),
                            "ruta_archivo": f"{tipo}s/{nombre_archivo}",
                            "actualizado": datetime.datetime.now().isoformat()
                        }
                    }
                )
                
                actualizados += 1
                print(f"Actualizado: {numero_cotizacion} -> {nueva_ruta}")
                
            except Exception as e:
                error_msg = f"Error actualizando {registro.get('numero_cotizacion', 'desconocido')}: {str(e)}"
                errores.append(error_msg)
                print(error_msg)
        
        resultado = {
            "success": True,
            "registros_encontrados": len(registros_antiguos),
            "actualizados": actualizados,
            "errores": len(errores),
            "detalles_errores": errores[:5],
            "mensaje": f"Se actualizaron {actualizados} registros de PDF a la nueva ruta",
            "nueva_ruta_base": str(pdf_manager.base_pdf_path)
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({"error": f"Error actualizando rutas: {str(e)}"}), 500

@app.route("/admin/escanear-pdfs-existentes")
def escanear_pdfs_existentes():
    """Escanea las carpetas de PDFs y registra archivos no indexados"""
    try:
        if db_manager.modo_offline:
            return jsonify({"error": "No disponible en modo offline"}), 400
        
        registrados = 0
        ya_existentes = 0
        errores = []
        
        # Escanear carpeta de PDFs nuevos
        if pdf_manager.nuevas_path.exists():
            for archivo_pdf in pdf_manager.nuevas_path.glob("*.pdf"):
                try:
                    # Extraer número de cotización del nombre del archivo
                    nombre_archivo = archivo_pdf.name
                    numero_cotizacion = nombre_archivo.replace("Cotizacion_", "").replace(".pdf", "")
                    
                    # Verificar si ya existe en la base de datos
                    existe = pdf_manager.pdf_collection.find_one({"numero_cotizacion": numero_cotizacion})
                    
                    if not existe:
                        # Registrar PDF nuevo
                        registro_pdf = {
                            "nombre_archivo": nombre_archivo,
                            "numero_cotizacion": numero_cotizacion,
                            "cliente": "Escaneado automáticamente",
                            "vendedor": "",
                            "proyecto": "",
                            "fecha": datetime.datetime.now().strftime('%Y-%m-%d'),
                            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                            "tipo": "nueva",
                            "tiene_desglose": True,  # Asumimos que los nuevos tienen desglose
                            "ruta_archivo": f"nuevas/{nombre_archivo}",
                            "ruta_completa": str(archivo_pdf.absolute()),
                            "tamaño_bytes": archivo_pdf.stat().st_size,
                            "escaneado_automaticamente": True,
                            "fecha_escaneo": datetime.datetime.now().isoformat()
                        }
                        
                        pdf_manager.pdf_collection.insert_one(registro_pdf)
                        registrados += 1
                        print(f"Registrado PDF nuevo: {numero_cotizacion}")
                    else:
                        ya_existentes += 1
                        
                except Exception as e:
                    error_msg = f"Error procesando {archivo_pdf.name}: {str(e)}"
                    errores.append(error_msg)
                    print(error_msg)
        
        # Escanear carpeta de PDFs antiguos
        if pdf_manager.antiguas_path.exists():
            for archivo_pdf in pdf_manager.antiguas_path.glob("*.pdf"):
                try:
                    # Para PDFs antiguos, usar el nombre completo como número de cotización
                    nombre_archivo = archivo_pdf.name
                    numero_cotizacion = nombre_archivo.replace(".pdf", "")
                    
                    # Verificar si ya existe en la base de datos
                    existe = pdf_manager.pdf_collection.find_one({"numero_cotizacion": numero_cotizacion})
                    
                    if not existe:
                        # Registrar PDF antiguo
                        registro_pdf = {
                            "nombre_archivo": nombre_archivo,
                            "numero_cotizacion": numero_cotizacion,
                            "cliente": "PDF Histórico",
                            "vendedor": "",
                            "proyecto": "",
                            "fecha": datetime.datetime.now().strftime('%Y-%m-%d'),
                            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                            "tipo": "antigua",
                            "tiene_desglose": False,  # Los antiguos no tienen desglose
                            "ruta_archivo": f"antiguas/{nombre_archivo}",
                            "ruta_completa": str(archivo_pdf.absolute()),
                            "tamaño_bytes": archivo_pdf.stat().st_size,
                            "escaneado_automaticamente": True,
                            "fecha_escaneo": datetime.datetime.now().isoformat()
                        }
                        
                        pdf_manager.pdf_collection.insert_one(registro_pdf)
                        registrados += 1
                        print(f"Registrado PDF antiguo: {numero_cotizacion}")
                    else:
                        ya_existentes += 1
                        
                except Exception as e:
                    error_msg = f"Error procesando {archivo_pdf.name}: {str(e)}"
                    errores.append(error_msg)
                    print(error_msg)
        
        resultado = {
            "success": True,
            "pdfs_registrados": registrados,
            "ya_existentes": ya_existentes,
            "errores": len(errores),
            "detalles_errores": errores[:5],
            "mensaje": f"Escaneo completado: {registrados} PDFs registrados, {ya_existentes} ya existían",
            "rutas_escaneadas": [
                str(pdf_manager.nuevas_path),
                str(pdf_manager.antiguas_path)
            ]
        }
        
        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": f"Error escaneando PDFs: {str(e)}"}), 500

@app.route("/admin/regenerar-pdfs-faltantes", methods=["POST"])
def regenerar_pdfs_faltantes():
    """Regenera PDFs para todas las cotizaciones que no tienen PDF en ningún storage."""
    try:
        if not (REPORTLAB_AVAILABLE or WEASYPRINT_AVAILABLE):
            return jsonify({"error": "No hay generador de PDF disponible (ReportLab/WeasyPrint)"}), 500

        # Obtener todas las cotizaciones de la base de datos
        resultado_busqueda = db_manager.buscar_cotizaciones("", pagina=1, por_pagina=500)
        cotizaciones = resultado_busqueda.get("items", [])

        total = len(cotizaciones)
        regenerados = 0
        ya_existentes = 0
        fallidos = []

        for cot in cotizaciones:
            numero = cot.get("numeroCotizacion") or cot.get("numero_cotizacion", "")
            if not numero:
                continue

            # Verificar si ya existe el PDF en algún storage
            resultado_pdf = pdf_manager.obtener_pdf(numero)
            if resultado_pdf.get("encontrado"):
                ya_existentes += 1
                continue

            # No existe — intentar regenerar
            try:
                # Obtener datos completos de la cotización
                cot_completa = db_manager.obtener_cotizacion(numero)
                if not cot_completa.get("encontrado"):
                    fallidos.append({"numero": numero, "razon": "cotización no encontrada en DB"})
                    continue

                cotizacion_data = cot_completa["item"]
                pdf_data = generar_pdf_reportlab(cotizacion_data) if REPORTLAB_AVAILABLE else None
                if not pdf_data:
                    fallidos.append({"numero": numero, "razon": "generación de PDF falló"})
                    continue

                pdf_manager.almacenar_pdf_nuevo(pdf_content=pdf_data, cotizacion_data=cotizacion_data)
                regenerados += 1
                print(f"[REGENERAR] PDF regenerado: {numero}")

            except Exception as err:
                fallidos.append({"numero": numero, "razon": str(err)})
                print(f"[REGENERAR] Error con {numero}: {err}")

        return jsonify({
            "total_cotizaciones": total,
            "ya_existentes": ya_existentes,
            "regenerados": regenerados,
            "fallidos": len(fallidos),
            "detalle_fallidos": fallidos[:50]  # Limitar a 50 para no saturar la respuesta
        })

    except Exception as e:
        return jsonify({"error": f"Error en regeneración masiva: {str(e)}"}), 500

@app.route("/admin/debug-pdf/<path:numero_cotizacion>")
def debug_pdf_especifico(numero_cotizacion):
    """Debug específico para un PDF que no se encuentra"""
    try:
        from urllib.parse import unquote
        numero_cotizacion = unquote(numero_cotizacion)
        
        debug_info = {
            "numero_buscado": numero_cotizacion,
            "rutas_verificadas": [],
            "registros_encontrados": [],
            "archivos_fisicos": []
        }
        
        # Verificar archivos físicos en ambas carpetas
        for carpeta, nombre in [(pdf_manager.nuevas_path, "nuevas"), (pdf_manager.antiguas_path, "antiguas")]:
            if carpeta.exists():
                archivos = list(carpeta.glob("*.pdf"))
                debug_info["archivos_fisicos"].append({
                    "carpeta": nombre,
                    "ruta": str(carpeta),
                    "archivos": [archivo.name for archivo in archivos]
                })
                
                # Buscar archivos que contengan parte del número
                for archivo in archivos:
                    if numero_cotizacion.lower() in archivo.name.lower() or archivo.name.lower() in numero_cotizacion.lower():
                        debug_info["rutas_verificadas"].append({
                            "archivo": archivo.name,
                            "ruta_completa": str(archivo.absolute()),
                            "existe": archivo.exists(),
                            "tamaño": archivo.stat().st_size if archivo.exists() else 0
                        })
        
        # Buscar en base de datos con diferentes variaciones
        variaciones = [
            numero_cotizacion,
            numero_cotizacion.replace(" ", ""),
            numero_cotizacion.replace("-", ""),
            numero_cotizacion.replace(".", ""),
            f"{numero_cotizacion}.pdf",
            numero_cotizacion.replace(".pdf", "")
        ]
        
        for variacion in variaciones:
            registros = list(pdf_manager.pdf_collection.find({
                "$or": [
                    {"numero_cotizacion": {"$regex": variacion, "$options": "i"}},
                    {"nombre_archivo": {"$regex": variacion, "$options": "i"}}
                ]
            }))
            
            for registro in registros:
                registro["_id"] = str(registro["_id"])
                debug_info["registros_encontrados"].append(registro)
        
        # Buscar todos los registros de tipo "antigua"
        todos_antiguos = list(pdf_manager.pdf_collection.find({"tipo": "antigua"}))
        for registro in todos_antiguos:
            registro["_id"] = str(registro["_id"])
        
        debug_info["todos_los_antiguos"] = todos_antiguos
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({"error": f"Error en debug: {str(e)}"}), 500

@app.route("/debug-env")
def debug_env():
    """Diagnostico de variables de entorno para Render"""
    import os

    # Verificar variables criticas
    supabase_url = os.getenv('SUPABASE_URL')
    env_check = {
        'SECRET_KEY': 'CONFIGURADO' if os.getenv('SECRET_KEY') else 'FALTA',
        'SUPABASE_URL': 'CONFIGURADO' if supabase_url else 'FALTA',
        'SUPABASE_URL_PREVIEW': f"{supabase_url[:50]}..." if supabase_url else 'N/A',
        'DATABASE_URL': 'CONFIGURADO' if os.getenv('DATABASE_URL') else 'FALTA',
        'RENDER': 'SI' if os.getenv('RENDER') else 'NO',
        'PORT': os.getenv('PORT', 'No configurado'),
        'entorno': 'RENDER' if os.getenv('RENDER') else 'LOCAL'
    }

    # Estado de Supabase
    env_check['supabase_modo_offline'] = db_manager.modo_offline

    # Intentar contar cotizaciones via Supabase
    try:
        if not db_manager.modo_offline:
            stats = db_manager.obtener_estadisticas()
            env_check['supabase_total_cotizaciones'] = stats.get('total_cotizaciones', 'N/A')
            env_check['supabase_conexion'] = 'EXITOSA'
            env_check['supabase_fuente'] = stats.get('fuente', 'desconocida')
        else:
            env_check['supabase_total_cotizaciones'] = 'N/A'
            env_check['supabase_conexion'] = 'FALLO - MODO OFFLINE'
    except Exception as e:
        env_check['supabase_total_cotizaciones'] = 'ERROR'
        env_check['supabase_conexion'] = f'ERROR: {str(e)}'

    return jsonify(env_check)

@app.route("/stats")
def stats_sistema():
    """Estadísticas detalladas de la base de datos"""
    try:
        if db_manager.modo_offline:
            # Modo offline - contar desde archivo JSON
            datos = db_manager._cargar_datos_offline()
            total_cotizaciones = len(datos.get("cotizaciones", []))
            
            # Estadísticas adicionales
            cotizaciones = datos.get("cotizaciones", [])
            clientes_unicos = set()
            vendedores_unicos = set()
            
            for cot in cotizaciones:
                datos_gen = cot.get("datosGenerales", {})
                if datos_gen.get("cliente"):
                    clientes_unicos.add(datos_gen["cliente"])
                if datos_gen.get("vendedor"):
                    vendedores_unicos.add(datos_gen["vendedor"])
            
            return jsonify({
                "modo": "OFFLINE",
                "total_cotizaciones": total_cotizaciones,
                "clientes_unicos": len(clientes_unicos),
                "vendedores_unicos": len(vendedores_unicos),
                "archivo_datos": db_manager.archivo_offline,
                "metadata": datos.get("metadata", {})
            })
        else:
            # Modo online - Supabase PostgreSQL
            # Usar obtener_estadisticas() que ya tiene triple capa (PG → SDK → JSON)
            stats = db_manager.obtener_estadisticas()
            total_cotizaciones = stats.get("total_cotizaciones", 0)

            # Clientes y vendedores únicos vía Supabase SDK
            clientes_unicos = 0
            vendedores_unicos = 0
            try:
                if hasattr(db_manager, 'supabase_client') and db_manager.supabase_client:
                    try:
                        resp = db_manager.supabase_client.table('cotizaciones').select('datosGenerales').execute()
                        if resp.data:
                            clientes_set = set()
                            vendedores_set = set()
                            for row in resp.data:
                                dg = row.get('datosGenerales', {})
                                if dg.get('cliente'):
                                    clientes_set.add(dg['cliente'])
                                if dg.get('vendedor'):
                                    vendedores_set.add(dg['vendedor'])
                            clientes_unicos = len(clientes_set)
                            vendedores_unicos = len(vendedores_set)
                    except Exception:
                        # Fallback: contar desde JSON offline
                        datos = db_manager._cargar_datos_offline()
                        cots = datos.get("cotizaciones", [])
                        c_set = set(c.get("datosGenerales", {}).get("cliente") for c in cots if c.get("datosGenerales", {}).get("cliente"))
                        v_set = set(c.get("datosGenerales", {}).get("vendedor") for c in cots if c.get("datosGenerales", {}).get("vendedor"))
                        clientes_unicos = len(c_set)
                        vendedores_unicos = len(v_set)
            except Exception:
                clientes_unicos = "Error calculando"
                vendedores_unicos = "Error calculando"

            # Última cotización vía Supabase SDK
            ultima_info = None
            try:
                if hasattr(db_manager, 'supabase_client') and db_manager.supabase_client:
                    ultima_resp = db_manager.supabase_client.table('cotizaciones') \
                        .select('numeroCotizacion, datosGenerales, fechaCreacion') \
                        .order('created_at', desc=True) \
                        .limit(1) \
                        .execute()
                    if ultima_resp.data:
                        ultima = ultima_resp.data[0]
                        ultima_info = {
                            "numero": ultima.get("numeroCotizacion"),
                            "cliente": ultima.get("datosGenerales", {}).get("cliente"),
                            "fecha": ultima.get("fechaCreacion")
                        }
            except Exception:
                ultima_info = None

            return jsonify({
                "modo": "ONLINE",
                "total_cotizaciones": total_cotizaciones,
                "clientes_unicos": clientes_unicos,
                "vendedores_unicos": vendedores_unicos,
                "database": "Supabase PostgreSQL",
                "fuente": stats.get("fuente", "desconocida"),
                "ultima_cotizacion": ultima_info
            })
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "modo": "OFFLINE" if db_manager.modo_offline else "ONLINE"
        }), 500

@app.route("/info")
def info_sistema():
    """Información del sistema y configuración (sin datos sensibles)"""
    
    # Información de PDFs
    pdf_info = {
        "ruta_base": str(pdf_manager.base_pdf_path),
        "carpeta_nuevas": str(pdf_manager.nuevas_path),
        "carpeta_antiguas": str(pdf_manager.antiguas_path),
        "nuevas_existe": pdf_manager.nuevas_path.exists(),
        "antiguas_existe": pdf_manager.antiguas_path.exists(),
        "google_drive_disponible": pdf_manager.drive_client.is_available() if pdf_manager.drive_client else False
    }
    
    # Contar archivos si las carpetas existen
    try:
        if pdf_manager.nuevas_path.exists():
            pdf_info["archivos_nuevos"] = len(list(pdf_manager.nuevas_path.glob("*.pdf")))
        else:
            pdf_info["archivos_nuevos"] = "Carpeta no existe"
            
        if pdf_manager.antiguas_path.exists():
            pdf_info["archivos_antiguos"] = len(list(pdf_manager.antiguas_path.glob("*.pdf")))
        else:
            pdf_info["archivos_antiguos"] = "Carpeta no existe"
    except Exception as e:
        pdf_info["error_conteo"] = str(e)
    
    # DEBUG: Información de Google Drive
    try:
        pdf_info["google_drive_debug"] = {
            "client_exists": pdf_manager.drive_client is not None,
            "is_available": pdf_manager.drive_client.is_available() if pdf_manager.drive_client else False,
            "folder_nuevas": getattr(pdf_manager.drive_client, 'folder_nuevas', 'No configurado'),
            "folder_antiguas": getattr(pdf_manager.drive_client, 'folder_antiguas', 'No configurado'),
            "env_vars_status": {
                "GOOGLE_SERVICE_ACCOUNT_JSON": "SI" if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else "NO",
                "GOOGLE_DRIVE_FOLDER_NUEVAS": os.getenv('GOOGLE_DRIVE_FOLDER_NUEVAS', 'NO'),
                "GOOGLE_DRIVE_FOLDER_ANTIGUAS": os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS', 'NO')
            }
        }
        
        # Test de búsqueda básica
        if pdf_info["google_drive_debug"]["is_available"]:
            try:
                test_pdfs = pdf_manager.drive_client.buscar_pdfs("")
                pdf_info["google_drive_debug"]["test_busqueda"] = {
                    "exitoso": True,
                    "total": len(test_pdfs),
                    "archivos": [pdf.get('nombre', 'N/A') for pdf in test_pdfs[:3]]
                }
            except Exception as search_error:
                pdf_info["google_drive_debug"]["test_busqueda"] = {
                    "exitoso": False,
                    "error": str(search_error)
                }
                
    except Exception as debug_error:
        pdf_info["google_drive_debug"] = {"error": str(debug_error)}
    
    return jsonify({
        "app": os.getenv('APP_NAME', 'CWS Cotizaciones'),
        "version": os.getenv('APP_VERSION', '1.0.0'),
        "environment": os.getenv('FLASK_ENV', 'development'),
        "debug": app.config.get('DEBUG', False),
        "database": os.getenv('MONGO_DATABASE', 'cotizaciones'),
        "modo_offline": db_manager.modo_offline,
        "weasyprint_disponible": WEASYPRINT_AVAILABLE,
        "generacion_pdf": "Habilitada" if WEASYPRINT_AVAILABLE else "Deshabilitada - Instalar WeasyPrint",
        "limits": {
            "max_results_per_page": int(os.getenv('MAX_RESULTS_PER_PAGE', '50')),
            "default_page_size": int(os.getenv('DEFAULT_PAGE_SIZE', '20'))
        },
        "pdfs": pdf_info
    })

@app.route("/debug-pdfs")
def debug_pdfs_simple():
    """Debug simple para ver PDFs en Google Drive"""
    try:
        if not pdf_manager.drive_client or not pdf_manager.drive_client.is_available():
            return jsonify({
                "error": "Google Drive no disponible",
                "available": False
            })
        
        # Buscar TODOS los PDFs
        todos_pdfs = pdf_manager.drive_client.buscar_pdfs("")
        
        resultado = {
            "total_pdfs": len(todos_pdfs),
            "archivos": []
        }
        
        for pdf in todos_pdfs:
            resultado["archivos"].append({
                "nombre_real": pdf.get('nombre', 'N/A'),
                "numero_extraido": pdf.get('numero_cotizacion', 'N/A'),
                "id": pdf.get('id', 'N/A')
            })
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        })

@app.route("/test-drive")
def test_drive():
    """Test super simple de Google Drive"""
    try:
        info = {
            "drive_client_exists": pdf_manager.drive_client is not None,
            "drive_available": pdf_manager.drive_client.is_available() if pdf_manager.drive_client else False,
            "folder_nuevas": getattr(pdf_manager.drive_client, 'folder_nuevas', 'No configurado'),
            "folder_antiguas": getattr(pdf_manager.drive_client, 'folder_antiguas', 'No configurado'),
            "env_vars": {
                "GOOGLE_SERVICE_ACCOUNT_JSON": "Configurado" if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else "NO configurado",
                "GOOGLE_DRIVE_FOLDER_NUEVAS": os.getenv('GOOGLE_DRIVE_FOLDER_NUEVAS', 'NO configurado'),
                "GOOGLE_DRIVE_FOLDER_ANTIGUAS": os.getenv('GOOGLE_DRIVE_FOLDER_ANTIGUAS', 'NO configurado')
            }
        }
        
        # Si Google Drive está disponible, intentar una búsqueda básica
        if info["drive_available"]:
            try:
                todos_pdfs = pdf_manager.drive_client.buscar_pdfs("")
                info["test_busqueda"] = {
                    "exitoso": True,
                    "total_encontrados": len(todos_pdfs),
                    "primeros_5": [pdf.get('nombre', 'N/A') for pdf in todos_pdfs[:5]]
                }
            except Exception as e:
                info["test_busqueda"] = {
                    "exitoso": False,
                    "error": str(e)
                }
        else:
            info["test_busqueda"] = "Drive no disponible"
            
        return jsonify(info)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "tipo": type(e).__name__
        })

@app.route("/debug/google-drive")
def debug_google_drive():
    """Debug específico para Google Drive"""
    try:
        debug_info = {
            "disponible": pdf_manager.drive_client.is_available() if pdf_manager.drive_client else False,
            "folder_id": pdf_manager.drive_client.folder_id if pdf_manager.drive_client else None,
            "credenciales_configuradas": bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')),
            "variables_entorno": {
                "GOOGLE_DRIVE_FOLDER_ID": os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'No configurado'),
                "GOOGLE_SERVICE_ACCOUNT_JSON": "Configurado" if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else "No configurado"
            }
        }
        
        # Test de búsqueda si está disponible
        if debug_info["disponible"]:
            try:
                test_pdfs = pdf_manager.drive_client.buscar_pdfs()
                debug_info["test_busqueda"] = {
                    "exitoso": True,
                    "cantidad_pdfs": len(test_pdfs),
                    "archivos": [pdf['nombre'] for pdf in test_pdfs[:5]]  # Solo mostrar 5
                }
            except Exception as e:
                debug_info["test_busqueda"] = {
                    "exitoso": False,
                    "error": str(e)
                }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "tipo": type(e).__name__
        }), 500

@app.route("/debug/buscar-pdf/<numero_cotizacion>")
def debug_buscar_pdf_especifico(numero_cotizacion):
    """Debug para buscar un PDF específico"""
    try:
        print(f"🔍 DEBUG: Buscando PDF específico: '{numero_cotizacion}'")
        
        # Búsqueda general en Google Drive
        if pdf_manager.drive_client and pdf_manager.drive_client.is_available():
            # Buscar sin query (todos los PDFs)
            todos_pdfs = pdf_manager.drive_client.buscar_pdfs()
            
            # Buscar con query específico  
            pdfs_query = pdf_manager.drive_client.buscar_pdfs(numero_cotizacion)
            
            # Intentar obtener el PDF
            resultado = pdf_manager.obtener_pdf(numero_cotizacion)
            
            debug_info = {
                "numero_buscado": numero_cotizacion,
                "total_pdfs_drive": len(todos_pdfs),
                "pdfs_con_query": len(pdfs_query),
                "nombres_encontrados": [pdf['nombre'] for pdf in todos_pdfs[:10]],  # Primeros 10
                "coincidencias_query": [pdf['nombre'] for pdf in pdfs_query],
                "resultado_busqueda": {
                    "encontrado": resultado.get("encontrado", False),
                    "error": resultado.get("error", "Sin error"),
                    "tipo_fuente": resultado.get("tipo_fuente", "N/A")
                },
                "variaciones_testeo": {
                    f"{numero_cotizacion}": "Búsqueda original",
                    f"{numero_cotizacion}.pdf": "Con extensión",
                    numero_cotizacion.upper(): "Mayúsculas",
                    numero_cotizacion.lower(): "Minúsculas"
                }
            }
            
            return jsonify(debug_info)
        else:
            return jsonify({
                "error": "Google Drive no disponible",
                "numero_buscado": numero_cotizacion
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "numero_buscado": numero_cotizacion,
            "tipo": type(e).__name__
        }), 500

@app.route("/debug/listar-pdfs-drive")
def debug_listar_todos_pdfs():
    """Lista TODOS los PDFs disponibles en Google Drive"""
    try:
        if not pdf_manager.drive_client or not pdf_manager.drive_client.is_available():
            return jsonify({
                "error": "Google Drive no disponible",
                "disponible": False
            }), 500
        
        # Buscar TODOS los PDFs (sin filtro)
        todos_pdfs = pdf_manager.drive_client.buscar_pdfs("")
        
        debug_info = {
            "drive_disponible": True,
            "total_pdfs_encontrados": len(todos_pdfs),
            "folder_id": pdf_manager.drive_client.folder_id,
            "archivos": []
        }
        
        # Mostrar información detallada de cada PDF
        for pdf in todos_pdfs:
            debug_info["archivos"].append({
                "nombre_archivo": pdf.get('nombre', 'N/A'),
                "numero_cotizacion": pdf.get('numero_cotizacion', 'N/A'),
                "drive_id": pdf.get('id', 'N/A'),
                "tamaño": pdf.get('tamaño', '0'),
                "fecha": pdf.get('fecha_modificacion', 'N/A')
            })
        
        # Buscar específicamente CWS-RM-800
        buscando = "CWS-RM-800"
        pdfs_especifico = pdf_manager.drive_client.buscar_pdfs(buscando)
        debug_info["busqueda_especifica"] = {
            "termino": buscando,
            "encontrados": len(pdfs_especifico),
            "resultados": [pdf.get('nombre', 'N/A') for pdf in pdfs_especifico]
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "tipo": type(e).__name__
        }), 500

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def is_json_request():
    """Verifica si la petición espera JSON"""
    return (request.headers.get('Accept') == 'application/json' or 
            request.args.get('format') == 'json')

def handle_error_response(error_msg, item_id):
    """Maneja respuestas de error"""
    if is_json_request():
        return jsonify({"error": True, "mensaje": error_msg}), 500
    else:
        return f"""
        <h1>Error del servidor</h1>
        <p>{error_msg}</p>
        <p><a href="/">Volver al inicio</a></p>
        """, 500

def handle_not_found_response(item_id):
    """Maneja respuestas de no encontrado"""
    if is_json_request():
        return jsonify({
            "encontrado": False,
            "mensaje": f"Cotización '{item_id}' no encontrada"
        }), 404
    else:
        return f"""
        <h1>Cotización no encontrada</h1>
        <p>La cotización '{item_id}' no existe.</p>
        <p><a href="/">Volver al inicio</a></p>
        """, 404

def render_cotizacion_html(cotizacion):
    """Renderiza la cotización mostrando TODOS los campos"""
    print(f"Renderizando cotizacion completa: {cotizacion.get('numeroCotizacion', 'Sin numero')}")
    
    # Datos básicos
    numero = cotizacion.get('numeroCotizacion', 'Sin número')
    
    # Datos generales
    datos_generales = cotizacion.get('datosGenerales', {})
    vendedor = datos_generales.get('vendedor', 'N/A')
    cliente = datos_generales.get('cliente', 'N/A')
    proyecto = datos_generales.get('proyecto', 'N/A')
    atencion = datos_generales.get('atencionA', 'N/A')
    contacto = datos_generales.get('contacto', 'N/A')
    revision = datos_generales.get('revision', 'N/A')
    actualizacion_revision = datos_generales.get('actualizacionRevision', 'N/A')
    
    # Items
    items = cotizacion.get('items', [])
    items_html = ""
    
    for i, item in enumerate(items):
        descripcion = item.get('descripcion', 'Sin descripción')
        uom = item.get('uom', 'N/A')
        cantidad = item.get('cantidad', '0')
        costo_unidad = item.get('costoUnidad', '0.00')
        total = item.get('total', '0.00')
        transporte = item.get('transporte', '0.00')
        instalacion = item.get('instalacion', '0.00')
        seguridad = item.get('seguridad', '0')
        descuento = item.get('descuento', '0')
        
        # Materiales del item
        materiales = item.get('materiales', [])
        materiales_html = ""
        
        if materiales:
            materiales_html = """
            <div style="margin-top: 15px;">
                <h4 style="color: #28a745; margin: 10px 0;">🔧 Materiales:</h4>
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 12px;">
                    <thead>
                        <tr style="background: #28a745; color: white;">
                            <th style="border: 1px solid #28a745; padding: 8px; text-align: left;">Material</th>
                            <th style="border: 1px solid #28a745; padding: 8px; text-align: center;">Peso/Kg</th>
                            <th style="border: 1px solid #28a745; padding: 8px; text-align: center;">Cantidad</th>
                            <th style="border: 1px solid #28a745; padding: 8px; text-align: center;">$/Kg</th>
                            <th style="border: 1px solid #28a745; padding: 8px; text-align: center;">Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for material in materiales:
                material_nombre = material.get('material', 'Sin nombre')
                peso = material.get('peso', '0')
                cantidad_mat = material.get('cantidad', '0')
                precio_mat = material.get('precio', '0.00')
                subtotal_mat = material.get('subtotal', '0.00')
                
                materiales_html += f"""
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="border: 1px solid #ddd; padding: 6px; font-weight: bold;">{material_nombre}</td>
                            <td style="border: 1px solid #ddd; padding: 6px; text-align: center;">{peso}</td>
                            <td style="border: 1px solid #ddd; padding: 6px; text-align: center;">{cantidad_mat}</td>
                            <td style="border: 1px solid #ddd; padding: 6px; text-align: center;">${precio_mat}</td>
                            <td style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold; color: #28a745;">${subtotal_mat}</td>
                        </tr>
                """
            
            materiales_html += """
                    </tbody>
                </table>
            </div>
            """
        
        # Otros materiales del item
        otros_materiales = item.get('otrosMateriales', [])
        otros_materiales_html = ""
        
        if otros_materiales:
            otros_materiales_html = """
            <div style="margin-top: 15px;">
                <h4 style="color: #17a2b8; margin: 10px 0;">🔩 Otros Materiales:</h4>
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 12px;">
                    <thead>
                        <tr style="background: #17a2b8; color: white;">
                            <th style="border: 1px solid #17a2b8; padding: 8px; text-align: left;">Descripción</th>
                            <th style="border: 1px solid #17a2b8; padding: 8px; text-align: center;">Precio</th>
                            <th style="border: 1px solid #17a2b8; padding: 8px; text-align: center;">Cantidad</th>
                            <th style="border: 1px solid #17a2b8; padding: 8px; text-align: center;">Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for otro in otros_materiales:
                descripcion_otro = otro.get('descripcion', 'Sin descripción')
                precio_otro = otro.get('precio', '0.00')
                cantidad_otro = otro.get('cantidad', '0')
                subtotal_otro = otro.get('subtotal', '0.00')
                
                otros_materiales_html += f"""
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="border: 1px solid #ddd; padding: 6px; font-weight: bold;">{descripcion_otro}</td>
                            <td style="border: 1px solid #ddd; padding: 6px; text-align: center;">${precio_otro}</td>
                            <td style="border: 1px solid #ddd; padding: 6px; text-align: center;">{cantidad_otro}</td>
                            <td style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold; color: #17a2b8;">${subtotal_otro}</td>
                        </tr>
                """
            
            otros_materiales_html += """
                    </tbody>
                </table>
            </div>
            """
        
        items_html += f"""
        <div style="background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; border: 2px solid #28a745;">
            <h3 style="color: #155724;">📦 Item {i+1}: {descripcion}</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                <div><strong>UOM:</strong> <span style="color: #007bff;">{uom}</span></div>
                <div><strong>Cantidad:</strong> <span style="color: #007bff;">{cantidad}</span></div>
                <div><strong>Costo/Unidad:</strong> <span style="color: #007bff; font-weight: bold;">${costo_unidad}</span></div>
                <div><strong>Total Item:</strong> <span style="color: #28a745; font-weight: bold;">${total}</span></div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0;">
                <div><strong>Transporte:</strong> <span style="color: #dc3545;">${transporte}</span></div>
                <div><strong>Instalación:</strong> <span style="color: #dc3545;">${instalacion}</span></div>
                <div><strong>% Seguridad:</strong> <span style="color: #dc3545;">{seguridad}%</span></div>
                <div><strong>% Descuento:</strong> <span style="color: #dc3545;">{descuento}%</span></div>
            </div>
            {materiales_html}
            {otros_materiales_html}
        </div>
        """
    
    # Condiciones
    condiciones = cotizacion.get('condiciones', {})
    moneda = condiciones.get('moneda', 'N/A')
    tipo_cambio = condiciones.get('tipoCambio', 'N/A')
    tiempo_entrega = condiciones.get('tiempoEntrega', 'N/A')
    entrega_en = condiciones.get('entregaEn', 'N/A')
    terminos_pago = condiciones.get('terminos', condiciones.get('terminosPago', 'N/A'))
    comentarios = condiciones.get('comentarios', 'N/A')
    
    # Sistema
    fecha_creacion = cotizacion.get('fechaCreacion', 'N/A')
    if fecha_creacion and fecha_creacion != 'N/A':
        try:
            fecha_creacion = fecha_creacion[:19]  # Solo fecha y hora, sin microsegundos
        except:
            pass
    
    version = cotizacion.get('version', 'N/A')
    id_cotizacion = cotizacion.get('_id', 'N/A')
    
    # HTML completo
    html_completo = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cotización {numero}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #007bff;
                padding-bottom: 20px;
            }}
            .section {{
                margin-bottom: 20px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fafafa;
            }}
            .section h3 {{
                margin-top: 0;
                color: #007bff;
                border-bottom: 1px solid #007bff;
                padding-bottom: 10px;
            }}
            .field {{
                margin-bottom: 10px;
                display: flex;
                align-items: flex-start;
            }}
            .field strong {{
                width: 150px;
                display: inline-block;
                flex-shrink: 0;
            }}
            .field span {{
                background: #f9f9f9;
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 3px;
                flex: 1;
                word-wrap: break-word;
                word-break: break-word;
                white-space: normal;
                text-align: left;
                overflow-wrap: break-word;
            }}
            .actions {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
            }}
            .btn {{
                padding: 10px 20px;
                margin: 0 10px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                background-color: #007bff;
                color: white;
            }}
            .btn:hover {{
                opacity: 0.9;
            }}
            table {{
                width: 100%;
                margin-top: 10px;
            }}
            @media (max-width: 768px) {{
                .field {{
                    flex-direction: column;
                }}
                .field strong {{
                    width: auto;
                    margin-bottom: 5px;
                }}
            }}
            @media print {{
                .actions {{
                    display: none;
                }}
                body {{
                    background: white;
                }}
                .container {{
                    box-shadow: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>🧾 Cotización {numero}</h1>
                <div style="color: #28a745; font-weight: bold;">
                    Vista completa con todos los campos
                </div>
            </div>

            <!-- Datos Generales -->
            <div class="section">
                <h3>Informacion General</h3>
                <div class="field">
                    <strong>Número:</strong>
                    <span>{numero}</span>
                </div>
                <div class="field">
                    <strong>Vendedor:</strong>
                    <span>{vendedor}</span>
                </div>
                <div class="field">
                    <strong>Cliente:</strong>
                    <span>{cliente}</span>
                </div>
                <div class="field">
                    <strong>Proyecto:</strong>
                    <span>{proyecto}</span>
                </div>
                <div class="field">
                    <strong>Atención a:</strong>
                    <span>{atencion}</span>
                </div>
                <div class="field">
                    <strong>Contacto:</strong>
                    <span>{contacto}</span>
                </div>
                <div class="field">
                    <strong>Revisión:</strong>
                    <span>{revision}</span>
                </div>
                {f'''<div class="field">
                    <strong>Actualización Revisión:</strong>
                    <span>{actualizacion_revision}</span>
                </div>''' if actualizacion_revision != 'N/A' and actualizacion_revision else ''}
            </div>

            <!-- Items con materiales -->
            <div class="section">
                <h3>Items de Cotizacion</h3>
                {items_html if items_html else '<p>No hay items en esta cotización</p>'}
            </div>

            <!-- Condiciones -->
            <div class="section">
                <h3>Terminos y Condiciones</h3>
                <div class="field">
                    <strong>Moneda:</strong>
                    <span>{moneda}</span>
                </div>
                {f'''<div class="field">
                    <strong>Tipo de Cambio:</strong>
                    <span>{tipo_cambio}</span>
                </div>''' if moneda == 'USD' and tipo_cambio != 'N/A' else ''}
                <div class="field">
                    <strong>Tiempo de Entrega:</strong>
                    <span>{tiempo_entrega} días hábiles</span>
                </div>
                <div class="field">
                    <strong>Entrega en:</strong>
                    <span>{entrega_en}</span>
                </div>
                <div class="field">
                    <strong>Términos de Pago:</strong>
                    <span style="background: #fff3cd; border-color: #ffeaa7; color: #856404; padding: 8px 12px;">{terminos_pago}</span>
                </div>
                <div class="field">
                    <strong>Comentarios:</strong>
                    <span>{comentarios}</span>
                </div>
            </div>

            <!-- Información del sistema -->
            <div class="section">
                <h3>Informacion del Sistema</h3>
                <div class="field">
                    <strong>ID:</strong>
                    <span style="font-family: monospace; font-size: 12px;">{id_cotizacion}</span>
                </div>
                <div class="field">
                    <strong>Fecha de Creación:</strong>
                    <span>{fecha_creacion}</span>
                </div>
                <div class="field">
                    <strong>Versión del Sistema:</strong>
                    <span>{version}</span>
                </div>
            </div>

            <!-- Acciones -->
            <div class="actions">
                <a href="/" class="btn">🏠 Inicio</a>
                <a href="/formulario" class="btn">Nueva Cotizacion</a>
                <button onclick="window.print()" class="btn">Imprimir</button>
                <a href="/debug-estructura/{numero}" class="btn" style="background: #6c757d;">Debug</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_completo
# ============================================
# MANEJO DE ERRORES
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": True,
        "codigo": 404,
        "mensaje": "Página no encontrada"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": True,
        "codigo": 500,
        "mensaje": "Error interno del servidor"
    }), 500

@app.route("/admin/actualizar-timestamps")
def actualizar_timestamps():
    """Actualiza cotizaciones existentes con timestamps faltantes (Supabase)"""
    try:
        print("Verificando cotizaciones existentes con timestamps...")

        # Obtener todas las cotizaciones via Supabase SDK
        try:
            resp = db_manager.supabase_client.table('cotizaciones') \
                .select('*').execute()
            todas_cotizaciones = resp.data if resp.data else []
        except Exception as e:
            return f"""
            <html>
            <body style="font-family: Arial; margin: 20px;">
                <h1>Error de conexión</h1>
                <p style="color: red;">No se pudo consultar Supabase: {str(e)[:200]}</p>
                <p>El sistema usa Supabase PostgreSQL. Esta ruta solo funciona con conexión activa.</p>
                <p><a href="/">← Volver al inicio</a></p>
            </body>
            </html>
            """, 503

        ahora = datetime.datetime.now()
        sin_timestamp = []
        for cot in todas_cotizaciones:
            if not cot.get("timestamp") or not cot.get("fechaCreacion"):
                sin_timestamp.append(cot)

        print(f"Encontradas {len(sin_timestamp)} cotizaciones sin timestamp")

        resultado_html = f"""
        <html>
        <head>
            <title>Actualización de Timestamps</title>
            <style>
                body {{ font-family: Arial; margin: 20px; }}
                .success {{ color: green; }}
                .info {{ color: blue; }}
                .error {{ color: red; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .log {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Actualizacion de Timestamps (Supabase)</h1>
                <div class="log">
                    <p class="info">Encontradas {len(sin_timestamp)} cotizaciones sin timestamp</p>
        """

        if len(sin_timestamp) == 0:
            resultado_html += """
                    <p class="success">Todas las cotizaciones ya tienen timestamps</p>
                </div>
                <p><a href="/">← Volver al inicio</a></p>
            </div>
        </body>
        </html>
            """
            return resultado_html

        # Actualizar cada cotización via Supabase SDK
        actualizadas = 0
        for cotizacion in sin_timestamp:
            cot_id = cotizacion.get("id")
            if not cot_id:
                continue

            update_data = {}
            if not cotizacion.get("timestamp"):
                update_data["timestamp"] = int(ahora.timestamp() * 1000)
            if not cotizacion.get("fechaCreacion"):
                update_data["fechaCreacion"] = ahora.isoformat()
            if not cotizacion.get("version"):
                update_data["version"] = os.getenv('APP_VERSION', '1.0.0')

            if update_data:
                try:
                    db_manager.supabase_client.table('cotizaciones') \
                        .update(update_data) \
                        .eq('id', cot_id) \
                        .execute()
                    actualizadas += 1
                    numero = cotizacion.get("numeroCotizacion", str(cot_id))
                    print(f"Actualizada: {numero}")
                    resultado_html += f'<p class="success">Actualizada: {numero}</p>\n'
                except Exception as e:
                    resultado_html += f'<p class="error">Error en {cotizacion.get("numeroCotizacion", cot_id)}: {str(e)[:100]}</p>\n'

        resultado_html += f"""
                    <p class="success">{actualizadas} cotizaciones actualizadas exitosamente</p>
                </div>
                <p><a href="/">← Volver al inicio</a></p>
                <p><a href="/ver/Ronal%20AC-234-Mesa">🧪 Probar cotización Ronal</a></p>
            </div>
        </body>
        </html>
        """

        return resultado_html

    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial; margin: 20px;">
            <h1>Error</h1>
            <p style="color: red;">Error actualizando cotizaciones: {str(e)}</p>
            <p><a href="/">← Volver al inicio</a></p>
        </body>
        </html>
        """, 500

@app.route("/debug-estructura/<path:item_id>")
def debug_estructura_items(item_id):
    """Debug específico para estructura de items"""
    try:
        from urllib.parse import unquote
        item_id = unquote(item_id)
        
        resultado = db_manager.obtener_cotizacion(item_id)
        
        if not resultado["encontrado"]:
            return "Cotización no encontrada", 404
        
        cotizacion = resultado["item"]
        
        # Analizar específicamente los items
        items_debug = {
            "items_raw": cotizacion.get("items", "NO EXISTE"),
            "items_tipo": type(cotizacion.get("items", None)).__name__,
            "items_length": len(cotizacion.get("items", [])) if cotizacion.get("items") else 0,
        }
        
        # Si hay items, analizar el primero en detalle
        items = cotizacion.get("items", [])
        if items and len(items) > 0:
            primer_item = items[0]
            items_debug["primer_item_completo"] = primer_item
            items_debug["primer_item_campos"] = list(primer_item.keys()) if isinstance(primer_item, dict) else "No es dict"
            
            # Buscar campos específicos
            campos_buscados = ["descripcion", "cantidad", "uom", "costoUnidad", "total", "transporte", "instalacion", "seguridad", "descuento"]
            items_debug["campos_encontrados"] = {}
            
            for campo in campos_buscados:
                if isinstance(primer_item, dict):
                    items_debug["campos_encontrados"][campo] = {
                        "existe": campo in primer_item,
                        "valor": primer_item.get(campo, "NO EXISTE"),
                        "tipo": type(primer_item.get(campo, None)).__name__
                    }
        
        # Condiciones
        condiciones = cotizacion.get("condiciones", {})
        condiciones_debug = {
            "condiciones_completas": condiciones,
            "campos_condiciones": list(condiciones.keys()) if isinstance(condiciones, dict) else "No es dict"
        }
        
        # Timestamps
        timestamp_debug = {
            "fechaCreacion": cotizacion.get("fechaCreacion"),
            "timestamp": cotizacion.get("timestamp"),
            "fechaCreacion_tipo": type(cotizacion.get("fechaCreacion", None)).__name__
        }
        
        return f"""
        <html>
        <head>
            <title>Debug Estructura Items: {item_id}</title>
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 2px solid #007bff; background: #f8f9fa; }}
                .error {{ border-color: #dc3545; background: #f8d7da; }}
                .success {{ border-color: #28a745; background: #d4edda; }}
                .json {{ background: #f4f4f4; padding: 10px; white-space: pre-wrap; overflow-x: auto; }}
                h2 {{ color: #007bff; }}
                h3 {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <h1>Debug Estructura: {item_id}</h1>
            
            <div class="section">
                <h2>📦 Items - Información General</h2>
                <div class="json">{json.dumps(items_debug, indent=2, ensure_ascii=False)}</div>
            </div>
            
            <div class="section">
                <h2>Condiciones</h2>
                <div class="json">{json.dumps(condiciones_debug, indent=2, ensure_ascii=False)}</div>
            </div>
            
            <div class="section">
                <h2>⏰ Timestamps</h2>
                <div class="json">{json.dumps(timestamp_debug, indent=2, ensure_ascii=False)}</div>
            </div>
            
            <p><a href="/ver/{item_id}">← Volver a la vista normal</a></p>
            <p><a href="/">← Ir al inicio</a></p>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"Error en debug: {str(e)}", 500
    
    # Agregar esta ruta temporal a tu app.py para diagnóstico directo

@app.route("/ver-datos/<path:item_id>")
def ver_datos_directo(item_id):
    """Ver datos directamente sin template complejo"""
    try:
        from urllib.parse import unquote
        item_id = unquote(item_id)
        
        resultado = db_manager.obtener_cotizacion(item_id)
        
        if not resultado["encontrado"]:
            return "Cotización no encontrada", 404
        
        cotizacion = resultado["item"]
        
        # Crear HTML simple y directo
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Datos Directos: {item_id}</title>
            <style>
                body {{ font-family: Arial; margin: 20px; }}
                .dato {{ margin: 10px 0; padding: 10px; background: #f5f5f5; border-left: 4px solid #007bff; }}
                .valor {{ font-weight: bold; color: #007bff; }}
                .items {{ background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>Datos Directos de Cotizacion: {item_id}</h1>
            
            <h2>Datos Generales</h2>
        """
        
        # Datos Generales
        datos_generales = cotizacion.get('datosGenerales', {})
        for key, value in datos_generales.items():
            html += f'<div class="dato"><strong>{key}:</strong> <span class="valor">{value}</span></div>'
        
        # Items
        html += "<h2>📦 Items</h2>"
        items = cotizacion.get('items', [])
        
        if items:
            for i, item in enumerate(items):
                html += f'<div class="items"><h3>Item {i+1}</h3>'
                for key, value in item.items():
                    html += f'<div class="dato"><strong>{key}:</strong> <span class="valor">{value}</span></div>'
                html += '</div>'
        else:
            html += '<p>No hay items</p>'
        
        # Condiciones
        html += "<h2>Condiciones</h2>"
        condiciones = cotizacion.get('condiciones', {})
        for key, value in condiciones.items():
            html += f'<div class="dato"><strong>{key}:</strong> <span class="valor">{value}</span></div>'
        
        # Sistema
        html += "<h2>Sistema</h2>"
        html += f'<div class="dato"><strong>ID:</strong> <span class="valor">{cotizacion.get("_id", "N/A")}</span></div>'
        html += f'<div class="dato"><strong>Fecha Creación:</strong> <span class="valor">{cotizacion.get("fechaCreacion", "N/A")}</span></div>'
        html += f'<div class="dato"><strong>Timestamp:</strong> <span class="valor">{cotizacion.get("timestamp", "N/A")}</span></div>'
        
        html += """
            <p><a href="/">← Volver al inicio</a></p>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"Error: {str(e)}", 500
    
# En app.py, asegúrate de que la función esté correctamente indentada:

@app.route("/ver-json/<path:item_id>")
def ver_json_cotizacion(item_id):
    """Ver estructura JSON completa de la cotización"""
    try:
        from urllib.parse import unquote
        item_id = unquote(item_id)
        
        resultado = db_manager.obtener_cotizacion(item_id)
        
        if not resultado["encontrado"]:
            return jsonify({"error": "Cotización no encontrada"}), 404
        
        # Devolver JSON formateado
        return jsonify(resultado["item"])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# MANEJO DE ERRORES
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": True,
        "codigo": 404,
        "mensaje": "Página no encontrada"
    }), 404

@app.route("/debug/sistema")
def debug_sistema():
    """Diagnóstico del sistema para debugging"""
    try:
        import os
        import sys
        # Verificar variables de entorno de Supabase Storage
        supabase_storage_vars = {
            'SUPABASE_URL': bool(os.getenv('SUPABASE_URL')),
            'SUPABASE_ANON_KEY': bool(os.getenv('SUPABASE_ANON_KEY'))
        }
        
        # Estado de managers
        estado_managers = {
            'supabase_offline': db_manager.modo_offline,
            'supabase_storage_disponible': pdf_manager.supabase_storage_disponible if pdf_manager else False,
            'drive_disponible': pdf_manager.drive_client.is_available() if pdf_manager else False
        }
        
        # Variables de entorno importantes
        env_vars = {
            'SUPABASE_URL': bool(os.getenv('SUPABASE_URL')),
            'DATABASE_URL': bool(os.getenv('DATABASE_URL')),
            'GOOGLE_SERVICE_ACCOUNT_JSON': bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
        }
        
        return jsonify({
            'supabase_storage': supabase_storage_vars,
            'managers': estado_managers, 
            'environment': env_vars,
            'render_environment': bool(os.getenv('RENDER')),
            'python_version': sys.version
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/buscar-texto-completo/<texto>")
def buscar_texto_completo(texto):
    """Busca un texto en TODOS los campos de las cotizaciones"""
    try:
        encontradas = []

        if db_manager.modo_offline:
            datos = db_manager._cargar_datos_offline()
            cotizaciones = datos.get("cotizaciones", [])
        else:
            # Usar Supabase SDK para obtener todas las cotizaciones
            try:
                resp = db_manager.supabase_client.table('cotizaciones') \
                    .select('*').execute()
                cotizaciones = resp.data if resp.data else []
            except Exception:
                # Fallback a JSON offline
                datos = db_manager._cargar_datos_offline()
                cotizaciones = datos.get("cotizaciones", [])

        # Buscar en TODO el documento
        for cot in cotizaciones:
            # Convertir todo el documento a string
            doc_str = json.dumps(cot, ensure_ascii=False).lower()
            if texto.lower() in doc_str:
                encontradas.append({
                    "id": cot.get("id", cot.get("_id")),
                    "numero": cot.get("numeroCotizacion"),
                    "cliente": cot.get("datosGenerales", {}).get("cliente"),
                    "vendedor": cot.get("datosGenerales", {}).get("vendedor"),
                    "proyecto": cot.get("datosGenerales", {}).get("proyecto")
                })

        return jsonify({
            "texto_buscado": texto,
            "total_encontradas": len(encontradas),
            "cotizaciones": encontradas
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/verificar-ultima")
def verificar_ultima():
    """Verifica la última cotización guardada"""
    try:
        if db_manager.modo_offline:
            # En modo offline, buscar en JSON local
            datos = db_manager._cargar_datos_offline()
            cotizaciones = datos.get("cotizaciones", [])
            if cotizaciones:
                # Ordenar por timestamp descendente
                cotizaciones_ordenadas = sorted(
                    cotizaciones,
                    key=lambda c: c.get("timestamp", 0),
                    reverse=True
                )
                ultima = cotizaciones_ordenadas[0]
                return jsonify({
                    "encontrada": True,
                    "id": ultima.get("_id"),
                    "numero": ultima.get("numeroCotizacion"),
                    "cliente": ultima.get("datosGenerales", {}).get("cliente"),
                    "vendedor": ultima.get("datosGenerales", {}).get("vendedor"),
                    "timestamp": ultima.get("timestamp"),
                    "fecha": ultima.get("fechaCreacion"),
                    "fuente": "JSON offline"
                })
            else:
                return jsonify({"encontrada": False})

        # Modo online - Supabase
        try:
            ultima_resp = db_manager.supabase_client.table('cotizaciones') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()

            if ultima_resp.data:
                ultima = ultima_resp.data[0]
                return jsonify({
                    "encontrada": True,
                    "id": ultima.get("id"),
                    "numero": ultima.get("numeroCotizacion"),
                    "cliente": ultima.get("datosGenerales", {}).get("cliente"),
                    "vendedor": ultima.get("datosGenerales", {}).get("vendedor"),
                    "fecha": ultima.get("fechaCreacion"),
                    "fuente": "Supabase PostgreSQL"
                })
            else:
                return jsonify({"encontrada": False})
        except Exception as e:
            return jsonify({
                "encontrada": False,
                "error_supabase": str(e)[:200]
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# RUTAS DE SCHEDULER DE SINCRONIZACIÓN
# ============================================

@app.route("/admin/scheduler/estado")
def scheduler_estado():
    """Obtiene el estado del scheduler de sincronización"""
    try:
        if not sync_scheduler:
            return jsonify({"error": "Scheduler no disponible"}), 503
        
        estado = sync_scheduler.obtener_estado()
        
        # Agregar información adicional
        if estado.get("activo", False):
            proximo_sync = sync_scheduler.obtener_proximo_sync()
            if proximo_sync:
                estado["proximo_sync"] = proximo_sync.isoformat()
                estado["minutos_hasta_proximo"] = int((proximo_sync - datetime.datetime.now()).total_seconds() / 60)
        
        return jsonify(estado)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/scheduler/sync-manual", methods=["POST"])
def scheduler_sync_manual():
    """Ejecuta una sincronización manual inmediata"""
    try:
        if not sync_scheduler:
            return jsonify({"error": "Scheduler no disponible"}), 503
        
        resultado = sync_scheduler.ejecutar_sincronizacion_manual()
        
        if resultado.get("success", False):
            return jsonify({
                "success": True,
                "resultado": resultado,
                "mensaje": "Sincronización manual completada"
            })
        else:
            return jsonify({
                "error": resultado.get("error", "Error en sincronización manual"),
                "resultado": resultado
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/supabase-storage/estado")
def supabase_storage_estado():
    """Obtiene el estado de Supabase Storage"""
    try:
        if not pdf_manager or not pdf_manager.supabase_storage:
            return jsonify({"error": "Supabase Storage no disponible"}), 503
        
        stats = pdf_manager.supabase_storage.obtener_estadisticas()
        
        if "error" in stats:
            return jsonify(stats), 500
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/storage-diagnostic")
def storage_diagnostic():
    """Diagnóstico completo del Storage para producción"""
    try:
        import os
        diagnostic = {
            "timestamp": datetime.datetime.now().isoformat(),
            "environment": "RENDER" if os.getenv("RENDER") else "LOCAL",
            "supabase_config": {
                "url_configured": bool(os.getenv("SUPABASE_URL")),
                "anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
                "url_preview": os.getenv("SUPABASE_URL", "NOT_SET")[:50] + "..." if os.getenv("SUPABASE_URL") else "NOT_SET"
            },
            "pdf_manager_status": {},
            "storage_test": {}
        }
        
        # Test PDF Manager
        if pdf_manager:
            try:
                diagnostic["pdf_manager_status"] = {
                    "initialized": True,
                    "supabase_storage_available": getattr(pdf_manager, 'supabase_storage_disponible', False),
                    "google_drive_available": pdf_manager.drive_client.is_available() if pdf_manager.drive_client else False,
                    "base_pdf_path": str(pdf_manager.base_pdf_path) if hasattr(pdf_manager, 'base_pdf_path') else "NOT_SET"
                }
                
                # Test Storage directo
                if hasattr(pdf_manager, 'supabase_storage'):
                    try:
                        storage_available = pdf_manager.supabase_storage.is_available()
                        diagnostic["storage_test"] = {
                            "supabase_storage_available": storage_available,
                            "error": None
                        }
                        
                        if storage_available:
                            # Test de estadísticas
                            try:
                                stats = pdf_manager.supabase_storage.obtener_estadisticas()
                                diagnostic["storage_test"]["stats"] = stats
                            except Exception as stats_error:
                                diagnostic["storage_test"]["stats_error"] = str(stats_error)
                    except Exception as storage_error:
                        diagnostic["storage_test"] = {
                            "supabase_storage_available": False,
                            "error": str(storage_error)
                        }
                        
            except Exception as pdf_manager_error:
                diagnostic["pdf_manager_status"] = {
                    "initialized": False,
                    "error": str(pdf_manager_error)
                }
        else:
            diagnostic["pdf_manager_status"] = {
                "initialized": False,
                "error": "pdf_manager is None"
            }
            
        return jsonify(diagnostic)
        
    except Exception as e:
        return jsonify({
            "error": f"Error en diagnóstico de storage: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

# ============================================
# DEBUG TEMPORAL PARA REVISIONES
# ============================================

@app.route("/debug-revision/<path:numero_cotizacion>")
def debug_revision_especifica(numero_cotizacion):
    """Debug temporal específico para el caso DAIKIN-CWS-RM-001-R1-COMPUTADOR"""
    try:
        from urllib.parse import unquote
        numero_decodificado = unquote(numero_cotizacion)
        
        debug_info = {
            "timestamp": datetime.datetime.now().isoformat(),
            "numero_original": numero_cotizacion,
            "numero_decodificado": numero_decodificado,
            "analisis": {}
        }
        
        print(f"[DEBUG_REVISION] ===== ANÁLISIS TEMPORAL PARA: {numero_decodificado} =====")
        
        # 1. Verificar si la cotización existe
        resultado_busqueda = db_manager.obtener_cotizacion(numero_decodificado)
        debug_info["analisis"]["cotizacion_existe"] = resultado_busqueda.get("encontrado", False)
        
        if resultado_busqueda.get("encontrado"):
            cotizacion = resultado_busqueda["item"]
            datos_generales = cotizacion.get("datosGenerales", {})
            
            debug_info["analisis"]["datos_cotizacion"] = {
                "numero_en_datos": datos_generales.get("numeroCotizacion"),
                "revision_actual": datos_generales.get("revision", 1),
                "cliente": datos_generales.get("cliente"),
                "vendedor": datos_generales.get("vendedor"),
                "proyecto": datos_generales.get("proyecto"),
                "fecha": datos_generales.get("fecha"),
                "tiene_actualizacion_revision": bool(datos_generales.get("actualizacionRevision"))
            }
            
            # 2. Simular preparación de nueva revisión
            try:
                datos_nueva_revision = preparar_datos_nueva_revision(cotizacion)
                debug_info["analisis"]["preparacion_revision"] = {
                    "exitosa": True,
                    "nueva_revision": datos_nueva_revision.get("datosGenerales", {}).get("revision"),
                    "nuevo_numero": datos_nueva_revision.get("datosGenerales", {}).get("numeroCotizacion"),
                    "campos_clave": {
                        "numeroCotizacion_raiz": datos_nueva_revision.get("numeroCotizacion"),
                        "numeroCotizacion_datosGenerales": datos_nueva_revision.get("datosGenerales", {}).get("numeroCotizacion"),
                        "revision": datos_nueva_revision.get("datosGenerales", {}).get("revision"),
                        "actualizacionRevision": datos_nueva_revision.get("datosGenerales", {}).get("actualizacionRevision")
                    }
                }
                
                # 3. Simular validación de guardado
                datos_simulacion = datos_nueva_revision.copy()
                datos_simulacion["datosGenerales"]["actualizacionRevision"] = "Justificación de prueba para validación temporal del sistema"
                
                # Aplicar la misma lógica de validación del formulario
                revision_sim = safe_int(datos_simulacion.get('datosGenerales', {}).get('revision', 1))
                debug_info["analisis"]["validacion_simulada"] = {
                    "revision_detectada": revision_sim,
                    "es_revision_mayor": revision_sim >= 2,
                    "justificacion_presente": bool(datos_simulacion.get("datosGenerales", {}).get("actualizacionRevision", "").strip()),
                    "justificacion_longitud": len(datos_simulacion.get("datosGenerales", {}).get("actualizacionRevision", "").strip()),
                    "validacion_pasaria": len(datos_simulacion.get("datosGenerales", {}).get("actualizacionRevision", "").strip()) >= 10
                }
                
            except Exception as e:
                debug_info["analisis"]["preparacion_revision"] = {
                    "exitosa": False,
                    "error": str(e)
                }
        
        # 4. Verificar estado del sistema
        debug_info["analisis"]["estado_sistema"] = {
            "db_manager_disponible": db_manager is not None,
            "db_manager_modo": "offline" if getattr(db_manager, 'modo_offline', None) else "online",
            "pdf_manager_disponible": pdf_manager is not None
        }
        
        # 5. Verificar estado de Supabase específicamente
        if hasattr(db_manager, 'supabase_client'):
            try:
                # Test simple de conectividad
                test_result = db_manager.supabase_client.table('cotizaciones').select('*').limit(1).execute()
                debug_info["analisis"]["supabase_conectividad"] = {
                    "conectado": True,
                    "registros_disponibles": len(test_result.data) if test_result.data else 0
                }
            except Exception as e:
                debug_info["analisis"]["supabase_conectividad"] = {
                    "conectado": False,
                    "error": str(e)
                }
        
        print(f"[DEBUG_REVISION] ===== FIN ANÁLISIS TEMPORAL =====")
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "error": f"Error en debug de revisión: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

@app.route("/test-revision-form", methods=["POST"])
def test_revision_form():
    """Endpoint temporal para probar el formulario de revisión con datos específicos"""
    try:
        datos_test = request.get_json()
        
        print(f"[TEST_REVISION] ===== PRUEBA DE FORMULARIO DE REVISIÓN =====")
        print(f"[TEST_REVISION] Datos recibidos: {json.dumps(datos_test, indent=2, ensure_ascii=False)}")
        
        # Aplicar exactamente la misma lógica del formulario real
        datos_generales = datos_test.get('datosGenerales', {})
        revision = safe_int(datos_generales.get('revision', 1))
        numero_cotizacion = datos_generales.get('numeroCotizacion', 'N/A')
        
        resultado_test = {
            "timestamp": datetime.datetime.now().isoformat(),
            "validacion": {
                "revision_detectada": revision,
                "es_revision_mayor": revision >= 2,
                "numero_cotizacion": numero_cotizacion
            }
        }
        
        if revision >= 2:
            actualizacion_revision = datos_generales.get('actualizacionRevision', '').strip()
            resultado_test["validacion"]["justificacion"] = {
                "presente": bool(actualizacion_revision),
                "longitud": len(actualizacion_revision),
                "valida": len(actualizacion_revision) >= 10,
                "contenido_preview": actualizacion_revision[:100] + "..." if len(actualizacion_revision) > 100 else actualizacion_revision
            }
            
            if not actualizacion_revision or len(actualizacion_revision) < 10:
                resultado_test["validacion"]["error"] = f"Justificación requerida para revisión R{revision}. Mínimo 10 caracteres (actual: {len(actualizacion_revision)})."
                return jsonify(resultado_test), 400
        
        # Si pasa la validación, intentar guardado simulado (sin commitear)
        try:
            resultado_guardado = db_manager.guardar_cotizacion(datos_test)
            resultado_test["guardado_simulado"] = {
                "exitoso": resultado_guardado.get("success", False),
                "error": resultado_guardado.get("error"),
                "numero_generado": resultado_guardado.get("numeroCotizacion") or resultado_guardado.get("numero_cotizacion")
            }
        except Exception as e:
            resultado_test["guardado_simulado"] = {
                "exitoso": False,
                "error": f"Excepción durante guardado: {str(e)}"
            }
        
        print(f"[TEST_REVISION] ===== FIN PRUEBA DE FORMULARIO =====")
        
        return jsonify(resultado_test)
        
    except Exception as e:
        return jsonify({
            "error": f"Error en test de revisión: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

# ============================================
# EJECUTAR APLICACIÓN
# ============================================

@app.route("/local-pdf/<path:numero_cotizacion>")
def servir_pdf_local(numero_cotizacion):
    """Servir PDF directamente desde almacenamiento local de Render"""
    try:
        import os
        from flask import send_file
        from urllib.parse import unquote
        
        numero_cotizacion = unquote(numero_cotizacion)
        
        # Limpiar extensión si viene incluida
        if numero_cotizacion.endswith('.pdf'):
            numero_cotizacion = numero_cotizacion[:-4]
        
        # Buscar en carpetas locales
        base_path = os.path.join(os.getcwd(), "pdfs_cotizaciones")
        posibles_rutas = [
            os.path.join(base_path, "nuevas", f"{numero_cotizacion}.pdf"),
            os.path.join(base_path, "antiguas", f"{numero_cotizacion}.pdf"),
            os.path.join(base_path, f"{numero_cotizacion}.pdf")
        ]
        
        for ruta in posibles_rutas:
            if os.path.exists(ruta):
                print(f"[LOCAL_PDF] Sirviendo: {ruta}")
                return send_file(ruta, as_attachment=False, mimetype='application/pdf')
        
        print(f"[LOCAL_PDF] No encontrado: {numero_cotizacion}")
        print(f"[LOCAL_PDF] Rutas buscadas: {posibles_rutas}")
        return jsonify({"error": "PDF no encontrado en almacenamiento local", "numero": numero_cotizacion}), 404
        
    except Exception as e:
        print(f"[LOCAL_PDF] Error sirviendo PDF: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================

if __name__ == "__main__":
    app_name = os.getenv('APP_NAME', 'CWS Cotizaciones')
    app_version = os.getenv('APP_VERSION', '1.0.0')
    environment = os.getenv('FLASK_ENV', 'development')
    database = os.getenv('MONGO_DATABASE', 'cotizaciones')
    
    print(f"Iniciando {app_name} v{app_version}")
    print(f"Entorno: {environment}")
    print(f"Base de datos: {database}")
    print(f"Servidor disponible en: http://127.0.0.1:5000")
    print(f"Info del sistema en: http://127.0.0.1:5000/info")
    
    # Para la nube, el puerto es asignado dinámicamente
    port = int(os.getenv('PORT', 5000))
    
    app.run(
        debug=app.config.get('DEBUG', False),
        host='0.0.0.0',
        port=port
    )