#!/usr/bin/env python3
"""
Script para verificar el entorno y configuración de MongoDB
Útil para debugging en diferentes entornos (local vs Render)
"""

import os
import sys
from datetime import datetime
import json

def verificar_entorno():
    print("VERIFICACION DEL ENTORNO")
    print("=" * 50)
    
    # 1. Variables de entorno críticas
    print("\nVARIABLES DE ENTORNO:")
    env_vars = [
        'MONGO_USERNAME',
        'MONGO_PASSWORD', 
        'MONGO_CLUSTER',
        'MONGO_DATABASE',
        'FLASK_ENV',
        'SECRET_KEY',
        'PORT',
        'RENDER',
        'DYNO'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if var in ['MONGO_PASSWORD', 'SECRET_KEY']:
            # No mostrar valores sensibles completos
            display_value = f"[SET - {len(value) if value else 0} chars]" if value else "[NOT SET]"
        else:
            display_value = value or "[NOT SET]"
        print(f"   {var}: {display_value}")
    
    # 2. Detección de entorno
    print(f"\nENTORNO DETECTADO:")
    es_render = bool(os.getenv('RENDER'))
    es_heroku = bool(os.getenv('DYNO'))
    es_local = not (es_render or es_heroku)
    
    if es_render:
        print("   [RENDER] Entorno de produccion Render")
    elif es_heroku:
        print("   [HEROKU] Entorno de produccion Heroku")
    else:
        print("   [LOCAL] Entorno de desarrollo local")
    
    # 3. Prueba de MongoDB
    print(f"\nPRUEBA DE MONGODB:")
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        
        print(f"   Modo offline: {db.modo_offline}")
        if not db.modo_offline:
            print("   [OK] Conexion MongoDB exitosa")
            
            # Contar documentos
            total = db.collection.count_documents({})
            print(f"   [DATA] Total cotizaciones: {total}")
            
            # Última cotización
            ultimas = list(db.collection.find().sort("timestamp", -1).limit(1))
            if ultimas:
                ultima = ultimas[0]
                numero = ultima.get('numeroCotizacion', 'Sin numero')
                fecha = ultima.get('fechaCreacion', 'Sin fecha')
                print(f"   [LAST] Ultima cotizacion: {numero} ({fecha[:19] if fecha else 'N/A'})")
        else:
            print("   [OFFLINE] MongoDB en modo offline")
        
        db.cerrar_conexion()
        
    except Exception as e:
        print(f"   [ERROR] Error conectando MongoDB: {e}")
    
    # 4. Prueba de guardado
    print(f"\nPRUEBA DE GUARDADO:")
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        
        datos_test = {
            'datosGenerales': {
                'cliente': f'Test Entorno {datetime.now().strftime("%H%M%S")}',
                'vendedor': 'Test Verificacion',
                'proyecto': 'Diagnostico',
                'revision': '1'
            },
            'items': [{'descripcion': 'Test guardado', 'cantidad': 1, 'total': 1}],
            'condiciones': {'moneda': 'USD'}
        }
        
        resultado = db.guardar_cotizacion(datos_test)
        
        if resultado.get('success'):
            numero = resultado.get('numeroCotizacion')
            print(f"   [OK] Guardado exitoso: {numero}")
            
            # Verificar que se puede recuperar
            verificacion = db.obtener_cotizacion(numero)
            if verificacion.get('encontrado'):
                print(f"   [OK] Verificacion exitosa: cotizacion recuperada")
            else:
                print(f"   [WARN] Guardo pero no se pudo recuperar")
        else:
            print(f"   [ERROR] Error guardando: {resultado.get('error')}")
        
        db.cerrar_conexion()
        
    except Exception as e:
        print(f"   [ERROR] Error en prueba de guardado: {e}")

if __name__ == "__main__":
    verificar_entorno()