#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Simple de Revisión - Sin Unicode
=====================================
"""

import requests
import json
from datetime import datetime

def test_simple_revision():
    """Test simple de revisión R2"""
    
    print("TESTING SIMPLE REVISION CREATION")
    print("=" * 40)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Datos para REVISIÓN R2 (simplificados)
    revision_data = {
        "numeroCotizacionHidden": "TEST-SDK-F-CWS-FI-001-R1-SDK-REST-P",
        "datosGenerales": {
            "cliente": "TEST-SDK-FIXED",
            "vendedor": "FIXED-SYSTEM", 
            "proyecto": "SDK-REST-PRIORITY-TEST",
            "revision": 2,
            "actualizacionRevision": "Test de revision R2 con sistema arreglado SDK REST - mas de 10 caracteres"
        },
        "items": [
            {
                "descripcion": "Item original", 
                "cantidad": 1,
                "precio_unitario": 199.99
            },
            {
                "descripcion": "Item agregado R2", 
                "cantidad": 1,
                "precio_unitario": 99.99
            }
        ],
        "condiciones": {
            "moneda": "MXN"
        },
        "observaciones": "REVISION R2 test"
    }
    
    print(f"Cotizacion base: {revision_data['numeroCotizacionHidden']}")
    print(f"Revision: R{revision_data['datosGenerales']['revision']}")
    
    try:
        response = requests.post(
            f"{base_url}/formulario",
            json=revision_data,
            timeout=30
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: Revision R2 creada correctamente!")
            try:
                resp_json = response.json()
                numero_generado = resp_json.get('numeroCotizacion', 'N/A')
                print(f"Numero generado: {numero_generado}")
                
                # Verificar si es realmente R2
                if 'R2' in numero_generado:
                    print("EXCELENTE: Número correcto con R2")
                elif numero_generado == revision_data['numeroCotizacionHidden']:
                    print("INFO: Número igual al base - verificar si es actualización in-place")
                else:
                    print("REVISAR: Número generado diferente al esperado")
                    
                # Mostrar toda la respuesta
                print(f"Respuesta completa: {response.text[:300]}...")
                
            except:
                print(f"Response text: {response.text[:200]}")
        else:
            print(f"ERROR HTTP {response.status_code}")
            if response.text:
                print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_simple_revision()