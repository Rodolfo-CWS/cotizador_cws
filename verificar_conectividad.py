#!/usr/bin/env python3
"""
Script para verificar problemas de conectividad con MongoDB Atlas y Google Drive
"""

import requests
import json

def verificar_conectividad():
    print("="*80)
    print("VERIFICACIÓN DE CONECTIVIDAD DE SERVICIOS")
    print("="*80)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # 1. Verificar estado general del sistema
    print("\n1. Verificando estado del sistema...")
    try:
        response = requests.get(f"{base_url}/debug/estado", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   MongoDB: {data.get('mongodb', 'N/A')}")
            print(f"   Google Drive: {data.get('google_drive', 'N/A')}")
            print(f"   Modo: {data.get('modo', 'N/A')}")
        else:
            print(f"   Error: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Verificar variables de entorno críticas
    print("\n2. Verificando configuración...")
    try:
        response = requests.get(f"{base_url}/debug/config", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   MONGODB_URI configurado: {'Sí' if data.get('mongodb_uri_set') else 'No'}")
            print(f"   GOOGLE_CREDENTIALS configurado: {'Sí' if data.get('google_creds_set') else 'No'}")
        else:
            print(f"   Error: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Test específico de búsqueda problemática
    print("\n3. Replicando problema específico...")
    
    scenarios = [
        ("Búsqueda directa por nombre", "/buscar_pdfs", "MONGO-CWS-CM-001-R1-BOBOX"),
        ("Búsqueda por vendedor", "/buscar", "Carlos Martinez")
    ]
    
    for nombre, endpoint, query in scenarios:
        print(f"\n   {nombre}:")
        try:
            response = requests.post(
                f"{base_url}{endpoint}",
                json={"query": query},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                modo = data.get('modo', 'N/A')
                print(f"     Resultados: {total}")
                print(f"     Modo: {modo}")
                
                if total > 0:
                    print("     [OK] Cotización encontrada")
                else:
                    print("     [PROBLEMA] Cotización NO encontrada")
            else:
                print(f"     [ERROR] Status: {response.status_code}")
                
        except Exception as e:
            print(f"     [ERROR] {e}")
    
    print(f"\n{'='*80}")
    print("DIAGNÓSTICO Y RECOMENDACIONES")
    print(f"{'='*80}")
    print("""
PROBLEMA IDENTIFICADO:
- El sistema está operando en MODO OFFLINE
- MongoDB Atlas no está conectado
- Google Drive tampoco responde correctamente
- Esto causa inconsistencias entre tipos de búsqueda

CAUSAS POSIBLES:
1. Variables de entorno mal configuradas en Render
2. Problemas de red/firewall
3. Credenciales expiradas o incorrectas
4. Límites de cuota de servicios excedidos

ACCIONES RECOMENDADAS:
1. Verificar variables de entorno en Render:
   - MONGODB_URI (debe ser la URI completa de Atlas)
   - GOOGLE_APPLICATION_CREDENTIALS_JSON
   
2. Revisar logs del servidor en tiempo real:
   - https://dashboard.render.com -> Ver logs
   
3. Verificar estado de MongoDB Atlas:
   - Dashboard de Atlas -> Network Access
   - Verificar que 0.0.0.0/0 esté permitido
   
4. Probar conexión manual desde línea de comandos

SOLUCIÓN TEMPORAL:
- Implementar fallback automático mejorado en frontend
- Asegurar que todas las búsquedas usen el mismo origen de datos
    """)

if __name__ == "__main__":
    verificar_conectividad()