#!/usr/bin/env python3
"""
Test del campo Actualización con texto largo y wrap
Verifica que el PDF muestre correctamente textos largos con ajuste de línea
"""

import sys
import os
from supabase_manager import SupabaseManager
from pdf_manager import PDFManager

def test_actualizacion_wrap():
    """Test del wrap en campo actualización"""
    print("=" * 80)
    print("TEST: Campo Actualización con Texto Largo y Wrap")
    print("=" * 80)

    # Inicializar managers
    db = SupabaseManager()
    pdf_manager = PDFManager(db)

    # Texto largo para probar el wrap (más de 200 caracteres)
    texto_largo = """Esta es una actualización muy detallada de la revisión que incluye múltiples cambios importantes en las especificaciones técnicas, ajustes de precios debido a variaciones en el mercado de materiales, modificaciones en los tiempos de entrega por factores logísticos externos, y actualizaciones en las condiciones comerciales acordadas con el cliente tras las reuniones de seguimiento del proyecto."""

    print(f"\n📝 Texto de prueba ({len(texto_largo)} caracteres):")
    print(f"   {texto_largo[:100]}...")

    # Crear cotización de prueba con texto largo en actualización
    cotizacion_test = {
        "numeroCotizacion": "TEST-CWS-WRAP-001-R2-ACTUALIZACION",
        "datosGenerales": {
            "cliente": "Cliente Test Wrap",
            "vendedor": "Test Vendedor",
            "proyecto": "Test Actualización Wrap",
            "atencionA": "Atención Test",
            "contacto": "test@wrap.com",
            "revision": "2",
            "actualizacionRevision": texto_largo
        },
        "items": [
            {
                "descripcion": "Item de prueba para verificar wrap",
                "cantidad": "1",
                "uom": "PZA",
                "costoUnidad": "1000.00",
                "total": "1000.00",
                "materiales": [
                    {
                        "nombre": "Material Test",
                        "cantidad": "1",
                        "costo": "1000.00"
                    }
                ],
                "transporte": "0",
                "instalacion": "0",
                "seguridad": "0",
                "descuento": "0"
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "tiempoEntrega": "2 semanas",
            "condicionesPago": "50% anticipo, 50% contra entrega",
            "comentarios": "Test de wrap en actualización"
        },
        "resumenGeneral": {
            "subtotal": 1000.00,
            "iva": 160.00,
            "total": 1160.00
        }
    }

    print("\n💾 Guardando cotización de prueba...")
    resultado_guardar = db.guardar_cotizacion(cotizacion_test)

    if not resultado_guardar.get("success"):
        print(f"❌ ERROR guardando cotización: {resultado_guardar.get('error')}")
        return False

    print(f"✅ Cotización guardada exitosamente")
    print(f"   ID: {resultado_guardar.get('id', 'N/A')}")

    # Generar PDF
    print("\n📄 Generando PDF con ReportLab...")
    from app import generar_pdf_reportlab

    try:
        pdf_bytes = generar_pdf_reportlab(cotizacion_test)
        print(f"✅ PDF generado exitosamente ({len(pdf_bytes)} bytes)")

        # Guardar PDF en disco para revisión manual
        test_pdf_path = "/home/user/cotizador_cws/test_actualizacion_wrap.pdf"
        with open(test_pdf_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"\n📁 PDF guardado en: {test_pdf_path}")
        print(f"   Tamaño: {len(pdf_bytes) / 1024:.2f} KB")

        # Almacenar en sistema
        print("\n☁️ Almacenando PDF en sistema...")
        resultado_pdf = pdf_manager.almacenar_pdf_nuevo(pdf_bytes, cotizacion_test)

        if resultado_pdf.get("success"):
            print(f"✅ PDF almacenado exitosamente")
            print(f"   Estado: {resultado_pdf.get('estado')}")
            print(f"   Ruta: {resultado_pdf.get('ruta_local', 'N/A')}")
        else:
            print(f"⚠️ WARNING: PDF no se pudo almacenar: {resultado_pdf.get('error')}")

        print("\n" + "=" * 80)
        print("✅ TEST COMPLETADO")
        print("=" * 80)
        print("\n📋 VERIFICACIÓN MANUAL:")
        print(f"   1. Abre el PDF: {test_pdf_path}")
        print("   2. Busca el campo 'Actualización:' en la sección de información del cliente")
        print("   3. Verifica que el texto largo se muestre con:")
        print("      - Múltiples líneas (wrap automático)")
        print("      - Justificación a la izquierda")
        print("      - Todo el texto visible sin cortes")
        print("\n")

        return True

    except Exception as e:
        print(f"\n❌ ERROR generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        exito = test_actualizacion_wrap()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
