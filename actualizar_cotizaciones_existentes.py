#!/usr/bin/env python3
"""
Script para actualizar cotizaciones existentes con timestamps faltantes
"""

import datetime
from database import DatabaseManager

def actualizar_cotizaciones_existentes():
    """Actualiza cotizaciones que no tienen timestamps"""
    print("🔄 Actualizando cotizaciones existentes con timestamps...")
    
    try:
        db_manager = DatabaseManager()
        
        # Buscar cotizaciones sin timestamp o fechaCreacion
        filtro = {
            "$or": [
                {"timestamp": {"$exists": False}},
                {"timestamp": None},
                {"fechaCreacion": {"$exists": False}},
                {"fechaCreacion": None}
            ]
        }
        
        cotizaciones_sin_timestamp = list(db_manager.collection.find(filtro))
        
        print(f"📊 Encontradas {len(cotizaciones_sin_timestamp)} cotizaciones sin timestamp")
        
        if len(cotizaciones_sin_timestamp) == 0:
            print("✅ Todas las cotizaciones ya tienen timestamps")
            return
        
        # Actualizar cada cotización
        actualizadas = 0
        
        for cotizacion in cotizaciones_sin_timestamp:
            # Usar fecha actual como fallback
            ahora = datetime.datetime.now()
            
            # Preparar actualización
            update_data = {}
            
            if not cotizacion.get("timestamp"):
                update_data["timestamp"] = int(ahora.timestamp() * 1000)
            
            if not cotizacion.get("fechaCreacion"):
                update_data["fechaCreacion"] = ahora.isoformat()
            
            if not cotizacion.get("version"):
                update_data["version"] = "1.0.0"
            
            # Actualizar en MongoDB
            if update_data:
                resultado = db_manager.collection.update_one(
                    {"_id": cotizacion["_id"]},
                    {"$set": update_data}
                )
                
                if resultado.modified_count > 0:
                    actualizadas += 1
                    numero = cotizacion.get("numeroCotizacion", str(cotizacion["_id"]))
                    print(f"✅ Actualizada: {numero}")
        
        print(f"🎉 {actualizadas} cotizaciones actualizadas exitosamente")
        
        # Cerrar conexión
        db_manager.cerrar_conexion()
        
    except Exception as e:
        print(f"❌ Error actualizando cotizaciones: {e}")

if __name__ == "__main__":
    actualizar_cotizaciones_existentes()
