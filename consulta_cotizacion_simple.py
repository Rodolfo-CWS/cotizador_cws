#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONSULTA SIMPLE DE COTIZACIÓN
============================

Script simplificado para consultar una cotización específica
y mostrar toda su información de forma detallada.
"""

import os
import sys
import json
from datetime import datetime

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from supabase_manager import SupabaseManager
except ImportError as e:
    print(f"Error importando SupabaseManager: {e}")
    sys.exit(1)

def mostrar_cotizacion_completa(numero_cotizacion: str):
    """Mostrar información completa de una cotización"""
    
    print("="*60)
    print(f"CONSULTA DE COTIZACION: {numero_cotizacion}")
    print("="*60)
    print(f"Fecha consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Inicializar manager
    try:
        db_manager = SupabaseManager()
        print(f"Modo de conexion: {'Online (Supabase)' if not db_manager.modo_offline else 'Offline (JSON)'}")
        print()
    except Exception as e:
        print(f"Error inicializando manager: {e}")
        return
    
    try:
        # Buscar cotización
        resultado = db_manager.obtener_cotizacion(numero_cotizacion)
        
        if not resultado.get('encontrado'):
            print("RESULTADO: COTIZACION NO ENCONTRADA")
            print(f"Error: {resultado.get('error', 'Desconocido')}")
            return
        
        cotizacion = resultado.get('item', {})
        
        print("RESULTADO: COTIZACION ENCONTRADA")
        print()
        
        # Información básica
        print("INFORMACION BASICA:")
        print(f"  Numero: {cotizacion.get('numeroCotizacion', 'N/A')}")
        print(f"  ID Base Datos: {cotizacion.get('_id', 'N/A')}")
        print(f"  Fecha Creacion: {cotizacion.get('fechaCreacion', 'N/A')}")
        print(f"  Timestamp: {cotizacion.get('timestamp', 'N/A')}")
        print(f"  Revision: {cotizacion.get('revision', 'N/A')}")
        print(f"  Usuario: {cotizacion.get('usuario', 'N/A')}")
        print()
        
        # Datos generales
        datos_generales = cotizacion.get('datosGenerales', {})
        print("DATOS GENERALES:")
        for key, value in datos_generales.items():
            print(f"  {key}: {value}")
        print()
        
        # Items
        items = cotizacion.get('items', [])
        print(f"ITEMS ({len(items)} elementos):")
        if items:
            for i, item in enumerate(items, 1):
                print(f"  [{i}] {item.get('descripcion', 'Sin descripcion')}")
                print(f"      Cantidad: {item.get('cantidad', 'N/A')}")
                print(f"      Precio Unit: {item.get('precioUnitario', 'N/A')}")
                print(f"      Total: {item.get('total', 'N/A')}")
                print()
        else:
            print("  (Sin items)")
            print()
        
        # Observaciones
        observaciones = cotizacion.get('observaciones')
        if observaciones:
            print("OBSERVACIONES:")
            print(f"  {observaciones}")
            print()
        
        # JSON completo (para debug)
        print("DATOS COMPLETOS (JSON):")
        print(json.dumps(cotizacion, indent=2, ensure_ascii=False, default=str))
        
    except Exception as e:
        print(f"Error consultando cotización: {e}")
        
    finally:
        try:
            db_manager.close()
        except:
            pass
    
    print("\n" + "="*60)
    print("CONSULTA COMPLETADA")
    print("="*60)

if __name__ == "__main__":
    # Cotización objetivo
    numero = "BMW-CWS-CM-001-R1-GROW"
    
    # Permitir pasar número como argumento
    if len(sys.argv) > 1:
        numero = sys.argv[1]
    
    mostrar_cotizacion_completa(numero)