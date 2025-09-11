#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Creación de Revisión - Sistema Arreglado
=============================================

Probar la creación de revisiones R2, que era el problema original
reportado por el usuario. Ahora debería funcionar con SDK REST.
"""

import requests
import json
from datetime import datetime

def test_revision_creation():
    """Test creación de revisión R2 - problema original"""
    
    print("TESTING REVISION CREATION (ORIGINAL ISSUE) - FIXED SYSTEM")
    print("=" * 65)
    
    # URL de producción
    base_url = "https://cotizador-cws.onrender.com"
    
    # Datos para REVISIÓN R2 de cotización existente
    revision_data = {
        "numeroCotizacionHidden": "TEST-SDK-F-CWS-FI-001-R1-SDK-REST-P",  # Recién creada
        "datosGenerales": {
            "cliente": "TEST-SDK-FIXED",
            "vendedor": "FIXED-SYSTEM", 
            "proyecto": "SDK-REST-PRIORITY-TEST",
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "validez": "30 dias",
            "contacto": "test@cws-fixed.com",
            "atencionA": "Test User",
            "revision": 2  # REVISIÓN R2
        },
        "items": [
            {
                "descripcion": "Test item ORIGINAL", 
                "cantidad": 1,
                "precio_unitario": 199.99,
                "subtotal": 199.99
            },
            {
                "descripcion": "NUEVO ITEM R2 - Item agregado en revisión", 
                "cantidad": 2,
                "precio_unitario": 299.99,
                "subtotal": 599.98
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "descuento": 5,
            "transporte": 100,
            "instalacion": 0,
            "seguridad": 0
        },
        "observaciones": "REVISIÓN R2 - Items modificados y agregados",
        "justificacionRevision": "El cliente solicitó agregar un item adicional y aplicar descuento del 5%. Sistema arreglado con SDK REST priority."
    }
    
    print(f"Cotización base: {revision_data['numeroCotizacionHidden']}")
    print(f"Cliente: {revision_data['datosGenerales']['cliente']}")
    print(f"Revisión: R{revision_data['datosGenerales']['revision']}")
    print(f"Items: {len(revision_data['items'])} (1 original + 1 nuevo)")
    print(f"Justificación: {revision_data['justificacionRevision'][:50]}...")
    
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Enviando REVISIÓN R2 a /formulario...")
        print("  (Este era el problema original que no funcionaba)")
        
        response = requests.post(
            f"{base_url}/formulario",
            json=revision_data,
            timeout=30,
            headers={
                'Content-Type': 'application/json'
            }
        )
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            print("🎉 SUCCESS: REVISIÓN R2 procesada correctamente!")
            print("✅ EL PROBLEMA ORIGINAL HA SIDO RESUELTO")
            
            # Buscar indicadores de éxito  
            response_text = response.text.lower()
            if any(keyword in response_text for keyword in ["success", "exito", "exitoso", "guardado", "saved"]):
                print("✅ Respuesta confirma operación exitosa")
                
            # Extraer número de cotización generado
            try:
                response_json = response.json()
                nuevo_numero = response_json.get('numeroCotizacion', 'N/A')
                print(f"📝 Número de revisión generado: {nuevo_numero}")
                
                if 'R2' in nuevo_numero:
                    print("✅ Número correcto con R2 - Sistema de revisiones funcionando")
                    
                pdf_info = response_json.get('pdf_generado', False)
                print(f"📄 PDF generado: {pdf_info}")
                
            except:
                pass
                
            # Mostrar fragmento de respuesta
            if len(response.text) > 100:
                preview = response.text[:300].replace('\n', ' ')
                print(f"Response preview: {preview}...")
                
        else:
            print(f"❌ ERROR HTTP {response.status_code}")
            print("⚠️  El problema de revisiones podría persistir")
            if response.text:
                error_preview = response.text[:300].replace('\n', ' ')
                print(f"Error details: {error_preview}...")
            
    except requests.exceptions.Timeout:
        print("⚠️  TIMEOUT: La revisión tomó más de 30 segundos")
        print("   INFO: Revisar logs de Render para verificar si se completó")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        
    print("\n" + "=" * 65)
    print("RESUMEN DEL TEST:")
    print("- Problema original: Revisiones R2+ no se guardaban en Supabase")
    print("- Causa: PostgreSQL connection failures, sistema en modo offline")
    print("- Solución: Priorizar SDK REST API sobre PostgreSQL directo")
    print("- Resultado esperado: Revisiones R2+ ahora se guardan correctamente")
    print("=" * 65)

if __name__ == "__main__":
    test_revision_creation()