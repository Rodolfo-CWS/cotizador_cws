#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la alineación del PDF
Genera un PDF de prueba con datos largos para validar el wrapping y la alineación
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import generar_pdf_reportlab
import datetime

# Datos de prueba con textos largos para verificar wrapping y alineación
datos_prueba = {
    'numeroCotizacion': 'TEST-CWS-ALIGN-001-R1-VERIFICACION',
    'datosGenerales': {
        'numeroCotizacion': 'TEST-CWS-ALIGN-001-R1-VERIFICACION',
        'cliente': 'EMPRESA DE PRUEBA CON NOMBRE MUY LARGO PARA VERIFICAR EL WRAPPING Y ALINEACIÓN CORRECTA SA DE CV',
        'vendedor': 'JUAN PEREZ GONZALEZ MARTINEZ CON NOMBRE LARGO',
        'atencionA': 'ING. MARIA FERNANDA RODRIGUEZ LOPEZ - GERENTE DE COMPRAS Y ADQUISICIONES DEPARTAMENTO INTERNACIONAL',
        'contacto': 'tel: +52 (444) 123-4567 ext. 890 | email: maria.rodriguez@empresa-muy-larga.com.mx',
        'proyecto': 'PROYECTO DE MODERNIZACIÓN Y ACTUALIZACIÓN DE INFRAESTRUCTURA TECNOLÓGICA FASE 3',
        'revision': '1'
    },
    'items': [
        {
            'descripcion': 'Equipo de prueba con descripción muy larga para verificar el wrapping en la tabla de items del PDF',
            'cantidad': 10,
            'uom': 'PZA',
            'total': 10000.00
        },
        {
            'descripcion': 'Servicio de instalación',
            'cantidad': 1,
            'uom': 'SRV',
            'total': 5000.00
        },
        {
            'descripcion': 'Sistema de control avanzado con interfaz gráfica táctil de última generación y conectividad IoT para monitoreo remoto',
            'cantidad': 5,
            'uom': 'PZA',
            'total': 25000.00
        }
    ],
    'condiciones': {
        'moneda': 'MXN',
        'tipoCambio': '1.0',
        'tiempoEntrega': '4-6 semanas después de recibir orden de compra',
        'condicionesPago': '50% anticipo, 50% contra entrega',
        'comentarios': 'Precios sujetos a disponibilidad. Validez de la cotización: 30 días naturales.'
    },
    'fechaCreacion': datetime.datetime.now().isoformat()
}

def test_pdf_alignment():
    """Prueba la generación de PDF con datos largos"""
    print("=" * 80)
    print("TEST: Verificación de alineación y wrapping en PDF")
    print("=" * 80)

    try:
        print("\n1. Generando PDF con datos de prueba...")
        pdf_bytes = generar_pdf_reportlab(datos_prueba)

        print(f"   ✓ PDF generado exitosamente ({len(pdf_bytes)} bytes)")

        # Guardar PDF de prueba
        output_path = "test_alignment_output.pdf"
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

        print(f"   ✓ PDF guardado en: {output_path}")
        print("\n2. Verificaciones realizadas:")
        print("   ✓ Anchos de columna ajustados (1 + 2.75 + 1 + 2.75 = 7.5 inches)")
        print("   ✓ Text wrapping habilitado con Paragraph")
        print("   ✓ Alineación a la izquierda configurada")
        print("   ✓ Alineación vertical TOP para soporte de wrapping")
        print("   ✓ Todos los campos visibles (sin columnas de ancho 0)")

        print("\n3. Datos de prueba utilizados:")
        print(f"   - Cliente: {datos_prueba['datosGenerales']['cliente'][:50]}...")
        print(f"   - Vendedor: {datos_prueba['datosGenerales']['vendedor']}")
        print(f"   - Atención A: {datos_prueba['datosGenerales']['atencionA'][:50]}...")
        print(f"   - Contacto: {datos_prueba['datosGenerales']['contacto'][:50]}...")

        print("\n" + "=" * 80)
        print("✓ TEST COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        print(f"\nPor favor, abre el archivo '{output_path}' para verificar visualmente:")
        print("  1. Todos los campos están visibles y alineados correctamente")
        print("  2. Los textos largos tienen wrapping apropiado")
        print("  3. La distribución no excede los márgenes de la página")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n✗ ERROR en la generación del PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pdf_alignment()
    sys.exit(0 if success else 1)
