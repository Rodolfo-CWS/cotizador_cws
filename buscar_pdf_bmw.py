#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscar específicamente el PDF de BMW-CWS-CM-001-R1-GROW
"""

def buscar_pdf_bmw():
    print("BUSCANDO PDF BMW-CWS-CM-001-R1-GROW")
    print("=" * 50)
    
    try:
        # Importar managers
        from supabase_storage_manager import SupabaseStorageManager
        from pdf_manager import PDFManager
        from supabase_manager import SupabaseManager
        
        # Inicializar
        db_manager = SupabaseManager()
        pdf_manager = PDFManager(db_manager)
        storage = SupabaseStorageManager()
        
        numero_buscar = "BMW-CWS-CM-001-R1-GROW"
        
        # 1. Buscar en Supabase Storage directamente
        print("\n1. BUSCANDO EN SUPABASE STORAGE...")
        pdfs_storage = storage.listar_pdfs()
        print(f"Total PDFs en storage: {len(pdfs_storage.get('archivos', []))}")
        
        bmw_encontrado = False
        for pdf in pdfs_storage.get('archivos', []):
            nombre = pdf.get('name', '')
            print(f"  - {nombre}")
            if 'BMW' in nombre.upper():
                bmw_encontrado = True
                print(f"    *** ENCONTRADO BMW PDF: {nombre}")
                print(f"        URL: {pdf.get('url', 'N/A')}")
        
        if not bmw_encontrado:
            print("  *** NO se encontró PDF de BMW en Supabase Storage")
        
        # 2. Buscar usando PDF Manager
        print("\n2. BUSCANDO CON PDF MANAGER...")
        try:
            resultado_pdf = pdf_manager.obtener_pdf(numero_buscar)
            if resultado_pdf.get("encontrado"):
                print(f"OK PDF encontrado por PDF Manager:")
                print(f"  Tipo: {resultado_pdf.get('tipo', 'N/A')}")
                print(f"  URL: {resultado_pdf.get('url_directa', 'N/A')}")
                print(f"  Ruta: {resultado_pdf.get('ruta_completa', 'N/A')}")
            else:
                print(f"ERROR PDF Manager no encontró: {numero_buscar}")
                print(f"  Error: {resultado_pdf.get('error', 'Sin error específico')}")
        except Exception as e:
            print(f"ERROR en PDF Manager: {e}")
        
        # 3. Verificar cotización en base de datos
        print("\n3. VERIFICANDO COTIZACION EN BD...")
        try:
            cotizacion = db_manager.obtener_cotizacion(numero_buscar)
            if cotizacion.get("encontrado"):
                print("OK Cotización encontrada en BD")
                item = cotizacion.get("item", {})
                print(f"  Cliente: {item.get('datosGenerales', {}).get('cliente', 'N/A')}")
                print(f"  Fecha: {item.get('fecha', 'N/A')}")
            else:
                print("ERROR Cotización no encontrada en BD")
        except Exception as e:
            print(f"ERROR verificando cotización: {e}")
            
        # 4. Buscar PDFs por query
        print("\n4. BUSQUEDA POR QUERY BMW...")
        try:
            busqueda_pdfs = pdf_manager.buscar_pdfs("BMW", 1, 10)
            total = busqueda_pdfs.get("total", 0)
            resultados = busqueda_pdfs.get("resultados", [])
            print(f"Resultados de búsqueda BMW: {total}")
            for pdf in resultados[:5]:  # Mostrar solo primeros 5
                print(f"  - {pdf.get('nombre_archivo', 'N/A')}")
                print(f"    Cliente: {pdf.get('cliente', 'N/A')}")
                print(f"    URL: {pdf.get('url_directa', 'N/A')}")
        except Exception as e:
            print(f"ERROR en búsqueda de PDFs: {e}")
            
        print("\n" + "=" * 50)
        print("BUSQUEDA COMPLETADA")
        
    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    buscar_pdf_bmw()