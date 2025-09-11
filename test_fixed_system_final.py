#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Sistema Arreglado Final - Verificación Completa
===================================================

Probar que el sistema ahora:
1. Guarda cotizaciones en Supabase (no solo JSON)
2. Genera PDFs correctamente
3. SDK REST funciona independiente de PostgreSQL
"""

import requests
import json
from datetime import datetime
import time

def test_fixed_system_final():
    """Test final del sistema arreglado"""
    
    print("TESTING FIXED SYSTEM - FINAL VERIFICATION")
    print("=" * 50)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Test con timestamp único para tracking
    timestamp = int(time.time())
    
    test_data = {
        "datosGenerales": {
            "cliente": f"FINAL-FIX-{timestamp}",
            "vendedor": "FIXED-SYSTEM", 
            "proyecto": "FINAL-VERIFICATION",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        "items": [{
            "descripcion": f"Final fix verification - {timestamp}", 
            "cantidad": 1,
            "precio_unitario": 888.88
        }],
        "condiciones": {"moneda": "MXN"},
        "observaciones": f"VERIFICATION FINAL DEL SISTEMA ARREGLADO - {timestamp}"
    }
    
    print(f"Timestamp: {timestamp}")
    print(f"Cliente: {test_data['datosGenerales']['cliente']}")
    
    try:
        print(f"\n1. CREANDO COTIZACIÓN...")
        
        response = requests.post(
            f"{base_url}/formulario",
            json=test_data,
            timeout=30
        )
        
        print(f"   HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            numero_generado = result.get('numeroCotizacion')
            
            print(f"   Success: {result.get('success')}")
            print(f"   Número: {numero_generado}")
            print(f"   PDF generado: {result.get('pdf_generado')}")
            
            if result.get('pdf_generado'):
                print("   ✅ PDF GENERADO - EXCELENTE!")
            else:
                pdf_mensaje = result.get('pdf_mensaje', 'Sin mensaje')
                print(f"   ⚠️ PDF no generado: {pdf_mensaje}")
                
            if numero_generado:
                print(f"\n2. VERIFICANDO EN BÚSQUEDA...")
                time.sleep(2)
                
                search_response = requests.post(
                    f"{base_url}/buscar",
                    json={"query": numero_generado},
                    timeout=10
                )
                
                if search_response.status_code == 200:
                    search_results = search_response.json()
                    resultados = search_results.get('resultados', [])
                    
                    print(f"   Encontradas: {len(resultados)} cotización(es)")
                    
                    if resultados:
                        print("   ✅ ENCONTRADA EN SISTEMA")
                        cotizacion = resultados[0]
                        print(f"   Cliente: {cotizacion.get('cliente')}")
                        print(f"   URL PDF: {bool(cotizacion.get('url'))}")
                        
                        # Test 3: Verificar PDF directo
                        if cotizacion.get('url'):
                            print(f"\n3. VERIFICANDO PDF DIRECTO...")
                            try:
                                pdf_response = requests.get(
                                    cotizacion.get('url'), 
                                    timeout=10
                                )
                                print(f"   PDF acceso: HTTP {pdf_response.status_code}")
                                if pdf_response.status_code == 200:
                                    print("   ✅ PDF ACCESIBLE")
                                else:
                                    print(f"   ⚠️ PDF no accesible: {pdf_response.status_code}")
                            except Exception as e:
                                print(f"   ❌ Error accediendo PDF: {e}")
                                
                    else:
                        print("   ❌ NO ENCONTRADA - Sistema sigue en modo offline")
                        
                else:
                    print(f"   Error búsqueda: HTTP {search_response.status_code}")
                    
        else:
            print(f"❌ Error creando cotización: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print(f"\n" + "=" * 50)
    print("RESUMEN:")
    print("SI TODO FUNCIONA CORRECTAMENTE:")
    print("✅ Cotización creada con Success: True")
    print("✅ PDF generado: True")
    print("✅ Cotización encontrada en búsqueda")
    print("✅ PDF accesible via URL")
    print("")
    print("LOGS DE RENDER DEBERÍAN MOSTRAR:")
    print("[HIBRIDO] PRIORIDAD 1: Intentando SDK REST de Supabase...")
    print("[SDK_REST] INICIO - Guardando cotización via SDK REST")
    print("[SDK_REST] VERIFICACIÓN OK - Cotización confirmada en Supabase")
    print("=" * 50)

if __name__ == "__main__":
    test_fixed_system_final()