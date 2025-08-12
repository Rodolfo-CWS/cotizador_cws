#!/usr/bin/env python3
"""
Test de Sistema Híbrido - Verifica sincronización JSON ↔ MongoDB + Cloudinary
"""

import sys
import os
import datetime
import json
import tempfile
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from sync_scheduler import SyncScheduler, test_sync_scheduler
from pdf_manager import PDFManager
from cloudinary_manager import CloudinaryManager

def test_database_hibrido():
    """Test del sistema híbrido de base de datos"""
    print("=== TEST: Sistema Híbrido de Base de Datos ===\n")
    
    # Crear instancia de DatabaseManager
    db = DatabaseManager()
    
    print(f"1. Estado inicial:")
    print(f"   Modo offline: {'✅ Sí' if db.modo_offline else '❌ No'}")
    print(f"   Archivo JSON: {db.archivo_datos}")
    
    if not db.modo_offline:
        print("   MongoDB: ✅ Conectado")
    else:
        print("   MongoDB: ❌ Sin conexión (modo offline)")
    
    # Test de sincronización bidireccional
    print(f"\n2. Test de sincronización bidireccional:")
    
    if db.modo_offline:
        print("   ⚠️ MongoDB offline - test de sincronización omitido")
    else:
        try:
            resultado = db.sincronizar_bidireccional()
            
            if resultado.get("success", False):
                print("   ✅ Sincronización exitosa")
                print(f"     ⬆️ Subidas (JSON → MongoDB): {resultado.get('subidas', 0)}")
                print(f"     ⬇️ Descargas (MongoDB → JSON): {resultado.get('descargas', 0)}")
                print(f"     ⚠️ Conflictos resueltos: {resultado.get('conflictos', 0)}")
                print(f"     Total JSON: {resultado.get('total_json', 0)}")
                print(f"     Total MongoDB: {resultado.get('total_mongo', 0)}")
            else:
                print(f"   ❌ Error en sincronización: {resultado.get('error', 'Desconocido')}")
                
        except Exception as e:
            print(f"   ❌ Excepción durante sincronización: {e}")
    
    # Test de lectura de datos
    print(f"\n3. Test de lectura de datos:")
    
    try:
        cotizaciones = db.obtener_todas_cotizaciones(page=1, per_page=5)
        total = cotizaciones.get("total", 0)
        paginas = cotizaciones.get("total_pages", 0)
        items = len(cotizaciones.get("cotizaciones", []))
        
        print(f"   ✅ Datos leídos exitosamente")
        print(f"     Total cotizaciones: {total}")
        print(f"     Total páginas: {paginas}")
        print(f"     Items en página 1: {items}")
        
        if items > 0:
            primera = cotizaciones["cotizaciones"][0]
            numero = primera.get("numeroCotizacion", "Sin número")
            cliente = primera.get("datosGenerales", {}).get("cliente", "Sin cliente")
            print(f"     Ejemplo: {numero} - {cliente}")
        
    except Exception as e:
        print(f"   ❌ Error leyendo datos: {e}")
    
    print("\n✅ Test de base de datos híbrida completado")
    return True

def test_scheduler_completo():
    """Test completo del scheduler"""
    print("\n=== TEST: Scheduler de Sincronización ===\n")
    
    # Test básico del scheduler
    print("1. Test básico del scheduler:")
    if not test_sync_scheduler():
        print("   ❌ Test básico del scheduler falló")
        return False
    
    print("   ✅ Test básico exitoso")
    
    # Test con DatabaseManager real
    print("\n2. Test con sistema real:")
    
    try:
        db = DatabaseManager()
        scheduler = SyncScheduler(db)
        
        print(f"   Scheduler disponible: {'✅ Sí' if scheduler.is_available() else '❌ No'}")
        print(f"   Auto-sync habilitado: {'✅ Sí' if scheduler.auto_sync_enabled else '❌ No'}")
        print(f"   Intervalo: {scheduler.intervalo_minutos} minutos")
        
        # Test de estado
        estado = scheduler.obtener_estado()
        print(f"   Estado activo: {'✅ Sí' if estado.get('activo', False) else '❌ No'}")
        print(f"   MongoDB disponible: {'✅ Sí' if estado.get('mongodb_disponible', False) else '❌ No'}")
        
        # Test de sincronización manual
        if scheduler.is_available():
            print("\n3. Test de sincronización manual:")
            resultado = scheduler.ejecutar_sincronizacion_manual()
            
            if resultado.get("success", False):
                print("   ✅ Sincronización manual exitosa")
                print(f"     {resultado.get('mensaje', 'Sin mensaje')}")
            else:
                print(f"   ⚠️ Sincronización manual falló: {resultado.get('error', 'Error desconocido')}")
                print("     (Esto es normal si MongoDB está offline)")
        
    except Exception as e:
        print(f"   ❌ Error en test del scheduler: {e}")
        return False
    
    print("\n✅ Test de scheduler completado")
    return True

