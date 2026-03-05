#!/usr/bin/env python3
"""
Test de wrapping de comentarios largos en PDFs
Valida que el campo de comentarios soporte textos largos con formato wrap
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import generar_pdf_reportlab
import datetime

def test_comentarios_largos():
    """Prueba generación de PDF con comentarios muy largos"""

    print("=" * 80)
    print("TEST: Generación de PDF con comentarios largos (text wrapping)")
    print("=" * 80)

    # Datos de prueba con comentario muy largo
    cotizacion_test = {
        "datosGenerales": {
            "numeroCotizacion": "TEST-CWS-CM-001-R1-COMENTARIOS-WRAP",
            "cliente": "Cliente Test Comentarios",
            "proyecto": "Validación de Text Wrapping",
            "atencionA": "Ing. Prueba",
            "vendedor": "Carlos Muñoz",
            "contacto": "555-1234",
            "revision": "1",
            "fechaCreacion": datetime.datetime.now().isoformat()
        },
        "items": [
            {
                "descripcion": "Item de prueba para validar comentarios largos",
                "cantidad": 10,
                "uom": "PZA",
                "precioUnitario": 100.00,
                "total": 1000.00
            },
            {
                "descripcion": "Segundo item de prueba con descripción corta",
                "cantidad": 5,
                "uom": "PZA",
                "precioUnitario": 200.00,
                "total": 1000.00
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "tipoCambio": "",
            "tiempoEntrega": "20 días hábiles",
            "entregaEn": "Planta del cliente en San Luis Potosí",
            "terminos": "50% anticipo, 50% contra entrega",
            "comentarios": """Esta es una prueba de comentarios extremadamente largos para validar que el sistema de text wrapping funciona correctamente en los PDFs generados.

El texto debe ajustarse automáticamente dentro del cuadro de comentarios sin cortarse o salirse de los márgenes. Esto es crítico para mantener la presentación profesional de las cotizaciones.

Los comentarios pueden incluir múltiples párrafos y líneas largas que necesitan ser ajustadas correctamente. El sistema debe manejar:
- Comentarios de una sola línea muy larga que necesita wrapping
- Comentarios con múltiples párrafos separados por saltos de línea
- Comentarios con información técnica detallada
- Comentarios con instrucciones especiales para el cliente

