"""Diagnostica el flujo de login paso a paso."""
import os, ssl
from dotenv import load_dotenv
load_dotenv()

# Parche para SSL local roto
import urllib3
urllib3.disable_warnings()
import requests
requests.packages.urllib3.disable_warnings()
# Desactivar SSL globalmente para requests
old_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return old_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

url = os.getenv('SUPABASE_URL')
anon = os.getenv('SUPABASE_ANON_KEY')
service = os.getenv('SUPABASE_SERVICE_KEY')
email = "cwsventas@cwscompany.com"
password = "MiCuenta123"

print("=== PASO 1: Verificar usuario en auth.users ===")
resp = requests.get(
    f'{url}/auth/v1/admin/users',
    headers={'Authorization': f'Bearer {service}', 'apikey': service}
)
users = resp.json().get('users', [])
user = next((u for u in users if u.get('email') == email), None)
if user:
    print(f"OK - {user['id']}, confirmado={user.get('email_confirmed_at') is not None}")
else:
    print(f"ERROR: Usuario {email} no encontrado")
    print("Usuarios:")
    for u in users:
        print(f"  {u.get('email')}")
    exit(1)

print("\n=== PASO 2: Login con password ===")
resp = requests.post(
    f'{url}/auth/v1/token?grant_type=password',
    headers={'apikey': anon, 'Content-Type': 'application/json'},
    json={'email': email, 'password': password}
)
if resp.status_code == 200:
    data = resp.json()
    uid = data.get('user', {}).get('id')
    print(f"OK - User ID: {uid}")
else:
    print(f"ERROR: {resp.status_code} - {resp.text[:300]}")
    exit(1)

print("\n=== PASO 3: Buscar perfil (service key) ===")
resp = requests.get(
    f'{url}/rest/v1/profiles?id=eq.{uid}&select=*',
    headers={'apikey': service, 'Authorization': f'Bearer {service}'}
)
profiles = resp.json()
if profiles:
    p = profiles[0]
    print(f"OK - {p.get('full_name')} | role={p.get('role')} | cid={p.get('company_id')}")
    cid = p['company_id']
else:
    print("ERROR: Perfil no encontrado")
    exit(1)

print("\n=== PASO 4: Buscar compañía ===")
resp = requests.get(
    f'{url}/rest/v1/companies?id=eq.{cid}&select=*',
    headers={'apikey': service, 'Authorization': f'Bearer {service}'}
)
companies = resp.json()
if companies:
    c = companies[0]
    print(f"OK - {c.get('name')} | active={c.get('is_active')}")
else:
    print("ERROR: Compañía no encontrada")

print("\n=== DIAGNÓSTICO COMPLETO ===")
print("El login debería funcionar. Si falla en Render, comparte los logs de Render.")
