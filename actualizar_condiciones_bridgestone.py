#!/usr/bin/env python3
"""
Script puntual: actualizar condiciones de la cotizacion
INDUSTRIAL-CWS-RM-001-R1-BRIDGESTONE MX en Supabase.

Ejecutar con: python actualizar_condiciones_bridgestone.py
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Faltan SUPABASE_URL o SUPABASE_KEY en .env")
    sys.exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

NUMERO = "INDUSTRIAL-CWS-RM-001-R1-BRIDGESTONE MX"

# 1. Leer cotizacion actual
print(f"[1/3] Leyendo: {NUMERO}")
existing = client.table('cotizaciones').select('*').eq('numero_cotizacion', NUMERO).execute()

if not existing.data:
    print(f"NO ENCONTRADA: {NUMERO}")
    search = client.table('cotizaciones').select('numero_cotizacion').ilike(
        'numero_cotizacion', '%BRIDGESTONE%'
    ).execute()
    print(f"Similares: {[r['numero_cotizacion'] for r in (search.data or [])]}")
    sys.exit(1)

row = existing.data[0]
print(f"  Encontrada! ID: {row['id']}")

# 2. Ver condiciones actuales
dg = row.get('datos_generales', {}) or {}
cond_actual = dg.get('condiciones', {}) or {}
print(f"\n[2/3] Condiciones ACTUALES: {cond_actual}")

# 3. Actualizar
nuevas_condiciones = {
    'moneda': 'MXN',
    'tipoCambio': 1,
    'tiempoEntrega': 'Entregas semanales a partir de la 4ta semana despues de OC',
    'entregaEn': 'Mexico',
    'terminos': '30% anticipo y el resto contra entrega (facturas parciales)',
    'condicionesPago': '30% anticipo y el resto contra entrega (facturas parciales)',
    'comentarios': (
        '-Los materiales considerados en esta cotizacion corresponden a materiales '
        'comerciales en Mexico expresados en pulgadas y calibres comerciales.\n'
        '-El precio incluye Ingenieria actualizada en 2D y 3D.'
    ),
    'comentariosAdicionales': (
        '-Los materiales considerados en esta cotizacion corresponden a materiales '
        'comerciales en Mexico expresados en pulgadas y calibres comerciales.\n'
        '-El precio incluye Ingenieria actualizada en 2D y 3D.'
    )
}

dg['condiciones'] = nuevas_condiciones

try:
    client.table('cotizaciones').update({
        'datos_generales': dg
    }).eq('id', row['id']).execute()
    print(f"\n[3/3] ACTUALIZADO!")
except Exception as e:
    print(f"\n[ERROR] {e}")
    sys.exit(1)

# Verificar
verify = client.table('cotizaciones').select('datos_generales').eq('id', row['id']).execute()
if verify.data:
    cv = verify.data[0].get('datos_generales', {}).get('condiciones', {})
    print(f"  moneda: {cv.get('moneda')}")
    print(f"  tiempoEntrega: {cv.get('tiempoEntrega')}")
    print(f"  terminos: {cv.get('terminos')}")
    print("\nLISTO. Recarga el desglose.")
