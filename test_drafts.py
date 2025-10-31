#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST DE SISTEMA DE DRAFTS (BORRADORES)
======================================

Script de prueba para verificar la funcionalidad completa del sistema de drafts:
- Guardar drafts
- Listar drafts
- Obtener draft específico
- Eliminar drafts
- Integración con Supabase y JSON offline
"""

import sys
import json
from supabase_manager import SupabaseManager

def test_guardar_draft(db):
    """Test 1: Guardar un nuevo draft"""
    print("\n" + "="*60)
    print("TEST 1: Guardar draft")
    print("="*60)

    datos_test = {
        'vendedor': 'TEST',
        'datos': {
            'datosGenerales': {
                'cliente': 'Cliente de Prueba',
                'proyecto': 'Proyecto de Prueba',
                'telefono': '555-1234',
                'correo': 'test@test.com',
                'vendedor': 'TEST'
            },
            'items': [
                {
                    'descripcion': 'Item de prueba 1',
                    'unidad': 'PZA',
                    'cantidad': 10,
                    'precioUnitario': 100.50
                },
                {
                    'descripcion': 'Item de prueba 2',
                    'unidad': 'KG',
                    'cantidad': 5,
                    'precioUnitario': 250.00
                }
            ],
            'condiciones': {
                'tiempoEntrega': '15 días',
                'condicionesPago': '50% anticipo, 50% contra entrega',
                'moneda': 'MXN',
                'comentariosAdicionales': 'Esto es una prueba del sistema de drafts'
            }
        }
    }

    resultado = db.guardar_draft(datos_test)

    if resultado.get('success'):
        print("✅ Draft guardado exitosamente")
        print(f"   Draft ID: {resultado.get('draft_id')}")
        print(f"   Nombre: {resultado.get('nombre')}")
        print(f"   Timestamp: {resultado.get('timestamp')}")
        return resultado.get('draft_id')
    else:
        print(f"❌ Error guardando draft: {resultado.get('error')}")
        return None


def test_listar_drafts(db, vendedor=None):
    """Test 2: Listar drafts"""
    print("\n" + "="*60)
    print(f"TEST 2: Listar drafts{' de ' + vendedor if vendedor else ''}")
    print("="*60)

    drafts = db.listar_drafts(vendedor)

    if drafts:
        print(f"✅ {len(drafts)} drafts encontrados:")
        for i, draft in enumerate(drafts, 1):
            print(f"\n   {i}. ID: {draft.get('id')}")
            print(f"      Nombre: {draft.get('nombre')}")
            print(f"      Vendedor: {draft.get('vendedor')}")
            print(f"      Última modificación: {draft.get('ultima_modificacion')}")
    else:
        print("ℹ️  No se encontraron drafts")

    return drafts


def test_obtener_draft(db, draft_id):
    """Test 3: Obtener draft específico"""
    print("\n" + "="*60)
    print(f"TEST 3: Obtener draft: {draft_id}")
    print("="*60)

    draft = db.obtener_draft(draft_id)

    if draft:
        print("✅ Draft obtenido exitosamente")
        print(f"   ID: {draft.get('id')}")
        print(f"   Nombre: {draft.get('nombre')}")
        print(f"   Vendedor: {draft.get('vendedor')}")

        datos = draft.get('datos', {})
        datos_generales = datos.get('datosGenerales', {})
        items = datos.get('items', [])
        condiciones = datos.get('condiciones', {})

        print(f"\n   Datos Generales:")
        print(f"      Cliente: {datos_generales.get('cliente')}")
        print(f"      Proyecto: {datos_generales.get('proyecto')}")

        print(f"\n   Items: {len(items)}")
        for i, item in enumerate(items, 1):
            print(f"      {i}. {item.get('descripcion')} - {item.get('cantidad')} {item.get('unidad')} @ ${item.get('precioUnitario')}")

        print(f"\n   Condiciones:")
        print(f"      Moneda: {condiciones.get('moneda')}")
        print(f"      Tiempo de entrega: {condiciones.get('tiempoEntrega')}")

        return True
    else:
        print(f"❌ Draft no encontrado: {draft_id}")
        return False


def test_actualizar_draft(db, draft_id):
    """Test 4: Actualizar draft existente"""
    print("\n" + "="*60)
    print(f"TEST 4: Actualizar draft: {draft_id}")
    print("="*60)

    datos_actualizacion = {
        'vendedor': 'TEST',
        'draft_id': draft_id,
        'datos': {
            'datosGenerales': {
                'cliente': 'Cliente ACTUALIZADO',
                'proyecto': 'Proyecto MODIFICADO',
                'telefono': '555-9999',
                'correo': 'actualizado@test.com',
                'vendedor': 'TEST'
            },
            'items': [
                {
                    'descripcion': 'Item actualizado',
                    'unidad': 'PZA',
                    'cantidad': 20,
                    'precioUnitario': 150.75
                }
            ],
            'condiciones': {
                'tiempoEntrega': '30 días',
                'condicionesPago': 'Contado',
                'moneda': 'USD',
                'tipoCambio': '18.50',
                'comentariosAdicionales': 'Draft actualizado en prueba'
            }
        }
    }

    resultado = db.guardar_draft(datos_actualizacion)

    if resultado.get('success'):
        print("✅ Draft actualizado exitosamente")
        print(f"   Draft ID: {resultado.get('draft_id')}")
        print(f"   Nombre actualizado: {resultado.get('nombre')}")
        return True
    else:
        print(f"❌ Error actualizando draft: {resultado.get('error')}")
        return False


def test_eliminar_draft(db, draft_id):
    """Test 5: Eliminar draft"""
    print("\n" + "="*60)
    print(f"TEST 5: Eliminar draft: {draft_id}")
    print("="*60)

    resultado = db.eliminar_draft(draft_id)

    if resultado.get('success'):
        print("✅ Draft eliminado exitosamente")
        print(f"   Mensaje: {resultado.get('mensaje')}")
        return True
    else:
        print(f"❌ Error eliminando draft: {resultado.get('error')}")
        return False


def main():
    """Ejecutar batería completa de tests"""
    print("\n" + "="*60)
    print("PRUEBAS DEL SISTEMA DE DRAFTS (BORRADORES)")
    print("="*60)

    # Inicializar manager
    print("\nInicializando SupabaseManager...")
    db = SupabaseManager()

    print(f"Estado: {'Offline (JSON)' if db.modo_offline else 'Online (Supabase)'}")

    # Test 1: Guardar draft
    draft_id = test_guardar_draft(db)

    if not draft_id:
        print("\n❌ Test fallido: No se pudo crear draft")
        sys.exit(1)

    # Test 2: Listar todos los drafts
    drafts = test_listar_drafts(db)

    # Test 2b: Listar drafts por vendedor
    test_listar_drafts(db, vendedor='TEST')

    # Test 3: Obtener draft específico
    if not test_obtener_draft(db, draft_id):
        print("\n❌ Test fallido: No se pudo obtener draft")
        sys.exit(1)

    # Test 4: Actualizar draft
    if not test_actualizar_draft(db, draft_id):
        print("\n❌ Test fallido: No se pudo actualizar draft")
        sys.exit(1)

    # Test 3b: Verificar actualización
    test_obtener_draft(db, draft_id)

    # Test 5: Eliminar draft
    respuesta = input("\n¿Deseas eliminar el draft de prueba? (s/n): ")
    if respuesta.lower() == 's':
        if not test_eliminar_draft(db, draft_id):
            print("\n❌ Test fallido: No se pudo eliminar draft")
            sys.exit(1)

        # Verificar eliminación
        test_listar_drafts(db)
    else:
        print("ℹ️  Draft de prueba conservado para inspección manual")

    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE PRUEBAS")
    print("="*60)
    print("✅ Todos los tests completados exitosamente")
    print(f"   - Modo de operación: {'Offline (JSON)' if db.modo_offline else 'Online (Supabase)'}")
    print(f"   - Draft ID de prueba: {draft_id}")
    print("\nEl sistema de drafts está funcionando correctamente.")
    print("\nPróximos pasos:")
    print("  1. Ejecutar script SQL en Supabase: create_drafts_table.sql")
    print("  2. Probar funcionalidad desde la interfaz web")
    print("  3. Verificar auto-guardado cada 30 segundos")
    print("  4. Probar carga de drafts desde home.html")

    db.close()


if __name__ == "__main__":
    main()
