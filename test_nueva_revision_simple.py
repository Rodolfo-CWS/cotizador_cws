#!/usr/bin/env python3
"""
Test simple para verificar que el boton Nueva Revision funciona
"""

import os
import sys

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_button_visibility():
    """Test simple para verificar que el boton es visible"""
    print("TEST: VISIBILIDAD DEL BOTON NUEVA REVISION")
    print("=" * 50)
    
    try:
        from supabase_manager import SupabaseManager
        
        # Inicializar manager
        db = SupabaseManager()
        print(f"Modo offline: {db.modo_offline}")
        
        # Buscar cotizaciones
        resultado = db.buscar_cotizaciones("", 1, 3)
        
        if resultado.get("error"):
            print(f"ERROR: {resultado['error']}")
            return False
        
        cotizaciones = resultado.get("resultados", [])
        print(f"Encontradas {len(cotizaciones)} cotizaciones")
        
        for i, cot in enumerate(cotizaciones):
            numero = cot.get('numeroCotizacion', 'N/A')
            _id = cot.get('_id', 'N/A')
            
            # Simular la logica del template
            revision_id = cot.get('numeroCotizacion') or cot.get('numero_cotizacion') or cot.get('_id')
            boton_visible = bool(revision_id)
            
            print(f"\nCotizacion {i+1}:")
            print(f"  Numero: {numero}")
            print(f"  ID: {_id}")
            print(f"  Boton visible: {'SI' if boton_visible else 'NO'}")
            if boton_visible:
                print(f"  URL: /formulario?revision={revision_id}")
                print(f"  Link directo: /desglose/{revision_id}")
        
        return len([c for c in cotizaciones if c.get('numeroCotizacion')]) > 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Funcion principal"""
    exito = test_button_visibility()
    
    print("\n" + "=" * 50)
    if exito:
        print("RESULTADO: Boton Nueva Revision deberia estar VISIBLE")
        print("\nPara probar:")
        print("1. Ejecutar: python app.py")  
        print("2. Abrir: http://localhost:5000")
        print("3. Buscar cualquier cotizacion")
        print("4. Hacer clic en 'Desglose'")
        print("5. Buscar el boton verde 'Nueva Revision'")
    else:
        print("RESULTADO: Problema detectado con el boton")
    
    return exito

if __name__ == "__main__":
    main()