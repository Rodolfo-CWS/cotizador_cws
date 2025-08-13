#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para limpiar completamente el archivo offline JSON
Elimina todas las cotizaciones y reinicializa el archivo
"""

import os
import json
import datetime
from pathlib import Path

def limpiar_archivo_offline():
    """Limpia completamente el archivo offline JSON"""
    archivo_datos = "cotizaciones_offline.json"
    archivo_path = Path(archivo_datos)
    
    print("LIMPIANDO ARCHIVO OFFLINE JSON")
    print("=" * 35)
    
    # Verificar si existe el archivo
    if not archivo_path.exists():
        print(f"El archivo {archivo_datos} no existe")
        return True
    
    try:
        # Leer archivo actual para mostrar información
        with open(archivo_datos, 'r', encoding='utf-8') as f:
            datos_actuales = json.load(f)
        
        cotizaciones_actuales = datos_actuales.get("cotizaciones", [])
        total_cotizaciones = len(cotizaciones_actuales)
        
        print(f"Archivo encontrado: {archivo_datos}")
        print(f"Total de cotizaciones actuales: {total_cotizaciones}")
        
        if total_cotizaciones > 0:
            print(f"\nEjemplos de cotizaciones (primeras 5):")
            for i, cot in enumerate(cotizaciones_actuales[:5], 1):
                numero = cot.get('numeroCotizacion', 'Sin numero')
                cliente = cot.get('datosGenerales', {}).get('cliente', 'Sin cliente') 
                fecha = cot.get('fechaCreacion', 'Sin fecha')[:10] if cot.get('fechaCreacion') else 'Sin fecha'
                print(f"  {i}. {numero} | {cliente} | {fecha}")
        
        # Crear estructura limpia
        datos_limpios = {
            "cotizaciones": [],
            "metadata": {
                "created": datetime.datetime.now().isoformat(),
                "version": "1.0.0",
                "total_cotizaciones": 0,
                "modo": "offline",
                "limpiado_en": datetime.datetime.now().isoformat(),
                "cotizaciones_eliminadas": total_cotizaciones
            }
        }
        
        # Guardar archivo limpio
        print(f"\nEliminando {total_cotizaciones} cotizaciones...")
        with open(archivo_datos, 'w', encoding='utf-8') as f:
            json.dump(datos_limpios, f, ensure_ascii=False, indent=2)
        
        print(f"Archivo {archivo_datos} limpiado exitosamente")
        print(f"Cotizaciones eliminadas: {total_cotizaciones}")
        print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificar que el archivo se guardó correctamente
        with open(archivo_datos, 'r', encoding='utf-8') as f:
            datos_verificacion = json.load(f)
        
        cotizaciones_restantes = len(datos_verificacion.get("cotizaciones", []))
        print(f"Verificacion: {cotizaciones_restantes} cotizaciones restantes")
        
        if cotizaciones_restantes == 0:
            print("EXITO: El archivo offline esta ahora completamente limpio")
        else:
            print(f"ADVERTENCIA: Aun quedan {cotizaciones_restantes} cotizaciones")
        
        return cotizaciones_restantes == 0
        
    except Exception as e:
        print(f"Error limpiando archivo: {e}")
        return False

def main():
    """Función principal"""
    try:
        # Cambiar al directorio del proyecto
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        exito = limpiar_archivo_offline()
        
        if exito:
            print("\n✓ Archivo offline limpiado exitosamente")
            print("El archivo cotizaciones_offline.json esta ahora vacio y reinicializado")
        else:
            print("\n✗ No se pudo limpiar completamente el archivo")
            
        return exito
        
    except Exception as e:
        print(f"\nError inesperado: {e}")
        return False

if __name__ == "__main__":
    main()