"""
Script para reparar PDFs que se subieron como carpetas en Supabase Storage
Problema: Algunos PDFs se subieron como "NOMBRE-COTIZACION.pdf/.pdf" (carpeta/archivo)
Solución: Mover estos PDFs a la estructura correcta "NOMBRE-COTIZACION.pdf"
"""

import os
from supabase_storage_manager import SupabaseStorageManager
from supabase_manager import SupabaseManager
from pdf_manager import PDFManager

def listar_carpetas_incorrectas():
    """
    Lista todas las carpetas que se crearon incorrectamente en Supabase Storage
    Busca estructuras como "BMW-CWS-FM-001-R1-ROLLERVEM.pdf/.pdf"
    """
    print("=" * 80)
    print("DIAGNÓSTICO DE CARPETAS INCORRECTAS EN SUPABASE STORAGE")
    print("=" * 80)

    storage = SupabaseStorageManager()

    if not storage.storage_available:
        print("\nERROR: Supabase Storage no disponible")
        return []

    print(f"\nSupabase Storage conectado")
    print(f"   URL: {storage.supabase.supabase_url}")
    print(f"   Bucket: {storage.bucket_name}")

    carpetas_problema = []

    # Verificar ambas carpetas: nuevas y antiguas
    for carpeta in [storage.folder_nuevas, storage.folder_antiguas]:
        print(f"\nAnalizando carpeta: {carpeta}/")
        print("-" * 80)

        try:
            # Listar todos los items en la carpeta (archivos y subcarpetas)
            response = storage.supabase.storage.from_(storage.bucket_name).list(carpeta)

            print(f"   Total items encontrados: {len(response)}")

            for item in response:
                nombre = item.get('name', '')
                metadata = item.get('metadata', {}) or {}
                tamano = metadata.get('size', 0)

                # Buscar items que NO tienen extensión .pdf O que no tienen tamaño
                # Estos podrían ser carpetas incorrectas
                if not nombre.endswith('.pdf') or tamano == 0:
                    # Intentar listar contenido dentro de este item
                    try:
                        subpath = f"{carpeta}/{nombre}"
                        contenido = storage.supabase.storage.from_(storage.bucket_name).list(subpath)

                        if len(contenido) > 0:
                            # Es una carpeta con contenido
                            # Verificar si contiene un archivo .pdf (estructura incorrecta)
                            tiene_pdf_interno = any(sub.get('name', '') == '.pdf' for sub in contenido)

                            if tiene_pdf_interno:
                                print(f"\n   CARPETA DETECTADA: {nombre}")
                                print(f"      Path completo: {subpath}")
                                print(f"      Contenido dentro:")

                                for sub_item in contenido:
                                    sub_nombre = sub_item.get('name', '')
                                    sub_metadata = sub_item.get('metadata', {}) or {}
                                    sub_size = sub_metadata.get('size', 0)
                                    print(f"         - {sub_nombre} ({sub_size} bytes)")

                                carpetas_problema.append({
                                    'carpeta_padre': carpeta,
                                    'nombre_carpeta': nombre,
                                    'path_completo': subpath,
                                    'contenido': contenido
                                })
                    except Exception as e:
                        # Si falla al listar, probablemente es un archivo normal
                        pass

        except Exception as e:
            print(f"   Error analizando carpeta {carpeta}: {e}")

    print(f"\n" + "=" * 80)
    print(f"RESUMEN: {len(carpetas_problema)} carpetas incorrectas encontradas")
    print("=" * 80)

    return carpetas_problema


