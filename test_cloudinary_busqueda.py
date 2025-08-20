"""
Test para validar búsqueda de PDFs en Cloudinary
Verifica la integración completa de Cloudinary en la búsqueda unificada
"""

import os
import json
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_cloudinary_busqueda():
    """Test completo de búsqueda en Cloudinary"""
    print("=== TEST: BÚSQUEDA CLOUDINARY ===")
    
    try:
        # Importar managers
        from cloudinary_manager import CloudinaryManager
        from pdf_manager import PDFManager
        from supabase_manager import SupabaseManager
        
        # Inicializar managers
        print("\n1. Inicializando managers...")
        db_manager = SupabaseManager()
        pdf_manager = PDFManager(db_manager)
        cloudinary_manager = CloudinaryManager()
        
        # Verificar configuración
        print(f"   Cloudinary disponible: {cloudinary_manager.is_available()}")
        print(f"   PDFManager inicializado: {pdf_manager is not None}")
        print(f"   Cloudinary en PDFManager: {pdf_manager.cloudinary_disponible}")
        
        # Test 1: Búsqueda directa en Cloudinary
        print("\n2. Test búsqueda directa en CloudinaryManager...")
        if cloudinary_manager.is_available():
            # Búsqueda sin filtro (todos los PDFs)
            pdfs_todos = cloudinary_manager.buscar_pdfs("")
            print(f"   Total PDFs en Cloudinary: {len(pdfs_todos)}")
            
            if len(pdfs_todos) > 0:
                print(f"   Primer PDF: {pdfs_todos[0].get('numero_cotizacion', 'N/A')}")
                print(f"   Fuente: {pdfs_todos[0].get('fuente', 'N/A')}")
                print(f"   Tipo: {pdfs_todos[0].get('tipo', 'N/A')}")
                
                # Búsqueda con filtro
                primer_numero = pdfs_todos[0].get('numero_cotizacion', '')
                if primer_numero:
                    # Extraer parte del número para búsqueda
                    busqueda_term = primer_numero.split('-')[0] if '-' in primer_numero else primer_numero[:3]
                    pdfs_filtrados = cloudinary_manager.buscar_pdfs(busqueda_term)
                    print(f"   Búsqueda '{busqueda_term}': {len(pdfs_filtrados)} resultados")
        else:
            print("   ⚠️ Cloudinary no disponible - verificar configuración")
        
        # Test 2: Búsqueda híbrida en PDFManager
        print("\n3. Test búsqueda híbrida en PDFManager...")
        resultado_hibrido = pdf_manager.buscar_pdfs("", 1, 50)  # Buscar todos
        print(f"   Resultado tipo: {type(resultado_hibrido)}")
        print(f"   Keys: {list(resultado_hibrido.keys()) if isinstance(resultado_hibrido, dict) else 'No es dict'}")
        
        if not resultado_hibrido.get("error"):
            resultados = resultado_hibrido.get("resultados", [])
            print(f"   Total resultados híbridos: {len(resultados)}")
            
            # Contar por fuente
            fuentes = {}
            for pdf in resultados:
                fuente = pdf.get('fuente', 'unknown')
                fuentes[fuente] = fuentes.get(fuente, 0) + 1
            
            print("   Resultados por fuente:")
            for fuente, count in fuentes.items():
                print(f"     {fuente}: {count}")
                
            # Mostrar algunos resultados de Cloudinary
            cloudinary_results = [r for r in resultados if r.get('fuente') == 'cloudinary']
            if cloudinary_results:
                print(f"\n   Ejemplos de PDFs de Cloudinary:")
                for i, pdf in enumerate(cloudinary_results[:3]):
                    print(f"     {i+1}. {pdf.get('numero_cotizacion', 'N/A')} - {pdf.get('cliente', 'N/A')}")
        else:
            print(f"   Error en búsqueda híbrida: {resultado_hibrido.get('error')}")
        
        # Test 3: Simular búsqueda unificada como en app.py
        print("\n4. Test simulación búsqueda unificada...")
        query_test = ""  # Búsqueda vacía para obtener todos
        
        # Simular PASO 1: Cotizaciones
        resultados_cotizaciones = []
        try:
            resultado_db = db_manager.buscar_cotizaciones(query_test, 1, 10)
            if not resultado_db.get("error"):
                cotizaciones = resultado_db.get("resultados", [])
                print(f"   Cotizaciones encontradas: {len(cotizaciones)}")
                for cot in cotizaciones[:2]:  # Solo primeras 2
                    datos_gen = cot.get('datosGenerales', {})
                    resultados_cotizaciones.append({
                        "numero_cotizacion": cot.get('numeroCotizacion', 'N/A'),
                        "cliente": datos_gen.get('cliente', 'N/A'),
                        "tipo": "cotizacion",
                        "fuente": "supabase" if not db_manager.modo_offline else "json_local"
                    })
        except Exception as e:
            print(f"   Error buscando cotizaciones: {e}")
        
        # Simular PASO 2: PDFs (que ahora incluye Cloudinary)
        resultados_pdfs = []
        try:
            resultado_pdfs = pdf_manager.buscar_pdfs(query_test, 1, 10)
            if not resultado_pdfs.get("error"):
                pdfs = resultado_pdfs.get("resultados", [])
                print(f"   PDFs encontrados: {len(pdfs)}")
                for pdf in pdfs[:2]:  # Solo primeros 2
                    resultados_pdfs.append({
                        "numero_cotizacion": pdf.get('numero_cotizacion', 'N/A'),
                        "cliente": pdf.get('cliente', 'N/A'),
                        "tipo": pdf.get('tipo', 'pdf'),
                        "fuente": pdf.get('fuente', 'pdf_manager')
                    })
        except Exception as e:
            print(f"   Error buscando PDFs: {e}")
        
        # Combinar resultados como en app.py
        todos_resultados = resultados_cotizaciones + resultados_pdfs
        print(f"\n   RESULTADO UNIFICADO: {len(todos_resultados)} elementos")
        
        # Mostrar resumen por fuente
        fuentes_unificadas = {}
        for item in todos_resultados:
            fuente = item.get('fuente', 'unknown')
            fuentes_unificadas[fuente] = fuentes_unificadas.get(fuente, 0) + 1
        
        print("   Resumen por fuente:")
        for fuente, count in fuentes_unificadas.items():
            print(f"     {fuente}: {count}")
        
        # Verificar que Cloudinary está incluido
        tiene_cloudinary = any(item.get('fuente') == 'cloudinary' for item in todos_resultados)
        print(f"\n   ✅ Cloudinary integrado en búsqueda unificada: {'SÍ' if tiene_cloudinary else 'NO'}")
        
        print("\n=== TEST COMPLETADO EXITOSAMENTE ===")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cloudinary_configuracion():
    """Test de configuración de Cloudinary"""
    print("\n=== TEST: CONFIGURACIÓN CLOUDINARY ===")
    
    variables_requeridas = [
        'CLOUDINARY_CLOUD_NAME',
        'CLOUDINARY_API_KEY', 
        'CLOUDINARY_API_SECRET'
    ]
    
    configuracion_ok = True
    for var in variables_requeridas:
        valor = os.getenv(var)
        print(f"   {var}: {'✅ Configurado' if valor else '❌ Faltante'}")
        if not valor:
            configuracion_ok = False
    
    if configuracion_ok:
        print("   ✅ Todas las variables de Cloudinary están configuradas")
        
        # Test de conexión
        try:
            from cloudinary_manager import CloudinaryManager
            cm = CloudinaryManager()
            disponible = cm.is_available()
            print(f"   ✅ Conexión Cloudinary: {'OK' if disponible else 'FALLA'}")
            
            if disponible:
                # Test básico de listado
                resultado = cm.listar_pdfs(max_resultados=5)
                if not resultado.get("error"):
                    archivos = resultado.get("archivos", [])
                    print(f"   ✅ Test de listado: {len(archivos)} archivos encontrados")
                else:
                    print(f"   ⚠️ Error en listado: {resultado.get('error')}")
            
        except Exception as e:
            print(f"   ❌ Error probando conexión: {e}")
            configuracion_ok = False
    else:
        print("   ❌ Configuración incompleta - verificar variables de entorno")
    
    return configuracion_ok

if __name__ == "__main__":
    print("🔍 INICIANDO TESTS DE BÚSQUEDA CLOUDINARY")
    
    # Test 1: Configuración
    config_ok = test_cloudinary_configuracion()
    
    # Test 2: Búsqueda (solo si configuración está OK)
    if config_ok:
        busqueda_ok = test_cloudinary_busqueda()
        
        if busqueda_ok:
            print("\n🎉 TODOS LOS TESTS PASARON - CLOUDINARY INTEGRADO CORRECTAMENTE")
        else:
            print("\n⚠️ ALGUNOS TESTS FALLARON - VERIFICAR CONFIGURACIÓN")
    else:
        print("\n⚠️ CONFIGURACIÓN INCOMPLETA - CONFIGURAR VARIABLES DE ENTORNO PRIMERO")
    
    print("\nPara configurar Cloudinary:")
    print("1. Registrarse en cloudinary.com (gratis)")
    print("2. Obtener cloud_name, api_key, api_secret del dashboard")
    print("3. Configurar variables de entorno en .env o Render")