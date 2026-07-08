"""Mueve usuario de Temporal a CWS Company y borra la empresa temporal."""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')
USER_ID = "62b12611-710c-40f4-b64a-447b40d4df33"

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SET statement_timeout = '30000'")

# 1. Obtener CWS Company ID
cur.execute("SELECT id, name FROM public.companies WHERE slug = 'cws-company'")
cws = cur.fetchone()
cws_id = cws[0]
print(f"CWS Company: {cws[1]} (id={cws_id})")

# 2. Ver empresa actual del usuario
cur.execute("SELECT c.id, c.name, c.slug FROM public.profiles p JOIN public.companies c ON c.id = p.company_id WHERE p.id = %s", (USER_ID,))
tmp = cur.fetchone()
print(f"Empresa actual: {tmp[1]} (slug={tmp[2]}, id={tmp[0]})")
tmp_id = tmp[0]

# 3. Mover perfil a CWS Company
cur.execute("""
    INSERT INTO public.profiles (id, company_id, full_name, role)
    VALUES (%s, %s, 'Rodolfo Moreno', 'admin')
    ON CONFLICT (id) DO UPDATE SET company_id = EXCLUDED.company_id
""", (USER_ID, cws_id))
print("Perfil movido a CWS Company")

# 4. Eliminar empresa Temporal
cur.execute("DELETE FROM public.profiles WHERE company_id = %s AND id != %s", (tmp_id, USER_ID))
cur.execute("DELETE FROM public.companies WHERE id = %s", (tmp_id,))
print(f"Empresa '{tmp[1]}' eliminada")

# 5. Verificar
cur.execute("""
    SELECT p.full_name, p.role, c.name
    FROM public.profiles p JOIN public.companies c ON c.id = p.company_id
    WHERE p.id = %s
""", (USER_ID,))
final = cur.fetchone()
print(f"\nLISTO: {final[0]} | {final[2]} | {final[1]}")

cur.close()
conn.close()
print("Listo!")
