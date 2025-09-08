#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para buscar la cotización que creamos
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from supabase_manager import SupabaseManager

db = SupabaseManager()

# Buscar cotizaciones con EMPRESA
print("Buscando cotizaciones con 'EMPRESA'...")
resultado = db.buscar_cotizaciones("EMPRESA", page=1, per_page=10)

print(f"Total encontradas: {resultado.get('total', 0)}")
print(f"Resultados: {len(resultado.get('resultados', []))}")

for i, cotizacion in enumerate(resultado.get('resultados', [])[:3]):
    numero = cotizacion.get('numeroCotizacion', 'Sin número')
    cliente = cotizacion.get('datosGenerales', {}).get('cliente', 'Sin cliente')
    print(f"{i+1}. {numero} - {cliente}")

# Probar obtener directamente
print(f"\nProbando obtener directamente: EMPRESAVIS-CWS-FO-001-R1-REVISIONDE")
cotizacion_directa = db.obtener_cotizacion("EMPRESAVIS-CWS-FO-001-R1-REVISIONDE")
print(f"Encontrada: {cotizacion_directa.get('encontrado', False)}")

if cotizacion_directa.get('encontrado'):
    cliente = cotizacion_directa.get('cotizacion', {}).get('datosGenerales', {}).get('cliente', 'No disponible')
    print(f"Cliente: {cliente}")
else:
    print(f"Error: {cotizacion_directa.get('error', 'No especificado')}")