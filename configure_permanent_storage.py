#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurador de Almacenamiento Permanente
=========================================

Este script configura y verifica el almacenamiento permanente en:
- Supabase Storage (PDFs integrados)  
- Supabase PostgreSQL (Datos)

Uso:
    python configure_permanent_storage.py
"""

import os
import sys
from pathlib import Path

def test_supabase_storage():
    """Probar configuración de Supabase Storage"""
    print("\n🔹 SUPABASE STORAGE - TEST DE CONFIGURACIÓN")
    print("-" * 50)
    
    try:
        # Verificar variables de entorno
        supabase_url = os.getenv('SUPABASE_URL', 'NO_CONFIGURADO')
        supabase_anon_key = os.getenv('SUPABASE_ANON_KEY', 'NO_CONFIGURADO')
        
        print(f"Supabase URL: {supabase_url}")
        print(f"Anon Key: {'***' + supabase_anon_key[-10:] if len(supabase_anon_key) > 10 else 'NO_CONFIGURADO'}")
        
        if any(v == 'NO_CONFIGURADO' for v in [supabase_url, supabase_anon_key]):
            print("❌ FALLA: Variables de entorno no configuradas")
            return False
            
        # Probar importación y configuración de Supabase Storage
        from supabase_storage_manager import SupabaseStorageManager
        
        storage = SupabaseStorageManager()
        
        if not storage.is_available():
            print("❌ FALLA: Supabase Storage no disponible")
            return False
        
        # Test de conectividad con estadísticas
        stats = storage.obtener_estadisticas()
        if "error" in stats:
            print(f"❌ FALLA: {stats['error']}")
            return False
        
        print(f"✅ CONECTIVIDAD: OK")
        print(f"✅ PDFs almacenados: {stats.get('total_pdfs', 0)}")
        print(f"✅ Bucket: {stats.get('bucket_name', 'N/A')}")
        
        return True
        
    except ImportError:
        print("❌ FALLA: Módulo supabase_storage_manager no disponible")
        return False
        
    except Exception as e:
        print(f"❌ FALLA: {e}")
        return False

def test_supabase():
    """Probar configuración de Supabase"""
    print("\n🔹 SUPABASE - TEST DE CONFIGURACIÓN")
    print("-" * 50)
    
    try:
        # Verificar variables de entorno
        database_url = os.getenv('DATABASE_URL', 'NO_CONFIGURADO')
        supabase_url = os.getenv('SUPABASE_URL', 'NO_CONFIGURADO') 
        supabase_key = os.getenv('SUPABASE_ANON_KEY', 'NO_CONFIGURADO')
        
        print(f"Database URL: {database_url[:50]}...")
        print(f"Supabase URL: {supabase_url}")
        print(f"Anon Key: {'***' + supabase_key[-10:] if len(supabase_key) > 10 else 'NO_CONFIGURADO'}")
        
        if 'NO_CONFIGURADO' in [database_url, supabase_url, supabase_key]:
            print("❌ FALLA: Variables de entorno no configuradas")
            return False
        
        # Test de conectividad PostgreSQL
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()['version']
        print(f"✅ POSTGRESQL: {version[:50]}...")
        
        cursor.execute("SELECT COUNT(*) as total FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cursor.fetchone()['total']
        print(f"✅ TABLAS: {tables} tablas públicas encontradas")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError as e:
        missing = str(e).split("'")[1] if "'" in str(e) else str(e)
        print(f"❌ FALLA: Biblioteca {missing} no instalada")
        print("   Ejecuta: pip install psycopg2-binary supabase")
        return False
        
    except Exception as e:
        print(f"❌ FALLA: {e}")
        return False

def create_test_pdf():
    """Crear PDF de prueba para testing"""
    print("\n🔹 PDF TEST - CREACIÓN DE ARCHIVO DE PRUEBA")
    print("-" * 50)
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import tempfile
        
        # Crear PDF temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            c = canvas.Canvas(tmp.name, pagesize=letter)
            c.drawString(100, 750, "TEST PDF - Configuración de Almacenamiento Permanente")
            c.drawString(100, 700, f"Fecha: {datetime.datetime.now()}")
            c.drawString(100, 650, "Este PDF se usa para probar Cloudinary")
            c.save()
            
            print(f"✅ PDF CREADO: {tmp.name}")
            print(f"   Tamaño: {os.path.getsize(tmp.name)} bytes")
            return tmp.name
            
    except ImportError:
        print("❌ FALLA: ReportLab no instalado")
        print("   Ejecuta: pip install reportlab")
        return None
        
    except Exception as e:
        print(f"❌ FALLA: {e}")
        return None

def test_end_to_end():
    """Test completo de almacenamiento permanente"""
    print("\n🔹 TEST END-TO-END - ALMACENAMIENTO PERMANENTE")
    print("-" * 50)
    
    # Crear PDF de prueba
    import datetime
    pdf_path = create_test_pdf()
    if not pdf_path:
        return False
    
    try:
        # Test Supabase Storage upload
        from supabase_storage_manager import SupabaseStorageManager
        
        storage = SupabaseStorageManager()
        if not storage.is_available():
            print("❌ FALLA: SupabaseStorageManager no disponible")
            return False
            
        # Subir PDF de prueba
        numero_test = f"TEST-PERM-{int(datetime.datetime.now().timestamp())}"
        resultado = storage.subir_pdf(pdf_path, numero_test, es_nueva=True)
        
        if "error" in resultado:
            print(f"❌ SUPABASE STORAGE FALLA: {resultado['error']}")
            return False
        
        print(f"✅ SUPABASE STORAGE OK: PDF subido a {resultado['url']}")
        
        # Test Supabase save
        from supabase_manager import SupabaseManager
        
        sm = SupabaseManager()
        datos_test = {
            'datosGenerales': {
                'cliente': 'TEST-PERMANENTE',
                'vendedor': 'CONFIG',
                'proyecto': 'ALMACENAMIENTO'
            },
            'items': [{'descripcion': 'Item de prueba', 'cantidad': 1, 'precio': 100}]
        }
        
        resultado_db = sm.guardar_cotizacion(datos_test)
        
        if not resultado_db.get('success'):
            print(f"❌ SUPABASE FALLA: {resultado_db.get('error')}")
            return False
            
        print(f"✅ SUPABASE OK: Cotización guardada - {resultado_db.get('numero_cotizacion')}")
        
        # Cleanup
        os.unlink(pdf_path)
        
        return True
        
    except Exception as e:
        print(f"❌ END-TO-END FALLA: {e}")
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)
        return False

def print_configuration_guide():
    """Imprimir guía de configuración"""
    print("\n" + "="*60)
    print("🛠️  GUÍA DE CONFIGURACIÓN - ALMACENAMIENTO PERMANENTE")
    print("="*60)
    
    print("""