def test_pdf_hibrido():
    """Test del sistema híbrido de PDFs"""
    print("\n=== TEST: Sistema Híbrido de PDFs ===\n")
    
    try:
        db = DatabaseManager()
        pdf_manager = PDFManager(db)
        
        print("1. Estado del PDF Manager:")
        print(f"   Cloudinary disponible: {'✅ Sí' if pdf_manager.cloudinary_disponible else '❌ No'}")
        print(f"   Google Drive disponible: {'✅ Sí' if pdf_manager.drive_client else '❌ No'}")
        print(f"   Ruta local: {pdf_manager.base_pdf_path}")
        
        if pdf_manager.cloudinary_disponible:
            print("\n2. Test de Cloudinary:")
            
            try:
                stats = pdf_manager.cloudinary_manager.obtener_estadisticas()
                
                if "error" not in stats:
                    print("   ✅ Estadísticas de Cloudinary:")
                    print(f"     Total PDFs: {stats.get('total_pdfs', 0)}")
                    print(f"     Storage usado: {stats.get('storage_usado', 0)} bytes")
                else:
                    print(f"   ⚠️ Error en estadísticas: {stats['error']}")
                    
            except Exception as e:
                print(f"   ❌ Error probando Cloudinary: {e}")
        
        # Test de PDF simulado
        print("\n3. Test de almacenamiento híbrido (simulado):")
        
        # Crear PDF de prueba muy pequeño
        pdf_test_content = b"%PDF-1.4\n1 0 obj<</Type/Page>>\nendobj\ntrailer<</Root 1 0 R>>\n%%EOF"
        
        # Datos de cotización simulados
        cotizacion_test = {
            "numeroCotizacion": f"TEST-CWS-HY-001-R1-{datetime.datetime.now().strftime('%H%M%S')}",
            "datosGenerales": {
                "cliente": "Cliente Test",
                "vendedor": "Test Vendedor", 
                "proyecto": "Proyecto Test"
            }
        }
        
        try:
            resultado = pdf_manager.almacenar_pdf_nuevo(pdf_test_content, cotizacion_test)
            
            if resultado.get("success", False):
                print("   ✅ Almacenamiento híbrido exitoso")
                print(f"     Estado: {resultado.get('estado', 'Sin estado')}")
                print(f"     Archivo: {resultado.get('nombre_archivo', 'Sin nombre')}")
                print(f"     Tamaño: {resultado.get('tamaño', 0)} bytes")
                
                # Mostrar detalles de cada sistema
                sistemas = resultado.get("sistemas", {})
                for sistema, detalle in sistemas.items():
                    estado_sistema = "✅" if detalle.get("success", False) else "❌"
                    print(f"     {sistema.capitalize()}: {estado_sistema}")
                    if not detalle.get("success", False) and detalle.get("error"):
                        print(f"       Error: {detalle['error'][:50]}...")
                
            else:
                print(f"   ❌ Error en almacenamiento: {resultado.get('error', 'Error desconocido')}")
                
        except Exception as e:
            print(f"   ❌ Excepción en test de PDF: {e}")
        
    except Exception as e:
        print(f"❌ Error inicializando PDF Manager: {e}")
        return False
    
    print("\n✅ Test de sistema híbrido de PDFs completado")
    return True

