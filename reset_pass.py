"""Cambia la contraseña de un usuario via Supabase Admin API."""
import os, sys, requests
from dotenv import load_dotenv
load_dotenv()

if len(sys.argv) < 2:
    print("Uso: python reset_pass.py TU-NUEVA-CONTRASEÑA")
    print("Ejemplo: python reset_pass.py MiClave123")
    exit(1)

new_pass = sys.argv[1]
if len(new_pass) < 8:
    print("ERROR: La contraseña debe tener al menos 8 caracteres")
    exit(1)

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
email = "cwsventas@cwscompany.com"

# Buscar usuario
resp = requests.get(
    f'{url}/auth/v1/admin/users',
    headers={'Authorization': f'Bearer {key}', 'apikey': key}
)
users = resp.json().get('users', [])
user = next((u for u in users if u.get('email') == email), None)

if not user:
    print(f"ERROR: Usuario {email} no encontrado")
    exit(1)

uid = user['id']
print(f"Usuario encontrado: {uid}")

# Cambiar password
resp = requests.put(
    f'{url}/auth/v1/admin/users/{uid}',
    headers={
        'Authorization': f'Bearer {key}',
        'apikey': key,
        'Content-Type': 'application/json'
    },
    json={'password': new_pass, 'email_confirm': True}
)

if resp.status_code == 200:
    print(f"OK! Contraseña actualizada para {email}")
else:
    print(f"Error: {resp.status_code} {resp.text}")
