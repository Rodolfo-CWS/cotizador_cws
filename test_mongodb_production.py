#!/usr/bin/env python3
"""
Script para verificar que MongoDB funciona en producción después de actualizar la configuración SSL
"""

import requests
import time
import json

def test_mongodb_production():
    print("="*60)
    print("VERIFICACIÓN DE MONGODB EN PRODUCCIÓN")
    print("="*60)
    
    # Datos de prueba
    datos_test = {
        'datosGenerales': {
            'cliente': 'MONGODB SSL TEST',
            'vendedor': 'Production Test',
            'proyecto': 'SSL VERIFICATION',
            'atencionA': 'System Admin',
            'contacto': 'admin@test.com',
            'revision': '1'
        },
        'items': [
            {
                'descripcion': 'SSL Connection Test',
                'cantidad': '1',
                'uom': 'Test',
                'costoUnidad': '999.99',
                'total': '999.99'
            }
        ],
        'condiciones': {'moneda': 'MXN'}
    }
    
    print("1. Creando cotización de prueba...")
    
    try:
        response = requests.post(
            'https://cotizador-cws.onrender.com/formulario',
            json=datos_test,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            numero = data.get('numeroCotizacion')
            print(f"   ✅ Cotización creada: {numero}")
            
            print("\n2. Esperando 5 segundos...")
            time.sleep(5)
            
            print("3. Buscando cotización para verificar modo...")
            
            search_response = requests.post(
                'https://cotizador-cws.onrender.com/buscar_pdfs',
                json={'query': numero},
                headers={'Content-Type': 'application/json'},
                timeout=20
            )
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                modo = search_data.get('modo', 'unknown')
                total = search_data.get('total', 0)
                
                print(f"   Modo de operación: {modo}")
                print(f"   Cotizaciones encontradas: {total}")
                
                if modo == 'mongodb' or modo == 'online':
                    print("\n" + "="*60)
                    print("🎉 ¡ÉXITO! MONGODB FUNCIONANDO EN PRODUCCIÓN")
                    print("="*60)
                    print("✅ Las cotizaciones se están guardando en MongoDB")
                    print("✅ La configuración SSL fue exitosa")
                    print("✅ El sistema está completamente online")
                    
                elif modo == 'offline':
                    print("\n" + "="*60)
                    print("⚠️  TODAVÍA EN MODO OFFLINE")
                    print("="*60)
                    print("ℹ️  Posibles causas:")
                    print("   - La variable MONGODB_URI no se actualizó correctamente")
                    print("   - El deploy no se completó")
                    print("   - Se necesita reiniciar el servicio")
                    print("\n💡 Verifica en Render:")
                    print("   1. Environment Variables -> MONGODB_URI")
                    print("   2. Deploy Logs para ver errores")
                    
                else:
                    print(f"\n⚠️  Modo desconocido: {modo}")
                    
                # Mostrar información adicional
                if search_data.get('cotizaciones'):
                    cot = search_data['cotizaciones'][0]
                    print(f"\nℹ️  Detalles de la cotización encontrada:")
                    print(f"   Cliente: {cot.get('cliente', 'N/A')}")
                    print(f"   Número: {cot.get('numeroCotizacion', 'N/A')}")
                    
            else:
                print(f"   ❌ Error en búsqueda: {search_response.status_code}")
                print(f"   Response: {search_response.text[:200]}")
                
        else:
            print(f"   ❌ Error creando cotización: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        
    print(f"\n{'='*60}")

if __name__ == "__main__":
    test_mongodb_production()