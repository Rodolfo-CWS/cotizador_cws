#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force Initialization Logs - Forzar Logs de Inicialización
========================================================

Hacer múltiples requests para forzar que veamos los logs de inicialización
en Render, ya que sabemos que las variables están configuradas.
"""

import requests
import time
from datetime import datetime

def force_initialization_logs():
    """Forzar múltiples requests para ver logs de inicialización"""
    
    print("FORCING INITIALIZATION LOGS - MULTIPLE REQUESTS")
    print("=" * 50)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    print("Haciendo múltiples requests para forzar logs...")
    
    for i in range(3):
        print(f"\nRequest {i+1}/3 - {datetime.now().strftime('%H:%M:%S')}")
        
        # Test básico de conectividad
        try:
            response = requests.get(f"{base_url}/info", timeout=5)
            print(f"  /info: HTTP {response.status_code}")
        except Exception as e:
            print(f"  /info: Error {e}")
            
        # Test de cotización 
        test_data = {
            "datosGenerales": {
                "cliente": f"FORCE-INIT-{i+1}",
                "vendedor": "INIT-LOGS", 
                "proyecto": f"LOG-FORCE-{i+1}"
            },
            "items": [{
                "descripcion": f"Force init logs test {i+1}", 
                "cantidad": 1,
                "precio_unitario": 10.00 * (i+1)
            }],
            "condiciones": {"moneda": "MXN"},
            "observaciones": f"Forzar logs de inicialización - Request {i+1}"
        }
        
        try:
            response = requests.post(
                f"{base_url}/formulario",
                json=test_data,
                timeout=20
            )
            print(f"  Cotización: HTTP {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Número: {result.get('numeroCotizacion', 'N/A')}")
                print(f"  Success: {result.get('success', 'N/A')}")
            else:
                print(f"  Error: {response.text[:100]}")
        except Exception as e:
            print(f"  Cotización: Error {e}")
            
        # Esperar un poco entre requests
        if i < 2:
            print("  Esperando 3 segundos...")
            time.sleep(3)
    
    print(f"\n" + "=" * 50)
    print("COMPLETADO - REVISA LOGS DE RENDER AHORA")
    print("=" * 50)
    print("Deberías ver uno de estos escenarios:")
    print("")
    print("ESCENARIO 1 - Variables OK, conexión exitosa:")
    print("  [SUPABASE] Variables disponibles:")
    print("  [SUPABASE] Cliente Supabase inicializado")  
    print("  [SUPABASE] Conectado a PostgreSQL exitosamente")
    print("  [HIBRIDO] PRIORIDAD 1: Intentando SDK REST...")
    print("")
    print("ESCENARIO 2 - Variables OK, conexión falla:")
    print("  [SUPABASE] Variables disponibles:")
    print("  [SUPABASE] Error conectando: [mensaje de error]")
    print("  [SUPABASE] Activando modo offline")
    print("")
    print("ESCENARIO 3 - Sin logs de inicialización:")
    print("  Problema con la carga del módulo supabase_manager")
    print("=" * 50)

if __name__ == "__main__":
    force_initialization_logs()