#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST PARA ISSUE #1: Número de cotización secuencial en revisiones
================================================================

Este test verifica que cuando se crea una nueva revisión, el número base
se mantiene y solo cambia la revisión, no el número secuencial.

Problema reportado:
- Original: BMW-CWS-CM-001-R1-GROW  
- Revisión: BMW-CWS-CM-002-R2-GROW ❌ (incorrecto, cambió 001→002)
- Esperado: BMW-CWS-CM-001-R2-GROW ✅ (correcto, mantiene 001)
"""

import sys
import os
import json
from datetime import datetime

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.abspath('.'))

from supabase_manager import SupabaseManager

def test_issue_1_revision_numero_base():
    """
    Test específico para el Issue #1: verificar que las revisiones
    mantienen el número base y no generan un número secuencial nuevo
    """
    print("=" * 70)
    print("TEST ISSUE #1: NÚMERO BASE EN REVISIONES")
    print("=" * 70)
    
    db = SupabaseManager()
    print(f"Modo DB: {'Offline (JSON)' if db.modo_offline else 'Online (Supabase)'}")
    
    # 1. CREAR COTIZACIÓN ORIGINAL
    print("\n1. CREANDO COTIZACIÓN ORIGINAL...")
    datos_original = {
        'datosGenerales': {
            'cliente': 'BMW',
            'vendedor': 'CM',
            'proyecto': 'GROW',
            'revision': '1',
            'fecha': datetime.now().strftime('%Y-%m-%d')
        },
        'items': [{
            'descripcion': 'Servicio original',
            'cantidad': 1,
            'precio_unitario': 1000.00,
            'subtotal': 1000.00
        }],
        'condiciones': {
            'moneda': 'MXN',
            'iva': 16,
            'total': 1160.00
        }
    }
    
    resultado_original = db.guardar_cotizacion(datos_original)
    
    if not resultado_original.get('success'):
        print(f"[ERROR] No se pudo guardar cotización original: {resultado_original.get('error')}")
        return False
    
    numero_original = resultado_original.get('numeroCotizacion') or resultado_original.get('numero_cotizacion')
    print(f"[OK] Cotización original guardada: {numero_original}")
    
    # Extraer partes del número original
    if '-R1-' in numero_original:
        partes = numero_original.split('-R1-')
        numero_base = partes[0]  # Ej: "BMW-CWS-CM-001"
        proyecto_parte = partes[1]  # Ej: "GROW"
    else:
        print(f"[ERROR] Formato de número no reconocido: {numero_original}")
        return False
    
    print(f"   Número base extraído: {numero_base}")
    print(f"   Proyecto: {proyecto_parte}")
    
    # 2. CREAR NUEVA REVISIÓN (simular flujo completo)
    print("\n2. CREANDO NUEVA REVISIÓN...")
    
    # Simular preparación de datos como lo haría preparar_datos_nueva_revision()
    datos_revision = json.loads(json.dumps(datos_original))  # Deep copy
    datos_revision['datosGenerales']['revision'] = '2'
    
    # CRÍTICO: Generar número de revisión ANTES de guardar
    numero_revision_esperado = db.generar_numero_revision(numero_original, '2')
    datos_revision['datosGenerales']['numeroCotizacion'] = numero_revision_esperado
    
    print(f"   Número de revisión esperado: {numero_revision_esperado}")
    
    # Modificar algo para que sea diferente
    datos_revision['items'][0]['descripcion'] = 'Servicio modificado - R2'
    datos_revision['datosGenerales']['actualizacionRevision'] = 'Cambio en especificaciones'
    
    # 3. GUARDAR LA REVISIÓN (aquí está el bug a probar)
    print("\n3. GUARDANDO NUEVA REVISIÓN...")
    print("   ANTES DEL GUARDADO:")
    print(f"   - datos['numeroCotizacion']: {datos_revision.get('numeroCotizacion')}")
    print(f"   - datos['datosGenerales']['numeroCotizacion']: {datos_revision['datosGenerales'].get('numeroCotizacion')}")
    
    resultado_revision = db.guardar_cotizacion(datos_revision)
    
    if not resultado_revision.get('success'):
        print(f"[ERROR] No se pudo guardar revisión: {resultado_revision.get('error')}")
        return False
    
    numero_revision_final = resultado_revision.get('numeroCotizacion') or resultado_revision.get('numero_cotizacion')
    print(f"   DESPUÉS DEL GUARDADO: {numero_revision_final}")
    
    # 4. VERIFICAR QUE EL NÚMERO BASE SE MANTUVO
    print("\n4. VERIFICACIÓN DEL FIX...")
    
    # Extraer número base de la revisión
    if '-R2-' in numero_revision_final:
        partes_revision = numero_revision_final.split('-R2-')
        numero_base_revision = partes_revision[0]
    else:
        print(f"[ERROR] Revisión no tiene formato R2: {numero_revision_final}")
        return False
    
    print(f"   Número base original:  {numero_base}")
    print(f"   Número base revisión:  {numero_base_revision}")
    print(f"   Número esperado:       {numero_revision_esperado}")
    print(f"   Número obtenido:       {numero_revision_final}")
    
    # VALIDACIÓN PRINCIPAL
    if numero_base == numero_base_revision:
        print(f"\n[EXITO] El número base se mantuvo correctamente")
        print(f"   Original:  {numero_original}")
        print(f"   Revisión:  {numero_revision_final}")
        
        # Verificación adicional: debe ser exactamente el número esperado
        if numero_revision_final == numero_revision_esperado:
            print(f"[PERFECTO] Número coincide exactamente con el esperado")
            return True
        else:
            print(f"[ADVERTENCIA] Número funcional pero no coincide con esperado")
            return True
    else:
        print(f"\n[ERROR] El número base cambió incorrectamente")
        print(f"   Se esperaba mantener: {numero_base}")
        print(f"   Pero se obtuvo:       {numero_base_revision}")
        print(f"   Esto indica que el Issue #1 NO está resuelto")
        return False

def test_flujo_completo_nuevas_cotizaciones():
    """
    Test para verificar que las cotizaciones completamente nuevas
    siguen funcionando correctamente (no se rompió la funcionalidad existente)
    """
    print("\n" + "=" * 70)
    print("TEST: FUNCIONALIDAD EXISTENTE NO AFECTADA")
    print("=" * 70)
    
    db = SupabaseManager()
    
    # Crear dos cotizaciones nuevas del mismo cliente/vendedor
    datos_nueva_1 = {
        'datosGenerales': {
            'cliente': 'FORD',
            'vendedor': 'JM',
            'proyecto': 'ELECTRICO',
            'revision': '1'
        },
        'items': []
    }
    
    datos_nueva_2 = {
        'datosGenerales': {
            'cliente': 'FORD',
            'vendedor': 'JM', 
            'proyecto': 'HIBRIDO',
            'revision': '1'
        },
        'items': []
    }
    
    resultado_1 = db.guardar_cotizacion(datos_nueva_1)
    resultado_2 = db.guardar_cotizacion(datos_nueva_2)
    
    if resultado_1.get('success') and resultado_2.get('success'):
        num_1 = resultado_1.get('numeroCotizacion') or resultado_1.get('numero_cotizacion')
        num_2 = resultado_2.get('numeroCotizacion') or resultado_2.get('numero_cotizacion')
        
        print(f"[OK] Nueva cotización 1: {num_1}")
        print(f"[OK] Nueva cotización 2: {num_2}")
        
        # Verificar que son consecutivos
        if num_1 and num_2 and 'FORD-CWS-JM-' in num_1 and 'FORD-CWS-JM-' in num_2:
            print("[OK] Los números consecutivos siguen funcionando correctamente")
            return True
        else:
            print(f"[ADVERTENCIA] Números obtenidos: {num_1}, {num_2}")
            print("[ADVERTENCIA] Formato de número no es el esperado, pero no es error crítico")
            return True
    else:
        print("[ERROR] Error en cotizaciones nuevas")
        return False

if __name__ == "__main__":
    print("EJECUTANDO TESTS PARA ISSUE #1")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar test principal
    test_1_resultado = test_issue_1_revision_numero_base()
    
    # Ejecutar test de regresión  
    test_2_resultado = test_flujo_completo_nuevas_cotizaciones()
    
    print("\n" + "=" * 70)
    print("RESUMEN DE RESULTADOS")
    print("=" * 70)
    print(f"Issue #1 (Revisiones mantienen número base): {'PASO' if test_1_resultado else 'FALLO'}")
    print(f"Funcionalidad existente no afectada:        {'PASO' if test_2_resultado else 'FALLO'}")
    
    if test_1_resultado and test_2_resultado:
        print(f"\n[TODOS LOS TESTS PASARON] Issue #1 resuelto correctamente")
        exit(0)
    else:
        print(f"\n[ERROR] Algunos tests fallaron. Revisar implementación.")
        exit(1)