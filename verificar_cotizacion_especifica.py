# -*- coding: utf-8 -*-
import os
import sys

# Añadir el directorio actual al path para encontrar los módulos del proyecto
sys.path.append(os.getcwd())

from supabase_manager import SupabaseManager

def verificar_cotizacion():
    """
    Se conecta a Supabase y verifica si una cotización específica existe.
    """
    print("Inicializando SupabaseManager para verificación...")
    db = SupabaseManager()

    if db.modo_offline:
        print("--- RESULTADO ---")
        print("FALLO: No se pudo conectar a Supabase. La aplicación sigue en modo offline.")
        print("Por favor, revisa las credenciales en el archivo .env y la conexión de red.")
        return

    print("Conexión a Supabase exitosa. Buscando cotización...")
    
    numero_cotizacion = "BMW-CWS-CHR-001-R1-NUEVO-FORMULARI"
    resultado = db.obtener_cotizacion(numero_cotizacion)
    
    print("\n--- RESULTADO ---")
    if resultado.get("encontrado"):
        print(f"ÉXITO: La cotización '{numero_cotizacion}' fue encontrada en Supabase.")
        # Opcional: imprimir algunos detalles para confirmar
        item = resultado.get("item", {})
        datos_generales = item.get("datosGenerales", {})
        print(f"  - Cliente: {datos_generales.get('cliente')}")
        print(f"  - Vendedor: {datos_generales.get('vendedor')}")
        print(f"  - Proyecto: {datos_generales.get('proyecto')}")
    else:
        print(f"FALLO: La cotización '{numero_cotizacion}' NO fue encontrada en Supabase.")
        print(f"  - Razón: {resultado.get('error', 'No se proporcionó detalle del error.')}")

    db.close()

if __name__ == "__main__":
    verificar_cotizacion()
