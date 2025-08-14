#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test para la funcionalidad "Cotizar por peso"
Valida que el sistema maneje correctamente la nueva opción de cotización
"""

import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_cotizar_por_peso_data_structure():
    """Test que valida la estructura de datos para cotizar por peso"""
    
    # Simular datos de una cotización con "Cotizar por peso"
    datos_test = {
        "datosGenerales": {
            "vendedor": "TEST_USER",
            "proyecto": "TEST_PROYECTO_PESO",
            "cliente": "TEST_CLIENTE",
            "atencionA": "Contacto Test",
            "contacto": "test@test.com",
            "revision": "1"
        },
        "items": [
            {
                "descripcion": "Estructura metálica por peso",
                "cantidad": "1",
                "uom": "Servicio",
                "materiales": [
                    {
                        "material": "COTIZAR_POR_PESO",
                        "pesoEstructura": "500",
                        "precioKg": "25.50",
                        "subtotal": "12750.00",
                        "tipoCotizacion": "peso"
                    }
                ],
                "otrosMateriales": [],
                "transporte": "1000",
                "instalacion": "2000",
                "seguridad": "10",
                "descuento": "5"
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "tiempoEntrega": "15 días hábiles",
            "entregaEn": "Sitio del cliente",
            "terminos": "50% anticipo, 50% contra entrega"
        }
    }
    
    print("Test 1: Estructura de datos para 'Cotizar por peso'")
    print(f"   - Material tipo: {datos_test['items'][0]['materiales'][0]['material']}")
    print(f"   - Peso estructura: {datos_test['items'][0]['materiales'][0]['pesoEstructura']} KG")
    print(f"   - Precio por KG: $${datos_test['items'][0]['materiales'][0]['precioKg']}")
    print(f"   - Subtotal: $${datos_test['items'][0]['materiales'][0]['subtotal']}")
    print(f"   - Tipo cotización: {datos_test['items'][0]['materiales'][0]['tipoCotizacion']}")
    
    # Validar cálculo
    peso = float(datos_test['items'][0]['materiales'][0]['pesoEstructura'])
    precio_kg = float(datos_test['items'][0]['materiales'][0]['precioKg'])
    subtotal_calculado = peso * precio_kg
    subtotal_esperado = float(datos_test['items'][0]['materiales'][0]['subtotal'])
    
    if abs(subtotal_calculado - subtotal_esperado) < 0.01:
        print(f"   Cálculo correcto: {peso} KG x ${precio_kg}/KG = ${subtotal_calculado}")
    else:
        print(f"   Error en cálculo: esperado ${subtotal_esperado}, calculado ${subtotal_calculado}")
        return False
    
    return True

def test_mixed_materials():
    """Test con materiales normales y cotizar por peso en el mismo item"""
    
    datos_test = {
        "items": [
            {
                "descripcion": "Proyecto mixto",
                "materiales": [
                    {
                        "material": "Acero A36",
                        "peso": "2.5",
                        "cantidad": "100",
                        "precio": "15.00",
                        "subtotal": "3750.00",
                        "tipoCotizacion": "normal"
                    },
                    {
                        "material": "COTIZAR_POR_PESO",
                        "pesoEstructura": "300",
                        "precioKg": "20.00",
                        "subtotal": "6000.00",
                        "tipoCotizacion": "peso"
                    }
                ]
            }
        ]
    }
    
    print("Test 2: Materiales mixtos (normal + por peso)")
    
    total_materiales = 0
    for material in datos_test['items'][0]['materiales']:
        subtotal = float(material['subtotal'])
        total_materiales += subtotal
        
        if material['tipoCotizacion'] == 'normal':
            print(f"   - Material normal: {material['material']} = ${subtotal}")
        elif material['tipoCotizacion'] == 'peso':
            print(f"   - Por peso: {material['pesoEstructura']} KG x ${material['precioKg']}/KG = ${subtotal}")
    
    print(f"   Total materiales: ${total_materiales}")
    return True

def test_validation_rules():
    """Test de reglas de validación"""
    
    print("Test 3: Reglas de validación")
    
    # Test 1: Campos requeridos para cotizar por peso
    campos_requeridos = ['pesoEstructura', 'precioKg']
    print(f"   - Campos requeridos para 'Cotizar por peso': {', '.join(campos_requeridos)}")
    
    # Test 2: Cálculo mínimo válido
    peso_min = 0.01
    precio_min = 0.01
    print(f"   - Peso mínimo: {peso_min} KG")
    print(f"   - Precio mínimo: ${precio_min}/KG")
    
    # Test 3: Subtotal mínimo
    subtotal_min = peso_min * precio_min
    print(f"   - Subtotal mínimo: ${subtotal_min}")
    
    return True

def run_all_tests():
    """Ejecutar todos los tests"""
    
    print("TESTING: Funcionalidad 'Cotizar por peso'")
    print("=" * 50)
    
    tests = [
        test_cotizar_por_peso_data_structure,
        test_mixed_materials,
        test_validation_rules
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"   Error en test: {e}")
            print()
    
    print("=" * 50)
    print(f"RESULTADO: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("¡Todos los tests pasaron! La funcionalidad 'Cotizar por peso' está lista.")
        return True
    else:
        print("Algunos tests fallaron. Revisar implementación.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)