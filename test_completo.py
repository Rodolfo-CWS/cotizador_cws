#!/usr/bin/env python3
"""
Test completo de la funcionalidad de numeración automática
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
import json
import requests

def test_backend_completo():
    """Prueba completa del backend"""
    print("=== TEST COMPLETO: Backend y Numeración Automática ===\n")
    
    # 1. Test de generación automática
    print("1. Test de DatabaseManager:")
    db = DatabaseManager()
    
    # 2. Test de guardado con datos reales del formulario
    print("2. Test de guardado de cotización:")
    datos_cotizacion = {
        "datosGenerales": {
            "cliente": "ACME Corporation",
            "vendedor": "Juan Pérez",
            "proyecto": "Torre Residencial", 
            "atencionA": "Luis Gómez",
            "contacto": "luis@acme.com",
            "revision": "1"
            # Nota: NO incluimos numeroCotizacion - se debe generar automáticamente
        },
        "items": [{
            "descripcion": "Rack Metálico",
            "cantidad": "2",
            "uom": "Pieza",
            "costoUnidad": "1500.00",
            "total": "3000.00",
            "materiales": [],
            "otrosMateriales": []
        }],
        "condiciones": {
            "moneda": "MXN",
            "tiempoEntrega": "15 días hábiles",
            "entregaEn": "Planta ACME",
            "terminos": "50% anticipo, 50% contra entrega"
        }
    }
    
    resultado = db.guardar_cotizacion(datos_cotizacion)
    print("Resultado del guardado:")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    
    if resultado.get("success"):
        numero_generado = resultado.get("numeroCotizacion")
        print(f"\n✓ Número generado exitosamente: {numero_generado}")
        
        # 3. Test de nueva revisión
        print("\n3. Test de nueva revisión:")
        datos_revision = datos_cotizacion.copy()
        datos_revision["datosGenerales"]["revision"] = "2"
        datos_revision["datosGenerales"]["numeroCotizacion"] = numero_generado  # Incluir número original
        datos_revision["datosGenerales"]["actualizacionRevision"] = "Cambio en especificaciones técnicas"
        
        resultado_revision = db.guardar_cotizacion(datos_revision)
        print("Resultado de la revisión:")
        print(json.dumps(resultado_revision, indent=2, ensure_ascii=False))
        
        if resultado_revision.get("success"):
            numero_revision = resultado_revision.get("numeroCotizacion")
            print(f"\n✓ Número de revisión generado: {numero_revision}")
            print(f"  Original: {numero_generado}")
            print(f"  Revisión: {numero_revision}")
        
        # 4. Test de búsqueda
        print("\n4. Test de búsqueda:")
        cotizacion_guardada = db.obtener_cotizacion(numero_generado)
        if cotizacion_guardada.get("encontrado"):
            print("✓ Cotización encontrada en la base de datos")
        else:
            print("✗ Error: Cotización no encontrada")
            
    else:
        print("✗ Error en el guardado:", resultado.get("error"))
    
    db.cerrar_conexion()
    print("\n=== Test Backend Completado ===")

def test_servidor_flask():
    """Test del servidor Flask si está ejecutándose"""
    print("\n=== TEST OPCIONAL: Servidor Flask ===")
    try:
        # Verificar si el servidor está corriendo
        response = requests.get("http://127.0.0.1:5000/info", timeout=5)
        if response.status_code == 200:
            print("✓ Servidor Flask está corriendo")
            info = response.json()
            print(f"  - WeasyPrint: {info.get('weasyprint_disponible', 'No disponible')}")
            print(f"  - Generación PDF: {info.get('generacion_pdf', 'Desconocido')}")
        else:
            print("⚠ Servidor responde pero con error:", response.status_code)
    except requests.exceptions.RequestException:
        print("ℹ Servidor Flask no está corriendo (esto es normal si no lo has iniciado)")
    except Exception as e:
        print(f"⚠ Error verificando servidor: {e}")

if __name__ == "__main__":
    test_backend_completo()
    test_servidor_flask()
    print("\n✓ Todos los tests completados")