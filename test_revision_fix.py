#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico para validar las correcciones del sistema de revisiones
Verifica que no se produzcan más errores HTTP 500
"""

import requests
import json
import time
from datetime import datetime

def test_revision_endpoints():
    """Prueba los nuevos endpoints de debug y el sistema mejorado"""
    
    BASE_URL = "http://localhost:5000"  # Cambiar a production si es necesario
    
    print("🧪 TEST SISTEMA DE REVISIONES - POST FIX")
    print("=" * 50)
    
    # 1. Test del endpoint de debug
    print("\n1. 🔍 Testing endpoint de debug...")
    try:
        response = requests.get(f"{BASE_URL}/debug-revision/DAIKIN-CWS-RM-001-R1-COMPUTADOR", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Debug endpoint funcional")
            print(f"   Cotización existe: {data.get('analisis', {}).get('cotizacion_existe', False)}")
            if data.get('analisis', {}).get('cotizacion_existe'):
                revision_info = data.get('analisis', {}).get('datos_cotizacion', {})
                print(f"   Revisión actual: {revision_info.get('revision_actual', 'N/A')}")
                print(f"   Cliente: {revision_info.get('cliente', 'N/A')}")
        else:
            print(f"   ❌ Error en debug endpoint: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Excepción en debug: {e}")
    
    # 2. Test de formulario con datos de revisión válidos
    print("\n2. 📝 Testing formulario con revisión válida...")
    try:
        datos_revision = {
            "datosGenerales": {
                "numeroCotizacion": "DAIKIN-CWS-RM-002-R2-COMPUTADOR", 
                "cliente": "DAIKIN TEST",
                "vendedor": "RM",
                "proyecto": "COMPUTADOR",
                "revision": "2",
                "actualizacionRevision": "Esta es una justificación de prueba para la revisión R2 que cumple con el mínimo de 10 caracteres requeridos.",
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "atencionA": "Ing. Prueba",
                "contacto": "test@example.com"
            },
            "condiciones": {
                "moneda": "MXN",
                "tipoCambio": "20.00",
                "tiempoEntrega": "15 días",
                "entregaEn": "SLP",
                "terminos": "pago inmediato",
                "comentarios": "Cotización de prueba"
            },
            "items": [
                {
                    "descripcion": "Item de prueba",
                    "cantidad": 1,
                    "precioUnitario": 1000.00
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/test-revision-form", 
                               json=datos_revision, 
                               headers={'Content-Type': 'application/json'},
                               timeout=30)
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Test de formulario exitoso")
            validacion = data.get('validacion', {})
            print(f"   Revisión detectada: {validacion.get('revision_detectada', 'N/A')}")
            print(f"   Justificación válida: {validacion.get('justificacion', {}).get('valida', False)}")
            
            guardado = data.get('guardado_simulado', {})
            print(f"   Guardado exitoso: {guardado.get('exitoso', False)}")
            if not guardado.get('exitoso'):
                print(f"   Error de guardado: {guardado.get('error', 'N/A')}")
                
        else:
            print(f"   ❌ Error en test: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error detalle: {error_data}")
            except:
                print(f"   Error text: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Excepción en test de formulario: {e}")
    
    # 3. Test de formulario con justificación insuficiente
    print("\n3. ❌ Testing validación de justificación insuficiente...")
    try:
        datos_invalidos = {
            "datosGenerales": {
                "numeroCotizacion": "TEST-CWS-XX-003-R2-PRUEBA", 
                "cliente": "TEST CLIENT",
                "vendedor": "XX",
                "proyecto": "PRUEBA",
                "revision": "2",
                "actualizacionRevision": "Corto",  # Muy corto - debería fallar
                "fecha": datetime.now().strftime("%Y-%m-%d")
            },
            "condiciones": {"moneda": "MXN"},
            "items": []
        }
        
        response = requests.post(f"{BASE_URL}/test-revision-form", 
                               json=datos_invalidos, 
                               headers={'Content-Type': 'application/json'},
                               timeout=10)
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print(f"   ✅ Validación funcionando correctamente (esperado 400)")
            try:
                error_data = response.json()
                error_msg = error_data.get('validacion', {}).get('error', 'N/A')
                print(f"   Mensaje de error: {error_msg}")
            except:
                pass
        else:
            print(f"   ❌ Validación no funcionó correctamente (esperado 400, recibido {response.status_code})")
            
    except Exception as e:
        print(f"   ❌ Excepción en test de validación: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 TEST COMPLETADO")
    print("\n📋 RESUMEN:")
    print("- Se agregó logging detallado para revisiones")
    print("- Se crearon endpoints de debug temporal")
    print("- Se mejoró validación y error handling")
    print("- Se aisló generación de PDF del guardado crítico")
    print("\n🔧 ENDPOINTS DE DEBUG DISPONIBLES:")
    print("- GET /debug-revision/<numero_cotizacion>")
    print("- POST /test-revision-form")
    print("\n⚠️  RECUERDA: Los endpoints de debug son temporales y deben")
    print("   ser removidos en producción después de resolver el problema.")

if __name__ == "__main__":
    test_revision_endpoints()