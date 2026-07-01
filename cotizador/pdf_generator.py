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


# ── Constantes de color corporativo (matices discretos azul + naranja) ──
CORPORATE_INDIGO = colors.HexColor('#1e293b')       # slate-800, sutil azul
CORPORATE_INDIGO_DARK = colors.HexColor('#0f172a')  # slate-900
CORPORATE_INDIGO_LIGHT = colors.HexColor('#f5f4f1') # sutil naranja (warm stone)
TEXT_DARK = colors.HexColor('#1e293b')
TEXT_GRAY = colors.HexColor('#78716c')              # stone-500, sutil naranja
TEXT_BODY = colors.HexColor('#44403c')              # stone-700
BORDER_GRAY = colors.HexColor('#d6d3d1')            # stone-300, sutil naranja
BG_LIGHT = colors.HexColor('#faf9f7')              # casi blanco, matiz cálido
BG_STRIPE = colors.HexColor('#f5f4f1')             # rayas suaves cálidas
WHITE = colors.white


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

    # Crear documento PDF con márgenes modernos
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=0.55*inch,
        bottomMargin=0.45*inch
    )
    story = []

    # Estilos base
    styles = getSampleStyleSheet()

    # ── ESTILOS ──
    header_style = ParagraphStyle(
        'CustomHeader', parent=styles['Normal'],
        fontSize=14, spaceAfter=6, alignment=1,
        textColor=CORPORATE_INDIGO, fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'SubTitle', parent=styles['Normal'],
        fontSize=11, spaceAfter=8, spaceBefore=8,
        fontName='Helvetica-Bold', textColor=TEXT_DARK
    )

    normal_style = ParagraphStyle(
        'CustomNormal', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica', textColor=TEXT_BODY
    )

    description_style = ParagraphStyle(
        'DescriptionStyle', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        alignment=0, leftIndent=0, rightIndent=0,
        spaceAfter=0, spaceBefore=0, leading=11
    )

    # Extraer datos
    datos_generales = datos_cotizacion.get('datosGenerales', {})
    items = datos_cotizacion.get('items', [])

    # ── ENCABEZADO REDISEÑADO ──
    logo_path = "static/logo.png"

    # Logo
    try:
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=1.0*inch, height=0.65*inch)
        else:
            logo = Paragraph("CWS<br/>COMPANY", header_style)
    except:
        logo = Paragraph("CWS<br/>COMPANY", header_style)

    # Empresa al lado del logo, dirección en font pequeño
    empresa_info = Paragraph("""
        <b>CWS COMPANY SA DE CV</b><br/>
        <font size="7">Puerta de los monos 250, 78421 Villa de Pozos, SLP</font>
    """, ParagraphStyle(
        'EmpresaInfo', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_DARK, alignment=0, leading=12
    ))

    # Logo + empresa juntos en la izquierda
    left_block_data = [[logo, empresa_info]]
    left_block = Table(left_block_data, colWidths=[1.15*inch, 2.85*inch])
    left_block.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
    ]))

    # Cotización alineada a la derecha
    fecha_actual = datetime.datetime.now().strftime('%d/%m/%Y')
    cotizacion_info = Paragraph(f"""
        <b>COTIZACIÓN</b><br/>
        <b>No. {datos_generales.get('numeroCotizacion', 'N/A')}</b><br/>
        Fecha: {fecha_actual} &nbsp;|&nbsp; Rev. {datos_generales.get('revision', '1')}
    """, ParagraphStyle(
        'CotizacionInfo', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        textColor=CORPORATE_INDIGO, alignment=2
    ))

    # Header en 2 columnas: [Logo+Empresa] [Datos Cotización]
    header_data = [[left_block, cotizacion_info]]
    header_table = Table(header_data, colWidths=[4.0*inch, 3.0*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 4))

    # ── INFORMACIÓN DEL CLIENTE ──
    # Proyecto destacado
    if datos_generales.get('proyecto'):
        proyecto_style = ParagraphStyle(
            'ProyectoDestacado', parent=styles['Normal'],
            fontSize=10, fontName='Helvetica-Bold',
            textColor=WHITE, backColor=CORPORATE_INDIGO,
            borderPadding=6, alignment=1
        )
        story.append(Paragraph(f"PROYECTO: {datos_generales.get('proyecto', '')}", proyecto_style))
        story.append(Spacer(1, 6))

    # Estilo para valores del cliente con word-wrap
    client_value_style = ParagraphStyle(
        'ClientValue', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_DARK, alignment=0,
        leading=11, wordWrap='CJK'
    )

    # Datos del cliente con Paragraph para wrap
    def p(text):
        return Paragraph(text or '', client_value_style)

    info_data = [
        ['Cliente:', p(datos_generales.get('cliente', '')), 'Vendedor:', p(datos_generales.get('vendedor', ''))],
        ['Atención A:', p(datos_generales.get('atencionA', '')), 'Contacto:', p(datos_generales.get('contacto', ''))],
    ]

    if datos_generales.get('revision', '1') != '1':
        info_data.append(['Revisión:', p(f"Rev. {datos_generales.get('revision', '1')}"),
                         'Actualización:', p(datos_generales.get('actualizacionRevision', ''))])

    info_table = Table(info_data, colWidths=[1.0*inch, 2.65*inch, 1.0*inch, 2.65*inch])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),

        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), CORPORATE_INDIGO),
        ('TEXTCOLOR', (2, 0), (2, -1), CORPORATE_INDIGO),
        ('BACKGROUND', (0, 0), (0, -1), CORPORATE_INDIGO_LIGHT),
        ('BACKGROUND', (2, 0), (2, -1), CORPORATE_INDIGO_LIGHT),

        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
        ('TEXTCOLOR', (3, 0), (3, -1), TEXT_DARK),

        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),

        ('BOX', (0, 0), (-1, -1), 0.75, CORPORATE_INDIGO),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('BACKGROUND', (3, 0), (3, -1), WHITE),
    ]))

    story.append(info_table)
    story.append(Spacer(1, 10))

    # ── TEXTO INTRODUCTORIO ──
    intro_style = ParagraphStyle(
        'IntroText', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_BODY, alignment=4,
        spaceAfter=8, leading=13
    )

    if texto_personalizado:
        intro_text = texto_personalizado.replace("\n", "<br/>\n")
    else:
        intro_text = """Estimado Cliente,<br/>
        CWS Company presenta esta propuesta económica para el proyecto solicitado.
        Quedamos a la espera de su respuesta."""

    story.append(Paragraph(intro_text, intro_style))
    story.append(Spacer(1, 4))

    # ── MONEDA Y TIPO DE CAMBIO ──
    condiciones = datos_cotizacion.get('condiciones', {})
    moneda = condiciones.get('moneda', 'MXN')
    tipo_cambio_str = condiciones.get('tipoCambio', '1.0')

    try:
        tipo_cambio = float(tipo_cambio_str) if tipo_cambio_str else 1.0
        if tipo_cambio <= 0 or tipo_cambio > 1000:
            tipo_cambio = 1.0
    except (ValueError, TypeError):
        tipo_cambio = 1.0

    conversion_note = None

    # Debug info
    print(f"[PDF_DEBUG] MONEDA: '{moneda}', TIPO_CAMBIO: {tipo_cambio}")

    # ── ITEMS ──
    if items:
        story.append(Paragraph("ITEMS DE COTIZACIÓN", subtitle_style))
        story.append(Spacer(1, 6))

        items_data = [['ITEM', 'DESCRIPCIÓN', 'CANT.', 'UOM', 'PRECIO UNIT.', 'TOTAL']]
        subtotal = 0

        for i, item in enumerate(items):
            cantidad = float(item.get('cantidad', 0))
            total_mxn = float(item.get('total', 0))
            precio_unitario_mxn = total_mxn / cantidad if cantidad > 0 else 0

            if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
                total_mostrar = total_mxn / tipo_cambio
                precio_unitario_mostrar = precio_unitario_mxn / tipo_cambio
                simbolo_item = 'USD $'
            else:
                total_mostrar = total_mxn
                precio_unitario_mostrar = precio_unitario_mxn
                simbolo_item = '$'

            descripcion_raw = item.get('descripcion', '')
            descripcion_wrapped = wrap_description_text(descripcion_raw)
            descripcion_paragraph = Paragraph(descripcion_wrapped, description_style)

            items_data.append([
                str(i + 1),
                descripcion_paragraph,
                f"{cantidad:,.0f}",
                item.get('uom', ''),
                f"{simbolo_item}{precio_unitario_mostrar:,.2f}",
                f"{simbolo_item}{total_mostrar:,.2f}"
            ])
            subtotal += total_mxn

        # Columnas optimizadas: descripción más ancha, total más ancho
        items_table = Table(items_data, colWidths=[0.4*inch, 3.3*inch, 0.55*inch, 0.5*inch, 1.1*inch, 1.45*inch])
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), CORPORATE_INDIGO),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (-1, 0), 'CENTER'),

            # Contenido
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),

            # Precios en bold índigo
            ('FONTNAME', (4, 1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (4, 1), (-1, -1), CORPORATE_INDIGO),

            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),

            # Bordes
            ('BOX', (0, 0), (-1, -1), 0.75, CORPORATE_INDIGO),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ]))

        story.append(items_table)
        story.append(Spacer(1, 10))

        # ── TOTALES EN BOX DESTACADO ──
        iva = subtotal * 0.16
        total = subtotal + iva

        if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
            subtotal_mostrar = subtotal / tipo_cambio
            iva_mostrar = iva / tipo_cambio
            total_mostrar = total / tipo_cambio
            simbolo_moneda = 'USD $'
            conversion_note = f"Tipo de cambio: {tipo_cambio:.2f} MXN/USD"
        else:
            subtotal_mostrar = subtotal
            iva_mostrar = iva
            total_mostrar = total
            simbolo_moneda = '$'
            conversion_note = None

        totales_data = [
            ['Subtotal:', f"{simbolo_moneda}{subtotal_mostrar:,.2f}"],
            ['IVA (16%):', f"{simbolo_moneda}{iva_mostrar:,.2f}"],
            ['TOTAL:', f"{simbolo_moneda}{total_mostrar:,.2f}"]
        ]

        totales_table = Table(totales_data, colWidths=[1.8*inch, 1.6*inch])
        totales_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),

            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, -1), (-1, -1), 11),

            ('TEXTCOLOR', (0, 0), (-1, -2), TEXT_DARK),
            ('TEXTCOLOR', (0, -1), (-1, -1), CORPORATE_INDIGO),

            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),

            ('BACKGROUND', (0, 0), (-1, -2), BG_LIGHT),
            ('BACKGROUND', (0, -1), (-1, -1), CORPORATE_INDIGO_LIGHT),
            ('LINEABOVE', (0, -1), (-1, -1), 2, CORPORATE_INDIGO),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_GRAY),
        ]))

        totales_container = Table([[totales_table]], colWidths=[6.5*inch])
        totales_container.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'RIGHT')]))

        story.append(totales_container)

    # ── NOTA DE CONVERSIÓN USD ──
    if moneda == 'USD' and conversion_note:
        story.append(Spacer(1, 6))
        conversion_style = ParagraphStyle(
            'ConversionNote', parent=styles['Normal'],
            fontSize=9, textColor=TEXT_GRAY,
            alignment=2, spaceAfter=0
        )
        story.append(Paragraph(f"<i>{conversion_note}</i>", conversion_style))

    # ── TÉRMINOS Y CONDICIONES ──
    story.append(Spacer(1, 4))
    story.append(Paragraph("TÉRMINOS Y CONDICIONES", subtitle_style))
    story.append(Spacer(1, 6))

    terms_label_style = ParagraphStyle(
        'TermsLabel', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        textColor=TEXT_DARK, alignment=0, leading=12
    )
    terms_value_style = ParagraphStyle(
        'TermsValue', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_BODY, alignment=0,
        leading=12, wordWrap='CJK'
    )

    def tv(value, default=''):
        """Formatea valor de término con fallback"""
        v = value.strip() if (value and value.strip()) else default
        return Paragraph(v, terms_value_style)

    def tl(label):
        return Paragraph(label, terms_label_style)

    moneda_val = condiciones.get('moneda', 'MXN') if condiciones else 'MXN'
    tiempo_val = condiciones.get('tiempoEntrega', '') if condiciones else ''
    entrega_val = condiciones.get('entregaEn', '') if condiciones else ''
    pago_val = (condiciones.get('terminos') or condiciones.get('condicionesPago', '')) if condiciones else ''
    comentarios_val = (condiciones.get('comentarios') or condiciones.get('comentariosAdicionales', '')) if condiciones else ''

    # Pares en 2 filas: layout 4 columnas
    terminos_data = [
        [tl('Moneda:'), tv(moneda_val, 'MXN'),
         tl('Tiempo de Entrega:'), tv(tiempo_val, 'A definir')],
        [tl('Entregar En:'), tv(entrega_val, 'A definir'),
         tl('Términos de Pago:'), tv(pago_val, 'A definir')],
    ]

    # USD: agregar fila de tipo de cambio
    if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
        terminos_data.append([
            tl('Tipo de Cambio:'), tv(f'{tipo_cambio:.2f} MXN/USD', ''), '', ''
        ])

    # Comentarios en fila aparte (full width)
    terminos_data.append([
        tl('Comentarios:'), tv(comentarios_val, 'Sin comentarios adicionales'), '', ''
    ])

    # Columnas asimétricas: labels derechos más anchos ("Tiempo de Entrega:", "Términos de Pago:")
    terms_col_L = 1.0*inch
    terms_val_L = 2.5*inch
    terms_col_R = 1.45*inch
    terms_val_R = 2.35*inch
    terminos_table = Table(terminos_data, colWidths=[terms_col_L, terms_val_L, terms_col_R, terms_val_R])

    # Estilo base
    base_style = [
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
    ]

    # Comentarios: combinar celdas 1-3 en la última fila
    last_row = len(terminos_data) - 1
    base_style.append(('SPAN', (1, last_row), (-1, last_row)))

    terminos_table.setStyle(TableStyle(base_style))

    story.append(terminos_table)

    # ── IMAGEN DE REFERENCIA ──
    imagen_referencia = datos_cotizacion.get('datosGenerales', {}).get('imagenReferencia', None)
    if imagen_referencia and imagen_referencia.get('url'):
        img_url = imagen_referencia.get('url', '')
        img_path = None
        _is_temp = False
        try:
            if img_url.startswith('http'):
                import urllib.request
                import tempfile
                req = urllib.request.Request(img_url, headers={'User-Agent': 'CWS-Cotizador/1.0'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    content_type = response.headers.get('Content-Type', '')
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")
                    # Verificar que sea una imagen, no HTML de login/error
                    if 'text/html' in content_type:
                        raise Exception(f"Recibido HTML en vez de imagen (URL requiere auth?). Content-Type: {content_type}")
                    img_bytes = response.read()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    tmp.write(img_bytes)
                    img_path = tmp.name
                    _is_temp = True
            elif img_url.startswith('/static/') or img_url.startswith('static/'):
                # Soporta tanto /static/... como static/...
                clean_url = img_url.lstrip('/')
                candidate = os.path.join(os.path.dirname(os.path.dirname(__file__)), clean_url)
                if os.path.exists(candidate):
                    img_path = candidate
            elif os.path.exists(img_url):
                img_path = img_url

            if img_path and os.path.exists(img_path):
                from reportlab.lib.utils import ImageReader
                img_reader = ImageReader(img_path)
                img_w, img_h = img_reader.getSize()

                max_w = 4 * inch
                max_h = 3 * inch
                scale = min(max_w / img_w, max_h / img_h, 1.0)
                display_w = img_w * scale
                display_h = img_h * scale

                img_flowable = Image(img_path, width=display_w, height=display_h)
                img_container = Table([[img_flowable]], colWidths=[6.5 * inch])
                img_container.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))

                story.append(Spacer(1, 6))
                story.append(Paragraph("IMAGEN DE REFERENCIA", subtitle_style))
                story.append(Spacer(1, 4))
                story.append(img_container)
                story.append(Spacer(1, 4))

                print(f"[PDF_IMAGEN] Imagen incrustada ({display_w:.0f}x{display_h:.0f}px)")
            else:
                print(f"[PDF_IMAGEN] No se pudo resolver ruta: {img_url}")
        except Exception as e:
            print(f"[PDF_IMAGEN] Error incrustando imagen (se omite): {e}")
        finally:
            if _is_temp and img_path and os.path.exists(img_path):
                try:
                    os.unlink(img_path)
                except Exception:
                    pass

    # ── PIE DE PÁGINA ──
    story.append(Spacer(1, 8))

    vendedor = datos_generales.get('vendedor', 'Equipo CWS')

    closing_style = ParagraphStyle(
        'ClosingText', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_DARK, alignment=0
    )
    story.append(Paragraph(f"Atentamente,<br/><b>{vendedor}</b> — CWS Company SA de CV", closing_style))
    story.append(Spacer(1, 10))

    footer_style = ParagraphStyle(
        'FooterText', parent=styles['Normal'],
        fontSize=7.5, fontName='Helvetica',
        textColor=TEXT_GRAY, alignment=1,
        borderPadding=5, backColor=BG_LIGHT,
        borderColor=BORDER_GRAY, borderWidth=0.5
    )

    footer_text = """
    <b>CWS Company SA de CV</b> &nbsp;|&nbsp; Puerta de los monos 250, 78421 Villa de Pozos, SLP, México<br/>
    Esta cotización es válida por 30 días a partir de la fecha de emisión &nbsp;|&nbsp; <b>¡Gracias por confiar en CWS Company!</b>
    """

    story.append(Paragraph(footer_text, footer_style))

    # Construir PDF
    doc.build(story)
    buffer.seek(0)

    return buffer.getvalue()


