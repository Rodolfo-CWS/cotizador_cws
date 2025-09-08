#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test del Sistema Arreglado - SDK REST Priority
=============================================

Probar el sistema con la nueva prioridad de SDK REST sobre PostgreSQL.
Debería funcionar correctamente ahora.
"""

import requests
import json
from datetime import datetime

def test_new_quotation():
    """Test creación de cotización nueva con sistema arreglado"""
    
    print("TESTING FIXED QUOTATION SYSTEM - SDK REST PRIORITY")
    print("=" * 60)
    
    # URL de producción
    base_url = "https://cotizador-cws.onrender.com"
    
    # Datos para nueva cotización (formato JSON correcto)
    quotation_data = {
        "datosGenerales": {
            "cliente": "TEST-SDK-FIXED",
            "vendedor": "FIXED-SYSTEM", 
            "proyecto": "SDK-REST-PRIORITY-TEST",
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "validez": "30 dias",
            "contacto": "test@cws-fixed.com",
            "atencionA": "Test User"
        },
        "items": [{
            "descripcion": "Test item con sistema arreglado", 
            "cantidad": 1,
            "precio_unitario": 199.99,
            "subtotal": 199.99
        }],
        "condiciones": {
            "moneda": "MXN",
            "descuento": 0,
            "transporte": 0,
            "instalacion": 0,
            "seguridad": 0
        },
        "observaciones": "Test del sistema arreglado - SDK REST debe funcionar ahora"
    }
    
    print(f"Cliente: {quotation_data['datosGenerales']['cliente']}")
    print(f"Vendedor: {quotation_data['datosGenerales']['vendedor']}")
    print(f"Proyecto: {quotation_data['datosGenerales']['proyecto']}")
    
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Enviando cotización a /formulario...")
        
        response = requests.post(
            f"{base_url}/formulario",
            json=quotation_data,  # Usar json= en lugar de data=
            timeout=30,
            headers={
                'Content-Type': 'application/json'  # JSON content type
            }
        )
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: Cotización procesada correctamente!")
            
            # Buscar indicadores de éxito
            response_text = response.text.lower()
            if any(keyword in response_text for keyword in ["success", "exito", "exitoso", "guardado", "saved"]):
                print("EXCELENTE: Respuesta indica operación exitosa")
            else:
                print("INFO: Revisar logs de Render para confirmar éxito")
                
            # Mostrar fragmento de respuesta  
            if len(response.text) > 100:
                preview = response.text[:200].replace('\n', ' ')
                print(f"Response preview: {preview}...")
                
        else:
            print(f"ERROR HTTP {response.status_code}")
            if response.text:
                error_preview = response.text[:300].replace('\n', ' ')
                print(f"Error details: {error_preview}...")
            
    except requests.exceptions.Timeout:
        print("TIMEOUT: La operación tomó más de 30 segundos")
        print("INFO: Revisar logs de Render para ver si se completó")
        
    except Exception as e:
        print(f"ERROR: {e}")
        
    print("\n" + "=" * 60)
    print("LOGS DE RENDER DEBERÍAN MOSTRAR AHORA:")
    print("[HIBRIDO] PRIORIDAD 1: Intentando SDK REST de Supabase...")
    print("[HIBRIDO] SDK REST exitoso - operación completada")  
    print("(Sin intentar PostgreSQL directo que causaba problemas)")
    print("=" * 60)

if __name__ == "__main__":
    test_new_quotation()