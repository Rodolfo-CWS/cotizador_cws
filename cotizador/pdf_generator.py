"""
Generador de PDF profesional CWS usando ReportLab.
"""
import io
import os
import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, Image, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line as GraphicsLine
from cotizador._compat import REPORTLAB_AVAILABLE
from cotizador.utilities import wrap_description_text


def generar_pdf_reportlab(datos_cotizacion, texto_personalizado=None):
    """Genera PDF usando ReportLab con formato profesional CWS

    Args:
        datos_cotizacion: Dict con datos de la cotización
        texto_personalizado: Texto introductorio personalizado (opcional).
                            Si es None, se usa el texto genérico.
    """
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
    
    # Estilo para descripciones en tabla - soporta múltiples líneas
    description_style = ParagraphStyle(
        'DescriptionStyle',
        parent=styles['Normal'],
        fontSize=7,
        fontName='Helvetica',
        alignment=0,  # Alineación izquierda
        leftIndent=0,
        rightIndent=0,
        spaceAfter=0,
        spaceBefore=0,
        leading=8  # Espaciado entre líneas
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
    
    if texto_personalizado:
        # Usar texto generado por IA (ya viene con formato HTML de ReportLab)
        intro_text = texto_personalizado.replace("\n", "<br/>\n")
    else:
        intro_text = """Estimado Cliente,<br/>
        CWS Company presenta esta propuesta económica para el proyecto solicitado.
        Quedamos a la espera de su respuesta."""

    story.append(Paragraph(intro_text, intro_style))
    story.append(Spacer(1, 8))

    # ── IMAGEN DE REFERENCIA (OPCIONAL) ──────────────────────────
    imagen_referencia = datos_cotizacion.get('datosGenerales', {}).get('imagenReferencia', None)
    if imagen_referencia and imagen_referencia.get('url'):
        img_url = imagen_referencia.get('url', '')
        img_path = None
        _is_temp = False
        try:
            # Si es URL remota (Supabase Storage), descargar a archivo temporal
            if img_url.startswith('http'):
                import urllib.request
                import tempfile
                with urllib.request.urlopen(img_url, timeout=15) as response:
                    img_bytes = response.read()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    tmp.write(img_bytes)
                    img_path = tmp.name
                    _is_temp = True
            # Si es ruta local relativa (static/imagenes_referencia/...)
            elif img_url.startswith('static/'):
                candidate = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_url)
                if os.path.exists(candidate):
                    img_path = candidate
            # Ruta absoluta o relativa directa
            elif os.path.exists(img_url):
                img_path = img_url

            if img_path and os.path.exists(img_path):
                from reportlab.lib.utils import ImageReader
                img_reader = ImageReader(img_path)
                img_w, img_h = img_reader.getSize()

                # Escalar proporcionalmente (máx 4" ancho × 3" alto)
                max_w = 4 * inch
                max_h = 3 * inch
                scale = min(max_w / img_w, max_h / img_h, 1.0)
                display_w = img_w * scale
                display_h = img_h * scale

                img_flowable = Image(img_path, width=display_w, height=display_h)
                img_container = Table([[img_flowable]], colWidths=[7 * inch])
                img_container.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))

                caption_style = ParagraphStyle(
                    'ImageCaption',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Helvetica-Oblique',
                    textColor=colors.HexColor('#718096'),
                    alignment=1,  # Center
                    spaceAfter=4
                )
                nombre_img = imagen_referencia.get('nombre', 'Sin nombre')
                caption_text = f"<i>Imagen de referencia: {nombre_img}</i>"

                story.append(Spacer(1, 4))
                story.append(img_container)
                story.append(Paragraph(caption_text, caption_style))
                story.append(Spacer(1, 6))

                print(f"[PDF_IMAGEN] Imagen incrustada: {nombre_img} ({display_w:.0f}x{display_h:.0f}px)")
            else:
                print(f"[PDF_IMAGEN] No se pudo resolver ruta de imagen: {img_url}")
        except Exception as e:
            print(f"[PDF_IMAGEN] Error incrustando imagen (se omite): {e}")
        finally:
            if _is_temp and img_path and os.path.exists(img_path):
                try:
                    os.unlink(img_path)
                except Exception:
                    pass
    # ── FIN IMAGEN DE REFERENCIA ─────────────────────────────────

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
    
    # DEBUG: Diagnóstico completo de datos USD
    print(f"[PDF_DEBUG] ======= INICIO DIAGNÓSTICO PDF =======")
    print(f"[PDF_DEBUG] DATOS COMPLETOS: {datos_cotizacion}")
    print(f"[PDF_DEBUG] CONDICIONES RAW: {datos_cotizacion.get('condiciones', 'NO_ENCONTRADO')}")
    print(f"[PDF_DEBUG] CONDICIONES OBJECT: {condiciones}")
    print(f"[PDF_DEBUG] MONEDA DETECTADA: '{moneda}' (tipo: {type(moneda)})")
    print(f"[PDF_DEBUG] TIPO_CAMBIO STR: '{tipo_cambio_str}' (tipo: {type(tipo_cambio_str)})")
    print(f"[PDF_DEBUG] TIPO_CAMBIO FLOAT: {tipo_cambio} (tipo: {type(tipo_cambio)})")
    print(f"[PDF_DEBUG] CONDICIÓN USD: moneda==USD? {moneda == 'USD'}, tipo_cambio>0? {tipo_cambio > 0}, tipo_cambio!=1.0? {tipo_cambio != 1.0}")
    print(f"[PDF_DEBUG] APLICARÁ CONVERSIÓN? {moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0}")
    print(f"[PDF_DEBUG] ======= FIN DIAGNÓSTICO PDF =======")
    
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
            
            # Aplicar conversión USD si corresponde (lógica corregida)
            if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
                total_mostrar = total_mxn / tipo_cambio
                precio_unitario_mostrar = precio_unitario_mxn / tipo_cambio
                simbolo_item = 'USD $'
            else:
                total_mostrar = total_mxn
                precio_unitario_mostrar = precio_unitario_mxn
                simbolo_item = '$'
            
            # Agregar número de item y formatear datos con descripción envuelta
            descripcion_raw = item.get('descripcion', '')
            descripcion_wrapped = wrap_description_text(descripcion_raw)
            descripcion_paragraph = Paragraph(descripcion_wrapped, description_style)
            
            items_data.append([
                str(i + 1),  # Número de item
                descripcion_paragraph,  # Usar Paragraph con text wrapping
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
            
            # Alineación vertical para soporte de Paragraph multi-línea
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),    # Alineación vertical superior para todas las celdas
            
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
        
        # Aplicar conversión si es USD y tipo de cambio válido (lógica corregida)
        if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:  # Consistente con items
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
    
    # Campos de términos usando datos reales del formulario
    campos_terminos = [
        ('Moneda:', condiciones.get('moneda', 'MXN') if condiciones else 'MXN'),
        ('Tiempo de Entrega:', condiciones.get('tiempoEntrega', '') if condiciones else ''),
        ('Entregar En:', condiciones.get('entregaEn', '') if condiciones else ''),
        ('Términos de Pago:', (condiciones.get('terminos') or condiciones.get('condicionesPago', '')) if condiciones else ''),
        ('Comentarios:', (condiciones.get('comentarios') or condiciones.get('comentariosAdicionales', '')) if condiciones else '')
    ]
    
    # Agregar tipo de cambio si es USD
    if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
        campos_terminos.insert(1, ('Tipo de Cambio:', f'{tipo_cambio:.2f} MXN/USD'))
    
    # Usar datos reales del formulario, mostrar "A definir" solo si están vacíos
    for label, value in campos_terminos:
        if value and value.strip():  # Si tiene contenido real, usarlo
            terminos_data.append([label, value.strip()])
        else:  # Solo si está vacío, mostrar valor por defecto
            default_value = 'A definir' if 'Tiempo' in label or 'Entregar' in label or 'Términos' in label else ('Sin comentarios adicionales' if 'Comentarios' in label else 'MXN')
            terminos_data.append([label, default_value])
    
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
