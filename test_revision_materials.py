#!/usr/bin/env python3
"""
Test específico para verificar el cálculo de subtotales de materiales en revisiones
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import preparar_datos_nueva_revision

def test_material_subtotals():
    """Test del cálculo de subtotales de materiales en revisiones"""
    print("=== TEST: Cálculo de subtotales de materiales en revisiones ===\n")
    
    # Datos de cotización original con materiales
    cotizacion_original = {
        "datosGenerales": {
            "numeroCotizacion": "ACME-CWS-JP-001-R1-PROYECTO",
            "cliente": "ACME Corp",
            "vendedor": "Juan Perez",
            "proyecto": "Proyecto Test",
            "revision": "1"
        },
        "items": [
            {
                "descripcion": "Rack Metálico",
                "materiales": [
                    {
                        "descripcion": "Perfil L 2x2x1/4",
                        "peso": 2.5,
                        "cantidad": 10,
                        "precio": 45.50,
                        "subtotal": 0  # Este valor debe ser recalculado
                    },
                    {
                        "descripcion": "Soldadura",
                        "peso": 1.0,
                        "cantidad": 5,
                        "precio": 25.00,
                        "subtotal": 0  # Este valor debe ser recalculado
                    }
                ],
                "otros": 100.00,
                "transporte": 50.00,
                "instalacion": 200.00,
                "total": 0  # Debe ser recalculado
            }
        ]
    }
    
    print("1. Datos originales:")
    for item in cotizacion_original["items"]:
        print(f"   Item: {item['descripcion']}")
        for material in item["materiales"]:
            print(f"      Material: {material['descripcion']} - Subtotal original: {material['subtotal']}")
    
    # Preparar datos para nueva revisión
    print("\n2. Preparando nueva revisión...")
    datos_revision = preparar_datos_nueva_revision(cotizacion_original)
    
    if datos_revision:
        print("3. Datos después de preparar revisión:")
        revision_num = datos_revision["datosGenerales"]["revision"]
        numero_nuevo = datos_revision["datosGenerales"]["numeroCotizacion"]
        print(f"   Nueva revisión: {revision_num}")
        print(f"   Nuevo número: {numero_nuevo}")
        
        print("\n4. Subtotales de materiales recalculados:")
        for item in datos_revision["items"]:
            print(f"   Item: {item['descripcion']}")
            for material in item["materiales"]:
                peso = material.get('peso', 1.0)
                cantidad = material.get('cantidad', 0)
                precio = material.get('precio', 0)
                subtotal = material.get('subtotal', 0)
                
                subtotal_esperado = peso * cantidad * precio
                
                print(f"      Material: {material['descripcion']}")
                print(f"         Peso: {peso}, Cantidad: {cantidad}, Precio: {precio}")
                print(f"         Subtotal calculado: {subtotal}")
                print(f"         Subtotal esperado: {subtotal_esperado}")
                
                if abs(subtotal - subtotal_esperado) < 0.01:  # Permitir diferencias de redondeo
                    print("         ✓ CORRECTO")
                else:
                    print("         ✗ ERROR - subtotal incorrecto")
                    return False
            
            print(f"   Total del item: {item.get('total', 0)}")
        
        print("\n✓ TEST EXITOSO: Los subtotales de materiales se calculan correctamente en revisiones")
        return True
    else:
        print("✗ ERROR: No se pudieron preparar los datos de revisión")
        return False

if __name__ == "__main__":
    success = test_material_subtotals()
    sys.exit(0 if success else 1)