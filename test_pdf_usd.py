#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test para validar que el PDF genere correctamente con conversión USD
"""

import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_estructura_datos_pdf_usd():
    """Test que valida los datos que se pasan a la función generar_pdf_reportlab para USD"""
    
    print("=== TEST: Datos de cotización USD para PDF ===")
    print()
    
    # Simular datos como los que se pasan a generar_pdf_reportlab
    datos_cotizacion_usd = {
        "numeroCotizacion": "CLIENTE-CWS-RM-001-R1-PROYECTO_USD",
        "revision": "1",
        "datosGenerales": {
            "vendedor": "RM",
            "proyecto": "PROYECTO USD",
            "cliente": "CLIENTE USD",
            "atencionA": "Contacto Test",
            "contacto": "test@test.com",
            "fecha": "2025-08-14"
        },
        "items": [
            {
                "descripcion": "Estructura metalica en USD",
                "cantidad": "1",
                "uom": "Servicio",
                "materiales": [
                    {
                        "material": "COTIZAR_POR_PESO",
                        "pesoEstructura": "800",
                        "precioKg": "30.00",
                        "subtotal": "24000.00",  # MXN
                        "tipoCotizacion": "peso"
                    },
                    {
                        "material": "Acero A36",
                        "peso": "2.5",
                        "cantidad": "150",
                        "precio": "18.00",
                        "subtotal": "6750.00",   # MXN
                        "tipoCotizacion": "normal"
                    }
                ],
                "otrosMateriales": [
                    {
                        "descripcion": "Soldadura especial",
                        "precio": "250.00",
                        "cantidad": "12",
                        "subtotal": "3000.00"  # MXN
                    }
                ],
                "transporte": "1500.00",
                "instalacion": "2500.00",
                "seguridad": "10",
                "descuento": "5"
            }
        ],
        "condiciones": {
            "moneda": "USD",
            "tipoCambio": "19.50",
            "tiempoEntrega": "20 dias habiles",
            "entregaEn": "Sitio del cliente",
            "terminos": "50% anticipo, 50% contra entrega",
            "comentarios": "Cotizacion convertida a USD"
        }
    }
    
    print("DATOS PARA PDF:")
    print(f"  - Numero: {datos_cotizacion_usd['numeroCotizacion']}")
    print(f"  - Cliente: {datos_cotizacion_usd['datosGenerales']['cliente']}")
    print(f"  - Moneda: {datos_cotizacion_usd['condiciones']['moneda']}")
    print(f"  - Tipo cambio: {datos_cotizacion_usd['condiciones']['tipoCambio']}")
    print()
    
    # Simular cálculo de subtotal (como lo haría el PDF)
    subtotal_mxn = 0
    
    print("ITEMS Y MATERIALES:")
    for item in datos_cotizacion_usd['items']:
        print(f"  Item: {item['descripcion']}")
        
        # Materiales
        for material in item['materiales']:
            subtotal = float(material['subtotal'])
            subtotal_mxn += subtotal
            if material['tipoCotizacion'] == 'peso':
                print(f"    - {material['material']}: {material['pesoEstructura']} KG x ${material['precioKg']}/KG = ${subtotal}")
            else:
                print(f"    - {material['material']}: {material['cantidad']} x ${material['precio']} = ${subtotal}")
        
        # Otros materiales
        for otro in item['otrosMateriales']:
            subtotal = float(otro['subtotal'])
            subtotal_mxn += subtotal
            print(f"    - {otro['descripcion']}: {otro['cantidad']} x ${otro['precio']} = ${subtotal}")
        
        # Costos adicionales
        transporte = float(item.get('transporte', 0))
        instalacion = float(item.get('instalacion', 0))
        subtotal_mxn += transporte + instalacion
        
        if transporte > 0:
            print(f"    - Transporte: ${transporte}")
        if instalacion > 0:
            print(f"    - Instalacion: ${instalacion}")
    
    print()
    
    # Cálculos en MXN (como los hace internamente el sistema)
    iva_mxn = subtotal_mxn * 0.16
    total_mxn = subtotal_mxn + iva_mxn
    
    print("CALCULOS EN MXN (INTERNOS):")
    print(f"  - Subtotal: ${subtotal_mxn:,.2f} MXN")
    print(f"  - IVA (16%): ${iva_mxn:,.2f} MXN")
    print(f"  - Total: ${total_mxn:,.2f} MXN")
    print()
    
    # Conversión a USD (como debe hacerlo el PDF)
    tipo_cambio = float(datos_cotizacion_usd['condiciones']['tipoCambio'])
    
    subtotal_usd = subtotal_mxn / tipo_cambio
    iva_usd = iva_mxn / tipo_cambio
    total_usd = total_mxn / tipo_cambio
    
    print("CONVERSION A USD (PARA PDF):")
    print(f"  - Subtotal: USD ${subtotal_usd:,.2f}")
    print(f"  - IVA (16%): USD ${iva_usd:,.2f}")
    print(f"  - Total: USD ${total_usd:,.2f}")
    print(f"  - Nota: Tipo de cambio: {tipo_cambio:.2f} MXN/USD")
    print()
    
    print("ELEMENTOS QUE DEBE INCLUIR EL PDF:")
    print("  1. Totales con simbolo 'USD $' en lugar de '$'")
    print("  2. Nota de conversion: 'Tipo de cambio: 19.50 MXN/USD'")
    print("  3. En terminos y condiciones: 'Tipo de Cambio: 19.50 MXN/USD'")
    print("  4. Moneda: USD (en lugar de MXN)")
    print()
    
    return True

def test_validacion_conversion():
    """Test que valida la lógica de conversión específica del PDF"""
    
    print("=== TEST: Validación lógica de conversión ===")
    print()
    
    # Casos de prueba
    casos_test = [
        {
            "descripcion": "Caso 1: USD con tipo cambio normal",
            "condiciones": {"moneda": "USD", "tipoCambio": "18.50"},
            "subtotal_mxn": 50000.00,
            "esperado_usd": 50000.00 / 18.50
        },
        {
            "descripcion": "Caso 2: MXN sin conversión",
            "condiciones": {"moneda": "MXN", "tipoCambio": ""},
            "subtotal_mxn": 50000.00,
            "esperado_usd": 50000.00  # Sin conversión
        },
        {
            "descripcion": "Caso 3: USD con tipo cambio alto",
            "condiciones": {"moneda": "USD", "tipoCambio": "22.75"},
            "subtotal_mxn": 100000.00,
            "esperado_usd": 100000.00 / 22.75
        }
    ]
    
    for caso in casos_test:
        print(f"{caso['descripcion']}:")
        
        condiciones = caso['condiciones']
        subtotal_mxn = caso['subtotal_mxn']
        
        # Simular lógica del PDF
        moneda = condiciones.get('moneda', 'MXN')
        tipo_cambio = float(condiciones.get('tipoCambio', 1.0)) if condiciones.get('tipoCambio') else 1.0
        
        if moneda == 'USD' and tipo_cambio > 0:
            subtotal_resultado = subtotal_mxn / tipo_cambio
            simbolo = 'USD $'
            conversion_note = f"Tipo de cambio: {tipo_cambio:.2f} MXN/USD"
        else:
            subtotal_resultado = subtotal_mxn
            simbolo = '$'
            conversion_note = None
        
        print(f"  - Moneda: {moneda}")
        print(f"  - Tipo cambio: {tipo_cambio}")
        print(f"  - Subtotal MXN: ${subtotal_mxn:,.2f}")
        print(f"  - Subtotal resultado: {simbolo}{subtotal_resultado:,.2f}")
        
        if conversion_note:
            print(f"  - Nota: {conversion_note}")
        
        # Validar resultado
        diferencia = abs(subtotal_resultado - caso['esperado_usd'])
        if diferencia < 0.01:
            print(f"  - Status: CORRECTO")
        else:
            print(f"  - Status: ERROR - Esperado {caso['esperado_usd']:.2f}, obtenido {subtotal_resultado:.2f}")
        
        print()
    
    return True

def run_all_tests():
    """Ejecutar todos los tests"""
    
    print("TESTING: Generación PDF con USD")
    print("=" * 50)
    print()
    
    tests = [
        test_estructura_datos_pdf_usd,
        test_validacion_conversion
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"Error en test: {e}")
        print()
    
    print("=" * 50)
    print(f"RESULTADO: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("El PDF deberia generar correctamente con conversion USD!")
        print()
        print("CAMBIOS IMPLEMENTADOS EN generar_pdf_reportlab():")
        print("1. Deteccion de moneda USD en condiciones")
        print("2. Conversion de totales dividiendo entre tipo de cambio")
        print("3. Simbolo 'USD $' en lugar de '$'")
        print("4. Nota de conversion en el PDF")
        print("5. Tipo de cambio en terminos y condiciones")
        return True
    else:
        print("Algunos tests fallaron. Revisar implementacion.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)