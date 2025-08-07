#!/usr/bin/env python3
"""
Test completo del proceso: Guardar cotización + Generar PDF
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
import json

def test_guardar_y_buscar():
    """Test del proceso completo de guardado y búsqueda para PDF"""
    print("=== TEST: Proceso completo Guardar + Buscar para PDF ===\n")
    
    # 1. Inicializar DatabaseManager
    db = DatabaseManager()
    
    # 2. Datos de prueba simulando el formulario
    datos_cotizacion = {
        "datosGenerales": {
            "cliente": "ACME Corporation",
            "vendedor": "Juan Perez",
            "proyecto": "Torre Residencial", 
            "atencionA": "Luis Gomez",
            "contacto": "luis@acme.com",
            "revision": "1"
            # SIN numeroCotizacion - se genera automáticamente
        },
        "items": [{
            "descripcion": "Rack Metalico",
            "cantidad": "2",
            "uom": "Pieza",
            "costoUnidad": "1500.00",
            "total": "3000.00",
            "transporte": "200.00",
            "instalacion": "300.00",
            "materiales": [],
            "otrosMateriales": []
        }],
        "condiciones": {
            "moneda": "MXN",
            "tiempoEntrega": "15 dias habiles",
            "entregaEn": "Planta ACME",
            "terminos": "50% anticipo, 50% contra entrega",
            "comentarios": "Instalacion incluida"
        }
    }
    
    print("1. Guardando cotización...")
    resultado = db.guardar_cotizacion(datos_cotizacion)
    
    if not resultado.get("success"):
        print(f"ERROR en guardado: {resultado.get('error')}")
        return False
    
    numero_generado = resultado.get("numeroCotizacion")
    print(f"✓ Cotización guardada exitosamente")
    print(f"  - ID: {resultado.get('id')}")
    print(f"  - Número: {numero_generado}")
    print(f"  - Formato: Cliente-CWS-Iniciales-###-R#-Proyecto")
    
    # 3. Test de búsqueda (simulando lo que hace el PDF)
    print(f"\n2. Buscando cotización por número: {numero_generado}")
    resultado_busqueda = db.obtener_cotizacion(numero_generado)
    
    if not resultado_busqueda.get("encontrado"):
        print(f"ERROR: Cotización no encontrada")
        print(f"Mensaje: {resultado_busqueda.get('mensaje')}")
        return False
    
    cotizacion_encontrada = resultado_busqueda.get("item")
    print(f"✓ Cotización encontrada para PDF")
    print(f"  - Cliente: {cotizacion_encontrada.get('datosGenerales', {}).get('cliente')}")
    print(f"  - Items: {len(cotizacion_encontrada.get('items', []))}")
    print(f"  - Condiciones: {len(cotizacion_encontrada.get('condiciones', {}))}")
    
    # 4. Verificar que los datos están completos para PDF
    print(f"\n3. Verificando datos para PDF...")
    datos_generales = cotizacion_encontrada.get('datosGenerales', {})
    items = cotizacion_encontrada.get('items', [])
    condiciones = cotizacion_encontrada.get('condiciones', {})
    
    campos_requeridos = ['cliente', 'vendedor', 'proyecto', 'atencionA', 'contacto']
    todos_presentes = all(datos_generales.get(campo) for campo in campos_requeridos)
    
    if todos_presentes and len(items) > 0:
        print("✓ Todos los datos necesarios están presentes para PDF")
        print(f"  - Datos generales: {len(datos_generales)} campos")
        print(f"  - Items: {len(items)}")
        print(f"  - Condiciones: {len(condiciones)} campos")
        
        # 5. Simular estructura de datos que se envía al template PDF
        datos_para_template = {
            "cotizacion": {
                "datosGenerales": datos_generales,
                "items": items,
                "condiciones": condiciones
            }
        }
        print("✓ Datos estructurados correctamente para template PDF")
        return True
    else:
        print("ERROR: Faltan datos requeridos para PDF")
        return False
    
    db.cerrar_conexion()

def test_busqueda_directa():
    """Test de búsqueda con diferentes formatos de número"""
    print("\n=== TEST: Búsqueda con diferentes formatos ===")
    
    db = DatabaseManager()
    
    # Probar con números existentes en diferentes formatos
    numeros_prueba = [
        "ACMECORPOR-CWS-JP-001-R1-TORRERESID",  # Formato nuevo
        "ACMECORPORCWSJP001R1TORRERESID",        # Formato anterior
        "acmecorpor-cws-jp-001-r1-torreresid"    # Minúsculas
    ]
    
    for numero in numeros_prueba:
        print(f"\nProbando búsqueda: {numero}")
        resultado = db.obtener_cotizacion(numero)
        if resultado.get("encontrado"):
            print(f"✓ Encontrada")
        else:
            print(f"✗ No encontrada")
    
    db.cerrar_conexion()

if __name__ == "__main__":
    success = test_guardar_y_buscar()
    test_busqueda_directa()
    
    if success:
        print("\n" + "="*50)
        print("✓ TEST COMPLETO EXITOSO")
        print("La funcionalidad de PDF debería funcionar correctamente")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("✗ TEST FALLÓ - Revisar errores arriba")
        print("="*50)