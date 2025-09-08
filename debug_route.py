#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruta temporal para debugging de Supabase Storage en Render
Agregar a app.py temporalmente
"""

# AGREGAR ESTA RUTA TEMPORAL A app.py:
"""
@app.route('/debug-storage')
def debug_storage():
    try:
        import os
        from supabase_storage_manager import SupabaseStorageManager
        
        # Variables de entorno
        supabase_url = os.getenv('SUPABASE_URL')
        service_key = os.getenv('SUPABASE_SERVICE_KEY')
        anon_key = os.getenv('SUPABASE_ANON_KEY')
        
        debug_info = {
            "variables": {
                "SUPABASE_URL": "Presente" if supabase_url else "Faltante",
                "SUPABASE_SERVICE_KEY": "Presente" if service_key else "Faltante", 
                "SUPABASE_ANON_KEY": "Presente" if anon_key else "Faltante"
            }
        }
        
        # Test de inicialización
        try:
            storage = SupabaseStorageManager()
            debug_info["storage_init"] = {
                "success": True,
                "available": storage.is_available(),
                "bucket": storage.bucket_name
            }
            
            # Test de operación básica
            try:
                files = storage.listar_pdfs()
                if "error" in files:
                    debug_info["storage_test"] = {"error": files["error"]}
                else:
                    debug_info["storage_test"] = {"success": True, "files_count": len(files.get("archivos", []))}
            except Exception as e:
                debug_info["storage_test"] = {"error": f"Test failed: {str(e)}"}
                
        except Exception as e:
            debug_info["storage_init"] = {"success": False, "error": str(e)}
        
        return debug_info
        
    except Exception as e:
        return {"error": f"Debug failed: {str(e)}"}
"""