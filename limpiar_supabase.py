#!/usr/bin/env python3
"""Limpiar cotizaciones de prueba de Supabase"""
import os, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

KEYWORDS = ['TEST','TEXTEX','PRUEBA','DEBUG','VALIDACION','VERIFICACION',
    'CLIENTE-PRUEBA','TESTING','DEMO','EJEMPLO','SAMPLE','TEMP',
    'BORRAR','ELIMINAR','XXXX','XXX','ABC','ASD','QWE',
    'N/A','SIN CLIENTE','DESCONOCIDO']

conn = psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor, connect_timeout=15)
cur = conn.cursor()

conds = []
params = []
for kw in KEYWORDS:
    for col in ["datos_generales->>'cliente'", 'numero_cotizacion', "datos_generales->>'proyecto'"]:
        conds.append(f'UPPER({col}) LIKE %s')
        params.append(f'%{kw}%')

cur.execute(f"SELECT id, numero_cotizacion, datos_generales->>'cliente' as cliente, "
            f"datos_generales->>'proyecto' as proyecto, revision, fecha_creacion "
            f"FROM cotizaciones WHERE {' OR '.join(conds)} ORDER BY numero_cotizacion", params)
results = cur.fetchall()

if not results:
    print('No se encontraron cotizaciones de prueba.')
else:
    print(f'\nCOTIZACIONES DE PRUEBA ENCONTRADAS: {len(results)}')
    print('='*70)
    for i, c in enumerate(results, 1):
        fecha = str(c['fecha_creacion'])[:10] if c['fecha_creacion'] else 'N/A'
        print(f"{i:3d}. [ID:{c['id']}] {c['numero_cotizacion']}")
        print(f"     Cliente: {c['cliente'] or 'N/A'} | Proyecto: {c['proyecto'] or 'N/A'} | R{c['revision']} | {fecha}")
    print('='*70)

    resp = input(f'\nEliminar estas {len(results)} cotizaciones? Escribe SI para confirmar: ')
    if resp.upper() == 'SI':
        ids = [c['id'] for c in results]
        cur.execute('DELETE FROM pdf_storage WHERE cotizacion_id = ANY(%s)', (ids,))
        print(f'PDFs eliminados: {cur.rowcount}')
        cur.execute('DELETE FROM cotizaciones WHERE id = ANY(%s)', (ids,))
        print(f'Cotizaciones eliminadas: {cur.rowcount}')
        conn.commit()
        print('\nHECHO - Limpieza completada.')
    else:
        print('\nCancelado. No se elimino nada.')

cur.execute('SELECT COUNT(*) as c FROM cotizaciones')
total = cur.fetchone()['c']
print(f'\nTotal cotizaciones en la BD: {total}')
conn.close()
