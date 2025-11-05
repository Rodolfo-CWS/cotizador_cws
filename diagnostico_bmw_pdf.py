"""
Script de diagnóstico para investigar por qué el PDF BMW-CWS-FM-002-R1-INSTALACIÓ no se abre
"""

import os
import sys

# No cargar dotenv - usar variables de entorno directamente del sistema
# load_dotenv()

print("=" * 80)
print("DIAGNÓSTICO: BMW-CWS-FM-002-R1-INSTALACIÓ PDF")
print("=" * 80)
print()

# 1. Verificar variables de entorno
print("1. VERIFICACIÓN DE VARIABLES DE ENTORNO")
print("-" * 80)

supabase_url = os.getenv('SUPABASE_URL')
supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

print(f"SUPABASE_URL: {'✓ Configurada' if supabase_url else '✗ NO CONFIGURADA'}")
print(f"SUPABASE_ANON_KEY: {'✓ Configurada' if supabase_anon_key else '✗ NO CONFIGURADA'}")
print(f"SUPABASE_SERVICE_KEY: {'✓ Configurada' if supabase_service_key else '✗ NO CONFIGURADA'}")

if not supabase_service_key:
    print()
    print("⚠️  PROBLEMA CRÍTICO: SUPABASE_SERVICE_KEY no está configurada")
    print("   → Esto previene que se suban PDFs a Supabase Storage")
    print("   → Los PDFs solo se guardan localmente y se pierden en cada deploy")
    print()

print()

# 2. Verificar Supabase Storage Manager
print("2. VERIFICACIÓN DE SUPABASE STORAGE MANAGER")
print("-" * 80)

try:
    from supabase_storage_manager import SupabaseStorageManager

    storage = SupabaseStorageManager()

    print(f"Storage disponible: {storage.is_available()}")
    print(f"Bucket: {storage.bucket_name}")
    print(f"Carpeta nuevas: {storage.folder_nuevas}")
    print(f"Carpeta antiguas: {storage.folder_antiguas}")
    print()

    if not storage.is_available():
        print("⚠️  PROBLEMA: Supabase Storage no está disponible")
        print("   → Los PDFs no se pueden subir a Supabase Storage")
        print()

except Exception as e:
    print(f"✗ Error inicializando SupabaseStorageManager: {e}")
    print()
    sys.exit(1)

# 3. Buscar el PDF específico en Supabase Storage
print("3. BÚSQUEDA DEL PDF EN SUPABASE STORAGE")
print("-" * 80)

numero_cotizacion = "BMW-CWS-FM-002-R1-INSTALACIÓ"
variaciones = [
    numero_cotizacion,
    "BMW-CWS-FM-002-R1-INSTALACIO",  # Sin acento
    "Cotizacion_BMW-CWS-FM-002-R1-INSTALACIÓ",
    "Cotizacion_BMW-CWS-FM-002-R1-INSTALACIO",
]

print(f"Buscando: {numero_cotizacion}")
print(f"Variaciones a buscar: {len(variaciones)}")
print()

encontrado = False
for variacion in variaciones:
    print(f"Buscando variación: '{variacion}'...")
    try:
        resultados = storage.buscar_pdfs(variacion, max_resultados=10)

        if resultados:
            print(f"  ✓ ENCONTRADO! ({len(resultados)} resultado(s))")
            for i, pdf_info in enumerate(resultados, 1):
                print(f"\n  Resultado #{i}:")
                print(f"    Número cotización: {pdf_info.get('numero_cotizacion', 'N/A')}")
                print(f"    File path: {pdf_info.get('file_path', 'N/A')}")
                print(f"    URL: {pdf_info.get('url', 'N/A')}")
                print(f"    Tamaño: {pdf_info.get('tamaño', 0)} bytes")
                print(f"    Fecha: {pdf_info.get('fecha_creacion', 'N/A')}")
            encontrado = True
            break
        else:
            print(f"  ✗ No encontrado con esta variación")
    except Exception as e:
        print(f"  ✗ Error buscando: {e}")

print()

if not encontrado:
    print("⚠️  PROBLEMA: PDF no encontrado en Supabase Storage")
    print("   → El PDF probablemente solo se guardó localmente")
    print("   → Los archivos locales se pierden en cada deploy de Render")
    print()

# 4. Listar todos los PDFs en Supabase Storage
print("4. LISTAR TODOS LOS PDFs EN SUPABASE STORAGE")
print("-" * 80)

