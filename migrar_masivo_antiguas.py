#!/usr/bin/env python3
"""
Script para migración masiva de cotizaciones a carpeta "antiguas"

Casos de uso:
1. Migrar todas las cotizaciones anteriores a una fecha
2. Migrar cotizaciones de un cliente específico
3. Migrar por criterios de búsqueda

Uso:
    python migrar_masivo_antiguas.py --fecha-limite 2024-01-01
    python migrar_masivo_antiguas.py --cliente "CLIENTE-X" 
    python migrar_masivo_antiguas.py --edad-dias 365
    python migrar_masivo_antiguas.py --listar-candidatos
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Importar el migrador individual
try:
    from migrar_a_antiguas import MigradorAntiguas
    from database import DatabaseManager
except ImportError as e:
    print(f"Error importando módulos: {e}")
    sys.exit(1)


class MigradorMasivo:
    def __init__(self):
        """Inicializa el migrador masivo"""
        self.migrador = MigradorAntiguas()
        self.db_manager = DatabaseManager()
        
    def listar_candidatos(self, filtros: dict) -> list:
        """
        Lista cotizaciones candidatas para migración
        
        Args:
            filtros: Criterios de filtrado
            
        Returns:
            Lista de cotizaciones que cumplen los criterios
        """
        print("🔍 Buscando cotizaciones candidatas...")
        
        candidatos = []
        
        # Obtener todas las cotizaciones
        todas_cotizaciones = self.db_manager.obtener_todas_cotizaciones()
        cotizaciones = todas_cotizaciones.get("resultados", [])
        
        for cot in cotizaciones:
            # Skip si ya está marcada como histórica
            if cot.get("metadata", {}).get("estado") == "historica":
                continue
                
            incluir = True
            
            # Filtro por fecha límite
            if "fecha_limite" in filtros:
                fecha_cot_str = cot.get("fechaCreacion", "")
                if fecha_cot_str:
                    try:
                        fecha_cot = datetime.fromisoformat(fecha_cot_str.replace('Z', '+00:00'))
                        if fecha_cot.date() > filtros["fecha_limite"]:
                            incluir = False
                    except:
                        pass  # Skip cotizaciones con fecha inválida
                        
            # Filtro por edad en días
            if "edad_minima_dias" in filtros:
                fecha_cot_str = cot.get("fechaCreacion", "")
                if fecha_cot_str:
                    try:
                        fecha_cot = datetime.fromisoformat(fecha_cot_str.replace('Z', '+00:00'))
                        edad_dias = (datetime.now() - fecha_cot).days
                        if edad_dias < filtros["edad_minima_dias"]:
                            incluir = False
                    except:
                        incluir = False
                        
            # Filtro por cliente
            if "cliente" in filtros:
                cliente_cot = cot.get("datosGenerales", {}).get("cliente", "").upper()
                if filtros["cliente"].upper() not in cliente_cot:
                    incluir = False
                    
            # Filtro por vendedor
            if "vendedor" in filtros:
                vendedor_cot = cot.get("datosGenerales", {}).get("vendedor", "").upper()
                if filtros["vendedor"].upper() not in vendedor_cot:
                    incluir = False
            
            if incluir:
                candidatos.append({
                    "numero_cotizacion": cot.get("numeroCotizacion", "Sin número"),
                    "cliente": cot.get("datosGenerales", {}).get("cliente", "N/A"),
                    "vendedor": cot.get("datosGenerales", {}).get("vendedor", "N/A"),
                    "proyecto": cot.get("datosGenerales", {}).get("proyecto", "N/A"),
                    "fecha_creacion": cot.get("fechaCreacion", "N/A"),
                    "revision": cot.get("revision", "1")
                })
        
        return candidatos
    
    def mostrar_candidatos(self, candidatos: list):
        """Muestra lista de candidatos de forma organizada"""
        if not candidatos:
            print("📭 No se encontraron cotizaciones candidatas")
            return
            
        print(f"\n📋 CANDIDATOS PARA MIGRACIÓN ({len(candidatos)} cotizaciones):")
        print("-" * 80)
        
        for i, cot in enumerate(candidatos, 1):
            fecha = cot["fecha_creacion"][:10] if len(cot["fecha_creacion"]) > 10 else cot["fecha_creacion"]
            
            print(f"{i:3}. {cot['numero_cotizacion']}")
            print(f"     Cliente: {cot['cliente'][:30]}{'...' if len(cot['cliente']) > 30 else ''}")
            print(f"     Proyecto: {cot['proyecto'][:25]}{'...' if len(cot['proyecto']) > 25 else ''}")
            print(f"     Fecha: {fecha} | Rev: R{cot['revision']}")
            print()
    
    def migrar_lote(self, candidatos: list, confirmar: bool = True) -> dict:
        """
        Migra un lote de cotizaciones
        
        Args:
            candidatos: Lista de cotizaciones a migrar
            confirmar: Si pedir confirmación antes de cada migración
            
        Returns:
            Resumen de resultados
        """
        if not candidatos:
            return {"total": 0, "exitosos": 0, "errores": 0, "detalles": []}
        
        print(f"\n🚀 INICIANDO MIGRACIÓN MASIVA ({len(candidatos)} cotizaciones)")
        print("=" * 60)
        
        resultados = {
            "total": len(candidatos),
            "exitosos": 0,
            "errores": 0,
            "detalles": []
        }
        
        for i, candidato in enumerate(candidatos, 1):
            numero_cot = candidato["numero_cotizacion"]
            
            print(f"\n[{i}/{len(candidatos)}] Migrando: {numero_cot}")
            
            if confirmar:
                respuesta = input(f"  ¿Migrar '{numero_cot}'? (s/N/a=all): ").lower()
                if respuesta.startswith('a'):
                    confirmar = False  # No pedir más confirmaciones
                elif not respuesta.startswith('s'):
                    print("  ⏭️  Saltado por usuario")
                    continue
            
            # Ejecutar migración individual
            try:
                resultado_individual = self.migrador.migrar_cotizacion(numero_cot)
                
                # Evaluar éxito
                exitos_individuales = sum([
                    resultado_individual["cloudinary"]["success"],
                    resultado_individual["local"]["success"],
                    resultado_individual["database"]["success"]
                ])
                
                if exitos_individuales >= 2:  # Al menos 2 de 3 exitosos
                    resultados["exitosos"] += 1
                    print(f"  ✅ Migrado exitosamente ({exitos_individuales}/3 operaciones)")
                else:
                    resultados["errores"] += 1
                    print(f"  ❌ Migración fallida ({exitos_individuales}/3 operaciones)")
                
                resultados["detalles"].append({
                    "numero_cotizacion": numero_cot,
                    "exito": exitos_individuales >= 2,
                    "operaciones_exitosas": exitos_individuales,
                    "errores": resultado_individual.get("errores", [])
                })
                
            except Exception as e:
                resultados["errores"] += 1
                error_msg = f"Error crítico migrando {numero_cot}: {str(e)}"
                print(f"  💥 {error_msg}")
                
                resultados["detalles"].append({
                    "numero_cotizacion": numero_cot,
                    "exito": False,
                    "operaciones_exitosas": 0,
                    "errores": [error_msg]
                })
        
        return resultados
    
    def generar_reporte(self, resultados: dict, filtros: dict):
        """Genera reporte de migración masiva"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporte_file = Path(f"reporte_migracion_masiva_{timestamp}.json")
        
        reporte = {
            "timestamp": datetime.now().isoformat(),
            "filtros_aplicados": filtros,
            "resumen": {
                "total_procesadas": resultados["total"],
                "migraciones_exitosas": resultados["exitosos"],
                "errores": resultados["errores"],
                "tasa_exito": f"{(resultados['exitosos']/resultados['total']*100):.1f}%" if resultados["total"] > 0 else "0%"
            },
            "detalles": resultados["detalles"]
        }
        
        with open(reporte_file, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Reporte detallado guardado en: {reporte_file}")
        return reporte_file


def main():
    """Función principal con argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Migrador masivo de cotizaciones a carpeta 'antiguas'",
        epilog="Ejemplos:\n"
               "  python migrar_masivo_antiguas.py --listar-candidatos --edad-dias 365\n"
               "  python migrar_masivo_antiguas.py --fecha-limite 2024-01-01 --confirmar\n"
               "  python migrar_masivo_antiguas.py --cliente 'ACME' --edad-dias 180",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--fecha-limite', type=str, 
                       help='Migrar cotizaciones anteriores a esta fecha (YYYY-MM-DD)')
    parser.add_argument('--edad-dias', type=int, 
                       help='Migrar cotizaciones con más de X días de antigüedad')
    parser.add_argument('--cliente', type=str, 
                       help='Filtrar por cliente específico')
    parser.add_argument('--vendedor', type=str, 
                       help='Filtrar por vendedor específico')
    parser.add_argument('--listar-candidatos', action='store_true',
                       help='Solo listar candidatos sin migrar')
    parser.add_argument('--confirmar', action='store_true',
                       help='Pedir confirmación antes de cada migración')
    parser.add_argument('--auto', action='store_true',
                       help='Migración automática sin confirmaciones')
    
    args = parser.parse_args()
    
    # Validaciones
    if not any([args.fecha_limite, args.edad_dias, args.cliente, args.vendedor]):
        print("❌ Debes especificar al menos un criterio de filtrado")
        parser.print_help()
        sys.exit(1)
    
    # Construir filtros
    filtros = {}
    
    if args.fecha_limite:
        try:
            filtros["fecha_limite"] = datetime.strptime(args.fecha_limite, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Fecha límite inválida. Usa formato YYYY-MM-DD")
            sys.exit(1)
    
    if args.edad_dias:
        filtros["edad_minima_dias"] = args.edad_dias
        
    if args.cliente:
        filtros["cliente"] = args.cliente
        
    if args.vendedor:
        filtros["vendedor"] = args.vendedor
    
    print("🚀 MIGRADOR MASIVO DE COTIZACIONES")
    print("=" * 40)
    print("Filtros aplicados:")
    for key, value in filtros.items():
        print(f"  - {key}: {value}")
    
    # Inicializar migrador
    migrador_masivo = MigradorMasivo()
    
    # Buscar candidatos
    candidatos = migrador_masivo.listar_candidatos(filtros)
    
    # Mostrar candidatos
    migrador_masivo.mostrar_candidatos(candidatos)
    
    # Solo listar o proceder con migración
    if args.listar_candidatos:
        print("✅ Lista de candidatos completada")
        sys.exit(0)
    
    if not candidatos:
        print("✅ No hay cotizaciones para migrar")
        sys.exit(0)
    
    # Confirmar migración masiva
    if not args.auto:
        respuesta = input(f"\n¿Proceder con la migración de {len(candidatos)} cotizaciones? (s/N): ")
        if not respuesta.lower().startswith('s'):
            print("❌ Migración cancelada por el usuario")
            sys.exit(0)
    
    # Ejecutar migración masiva
    resultados = migrador_masivo.migrar_lote(candidatos, confirmar=args.confirmar and not args.auto)
    
    # Generar reporte
    reporte_file = migrador_masivo.generar_reporte(resultados, filtros)
    
    # Resumen final
    print(f"\n📊 RESUMEN FINAL:")
    print(f"   Total procesadas: {resultados['total']}")
    print(f"   Migraciones exitosas: {resultados['exitosos']}")
    print(f"   Errores: {resultados['errores']}")
    
    if resultados['total'] > 0:
        tasa_exito = (resultados['exitosos']/resultados['total']*100)
        print(f"   Tasa de éxito: {tasa_exito:.1f}%")
    
    print("\n✅ Migración masiva completada")


if __name__ == "__main__":
    main()