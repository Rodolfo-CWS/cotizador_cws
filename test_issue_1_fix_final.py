#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST ESPECÍFICO PARA ISSUE #1 - FIX FINAL
==========================================

Problema Original:
- Cuando se genera una nueva revisión, el número se vuelve secuencial
- Ejemplo INCORRECTO: BMW-CWS-CM-001-R1-GROW → BMW-CWS-CM-002-R2-GROW
- Ejemplo CORRECTO: BMW-CWS-CM-001-R1-GROW → BMW-CWS-CM-001-R2-GROW

Fix Implementado:
- En guardar_cotizacion(), se previene la generación de números secuenciales para revisiones R2+
- Solo se permite generar números nuevos para cotizaciones R1 (nuevas)
- Revisiones que lleguen sin número base generan error crítico
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_manager import SupabaseManager

def test_issue_1_fix():
    """
    Test completo del Issue #1 - Verificar que revisiones mantienen número base
    """
    print("=== TEST ISSUE #1 FIX - REVISIONES MANTIENEN NÚMERO BASE ===")
    
    try:
        # 1. INICIALIZAR DATABASE MANAGER
        print("\n1. Inicializando SupabaseManager...")
        db = SupabaseManager()
        print(f"   Modo: {'Online (Supabase)' if not db.modo_offline else 'Offline (JSON)'}")
        
        # 2. CREAR COTIZACIÓN ORIGINAL (R1)
        print("\n2. CREANDO COTIZACIÓN ORIGINAL (R1)...")
        datos_original = {
            'datosGenerales': {
                'cliente': 'BMW-TEST',
                'vendedor': 'Carlos Martinez', 
                'proyecto': 'GROW-TEST',
                'revision': '1',
                'fecha': '2025-09-02'
            },
            'items': [
                {
                    'descripcion': 'Material de prueba',
                    'cantidad': 1,
                    'precio': 100.0,
                    'subtotal': 100.0
                }
            ],
            'condiciones': {
                'moneda': 'MXN',
                'tiempoEntrega': '5 días',
                'terminos': 'Contado'
            }
        }
        
        # Guardar cotización original
        resultado_original = db.guardar_cotizacion(datos_original)
        
        if resultado_original.get('success'):
            numero_original = resultado_original['numero_cotizacion']
            print(f"   [OK] Cotizacion original creada: {numero_original}")
            
            # Verificar que es R1
            if '-R1-' in numero_original:
                print(f"   [OK] Contiene R1 correctamente")
            else:
                print(f"   [ERROR] No contiene R1 - Formato: {numero_original}")
                return False
        else:
            print(f"   [ERROR] Error creando cotizacion original: {resultado_original}")
            return False
        
        # 3. SIMULAR PREPARACIÓN DE REVISIÓN (como lo hace app.py)
        print(f"\n3. SIMULANDO PREPARACIÓN DE REVISIÓN R2...")
        
        # Simular lo que hace preparar_datos_nueva_revision()
        datos_revision = json.loads(json.dumps(datos_original))  # Deep copy
        datos_revision['datosGenerales']['revision'] = '2'
        
        # CRÍTICO: Generar número de revisión ANTES de guardar (como debe ser)
        numero_revision_esperado = db.generar_numero_revision(numero_original, '2')
        datos_revision['datosGenerales']['numeroCotizacion'] = numero_revision_esperado
        datos_revision['numeroCotizacion'] = numero_revision_esperado  # También en nivel raíz
        
        print(f"   Número original: {numero_original}")
        print(f"   Número R2 esperado: {numero_revision_esperado}")
        print(f"   [OK] Numero preparado correctamente")
        
        # 4. GUARDAR REVISIÓN - AQUÍ ES DONDE ESTABA EL BUG
        print(f"\n4. GUARDANDO REVISIÓN (donde estaba el bug)...")
        
        resultado_revision = db.guardar_cotizacion(datos_revision)
        
        if resultado_revision.get('success'):
            numero_guardado = resultado_revision['numero_cotizacion']
            print(f"   Número guardado: {numero_guardado}")
            
            # VERIFICACIÓN CRÍTICA: ¿Se mantuvo el número base?
            if numero_guardado == numero_revision_esperado:
                print(f"   [SUCCESS] ISSUE #1 RESUELTO: Revision mantiene numero base")
                print(f"   [SUCCESS] Correcto: {numero_original} -> {numero_guardado}")
                
                # Verificar que mantiene la parte base (antes de -R)
                base_original = numero_original.split('-R')[0] 
                base_revision = numero_guardado.split('-R')[0]
                
                if base_original == base_revision:
                    print(f"   [SUCCESS] Base numerica preservada: {base_original}")
                    
                    # Verificar que cambió la revisión
                    if '-R2-' in numero_guardado:
                        print(f"   [SUCCESS] Revision actualizada correctamente a R2")
                        return True
                    else:
                        print(f"   [ERROR] Revision no se actualizo a R2")
                        return False
                else:
                    print(f"   [ERROR] Base numerica cambio: {base_original} -> {base_revision}")
                    return False
            else:
                print(f"   [ERROR] ISSUE #1 PERSISTE: Numero no coincide")
                print(f"   [ERROR] Esperado: {numero_revision_esperado}")
                print(f"   [ERROR] Obtenido: {numero_guardado}")
                return False
        else:
            print(f"   [ERROR] Error guardando revision: {resultado_revision}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scenario_critico_revision_sin_numero():
    """
    Test del escenario crítico: ¿Qué pasa si una revisión llega sin número?
    Esto NO debe ocurrir, pero el código debe manejarlo correctamente.
    """
    print("\n\n=== TEST ESCENARIO CRÍTICO: REVISIÓN SIN NÚMERO ===")
    
    try:
        db = SupabaseManager()
        
        # Simular datos de revisión SIN número (escenario de error)
        datos_revision_sin_numero = {
            'datosGenerales': {
                'cliente': 'CLIENTE-CRITICO',
                'vendedor': 'Test Vendor',
                'proyecto': 'PROYECTO-CRITICO', 
                'revision': '2',  # R2 pero SIN número base
                'fecha': '2025-09-02'
            },
            'items': []
        }
        
        print("   Intentando guardar revisión R2 SIN número base...")
        resultado = db.guardar_cotizacion(datos_revision_sin_numero)
        
        # Debe FALLAR con el error específico
        if not resultado.get('success') and 'Issue #1' in resultado.get('error', ''):
            print(f"   [SUCCESS] Error detectado correctamente: {resultado['error']}")
            print(f"   [SUCCESS] Sistema previene generacion incorrecta de numeros secuenciales")
            return True
        else:
            print(f"   [ERROR] Error no detectado - Resultado: {resultado}")
            print(f"   [ERROR] Sistema permitio generacion incorrecta")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error en test critico: {e}")
        return False

if __name__ == "__main__":
    print("INICIANDO TESTS ESPECÍFICOS PARA ISSUE #1 FIX")
    
    # Test 1: Flujo normal de revisión
    test1_ok = test_issue_1_fix()
    
    # Test 2: Escenario crítico
    test2_ok = test_scenario_critico_revision_sin_numero()
    
    # RESULTADO FINAL
    print(f"\n" + "="*60)
    print(f"RESULTADO FINAL DEL TEST ISSUE #1")
    print(f"="*60)
    print(f"Test 1 - Revisiones mantienen numero base: {'[PASO]' if test1_ok else '[FALLO]'}")
    print(f"Test 2 - Prevencion error critico: {'[PASO]' if test2_ok else '[FALLO]'}")
    
    if test1_ok and test2_ok:
        print(f"\n[EXITO] ISSUE #1 COMPLETAMENTE RESUELTO")
        print(f"   Las revisiones ahora mantienen correctamente el numero base")
        print(f"   El sistema previene la generacion incorrecta de numeros secuenciales")
    else:
        print(f"\n[ERROR] ISSUE #1 AUN REQUIERE ATENCION")
        if not test1_ok:
            print(f"   - Revisiones no mantienen numero base")
        if not test2_ok:
            print(f"   - Sistema no previene errores criticos")
            
    print(f"\nTest completado.")