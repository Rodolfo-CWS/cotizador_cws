#!/usr/bin/env python3
"""
Test simple sin Unicode para verificar producción
"""

import requests
import json

def test_production():
    """Test simple de producción"""
    print("TESTING PRODUCTION SITE")
    print("=" * 50)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    try:
        # 1. Test básico de conectividad
        print("1. Testing basic connectivity...")
        response = requests.get(base_url, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ERROR: Site not accessible")
            return False
            
        print("   SUCCESS: Site is accessible")
        
        # 2. Test de creación de PDF
        print("\n2. Testing PDF generation...")
        test_data = {
            "datosGenerales": {
                "cliente": "CLIENTE-TEST-PDF",
                "vendedor": "TT",
                "proyecto": "TEST-DEPLOY",
                "revision": "1"
            },
            "items": [{
                "descripcion": "Test item for PDF",
                "cantidad": 1,
                "total": 500.00,
                "uom": "PZA"
            }],
            "condiciones": {
                "moneda": "MXN",
                "tiempoEntrega": "5 dias",
                "entregaEn": "Test site",
                "terminos": "Test payment terms"
            }
        }
        
        pdf_response = requests.post(
            f"{base_url}/formulario",
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"   PDF Response Status: {pdf_response.status_code}")
        
        if pdf_response.status_code == 200:
            result = pdf_response.json()
            print("   SUCCESS: Quotation created")
            print(f"   Number: {result.get('numeroCotizacion', 'N/A')}")
            
            pdf_generated = result.get('pdf_generado', False)
            print(f"   PDF Generated: {pdf_generated}")
            
            if pdf_generated:
                print("   SUCCESS: PDF generation working!")
                return True
            else:
                pdf_error = result.get('pdf_error', 'Unknown error')
                print(f"   ERROR: PDF generation failed - {pdf_error}")
                return False
                
        else:
            print(f"   ERROR: Request failed")
            try:
                error_data = pdf_response.json()
                print(f"   Error details: {error_data}")
            except:
                print(f"   Raw response: {pdf_response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   EXCEPTION: {e}")
        return False

def check_environment_variables():
    """Verificar variables de entorno via API"""
    print("\n3. Checking environment variables...")
    
    try:
        response = requests.get("https://cotizador-cws.onrender.com/env-check", timeout=10)
        if response.status_code == 200:
            env_data = response.json()
            
            cloudinary_configured = all([
                env_data.get('cloudinary_cloud_name'),
                env_data.get('cloudinary_api_key'),
                env_data.get('cloudinary_api_secret_configured')
            ])
            
            print(f"   Cloudinary configured: {cloudinary_configured}")
            print(f"   MongoDB configured: {env_data.get('mongodb_configurado', False)}")
            print(f"   Environment: {env_data.get('environment', 'unknown')}")
            
            return cloudinary_configured
        else:
            print(f"   ERROR: Cannot check environment - {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Starting production test...")
    
    # Test conectividad y PDF
    pdf_working = test_production()
    
    # Test variables de entorno
    env_ok = check_environment_variables()
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS")
    print("=" * 50)
    
    print(f"PDF Generation: {'WORKING' if pdf_working else 'FAILING'}")
    print(f"Environment: {'OK' if env_ok else 'NEEDS_ATTENTION'}")
    
    if not pdf_working:
        print("\nTROUBLESHOOTING STEPS:")
        print("1. Check Render dashboard for deployment errors")
        print("2. Verify environment variables are set correctly")
        print("3. Check application logs in Render")
        print("4. Try manual redeploy")
    else:
        print("\nSUCCESS: Deployment is working correctly!")