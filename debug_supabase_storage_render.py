#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico específico para Supabase Storage en Render
"""

import os
import sys
import traceback
from datetime import datetime

def debug_supabase_storage_render():
    """Diagnóstico completo del problema de Storage en Render"""
    print("=" * 70)
    print("🔍 DIAGNÓSTICO SUPABASE STORAGE EN RENDER")
    print("=" * 70)
    
    # 1. Verificar variables de entorno
    print("\n1. 🔑 VERIFICACIÓN DE VARIABLES DE ENTORNO:")
    variables = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY'),
        'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY')
    }
    
    for var, value in variables.items():
        if value:
            # Mostrar solo primeros y últimos caracteres para seguridad
            masked = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else "PRESENTE"
            print(f"   ✅ {var}: {masked}")
        else:
            print(f"   ❌ {var}: FALTANTE")
    
    # Verificar si SERVICE_KEY es diferente de ANON_KEY
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    if service_key and anon_key:
        if service_key == anon_key:
            print("   ⚠️  WARNING: SERVICE_KEY es igual a ANON_KEY - esto es incorrecto")
            print("      SERVICE_KEY debe ser la clave 'service_role', no 'anon'")
        else:
            print("   ✅ SERVICE_KEY es diferente de ANON_KEY (correcto)")
    
    # 2. Test de inicialización de SupabaseStorageManager
    print("\n2. 🚀 TEST DE INICIALIZACIÓN:")
    try:
        from supabase_storage_manager import SupabaseStorageManager
        storage = SupabaseStorageManager()
        
        if storage.is_available():
            print("   ✅ SupabaseStorageManager inicializado correctamente")
        else:
            print("   ❌ SupabaseStorageManager NO disponible")
            return False
            
    except Exception as e:
        print(f"   ❌ Error inicializando Storage: {e}")
        traceback.print_exc()
        return False
    
    # 3. Test de permisos de bucket
    print("\n3. 🪣 TEST DE PERMISOS DE BUCKET:")
    try:
        # Intentar listar archivos (requiere permisos de lectura)
        files = storage.listar_pdfs(max_resultados=5)
        if "error" not in files:
            print(f"   ✅ Lectura: {len(files.get('archivos', []))} archivos listados")
        else:
            print(f"   ❌ Lectura falló: {files['error']}")
            
    except Exception as e:
        print(f"   ❌ Error listando archivos: {e}")
        traceback.print_exc()
    
    # 4. Test de subida (archivo temporal)
    print("\n4. 📤 TEST DE SUBIDA DE PDF:")
    try:
        import tempfile
        
        # Crear PDF mínimo válido
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
200
%%EOF"""
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_content)
            temp_file_path = temp_file.name
        
        # Generar nombre único
        test_name = f"DEBUG-RENDER-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print(f"   🧪 Probando subida: {test_name}")
        
        # Intentar subir
        result = storage.subir_pdf(
            archivo_local=temp_file_path,
            numero_cotizacion=test_name,
            es_nueva=True
        )
        
        # Limpiar archivo temporal
        os.unlink(temp_file_path)
        
        if "error" not in result:
            print("   ✅ SUBIDA EXITOSA!")
            print(f"      URL: {result.get('url', 'N/A')}")
            print(f"      Path: {result.get('file_path', 'N/A')}")
            print(f"      Bytes: {result.get('bytes', 0)}")
            
            # Intentar eliminar archivo de prueba
            try:
                delete_result = storage.eliminar_pdf(result.get('file_path', ''))
                if "error" not in delete_result:
                    print("   ✅ Archivo de prueba eliminado exitosamente")
                else:
                    print(f"   ⚠️  No se pudo eliminar archivo de prueba: {delete_result.get('error')}")
            except Exception as del_e:
                print(f"   ⚠️  Error eliminando archivo de prueba: {del_e}")
                
        else:
            print("   ❌ SUBIDA FALLÓ!")
            print(f"      Error: {result.get('error', 'Desconocido')}")
            print(f"      Tipo: {result.get('tipo_error', 'N/A')}")
            print(f"      Fallback: {result.get('fallback', False)}")
            
            # Analizar tipo de error
            error_msg = result.get('error', '').lower()
            if 'permission' in error_msg or 'forbidden' in error_msg or 'unauthorized' in error_msg:
                print("   🔍 ANÁLISIS: Error de permisos - posible problema con SERVICE_KEY")
            elif 'bucket' in error_msg or 'not found' in error_msg:
                print("   🔍 ANÁLISIS: Problema con bucket - verificar configuración en Supabase")
            elif 'network' in error_msg or 'timeout' in error_msg:
                print("   🔍 ANÁLISIS: Problema de conectividad")
            else:
                print("   🔍 ANÁLISIS: Error desconocido - ver logs completos")
            
            return False
            
    except Exception as e:
        print(f"   ❌ Error en test de subida: {e}")
        traceback.print_exc()
        return False
    
    # 5. Verificar integración con PDFManager
    print("\n5. 🔗 TEST DE INTEGRACIÓN CON PDF MANAGER:")
    try:
        from pdf_manager import PDFManager
        from supabase_manager import SupabaseManager
        
        # Crear instancias como en la app real
        db_manager = SupabaseManager()
        pdf_manager = PDFManager(db_manager)
        
        print(f"   ✅ PDFManager inicializado")
        print(f"   ✅ Supabase Storage disponible: {pdf_manager.supabase_storage_disponible}")
        
        if not pdf_manager.supabase_storage_disponible:
            print("   ❌ PDFManager no detecta Supabase Storage como disponible")
            print("      Esto explica por qué los PDFs no se guardan en Storage")
            return False
        
    except Exception as e:
        print(f"   ❌ Error en integración: {e}")
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("\nSi todos los tests pasaron, el problema puede ser:")
    print("1. Configuración del bucket en Supabase dashboard")
    print("2. Políticas de acceso RLS (Row Level Security)")
    print("3. Variables de entorno en Render diferentes a las locales")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    try:
        success = debug_supabase_storage_render()
        if success:
            print("\n🎉 Diagnóstico completado exitosamente")
        else:
            print("\n💥 Se encontraron problemas - revisar output")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error general en diagnóstico: {e}")
        traceback.print_exc()
        sys.exit(1)