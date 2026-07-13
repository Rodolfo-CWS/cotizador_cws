import os, requests, urllib3
urllib3.disable_warnings()
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
cws = '5f6b07c9-3b9f-42ac-8ea0-e3ad9a4fe56b'
uid = '62b12611-710c-40f4-b64a-447b40d4df33'

r = requests.patch(
    f'{url}/rest/v1/profiles?id=eq.{uid}',
    headers={'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={'company_id': cws, 'role': 'admin'},
    verify=False
)
print(f'Perfil movido a CWS: {r.status_code}')

r2 = requests.delete(
    f'{url}/rest/v1/companies?id=eq.464bec5b-bffb-44f6-bc82-794c75f7564c',
    headers={'apikey': key, 'Authorization': f'Bearer {key}'},
    verify=False
)
print(f'Temporal eliminada: {r2.status_code}')
print('Hecho. Cierra sesion y vuelve a entrar.')