def reparar_carpetas(carpetas_problema, dry_run=True):
    """
    Repara las carpetas incorrectas descargando el PDF y volviéndolo a subir correctamente

    Args:
        carpetas_problema: Lista de carpetas con problemas detectadas
        dry_run: Si es True, solo muestra lo que haría sin ejecutar cambios
    """
    print("\n" + "=" * 80)
    print("REPARACIÓN DE CARPETAS INCORRECTAS")
    print("=" * 80)

    if dry_run:
        print("\nMODO DRY RUN - Solo mostrando acciones, sin ejecutar cambios")
    else:
        print("\nMODO EJECUCION - Se realizaran cambios permanentes")

    storage = SupabaseStorageManager()
    db_manager = SupabaseManager()
    pdf_manager = PDFManager(db_manager)

    reparados = 0
    errores = []

    for problema in carpetas_problema:
        carpeta_padre = problema['carpeta_padre']
        nombre_carpeta = problema['nombre_carpeta']  # ej: "BMW-CWS-FM-001-R1-ROLLERVEM.pdf"
        path_carpeta = problema['path_completo']     # ej: "nuevas/BMW-CWS-FM-001-R1-ROLLERVEM.pdf"
        contenido = problema['contenido']

        print(f"\nProcesando: {nombre_carpeta}")
        print(f"   Path: {path_carpeta}")

        # Buscar el archivo PDF dentro de la carpeta (debería ser ".pdf")
        archivo_pdf = None
        for item in contenido:
            if item.get('name') == '.pdf':
                archivo_pdf = item
                break

        if not archivo_pdf:
            print(f"   No se encontro archivo .pdf dentro de la carpeta")
            errores.append(f"{nombre_carpeta}: Sin archivo .pdf interno")
            continue

        # Construir paths
        path_incorrecto = f"{path_carpeta}/.pdf"  # ej: "nuevas/BMW-CWS-FM-001-R1-ROLLERVEM.pdf/.pdf"
        numero_cotizacion = nombre_carpeta.replace('.pdf', '')  # Remover .pdf del nombre
        path_correcto = f"{carpeta_padre}/{numero_cotizacion}.pdf"  # ej: "nuevas/BMW-CWS-FM-001-R1-ROLLERVEM.pdf"

        print(f"   Path incorrecto: {path_incorrecto}")
        print(f"   Path correcto: {path_correcto}")
        print(f"   Número cotización: {numero_cotizacion}")

        if dry_run:
            print(f"   [DRY RUN] Se moveria de {path_incorrecto} -> {path_correcto}")
            reparados += 1
        else:
            try:
                # Paso 1: Obtener URL pública del archivo incorrecto
                url_incorrecta = storage.supabase.storage.from_(storage.bucket_name).get_public_url(path_incorrecto)
                print(f"   Descargando PDF desde: {url_incorrecta[:80]}...")

                # Paso 2: Descargar el contenido del PDF
                import requests
                import tempfile

                response = requests.get(url_incorrecta, timeout=30)
                if response.status_code != 200:
                    raise Exception(f"Error descargando PDF: HTTP {response.status_code}")

                pdf_content = response.content
                tamano = len(pdf_content)
                print(f"   PDF descargado: {tamano} bytes")

                # Paso 3: Crear archivo temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(pdf_content)
                    temp_path = temp_file.name

                # Paso 4: Subir con el nombre correcto
                print(f"   Subiendo con nombre correcto...")
                es_nueva = (carpeta_padre == storage.folder_nuevas)
                resultado = storage.subir_pdf(temp_path, numero_cotizacion, es_nueva=es_nueva)

                # Paso 5: Limpiar archivo temporal
                os.unlink(temp_path)

                if resultado.get('url'):
                    print(f"   PDF reparado exitosamente")
                    print(f"   Nueva URL: {resultado['url'][:80]}...")

                    # Paso 6: Eliminar la carpeta incorrecta
                    try:
                        storage.supabase.storage.from_(storage.bucket_name).remove([path_incorrecto])
                        print(f"   Archivo incorrecto eliminado: {path_incorrecto}")

                        # Tambien intentar eliminar la carpeta vacia
                        try:
                            storage.supabase.storage.from_(storage.bucket_name).remove([path_carpeta])
                            print(f"   Carpeta vacia eliminada: {path_carpeta}")
                        except:
                            pass  # La carpeta puede no quedar vacia o no eliminarse, no critico
                    except Exception as del_error:
                        print(f"   No se pudo eliminar archivo incorrecto: {del_error}")

                    reparados += 1
                else:
                    raise Exception(f"Subida falló: {resultado.get('error', 'Error desconocido')}")

            except Exception as e:
                error_msg = f"{nombre_carpeta}: {str(e)}"
                errores.append(error_msg)
                print(f"   ERROR: {e}")

    # Resumen final
    print(f"\n" + "=" * 80)
    print("RESUMEN DE REPARACION")
    print("=" * 80)
    print(f"PDFs reparados exitosamente: {reparados}")
    print(f"Errores: {len(errores)}")

    if errores:
        print(f"\nDetalles de errores:")
        for error in errores:
            print(f"  - {error}")

    return reparados, errores


if __name__ == "__main__":
    print("\nHERRAMIENTA DE REPARACION DE PDFs EN SUPABASE STORAGE\n")

    # Paso 1: Diagnostico
    carpetas_problema = listar_carpetas_incorrectas()

    if len(carpetas_problema) == 0:
        print("\nNo se encontraron carpetas con problemas. Sistema OK!")
    else:
        print(f"\nSe encontraron {len(carpetas_problema)} carpetas con problemas")

        # Paso 2: Mostrar lo que se haria (dry run)
        print("\n" + "=" * 80)
        print("SIMULACION DE REPARACION (DRY RUN)")
        print("=" * 80)
        reparar_carpetas(carpetas_problema, dry_run=True)

        # Paso 3: Preguntar si ejecutar reparacion
        print("\n" + "=" * 80)
        respuesta = input("\nDeseas ejecutar la reparacion? (escribe 'SI' para confirmar): ")

        if respuesta.strip().upper() == "SI":
            print("\nIniciando reparacion...")
            reparar_carpetas(carpetas_problema, dry_run=False)
            print("\nReparacion completada!")
        else:
            print("\nReparacion cancelada por el usuario")
