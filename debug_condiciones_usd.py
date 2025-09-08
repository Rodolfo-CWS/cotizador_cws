#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Condiciones USD - Investigar por qué se pierden las condiciones
====================================================================
"""

import requests
import json
from datetime import datetime
import time

def debug_condiciones_usd():
    """Debug del problema de condiciones USD"""
    
    print("DEBUG: Investigando problema con condiciones USD")
    print("=" * 55)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Test data con condiciones USD específicas
    timestamp = int(time.time())
    
    test_data = {
        "datosGenerales": {
            "cliente": f"DEBUG-USD-{timestamp}",
            "vendedor": "USD-DEBUG", 
            "proyecto": "CONDICIONES-TEST",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        "items": [{
            "descripcion": "Debug USD test item", 
            "cantidad": 1,
            "precio_unitario": 100.00
        }],
        "condiciones": {
            "moneda": "USD",
            "tiempoEntrega": "15 días",
            "entregaEn": "Planta cliente", 
            "terminos": "NET 30",
            "comentarios": "Test USD con condiciones completas",
            "tipoCambio": "20.50"
        },
        "observaciones": f"DEBUG USD conditions test - {timestamp}"
    }
    
    print(f"DATOS ENVIADOS:")
    print(f"- Cliente: {test_data['datosGenerales']['cliente']}")
    print(f"- Moneda: {test_data['condiciones']['moneda']}")
    print(f"- Tiempo Entrega: {test_data['condiciones']['tiempoEntrega']}")
    print(f"- Entrega En: {test_data['condiciones']['entregaEn']}")
    print(f"- Términos: {test_data['condiciones']['terminos']}")
    print(f"- Comentarios: {test_data['condiciones']['comentarios']}")
    print(f"- Tipo Cambio: {test_data['condiciones']['tipoCambio']}")
    
    try:
        print(f"\n1. CREANDO COTIZACIÓN USD...")
        
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
            
            if numero_generado:
                print(f"\n2. VERIFICANDO DATOS EN BÚSQUEDA...")
                time.sleep(3)
                
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
                        cotizacion = resultados[0]
                        print(f"\n3. DATOS RECUPERADOS DE LA BASE:")
                        print(f"   - Cliente: {cotizacion.get('cliente', 'NO ENCONTRADO')}")
                        print(f"   - Número: {cotizacion.get('numero_cotizacion', 'NO ENCONTRADO')}")
                        
                        # Verificar condiciones específicamente
                        condiciones_recuperadas = cotizacion.get('condiciones')
                        if isinstance(condiciones_recuperadas, str):
                            try:
                                condiciones_recuperadas = json.loads(condiciones_recuperadas)
                            except:
                                condiciones_recuperadas = {}
                        
                        print(f"\n   CONDICIONES RECUPERADAS:")
                        print(f"   - Tipo: {type(condiciones_recuperadas)}")
                        if isinstance(condiciones_recuperadas, dict):
                            print(f"   - Moneda: {condiciones_recuperadas.get('moneda', 'NO ENCONTRADO')}")
                            print(f"   - Tiempo Entrega: {condiciones_recuperadas.get('tiempoEntrega', 'NO ENCONTRADO')}")
                            print(f"   - Entrega En: {condiciones_recuperadas.get('entregaEn', 'NO ENCONTRADO')}")
                            print(f"   - Términos: {condiciones_recuperadas.get('terminos', 'NO ENCONTRADO')}")
                            print(f"   - Comentarios: {condiciones_recuperadas.get('comentarios', 'NO ENCONTRADO')}")
                            print(f"   - Tipo Cambio: {condiciones_recuperadas.get('tipoCambio', 'NO ENCONTRADO')}")
                        else:
                            print(f"   - Condiciones RAW: {condiciones_recuperadas}")
                        
                        # Test del PDF si está disponible
                        if cotizacion.get('url'):
                            print(f"\n4. VERIFICANDO PDF...")
                            try:
                                pdf_response = requests.get(
                                    cotizacion.get('url'), 
                                    timeout=10
                                )
                                print(f"   PDF Status: HTTP {pdf_response.status_code}")
                                if pdf_response.status_code == 200:
                                    print(f"   PDF Size: {len(pdf_response.content)} bytes")
                                    print("   ✅ PDF ACCESIBLE - Revisar contenido manualmente")
                                else:
                                    print(f"   ❌ PDF no accesible")
                            except Exception as e:
                                print(f"   ❌ Error accediendo PDF: {e}")
                        
                    else:
                        print("   ❌ NO ENCONTRADA - No se guardó en base de datos")
                        
        else:
            print(f"❌ Error creando cotización: {response.status_code}")
            print(f"   Response: {response.text[:300]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print(f"\n" + "=" * 55)
    print("CONCLUSIONES:")
    print("1. Verifica si las condiciones se guardan correctamente en Supabase")
    print("2. Compara condiciones enviadas vs condiciones recuperadas")
    print("3. Si el PDF se genera, revisar manualmente si tiene USD o MXN")
    print("4. Si hay discrepancias, el problema está en el guardado o recuperación")
    print(f"   Busca en Supabase: {test_data['datosGenerales']['cliente']}")
    print("=" * 55)

if __name__ == "__main__":
    debug_condiciones_usd()