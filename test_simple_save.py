#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple para verificar el proceso de guardado de cotizaciones
"""

from supabase_manager import SupabaseManager

def test_save_simple():
    """Test básico de guardado"""
    print("=== TEST GUARDADO SIMPLE ===")
    
    # Crear manager
    db = SupabaseManager()
    print(f"Modo offline: {db.modo_offline}")
    
    # Datos de prueba MÍNIMOS
    datos_test = {
        'datosGenerales': {
            'cliente': 'TEST-CLIENTE',
            'vendedor': 'TEST',
            'proyecto': 'PROYECTO-TEST'
        },
        'items': []
    }
    
    print(f"Datos a guardar: {datos_test}")
    
    try:
        # Intentar guardado
        print("\n--- INICIANDO GUARDADO ---")
        resultado = db.guardar_cotizacion(datos_test)
        print(f"Resultado completo: {resultado}")
        
        if resultado.get("success"):
            numero = resultado.get('numero_cotizacion') or resultado.get('numeroCotizacion')
            print(f"✅ ÉXITO - Número: {numero}")
        else:
            print(f"❌ FALLÓ - Error: {resultado.get('error')}")
            
    except Exception as e:
        print(f"💥 EXCEPCIÓN - {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_save_simple()