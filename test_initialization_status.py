#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Estado de Inicialización - Verificar Por Qué Está en Modo Offline
====================================================================
"""

import requests
import json

def test_initialization_status():
    """Test para ver el estado de inicialización del sistema"""
    
    print("TESTING SYSTEM INITIALIZATION STATUS")
    print("=" * 45)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Test 1: Verificar endpoint de info/debug
    endpoints_to_test = [
        "/info", 
        "/debug",
        "/diagnosticos",
        "/admin/sistema/diagnostico",
        "/sistema/estado"
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\nTesting {endpoint}...")
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            print(f"  HTTP {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Look for Supabase/database info
                    if 'supabase' in str(data).lower():
                        print("  ✓ Contains Supabase info:")
                        supabase_info = str(data)[:300]
                        print(f"    {supabase_info}...")
                        
                    if 'offline' in str(data).lower():
                        print("  ⚠ Contains offline info")
                        
                except:
                    print(f"  Response (not JSON): {response.text[:100]}...")
                    
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test 2: Crear cotización simple y ver logs detallados
    print(f"\n" + "=" * 45)
    print("CREATING TEST QUOTATION TO TRIGGER DETAILED LOGS")
    print("=" * 45)
    
    test_data = {
        "datosGenerales": {
            "cliente": "INIT-STATUS-TEST",
            "vendedor": "INIT-DEBUG", 
            "proyecto": "INITIALIZATION-TEST"
        },
        "items": [{
            "descripcion": "Test initialization status", 
            "cantidad": 1,
            "precio_unitario": 77.77
        }],
        "condiciones": {"moneda": "MXN"},
        "observaciones": "Test para ver logs de inicialización detallados"
    }
    
    try:
        response = requests.post(
            f"{base_url}/formulario",
            json=test_data,
            timeout=30
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            print(f"Número: {result.get('numeroCotizacion')}")
            
        else:
            print(f"Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"\n" + "=" * 45)
    print("INSTRUCCIONES PARA ANÁLISIS:")
    print("En los logs de Render deberías ver:")
    print("1. [SUPABASE] Inicializando conexion...")
    print("2. [SUPABASE] Variables disponibles:")
    print("3. Estado de cada variable (Configurada/Faltante)")
    print("4. Si faltan variables → modo offline")
    print("5. Si variables OK pero conexión falla → logs de error")
    print("=" * 45)

if __name__ == "__main__":
    test_initialization_status()