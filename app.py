from flask import Flask, render_template, request, jsonify, send_file

# Intentar importar weasyprint, usar fallback si no está disponible
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    print("WeasyPrint disponible - Generacion de PDF habilitada")
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("WeasyPrint no encontrado - Generacion de PDF deshabilitada")
    print("Consulta INSTRUCCIONES_PDF.md para instalar WeasyPrint")

import io
import datetime
import atexit
import os
import json  # ← IMPORTANTE
import csv  # Para leer archivo CSV de materiales
from dotenv import load_dotenv
from database import DatabaseManager
from pdf_manager import PDFManager

# Cargar variables de entorno
load_dotenv()

# Crear aplicación Flask
app = Flask(__name__)

# Configuración básica desde variables de entorno
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Crear instancia de base de datos
db_manager = DatabaseManager()

# Crear instancia de gestor de PDFs
pdf_manager = PDFManager(db_manager)

# Cargar lista de materiales desde CSV
def cargar_materiales_csv():
    """Carga la lista de materiales desde el archivo CSV"""
    materiales = []
    try:
        ruta_csv = os.path.join(os.path.dirname(__file__), 'Lista de materiales.csv')
        with open(ruta_csv, 'r', encoding='utf-8-sig') as archivo:
            reader = csv.DictReader(archivo)
            for fila in reader:
                # Limpiar los headers que pueden tener espacios
                headers_limpios = {k.strip(): v for k, v in fila.items()}
                material = {
                    'descripcion': headers_limpios['Tipo de material'].strip(),
                    'peso': float(headers_limpios['Peso']),
                    'uom': headers_limpios['Ref de Peso'].strip()
                }
                materiales.append(material)
        print(f"Cargados {len(materiales)} materiales desde CSV")
    except Exception as e:
        print(f"Error cargando materiales: {e}")
        # Materiales por defecto si falla la carga
        materiales = [
            {'descripcion': 'Material personalizado', 'peso': 0, 'uom': 'Especificar'}
        ]
    return materiales

# Cargar materiales al iniciar la aplicación
LISTA_MATERIALES = cargar_materiales_csv()
print(f"✅ Cargados {len(LISTA_MATERIALES)} materiales desde CSV")

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
        
        # Generar nuevo número de cotización con revisión usando el sistema automático
        numero_original = datos['datosGenerales'].get('numeroCotizacion', '')
        if numero_original:
            # Usar la función del DatabaseManager para generar el número de revisión
            nuevo_numero = db_manager.generar_numero_revision(numero_original, nueva_revision)
            datos['datosGenerales']['numeroCotizacion'] = nuevo_numero
        else:
            # Si no hay número original, generar uno nuevo completo
            cliente = datos['datosGenerales'].get('cliente', '')
            vendedor = datos['datosGenerales'].get('vendedor', '')
            proyecto = datos['datosGenerales'].get('proyecto', '')
            nuevo_numero = db_manager.generar_numero_cotizacion(cliente, vendedor, proyecto, int(nueva_revision))
            datos['datosGenerales']['numeroCotizacion'] = nuevo_numero
        
        # Limpiar campos que no deben copiarse
        campos_a_limpiar = ['_id', 'fechaCreacion', 'timestamp', 'version']
        for campo in campos_a_limpiar:
            datos.pop(campo, None)
        
        # Agregar campo de actualización
        datos['datosGenerales']['actualizacionRevision'] = f"Revisión {nueva_revision} basada en cotización original"
        
        print(f"✅ Datos preparados para nueva revisión: {nuevo_numero}")
        return datos
        
    except Exception as e:
        print(f"❌ Error preparando nueva revisión: {e}")
        return None

# Registrar cierre de conexión al salir
atexit.register(db_manager.cerrar_conexion)

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
# RUTAS PRINCIPALES
# ============================================

@app.route("/", methods=["GET", "POST"])
def home():
    """Página principal - Recibe cotizaciones completas"""
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
                return jsonify({"error": resultado["error"]}), 500
                
        except Exception as e:
            print(f"Error en ruta principal: {e}")
            return jsonify({"error": "Error del servidor"}), 500

    return render_template("home.html")