Además, es importante que el formato se mantenga legible y profesional, respetando los márgenes de la tabla y sin afectar el diseño general del PDF. El cliente debe poder leer toda la información sin problemas de formato o recorte de texto."""
        }
    }

    try:
        print("\n1️⃣  Generando PDF con comentarios largos...")
        pdf_bytes = generar_pdf_reportlab(cotizacion_test)

        print(f"✅ PDF generado exitosamente ({len(pdf_bytes)} bytes)")

        # Guardar PDF para inspección manual
        output_path = "test_comentarios_wrap_output.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"📄 PDF guardado en: {output_path}")
        print("\n✅ TEST EXITOSO: El PDF se generó correctamente con comentarios largos")
        print("   Por favor revisa manualmente el PDF para confirmar que:")
        print("   - Los comentarios se muestran completos")
        print("   - El texto hace wrap correctamente dentro del cuadro")
        print("   - No hay texto cortado o fuera de márgenes")
        print("   - El formato es profesional y legible")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_comentarios_cortos():
    """Prueba generación de PDF con comentarios cortos (caso normal)"""

    print("\n" + "=" * 80)
    print("TEST: Generación de PDF con comentarios cortos (caso normal)")
    print("=" * 80)

    cotizacion_test = {
        "datosGenerales": {
            "numeroCotizacion": "TEST-CWS-CM-002-R1-COMENTARIOS-CORTOS",
            "cliente": "Cliente Test Corto",
            "proyecto": "Comentarios Normales",
            "atencionA": "Ing. Normal",
            "vendedor": "Carlos Muñoz",
            "contacto": "555-5678",
            "revision": "1",
            "fechaCreacion": datetime.datetime.now().isoformat()
        },
        "items": [
            {
                "descripcion": "Item simple",
                "cantidad": 1,
                "uom": "PZA",
                "precioUnitario": 500.00,
                "total": 500.00
            }
        ],
        "condiciones": {
            "moneda": "USD",
            "tipoCambio": "18.50",
            "tiempoEntrega": "15 días",
            "entregaEn": "Almacén cliente",
            "terminos": "Pago anticipado",
            "comentarios": "Incluye instalación y capacitación básica"
        }
    }

    try:
        print("\n2️⃣  Generando PDF con comentarios cortos...")
        pdf_bytes = generar_pdf_reportlab(cotizacion_test)

        print(f"✅ PDF generado exitosamente ({len(pdf_bytes)} bytes)")

        # Guardar PDF para inspección
        output_path = "test_comentarios_cortos_output.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"📄 PDF guardado en: {output_path}")
        print("\n✅ TEST EXITOSO: Comentarios cortos funcionan correctamente")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sin_comentarios():
    """Prueba generación de PDF sin comentarios (campo vacío)"""

    print("\n" + "=" * 80)
    print("TEST: Generación de PDF sin comentarios")
    print("=" * 80)

    cotizacion_test = {
        "datosGenerales": {
            "numeroCotizacion": "TEST-CWS-CM-003-R1-SIN-COMENTARIOS",
            "cliente": "Cliente Sin Comentarios",
            "proyecto": "Sin Comentarios",
            "atencionA": "Ing. Sin Comentarios",
            "vendedor": "Carlos Muñoz",
            "contacto": "555-9999",
            "revision": "1",
            "fechaCreacion": datetime.datetime.now().isoformat()
        },
        "items": [
            {
                "descripcion": "Item básico",
                "cantidad": 3,
                "uom": "PZA",
                "precioUnitario": 150.00,
                "total": 450.00
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "tipoCambio": "",
            "tiempoEntrega": "10 días",
            "entregaEn": "Local",
            "terminos": "Contado",
            "comentarios": ""  # Campo vacío
        }
    }

    try:
        print("\n3️⃣  Generando PDF sin comentarios...")
        pdf_bytes = generar_pdf_reportlab(cotizacion_test)

        print(f"✅ PDF generado exitosamente ({len(pdf_bytes)} bytes)")

        # Guardar PDF
        output_path = "test_sin_comentarios_output.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"📄 PDF guardado en: {output_path}")
        print("\n✅ TEST EXITOSO: PDF sin comentarios funciona correctamente")
        print("   Debería mostrar: 'Sin comentarios adicionales'")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 Iniciando suite de tests de comentarios con text wrapping\n")

    resultados = []

    # Test 1: Comentarios largos (crítico)
    resultados.append(("Comentarios Largos", test_comentarios_largos()))

    # Test 2: Comentarios cortos (normal)
    resultados.append(("Comentarios Cortos", test_comentarios_cortos()))

    # Test 3: Sin comentarios (edge case)
    resultados.append(("Sin Comentarios", test_sin_comentarios()))

    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE TESTS")
    print("=" * 80)

    exitosos = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)

    for nombre, resultado in resultados:
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"{status} - {nombre}")

    print("\n" + "=" * 80)
    print(f"Resultado Final: {exitosos}/{total} tests exitosos")

    if exitosos == total:
        print("🎉 TODOS LOS TESTS PASARON")
        print("\n📝 Por favor revisa manualmente los PDFs generados:")
        print("   - test_comentarios_wrap_output.pdf (comentarios largos)")
        print("   - test_comentarios_cortos_output.pdf (comentarios normales)")
        print("   - test_sin_comentarios_output.pdf (sin comentarios)")
        sys.exit(0)
    else:
        print("⚠️  ALGUNOS TESTS FALLARON")
        sys.exit(1)
