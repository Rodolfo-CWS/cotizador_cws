from flask import Flask, render_template, request, jsonify, send_file
# Updated: Aug 14, 2025 - PDF fix deployed - Force redeploy

# Intentar importar generadores de PDF
WEASYPRINT_AVAILABLE = False
REPORTLAB_AVAILABLE = False

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    print("WeasyPrint disponible")
except ImportError:
    print("WeasyPrint no disponible")

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
    print("ReportLab disponible - Generacion de PDF habilitada con ReportLab")
except ImportError:
    print("ReportLab no disponible")

if not WEASYPRINT_AVAILABLE and not REPORTLAB_AVAILABLE:
    print("ADVERTENCIA: Ningún generador de PDF disponible")

import io
import datetime
import atexit
import os
import json  # ← IMPORTANTE
import csv  # Para leer archivo CSV de materiales
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
# SOLO SUPABASE - MongoDB eliminado completamente
from supabase_manager import SupabaseManager as DatabaseManager
from pdf_manager import PDFManager

# Configurar logging detallado para detectar fallos silenciosos
def configurar_logging():
    """Configura logging detallado para la aplicación"""
    # Crear directorio de logs si no existe
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurar logging principal
    log_file = os.path.join(log_dir, 'cotizador_fallos_criticos.log')
    
    # Handler rotativo para evitar archivos de log enormes
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB por archivo
        backupCount=5  # Mantener 5 archivos de respaldo
    )
    
    # Formato detallado de logs
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Configurar logger raíz
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # Logger específico para fallos críticos
    critical_logger = logging.getLogger('FALLOS_CRITICOS')
    critical_handler = RotatingFileHandler(
        os.path.join(log_dir, 'fallos_silenciosos_detectados.log'),
        maxBytes=5*1024*1024,
        backupCount=3
    )
    critical_handler.setFormatter(formatter)
    critical_logger.addHandler(critical_handler)
    critical_logger.setLevel(logging.ERROR)
    
    print(f"Logging configurado: {log_file}")
    return logger

# Configurar logging al inicio
configurar_logging()

# Cargar variables de entorno
load_dotenv()

# Crear aplicación Flask
app = Flask(__name__)

# Configuración básica desde variables de entorno
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Crear instancia de base de datos
print("Inicializando DatabaseManager (SupabaseManager)...")
db_manager = DatabaseManager()

# Validar estado de conexión al inicio
print(f"Estado de conexión:")
print(f"   Modo offline: {db_manager.modo_offline}")
if not db_manager.modo_offline:
    print(f"   Supabase conectado: {db_manager.supabase_url}")
    print(f"   Base de datos: PostgreSQL")
else:
    print(f"   Modo offline activo - usando JSON local")
    print(f"   Archivo offline: {db_manager.archivo_offline}")

