#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test del fix para Supabase Storage - Verificar que ahora usa SERVICE_KEY
"""

import os
import tempfile
from datetime import datetime

def test_supabase_storage_fix():
    """Probar que Supabase Storage ahora funciona con SERVICE_KEY"""
    print("=" * 60)
    print("TEST: SUPABASE STORAGE FIX VERIFICATION")  
    print("=" * 60)
    
    # Verificar variables de entorno
    print("\n1. VERIFICANDO VARIABLES DE ENTORNO:")
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"   SUPABASE_URL: {'✅ Configurada' if supabase_url else '❌ Faltante'}")
    print(f"   SUPABASE_SERVICE_KEY: {'✅ Configurada' if service_key else '❌ Faltante'}")
    print(f"   SUPABASE_ANON_KEY: {'✅ Configurada' if anon_key else '❌ Faltante'}")
    
    if not service_key:
        print("\n❌ ERROR CRÍTICO: SUPABASE_SERVICE_KEY no está configurada")
        print("   Este es el problema - necesitas configurar esta variable en Render")
        return False
    
    # Test de inicialización
    print("\n2. PROBANDO INICIALIZACIÓN DE SUPABASE STORAGE:")
    try:
        from supabase_storage_manager import SupabaseStorageManager
        
        storage_manager = SupabaseStorageManager()
        
        if storage_manager.is_available():
            print("✅ SupabaseStorageManager inicializado correctamente")
            print("✅ El sistema ahora usará SERVICE_KEY para Storage operations")
        else:
            print("❌ SupabaseStorageManager no está disponible")
            return False
            
    except Exception as e:
        print(f"❌ Error inicializando SupabaseStorageManager: {e}")
        return False
    
    # Test de operaciones básicas
    print("\n3. PROBANDO OPERACIONES BÁSICAS:")
    try:
        # Listar PDFs existentes
        pdfs = storage_manager.listar_pdfs()
        if "error" not in pdfs:
            total_pdfs = len(pdfs.get("archivos", []))
            print(f"✅ Listar PDFs: {total_pdfs} archivos encontrados")
        else:
            print(f"⚠️  Listar PDFs: {pdfs['error']}")
        
        # Obtener estadísticas
        stats = storage_manager.obtener_estadisticas()
        if "error" not in stats:
            print(f"✅ Estadísticas: {stats.get('total_pdfs', 0)} PDFs total")
        else:
            print(f"⚠️  Estadísticas: {stats['error']}")
            
    except Exception as e:
        print(f"❌ Error en operaciones básicas: {e}")
        return False
    
    # Test de subida (con archivo temporal)
    print("\n4. PROBANDO SUBIDA DE PDF (TEST):")
    try:
        # Crear PDF de prueba temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
            temp_pdf.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
            temp_pdf.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n")
            temp_pdf.write(b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n")
            temp_pdf.write(b"0000000058 00000 n \n0000000115 00000 n \ntrailer\n")
            temp_pdf.write(b"<< /Size 4 /Root 1 0 R >>\nstartxref\n200\n%%EOF")
            temp_pdf_path = temp_pdf.name
        
        # Generar nombre único para la prueba
        test_number = f"TEST-STORAGE-FIX-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Intentar subir
        result = storage_manager.subir_pdf(
            archivo_local=temp_pdf_path,
            numero_cotizacion=test_number,
            es_nueva=True
        )
        
        # Limpiar archivo temporal
        os.unlink(temp_pdf_path)
        
        if "error" not in result:
            print("✅ SUBIDA EXITOSA!")
            print(f"   URL: {result.get('url', 'N/A')}")
            print(f"   Archivo: {result.get('file_path', 'N/A')}")
            print("✅ EL FIX FUNCIONÓ - PDFs ahora se guardan en Supabase Storage")
            
            # Intentar eliminar el archivo de prueba
            try:
                storage_manager.eliminar_pdf(result.get('file_path', ''))
                print("✅ Archivo de prueba eliminado")
            except:
                print("⚠️  Archivo de prueba no eliminado (no es problema)")
                
        else:
            print(f"❌ ERROR EN SUBIDA: {result.get('error', 'Error desconocido')}")
            print(f"   Tipo: {result.get('tipo_error', 'N/A')}")
            if result.get('fallback'):
                print("   El sistema usará fallbacks (Google Drive/Local)")
            return False
            
    except Exception as e:
        print(f"❌ Error en test de subida: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ RESULTADO: FIX APLICADO CORRECTAMENTE")
    print("   - SupabaseStorageManager ahora usa SUPABASE_SERVICE_KEY")
    print("   - Storage operations deberían funcionar en Render")
    print("   - PDFs se guardarán en Supabase Storage correctamente")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_supabase_storage_fix()
    if success:
        print("\n🎉 ¡TEST EXITOSO! El fix está funcionando.")
    else:
        print("\n💥 Test falló. Revisar configuración.")