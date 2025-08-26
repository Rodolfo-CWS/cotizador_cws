#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug específico para obtener_pdf que está devolviendo URL vacía
"""

from pdf_manager import PDFManager
from supabase_manager import SupabaseManager
from supabase_storage_manager import SupabaseStorageManager

def debug_obtener_pdf():
    """Debug del método obtener_pdf"""
    print("=" * 60)
    print("DEBUG: OBTENER_PDF CON URL VACÍA")
    print("=" * 60)
    
    # 1. Obtener un PDF disponible
    print("\n1. OBTENIENDO LISTA DE PDFs:")
    storage = SupabaseStorageManager()
    resultado = storage.listar_pdfs()
    
    if "error" in resultado or len(resultado.get("archivos", [])) == 0:
        print("ERROR: No hay PDFs disponibles")
        return False
    
    archivos = resultado["archivos"]
    print(f"PDFs disponibles: {len(archivos)}")
    
    # Mostrar información de cada PDF
    for i, pdf in enumerate(archivos):
        print(f"   [{i+1}] {pdf.get('numero_cotizacion', 'N/A')} -> URL: {pdf.get('url', 'VACÍA')}")
    
    # 2. Seleccionar primer PDF para prueba
    primer_pdf = archivos[0]
    numero_test = primer_pdf.get("numero_cotizacion", "")
    url_directa = primer_pdf.get("url", "")
    
    print(f"\n2. PDF SELECCIONADO PARA PRUEBA:")
    print(f"   Número: {numero_test}")
    print(f"   URL directa: {url_directa}")
    
    if not url_directa:
        print("   ERROR: URL directa está vacía - este es el problema")
        return False
    
    # 3. Crear PDF Manager y probar obtener_pdf
    print(f"\n3. PROBANDO OBTENER_PDF:")
    db_manager = SupabaseManager()
    pdf_manager = PDFManager(db_manager)
    
    resultado_obtener = pdf_manager.obtener_pdf(numero_test)
    
    print(f"   Resultado obtener_pdf:")
    print(f"   - encontrado: {resultado_obtener.get('encontrado', False)}")
    print(f"   - ruta_completa: '{resultado_obtener.get('ruta_completa', 'VACÍA')}'")
    print(f"   - tipo: {resultado_obtener.get('tipo', 'N/A')}")
    print(f"   - error: {resultado_obtener.get('error', 'Ninguno')}")
    
    if resultado_obtener.get("encontrado", False):
        ruta_completa = resultado_obtener.get("ruta_completa", "")
        if ruta_completa:
            print("   SUCCESS: ruta_completa tiene valor")
            return True
        else:
            print("   ERROR: ruta_completa está vacía")
            return False
    else:
        print("   ERROR: PDF no encontrado por obtener_pdf")
        return False

def debug_buscar_pdfs_method():
    """Debug específico del método buscar_pdfs"""
    print(f"\n4. DEBUG DEL MÉTODO BUSCAR_PDFS:")
    
    storage = SupabaseStorageManager()
    
    # Obtener un número de cotización real
    resultado = storage.listar_pdfs()
    if len(resultado.get("archivos", [])) == 0:
        print("   No hay PDFs para probar")
        return False
    
    numero_test = resultado["archivos"][0].get("numero_cotizacion", "")
    print(f"   Buscando: '{numero_test}'")
    
    # Probar buscar_pdfs con el número específico
    pdfs_encontrados = storage.buscar_pdfs(numero_test, 10)
    
    print(f"   PDFs encontrados por buscar_pdfs: {len(pdfs_encontrados)}")
    
    for pdf in pdfs_encontrados:
        print(f"   - {pdf.get('numero_cotizacion', 'N/A')} -> URL: {pdf.get('url', 'VACÍA')}")
        
        if not pdf.get('url', ''):
            print(f"     ERROR: Este PDF tiene URL vacía")
            return False
    
    return True

if __name__ == "__main__":
    success1 = debug_obtener_pdf()
    success2 = debug_buscar_pdfs_method()
    
    print(f"\n" + "=" * 60)
    print(f"RESULTADO obtener_pdf: {'SUCCESS' if success1 else 'FALLA'}")
    print(f"RESULTADO buscar_pdfs: {'SUCCESS' if success2 else 'FALLA'}")
    
    if not success1 or not success2:
        print("\nPROBLEMAS DETECTADOS:")
        if not success1:
            print("- obtener_pdf no devuelve ruta_completa válida")
        if not success2:
            print("- buscar_pdfs devuelve URLs vacías")
        print("\nPOSIBLE CAUSA:")
        print("- Problema en la generación de URLs públicas de Supabase Storage")
        print("- El método get_public_url() no funciona correctamente")
    print("=" * 60)