@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    """Formulario de cotización"""
    if request.method == "POST":
        try:
            datos = request.get_json()
            print("Datos del formulario recibidos")
            
            # Guardar usando DatabaseManager
            resultado = db_manager.guardar_cotizacion(datos)
            
            if resultado["success"]:
                return jsonify({
                    "success": True,
                    "mensaje": "Cotización guardada correctamente",
                    "id": resultado["id"],
                    "numeroCotizacion": resultado["numeroCotizacion"]
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Error al guardar",
                    "detalle": resultado["error"]
                }), 500
                
        except Exception as e:
            print(f"Error en formulario: {e}")
            return jsonify({
                "success": False,
                "error": "Error del servidor",
                "detalle": str(e)
            }), 500
    
    # Verificar si es una nueva revisión
    revision_id = request.args.get('revision')
    datos_precargados = None
    
    if revision_id:
        # Cargar datos de la cotización original para nueva revisión
        resultado = db_manager.obtener_cotizacion(revision_id)
        if resultado.get('encontrado'):
            cotizacion_original = resultado['item']
            datos_precargados = preparar_datos_nueva_revision(cotizacion_original)
    
    return render_template("formulario.html", 
                         materiales=LISTA_MATERIALES, 
                         datos_precargados=datos_precargados)

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

# ============================================
# RUTAS DE BÚSQUEDA Y CONSULTA
# ============================================

@app.route("/buscar", methods=["POST"])
def buscar():
    """Buscar cotizaciones con paginación"""
    try:
        datos = request.get_json()
        query = datos.get("query", "")
        page = datos.get("page", 1)
        per_page = datos.get("per_page", int(os.getenv('DEFAULT_PAGE_SIZE', '20')))
        
        print(f"Buscando: '{query}' (pagina {page})")
        
        resultado = db_manager.buscar_cotizaciones(query, page, per_page)
        
        if "error" in resultado:
            return jsonify({"error": resultado["error"]}), 500
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"Error en busqueda: {e}")
        return jsonify({"error": "Error al buscar"}), 500

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
# GENERACIÓN DE PDF
# ============================================

