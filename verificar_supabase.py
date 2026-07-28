import os, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor, connect_timeout=15)
cur = conn.cursor()

# Total
cur.execute("SELECT COUNT(*) as c FROM cotizaciones")
print(f"Total en Supabase: {cur.fetchone()['c']}")

# Buscar TEXTEX
cur.execute("SELECT numero_cotizacion, datos_generales->>'cliente' as cliente "
            "FROM cotizaciones WHERE UPPER(datos_generales->>'cliente') LIKE '%TEXTEX%' "
            "OR UPPER(numero_cotizacion) LIKE '%TEXTEX%'")
r = cur.fetchall()
if r:
    print(f"TEXTEX encontradas: {len(r)}")
    for c in r:
        print(f"  {c['numero_cotizacion']} - {c['cliente']}")
else:
    print("No hay TEXTEX en Supabase")

# Buscar TEST, PRUEBA, DEBUG
cur.execute("SELECT numero_cotizacion, datos_generales->>'cliente' as cliente "
            "FROM cotizaciones WHERE UPPER(datos_generales->>'cliente') LIKE '%TEST%' "
            "OR UPPER(datos_generales->>'cliente') LIKE '%PRUEBA%' "
            "OR UPPER(datos_generales->>'cliente') LIKE '%DEBUG%' "
            "ORDER BY numero_cotizacion")
r2 = cur.fetchall()
if r2:
    print(f"\nOtras de prueba (TEST/PRUEBA/DEBUG): {len(r2)}")
    for c in r2:
        print(f"  {c['numero_cotizacion']} - {c['cliente']}")
else:
    print("\nNo quedan TEST/PRUEBA/DEBUG en Supabase")

conn.close()
input("\nPresiona Enter para cerrar...")