# Obtener estadísticas iniciales
try:
    stats = db_manager.obtener_estadisticas()
    print(f"Estadísticas iniciales:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
except Exception as e:
    print(f"Error obteniendo estadísticas: {e}")

# Crear instancia de gestor de PDFs
try:
    from pdf_manager import PDFManager
    pdf_manager = PDFManager(db_manager)
    print("PDFManager inicializado exitosamente")
except Exception as e:
    print(f"Error inicializando PDFManager: {e}")
    pdf_manager = None

# Crear instancia de scheduler de sincronización
try:
    from sync_scheduler import SyncScheduler
    sync_scheduler = SyncScheduler(db_manager)
    print("SyncScheduler inicializado exitosamente")
    
    # Iniciar scheduler automático si está habilitado
    if sync_scheduler.auto_sync_enabled and sync_scheduler.is_available():
        sync_scheduler.iniciar()
    
except Exception as e:
    print(f"Error inicializando SyncScheduler: {e}")
    sync_scheduler = None

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
LISTA_MATERIALES = cargar_materiales_csv()
print(f"[OK] Cargados {len(LISTA_MATERIALES)} materiales desde CSV")

def generar_pdf_reportlab(datos_cotizacion):
    """Genera PDF usando ReportLab con formato profesional CWS"""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab no está disponible")
    
    # Crear buffer en memoria
    buffer = io.BytesIO()
    
    # Crear documento PDF con márgenes reducidos para página única
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.4*inch
    )
    story = []
    
    # Estilos profesionales
    styles = getSampleStyleSheet()
    
    # Estilo para el encabezado principal - reducido
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=6,
        alignment=1,  # Centro
        textColor=colors.HexColor('#2C5282'),  # Azul corporativo
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos - reducido
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        spaceBefore=6,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2D3748')
    )
    
    # Estilo para texto normal - reducido
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica'
    )
    
    # Extraer datos
    datos_generales = datos_cotizacion.get('datosGenerales', {})
    items = datos_cotizacion.get('items', [])
    condiciones = datos_cotizacion.get('condiciones', {})
    
    # ENCABEZADO CON LOGO Y INFORMACIÓN DE EMPRESA
    # Crear tabla para encabezado con logo y datos de empresa
    logo_path = "static/logo.png"
    from reportlab.platypus import Image
    
    # Intentar cargar logo, si no existe usar texto - tamaño reducido
    try:
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=0.8*inch, height=0.5*inch)
        else:
            logo = Paragraph("CWS<br/>COMPANY", header_style)
    except:
        logo = Paragraph("CWS<br/>COMPANY", header_style)
    
    # Información de la empresa - reducida
    empresa_info = Paragraph("""
        <b>CWS COMPANY SA DE CV</b><br/>
        Puerta de los monos 250<br/>
        78421 Villa de Pozos, SLP, México<br/>
        <b>COTIZACIÓN OFICIAL</b>
    """, ParagraphStyle(
        'EmpresaInfo',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=colors.HexColor('#2D3748'),
        alignment=0  # Izquierda
    ))
    
    # Información de cotización (derecha) - reducida
    fecha_actual = datetime.datetime.now().strftime('%d/%m/%Y')
    cotizacion_info = Paragraph(f"""
        <b>COTIZACIÓN</b><br/>
        <b>No. {datos_generales.get('numeroCotizacion', 'N/A')}</b><br/>
        Fecha: {fecha_actual}<br/>
        Rev. {datos_generales.get('revision', '1')}
    """, ParagraphStyle(
        'CotizacionInfo',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2C5282'),
        alignment=2  # Derecha
    ))
    
    # Tabla de encabezado con 3 columnas
    header_data = [[logo, empresa_info, cotizacion_info]]
    header_table = Table(header_data, colWidths=[1.5*inch, 3.5*inch, 2*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),  # Logo centrado
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),    # Empresa a la izquierda
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),   # Cotización a la derecha
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 6))
    
    # Línea separadora
    from reportlab.graphics.shapes import Drawing, Line as GraphicsLine
    line_drawing = Drawing(400, 1)
    line_drawing.add(GraphicsLine(0, 0, 400, 0, strokeColor=colors.HexColor('#2C5282'), strokeWidth=2))
    story.append(line_drawing)
    story.append(Spacer(1, 8))
    
    # INFORMACIÓN DEL CLIENTE - Diseño profesional en formato de tarjeta
    story.append(Paragraph("INFORMACIÓN DEL CLIENTE", subtitle_style))
    story.append(Spacer(1, 3))
    
    # Crear sección destacada para el proyecto - reducida
    if datos_generales.get('proyecto'):
        proyecto_style = ParagraphStyle(
            'ProyectoDestacado',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=colors.white,
            backColor=colors.HexColor('#2C5282'),
            borderPadding=5,
            alignment=1  # Centro
        )
        story.append(Paragraph(f"PROYECTO: {datos_generales.get('proyecto', '')}", proyecto_style))
        story.append(Spacer(1, 8))
    
    # Datos del cliente en formato mejorado
    info_data = [
        ['Cliente:', datos_generales.get('cliente', ''), 'Vendedor:', datos_generales.get('vendedor', '')],
        ['Atención A:', datos_generales.get('atencionA', ''), 'Contacto:', datos_generales.get('contacto', '')],
    ]
    
    # Agregar información de revisión si existe
    if datos_generales.get('revision', '1') != '1':
        info_data.append(['Revisión:', f"Rev. {datos_generales.get('revision', '1')}", 
                         'Actualización:', datos_generales.get('actualizacionRevision', '')])
    
    info_table = Table(info_data, colWidths=[1.2*inch, 2.8*inch, 1.2*inch, 2.8*inch])
    info_table.setStyle(TableStyle([
        # Estilo general - reducido
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        
        # Labels (columnas 0 y 2) - Estilo destacado
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2C5282')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#2C5282')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EDF2F7')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#EDF2F7')),
        
        # Valores (columnas 1 y 3)
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2D3748')),
        ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor('#2D3748')),
        
        # Alineación
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Bordes elegantes
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2C5282')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('BACKGROUND', (3, 0), (3, -1), colors.white),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 10))
    
    # TEXTO INTRODUCTORIO PROFESIONAL - reducido
    intro_style = ParagraphStyle(
        'IntroText',
        parent=styles['Normal'],
        fontSize=7,
        fontName='Helvetica',
        textColor=colors.HexColor('#2D3748'),
        alignment=4,  # Justificado
        spaceAfter=8,
        borderPadding=6,
        backColor=colors.HexColor('#F7FAFC'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=0.5
    )
    
    intro_text = """Estimado Cliente,<br/>
    CWS Company se complace en presentar esta propuesta económica para el proyecto solicitado. 
    Esperamos haber entendido sus requerimientos y permanecemos a la espera de su respuesta."""
    
    story.append(Paragraph(intro_text, intro_style))
    story.append(Spacer(1, 8))
    
    # Definir variables de moneda y tipo de cambio GLOBALMENTE
    condiciones = datos_cotizacion.get('condiciones', {})
    moneda = condiciones.get('moneda', 'MXN')
    tipo_cambio_str = condiciones.get('tipoCambio', '1.0')
    
    # SEGURIDAD: Validar tipo de cambio
    try:
        tipo_cambio = float(tipo_cambio_str) if tipo_cambio_str else 1.0
        if tipo_cambio <= 0 or tipo_cambio > 1000:
            tipo_cambio = 1.0  # Valor seguro por defecto
    except (ValueError, TypeError):
        tipo_cambio = 1.0  # Valor seguro por defecto
    
    # Inicializar conversion_note
    conversion_note = None
    
    # ITEMS - Tabla profesional mejorada
    if items:
        story.append(Paragraph("ITEMS DE COTIZACIÓN", subtitle_style))
        story.append(Spacer(1, 5))
        
        # Encabezado de tabla mejorado
        items_data = [['ITEM', 'DESCRIPCIÓN', 'CANT.', 'UOM', 'PRECIO UNITARIO', 'TOTAL']]
        subtotal = 0
        
        # Verificar conversión USD para items (mejorado con debug)
        for i, item in enumerate(items):
            cantidad = float(item.get('cantidad', 0))
            total_mxn = float(item.get('total', 0))
            precio_unitario_mxn = total_mxn / cantidad if cantidad > 0 else 0
            
            # Aplicar conversión USD si corresponde (lógica mejorada)
            if moneda == 'USD' and tipo_cambio > 1.0:  # Mejorado: tipo_cambio > 1.0 en lugar de != 1.0
                total_mostrar = total_mxn / tipo_cambio
                precio_unitario_mostrar = precio_unitario_mxn / tipo_cambio
                simbolo_item = 'USD $'
            else:
                total_mostrar = total_mxn
                precio_unitario_mostrar = precio_unitario_mxn
                simbolo_item = '$'
            
            # Agregar número de item y formatear datos
            items_data.append([
                str(i + 1),  # Número de item
                item.get('descripcion', ''),
                f"{cantidad:,.0f}",
                item.get('uom', ''),
                f"{simbolo_item}{precio_unitario_mostrar:,.2f}",
                f"{simbolo_item}{total_mostrar:,.2f}"
            ])
            subtotal += total_mxn  # Siempre sumar en MXN para cálculos internos
        
        items_table = Table(items_data, colWidths=[0.5*inch, 2.5*inch, 0.7*inch, 0.6*inch, 1.1*inch, 1.1*inch])
        items_table.setStyle(TableStyle([
            # Encabezado mejorado - reducido
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),  # ITEM
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # DESCRIPCIÓN
            ('ALIGN', (2, 0), (-1, 0), 'CENTER'), # CANT, UOM, PRECIO, TOTAL
            
            # Contenido con mejor alineación - reducido
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),   # ITEM número centrado
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Descripción a la izquierda
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),   # CANT y UOM centrados
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),   # Precios a la derecha
            
            # Estilo de fuentes para precios
            ('FONTNAME', (4, 1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (4, 1), (-1, -1), colors.HexColor('#2C5282')),
            
            # Padding mejorado - reducido
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            
            # Bordes profesionales
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2C5282')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
            
            # Línea destacada debajo del encabezado
            ('LINEBELOW', (0, 0), (-1, 0), 3, colors.HexColor('#1A365D')),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 8))
        
        # TOTALES - Caja profesional alineada a la derecha
        iva = subtotal * 0.16
        total = subtotal + iva
        
        # Las variables moneda y tipo_cambio ya están definidas arriba
        
        # Aplicar conversión si es USD y tipo de cambio válido (lógica mejorada)
        if moneda == 'USD' and tipo_cambio > 1.0:  # Consistente con items
            subtotal_mostrar = subtotal / tipo_cambio
            iva_mostrar = iva / tipo_cambio
            total_mostrar = total / tipo_cambio
            simbolo_moneda = 'USD $'
            
            # Crear tabla de totales con conversión USD
            totales_data = [
                ['Subtotal:', f"{simbolo_moneda}{subtotal_mostrar:,.2f}"],
                ['IVA (16%):', f"{simbolo_moneda}{iva_mostrar:,.2f}"],
                ['TOTAL:', f"{simbolo_moneda}{total_mostrar:,.2f}"]
            ]
            
            # Agregar nota de conversión al final
            conversion_note = f"Tipo de cambio: {tipo_cambio:.2f} MXN/USD"
        else:
            # Mantener formato original para MXN
            simbolo_moneda = '$'
            totales_data = [
                ['Subtotal:', f"{simbolo_moneda}{subtotal:,.2f}"],
                ['IVA (16%):', f"{simbolo_moneda}{iva:,.2f}"],
                ['TOTAL:', f"{simbolo_moneda}{total:,.2f}"]
            ]
            conversion_note = None
        
        # Tabla con ancho fijo alineada a la derecha
        totales_table = Table(totales_data, colWidths=[1.8*inch, 1.5*inch])
        totales_table.setStyle(TableStyle([
            # Alineación
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),  # Labels a la derecha
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Valores a la derecha
            
            # Fuentes - reducidas
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Total en bold
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            
            # Colores
            ('TEXTCOLOR', (0, 0), (-1, -2), colors.HexColor('#2D3748')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#2C5282')),
            
            # Padding - reducido
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            
            # Bordes
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2C5282')),
            ('BACKGROUND', (0, 0), (-1, -2), colors.HexColor('#F7FAFC')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EDF2F7')),
        ]))
        
        # Contenedor para alinear la tabla a la derecha
        from reportlab.platypus import KeepTogether
        totales_container = Table([[totales_table]], colWidths=[7*inch])
        totales_container.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'RIGHT')]))
        
        story.append(totales_container)
    
    # Agregar nota de conversión USD si aplica
    if moneda == 'USD' and conversion_note:
        story.append(Spacer(1, 6))
        conversion_style = ParagraphStyle(
            'ConversionNote',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=2,  # Alineación derecha
            spaceAfter=0
        )
        story.append(Paragraph(f"<i>{conversion_note}</i>", conversion_style))
    
    # TÉRMINOS Y CONDICIONES - Sección profesional (SIEMPRE VISIBLE)
    story.append(Spacer(1, 12))
    story.append(Paragraph("TÉRMINOS Y CONDICIONES", subtitle_style))
    story.append(Spacer(1, 5))
    
    # Preparar datos de términos (mejorado para garantizar contenido)
    terminos_data = []
    
    # Campos de términos con valores por defecto más informativos
    campos_terminos = [
        ('Moneda:', condiciones.get('moneda', 'MXN') if condiciones else 'MXN'),
        ('Tiempo de Entrega:', condiciones.get('tiempoEntrega', 'A definir') if condiciones else 'A definir'),
        ('Entregar En:', condiciones.get('entregaEn', 'A definir') if condiciones else 'A definir'),
        ('Términos de Pago:', condiciones.get('terminos', 'A definir') if condiciones else 'A definir'),
        ('Comentarios:', condiciones.get('comentarios', 'Sin comentarios adicionales') if condiciones else 'Sin comentarios adicionales')
    ]
    
    # Agregar tipo de cambio si es USD
    if moneda == 'USD' and tipo_cambio > 1.0:
        campos_terminos.insert(1, ('Tipo de Cambio:', f'{tipo_cambio:.2f} MXN/USD'))
    
    # Agregar TODOS los campos (ya no se omiten campos vacíos)
    for label, value in campos_terminos:
        # Garantizar que siempre hay un valor
        display_value = value.strip() if value and value.strip() else 'No especificado'
        terminos_data.append([label, display_value])
    
    # SIEMPRE crear la tabla (eliminar condicional)
    terminos_table = Table(terminos_data, colWidths=[2*inch, 5*inch])
    terminos_table.setStyle(TableStyle([
        # Fuentes y tamaños - reducidas
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        
        # Colores
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2D3748')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#4A5568')),
        
        # Alineación y padding - reducido
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        
        # Fondo y bordes sutiles
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#E2E8F0')),
    ]))
    
    story.append(terminos_table)
        
    # PIE DE PÁGINA PROFESIONAL - reducido
    story.append(Spacer(1, 12))
    
    # Línea separadora
    footer_line = Drawing(400, 1)
    footer_line.add(GraphicsLine(0, 0, 400, 0, strokeColor=colors.HexColor('#2C5282'), strokeWidth=1))
    story.append(footer_line)
    story.append(Spacer(1, 6))
    
    # Saludo de cierre - reducido
    closing_style = ParagraphStyle(
        'ClosingText',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=colors.HexColor('#2D3748'),
        alignment=0  # Izquierda
    )
    
    closing_text = """Atentamente,<br/>"""
    story.append(Paragraph(closing_text, closing_style))
    
    # Información del vendedor - reducida
    vendedor = datos_generales.get('vendedor', 'Equipo CWS')
    vendor_style = ParagraphStyle(
        'VendorInfo',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2C5282'),
        alignment=0
    )
    
    story.append(Paragraph(f"{vendedor}", vendor_style))
    story.append(Paragraph("CWS Company SA de CV", vendor_style))
    story.append(Spacer(1, 8))
    
    # Footer corporativo mejorado - reducido
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=7,
        fontName='Helvetica',
        textColor=colors.HexColor('#718096'),
        alignment=1,  # Centro
        borderPadding=4,
        backColor=colors.HexColor('#F7FAFC'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=0.5
    )
    
    footer_text = """
    <b>CWS Company SA de CV</b> | Puerta de los monos 250, 78421 Villa de Pozos, SLP, México<br/>
    Esta cotización es válida por 30 días a partir de la fecha de emisión<br/>
    <b>¡Gracias por confiar en CWS Company!</b>
    """
    
    story.append(Paragraph(footer_text, footer_style))
    
    # Construir PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer.getvalue()

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
        print(f"[REVISION] Número original: '{numero_original}' -> Nueva revisión: {nueva_revision}")
        
        if numero_original:
            # Usar la función del DatabaseManager para generar el número de revisión
            nuevo_numero = db_manager.generar_numero_revision(numero_original, nueva_revision)
            datos['datosGenerales']['numeroCotizacion'] = nuevo_numero
            print(f"[REVISION] Número actualizado: '{nuevo_numero}'")
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
                    
                    # Usar safe_float para conversión robusta de otros campos
                    otros = safe_float(item.get('otros', 0))
                    transporte = safe_float(item.get('transporte', 0))
                    instalacion = safe_float(item.get('instalacion', 0))
                    
                    total_item = total_materiales + otros + transporte + instalacion
                    item['total'] = round(total_item, 2)
                    
                    print(f"  [RECALC] Item total: {item.get('descripcion', 'Sin desc')} = {total_materiales} + {otros} + {transporte} + {instalacion} = {total_item}")
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
        return datos
        
    except Exception as e:
        print(f"[ERROR] Error preparando nueva revisión: {e}")
        import traceback
        traceback.print_exc()
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

    return render_template("home.html")

