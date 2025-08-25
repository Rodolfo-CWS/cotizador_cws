#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico del PDF Manager después de migración a Supabase Storage
"""

import sys
import os
from pathlib import Path

def diagnosticar_pdf_manager():
    """Diagnosticar el estado del PDF Manager"""
    print("DIAGNOSTICO DEL PDF MANAGER POST-MIGRACION")
    print("=" * 60)
    
    try:
        # 1. Verificar importación de SupabaseStorageManager
        print("\n1. VERIFICANDO IMPORTACIONES...")
        try:
            from supabase_storage_manager import SupabaseStorageManager
            print("OK SupabaseStorageManager importado correctamente")
        except Exception as e:
            print(f"ERROR importando SupabaseStorageManager: {e}")
            return False
            
        try:
            from pdf_manager import PDFManager
            print("OK PDFManager importado correctamente")
        except Exception as e:
            print(f"ERROR importando PDFManager: {e}")
            return False
            
        # 2. Verificar inicialización de SupabaseStorageManager
        print("\n2. VERIFICANDO SUPABASE STORAGE MANAGER...")
        try:
            storage_manager = SupabaseStorageManager()
            print("OK SupabaseStorageManager creado")
            
            if storage_manager.is_available():
                print("OK SupabaseStorageManager esta disponible")
                
                # Obtener estadísticas
                stats = storage_manager.obtener_estadisticas()
                if "error" not in stats:
                    print(f"OK Estadisticas: {stats}")
                else:
                    print(f"WARNING Error en estadisticas: {stats['error']}")
            else:
                print("ERROR SupabaseStorageManager NO esta disponible")
                
        except Exception as e:
            print(f"ERROR inicializando SupabaseStorageManager: {e}")
            return False
            
        # 3. Verificar inicialización completa del PDFManager
        print("\n3. VERIFICANDO PDF MANAGER COMPLETO...")
        try:
            from supabase_manager import SupabaseManager
            db_manager = SupabaseManager()
            
            pdf_manager = PDFManager(db_manager)
            print("OK PDFManager inicializado correctamente")
            
            # Verificar componentes internos
            print(f"OK Supabase Storage disponible: {pdf_manager.supabase_storage_disponible}")
            print(f"OK Google Drive disponible: {pdf_manager.drive_client.is_available()}")
            print(f"OK Base PDF path: {pdf_manager.base_pdf_path}")
            
        except Exception as e:
            print(f"ERROR inicializando PDFManager completo: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        # 4. Test de generación de PDF simple
        print("\n4. TEST DE GENERACION DE PDF...")
        try:
            # Datos de prueba
            datos_test = {
                'datosGenerales': {
                    'numeroCotizacion': 'TEST-DIAG-001-R1-DEMO',
                    'cliente': 'TEST DIAGNOSTICO',
                    'vendedor': 'SISTEMA',
                    'proyecto': 'DIAGNOSTICO'
                },
                'items': [
                    {'descripcion': 'Item de prueba', 'cantidad': 1, 'precio': 100}
                ]
            }
            
            # Generar PDF usando ReportLab
            try:
                from app import generar_pdf_reportlab
                pdf_data = generar_pdf_reportlab(datos_test)
                print(f"OK PDF generado correctamente: {len(pdf_data)} bytes")
                
                # Test de almacenamiento
                resultado = pdf_manager.almacenar_pdf_nuevo(pdf_data, datos_test)
                if resultado["success"]:
                    print("OK PDF almacenado correctamente")
                    print(f"   Detalles: {resultado['mensaje']}")
                else:
                    print(f"ERROR almacenando PDF: {resultado.get('error', 'Error desconocido')}")
                    
            except Exception as pdf_error:
                print(f"ERROR en generacion/almacenamiento de PDF: {pdf_error}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"ERROR en test de PDF: {e}")
            
        print("\n" + "=" * 60)
        print("DIAGNOSTICO COMPLETADO")
        return True
        
    except Exception as e:
        print(f"ERROR GENERAL EN DIAGNOSTICO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    diagnosticar_pdf_manager()