@app.route("/generar_pdf", methods=["POST"])
def generar_pdf():
    """Genera PDF de la cotización usando el formato CWS oficial"""
    # Verificar si WeasyPrint está disponible
    if not WEASYPRINT_AVAILABLE:
        return jsonify({
            "error": "WeasyPrint no está instalado",
            "mensaje": "Para habilitar la generación de PDF, instala WeasyPrint siguiendo las instrucciones en INSTRUCCIONES_PDF.md",
            "solucion": "Ejecuta: pip install weasyprint"
        }), 503
    
    try:
        datos = request.get_json()
        numero_cotizacion = datos.get('numeroCotizacion')
        
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
            'terminos': condiciones.get('terminos', ''),
            'comentarios': condiciones.get('comentarios', ''),
            
            # Totales
            'subtotal': f"{subtotal:.2f}",
            'iva': f"{iva:.2f}",
            'total': f"{total:.2f}",
            
            # Logo path for PDF
            'logo_path': os.path.abspath(os.path.join('static', 'logo.png'))
        }
        
        # Renderizar el HTML
        print(f"Renderizando template PDF para: {numero_cotizacion}")
        print(f"Items count: {len(items)}")
        print(f"Cliente: {datos_generales.get('cliente', 'No encontrado')}")
        
        html_content = render_template('formato_pdf_cws.html', **template_data)
        
        # Generar PDF (método original que funcionaba)
        pdf_file = weasyprint.HTML(string=html_content).write_pdf()
        
        # Almacenar PDF en el sistema de archivos
        resultado_almacenamiento = pdf_manager.almacenar_pdf_nuevo(pdf_file, cotizacion)
        
        if not resultado_almacenamiento["success"]:
            print(f"Advertencia: No se pudo almacenar PDF: {resultado_almacenamiento.get('error')}")
            # Continuar con la descarga aunque el almacenamiento falle
        else:
            print(f"PDF almacenado exitosamente: {resultado_almacenamiento['nombre_archivo']}")
        
        # Crear respuesta para descarga
        pdf_buffer = io.BytesIO(pdf_file)
        pdf_buffer.seek(0)
        
        filename = f"Cotizacion_{numero_cotizacion.replace('/', '_').replace('-', '_')}.pdf"
        
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
        
        print(f"📄 Sirviendo PDF:")
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
        
        if "error" in resultado:
            return jsonify({"error": resultado["error"]}), 500
        
        if not resultado["encontrado"]:
            return jsonify({"error": f"PDF '{numero_cotizacion}' no encontrado"}), 404
        
        # Servir el archivo PDF
        ruta_completa = resultado["ruta_completa"]
        
        # Si es un PDF de Google Drive, descargar y servir
        if ruta_completa.startswith("gdrive://"):
            drive_id = resultado.get("drive_id")
            if not drive_id:
                return jsonify({"error": "ID de Google Drive no encontrado"}), 500
            
            print(f"📄 Sirviendo PDF desde Google Drive: {numero_cotizacion} (ID: {drive_id})")
            
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
    """Ver desglose detallado de cotización (vista actual de MongoDB)"""
    try:
        from urllib.parse import unquote
        numero_cotizacion = unquote(numero_cotizacion)
        
        print(f"Viendo desglose: '{numero_cotizacion}'")
        
        # Verificar que el PDF existe y tiene desglose
        resultado_pdf = pdf_manager.obtener_pdf(numero_cotizacion)
        
        if resultado_pdf.get("encontrado") and not resultado_pdf["registro"].get("tiene_desglose", False):
            # Es un PDF antiguo sin desglose
            return render_template_string("""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>Desglose no disponible</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .mensaje { background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 500px; }
                </style>
            </head>
            <body>
                <h1>Desglose no disponible</h1>
                <div class="mensaje">
                    <p>Esta cotización fue importada como PDF histórico.</p>
                    <p>El desglose detallado no está disponible.</p>
                    <p><strong>Número:</strong> {{ numero }}</p>
                </div>
                <a href="/">← Volver al inicio</a>
            </body>
            </html>
            """, numero=numero_cotizacion)
        
        # Usar la funcionalidad existente de ver cotización
        return ver_item(numero_cotizacion)
        
    except Exception as e:
        print(f"Error viendo desglose: {e}")
        return f"Error: {str(e)}", 500

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
    """Migra todas las cotizaciones del archivo offline a MongoDB"""
    try:
        # Verificar que estemos en modo online
        if db_manager.modo_offline:
            return jsonify({
                "error": "No se puede migrar: MongoDB no disponible",
                "solucion": "Verificar conexión a internet y credenciales MongoDB"
            }), 503
        
        # Cargar datos del archivo offline
        datos_offline = db_manager._cargar_datos_offline()
        cotizaciones_offline = datos_offline.get("cotizaciones", [])
        
        if not cotizaciones_offline:
            return jsonify({
                "mensaje": "No hay cotizaciones offline para migrar",
                "total_offline": 0,
                "total_mongodb": db_manager.collection.count_documents({})
            })
        
        migradas = 0
        errores = []
        duplicados = 0
        
        for i, cotizacion in enumerate(cotizaciones_offline):
            try:
                # Verificar si ya existe en MongoDB (por número de cotización)
                numero = cotizacion.get("numeroCotizacion")
                if numero:
                    existe = db_manager.collection.find_one({"numeroCotizacion": numero})
                    if existe:
                        duplicados += 1
                        continue
                
                # Limpiar el _id del archivo offline (MongoDB generará uno nuevo)
                cotizacion_limpia = cotizacion.copy()
                if "_id" in cotizacion_limpia:
                    del cotizacion_limpia["_id"]
                
                # Agregar timestamp de migración
                cotizacion_limpia["migrado_desde_offline"] = datetime.datetime.now().isoformat()
                
                # Insertar en MongoDB
                resultado = db_manager.collection.insert_one(cotizacion_limpia)
                if resultado.inserted_id:
                    migradas += 1
                    print(f"Migrada {i+1}/{len(cotizaciones_offline)}: {numero}")
                
            except Exception as e:
                error_msg = f"Error en cotización {i+1}: {str(e)[:100]}"
                errores.append(error_msg)
                print(f"{error_msg}")
        
        # Crear respaldo del archivo offline antes de limpiarlo
        import shutil
        fecha_backup = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_backup = f"cotizaciones_offline_backup_{fecha_backup}.json"
        shutil.copy(db_manager.archivo_datos, archivo_backup)
        
        # Limpiar archivo offline (opcional)
        datos_offline["cotizaciones"] = []
        datos_offline["metadata"]["migrado_a_mongodb"] = datetime.datetime.now().isoformat()
        datos_offline["metadata"]["total_migradas"] = migradas
        db_manager._guardar_datos_offline(datos_offline)
        
        return jsonify({
            "exito": True,
            "total_offline": len(cotizaciones_offline),
            "migradas": migradas,
            "duplicados": duplicados,
            "errores": len(errores),
            "detalles_errores": errores[:5],  # Solo primeros 5 errores
            "total_mongodb_actual": db_manager.collection.count_documents({}),
            "archivo_backup": archivo_backup,
            "mensaje": f"Migracion completada: {migradas} cotizaciones transferidas a MongoDB"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error durante migración: {str(e)}",
            "tipo": "error_migracion"
        }), 500

