#!/usr/bin/env python3
"""
Test directo para verificar si el fix del PDF está funcionando
"""

import requests
import json

def test_production_pdf():
    """Test el PDF en producción"""
    print("TESTING PDF GENERATION ON PRODUCTION")
    print("=" * 50)
    
    # URL de producción
    base_url = "https://cotizador-cws.onrender.com"
    
    # Datos de prueba simples
    test_data = {
        "datosGenerales": {
            "cliente": "CLIENTE-TEST",
            "vendedor": "TEST",
            "proyecto": "PDF-TEST",
            "revision": "1"
        },
        "items": [{
            "descripcion": "Item de prueba PDF",
            "cantidad": 1,
            "total": 100.00,
            "uom": "PZA"
        }],
        "condiciones": {
            "moneda": "USD",
            "tipoCambio": "18.50",
            "tiempoEntrega": "5 dias",
            "entregaEn": "Test location",
            "terminos": "Test terms"
        }
    }
    
    try:
        print("1. Enviando cotización de prueba...")
        response = requests.post(
            f"{base_url}/formulario",
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ COTIZACIÓN CREADA EXITOSAMENTE")
            print(f"Número: {result.get('numeroCotizacion', 'N/A')}")
            print(f"PDF: {result.get('pdf_generado', 'N/A')}")
            
            if result.get('pdf_generado'):
                print("✅ PDF SE GENERÓ SIN ERRORES")
                return True
            else:
                print("❌ PDF NO SE GENERÓ")
                print(f"Error PDF: {result.get('pdf_error', 'No especificado')}")
                return False
                
        else:
            print("❌ ERROR EN CREACIÓN DE COTIZACIÓN")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR EN REQUEST: {e}")
        return False

def check_deployment_status():
    """Verificar estado del deployment"""
    print("\nVERIFYING DEPLOYMENT STATUS")
    print("=" * 50)
    
    try:
        # Test básico de conectividad
        response = requests.get("https://cotizador-cws.onrender.com/", timeout=10)
        print(f"Site status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Site is accessible")
            
            # Verificar si hay endpoint de salud
            try:
                health_response = requests.get("https://cotizador-cws.onrender.com/env-check", timeout=10)
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    print(f"App version info: {health_data.get('app_info', 'N/A')}")
                    print(f"Python version: {health_data.get('python_version', 'N/A')}")
                    print(f"Environment: {health_data.get('environment', 'N/A')}")
                else:
                    print("Health check not available")
            except:
                print("Health check endpoint not accessible")
                
        else:
            print(f"❌ Site not accessible: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    try:
        # Verificar estado del deployment
        check_deployment_status()
        
        # Test de generación de PDF
        pdf_success = test_production_pdf()
        
        print("\n" + "=" * 50)
        print("RESULTADO FINAL")
        print("=" * 50)
        
        if pdf_success:
            print("✅ DEPLOYMENT EXITOSO - PDF FUNCIONANDO")
        else:
            print("❌ DEPLOYMENT TIENE PROBLEMAS - PDF FALLANDO")
            print("\nRECOMENDACIONES:")
            print("1. Verificar logs en Render Dashboard")
            print("2. Verificar variables de entorno")
            print("3. Considerar redeploy manual")
            
    except KeyboardInterrupt:
        print("\nTest interrumpido por usuario")
    except Exception as e:
        print(f"\nError crítico en test: {e}")