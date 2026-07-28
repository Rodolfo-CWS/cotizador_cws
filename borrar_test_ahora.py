import os, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor, connect_timeout=15)
conn.autocommit = False
cur = conn.cursor()

# Buscar todas las de prueba
KEYWORDS = ['TEXTEX','TEST','PRUEBA','DEBUG','CLIENTE-PRUEBA','CLIENTE-TEST','TEST-CLIENTE','TEST-CORRECCIONES','CLIENTE-DEBUG','TEST-DEBUG']
conds = []
params = []
for kw in KEYWORDS:
    conds.append("UPPER(datos_generales->>'cliente') LIKE %s")
    params.append(f'%{kw}%')
    conds.append("UPPER(numero_cotizacion) LIKE %s")
    params.append(f'%{kw}%')

cur.execute(f"SELECT id, numero_cotizacion, datos_generales->>'cliente' as cliente "
            f"FROM cotizaciones WHERE {' OR '.join(conds)} ORDER BY numero_cotizacion", params)
results = cur.fetchall()

print(f"COTIZACIONES DE PRUEBA: {len(results)}")
print("="*60)
for i, c in enumerate(results, 1):
    print(f"{i:2d}. [ID:{c['id']}] {c['numero_cotizacion']}")
    print(f"    Cliente: {c['cliente']}")
print("="*60)

if results:
    resp = input(f"\nEliminar estas {len(results)} cotizaciones? Escribe SI: ")
    if resp.upper() == 'SI':
        ids = [c['id'] for c in results]
        numeros = [c['numero_cotizacion'] for c in results]

        try:
            cur.execute('DELETE FROM pdf_storage WHERE numero_cotizacion = ANY(%s)', (numeros,))
            print(f"PDFs borrados: {cur.rowcount}")
        except Exception as e:
            print(f"PDFs: {e}")

        cur.execute('DELETE FROM cotizaciones WHERE id = ANY(%s)', (ids,))
        cotiz = cur.rowcount

        conn.commit()
        print(f"Cotizaciones borradas: {cotiz}")
        print("COMMIT OK.")

        cur.execute("SELECT COUNT(*) as c FROM cotizaciones")
        total = cur.fetchone()['c']
        print(f"\nTotal restante en BD: {total}")
    else:
        print("Cancelado.")

conn.close()
input("\nPresiona Enter para cerrar...")
