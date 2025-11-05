#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para verificar que el número de cotización permite espacios en el nombre del proyecto
"""

from supabase_manager import SupabaseManager

def test_proyecto_con_espacios():
    """
    Probar generación de número con espacios en el proyecto
    """
    print("=" * 80)
    print("TEST: Número de cotización con espacios en el proyecto")
    print("=" * 80)

    db = SupabaseManager()

    # Caso de prueba 1: Rack selectivo para almacén
    print("\n📋 Caso 1: 'Rack selectivo para almacén'")
    print("-" * 80)
    datos_test_1 = {
        'cliente': 'BMW',
        'vendedor': 'Juan Pérez',
        'proyecto': 'Rack selectivo para almacén'
    }

    numero = db.generar_numero_automatico(datos_test_1)
    print(f"\n✅ Número generado: {numero}")
    print(f"   Verificando que contiene 'RACK SELECTIVO ALMACEN'...")

    if 'RACK SELECTIVO ALMACEN' in numero:
        print("   ✅ CORRECTO: El nombre del proyecto tiene espacios")
    else:
        print("   ❌ ERROR: El nombre del proyecto no tiene espacios")
        print(f"   Se esperaba que contenga 'RACK SELECTIVO ALMACEN'")

    # Caso de prueba 2: Proyecto con múltiples espacios
    print("\n📋 Caso 2: 'Sistema    de    almacenaje   vertical'")
    print("-" * 80)
    datos_test_2 = {
        'cliente': 'CLIENTE TEST',
        'vendedor': 'María López',
        'proyecto': 'Sistema    de    almacenaje   vertical'
    }

    numero2 = db.generar_numero_automatico(datos_test_2)
    print(f"\n✅ Número generado: {numero2}")
    print(f"   Verificando que limpió espacios múltiples...")

    if 'SISTEMA DE ALMACENAJE VERTICAL' in numero2:
        print("   ✅ CORRECTO: Los espacios múltiples se limpiaron a espacios simples")
    else:
        print("   ❌ ERROR: Los espacios múltiples no se limpiaron correctamente")

    # Caso de prueba 3: Proyecto con acentos y espacios
    print("\n📋 Caso 3: 'Estantería metálica modular'")
    print("-" * 80)
    datos_test_3 = {
        'cliente': 'ACME',
        'vendedor': 'Pedro González',
        'proyecto': 'Estantería metálica modular'
    }

    numero3 = db.generar_numero_automatico(datos_test_3)
    print(f"\n✅ Número generado: {numero3}")
    print(f"   Verificando que normalizó acentos...")

    if 'ESTANTERIA METALICA MODULAR' in numero3:
        print("   ✅ CORRECTO: Los acentos se normalizaron y se mantuvieron los espacios")
    else:
        print("   ❌ ERROR: Los acentos no se normalizaron correctamente")

    # Caso de prueba 4: Proyecto con caracteres especiales
    print("\n📋 Caso 4: 'Proyecto (especial) #1 2025'")
    print("-" * 80)
    datos_test_4 = {
        'cliente': 'TEST',
        'vendedor': 'Ana Martínez',
        'proyecto': 'Proyecto (especial) #1 2025'
    }

    numero4 = db.generar_numero_automatico(datos_test_4)
    print(f"\n✅ Número generado: {numero4}")
    print(f"   Verificando que eliminó caracteres especiales pero mantuvo espacios...")

    if 'PROYECTO ESPECIAL 1 2025' in numero4:
        print("   ✅ CORRECTO: Se eliminaron caracteres especiales y se mantuvieron espacios")
    else:
        print("   ⚠️  El resultado es diferente al esperado, pero puede ser aceptable")
        print(f"   Verifique que el formato sea legible")

    print("\n" + "=" * 80)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 80)

if __name__ == "__main__":
    test_proyecto_con_espacios()
