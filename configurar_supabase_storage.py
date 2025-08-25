#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurar automáticamente las políticas de Supabase Storage
"""

def configurar_storage_policies():
    """Configurar políticas de acceso para Supabase Storage"""
    print("CONFIGURANDO POLITICAS DE SUPABASE STORAGE")
    print("=" * 50)
    
    try:
        from supabase_manager import SupabaseManager
        
        # Conectar a Supabase
        db_manager = SupabaseManager()
        if db_manager.modo_offline:
            print("ERROR: No se puede conectar a Supabase")
            return False
            
        print("OK: Conectado a Supabase")
        
        # Políticas SQL para Storage
        policies = [
            {
                "name": "Public read access",
                "sql": """
                CREATE POLICY "Public read access" ON storage.objects 
                FOR SELECT 
                USING (bucket_id = 'cotizaciones-pdfs');
                """,
                "description": "Permitir lectura pública de PDFs"
            },
            {
                "name": "Public upload access", 
                "sql": """
                CREATE POLICY "Public upload access" ON storage.objects 
                FOR INSERT 
                WITH CHECK (bucket_id = 'cotizaciones-pdfs');
                """,
                "description": "Permitir subida de PDFs desde la aplicación"
            },
            {
                "name": "Public update access",
                "sql": """
                CREATE POLICY "Public update access" ON storage.objects 
                FOR UPDATE 
                USING (bucket_id = 'cotizaciones-pdfs');
                """,
                "description": "Permitir actualización de PDFs"
            }
        ]
        
        # Ejecutar políticas
        for policy in policies:
            try:
                print(f"\nConfigurando: {policy['description']}")
                
                # Primero intentar eliminar si existe
                drop_sql = f"""
                DROP POLICY IF EXISTS "{policy['name']}" ON storage.objects;
                """
                
                try:
                    db_manager.supabase.rpc('execute_sql', {'query': drop_sql}).execute()
                    print(f"  - Política existente eliminada")
                except Exception as e:
                    print(f"  - Sin política previa (normal): {e}")
                
                # Crear nueva política
                db_manager.supabase.rpc('execute_sql', {'query': policy['sql']}).execute()
                print(f"  ✅ Política creada exitosamente")
                
            except Exception as e:
                print(f"  ❌ Error configurando política: {e}")
                
        # Verificar bucket
        print(f"\nVerificando bucket 'cotizaciones-pdfs'...")
        try:
            from supabase_storage_manager import SupabaseStorageManager
            storage = SupabaseStorageManager()
            
            # Listar archivos para verificar acceso
            files = storage.listar_pdfs()
            if "error" not in files:
                print(f"  ✅ Bucket accesible - {len(files.get('archivos', []))} archivos")
                
                # Mostrar archivos
                for archivo in files.get('archivos', [])[:3]:
                    nombre = archivo.get('name', 'Sin nombre')
                    url = archivo.get('url', 'Sin URL')
                    print(f"    - {nombre}")
                    print(f"      URL: {url}")
            else:
                print(f"  ❌ Error accediendo bucket: {files['error']}")
                
        except Exception as e:
            print(f"  ❌ Error verificando bucket: {e}")
            
        print(f"\n{'='*50}")
        print("CONFIGURACION COMPLETADA")
        print("\nPRUEBA MANUAL:")
        print("1. Ve a Supabase → Storage → cotizaciones-pdfs")
        print("2. Haz clic en cualquier PDF")  
        print("3. Copia la URL y ábrela en el navegador")
        print("4. Debería mostrar el PDF directamente")
        
        return True
        
    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    configurar_storage_policies()