try:
    resultado = storage.listar_pdfs(max_resultados=1000)
    archivos = resultado.get("archivos", [])

    print(f"Total de PDFs en Supabase Storage: {len(archivos)}")

    if archivos:
        print("\nPrimeros 5 PDFs:")
        for i, pdf in enumerate(archivos[:5], 1):
            print(f"  {i}. {pdf.get('numero_cotizacion', 'N/A')} - {pdf.get('bytes', 0)} bytes")

        # Buscar PDFs de BMW
        pdfs_bmw = [p for p in archivos if 'BMW' in p.get('numero_cotizacion', '').upper()]
        print(f"\nPDFs de BMW encontrados: {len(pdfs_bmw)}")
        for pdf in pdfs_bmw:
            print(f"  - {pdf.get('numero_cotizacion', 'N/A')}")
    else:
        print("⚠️  No hay PDFs en Supabase Storage")

    print()

except Exception as e:
    print(f"✗ Error listando PDFs: {e}")
    print()

# 5. Verificar archivos locales
print("5. VERIFICACIÓN DE ARCHIVOS LOCALES")
print("-" * 80)

try:
    from pdf_manager import PDFManager
    from supabase_manager import SupabaseManager

    db_manager = SupabaseManager()
    pdf_manager = PDFManager(db_manager)

    print(f"Carpeta nuevas: {pdf_manager.nuevas_path}")
    print(f"Existe: {pdf_manager.nuevas_path.exists()}")

    if pdf_manager.nuevas_path.exists():
        archivos_locales = list(pdf_manager.nuevas_path.glob("*.pdf"))
        print(f"Total de PDFs locales: {len(archivos_locales)}")

        # Buscar PDF específico
        for variacion in variaciones:
            pdf_path = pdf_manager.nuevas_path / f"{variacion}.pdf"
            if pdf_path.exists():
                print(f"\n✓ PDF encontrado localmente: {pdf_path}")
                print(f"  Tamaño: {pdf_path.stat().st_size} bytes")
                encontrado = True
                break

        if not encontrado:
            print(f"\n⚠️  PDF NO encontrado localmente")

            # Buscar PDFs de BMW
            bmw_pdfs = [f for f in archivos_locales if 'BMW' in f.name.upper()]
            print(f"\nPDFs de BMW encontrados localmente: {len(bmw_pdfs)}")
            for pdf in bmw_pdfs:
                print(f"  - {pdf.name}")

    print()

except Exception as e:
    print(f"✗ Error verificando archivos locales: {e}")
    print()

# 6. Verificar en base de datos
print("6. VERIFICACIÓN EN BASE DE DATOS")
print("-" * 80)

try:
    from supabase_manager import SupabaseManager

    db = SupabaseManager()
    print(f"Modo offline: {db.modo_offline}")

    # Buscar la cotización
    print(f"\nBuscando cotización: {numero_cotizacion}")

    resultados = db.buscar_cotizaciones(numero_cotizacion, pagina=1, por_pagina=10)

    if resultados.get("cotizaciones"):
        print(f"✓ Cotización encontrada en la base de datos")
        cotizacion = resultados["cotizaciones"][0]
        print(f"  Cliente: {cotizacion.get('cliente', 'N/A')}")
        print(f"  Número: {cotizacion.get('numeroCotizacion', 'N/A')}")
        print(f"  Fecha: {cotizacion.get('fecha', 'N/A')}")
    else:
        print(f"⚠️  Cotización NO encontrada en la base de datos")

    print()

except Exception as e:
    print(f"✗ Error buscando en base de datos: {e}")
    print()

# Resumen final
print("=" * 80)
print("RESUMEN DEL DIAGNÓSTICO")
print("=" * 80)
print()

if not supabase_service_key:
    print("❌ PROBLEMA PRINCIPAL: SUPABASE_SERVICE_KEY no configurada")
    print()
    print("SOLUCIÓN:")
    print("1. Configurar SUPABASE_SERVICE_KEY en Render")
    print("2. Regenerar el PDF de la cotización BMW")
    print("3. Verificar que se suba correctamente a Supabase Storage")
    print()
elif not storage.is_available():
    print("❌ PROBLEMA: Supabase Storage no disponible")
    print()
    print("SOLUCIÓN:")
    print("1. Verificar credenciales de Supabase")
    print("2. Verificar conectividad con Supabase")
    print()
elif not encontrado:
    print("❌ PROBLEMA: PDF no encontrado en Supabase Storage ni localmente")
    print()
    print("SOLUCIÓN:")
    print("1. El PDF se perdió probablemente en un redeploy")
    print("2. Regenerar el PDF de la cotización BMW")
    print("3. Verificar que se suba correctamente a Supabase Storage")
    print()
else:
    print("✓ PDF encontrado - investigar por qué no se puede abrir")
    print()
    print("PRÓXIMOS PASOS:")
    print("1. Verificar la URL del PDF")
    print("2. Probar acceso directo a la URL")
    print("3. Revisar permisos del bucket de Supabase Storage")
    print()

print("=" * 80)