@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    """Formulario de cotización"""
    if request.method == "POST":
        try:
            datos = request.get_json()
            print("[FORM] FORMULARIO: Datos del formulario recibidos")
            print(f"[FORM] FORMULARIO: Cliente='{datos.get('datosGenerales', {}).get('cliente', 'N/A')}' | Items={len(datos.get('items', []))}")
            
            # VALIDACIÓN OBLIGATORIA BACKEND: Justificación de actualización para revisiones >= 2
            datos_generales = datos.get('datosGenerales', {})
            revision = safe_int(datos_generales.get('revision', 1))
            
            if revision >= 2:
                actualizacion_revision = datos_generales.get('actualizacionRevision', '').strip()
                if not actualizacion_revision or len(actualizacion_revision) < 10:
                    error_msg = "Justificación de actualización requerida para revisiones R2+. Debe tener al menos 10 caracteres."
                    print(f"[VALIDATION ERROR] {error_msg}")
                    return jsonify({
                        "error": error_msg,
                        "campo_requerido": "actualizacionRevision",
                        "revision": revision,
                        "longitud_actual": len(actualizacion_revision)
                    }), 400
            
            # Guardar usando DatabaseManager
            print("[FORM] FORMULARIO: Llamando a guardar_cotizacion...")
            resultado = db_manager.guardar_cotizacion(datos)
            print(f"[FORM] FORMULARIO: Resultado guardado = {resultado}")
            
            if resultado["success"]:
                numero_cotizacion = resultado.get('numero_cotizacion') or resultado.get('numeroCotizacion')
                print(f"[OK] FORMULARIO: Guardado exitoso - Numero: {numero_cotizacion}")
                
                # ✅ LOG CRÍTICO: Cotización guardada exitosamente
                logging.info(f"COTIZACION_GUARDADA: {numero_cotizacion} - Cliente: {datos.get('datosGenerales', {}).get('cliente', 'N/A')}")
                
                # Verificar si es un fallo silencioso detectado
                if resultado.get("tipo_error") == "fallo_silencioso":
                    critical_logger = logging.getLogger('FALLOS_CRITICOS')
                    critical_logger.error(f"FALLO_SILENCIOSO_DETECTADO: {numero_cotizacion} - {resultado.get('error', 'Error desconocido')}")
                    
                    return jsonify({
                        "error": "Error crítico en guardado - datos no persistieron",
                        "tipo_error": "fallo_silencioso",
                        "numero_cotizacion": numero_cotizacion
                    }), 500
                
                # AGREGAR: Generar PDF automáticamente después de guardar
                pdf_resultado = None
                pdf_error = None
                
                try:
                    print(f"[PDF] FORMULARIO: Generando PDF automáticamente para {numero_cotizacion}")
                    
                    if pdf_manager and (WEASYPRINT_AVAILABLE or REPORTLAB_AVAILABLE):
                        # Buscar la cotización recién guardada
                        cotizacion_busqueda = db_manager.obtener_cotizacion(numero_cotizacion)
                        
                        if cotizacion_busqueda["encontrado"]:
                            cotizacion = cotizacion_busqueda["item"]
                            
                            # Generar PDF usando ReportLab
                            try:
                                pdf_data = generar_pdf_reportlab(cotizacion)
                                
                                # Almacenar en Google Drive y localmente
                                resultado_almacenamiento = pdf_manager.almacenar_pdf_nuevo(
                                    pdf_data, 
                                    cotizacion
                                )
                                
                                pdf_resultado = resultado_almacenamiento
                                print(f"[PDF] FORMULARIO: PDF generado y almacenado exitosamente")
                                
                            except Exception as pdf_gen_error:
                                print(f"[ERROR] FORMULARIO: Error generando PDF: {pdf_gen_error}")
                                pdf_error = str(pdf_gen_error)
                        else:
                            print(f"[ERROR] FORMULARIO: No se pudo recuperar cotización para PDF: {numero_cotizacion}")
                            pdf_error = "No se pudo recuperar la cotización para generar PDF"
                    else:
                        print(f"[WARNING] FORMULARIO: PDF Manager no disponible o generadores PDF no instalados")
                        pdf_error = "Generadores de PDF no disponibles"
                        
                except Exception as e:
                    print(f"[ERROR] FORMULARIO: Error en generación automática de PDF: {e}")
                    pdf_error = str(e)
                
                # Respuesta con información de PDF
                respuesta = {
                    "success": True,
                    "mensaje": "Cotización guardada correctamente",
                    "numeroCotizacion": numero_cotizacion,
                    "pdf_generado": pdf_resultado is not None,
                    "pdf_error": pdf_error
                }
                
                # Agregar ID solo si existe (modo online)
                if "id" in resultado:
                    respuesta["id"] = resultado["id"]
                
                if pdf_resultado:
                    respuesta["pdf_info"] = {
                        "ruta_local": pdf_resultado.get("ruta_local"),
                        "google_drive": pdf_resultado.get("google_drive", {})
                    }
                
                return jsonify(respuesta)
            else:
                print(f"[ERROR] FORMULARIO: Error al guardar - {resultado.get('error')}")
                return jsonify({
                    "success": False,
                    "error": "Error al guardar",
                    "detalle": resultado["error"]
                }), 500
                
        except Exception as e:
            print(f"[CRITICAL] FORMULARIO: ERROR CRITICO - {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": "Error del servidor",
                "detalle": str(e)
            }), 500
    
    # Verificar si es una nueva revisión
    revision_id = request.args.get('revision')
    datos_precargados = None
    
    if revision_id:
        print(f"[REVISION] Solicitando nueva revisión de: '{revision_id}'")
        # Cargar datos de la cotización original para nueva revisión
        resultado = db_manager.obtener_cotizacion(revision_id)
        if resultado.get('encontrado'):
            cotizacion_original = resultado['item']
            print(f"[REVISION] Cotización original encontrada: {cotizacion_original.get('numeroCotizacion', 'N/A')}")
            datos_precargados = preparar_datos_nueva_revision(cotizacion_original)
            print(f"[REVISION] Datos precargados preparados - Nueva revisión: {datos_precargados.get('datosGenerales', {}).get('revision', 'N/A')}")
        else:
            print(f"[REVISION] ⚠️ Cotización original no encontrada para: '{revision_id}'")
    
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
        "mongodb": {
            "estado": "offline" if db_manager.modo_offline else "online",
            "uri_configurada": bool(os.getenv('MONGODB_URI')),
            "variables_componentes": {
                "username": bool(os.getenv('MONGO_USERNAME')),
                "password": bool(os.getenv('MONGO_PASSWORD')),
                "cluster": bool(os.getenv('MONGO_CLUSTER')),
                "database": bool(os.getenv('MONGO_DATABASE'))
            }
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
            # Test rápido de MongoDB
            test_ping = db_manager.client.admin.command('ping')
            diagnostico["mongodb"]["test_ping"] = "exitoso"
            diagnostico["mongodb"]["database_name"] = db_manager.database_name
            diagnostico["mongodb"]["total_cotizaciones"] = db_manager.collection.count_documents({})
        except Exception as e:
            diagnostico["mongodb"]["test_ping"] = f"fallo: {str(e)[:100]}"
    
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
        'mongodb_uri_set': bool(os.getenv('MONGODB_URI')),
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
            
            # Logo path for PDF (solo para WeasyPrint)
            'logo_path': 'static/logo.png'
        }
        
        print(f"Generando PDF para: {numero_cotizacion}")
        print(f"Items count: {len(items)}")
        print(f"Cliente: {datos_generales.get('cliente', 'No encontrado')}")
        
        # Intentar con ReportLab primero (más estable)
        if REPORTLAB_AVAILABLE:
            print("Generando PDF con ReportLab")
            pdf_data = generar_pdf_reportlab(cotizacion)
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
        
        if "error" in resultado:
            return jsonify({"error": resultado["error"]}), 500
        
        if not resultado["encontrado"]:
            return jsonify({"error": f"PDF '{numero_cotizacion}' no encontrado en Supabase Storage, Google Drive ni localmente"}), 404
        
        # Servir el archivo PDF
        ruta_completa = resultado["ruta_completa"]
        tipo_fuente = resultado.get("tipo", "local")
        
        # Si es un PDF de Supabase Storage, redirigir a su URL directa
        if (tipo_fuente in ["supabase_storage"] or 
            ruta_completa.startswith("https://")):
            
            fuente_nombre = {
                "supabase_storage": "Supabase Storage",
                # Cloudinary eliminado
            }.get(tipo_fuente, "URL directa")
            
            print(f"PDF: Redirigiendo a PDF de {fuente_nombre}: {numero_cotizacion}")
            print(f"   URL: {ruta_completa}")
            
            # Redirigir directamente a la URL
            from flask import redirect
            return redirect(ruta_completa)
        
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
        print(f"[DESGLOSE] Error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error procesando desglose: {str(e)}", 500

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

@app.route("/debug-env")
def debug_env():
    """Diagnostico de variables de entorno para Render"""
    import os
    
    # Verificar variables criticas
    mongodb_uri = os.getenv('MONGODB_URI')
    env_check = {
        'SECRET_KEY': 'CONFIGURADO' if os.getenv('SECRET_KEY') else 'FALTA',
        'MONGODB_URI': 'CONFIGURADO' if mongodb_uri else 'FALTA',
        'MONGODB_URI_PREVIEW': f"{mongodb_uri[:50]}..." if mongodb_uri else 'N/A',
        'RENDER': 'SI' if os.getenv('RENDER') else 'NO',
        'PORT': os.getenv('PORT', 'No configurado'),
        'entorno': 'RENDER' if os.getenv('RENDER') else 'LOCAL'
    }
    
    # Estado de MongoDB
    env_check['mongodb_modo_offline'] = db_manager.modo_offline
    
    # Intentar contar cotizaciones
    try:
        if not db_manager.modo_offline:
            env_check['mongodb_total_cotizaciones'] = db_manager.collection.count_documents({})
            env_check['mongodb_conexion'] = 'EXITOSA'
        else:
            env_check['mongodb_total_cotizaciones'] = 'N/A'
            env_check['mongodb_conexion'] = 'FALLO - MODO OFFLINE'
    except Exception as e:
        env_check['mongodb_total_cotizaciones'] = 'ERROR'
        env_check['mongodb_conexion'] = f'ERROR: {str(e)}'
    
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