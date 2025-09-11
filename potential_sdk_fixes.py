#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Potential SDK REST Fixes
========================

Based on common Supabase SDK issues, here are the likely fixes
depending on what error we see in the Render logs.
"""

# POTENTIAL FIX 1: RLS (Row Level Security) Issue
"""
If error mentions "permission denied" or "RLS":
- Supabase has Row Level Security enabled
- Need to use SERVICE_KEY instead of ANON_KEY for writes
- Or disable RLS on cotizaciones table
"""

# POTENTIAL FIX 2: Column Naming Issue
"""
If error mentions "column does not exist":
- PostgreSQL columns might be snake_case but we're sending camelCase
- Need to check actual table schema in Supabase
- Common mismatches:
  - numero_cotizacion vs numeroCotizacion
  - datos_generales vs datosGenerales
  - fecha_creacion vs fechaCreacion
"""

# POTENTIAL FIX 3: Data Type Issue
"""
If error mentions data type mismatch:
- JSON fields need to be properly serialized
- TIMESTAMP fields need correct format
- INTEGER fields can't receive strings
"""

# POTENTIAL FIX 4: Authentication Issue
"""
If error mentions "invalid JWT" or "unauthorized":
- SUPABASE_ANON_KEY might be wrong
- SUPABASE_URL might be wrong
- Environment variables not loaded properly
"""

# POTENTIAL FIX 5: Network/Timeout Issue  
"""
If error mentions timeout or network:
- Add retry logic
- Increase timeout
- Check if Supabase service is down
"""

def create_service_key_fix():
    """Fix using SERVICE_KEY instead of ANON_KEY for writes"""
    return """
    # In supabase_manager.py __init__ method:
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    if service_key:
        self.supabase_write_client = create_client(self.supabase_url, service_key)
        print("[SUPABASE] Cliente de escritura con SERVICE_KEY creado")
    
    # In _guardar_cotizacion_sdk method:
    write_client = getattr(self, 'supabase_write_client', self.supabase_client)
    response = write_client.table('cotizaciones').insert(sdk_data).execute()
    """

def create_column_mapping_fix():
    """Fix column naming mismatches"""
    return """
    # Map camelCase to snake_case for PostgreSQL
    sdk_data = {
        'numero_cotizacion': numero_cotizacion,
        'datos_generales': json.dumps(datos_generales),  # Serialize JSON
        'items': json.dumps(items),  # Serialize JSON  
        'revision': revision,
        'version': version,
        'fecha_creacion': fecha_creacion,
        'timestamp': timestamp,
        'usuario': usuario,
        'observaciones': observaciones
    }
    """

def create_rls_bypass_fix():
    """Fix RLS permission issues"""
    return """
    # Option 1: Use service key (full permissions)
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    admin_client = create_client(self.supabase_url, service_key)
    
    # Option 2: Add RLS policy for authenticated users
    # In Supabase Dashboard → Authentication → Policies:
    # CREATE POLICY "Enable insert for authenticated users" 
    # ON cotizaciones FOR INSERT 
    # WITH CHECK (true);
    """

print("SDK REST Potential Fixes Ready")
print("Waiting for Render logs analysis...")