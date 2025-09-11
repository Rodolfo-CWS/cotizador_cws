#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Enhanced SDK Error Logging
==============================

Crear una cotización para ver el error específico del SDK REST
con el logging mejorado ahora en producción.
"""

import requests
import json
from datetime import datetime
import time

def test_sdk_error_logging():
    """Test para ver el error específico del SDK REST"""
    
    print("TESTING ENHANCED SDK ERROR LOGGING")
    print("=" * 40)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Crear cotización simple para ver error SDK
    timestamp = int(time.time())
    
    test_data = {
        "datosGenerales": {
            "cliente": f"ERROR-LOG-{timestamp}",
            "vendedor": "ERROR-TEST", 
            "proyecto": "SDK-ERROR-DIAGNOSIS"
        },
        "items": [{
            "descripcion": f"Test error logging {timestamp}", 
            "cantidad": 1,
            "precio_unitario": 99.99
        }],
        "condiciones": {"moneda": "MXN"},
        "observaciones": f"Test enhanced error logging - {timestamp}"
    }
    
    print(f"Timestamp: {timestamp}")
    print(f"Cliente: {test_data['datosGenerales']['cliente']}")
    
    try:
        print(f"\nEnviando cotización...")
        
        response = requests.post(
            f"{base_url}/formulario",
            json=test_data,
            timeout=30
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Sistema reporta: {result.get('mensaje')}")
            print(f"Número generado: {result.get('numeroCotizacion')}")
            
            print(f"\nRESULTADO:")
            if result.get('success'):
                print("- Sistema reporta ÉXITO")
                print("- PERO ahora deberíamos ver en logs de Render:")
                print("  [HIBRIDO] SDK REST falló: [error específico]")
                print("  [HIBRIDO] SDK REST resultado completo: [JSON completo]") 
                print("\nEsto nos dirá exactamente por qué falla SDK REST")
            else:
                print("- Sistema reporta ERROR")
                
        else:
            print(f"Error HTTP: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")
        
    print("\n" + "=" * 40)
    print("INSTRUCCIONES:")
    print("1. Ve a Render Dashboard → cotizador-cws → Logs")
    print("2. Busca líneas que contengan:")
    print("   '[HIBRIDO] SDK REST falló:'")
    print("   '[HIBRIDO] SDK REST resultado completo:'")
    print("3. Eso revelará el error exacto del SDK")
    print("=" * 40)

if __name__ == "__main__":
    test_sdk_error_logging()