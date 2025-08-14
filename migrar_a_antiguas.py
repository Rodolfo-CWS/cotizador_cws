#!/usr/bin/env python3
"""
Script para migrar cotizaciones específicas de "nuevas" a "antiguas"

Uso:
    python migrar_a_antiguas.py NUMERO-COTIZACION
    python migrar_a_antiguas.py CLIENTE-CWS-VV-001-R1-PROYECTO

Este script:
1. Mueve el PDF de carpeta "nuevas" a "antiguas" en todos los storage
2. Actualiza registros en la base de datos
3. Mantiene el PDF visible en búsquedas pero marcado como "histórico"
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# Importar managers del sistema
try:
    from pdf_manager import PDFManager
    from cloudinary_manager import CloudinaryManager
    from database import DatabaseManager
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrate de ejecutar desde el directorio del proyecto")
    sys.exit(1)


class MigradorAntiguas:
    def __init__(self):
        """Inicializa todos los managers necesarios"""
        print("🔧 Inicializando managers...")
        
        self.pdf_manager = PDFManager(None)  # No necesita db_manager para esto
        self.cloudinary_manager = CloudinaryManager()
        self.db_manager = DatabaseManager()
        
        print("✅ Managers inicializados correctamente")

    def migrar_cotizacion(self, numero_cotizacion: str) -> dict:
        """
        Migra una cotización específica a carpeta de antiguos
        
        Args:
            numero_cotizacion: Número exacto de la cotización a migrar
            
        Returns:
            Dict con resultado detallado de la migración
        """
        print(f"\n📦 Iniciando migración de: {numero_cotizacion}")
        
        resultado = {
            "numero_cotizacion": numero_cotizacion,
            "cloudinary": {"success": False, "message": ""},
            "local": {"success": False, "message": ""},
            "database": {"success": False, "message": ""},
            "errores": []
        }
        
        # 1. MIGRAR EN CLOUDINARY
        print("☁️  Migrando en Cloudinary...")
        try:
            cloudinary_result = self.cloudinary_manager.mover_a_antiguas(numero_cotizacion)
            if "error" not in cloudinary_result:
                resultado["cloudinary"]["success"] = True
                resultado["cloudinary"]["message"] = "PDF movido exitosamente en Cloudinary"
                print("   ✅ Cloudinary: OK")
            else:
                resultado["cloudinary"]["message"] = cloudinary_result["error"]
                resultado["errores"].append(f"Cloudinary: {cloudinary_result['error']}")
                print(f"   ❌ Cloudinary: {cloudinary_result['error']}")
        except Exception as e:
            error_msg = f"Error en Cloudinary: {str(e)}"
            resultado["cloudinary"]["message"] = error_msg
            resultado["errores"].append(error_msg)
            print(f"   ❌ Cloudinary: {error_msg}")

        # 2. MIGRAR ARCHIVO LOCAL
        print("💾 Migrando archivo local...")
        try:
            archivo_origen = self.pdf_manager.nuevas_path / f"{numero_cotizacion}.pdf"
            archivo_destino = self.pdf_manager.antiguas_path / f"{numero_cotizacion}.pdf"
            
            if archivo_origen.exists():
                # Mover archivo
                shutil.move(str(archivo_origen), str(archivo_destino))
                resultado["local"]["success"] = True
                resultado["local"]["message"] = f"PDF movido localmente: {archivo_destino}"
                print(f"   ✅ Local: {archivo_origen} → {archivo_destino}")
            else:
                resultado["local"]["message"] = "PDF no encontrado en carpeta local 'nuevas'"
                print("   ⚠️  Local: PDF no encontrado en 'nuevas'")
        except Exception as e:
            error_msg = f"Error moviendo archivo local: {str(e)}"
            resultado["local"]["message"] = error_msg
            resultado["errores"].append(error_msg)
            print(f"   ❌ Local: {error_msg}")

        # 3. ACTUALIZAR BASE DE DATOS
        print("🗄️  Actualizando registros en base de datos...")
        try:
            # Buscar cotización en sistema
            cotizacion_info = self.db_manager.obtener_cotizacion(numero_cotizacion)
            
            if cotizacion_info.get("encontrado"):
                # Agregar metadata de migración
                cotizacion = cotizacion_info["item"]
                
                # Marcar como histórica
                if "metadata" not in cotizacion:
                    cotizacion["metadata"] = {}
                    
                cotizacion["metadata"].update({
                    "estado": "historica",
                    "migrado_a_antiguas": datetime.now().isoformat(),
                    "migrado_por": "script_automatico",
                    "razon_migracion": "Cotización completada - archivo histórico"
                })
                
                # Si está en MongoDB, actualizar
                if not self.db_manager.modo_offline:
                    from bson import ObjectId
                    self.db_manager.collection.update_one(
                        {"_id": ObjectId(cotizacion["_id"])},
                        {"$set": {"metadata": cotizacion["metadata"]}}
                    )
                
                # Actualizar JSON también
                datos_json = self.db_manager._cargar_datos_offline()
                for i, cot_json in enumerate(datos_json.get("cotizaciones", [])):
                    if cot_json.get("numeroCotizacion") == numero_cotizacion:
                        datos_json["cotizaciones"][i]["metadata"] = cotizacion["metadata"]
                        break
                
                self.db_manager._guardar_datos_offline(datos_json)
                
                resultado["database"]["success"] = True
                resultado["database"]["message"] = "Registro actualizado como histórico"
                print("   ✅ Base de datos: Marcado como histórico")
            else:
                resultado["database"]["message"] = "Cotización no encontrada en base de datos"
                print("   ⚠️  Base de datos: Cotización no encontrada")
                
        except Exception as e:
            error_msg = f"Error actualizando base de datos: {str(e)}"
            resultado["database"]["message"] = error_msg
            resultado["errores"].append(error_msg)
            print(f"   ❌ Base de datos: {error_msg}")

        # RESUMEN FINAL
        exitos = sum([1 for k in ["cloudinary", "local", "database"] if resultado[k]["success"]])
        total = 3
        
        print(f"\n📊 RESUMEN MIGRACIÓN: {exitos}/{total} operaciones exitosas")
        if resultado["errores"]:
            print("❌ Errores encontrados:")
            for error in resultado["errores"]:
                print(f"   - {error}")
        else:
            print("✅ Migración completada sin errores")
            
        return resultado

    def verificar_migracion(self, numero_cotizacion: str):
        """Verifica que la migración fue exitosa"""
        print(f"\n🔍 Verificando migración de: {numero_cotizacion}")
        
        # Verificar archivo local
        archivo_antiguas = self.pdf_manager.antiguas_path / f"{numero_cotizacion}.pdf"
        archivo_nuevas = self.pdf_manager.nuevas_path / f"{numero_cotizacion}.pdf"
        
        print(f"📁 Archivo en 'nuevas': {'❌ No existe' if not archivo_nuevas.exists() else '⚠️ Aún existe'}")
        print(f"📁 Archivo en 'antiguas': {'✅ Existe' if archivo_antiguas.exists() else '❌ No existe'}")
        
        # Verificar en base de datos
        cotizacion = self.db_manager.obtener_cotizacion(numero_cotizacion)
        if cotizacion.get("encontrado"):
            metadata = cotizacion["item"].get("metadata", {})
            estado = metadata.get("estado", "normal")
            migrado = metadata.get("migrado_a_antiguas", "No")
            
            print(f"🗄️  Estado en BD: {estado}")
            print(f"🗄️  Migrado el: {migrado}")
        else:
            print("🗄️  ❌ No encontrado en base de datos")


def main():
    """Función principal del script"""
    if len(sys.argv) != 2:
        print("❌ Uso incorrecto")
        print(f"   Uso: python {sys.argv[0]} NUMERO-COTIZACION")
        print(f"   Ejemplo: python {sys.argv[0]} CLIENTE-CWS-VV-001-R1-PROYECTO")
        sys.exit(1)
    
    numero_cotizacion = sys.argv[1].strip()
    
    print("🚀 MIGRADOR DE COTIZACIONES A CARPETA 'ANTIGUAS'")
    print("=" * 50)
    print(f"Cotización a migrar: {numero_cotizacion}")
    
    if not input(f"¿Confirmas la migración de '{numero_cotizacion}' a antiguas? (s/N): ").lower().startswith('s'):
        print("❌ Migración cancelada por el usuario")
        sys.exit(0)
    
    # Ejecutar migración
    migrador = MigradorAntiguas()
    resultado = migrador.migrar_cotizacion(numero_cotizacion)
    
    # Verificar resultado
    migrador.verificar_migracion(numero_cotizacion)
    
    # Guardar log de la migración
    log_file = Path("migraciones_log.json")
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    else:
        logs = []
    
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "numero_cotizacion": numero_cotizacion,
        "resultado": resultado
    })
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Log guardado en: {log_file}")
    print("✅ Proceso completado")


if __name__ == "__main__":
    main()