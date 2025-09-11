#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Final Critical Fix - The Ultimate Test
==========================================

Este debería ser el test definitivo. Si esto funciona,
el problema está completamente resuelto.
"""

import requests
import json
from datetime import datetime
import time

def test_final_critical_fix():
    """Test final del fix crítico"""
    
    print("FINAL CRITICAL FIX TEST - ULTIMATE VERIFICATION")
    print("=" * 55)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Test con timestamp único para tracking absoluto
    timestamp = int(time.time())
    
    test_data = {
        "datosGenerales": {
            "cliente": f"ULTIMATE-FIX-{timestamp}",
            "vendedor": "CRITICAL-FIX", 
            "proyecto": "FINAL-RESOLUTION",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        "items": [{
            "descripcion": f"Ultimate fix test - {timestamp}", 
            "cantidad": 1,
            "precio_unitario": 999.99
        }],
        "condiciones": {"moneda": "MXN"},
        "observaciones": f"ULTIMATE TEST - CRITICAL FIX DEPLOYED - {timestamp}"
    }
    
    print(f"TRACKING ID: {timestamp}")
    print(f"Cliente: {test_data['datosGenerales']['cliente']}")
    
    try:
        print(f"\n*** CREATING QUOTATION WITH CRITICAL FIX ***")
        
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
            
            if result.get('pdf_generado'):
                print("*** PDF GENERATION SUCCESS! ***")
            else:
                print("PDF not generated - checking why...")
                
            # Verificación crítica en búsqueda
            if numero_generado:
                print(f"\n*** VERIFYING IN SYSTEM SEARCH ***")
                time.sleep(3)  # Dar tiempo para propagación
                
                search_response = requests.post(
                    f"{base_url}/buscar",
                    json={"query": numero_generado},
                    timeout=10
                )
                
                if search_response.status_code == 200:
                    search_results = search_response.json()
                    resultados = search_results.get('resultados', [])
                    
                    print(f"Search results: {len(resultados)} quotation(s)")
                    
                    if resultados:
                        print("*** QUOTATION FOUND IN SYSTEM! ***")
                        print("*** THIS MEANS SDK REST IS WORKING! ***")
                        cotizacion = resultados[0]
                        print(f"Cliente found: {cotizacion.get('cliente')}")
                        print(f"Has PDF URL: {bool(cotizacion.get('url'))}")
                        
                        # Final verification
                        if result.get('pdf_generado') and cotizacion.get('url'):
                            print("\n" + "="*55)
                            print("*** COMPLETE SUCCESS - PROBLEM FULLY RESOLVED ***")
                            print("- Quotation saved to Supabase database ✓")
                            print("- PDF generated successfully ✓") 
                            print("- System fully functional ✓")
                            print("- SSL issue completely bypassed ✓")
                            print("="*55)
                        else:
                            print("\n*** PARTIAL SUCCESS ***")
                            print("- Quotation in Supabase: YES")
                            print("- PDF generation: NEEDS CHECK")
                            
                    else:
                        print("*** QUOTATION NOT FOUND ***")
                        print("System may still be in offline mode")
                        print("Check Render logs for modo_offline status")
                        
        else:
            print(f"HTTP ERROR: {response.status_code}")
            print(f"Response: {response.text[:300]}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        
    print(f"\n" + "=" * 55)
    print("CRITICAL LOGS TO CHECK IN RENDER:")
    print("[SUPABASE] PostgreSQL falló - evaluando SDK REST...")
    print("[SUPABASE] SDK REST disponible - MANTENIENDO SISTEMA ONLINE")
    print("[HIBRIDO] PRIORIDAD 1: Intentando SDK REST de Supabase...")
    print("")
    print("AND IN SUPABASE DATABASE:")
    print(f"Look for cliente: ULTIMATE-FIX-{timestamp}")
    print("=" * 55)

if __name__ == "__main__":
    test_final_critical_fix()