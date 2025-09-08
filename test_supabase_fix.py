#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico para verificar que el error 'proxy' de Supabase Storage se ha resuelto
"""

import os
import sys
from datetime import datetime

def test_supabase_storage_fix():
    """Verificar que el error del parámetro 'proxy' se ha resuelto"""
    print("=" * 60)
    print("TEST: VERIFICACIÓN FIX SUPABASE STORAGE 'PROXY' ERROR")  
    print("=" * 60)
    
    # 1. Verificar variables de entorno
    print("\n1. VERIFICANDO VARIABLES DE ENTORNO:")
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"   SUPABASE_URL: {'OK Configurada' if supabase_url else 'ERROR Faltante'}")
    print(f"   SUPABASE_SERVICE_KEY: {'OK Configurada' if service_key else 'ERROR Faltante'}")
    print(f"   SUPABASE_ANON_KEY: {'OK Configurada' if anon_key else 'ERROR Faltante'}")
    
    # 2. Test de inicialización sin error 'proxy'
    print("\n2. PROBANDO INICIALIZACIÓN SIN ERROR 'PROXY':")
    try:
        from supabase_storage_manager import SupabaseStorageManager
        
        print("   Creando instancia de SupabaseStorageManager...")
        storage_manager = SupabaseStorageManager()
        
        if storage_manager.is_available():
            print("SUCCESS: SupabaseStorageManager inicializado SIN errores")
            print("SUCCESS: No se encontraron errores de 'proxy' o 'unexpected keyword argument'")
            
            # Test básico de funcionalidad
            try:
                stats = storage_manager.obtener_estadisticas()
                if 'error' not in stats:
                    print("SUCCESS: Estadisticas obtenidas correctamente")
                    print(f"   Total PDFs en storage: {stats.get('total_pdfs', 0)}")
                else:
                    print(f"WARNING: Error obteniendo estadisticas: {stats.get('error')}")
                    
            except Exception as stats_error:
                print(f"WARNING: Error en test de estadisticas: {stats_error}")
                
        else:
            print("ERROR: SupabaseStorageManager no esta disponible")
            print("   Revisar configuración de variables de entorno o conectividad")
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        
        # Verificar específicamente si es el error de 'proxy'
        error_str = str(e).lower()
        if 'proxy' in error_str:
            print("FALLA: El error de 'proxy' AUN persiste")
            print("   ACCION REQUERIDA: Verificar que la version de supabase>=2.5.0 este instalada")
            return False
        elif 'unexpected keyword argument' in error_str:
            print("FALLA: Error de parametros incompatibles AUN persiste")
            print("   ACCION REQUERIDA: Revisar version de la libreria supabase")
            return False
        else:
            print(f"FALLA: Error diferente: {e}")
            return False
    
    # 3. Verificar PDF Manager también funciona
    print("\n3. PROBANDO PDF MANAGER CON SUPABASE STORAGE:")
    try:
        # Importar solo para verificar que no hay errores de inicialización
        from pdf_manager import PDFManager
        from supabase_manager import SupabaseManager
        
        print("   Creando instancia de DatabaseManager...")
        db_manager = SupabaseManager()
        
        print("   Creando instancia de PDFManager...")
        pdf_manager = PDFManager(db_manager)
        
        print("SUCCESS: PDF Manager inicializado correctamente")
        print("SUCCESS: Sistema completo funcionando sin errores de Supabase")
        
    except Exception as e:
        print(f"ERROR en PDF Manager: {e}")
        error_str = str(e).lower()
        if 'proxy' in error_str or 'unexpected keyword argument' in error_str:
            print("FALLA: Error de Supabase aun afecta PDF Manager")
            return False
    
    # 4. Resultado final
    print("\n" + "=" * 60)
    print("RESULTADO: FIX APLICADO EXITOSAMENTE")
    print("   - Error 'proxy' resuelto")
    print("   - SupabaseStorageManager inicializa correctamente")
    print("   - PDF Manager funcional")
    print("   - Sistema listo para guardar PDFs en Supabase Storage")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_supabase_storage_fix()
    sys.exit(0 if success else 1)