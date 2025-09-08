#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG ISSUE #1: ANALIZAR PROBLEMA REVISIÓN R2
============================================
Simular exactamente lo que pasa cuando se carga una revisión
"""

from app import db_manager, preparar_datos_nueva_revision
import json

def debug_revision_completo():
    """Debug completo del Issue #1"""
    
    print("=" * 60)
    print("DEBUG ISSUE #1: REVISIÓN R2 PROBLEM")
    print("=" * 60)
    
    # Buscar la cotización que está causando problemas
    numero_buscar = "TEST-CORRE-CWS-TE-001-R1-PRUEBA-IMP"
    print(f"\n1. BUSCANDO COTIZACIÓN ORIGINAL: {numero_buscar}")
    
    resultado = db_manager.obtener_cotizacion(numero_buscar)
    
    if not resultado.get('encontrado'):
        print(f"   ❌ ERROR: No se encontró la cotización {numero_buscar}")
        print("   ✅ ESTO EXPLICA EL PROBLEMA - no puede crear R2 sin R1 base")
        
        # Buscar cotizaciones similares
        print(f"\n2. BUSCANDO COTIZACIONES SIMILARES:")
        todas = db_manager.listar_cotizaciones()
        
        if todas.get('success'):
            cotizaciones = todas.get('cotizaciones', [])
            print(f"   Total encontradas: {len(cotizaciones)}")
            
            for cot in cotizaciones:
                numero = cot.get('numeroCotizacion', 'N/A')
                if 'TEST-CORRE' in numero or 'PRUEBA-IMP' in numero:
                    print(f"   📋 Similar: {numero}")
                    
        return False
    
    print(f"   ✅ ENCONTRADA: {resultado['item'].get('numeroCotizacion', 'N/A')}")
    cotizacion_original = resultado['item']
    
    print(f"\n2. PREPARANDO DATOS NUEVA REVISIÓN:")
    datos_precargados = preparar_datos_nueva_revision(cotizacion_original)
    
    print(f"   Revisión original: {cotizacion_original.get('datosGenerales', {}).get('revision', 'N/A')}")
    print(f"   Nueva revisión: {datos_precargados.get('datosGenerales', {}).get('revision', 'N/A')}")
    print(f"   Número en datosGenerales: {datos_precargados.get('datosGenerales', {}).get('numeroCotizacion', 'VACIO')}")
    print(f"   Número en nivel raíz: {datos_precargados.get('numeroCotizacion', 'VACIO')}")
    
    print(f"\n3. SIMULANDO GUARDADO (como si viniera del formulario):")
    
    # Simular exactamente lo que llega del formulario
    datos_formulario = {
        'datosGenerales': datos_precargados.get('datosGenerales', {}),
        'items': datos_precargados.get('items', []),
        'numeroCotizacion': datos_precargados.get('numeroCotizacion'),  # ← Esto puede ser None
        'numeroCotizacionHidden': datos_precargados.get('numeroCotizacion')  # ← Y esto también
    }
    
    print(f"   datos_formulario['numeroCotizacion']: {datos_formulario.get('numeroCotizacion', 'VACIO')}")
    print(f"   datos_formulario['numeroCotizacionHidden']: {datos_formulario.get('numeroCotizacionHidden', 'VACIO')}")
    print(f"   datos_formulario['datosGenerales']['numeroCotizacion']: {datos_formulario.get('datosGenerales', {}).get('numeroCotizacion', 'VACIO')}")
    
    # Intentar guardado
    print(f"\n4. EJECUTANDO GUARDADO:")
    try:
        resultado_guardado = db_manager.guardar_cotizacion(datos_formulario)
        print(f"   Resultado: {json.dumps(resultado_guardado, indent=2)}")
        
        if not resultado_guardado.get('success'):
            print(f"   ❌ ERROR CONFIRMADO: {resultado_guardado.get('error', 'Sin error específico')}")
            return False
        else:
            print(f"   ✅ ÉXITO: Revisión guardada correctamente")
            return True
            
    except Exception as e:
        print(f"   💥 EXCEPCIÓN: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        exito = debug_revision_completo()
        
        print("\n" + "=" * 60)
        if exito:
            print("🎉 RESULTADO: Issue #1 resuelto")
        else:
            print("❌ RESULTADO: Issue #1 confirmado - necesita fix")
            print("\n💡 SIGUIENTE PASO: Verificar por qué no se encuentra la cotización base")
        print("=" * 60)
        
    except Exception as e:
        print(f"💥 ERROR EN DEBUG: {e}")
        import traceback
        traceback.print_exc()