"""
Script de migracion SaaS para Supabase.
Ejecuta: python run_migration.py
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')

if not DB_URL:
    print("ERROR: DATABASE_URL no encontrada en .env")
    exit(1)

print("Conectando a PostgreSQL...")
conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

# Aumentar timeout para operaciones pesadas
cur.execute("SET statement_timeout = '120000'")  # 2 minutos
cur.execute("SET lock_timeout = '60000'")         # 1 minuto
print("OK (timeout: 2min)\n")

# 1. Tabla companies
print("1/5 Creando companies...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS public.companies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        slug VARCHAR(100) UNIQUE NOT NULL,
        tax_id VARCHAR(50),
        address TEXT,
        phone VARCHAR(50),
        email VARCHAR(255),
        logo_url TEXT,
        primary_color VARCHAR(7) DEFAULT '#4f46e5',
        secondary_color VARCHAR(7) DEFAULT '#1e293b',
        footer_text TEXT,
        iva_rate DECIMAL(5,2) DEFAULT 16.00,
        is_active BOOLEAN DEFAULT true,
        max_users INTEGER DEFAULT 10,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
""")
print("   OK")

# 2. Columnas company_id
for tabla in ['cotizaciones', 'pdf_storage', 'drafts']:
    print(f"2/5 Agregando company_id a {tabla}...")
    cur.execute(f"ALTER TABLE public.{tabla} ADD COLUMN IF NOT EXISTS company_id UUID")
    print(f"   OK")

# 3. Seed CWS Company
print("3/5 Creando CWS Company...")
cur.execute("""
    INSERT INTO public.companies (name, slug, tax_id, address, phone, email,
        primary_color, secondary_color, footer_text, iva_rate, codigo, legacy_drive_import)
    VALUES (
        'CWS Company SA de CV', 'cws-company', 'CWS-123456',
        'Puerta de los monos 250, 78421 Villa de Pozos, SLP, Mexico',
        '+52 444 123 4567', 'info@cwscompany.com',
        '#1e293b', '#0f172a',
        '<b>CWS Company SA de CV</b> | Puerta de los monos 250, 78421 Villa de Pozos, SLP, Mexico<br/>Esta cotizacion es valida por 30 dias | <b>Gracias por confiar en CWS Company!</b>',
        16.00, 'CWS', true
    ) ON CONFLICT (slug) DO NOTHING
""")
cur.execute("SELECT id FROM public.companies WHERE slug = 'cws-company'")
row = cur.fetchone()
cws_id = row[0]
print(f"   CWS Company ID: {cws_id}")

cur.execute("UPDATE public.cotizaciones SET company_id = %s WHERE company_id IS NULL", (cws_id,))
print(f"   Cotizaciones migradas: {cur.rowcount}")
cur.execute("UPDATE public.pdf_storage SET company_id = %s WHERE company_id IS NULL", (cws_id,))
print(f"   PDFs migrados: {cur.rowcount}")
cur.execute("UPDATE public.drafts SET company_id = %s WHERE company_id IS NULL", (cws_id,))
print(f"   Drafts migrados: {cur.rowcount}")

# 4. RLS
print("4/5 Activando RLS...")
cur.execute("ALTER TABLE public.cotizaciones ENABLE ROW LEVEL SECURITY")
cur.execute("ALTER TABLE public.pdf_storage ENABLE ROW LEVEL SECURITY")
cur.execute("DROP POLICY IF EXISTS \"Permitir acceso publico a drafts\" ON public.drafts")

for tabla in ['cotizaciones', 'pdf_storage', 'drafts']:
    policy = f'company_isolation_{tabla}'
    cur.execute(f"DROP POLICY IF EXISTS {policy} ON public.{tabla}")
    cur.execute(f"""
        CREATE POLICY {policy} ON public.{tabla}
        FOR ALL USING (
            company_id = COALESCE(
                current_setting('app.current_company_id', true)::UUID,
                '00000000-0000-0000-0000-000000000000'::UUID
            )
        )
    """)
    print(f"   RLS: {tabla}")

# 5. Profiles
print("5/5 Creando profiles...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS public.profiles (
        id UUID PRIMARY KEY,
        company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
        full_name VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'seller'
            CHECK (role IN ('admin', 'manager', 'seller')),
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
""")
cur.execute("ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY")
print("   OK")

# Done
cur.close()
conn.close()
print("\nMigracion completada!")
