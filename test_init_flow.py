#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test del flujo de inicialización completo como en la app real
"""

import os
import sys

def test_init_flow():
    """Probar el flujo exacto de inicialización que usa la app"""
    print("=" * 60)
    print("🔄 TEST FLUJO INICIALIZACIÓN COMPLETO")
    print("=" * 60)
    
    print("\n1. 📦 Importando módulos...")
    try:
        from supabase_manager import SupabaseManager
        from pdf_manager import PDFManager
        print("   ✅ Módulos importados correctamente")
    except Exception as e:
        print(f"   ❌ Error importando: {e}")
        return False
    
    print("\n2. 🗄️ Inicializando SupabaseManager...")
    try:
        db_manager = SupabaseManager()
        print(f"   ✅ SupabaseManager: {'Online' if not db_manager.modo_offline else 'Offline'}")
    except Exception as e:
        print(f"   ❌ Error SupabaseManager: {e}")
        return False
    
    print("\n3. 📄 Inicializando PDFManager...")
    try:
        # Esto es exactamente como se hace en app.py
        pdf_manager = PDFManager(db_manager)
        print(f"   ✅ PDFManager inicializado")
        print(f"   📊 Supabase Storage disponible: {pdf_manager.supabase_storage_disponible}")
        print(f"   📊 Google Drive disponible: {pdf_manager.drive_client.is_available()}")
    except Exception as e:
        print(f"   ❌ Error PDFManager: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n4. 🔍 Análisis detallado del estado...")
    
    # Verificar estado interno de SupabaseStorageManager
    try:
        storage_mgr = pdf_manager.supabase_storage
        print(f"   📊 Storage available: {storage_mgr.storage_available}")
        print(f"   📊 Bucket name: {storage_mgr.bucket_name}")
        
        # Verificar variables de entorno específicas
        service_key = os.getenv('SUPABASE_SERVICE_KEY')
        anon_key = os.getenv('SUPABASE_ANON_KEY')
        
        print(f"   🔑 SERVICE_KEY presente: {'Sí' if service_key else 'No'}")
        print(f"   🔑 ANON_KEY presente: {'Sí' if anon_key else 'No'}")
        
        if service_key and anon_key:
            keys_different = service_key != anon_key
            print(f"   🔍 Claves son diferentes: {'Sí' if keys_different else 'No'}")
            if not keys_different:
                print("   ⚠️  PROBLEMA: Las claves son iguales - debe usar service_role key")
        
    except Exception as e:
        print(f"   ❌ Error análisis: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n5. 🧪 Test de operación completa...")
    if pdf_manager.supabase_storage_disponible:
        try:
            # Test similar al flujo real de almacenamiento
            import tempfile
            import datetime
            
            # PDF mínimo
            pdf_content = b"%PDF-1.4\n%%EOF"
            
            # Datos de cotización simulados
            cotizacion_data = {
                'numeroCotizacion': f'TEST-FLOW-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}',
                'datosGenerales': {
                    'cliente': 'TEST',
                    'vendedor': 'TEST',
                    'proyecto': 'INIT-FLOW'
                }
            }
            
            print("   🚀 Probando almacenar_pdf_nuevo...")
            resultado = pdf_manager.almacenar_pdf_nuevo(
                pdf_content=pdf_content,
                cotizacion_data=cotizacion_data
            )
            
            if resultado.get("success"):
                print("   ✅ almacenar_pdf_nuevo EXITOSO!")
                print(f"      Estado: {resultado.get('estado')}")
                print(f"      Archivo: {resultado.get('nombre_archivo')}")
                
                # Verificar detalles de cada sistema
                sistemas = resultado.get('sistemas', {})
                supabase_result = sistemas.get('supabase_storage', {})
                
                if supabase_result.get('success'):
                    print("   🎉 SUPABASE STORAGE FUNCIONÓ!")
                    print(f"      URL: {supabase_result.get('url', 'N/A')}")
                else:
                    print("   ❌ Supabase Storage falló:")
                    print(f"      Error: {supabase_result.get('error', 'N/A')}")
                    print(f"      Tipo: {supabase_result.get('tipo_error', 'N/A')}")
                
            else:
                print("   ❌ almacenar_pdf_nuevo FALLÓ!")
                print(f"      Error: {resultado.get('error', 'N/A')}")
                
        except Exception as e:
            print(f"   ❌ Error en test: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("   ⏩ Supabase Storage no disponible - saltando test")
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO DEL DIAGNÓSTICO:")
    
    if pdf_manager.supabase_storage_disponible:
        print("✅ Supabase Storage está DISPONIBLE según PDFManager")
        print("   El problema puede estar en:")
        print("   - Permisos del bucket en Supabase")
        print("   - Configuración RLS (Row Level Security)")
        print("   - Variables de entorno en Render vs local")
    else:
        print("❌ Supabase Storage NO ESTÁ DISPONIBLE según PDFManager")
        print("   Esto explica por qué no se guardan PDFs")
        print("   Revisar inicialización de SupabaseStorageManager")
    
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_init_flow()