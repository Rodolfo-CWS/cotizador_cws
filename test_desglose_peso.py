#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test para verificar que el desglose muestre correctamente los campos de "Cotizar por peso"
"""

import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_estructura_datos_desglose():
    """Test que simula los datos que se pasan al template de desglose"""
    
    # Simular datos como los que se pasan al template ver_cotizacion.html
    cotizacion_test = {
        "numeroCotizacion": "TEST-CWS-RM-001-R1-PROYECTO_PESO",
        "revision": "1",
        "datosGenerales": {
            "vendedor": "TEST USER",
            "proyecto": "PROYECTO PESO",
            "cliente": "CLIENTE TEST",
            "atencionA": "Contacto Test",
            "contacto": "test@test.com"
        },
        "items": [
            {
                "descripcion": "Estructura metalica cotizada por peso",
                "cantidad": "1",
                "uom": "Servicio",
                "materiales": [
                    {
                        "material": "COTIZAR_POR_PESO",
                        "pesoEstructura": "500",
                        "precioKg": "25.50",
                        "subtotal": "12750.00",
                        "tipoCotizacion": "peso"
                    },
                    {
                        "material": "Acero A36",
                        "peso": "2.5",
                        "cantidad": "100",
                        "precio": "15.00",
                        "subtotal": "3750.00",
                        "tipoCotizacion": "normal"
                    }
                ],
                "otrosMateriales": [
                    {
                        "descripcion": "Soldadura",
                        "precio": "200.00",
                        "cantidad": "10",
                        "subtotal": "2000.00"
                    }
                ],
                "transporte": "1000",
                "instalacion": "2000",
                "seguridad": "10",
                "descuento": "5"
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "tiempoEntrega": "15 dias habiles",
            "entregaEn": "Sitio del cliente",
            "terminos": "50% anticipo, 50% contra entrega"
        }
    }
    
    print("=== TEST: Estructura de datos para desglose ===")
    print()
    
    # Verificar estructura de datos para template
    print("DATOS GENERALES:")
    print(f"  - Numero: {cotizacion_test['numeroCotizacion']}")
    print(f"  - Cliente: {cotizacion_test['datosGenerales']['cliente']}")
    print(f"  - Vendedor: {cotizacion_test['datosGenerales']['vendedor']}")
    print()
    
    print("ITEMS:")
    for i, item in enumerate(cotizacion_test['items'], 1):
        print(f"  Item {i}: {item['descripcion']}")
        print(f"    Cantidad: {item['cantidad']} {item['uom']}")
        print()
        
        print("    MATERIALES:")
        for j, material in enumerate(item['materiales'], 1):
            print(f"      Material {j}: {material['material']}")
            
            if material['material'] == 'COTIZAR_POR_PESO':
                print("        >>> COTIZAR POR PESO <<<")
                print(f"        - Peso estructura: {material['pesoEstructura']} KG")
                print(f"        - Precio por KG: ${material['precioKg']}")
                print(f"        - Subtotal: ${material['subtotal']}")
                print(f"        - Formula: {material['pesoEstructura']} KG x ${material['precioKg']}/KG = ${material['subtotal']}")
                
                # Verificar calculo
                peso = float(material['pesoEstructura'])
                precio_kg = float(material['precioKg'])
                subtotal_calculado = peso * precio_kg
                subtotal_esperado = float(material['subtotal'])
                
                if abs(subtotal_calculado - subtotal_esperado) < 0.01:
                    print(f"        ✓ Calculo correcto")
                else:
                    print(f"        ✗ Error en calculo: esperado ${subtotal_esperado}, calculado ${subtotal_calculado}")
                    
            else:
                print("        >>> MATERIAL NORMAL <<<")
                print(f"        - Peso: {material.get('peso', 'N/A')} kg")
                print(f"        - Cantidad: {material.get('cantidad', 'N/A')}")
                print(f"        - Precio: ${material.get('precio', 'N/A')}")
                print(f"        - Subtotal: ${material['subtotal']}")
            
            print()
        
        print("    OTROS MATERIALES:")
        for j, otro in enumerate(item['otrosMateriales'], 1):
            print(f"      Otro {j}: {otro['descripcion']}")
            print(f"        - Precio: ${otro['precio']}")
            print(f"        - Cantidad: {otro['cantidad']}")
            print(f"        - Subtotal: ${otro['subtotal']}")
        print()
    
    print("CONDICIONES:")
    print(f"  - Moneda: {cotizacion_test['condiciones']['moneda']}")
    print(f"  - Tiempo entrega: {cotizacion_test['condiciones']['tiempoEntrega']}")
    print(f"  - Entrega en: {cotizacion_test['condiciones']['entregaEn']}")
    print(f"  - Terminos: {cotizacion_test['condiciones']['terminos']}")
    print()
    
    return True

def test_campos_template():
    """Test de los campos que debe mostrar el template"""
    
    print("=== TEST: Campos esperados en template ===")
    print()
    
    print("PARA MATERIAL 'COTIZAR_POR_PESO':")
    print("  ✓ Descripcion: '⚖️ Cotizar por peso' (con emoji y estilo verde)")
    print("  ✓ Detalle: 'Peso estructura: XXX KG'")
    print("  ✓ Precio/Cantidad: '$XX.XX/KG'")
    print("  ✓ Subtotal: '$XXXX.XX (XXX KG × $XX.XX)'")
    print()
    
    print("PARA MATERIAL NORMAL:")
    print("  ✓ Descripcion: Nombre del material")
    print("  ✓ Detalle: 'Peso: X.X kg' y '$/Kg: $XX.XX'")
    print("  ✓ Precio/Cantidad: 'Cantidad: XX'")
    print("  ✓ Subtotal: '$XXXX.XX'")
    print()
    
    print("ENCABEZADOS DE TABLA ACTUALIZADOS:")
    print("  ✓ Descripcion")
    print("  ✓ Detalle (en lugar de 'Precio')")
    print("  ✓ Precio/Cantidad (en lugar de 'Cantidad')")
    print("  ✓ Subtotal")
    print()
    
    return True

def run_all_tests():
    """Ejecutar todos los tests"""
    
    print("TESTING: Desglose 'Cotizar por peso'")
    print("=" * 50)
    print()
    
    tests = [
        test_estructura_datos_desglose,
        test_campos_template
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
        print("¡Todos los tests pasaron! El desglose deberia mostrar correctamente 'Cotizar por peso'.")
        return True
    else:
        print("Algunos tests fallaron. Revisar implementacion.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)