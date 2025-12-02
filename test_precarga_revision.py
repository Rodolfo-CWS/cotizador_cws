#!/usr/bin/env python3
"""
Test para diagnosticar el problema de precarga de cantidad y UOM en revisiones
"""

import json

# Leer archivo JSON
with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Buscar una cotización con items completos
print("=" * 80)
print("DIAGNÓSTICO DE PRECARGA DE REVISIONES")
print("=" * 80)

cotizaciones = data.get('cotizaciones', [])

if cotizaciones:
    # Tomar la primera cotización con items que tenga UOM
    for cot in cotizaciones:
        items = cot.get('items', [])
        if items and len(items) > 0:
            item = items[0]
            if 'uom' in item and 'cantidad' in item:
                print(f"\n✅ Cotización encontrada: {cot.get('numeroCotizacion', 'N/A')}")
                print(f"   Cliente: {cot.get('datosGenerales', {}).get('cliente', 'N/A')}")
                print(f"\n📦 PRIMER ITEM:")
                print(f"   Descripción: {item.get('descripcion', 'N/A')}")
                print(f"   UOM: '{item.get('uom', 'NO_ENCONTRADO')}'")
                print(f"   Cantidad: '{item.get('cantidad', 'NO_ENCONTRADO')}'")
                print(f"   Costo Unidad: '{item.get('costoUnidad', 'NO_ENCONTRADO')}'")
                print(f"   Total (total): '{item.get('total', 'NO_ENCONTRADO')}'")
                print(f"   Total (totalItem): '{item.get('totalItem', 'NO_ENCONTRADO')}'")

                print(f"\n🔍 TODOS LOS CAMPOS DEL ITEM:")
                for key, value in item.items():
                    if key not in ['materiales', 'otrosMateriales']:
                        print(f"   {key}: {value}")

                # Simular lo que haría preparar_datos_nueva_revision
                print(f"\n🔄 SIMULANDO PREPARACIÓN DE REVISIÓN:")
                import copy
                datos_revision = copy.deepcopy(cot)

                # Simular preparar_datos_nueva_revision
                if 'items' in datos_revision:
                    for idx, item_rev in enumerate(datos_revision['items']):
                        print(f"\n   Item {idx + 1} después de deepcopy:")
                        print(f"      UOM: '{item_rev.get('uom', 'NO_ENCONTRADO')}'")
                        print(f"      Cantidad: '{item_rev.get('cantidad', 'NO_ENCONTRADO')}'")
                        print(f"      Descripción: {item_rev.get('descripcion', 'N/A')[:50]}")

                break
else:
    print("❌ No hay cotizaciones en el archivo")

print("\n" + "=" * 80)
