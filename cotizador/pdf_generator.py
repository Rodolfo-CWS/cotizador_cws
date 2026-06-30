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


# ── Constantes de color corporativo ──
CORPORATE_INDIGO = colors.HexColor('#4f46e5')
CORPORATE_INDIGO_DARK = colors.HexColor('#3730a3')
CORPORATE_INDIGO_LIGHT = colors.HexColor('#eef2ff')
TEXT_DARK = colors.HexColor('#1f2937')
TEXT_GRAY = colors.HexColor('#6b7280')
TEXT_BODY = colors.HexColor('#374151')
BORDER_GRAY = colors.HexColor('#d1d5db')
BG_LIGHT = colors.HexColor('#f9fafb')
BG_STRIPE = colors.HexColor('#f3f4f6')
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
        fontSize=8, fontName='Helvetica',
        alignment=0, leftIndent=0, rightIndent=0,
        spaceAfter=0, spaceBefore=0, leading=10
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
    story.append(Spacer(1, 6))

    # Línea separadora gruesa
    line_drawing = Drawing(430, 2)
    line_drawing.add(GraphicsLine(0, 0, 430, 0, strokeColor=CORPORATE_INDIGO, strokeWidth=3))
    story.append(line_drawing)
    story.append(Spacer(1, 10))

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
        story.append(Spacer(1, 8))

    # Datos del cliente
    info_data = [
        ['Cliente:', datos_generales.get('cliente', ''), 'Vendedor:', datos_generales.get('vendedor', '')],
        ['Atención A:', datos_generales.get('atencionA', ''), 'Contacto:', datos_generales.get('contacto', '')],
    ]

    if datos_generales.get('revision', '1') != '1':
        info_data.append(['Revisión:', f"Rev. {datos_generales.get('revision', '1')}",
                         'Actualización:', datos_generales.get('actualizacionRevision', '')])

    info_table = Table(info_data, colWidths=[1.2*inch, 2.8*inch, 1.2*inch, 2.8*inch])
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
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        ('BOX', (0, 0), (-1, -1), 1.5, CORPORATE_INDIGO),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('BACKGROUND', (3, 0), (3, -1), WHITE),
    ]))

    story.append(info_table)
    story.append(Spacer(1, 10))

    # ── TEXTO INTRODUCTORIO ──
    intro_style = ParagraphStyle(
        'IntroText', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica',
        textColor=TEXT_BODY, alignment=4,
        spaceAfter=8, borderPadding=8,
        backColor=BG_LIGHT, borderColor=BORDER_GRAY, borderWidth=0.5
    )

    if texto_personalizado:
        intro_text = texto_personalizado.replace("\n", "<br/>\n")
    else:
        intro_text = """Estimado Cliente,<br/>
        CWS Company presenta esta propuesta económica para el proyecto solicitado.
        Quedamos a la espera de su respuesta."""

    story.append(Paragraph(intro_text, intro_style))
    story.append(Spacer(1, 10))

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
        items_table = Table(items_data, colWidths=[0.45*inch, 2.85*inch, 0.55*inch, 0.5*inch, 1.05*inch, 1.1*inch])
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), CORPORATE_INDIGO),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (-1, 0), 'CENTER'),

            # Contenido
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
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
            ('BOX', (0, 0), (-1, -1), 1.5, CORPORATE_INDIGO),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
            ('LINEBELOW', (0, 0), (-1, 0), 3, CORPORATE_INDIGO_DARK),
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
                with urllib.request.urlopen(img_url, timeout=15) as response:
                    img_bytes = response.read()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    tmp.write(img_bytes)
                    img_path = tmp.name
                    _is_temp = True
            elif img_url.startswith('static/'):
                candidate = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_url)
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

                story.append(Spacer(1, 10))
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
    story.append(Spacer(1, 14))
    story.append(Paragraph("TÉRMINOS Y CONDICIONES", subtitle_style))
    story.append(Spacer(1, 6))

    campos_terminos = [
        ('Moneda:', condiciones.get('moneda', 'MXN') if condiciones else 'MXN'),
        ('Tiempo de Entrega:', condiciones.get('tiempoEntrega', '') if condiciones else ''),
        ('Entregar En:', condiciones.get('entregaEn', '') if condiciones else ''),
        ('Términos de Pago:', (condiciones.get('terminos') or condiciones.get('condicionesPago', '')) if condiciones else ''),
        ('Comentarios:', (condiciones.get('comentarios') or condiciones.get('comentariosAdicionales', '')) if condiciones else '')
    ]

    if moneda == 'USD' and tipo_cambio > 0 and tipo_cambio != 1.0:
        campos_terminos.insert(1, ('Tipo de Cambio:', f'{tipo_cambio:.2f} MXN/USD'))

    terms_value_style = ParagraphStyle(
        'TermsValue', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=TEXT_BODY, alignment=0,
        leading=12, wordWrap='CJK'
    )

    terminos_data = []
    for label, value in campos_terminos:
        texto = value.strip() if (value and value.strip()) else (
            'A definir' if 'Tiempo' in label or 'Entregar' in label or 'Términos' in label
            else ('Sin comentarios adicionales' if 'Comentarios' in label else 'MXN')
        )
        terminos_data.append([Paragraph(label, terms_value_style), Paragraph(texto, terms_value_style)])

    terminos_table = Table(terminos_data, colWidths=[1.8*inch, 4.7*inch])
    terminos_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),

        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_BODY),

        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),

        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_GRAY),
    ]))

    story.append(terminos_table)

    # ── PIE DE PÁGINA ──
    story.append(Spacer(1, 14))

    footer_line = Drawing(430, 2)
    footer_line.add(GraphicsLine(0, 0, 430, 0, strokeColor=CORPORATE_INDIGO, strokeWidth=2))
    story.append(footer_line)
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
