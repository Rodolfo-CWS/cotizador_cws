#!/usr/bin/env python3
"""
Test simple del campo Actualización con texto largo y wrap
Solo genera el PDF sin conexión a base de datos
"""

import sys
import os

# Importar solo ReportLab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def test_actualizacion_wrap_simple():
    """Test simple del wrap en campo actualización"""
    print("=" * 80)
    print("TEST SIMPLE: Campo Actualización con Texto Largo y Wrap")
    print("=" * 80)

    # Texto largo para probar el wrap (más de 200 caracteres)
    texto_largo = """Esta es una actualización muy detallada de la revisión que incluye múltiples cambios importantes en las especificaciones técnicas, ajustes de precios debido a variaciones en el mercado de materiales, modificaciones en los tiempos de entrega por factores logísticos externos, y actualizaciones en las condiciones comerciales acordadas con el cliente tras las reuniones de seguimiento del proyecto. Además se incluyen consideraciones adicionales sobre garantías extendidas y soporte técnico."""

    print(f"\n📝 Texto de prueba ({len(texto_largo)} caracteres):")
    print(f"   Primeros 100 caracteres: {texto_largo[:100]}...")
    print(f"   Últimos 100 caracteres: ...{texto_largo[-100:]}")

    # Crear PDF de prueba
    pdf_path = "/home/user/cotizador_cws/test_actualizacion_wrap.pdf"

    print(f"\n📄 Generando PDF de prueba...")
    print(f"   Ruta: {pdf_path}")

    try:
        # Crear documento
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2C5282'),
            alignment=1
        )
        story.append(Paragraph("TEST: Campo Actualización con Wrap", title_style))
        story.append(Spacer(1, 20))

        # Crear tabla de información similar a la del PDF real
        info_data = [
            ['Cliente:', 'Cliente Test Wrap', 'Vendedor:', 'Test Vendedor'],
            ['Atención A:', 'Atención Test', 'Contacto:', 'test@wrap.com'],
            ['Revisión:', 'Rev. 2', '', '']
        ]

        # Agregar campo de actualización con Paragraph para wrap
        actualizacion_style = ParagraphStyle(
            'ActualizacionStyle',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            textColor=colors.HexColor('#2D3748'),
            alignment=0,  # 0 = LEFT (justificado a la izquierda)
            leading=10,   # Espaciado entre líneas
            leftIndent=0,
            rightIndent=0
        )
        actualizacion_paragraph = Paragraph(texto_largo, actualizacion_style)
        info_data.append(['Actualización:', actualizacion_paragraph, '', ''])

        # Crear tabla con anchos ajustados
        info_table = Table(info_data, colWidths=[1.2*inch, 6.8*inch, 0*inch, 0*inch])
        info_table.setStyle(TableStyle([
            # Estilo general
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),

            # Labels (columna 0)
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2C5282')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EDF2F7')),

            # Labels (columna 2)
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#2C5282')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#EDF2F7')),

            # Valores
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2D3748')),
            ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor('#2D3748')),

            # Alineación
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),

            # Bordes
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2C5282')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('BACKGROUND', (3, 0), (3, -1), colors.white),
        ]))

        story.append(info_table)
        story.append(Spacer(1, 20))

        # Agregar nota explicativa
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=0
        )

        note_text = """
        <b>Verificación del Test:</b><br/>
        El campo "Actualización:" debe mostrar el texto largo en múltiples líneas con:
        <br/>• Ajuste automático de línea (wrap)
        <br/>• Justificación a la izquierda
        <br/>• Todo el texto completo visible sin cortes
        <br/>• Espaciado legible entre líneas
        """
        story.append(Paragraph(note_text, note_style))

        # Construir PDF
        doc.build(story)

        # Verificar que se creó
        if os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            print(f"\n✅ PDF generado exitosamente")
            print(f"   Tamaño: {file_size / 1024:.2f} KB")
            print(f"   Ubicación: {pdf_path}")

            print("\n" + "=" * 80)
            print("✅ TEST COMPLETADO")
            print("=" * 80)
            print("\n📋 VERIFICACIÓN MANUAL:")
            print(f"   1. Abre el PDF: {pdf_path}")
            print("   2. Busca el campo 'Actualización:' en la tabla")
            print("   3. Verifica que el texto largo se muestre con:")
            print("      ✓ Múltiples líneas (wrap automático)")
            print("      ✓ Justificación a la izquierda")
            print("      ✓ Todo el texto visible (más de 300 caracteres)")
            print("      ✓ Espaciado legible entre líneas")
            print("\n")

            return True
        else:
            print(f"❌ ERROR: PDF no se creó en {pdf_path}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        exito = test_actualizacion_wrap_simple()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
