#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test SDK Verification - Descubrir Por Qué No Aparece en Supabase
==============================================================

Crear una cotización específicamente para verificar si el SDK REST
realmente está funcionando o si está fallando silenciosamente.
"""

import requests
import json
from datetime import datetime
import time

def test_sdk_verification():
    """Test específico para verificar funcionamiento SDK REST"""
    
    print("TESTING SDK REST VERIFICATION - SUPABASE DB CHECK")
    print("=" * 55)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Crear cotización con timestamp único para tracking
    timestamp_unique = int(time.time())
    
    test_quotation = {
        "datosGenerales": {
            "cliente": f"SDK-VERIFY-{timestamp_unique}",
            "vendedor": "SDK-TEST", 
            "proyecto": "VERIFICATION-TEST",
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "contacto": f"sdk-test-{timestamp_unique}@verification.com"
        },
        "items": [{
            "descripcion": f"SDK verification item - timestamp {timestamp_unique}", 
            "cantidad": 1,
            "precio_unitario": 123.45
        }],
        "condiciones": {"moneda": "MXN"},
        "observaciones": f"SDK VERIFICATION TEST - Timestamp: {timestamp_unique} - If this appears in Supabase DB, SDK is working"
    }
    
    print(f"Timestamp único: {timestamp_unique}")
    print(f"Cliente: {test_quotation['datosGenerales']['cliente']}")
    
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Enviando cotización de verificación...")
        
        response = requests.post(
            f"{base_url}/formulario",
            json=test_quotation,
            timeout=30
        )
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            numero_generado = result.get('numeroCotizacion')
            
            print(f"RESPUESTA DEL SISTEMA:")
            print(f"  Success: {result.get('success', 'N/A')}")
            print(f"  Número: {numero_generado}")
            print(f"  Mensaje: {result.get('mensaje', 'N/A')}")
            print(f"  PDF generado: {result.get('pdf_generado')}")
            
            if numero_generado:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] VERIFICANDO EN BÚSQUEDA DEL SISTEMA...")
                
                # Esperar un momento para que se propague
                time.sleep(2)
                
                # Buscar la cotización recién creada
                search_response = requests.post(
                    f"{base_url}/buscar",
                    json={"query": numero_generado},
                    timeout=10
                )
                
                if search_response.status_code == 200:
                    search_results = search_response.json()
                    resultados = search_results.get('resultados', [])
                    
                    print(f"  Búsqueda en sistema: {len(resultados)} resultado(s)")
                    
                    if resultados:
                        cotizacion_encontrada = resultados[0]
                        print(f"  ✓ ENCONTRADA EN SISTEMA:")
                        print(f"    Cliente: {cotizacion_encontrada.get('cliente')}")
                        print(f"    Número: {cotizacion_encontrada.get('numero_cotizacion')}")
                        print(f"    Tiene URL PDF: {bool(cotizacion_encontrada.get('url'))}")
                        
                        # Intentar obtener breakdown
                        print(f"\n  VERIFICANDO DESGLOSE DETALLADO...")
                        id_cotizacion = cotizacion_encontrada.get('_id') or cotizacion_encontrada.get('id')
                        
                        if id_cotizacion:
                            desglose_response = requests.get(
                                f"{base_url}/desglose/{id_cotizacion}",
                                timeout=10
                            )
                            print(f"  Desglose disponible: HTTP {desglose_response.status_code}")
                        
                    else:
                        print(f"  ✗ NO ENCONTRADA EN BÚSQUEDA DEL SISTEMA")
                        print(f"  ESTO CONFIRMA: La cotización se 'guardó' pero no es accesible")
                        
                else:
                    print(f"  Error en búsqueda: HTTP {search_response.status_code}")
                    
            print(f"\n" + "=" * 55)
            print("ANÁLISIS DE RESULTADOS:")
            
            if result.get('success') and numero_generado:
                print("✓ Sistema reporta: ÉXITO")
                print("? Verificación necesaria: ¿Aparece en Supabase Database?")
                print()
                print("INSTRUCCIONES PARA VERIFICACIÓN MANUAL:")
                print("1. Accede a tu panel de Supabase")
                print("2. Ve a la tabla 'cotizaciones'") 
                print(f"3. Busca numero_cotizacion = '{numero_generado}'")
                print(f"4. O busca cliente = '{test_quotation['datosGenerales']['cliente']}'")
                print(f"5. O busca observaciones que contengan '{timestamp_unique}'")
                print()
                print("RESULTADOS ESPERADOS:")
                print("- SI aparece → SDK REST funciona, problema es en PDF/retrieval")
                print("- SI NO aparece → SDK REST falla silenciosamente, usar offline mode")
            else:
                print("✗ Sistema reporta: ERROR")
                print("El problema es más básico - revisar logs de Render")
                
        else:
            print(f"ERROR HTTP {response.status_code}")
            print(f"Response: {response.text[:300]}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        
    print("=" * 55)

if __name__ == "__main__":
    test_sdk_verification()