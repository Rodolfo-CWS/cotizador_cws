"""
Script de diagnóstico para investigar el problema de búsqueda de PDFs
Problema: El buscador muestra "CWS-FM-002-R1-INSTALACIÓ" pero busca "BMW-CWS-FM-002-R1-INSTALACI"
"""

import json
from supabase_manager import SupabaseManager
from pdf_manager import PDFManager
from supabase_storage_manager import SupabaseStorageManager

print("=" * 80)
print("DIAGNÓSTICO DE BÚSQUEDA DE PDFs")
print("=" * 80)

# 1. Verificar cotizaciones en JSON local
print("\n1. COTIZACIONES EN JSON LOCAL (cotizaciones_offline.json)")
print("-" * 80)
with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    cotizaciones = data['cotizaciones']

    # Buscar FM-002
    fm002_cotizaciones = [c for c in cotizaciones if 'FM-002' in c.get('numeroCotizacion', '')]

    if fm002_cotizaciones:
        for cot in fm002_cotizaciones:
            print(f"\nNúmero: {cot['numeroCotizacion']}")
            print(f"Cliente: {cot['datosGenerales']['cliente']}")
            print(f"Proyecto: {cot['datosGenerales']['proyecto']}")
            print(f"Vendedor: {cot['datosGenerales']['vendedor']}")
    else:
        print("No se encontraron cotizaciones FM-002")

# 2. Verificar PDFs en Supabase Storage
print("\n\n2. PDFs EN SUPABASE STORAGE")
print("-" * 80)
storage = SupabaseStorageManager()
if storage.is_available():
    resultado = storage.listar_pdfs()
    archivos = resultado.get('archivos', resultado)

    if isinstance(archivos, dict):
        archivos = archivos.get('archivos', [])

    # Buscar FM-002
    fm002_pdfs = [pdf for pdf in archivos if 'FM-002' in pdf.get('numero_cotizacion', '') or 'FM-002' in pdf.get('file_path', '')]

    if fm002_pdfs:
        for pdf in fm002_pdfs:
            print(f"\nNúmero cotización: {pdf['numero_cotizacion']}")
            print(f"Ruta archivo: {pdf['file_path']}")
            print(f"URL: {pdf['url'][:80]}...")
    else:
        print("No se encontraron PDFs FM-002")
else:
    print("Supabase Storage NO disponible")

# 3. Simular búsqueda unificada
print("\n\n3. SIMULACIÓN DE BÚSQUEDA UNIFICADA (como lo hace app.py)")
print("-" * 80)
db_manager = SupabaseManager()
pdf_manager_instance = PDFManager(db_manager)

# Buscar con query "FM-002"
query = "FM-002"
print(f"\nBuscando con query: '{query}'")

# Buscar en base de datos
print("\n3a. Búsqueda en base de datos (SupabaseManager):")
resultado_db = db_manager.buscar_cotizaciones(query, 1, 100)
if not resultado_db.get("error"):
    cotizaciones_encontradas = resultado_db.get("resultados", [])
    print(f"Encontradas {len(cotizaciones_encontradas)} cotizaciones")
    for cot in cotizaciones_encontradas:
        if 'FM-002' in cot.get('numeroCotizacion', ''):
            print(f"  - {cot['numeroCotizacion']}")
            print(f"    Cliente: {cot['datosGenerales']['cliente']}")
            print(f"    Proyecto: {cot['datosGenerales']['proyecto']}")
else:
    print(f"Error: {resultado_db.get('error')}")

# Buscar PDFs
print("\n3b. Búsqueda en PDFs (PDFManager):")
resultado_pdfs = pdf_manager_instance.buscar_pdfs(query, 1, 100)
if not resultado_pdfs.get("error"):
    pdfs_encontrados = resultado_pdfs.get("resultados", [])
    print(f"Encontrados {len(pdfs_encontrados)} PDFs")
    for pdf in pdfs_encontrados:
        if 'FM-002' in pdf.get('numero_cotizacion', ''):
            print(f"  - {pdf['numero_cotizacion']}")
            print(f"    Cliente: {pdf.get('cliente', 'N/A')}")
            print(f"    Tiene desglose: {pdf.get('tiene_desglose', False)}")
else:
    print(f"Error: {resultado_pdfs.get('error')}")

# 4. Simular intento de obtener PDF con diferentes nombres
print("\n\n4. PRUEBA DE OBTENER PDF CON DIFERENTES VARIACIONES")
print("-" * 80)

variaciones_prueba = [
    "DAIKIN-CWS-FM-002-R1-CARTGASKET",  # Nombre real en Supabase Storage
    "CWS-FM-002-R1-INSTALACIÓ",          # Nombre que muestra el buscador (incorrecto)
    "BMW-CWS-FM-002-R1-INSTALACI",       # Nombre en el error
    "FM-002"                             # Búsqueda simple
]

for variacion in variaciones_prueba:
    print(f"\nIntentando obtener PDF: '{variacion}'")
    resultado = pdf_manager_instance.obtener_pdf(variacion)
    if resultado.get("encontrado"):
        print(f"  ✓ ENCONTRADO")
        print(f"    Ruta: {resultado.get('ruta_completa', 'N/A')[:80]}")
        print(f"    Tipo: {resultado.get('tipo', 'N/A')}")
    else:
        print(f"  ✗ NO ENCONTRADO")
        if "error" in resultado:
            print(f"    Error: {resultado['error']}")

print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
