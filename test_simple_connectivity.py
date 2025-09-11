#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Simple Connectivity - Check if system is responding
========================================================
"""

import requests
from datetime import datetime

def test_connectivity():
    """Test basic connectivity"""
    
    print("TESTING BASIC CONNECTIVITY")
    print("=" * 30)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    try:
        print("Testing /info endpoint...")
        response = requests.get(f"{base_url}/info", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("System is responding!")
            return True
        else:
            print("System returned error")
            return False
            
    except requests.exceptions.Timeout:
        print("System timeout - may be restarting")
        return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def test_simple_form():
    """Test with very simple form data"""
    
    print("\nTesting simple quotation...")
    
    simple_data = {
        "datosGenerales": {
            "cliente": "SIMPLE-TEST",
            "vendedor": "TEST", 
            "proyecto": "CONNECTIVITY"
        },
        "items": [{
            "descripcion": "Simple test", 
            "cantidad": 1,
            "precio_unitario": 1.0
        }],
        "condiciones": {"moneda": "MXN"}
    }
    
    try:
        response = requests.post(
            "https://cotizador-cws.onrender.com/formulario",
            json=simple_data,
            timeout=15
        )
        
        print(f"HTTP Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            print(f"Number: {result.get('numeroCotizacion')}")
            print(f"PDF: {result.get('pdf_generado')}")
            return True
        else:
            print("Form processing failed")
            return False
            
    except requests.exceptions.Timeout:
        print("Form timeout - system may be processing")
        return False
    except Exception as e:
        print(f"Form error: {e}")
        return False

if __name__ == "__main__":
    if test_connectivity():
        test_simple_form()
    print("\nCheck Render Dashboard for deployment status")