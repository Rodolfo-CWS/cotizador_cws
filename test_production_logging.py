#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de Logging Producción - Crear Revisión para Diagnosticar Supabase
====================================================================

Este script creará una revisión R2 de una cotización existente para
disparar el logging detallado en producción y diagnosticar el problema
exacto con la conexión a Supabase.
"""

import requests
import json
import time
from datetime import datetime

def test_production_revision():
    """Crear revisión R2 en producción para disparar logging detallado"""
    
    print("=" * 60)
    print("TESTING PRODUCTION REVISION CREATION WITH ENHANCED LOGGING")
    print("=" * 60)
    
    # URL de producción
    base_url = "https://cotizador-cws.onrender.com"
    
    # Datos para crear revisión R2 de cotización existente
    revision_data = {
        "numeroCotizacionBase": "CLIENTE-PR-CWS-TES-001-R1-VERIFICACION-SU",
        "datosGenerales": {
            "cliente": "CLIENTE-PRUEBA",
            "vendedor": "TEST", 
            "proyecto": "VERIFICACION-SUPABASE",
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "validez": "30 dias",
            "contacto": "test@ejemplo.com",
            "atencionA": "Usuario Test"
        },
        "items": [
            {
                "cantidad": 1,
                "descripcion": "Item de prueba REVISION R2",
                "precio_unitario": 150.0,
                "subtotal": 150.0
            }
        ],
        "condiciones": {
            "moneda": "MXN"
        },
        "observaciones": "REVISION R2 - TEST PARA DIAGNOSTICAR LOGGING PRODUCCION",
        "justificacionRevision": "Prueba de logging detallado para diagnosticar problema Supabase"
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Enviando revisión R2 a {base_url}/formulario...")
    print(f"Cotización base: {revision_data['numeroCotizacionBase']}")
    print(f"Justificación: {revision_data['justificacionRevision'][:50]}...")
    
    try:
        # Enviar POST a /formulario
        response = requests.post(
            f"{base_url}/formulario",
            data=revision_data,
            timeout=30,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Test-Production-Logging/1.0'
            }
        )
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            print("EXITO: FORMULARIO PROCESADO CORRECTAMENTE")
            print(f"Response headers: {dict(response.headers)}")
            
            # Verificar contenido de respuesta
            if "success" in response.text.lower() or "exito" in response.text.lower():
                print("EXITO: RESPUESTA INDICA EXITO")
            else:
                print("WARNING: RESPUESTA NO CLARA - REVISAR LOGS DE RENDER")
                
            # Mostrar fragmento de respuesta
            response_preview = response.text[:500] if response.text else "Sin contenido"
            print(f"Preview respuesta: {response_preview}...")
            
        else:
            print(f"ERROR HTTP {response.status_code}")
            print(f"Response: {response.text[:300]}...")
            
    except requests.exceptions.Timeout:
        print("WARNING: TIMEOUT - Operacion puede estar procesandose")
        print("   Revisar logs de Render para ver el logging detallado")
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR DE RED: {e}")
        
    print("\n" + "=" * 60)
    print("SIGUIENTE PASO: REVISAR LOGS DE RENDER")
    print("=" * 60)
    print("1. Ve a https://dashboard.render.com")
    print("2. Selecciona el servicio 'cotizador-cws'") 
    print("3. Ve a la pestaña 'Logs'")
    print("4. Busca líneas que contengan:")
    print("   - [HIBRIDO] PostgreSQL falló")
    print("   - [SDK_REST] INICIO")
    print("   - [SDK_REST] ERROR")
    print("   - [SDK_REST] EXITO")
    print("   - [OFFLINE] Guardando en JSON")
    print("\n5. El logging detallado revelará exactamente dónde falla")
    print("   y qué método de guardado realmente funciona en producción")
    
if __name__ == "__main__":
    test_production_revision()