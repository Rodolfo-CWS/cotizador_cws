"""
Diagnóstico exhaustivo de la estructura de archivos en Supabase Storage
"""

from supabase_storage_manager import SupabaseStorageManager
import json

def listar_todo_recursivamente():
    """Lista TODA la estructura de Supabase Storage de manera recursiva"""

    storage = SupabaseStorageManager()

    if not storage.storage_available:
        print("ERROR: Supabase Storage no disponible")
        return

    print("=" * 80)
    print("LISTADO COMPLETO DE SUPABASE STORAGE")
    print("=" * 80)
    print(f"Bucket: {storage.bucket_name}")
    print(f"URL: {storage.supabase.supabase_url}\n")

    def listar_carpeta(path="", nivel=0):
        """Lista contenido de una carpeta recursivamente"""
        indent = "  " * nivel

        try:
            if path:
                print(f"{indent}Listando: {path}/")
                response = storage.supabase.storage.from_(storage.bucket_name).list(path)
            else:
                print(f"{indent}Listando: / (raiz)")
                response = storage.supabase.storage.from_(storage.bucket_name).list()

            print(f"{indent}  Items encontrados: {len(response)}\n")

            for item in response:
                nombre = item.get('name', '')
                metadata = item.get('metadata', {}) or {}
                tamano = metadata.get('size', 0)

                # Construir path completo
                if path:
                    path_completo = f"{path}/{nombre}"
                else:
                    path_completo = nombre

                # Verificar si es archivo o carpeta
                # En Supabase Storage, los items sin size son generalmente carpetas
                es_archivo = tamano > 0 or nombre.endswith('.pdf')

                if es_archivo:
                    print(f"{indent}  [ARCHIVO] {nombre}")
                    print(f"{indent}    Size: {tamano} bytes")
                    print(f"{indent}    Path: {path_completo}")

                    # Obtener URL
                    try:
                        url = storage.supabase.storage.from_(storage.bucket_name).get_public_url(path_completo)
                        print(f"{indent}    URL: {url[:60]}...")
                    except:
                        pass
                    print()
                else:
                    # Podría ser una carpeta, intentar listar su contenido
                    print(f"{indent}  [CARPETA?] {nombre}")
                    print(f"{indent}    Path: {path_completo}")

                    try:
                        # Intentar listar contenido
                        sub_response = storage.supabase.storage.from_(storage.bucket_name).list(path_completo)

                        if len(sub_response) > 0:
                            print(f"{indent}    -> ES UNA CARPETA (tiene {len(sub_response)} items dentro)")
                            print()
                            # Listar recursivamente
                            listar_carpeta(path_completo, nivel + 1)
                        else:
                            print(f"{indent}    -> Carpeta vacia o archivo sin metadata")
                            print()
                    except Exception as e:
                        print(f"{indent}    -> No se puede listar (probablemente es un archivo)")
                        print(f"{indent}    Error: {e}")
                        print()

        except Exception as e:
            print(f"{indent}ERROR listando {path}: {e}\n")

    # Empezar desde la raíz
    listar_carpeta("", 0)

    print("=" * 80)
    print("FIN DEL LISTADO")
    print("=" * 80)

if __name__ == "__main__":
    listar_todo_recursivamente()
