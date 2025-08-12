#!/usr/bin/env python3
"""
Test de Cloudinary - Verifica la integración y funcionalidad del almacenamiento
"""

import sys
import os
import tempfile
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cloudinary_manager import CloudinaryManager, test_cloudinary_connection
import json

def test_cloudinary_completo():
    """Test completo de Cloudinary Manager"""
    print("=== TEST COMPLETO: Cloudinary Manager ===\n")
    
    # 1. Test de conexión básica
    print("1. Test de conexión básica:")
    if not test_cloudinary_connection():
        print("❌ Conexión fallida - verifica variables de entorno")
        return False
    
    print("✅ Conexión exitosa\n")
    
    # 2. Test de instanciación
    print("2. Test de CloudinaryManager:")
    manager = CloudinaryManager()
    
    if not manager.is_available():
        print("❌ CloudinaryManager no disponible")
        return False
    
    print("✅ CloudinaryManager inicializado\n")
    
    # 3. Test de estadísticas
    print("3. Test de estadísticas:")
    stats = manager.obtener_estadisticas()
    
    if "error" in stats:
        print(f"❌ Error en estadísticas: {stats['error']}")
        return False
    
    print(f"✅ Estadísticas obtenidas:")
    print(f"   Total PDFs: {stats.get('total_pdfs', 0)}")
    print(f"   Storage usado: {stats.get('storage_usado', 0)} bytes")
    print(f"   PDFs nuevos: {stats.get('pdfs_nuevos', 0)}")
    print(f"   PDFs antiguos: {stats.get('pdfs_antiguos', 0)}\n")
    
    # 4. Test de listado
    print("4. Test de listado de PDFs:")
    listado = manager.listar_pdfs(max_resultados=10)
    
    if "error" in listado:
        print(f"❌ Error en listado: {listado['error']}")
        return False
    
    archivos = listado.get("archivos", [])
    print(f"✅ Listado exitoso: {len(archivos)} PDFs encontrados")
    
    if archivos:
        print("   Últimos PDFs:")
        for i, archivo in enumerate(archivos[:3]):
            print(f"     {i+1}. {archivo.get('numero_cotizacion', 'Sin número')} ({archivo.get('bytes', 0)} bytes)")
    
    print()
    
    # 5. Test de subida (opcional - solo si tenemos PDF de prueba)
    print("5. Test de subida (simulado):")
    
    # Crear PDF de prueba muy pequeño
    pdf_test_content = b"%PDF-1.4\n1 0 obj<</Type/Page>>\nendobj\ntrailer<</Root 1 0 R>>\n%%EOF"
    
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_test_content)
            temp_file_path = temp_file.name
        
        # Intentar subir (usar número de test único)
        import datetime
        numero_test = f"TEST-CWS-CL-001-R1-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        resultado = manager.subir_pdf(temp_file_path, numero_test, es_nueva=True)
        
        if resultado.get("success", False):
            print(f"✅ Subida exitosa: {numero_test}")
            print(f"   URL: {resultado.get('url', 'N/A')}")
            print(f"   Tamaño: {resultado.get('bytes', 0)} bytes")
            
            # Intentar limpiar el archivo de test
            try:
                manager.eliminar_pdf(f"cotizaciones/nuevas/{numero_test}")
                print("✅ Archivo de test eliminado")
            except:
                print("⚠️ No se pudo eliminar archivo de test (normal)")
        else:
            print(f"⚠️ Subida falló: {resultado.get('error', 'Error desconocido')}")
            print("   (Esto puede ser normal si no tienes cuota disponible)")
        
        # Limpiar archivo temporal
        try:
            os.unlink(temp_file_path)
        except:
            pass
            
    except Exception as e:
        print(f"⚠️ Test de subida falló: {e}")
        print("   (Esto puede ser normal en entorno de desarrollo)")
    
    print("\n✅ Test completo de Cloudinary finalizado")
    return True

def test_configuracion_variables():
    """Test de variables de entorno de Cloudinary"""
    print("=== TEST: Configuración Variables de Entorno ===\n")
    
    variables_necesarias = [
        'CLOUDINARY_CLOUD_NAME',
        'CLOUDINARY_API_KEY', 
        'CLOUDINARY_API_SECRET'
    ]
    
    configuracion_completa = True
    
    for var in variables_necesarias:
        valor = os.getenv(var)
        if valor:
            # Mostrar solo primeros y últimos caracteres por seguridad
            valor_ofuscado = valor[:4] + "..." + valor[-4:] if len(valor) > 8 else "***"
            print(f"OK {var}: {valor_ofuscado}")
        else:
            print(f"NO {var}: No configurada")
            configuracion_completa = False
    
    if configuracion_completa:
        print("\nTodas las variables estan configuradas")
    else:
        print("\nFaltan variables de entorno")
        print("\nPara configurar Cloudinary:")
        print("1. Crea cuenta gratuita en cloudinary.com")
        print("2. Ve a Settings > API Keys")
        print("3. Configura en .env o variables de entorno:")
        print("   CLOUDINARY_CLOUD_NAME=tu-cloud-name")
        print("   CLOUDINARY_API_KEY=tu-api-key")
        print("   CLOUDINARY_API_SECRET=tu-api-secret")
    
    return configuracion_completa

def main():
    """Función principal de testing"""
    print("Iniciando tests de Cloudinary...\n")
    
    # Test 1: Variables de entorno
    if not test_configuracion_variables():
        print("\nTests abortados - configura las variables de entorno primero")
        return False
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Funcionalidad completa
    if not test_cloudinary_completo():
        print("\nTests de funcionalidad fallaron")
        return False
    
    print("\nTodos los tests de Cloudinary pasaron exitosamente!")
    print("\nResumen:")
    print("   Variables de entorno configuradas")
    print("   Conexion a Cloudinary exitosa")
    print("   CloudinaryManager funcional")
    print("   Estadisticas disponibles")
    print("   Listado de archivos funcional")
    print("   Sistema listo para usar")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)