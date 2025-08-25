#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE VERIFICACIÓN DE COTIZACIÓN
====================================

Script para verificar si la cotización BMW-CWS-CM-001-R1-GROW
se guardó correctamente en Supabase y si su PDF existe en Storage.

Funcionalidades:
1. Buscar cotización específica en la base de datos
2. Verificar existencia de PDF en Supabase Storage
3. Listar últimas cotizaciones creadas
4. Mostrar estadísticas de la base de datos
5. Verificar conectividad con Supabase
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

# Agregar el directorio actual al path para importar módulos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from supabase_manager import SupabaseManager
    print("[OK] Módulo SupabaseManager importado correctamente")
except ImportError as e:
    print(f"[ERROR] Error importando SupabaseManager: {e}")
    sys.exit(1)

def imprimir_separador(titulo: str):
    """Imprime un separador visual con título"""
    print("\n" + "="*60)
    print(f"  {titulo}")
    print("="*60)

def imprimir_resultado(titulo: str, datos: Any, indentacion: int = 0):
    """Imprime resultado de forma organizada"""
    indent = "  " * indentacion
    print(f"{indent}{titulo}:")
    
    if isinstance(datos, dict):
        for key, value in datos.items():
            if isinstance(value, (dict, list)) and len(str(value)) > 100:
                print(f"{indent}  {key}: [Objeto complejo - {type(value).__name__}]")
            else:
                print(f"{indent}  {key}: {value}")
    elif isinstance(datos, list):
        if len(datos) == 0:
            print(f"{indent}  [Lista vacía]")
        else:
            for i, item in enumerate(datos[:3]):  # Solo primeros 3 elementos
                print(f"{indent}  [{i}]: {item if not isinstance(item, dict) else '[Objeto]'}")
            if len(datos) > 3:
                print(f"{indent}  ... y {len(datos) - 3} elementos más")
    else:
        print(f"{indent}  {datos}")
    print()

def verificar_conexion_supabase(db_manager: SupabaseManager) -> Dict:
    """Verificar conectividad con Supabase"""
    imprimir_separador("VERIFICACIÓN DE CONECTIVIDAD")
    
    try:
        # Verificar estado de conexión
        estado = {
            "modo_offline": db_manager.modo_offline,
            "url_supabase": db_manager.supabase_url,
            "conexion_pg": db_manager.pg_connection is not None,
            "cliente_supabase": db_manager.supabase_client is not None,
            "ultima_conexion": db_manager.ultima_conexion
        }
        
        imprimir_resultado("Estado de Conexión", estado)
        
        # Obtener estadísticas
        stats = db_manager.obtener_estadisticas()
        imprimir_resultado("Estadísticas de la Base de Datos", stats)
        
        return {"success": True, "estado": estado, "estadisticas": stats}
        
    except Exception as e:
        error_info = {"error": str(e), "tipo": type(e).__name__}
        imprimir_resultado("Error de Conexión", error_info)
        return {"success": False, "error": error_info}

def buscar_cotizacion_especifica(db_manager: SupabaseManager, numero_cotizacion: str) -> Dict:
    """Buscar cotización específica"""
    imprimir_separador(f"BÚSQUEDA DE COTIZACIÓN: {numero_cotizacion}")
    
    try:
        # Buscar cotización específica
        resultado = db_manager.obtener_cotizacion(numero_cotizacion)
        
        if resultado.get('encontrado'):
            cotizacion = resultado.get('item', {})
            
            print("[OK] Cotización ENCONTRADA")
            imprimir_resultado("Datos Básicos", {
                "Número": cotizacion.get('numeroCotizacion'),
                "Fecha Creación": cotizacion.get('fechaCreacion'),
                "Timestamp": cotizacion.get('timestamp'),
                "Usuario": cotizacion.get('usuario'),
                "Revisión": cotizacion.get('revision')
            })
            
            # Datos generales
            datos_generales = cotizacion.get('datosGenerales', {})
            imprimir_resultado("Datos Generales", {
                "Cliente": datos_generales.get('cliente'),
                "Vendedor": datos_generales.get('vendedor'),
                "Proyecto": datos_generales.get('proyecto'),
                "Atención A": datos_generales.get('atencionA'),
                "Contacto": datos_generales.get('contacto'),
                "Email": datos_generales.get('email')
            })
            
            # Items
            items = cotizacion.get('items', [])
            print(f"  Items de la Cotización: {len(items)} elementos")
            if items:
                for i, item in enumerate(items[:3]):  # Mostrar solo primeros 3
                    print(f"    [{i+1}] {item.get('descripcion', 'Sin descripción')[:50]}...")
                if len(items) > 3:
                    print(f"    ... y {len(items) - 3} items más")
            print()
            
            return {"success": True, "encontrada": True, "cotizacion": cotizacion}
            
        else:
            print("[ERROR] Cotización NO ENCONTRADA")
            error_msg = resultado.get('error', 'Razón desconocida')
            imprimir_resultado("Detalles del Error", {"mensaje": error_msg})
            return {"success": True, "encontrada": False, "error": error_msg}
            
    except Exception as e:
        error_info = {"error": str(e), "tipo": type(e).__name__}
        print(f"[ERROR] Error buscando cotización: {e}")
        imprimir_resultado("Error de Búsqueda", error_info)
        return {"success": False, "error": error_info}

