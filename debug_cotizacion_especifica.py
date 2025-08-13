#!/usr/bin/env python3
"""
Script de debugging específico para investigar la cotización MONGO-CWS-CM-001-R1-BOBOX
"""

import requests
import json
import time

def debug_cotizacion_problematica():
    print("="*80)
    print("DEBUG: COTIZACIÓN MONGO-CWS-CM-001-R1-BOBOX")
    print("="*80)
    
    cotizacion_target = "MONGO-CWS-CM-001-R1-BOBOX"
    base_url = "https://cotizador-cws.onrender.com"
    
    # Scenarios de prueba
    scenarios = [
        {
            "name": "Búsqueda por nombre completo",
            "query": cotizacion_target,
            "endpoint": "/buscar_pdfs"
        },
        {
            "name": "Búsqueda por nombre parcial",
            "query": "MONGO-CWS-CM-001",
            "endpoint": "/buscar_pdfs"
        },
        {
            "name": "Búsqueda en cotizaciones (fallback)",
            "query": cotizacion_target,
            "endpoint": "/buscar"
        },
        {
            "name": "Búsqueda por vendedor CM",
            "query": "CM",
            "endpoint": "/buscar_pdfs"
        },
        {
            "name": "Búsqueda por vendedor CM (cotizaciones)",
            "query": "CM",
            "endpoint": "/buscar"
        }
    ]
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    resultados = {}
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 50)
        
        try:
            payload = {"query": scenario["query"]}
            
            response = requests.post(
                f"{base_url}{scenario['endpoint']}",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Información general
                total = data.get('total', 0)
                resultados_encontrados = data.get('resultados', [])
                modo = data.get('modo', 'N/A')
                
                print(f"   Total encontrados: {total}")
                print(f"   Modo: {modo}")
                print(f"   Resultados en respuesta: {len(resultados_encontrados)}")
                
                # Buscar específicamente nuestra cotización
                encontrado = False
                for resultado in resultados_encontrados:
                    # Verificar diferentes formas de identificar la cotización
                    numero_cot = (resultado.get('numero_cotizacion') or 
                                resultado.get('numeroCotizacion') or 
                                resultado.get('datosGenerales', {}).get('numeroCotizacion') or
                                str(resultado.get('_id', '')))
                    
                    if cotizacion_target.lower() in numero_cot.lower():
                        encontrado = True
                        print(f"   [OK] ENCONTRADA: {numero_cot}")
                        print(f"      Cliente: {resultado.get('cliente') or resultado.get('datosGenerales', {}).get('cliente', 'N/A')}")
                        print(f"      Vendedor: {resultado.get('vendedor') or resultado.get('datosGenerales', {}).get('vendedor', 'N/A')}")
                        print(f"      Tipo: {resultado.get('tipo', 'N/A')}")
                        print(f"      Tiene PDF: {'id' in resultado}")
                        print(f"      Tiene desglose: {resultado.get('tiene_desglose', False)}")
                        break
                
                if not encontrado and total > 0:
                    print(f"   [NO] No encontrada entre los {total} resultados")
                    # Mostrar algunos ejemplos
                    if resultados_encontrados:
                        print("   Ejemplos encontrados:")
                        for j, res in enumerate(resultados_encontrados[:3]):
                            numero = (res.get('numero_cotizacion') or 
                                    res.get('numeroCotizacion') or 
                                    str(res.get('_id', f'Item-{j}')))
                            print(f"     - {numero}")
                
                elif not encontrado:
                    print("   [NO] No se encontraron resultados")
                
                # Guardar resultado para análisis
                resultados[scenario['name']] = {
                    'total': total,
                    'encontrado': encontrado,
                    'modo': modo,
                    'resultados': len(resultados_encontrados)
                }
                
            else:
                print(f"   [ERROR] Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Error desconocido')}")
                except:
                    print(f"   Respuesta: {response.text[:100]}")
                    
        except requests.exceptions.Timeout:
            print("   [TIMEOUT] Timeout en la peticion")
            
        except Exception as e:
            print(f"   [ERROR] Error: {e}")
    
    # Resumen
    print(f"\n{'='*80}")
    print("RESUMEN DEL DEBUGGING")
    print(f"{'='*80}")
    
    for scenario, resultado in resultados.items():
        status = "[OK] ENCONTRADA" if resultado['encontrado'] else "[NO] NO ENCONTRADA"
        print(f"{scenario}: {status} (Total: {resultado['total']}, Modo: {resultado['modo']})")
    
    # Análisis de inconsistencias
    print(f"\n{'='*80}")
    print("ANALISIS DE INCONSISTENCIAS")
    print(f"{'='*80}")
    
    pdf_results = [r for name, r in resultados.items() if 'buscar_pdfs' in name]
    cot_results = [r for name, r in resultados.items() if 'buscar' in name and 'buscar_pdfs' not in name]
    
    if pdf_results and cot_results:
        pdf_encontrados = sum(1 for r in pdf_results if r['encontrado'])
        cot_encontrados = sum(1 for r in cot_results if r['encontrado'])
        
        if pdf_encontrados != cot_encontrados:
            print("[INCONSISTENCIA] DETECTADA:")
            print(f"   PDFs: {pdf_encontrados} encontrados")
            print(f"   Cotizaciones: {cot_encontrados} encontrados")
            print("   Esto explica por que los botones aparecen diferentes")
        else:
            print("[OK] Comportamiento consistente entre busquedas")
    
    print(f"\n{'='*80}")
    print("RECOMENDACIONES PARA DEBUGGING")
    print(f"{'='*80}")
    print("1. Verificar logs del servidor durante estas búsquedas")
    print("2. Revisar la base de datos MongoDB directamente")
    print("3. Verificar la sincronización entre Google Drive y MongoDB")
    print("4. Analizar el comportamiento del fallback en el frontend")

if __name__ == "__main__":
    debug_cotizacion_problematica()