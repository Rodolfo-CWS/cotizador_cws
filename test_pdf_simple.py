#!/usr/bin/env python3
"""
Test simple de PDF con colores grises
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import generar_pdf_reportlab, REPORTLAB_AVAILABLE
    print("OK: Funcion generar_pdf_reportlab importada correctamente")
except ImportError as e:
    print(f"ERROR: Error importando funcion PDF: {e}")
    sys.exit(1)

def crear_datos_test():
    return {
        "datosGenerales": {
            "cliente": "TEST COLORES GRISES",
            "vendedor": "VERIFICACION",
            "proyecto": "CAMBIO DE COLORES PDF",
            "numeroCotizacion": "TEST-GRISES-CWS-VER-001-R1-COLORES",
            "revision": 1
        },
        "items": [
            {
                "descripcion": "Servicio de prueba",
                "cantidad": 1,
                "precio_unitario": 1000.0,
                "subtotal": 1000.0
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "total": 1160.0
        }
    }

def main():
    print("TEST: Verificacion PDF con colores grises")
    print("=" * 50)
    
    if not REPORTLAB_AVAILABLE:
        print("ERROR: ReportLab no disponible")
        return False
    
    try:
        datos_test = crear_datos_test()
        pdf_bytes = generar_pdf_reportlab(datos_test)
        
        if pdf_bytes and len(pdf_bytes) > 1000:
            filename = "test_pdf_grises_simple.pdf"
            with open(filename, 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"OK: PDF generado exitosamente: {len(pdf_bytes)} bytes")
            print(f"OK: PDF guardado como: {filename}")
            
            # Verificar cambios de colores en codigo
            with open('app.py', 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            azules = contenido.count('#2C5282') + contenido.count('#1A365D')
            grises = contenido.count('#4A5568') + contenido.count('#2D3748')
            
            print(f"INFO: Colores azules en codigo: {azules}")
            print(f"INFO: Colores grises en codigo: {grises}")
            
            if azules == 0 and grises > 5:
                print("OK: Cambios de colores aplicados correctamente")
                print("OK: VERIFICACION EXITOSA - PDF con colores grises")
                return True
            else:
                print("WARNING: Verificar cambios de colores")
                return False
                
        else:
            print("ERROR: PDF no generado correctamente")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print("=" * 50)
    if success:
        print("RESULTADO: EXITOSO - Funcionalidad intacta, colores cambiados a gris")
    else:
        print("RESULTADO: ERROR - Revisar implementacion")
    sys.exit(0 if success else 1)