def verificar_pdf_storage(db_manager: SupabaseManager, numero_cotizacion: str) -> Dict:
    """Verificar si existe PDF en Supabase Storage"""
    imprimir_separador(f"VERIFICACIÓN DE PDF: {numero_cotizacion}")
    
    try:
        if db_manager.modo_offline:
            print("[WARNING] Modo offline - No se puede verificar PDF en Supabase Storage")
            return {"success": False, "error": "Modo offline"}
        
        # Verificar tabla pdf_storage
        cursor = db_manager.pg_connection.cursor()
        
        # Buscar PDF por número de cotización
        cursor.execute("""
            SELECT id, numero_cotizacion, filename, file_size, 
                   created_at, pdf_data IS NOT NULL as tiene_datos
            FROM pdf_storage 
            WHERE numero_cotizacion = %s;
        """, (numero_cotizacion,))
        
        pdf_records = cursor.fetchall()
        
        if pdf_records:
            print(f"[OK] Encontrados {len(pdf_records)} registro(s) de PDF")
            for record in pdf_records:
                imprimir_resultado("Registro PDF", {
                    "ID": record['id'],
                    "Número Cotización": record['numero_cotizacion'],
                    "Filename": record['filename'],
                    "Tamaño": record['file_size'],
                    "Fecha Creación": record['created_at'],
                    "Tiene Datos": record['tiene_datos']
                })
        else:
            print("[INFO] No se encontraron registros de PDF")
        
        # Verificar Storage usando cliente Supabase
        if db_manager.supabase_client:
            try:
                # Listar archivos en bucket (si existe)
                storage_response = db_manager.supabase_client.storage.from_("pdfs").list()
                
                if storage_response:
                    print(f"[OK] Bucket 'pdfs' contiene {len(storage_response)} archivos")
                    
                    # Buscar archivo específico
                    archivo_encontrado = None
                    for archivo in storage_response:
                        if numero_cotizacion in archivo['name']:
                            archivo_encontrado = archivo
                            break
                    
                    if archivo_encontrado:
                        imprimir_resultado("Archivo en Storage", archivo_encontrado)
                    else:
                        print(f"[INFO] No se encontró archivo con nombre que contenga: {numero_cotizacion}")
                else:
                    print("[INFO] Bucket 'pdfs' vacío o no existe")
                    
            except Exception as storage_error:
                print(f"[WARNING] Error accediendo a Storage: {storage_error}")
        
        cursor.close()
        return {"success": True, "registros_pdf": len(pdf_records)}
        
    except Exception as e:
        error_info = {"error": str(e), "tipo": type(e).__name__}
        print(f"[ERROR] Error verificando PDF: {e}")
        imprimir_resultado("Error PDF", error_info)
        return {"success": False, "error": error_info}

def listar_ultimas_cotizaciones(db_manager: SupabaseManager, limite: int = 10) -> Dict:
    """Listar últimas cotizaciones creadas"""
    imprimir_separador(f"ÚLTIMAS {limite} COTIZACIONES")
    
    try:
        # Obtener últimas cotizaciones
        resultado = db_manager.obtener_todas_cotizaciones(page=1, per_page=limite)
        
        if resultado.get('resultados'):
            cotizaciones = resultado['resultados']
            total = resultado.get('total', 0)
            
            print(f"[OK] Mostrando {len(cotizaciones)} de {total} cotizaciones totales")
            print()
            
            for i, cot in enumerate(cotizaciones, 1):
                datos_generales = cot.get('datosGenerales', {})
                print(f"{i:2d}. {cot.get('numeroCotizacion', 'Sin número')}")
                print(f"     Cliente: {datos_generales.get('cliente', 'N/A')}")
                print(f"     Vendedor: {datos_generales.get('vendedor', 'N/A')}")
                print(f"     Proyecto: {datos_generales.get('proyecto', 'N/A')}")
                print(f"     Fecha: {cot.get('fechaCreacion', 'N/A')}")
                print(f"     Items: {len(cot.get('items', []))}")
                print()
            
            return {"success": True, "cotizaciones": cotizaciones, "total": total}
        else:
            print("[INFO] No se encontraron cotizaciones")
            error_msg = resultado.get('error', 'Sin resultados')
            return {"success": True, "cotizaciones": [], "error": error_msg}
            
    except Exception as e:
        error_info = {"error": str(e), "tipo": type(e).__name__}
        print(f"[ERROR] Error listando cotizaciones: {e}")
        imprimir_resultado("Error Listado", error_info)
        return {"success": False, "error": error_info}