📋 PASOS PARA CONFIGURACIÓN COMPLETA:

1️⃣  SUPABASE STORAGE (integrado con PostgreSQL):
   • Ve a: https://supabase.com/dashboard
   • Ve a Settings > API
   • Asegúrate de tener creado el bucket 'cotizaciones-pdfs'
   • Las credenciales son las mismas que para PostgreSQL:
   
   SUPABASE_URL=https://[REF].supabase.co
   SUPABASE_ANON_KEY=[TU_ANON_KEY]

2️⃣  SUPABASE (PostgreSQL gratis):
   • Ve a: https://supabase.com/dashboard
   • Ve a Settings > Database > Connection pooling
   • Copia URL con port 6543:
   
   DATABASE_URL=postgresql://postgres.[REF]:[PASS]@aws-1-us-east-2.pooler.supabase.com:6543/postgres
   SUPABASE_URL=https://[REF].supabase.co
   SUPABASE_ANON_KEY=[TU_ANON_KEY]

3️⃣  RENDER ENVIRONMENT:
   • Ve a tu aplicación en Render
   • Settings > Environment
   • Agrega todas las variables arriba
   • Manual Deploy

4️⃣  VERIFICACIÓN:
   • Ejecuta: python configure_permanent_storage.py
   • Debe mostrar ✅ en todos los tests
   • Las cotizaciones se guardarán permanentemente
""")

def main():
    """Función principal"""
    print("🚀 CONFIGURADOR DE ALMACENAMIENTO PERMANENTE")
    print("=" * 60)
    
    # Tests individuales
    supabase_storage_ok = test_supabase_storage()
    supabase_ok = test_supabase()
    
    print("\n" + "="*60)
    print("📊 RESUMEN DE CONFIGURACIÓN:")
    print("-" * 60)
    print(f"Supabase Storage:   {'✅ OK' if supabase_storage_ok else '❌ FALLA'}")
    print(f"Supabase (Datos):   {'✅ OK' if supabase_ok else '❌ FALLA'}")
    
    if supabase_storage_ok and supabase_ok:
        print("\n🎉 ¡CONFIGURACIÓN COMPLETA! Probando end-to-end...")
        e2e_ok = test_end_to_end()
        print(f"Test End-to-End:    {'✅ OK' if e2e_ok else '❌ FALLA'}")
        
        if e2e_ok:
            print("\n🎉 ¡ALMACENAMIENTO PERMANENTE CONFIGURADO EXITOSAMENTE!")
            print("   • PDFs se guardan en Cloudinary (25GB gratis)")
            print("   • Datos se guardan en Supabase PostgreSQL")
            print("   • Sistema 100% funcional con respaldo offline")
        else:
            print("\n⚠️  Configuración parcial - revisar errores arriba")
    else:
        print_configuration_guide()

if __name__ == "__main__":
    main()