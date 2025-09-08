#!/usr/bin/env python3
"""Test rápido después de agregar columna condiciones"""

from supabase_manager import SupabaseManager

print("=== TEST POST-FIX ===")

# Test guardado
db = SupabaseManager()
datos_test = {
    'datosGenerales': {'cliente': 'POST-FIX-TEST', 'vendedor': 'Validator', 'proyecto': 'SUCCESS'},
    'items': [{'descripcion': 'Test item', 'cantidad': 1, 'precio_unitario': 100}],
    'condiciones': {'moneda': 'USD', 'terminos': 'NET 30'},
    'observaciones': 'Test después de agregar columna condiciones'
}

resultado = db.guardar_cotizacion(datos_test)

print(f"Resultado: {resultado.get('success')}")
print(f"Modo: {resultado.get('modo')}")
print(f"ID: {resultado.get('id', 'N/A')}")

if resultado.get('modo') == 'online':
    print("🎉 ¡ÉXITO! Supabase DB funcionando")
else:
    print("❌ Aún en modo offline")