def generar_desglose_pdf_reportlab(datos_cotizacion):
    """Genera un PDF COMPACTO tipo lista/resumen del desglose — optimizado para compartir.

    A diferencia del PDF formal (generar_pdf_reportlab), este es:
    - Sin logo ni branding pesado
    - Sin texto introductorio
    - Sin imagen de referencia
    - Sin pie de página extenso
    - Layout de 1 sola columna tipo "lista de materiales"
    - Legible en pantalla de celular (ancho A4, texto grande)
    - Ideal para WhatsApp, email, screenshots

    Args:
        datos_cotizacion: Dict con datos de la cotización (misma estructura que el PDF formal)
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab no está disponible")

    buffer = io.BytesIO()

    # Márgenes más amplios para lectura en móvil
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.4*inch,
        bottomMargin=0.35*inch
    )
    story = []

    styles = getSampleStyleSheet()

    # ── ESTILOS COMPACTOS ──
    title_style = ParagraphStyle(
        'DesgloseTitle', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold',
        textColor=CORPORATE_INDIGO, alignment=1,
        spaceAfter=2, leading=16
    )

    subtitle_style = ParagraphStyle(
        'DesgloseSubtitle', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_GRAY, alignment=1,
        spaceAfter=10
    )

    section_style = ParagraphStyle(
        'DesgloseSection', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=CORPORATE_INDIGO, spaceAfter=6, spaceBefore=10,
        leading=13
    )

    item_name_style = ParagraphStyle(
        'DesgloseItemName', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=TEXT_DARK, leading=13
    )

    cell_style = ParagraphStyle(
        'DesgloseCell', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_BODY, leading=11
    )

    total_label_style = ParagraphStyle(
        'DesgloseTotalLabel', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=TEXT_DARK, alignment=2, leading=13
    )

    total_value_style = ParagraphStyle(
        'DesgloseTotalValue', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=CORPORATE_INDIGO, alignment=2, leading=13
    )

    grand_total_style = ParagraphStyle(
        'DesgloseGrandTotal', parent=styles['Normal'],
        fontSize=12, fontName='Helvetica-Bold',
        textColor=WHITE, alignment=2, leading=15
    )

    small_style = ParagraphStyle(
        'DesgloseSmall', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica',
        textColor=TEXT_GRAY, leading=10
    )

    # ── DATOS ──
    datos_generales = datos_cotizacion.get('datosGenerales', {})
    items = datos_cotizacion.get('items', [])
    condiciones = datos_cotizacion.get('condiciones', {})
    moneda = condiciones.get('moneda', 'MXN')
    tipo_cambio_str = condiciones.get('tipoCambio', '1.0')

    try:
        tipo_cambio = float(tipo_cambio_str) if tipo_cambio_str else 1.0
        if tipo_cambio <= 0 or tipo_cambio > 1000:
            tipo_cambio = 1.0
    except (ValueError, TypeError):
        tipo_cambio = 1.0

    cliente = datos_generales.get('cliente', '')
    proyecto = datos_generales.get('proyecto', '')
    numero = datos_cotizacion.get('numeroCotizacion', datos_generales.get('numeroCotizacion', 'N/A'))
    revision = datos_generales.get('revision', '1')

    # ── TÍTULO ──
    story.append(Paragraph("DESGLOSE DE COTIZACIÓN", title_style))
    story.append(Paragraph(
        f"No. {numero} &nbsp;|&nbsp; Rev. {revision} &nbsp;|&nbsp; {datetime.datetime.now().strftime('%d/%m/%Y')}",
        subtitle_style
    ))

    if cliente or proyecto:
        info_parts = []
        if cliente:
            info_parts.append(f"Cliente: <b>{cliente}</b>")
        if proyecto:
            info_parts.append(f"Proyecto: <b>{proyecto}</b>")
        story.append(Paragraph(" &nbsp;|&nbsp; ".join(info_parts), subtitle_style))

    # Línea separadora
    story.append(Spacer(1, 4))
    from reportlab.graphics.shapes import Drawing as RL_Drawing, Line as RL_Line
    separator = RL_Drawing(480, 1)
    sep_line = RL_Line(0, 0, 480, 0)
    sep_line.strokeColor = BORDER_GRAY
    sep_line.strokeWidth = 0.5
    separator.add(sep_line)
    story.append(separator)
    story.append(Spacer(1, 8))

    # ── ITEMS ──
    if not items:
        story.append(Paragraph("No hay items en esta cotización.", cell_style))
    else:
        subtotal_general = 0.0

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            descripcion = item.get('descripcion', f'Item {idx+1}')
            cantidad = float(item.get('cantidad', 0))
            uom = item.get('uom', '')
            total_item = float(item.get('total', item.get('subtotal', 0)))
            precio_unitario = total_item / cantidad if cantidad > 0 else 0

            subtotal_general += total_item

            # Nombre del item
            story.append(Paragraph(
                f"ITEM {idx+1}: {descripcion[:100]}{'...' if len(descripcion) > 100 else ''}",
                item_name_style
            ))

            # Datos básicos del item
            if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
                total_mostrar = total_item / tipo_cambio
                pu_mostrar = precio_unitario / tipo_cambio
                simbolo = 'USD $'
            else:
                total_mostrar = total_item
                pu_mostrar = precio_unitario
                simbolo = '$'

            item_info = f"Cantidad: <b>{cantidad:,.0f}</b> {uom} &nbsp;|&nbsp; Precio Unitario: <b>{simbolo}{pu_mostrar:,.2f}</b> &nbsp;|&nbsp; Total Item: <b>{simbolo}{total_mostrar:,.2f}</b>"
            story.append(Paragraph(item_info, cell_style))

            # Transporte / Instalación / % Seguridad / % Descuento si aplican
            extras = []
            if float(item.get('transporte', 0)) > 0:
                extras.append(f"Transp: ${float(item.get('transporte', 0)):,.2f}")
            if float(item.get('instalacion', 0)) > 0:
                extras.append(f"Inst: ${float(item.get('instalacion', 0)):,.2f}")
            if float(item.get('seguridad', 0)) > 0:
                extras.append(f"Seg: {float(item.get('seguridad', 0))}%")
            if float(item.get('descuento', 0)) > 0:
                extras.append(f"Desc: {float(item.get('descuento', 0))}%")
            if extras:
                story.append(Paragraph(" &nbsp;|&nbsp; ".join(extras), small_style))

            # Materiales
            materiales = item.get('materiales', [])
            otros_materiales = item.get('otrosMateriales', [])

            if materiales or otros_materiales:
                mat_data = [['Material', 'Detalle', 'Subtotal']]
                mat_subtotal = 0.0

                for mat in materiales:
                    nombre_mat = mat.get('material', 'Sin descripción')
                    if nombre_mat == 'COTIZAR_POR_PESO':
                        peso = float(mat.get('pesoEstructura', 0))
                        precio_kg = float(mat.get('precioKg', 0))
                        sub = peso * precio_kg
                        detalle = f"{peso:,.1f} KG × ${precio_kg:,.2f}/KG"
                    else:
                        peso = float(mat.get('peso', 0))
                        precio = float(mat.get('precio', 0))
                        cant = float(mat.get('cantidad', 0))
                        sub = float(mat.get('subtotal', peso * precio * cant))
                        detalle = f"{cant:,.0f} × {peso:,.1f}kg × ${precio:,.2f}/kg"

                    mat_subtotal += sub
                    mat_data.append([
                        Paragraph(nombre_mat[:60], cell_style),
                        Paragraph(detalle, cell_style),
                        Paragraph(f"${sub:,.2f}", cell_style)
                    ])

                for otro in otros_materiales:
                    sub = float(otro.get('subtotal', 0))
                    mat_subtotal += sub
                    mat_data.append([
                        Paragraph(str(otro.get('descripcion', 'Sin descripción'))[:60], cell_style),
                        Paragraph(f"Cant: {otro.get('cantidad', '0')}", cell_style),
                        Paragraph(f"${sub:,.2f}", cell_style)
                    ])

                # Tabla de materiales compacta
                mat_table = Table(mat_data, colWidths=[2.8*inch, 2.2*inch, 1.0*inch])
                mat_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), CORPORATE_INDIGO),
                    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                    ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_GRAY),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
                ]))

                story.append(Spacer(1, 3))
                story.append(mat_table)

                # Subtotal materiales
                mat_total_row = [
                    Paragraph('<b>Subtotal Materiales</b>', cell_style),
                    '',
                    Paragraph(f'<b>${mat_subtotal:,.2f}</b>', cell_style)
                ]
                mat_total_table = Table([mat_total_row], colWidths=[2.8*inch, 2.2*inch, 1.0*inch])
                mat_total_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
                    ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                    ('SPAN', (0, 0), (1, 0)),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
                    ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                ]))
                story.append(mat_total_table)

            story.append(Spacer(1, 8))

        # ── TOTALES ──
        iva = subtotal_general * 0.16
        total = subtotal_general + iva

        if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
            st_mostrar = subtotal_general / tipo_cambio
            iva_mostrar = iva / tipo_cambio
            tot_mostrar = total / tipo_cambio
            simbolo_tot = 'USD $'
            conversion_note = f"TC: {tipo_cambio:.2f} MXN/USD"
        else:
            st_mostrar = subtotal_general
            iva_mostrar = iva
            tot_mostrar = total
            simbolo_tot = '$'
            conversion_note = None

        story.append(Spacer(1, 4))
        story.append(Paragraph("RESUMEN", section_style))

        totales_data = [
            ['Subtotal:', f"{simbolo_tot}{st_mostrar:,.2f}"],
            ['IVA (16%):', f"{simbolo_tot}{iva_mostrar:,.2f}"],
            ['TOTAL:', f"{simbolo_tot}{tot_mostrar:,.2f}"]
        ]

        totales_table = Table(totales_data, colWidths=[1.5*inch, 1.5*inch])
        totales_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -2), TEXT_DARK),
            ('TEXTCOLOR', (0, -1), (-1, -1), CORPORATE_INDIGO),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -2), BG_LIGHT),
            ('BACKGROUND', (0, -1), (-1, -1), CORPORATE_INDIGO_LIGHT),
            ('LINEABOVE', (0, -1), (-1, -1), 2, CORPORATE_INDIGO),
            ('BOX', (0, 0), (-1, -1), 0.75, BORDER_GRAY),
        ]))

        totales_container = Table([[totales_table]], colWidths=[6.2*inch])
        totales_container.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'RIGHT')]))
        story.append(totales_container)

        if conversion_note:
            story.append(Spacer(1, 3))
            story.append(Paragraph(f"<i>{conversion_note}</i>", small_style))

    # ── TÉRMINOS (COMPACTOS) ──
    if condiciones:
        story.append(Spacer(1, 6))
        story.append(Paragraph("TÉRMINOS", section_style))

        terminos_items = []
        tiempo = condiciones.get('tiempoEntrega', '')
        if tiempo:
            terminos_items.append(f"Entrega: <b>{tiempo} días hábiles</b>")
        entrega = condiciones.get('entregaEn', '')
        if entrega:
            terminos_items.append(f"Entregar en: <b>{entrega}</b>")
        pago = condiciones.get('terminos') or condiciones.get('terminosPago', '')
        if pago:
            terminos_items.append(f"Pago: <b>{pago}</b>")
        comentarios = condiciones.get('comentarios', condiciones.get('comentariosAdicionales', ''))
        if comentarios:
            terminos_items.append(f"Notas: {comentarios}")

        if terminos_items:
            for t in terminos_items:
                story.append(Paragraph(t, cell_style))
        else:
            story.append(Paragraph("No se especificaron términos.", cell_style))

    # ── PIE MÍNIMO ──
    story.append(Spacer(1, 10))
    separator2 = RL_Drawing(480, 1)
    sep_line2 = RL_Line(0, 0, 480, 0)
    sep_line2.strokeColor = BORDER_GRAY
    sep_line2.strokeWidth = 0.5
    separator2.add(sep_line2)
    story.append(separator2)
    story.append(Spacer(1, 4))

    vendedor = datos_generales.get('vendedor', 'CWS Company')
    story.append(Paragraph(
        f"CWS Company SA de CV &nbsp;|&nbsp; {vendedor} &nbsp;|&nbsp; {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        small_style
    ))
    story.append(Paragraph(
        "Este documento es un desglose de referencia. Para el documento oficial consulte el PDF de cotización.",
        small_style
    ))

    # Construir PDF
    doc.build(story)
    buffer.seek(0)

    return buffer.getvalue()