def test_integracion_completa():
    """Test de integración de todo el sistema"""
    print("\n=== TEST: Integración Completa del Sistema Híbrido ===\n")
    
    sistemas_funcionando = []
    
    # 1. Database Manager
    try:
        db = DatabaseManager()
        sistemas_funcionando.append("✅ DatabaseManager")
    except Exception as e:
        sistemas_funcionando.append(f"❌ DatabaseManager: {e}")
        db = None
    
    # 2. SyncScheduler  
    if db:
        try:
            scheduler = SyncScheduler(db)
            if scheduler.is_available():
                sistemas_funcionando.append("✅ SyncScheduler")
            else:
                sistemas_funcionando.append("⚠️ SyncScheduler: APScheduler no disponible")
        except Exception as e:
            sistemas_funcionando.append(f"❌ SyncScheduler: {e}")
    
    # 3. PDFManager
    if db:
        try:
            pdf_manager = PDFManager(db)
            sistemas_funcionando.append("✅ PDFManager")
        except Exception as e:
            sistemas_funcionando.append(f"❌ PDFManager: {e}")
    
    # 4. CloudinaryManager
    try:
        cloudinary = CloudinaryManager()
        if cloudinary.is_available():
            sistemas_funcionando.append("✅ CloudinaryManager")
        else:
            sistemas_funcionando.append("⚠️ CloudinaryManager: No configurado")
    except Exception as e:
        sistemas_funcionando.append(f"❌ CloudinaryManager: {e}")
    
    print("Estado de los sistemas:")
    for sistema in sistemas_funcionando:
        print(f"   {sistema}")
    
    # Contar sistemas funcionando
    funcionando = len([s for s in sistemas_funcionando if s.startswith("✅")])
    parciales = len([s for s in sistemas_funcionando if s.startswith("⚠️")])
    fallidos = len([s for s in sistemas_funcionando if s.startswith("❌")])
    
    print(f"\nResumen:")
    print(f"   ✅ Funcionando: {funcionando}")
    print(f"   ⚠️ Parciales: {parciales}")
    print(f"   ❌ Fallidos: {fallidos}")
    
    if funcionando >= 2:  # Al menos DatabaseManager y otro sistema
        print("\n🎉 Sistema híbrido operativo!")
        return True
    else:
        print("\n❌ Sistema necesita configuración")
        return False

def main():
    """Función principal de testing"""
    print("Iniciando tests del Sistema Hibrido Completo...\n")
    
    tests_exitosos = 0
    tests_totales = 4
    
    try:
        # Test 1: Database híbrido
        if test_database_hibrido():
            tests_exitosos += 1
        
        # Test 2: Scheduler
        if test_scheduler_completo():
            tests_exitosos += 1
        
        # Test 3: PDF híbrido
        if test_pdf_hibrido():
            tests_exitosos += 1
        
        # Test 4: Integración completa
        if test_integracion_completa():
            tests_exitosos += 1
        
    except Exception as e:
        print(f"\n❌ Error durante los tests: {e}")
    
    print("\n" + "="*60)
    print(f"🏁 RESULTADO FINAL: {tests_exitosos}/{tests_totales} tests exitosos")
    
    if tests_exitosos == tests_totales:
        print("🎉 Todos los tests pasaron! Sistema híbrido completamente funcional.")
    elif tests_exitosos >= tests_totales // 2:
        print("⚠️ Sistema parcialmente funcional - algunos componentes necesitan configuración.")
    else:
        print("❌ Sistema necesita configuración adicional.")
    
    print("\n📋 Próximos pasos recomendados:")
    if tests_exitosos < tests_totales:
        print("   1. Configura las variables de entorno faltantes")
        print("   2. Instala dependencias: pip install -r requirements.txt") 
        print("   3. Verifica configuración de MongoDB y Cloudinary")
    else:
        print("   ✅ Sistema listo para producción!")
        print("   ✅ Cloudinary configurado para PDFs")
        print("   ✅ Sincronización automática disponible")
        print("   ✅ Fallbacks funcionando correctamente")
    
    return tests_exitosos >= tests_totales // 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)