@app.route("/admin/sincronizar-offline")
def sincronizar_offline():
    """Sincroniza MongoDB hacia archivo offline como respaldo"""
    try:
        if db_manager.modo_offline:
            return jsonify({
                "error": "En modo offline, no se puede sincronizar desde MongoDB"
            }), 503
        
        # Obtener todas las cotizaciones de MongoDB
        cotizaciones_mongo = list(db_manager.collection.find().sort("timestamp", -1))
        
        # Convertir ObjectId a string para JSON
        for cot in cotizaciones_mongo:
            cot["_id"] = str(cot["_id"])
        
        # Crear estructura offline
        datos_offline = {
            "cotizaciones": cotizaciones_mongo,
            "metadata": {
                "sincronizado_desde_mongodb": datetime.datetime.now().isoformat(),
                "total_cotizaciones": len(cotizaciones_mongo),
                "version": os.getenv('APP_VERSION', '1.0.0'),
                "modo": "respaldo_mongodb"
            }
        }
        
        # Guardar archivo offline actualizado
        if db_manager._guardar_datos_offline(datos_offline):
            return jsonify({
                "exito": True,
                "total_sincronizadas": len(cotizaciones_mongo),
                "archivo": db_manager.archivo_datos,
                "mensaje": f"{len(cotizaciones_mongo)} cotizaciones sincronizadas a archivo offline"
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
                "archivo_datos": db_manager.archivo_datos,
                "metadata": datos.get("metadata", {})
            })
        else:
            # Modo online - MongoDB
            total_cotizaciones = db_manager.collection.count_documents({})
            
            # Estadísticas adicionales
            pipeline_clientes = [
                {"$group": {"_id": "$datosGenerales.cliente"}},
                {"$count": "total"}
            ]
            
            pipeline_vendedores = [
                {"$group": {"_id": "$datosGenerales.vendedor"}},
                {"$count": "total"}
            ]
            
            try:
                clientes_count = list(db_manager.collection.aggregate(pipeline_clientes))
                vendedores_count = list(db_manager.collection.aggregate(pipeline_vendedores))
                
                clientes_unicos = clientes_count[0]["total"] if clientes_count else 0
                vendedores_unicos = vendedores_count[0]["total"] if vendedores_count else 0
            except:
                clientes_unicos = "Error calculando"
                vendedores_unicos = "Error calculando"
            
            # Última cotización
            ultima = db_manager.collection.find_one(sort=[("timestamp", -1)])
            ultima_info = None
            if ultima:
                ultima_info = {
                    "numero": ultima.get("numeroCotizacion"),
                    "cliente": ultima.get("datosGenerales", {}).get("cliente"),
                    "fecha": ultima.get("fechaCreacion")
                }
            
            return jsonify({
                "modo": "ONLINE",
                "total_cotizaciones": total_cotizaciones,
                "clientes_unicos": clientes_unicos,
                "vendedores_unicos": vendedores_unicos,
                "database": db_manager.database_name,
                "collection": "cotizacions",
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
    """Actualiza cotizaciones existentes con timestamps faltantes"""
    try:
        print("Actualizando cotizaciones existentes con timestamps...")
        
        # Buscar cotizaciones sin timestamp o fechaCreacion
        filtro = {
            "$or": [
                {"timestamp": {"$exists": False}},
                {"timestamp": None},
                {"fechaCreacion": {"$exists": False}},
                {"fechaCreacion": None}
            ]
        }
        
        cotizaciones_sin_timestamp = list(db_manager.collection.find(filtro))
        
        print(f"Encontradas {len(cotizaciones_sin_timestamp)} cotizaciones sin timestamp")
        
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
                <h1>Actualizacion de Timestamps</h1>
                <div class="log">
                    <p class="info">Encontradas {len(cotizaciones_sin_timestamp)} cotizaciones sin timestamp</p>
        """
        
        if len(cotizaciones_sin_timestamp) == 0:
            resultado_html += """
                    <p class="success">Todas las cotizaciones ya tienen timestamps</p>
                </div>
                <p><a href="/">← Volver al inicio</a></p>
            </div>
        </body>
        </html>
            """
            return resultado_html
        
        # Actualizar cada cotización
        actualizadas = 0
        
        for cotizacion in cotizaciones_sin_timestamp:
            # Usar fecha actual como fallback
            ahora = datetime.datetime.now()
            
            # Preparar actualización
            update_data = {}
            
            if not cotizacion.get("timestamp"):
                update_data["timestamp"] = int(ahora.timestamp() * 1000)
            
            if not cotizacion.get("fechaCreacion"):
                update_data["fechaCreacion"] = ahora.isoformat()
            
            if not cotizacion.get("version"):
                update_data["version"] = os.getenv('APP_VERSION', '1.0.0')
            
            # Actualizar en MongoDB
            if update_data:
                resultado_update = db_manager.collection.update_one(
                    {"_id": cotizacion["_id"]},
                    {"$set": update_data}
                )
                
                if resultado_update.modified_count > 0:
                    actualizadas += 1
                    numero = cotizacion.get("numeroCotizacion", str(cotizacion["_id"]))
                    print(f"Actualizada: {numero}")
                    resultado_html += f'<p class="success">Actualizada: {numero}</p>\n'
        
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
    
    # Agregar esta ruta temporal a tu app.py para diagnosticar

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

@app.route("/buscar-texto-completo/<texto>")
def buscar_texto_completo(texto):
    """Busca un texto en TODOS los campos de las cotizaciones"""
    try:
        encontradas = []
        
        if db_manager.modo_offline:
            datos = db_manager._cargar_datos_offline()
            cotizaciones = datos.get("cotizaciones", [])
        else:
            cotizaciones = list(db_manager.collection.find())
            for cot in cotizaciones:
                cot["_id"] = str(cot["_id"])
        
        # Buscar en TODO el documento
        for cot in cotizaciones:
            # Convertir todo el documento a string
            doc_str = json.dumps(cot, ensure_ascii=False).lower()
            if texto.lower() in doc_str:
                encontradas.append({
                    "id": cot.get("_id"),
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
            return jsonify({"error": "No disponible en modo offline"}), 400
        
        # Obtener la última cotización
        ultima = db_manager.collection.find_one(
            sort=[("timestamp", -1)]
        )
        
        if ultima:
            ultima["_id"] = str(ultima["_id"])
            return jsonify({
                "encontrada": True,
                "id": ultima["_id"],
                "numero": ultima.get("numeroCotizacion"),
                "cliente": ultima.get("datosGenerales", {}).get("cliente"),
                "vendedor": ultima.get("datosGenerales", {}).get("vendedor"),
                "timestamp": ultima.get("timestamp"),
                "fecha": ultima.get("fechaCreacion")
            })
        else:
            return jsonify({"encontrada": False})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# EJECUTAR APLICACIÓN
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