#!/usr/bin/env python3
"""
Script para verificar que el servidor Flask está respondiendo
"""
import requests
import json

def test_servidor():
    try:
        print("🔍 Verificando servidor Flask...")
        
        # Test básico
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        print(f"✅ Servidor responde - Status: {response.status_code}")
        
        # Test del formulario
        response = requests.get('http://127.0.0.1:5000/formulario', timeout=5)
        print(f"✅ Formulario disponible - Status: {response.status_code}")
        
        # Test de guardado simulado
        datos_test = {
            'datosGenerales': {
                'cliente': 'Test Cliente',
                'vendedor': 'Test Vendedor',
                'proyecto': 'Test Proyecto',
                'revision': '1'
            },
            'items': [{'descripcion': 'Test', 'cantidad': 1, 'total': 100}],
            'condiciones': {'moneda': 'USD'}
        }
        
        response = requests.post('http://127.0.0.1:5000/formulario', 
                               json=datos_test, timeout=10)
        print(f"✅ Endpoint guardado responde - Status: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            if resultado.get('success'):
                print(f"✅ Guardado funciona - Número: {resultado.get('numeroCotizacion')}")
            else:
                print(f"❌ Error en guardado: {resultado.get('error')}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ SERVIDOR NO ESTÁ CORRIENDO")
        print("   👉 Ejecuta: ARRANCAR_SERVIDOR.bat")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_servidor()