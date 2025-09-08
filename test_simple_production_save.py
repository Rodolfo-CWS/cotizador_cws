#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Simple de Producción - Crear Cotización Nueva
================================================

Test más simple para disparar el logging detallado y diagnosticar
el problema exacto con Supabase en producción.
"""

import requests
import json
from datetime import datetime

def test_simple_quotation():
    """Crear cotización simple para disparar logging detallado"""
    
    print("TESTING SIMPLE QUOTATION CREATION IN PRODUCTION")
    print("=" * 50)
    
    # URL de producción
    base_url = "https://cotizador-cws.onrender.com"
    
    # Datos mínimos para cotización nueva
    quotation_data = {
        "cliente": "TEST-LOGGING",
        "vendedor": "DEBUG",
        "proyecto": "DIAGNOSTICO-SUPABASE",
        "items": json.dumps([{
            "descripcion": "Test item logging",
            "cantidad": 1,
            "precio_unitario": 100
        }]),
        "condiciones": json.dumps({
            "moneda": "MXN"
        }),
        "observaciones": "Test logging detallado produccion"
    }
    
    print(f"Cliente: {quotation_data['cliente']}")
    print(f"Vendedor: {quotation_data['vendedor']}")
    print(f"Proyecto: {quotation_data['proyecto']}")
    
    try:
        print("\nEnviando POST a /formulario...")
        response = requests.post(
            f"{base_url}/formulario",
            data=quotation_data,
            timeout=30
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: Formulario procesado")
        else:
            print(f"ERROR HTTP {response.status_code}")
            
        # Mostrar fragmento de respuesta
        if response.text:
            preview = response.text[:200].replace('\n', ' ')
            print(f"Response preview: {preview}...")
            
    except Exception as e:
        print(f"ERROR: {e}")
        
    print("\n" + "=" * 50)
    print("LOGS DE RENDER DEBERIAN MOSTRAR:")
    print("- [HIBRIDO] Iniciando guardado hibrido")
    print("- [HIBRIDO] PostgreSQL fallo o SDK REST fallo") 
    print("- [OFFLINE] Guardando en JSON como fallback")
    print("=" * 50)

if __name__ == "__main__":
    test_simple_quotation()