def buscar_cotizaciones_similares(db_manager: SupabaseManager, termino_busqueda: str) -> Dict:
    """Buscar cotizaciones que contengan un término específico"""
    imprimir_separador(f"BÚSQUEDA SIMILAR: '{termino_busqueda}'")
    
    try:
        resultado = db_manager.buscar_cotizaciones(termino_busqueda, page=1, per_page=20)
        
        if resultado.get('resultados'):
            cotizaciones = resultado['resultados']
            total = resultado.get('total', 0)
            
            print(f"[OK] Encontradas {len(cotizaciones)} cotizaciones de {total} total")
            print()
            
            for i, cot in enumerate(cotizaciones, 1):
                datos_generales = cot.get('datosGenerales', {})
                print(f"{i:2d}. {cot.get('numeroCotizacion', 'Sin número')}")
                print(f"     Cliente: {datos_generales.get('cliente', 'N/A')}")
                print(f"     Vendedor: {datos_generales.get('vendedor', 'N/A')}")
                print()
            
            return {"success": True, "encontradas": len(cotizaciones)}
        else:
            print("[INFO] No se encontraron cotizaciones similares")
            return {"success": True, "encontradas": 0}
            
    except Exception as e:
        error_info = {"error": str(e), "tipo": type(e).__name__}
        print(f"[ERROR] Error en búsqueda similar: {e}")
        return {"success": False, "error": error_info}

def main():
    """Función principal del diagnóstico"""
    
    print("SCRIPT DE VERIFICACIÓN DE COTIZACIÓN CWS")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cotización objetivo: BMW-CWS-CM-001-R1-GROW")
    
    # Inicializar manager
    try:
        db_manager = SupabaseManager()
    except Exception as e:
        print(f"[ERROR] Error inicializando SupabaseManager: {e}")
        return
    
    resultados = {}
    
    try:
        # 1. Verificar conectividad
        resultados['conectividad'] = verificar_conexion_supabase(db_manager)
        
        # 2. Buscar cotización específica
        numero_objetivo = "BMW-CWS-CM-001-R1-GROW"
        resultados['cotizacion_especifica'] = buscar_cotizacion_especifica(db_manager, numero_objetivo)
        
        # 3. Verificar PDF
        resultados['pdf_storage'] = verificar_pdf_storage(db_manager, numero_objetivo)
        
        # 4. Listar últimas cotizaciones
        resultados['ultimas_cotizaciones'] = listar_ultimas_cotizaciones(db_manager, 10)
        
        # 5. Buscar cotizaciones similares (por BMW)
        resultados['busqueda_similar'] = buscar_cotizaciones_similares(db_manager, "BMW")
        
        # 6. También buscar por CM (parte del número)
        resultados['busqueda_cm'] = buscar_cotizaciones_similares(db_manager, "CM")
        
    except Exception as e:
        print(f"[ERROR] Error durante el diagnóstico: {e}")
    
    finally:
        # Cerrar conexiones
        try:
            db_manager.close()
            print("[OK] Conexiones cerradas correctamente")
        except:
            pass
    
    # Resumen final
    imprimir_separador("RESUMEN DEL DIAGNÓSTICO")
    
    # Verificar si la cotización fue encontrada
    cotizacion_encontrada = (resultados.get('cotizacion_especifica', {}).get('encontrada', False))
    pdf_encontrado = (resultados.get('pdf_storage', {}).get('success', False) and 
                     resultados.get('pdf_storage', {}).get('registros_pdf', 0) > 0)
    
    print(f"Cotización BMW-CWS-CM-001-R1-GROW:")
    print(f"   - Base de Datos: {'ENCONTRADA' if cotizacion_encontrada else 'NO ENCONTRADA'}")
    print(f"   - PDF Storage: {'ENCONTRADO' if pdf_encontrado else 'NO ENCONTRADO'}")
    
    # Estadísticas generales
    stats = resultados.get('conectividad', {}).get('estadisticas', {})
    if stats:
        print(f"\nEstadísticas generales:")
        print(f"   - Total cotizaciones: {stats.get('total_cotizaciones', 'N/A')}")
        print(f"   - Modo: {stats.get('modo', 'N/A')}")
        print(f"   - Fuente: {stats.get('fuente', 'N/A')}")
    
    # Búsquedas similares
    similares_bmw = resultados.get('busqueda_similar', {}).get('encontradas', 0)
    similares_cm = resultados.get('busqueda_cm', {}).get('encontradas', 0)
    
    print(f"\nBúsquedas relacionadas:")
    print(f"   - Cotizaciones con 'BMW': {similares_bmw}")
    print(f"   - Cotizaciones con 'CM': {similares_cm}")
    
    print("\n" + "="*60)
    print("DIAGNÓSTICO COMPLETADO")
    print("="*60)

if __name__ == "__main__":
    main()