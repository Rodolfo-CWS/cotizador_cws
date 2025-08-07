#!/usr/bin/env python3
"""
Test script para verificar la funcionalidad de generación automática de números de cotización
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager

def test_generacion_numero():
    """Prueba la generación automática de números de cotización"""
    print("=== TEST: Generación Automática de Números de Cotización ===\n")
    
    # Inicializar DatabaseManager
    db = DatabaseManager()
    
    # Test 1: Generar número básico
    print("1. Generación de número básico:")
    cliente = "ACME Corporation"
    vendedor = "Juan Pérez"
    proyecto = "Torre Residencial"
    revision = 1
    
    numero = db.generar_numero_cotizacion(cliente, vendedor, proyecto, revision)
    print(f"   Cliente: {cliente}")
    print(f"   Vendedor: {vendedor}")
    print(f"   Proyecto: {proyecto}")
    print(f"   Revisión: {revision}")
    print(f"   -> Numero generado: {numero}")
    print()
    
    # Test 2: Generar revisión
    print("2. Generacion de nueva revision:")
    numero_revision_2 = db.generar_numero_revision(numero, 2)
    numero_revision_3 = db.generar_numero_revision(numero, 3)
    print(f"   Numero original: {numero}")
    print(f"   -> Revision 2: {numero_revision_2}")
    print(f"   -> Revision 3: {numero_revision_3}")
    print()
    
    # Test 3: Casos edge con nombres complejos
    print("3. Casos con nombres complejos:")
    casos_test = [
        ("Grupo Empresarial XYZ", "Maria Jose Santos", "Centro Comercial"),
        ("ABC", "Luis", "Proyecto A"),
        ("Empresa Con Nombre Muy Largo", "Jose Maria de la Cruz", "Otro Proyecto Largo"),
    ]
    
    for cliente_test, vendedor_test, proyecto_test in casos_test:
        numero_test = db.generar_numero_cotizacion(cliente_test, vendedor_test, proyecto_test)
        print(f"   {cliente_test} + {vendedor_test} + {proyecto_test}")
        print(f"   -> {numero_test}")
        print()
    
    # Test 4: Obtener consecutivo
    print("4. Test de consecutivos:")
    patron_base = "ACMECORPCWSJP"
    consecutivo = db._obtener_siguiente_consecutivo(patron_base)
    print(f"   Patron base: {patron_base}")
    print(f"   -> Siguiente consecutivo: {consecutivo}")
    print()
    
    print("OK: Todos los tests completados exitosamente!")
    
    # Cerrar conexión
    db.cerrar_conexion()

if __name__ == "__main__":
    test_generacion_numero()