#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test After Complete Restart - Verificar Fix Aplicado
===================================================

Probar después del restart completo que el SDK REST fix se aplicó.
"""

import requests
import json
from datetime import datetime
import time

def test_after_restart():
    """Test después del restart completo"""
    
    print("TESTING AFTER COMPLETE RESTART - SDK REST FIX")
    print("=" * 50)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Test con timestamp único
    timestamp = int(time.time())
    
    test_data = {
        "datosGenerales": {
            "cliente": f"RESTART-TEST-{timestamp}",
            "vendedor": "POST-RESTART", 
            "proyecto": "SDK-REST-VERIFICATION",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        "items": [{
            "descripcion": f"Post restart test - {timestamp}", 
            "cantidad": 1,
            "precio_unitario": 777.77
        }],
        "condiciones": {"moneda": "MXN"},
        "observaciones": f"Test después de restart completo - {timestamp}"
    }
    
    print(f"Timestamp: {timestamp}")
    print(f"Cliente: {test_data['datosGenerales']['cliente']}")
    
    try:
        print(f"\nCreando cotización post-restart...")
        
        response = requests.post(
            f"{base_url}/formulario",
            json=test_data,
            timeout=30
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            numero_generado = result.get('numeroCotizacion')
            
            print(f"Success: {result.get('success')}")
            print(f"Número: {numero_generado}")
            print(f"PDF generado: {result.get('pdf_generado')}")
            
            # Verificar en búsqueda
            if numero_generado:
                print(f"\nVerificando en búsqueda...")
                time.sleep(3)
                
                search_response = requests.post(
                    f"{base_url}/buscar",
                    json={"query": numero_generado},
                    timeout=10
                )
                
                if search_response.status_code == 200:
                    search_results = search_response.json()
                    resultados = search_results.get('resultados', [])
                    
                    print(f"Cotizaciones encontradas: {len(resultados)}")
                    
                    if resultados:
                        print("EXITO: Cotización encontrada en sistema")
                        cotizacion = resultados[0]
                        print(f"Cliente: {cotizacion.get('cliente')}")
                        tiene_pdf = bool(cotizacion.get('url'))
                        print(f"Tiene PDF: {tiene_pdf}")
                        
                        # Resultado final
                        if result.get('pdf_generado') and tiene_pdf:
                            print("\n*** SISTEMA COMPLETAMENTE FUNCIONAL ***")
                            print("- Cotización guardada en Supabase")
                            print("- PDF generado correctamente")
                            print("- Sistema fuera de modo offline")
                            
                        elif not result.get('pdf_generado'):
                            print("\nParcialmente funcional:")
                            print("- Cotización en Supabase: SI")
                            print("- PDF generado: NO")
                            print("- Necesita revisar logs para ver error PDF")
                            
                    else:
                        print("PROBLEMA: Cotización no encontrada")
                        print("Sistema posiblemente aún en modo offline")
                        
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")
        
    print(f"\n" + "=" * 50)
    print("INSTRUCCIONES:")
    print("1. Verifica los logs de Render para esta cotización")
    print("2. Busca específicamente:")
    print("   [HIBRIDO] PRIORIDAD 1: Intentando SDK REST...")
    print("   [SDK_REST] INICIO - Guardando cotización...")
    print("3. Si ves esos logs = FIX APLICADO CORRECTAMENTE")
    print("4. Verifica también en Supabase si aparece:")
    print(f"   Cliente: RESTART-TEST-{timestamp}")
    print("=" * 50)

if __name__ == "__main__":
    test_after_restart()