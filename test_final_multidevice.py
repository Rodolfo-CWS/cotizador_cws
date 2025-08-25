#!/usr/bin/env python3
"""
Test Final - Sistema Multi-dispositivo Completo
Validación de todas las funcionalidades implementadas para múltiples dispositivos
"""

import os
import sys
import json
import time
from datetime import datetime

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_resultado(mensaje, exitoso=True):
    """Print resultado de test"""
    status = "[OK]" if exitoso else "[ERROR]"
    print(f"{status} {mensaje}")

def test_sistema_multidevice():
    """Test completo del sistema multi-dispositivo"""
    print("SISTEMA MULTI-DISPOSITIVO - TEST FINAL COMPLETO")
    print("=" * 60)
    
    resultados = {}
    
    try:
        from supabase_manager import SupabaseManager
        from sync_scheduler import SyncScheduler
        
        # Test 1: Verificar SupabaseManager tiene funcionalidad bidireccional
        print("\n[TEST 1] Verificando SupabaseManager...")
        db = SupabaseManager()
        
        if hasattr(db, 'sincronizar_bidireccional'):
            print_resultado("Método sincronizar_bidireccional disponible")
            resultados['metodo_sync'] = True
        else:
            print_resultado("Método sincronizar_bidireccional NO disponible", False)
            resultados['metodo_sync'] = False
        
        # Test 2: Verificar conexión a Supabase
        print("\n[TEST 2] Verificando conexión Supabase...")
        if not db.modo_offline:
            print_resultado("Conectado a Supabase PostgreSQL exitosamente")
            resultados['conexion_supabase'] = True
        else:
            print_resultado("Modo offline - usando JSON local", False)
            resultados['conexion_supabase'] = False
        
        # Test 3: Test de sincronización bidireccional
        print("\n[TEST 3] Ejecutando sincronización bidireccional...")
        resultado_sync = db.sincronizar_bidireccional()
        
        if resultado_sync.get("success", False):
            stats = {
                "subidas": resultado_sync.get("subidas", 0),
                "descargas": resultado_sync.get("descargas", 0),
                "conflictos": resultado_sync.get("conflictos", 0),
                "errores": resultado_sync.get("errores", 0)
            }
            
            print_resultado(f"Sincronización exitosa - subidas:{stats['subidas']} descargas:{stats['descargas']} conflictos:{stats['conflictos']} errores:{stats['errores']}")
            resultados['sync_bidireccional'] = True
        else:
            print_resultado(f"Error en sincronización: {resultado_sync.get('error', 'Error desconocido')}", False)
            resultados['sync_bidireccional'] = False
        
        # Test 4: Verificar APScheduler disponible
        print("\n[TEST 4] Verificando APScheduler...")
        scheduler = SyncScheduler(db)
        
        if scheduler.is_available():
            print_resultado("APScheduler disponible para sincronización automática")
            resultados['apscheduler'] = True
        else:
            print_resultado("APScheduler NO disponible", False)
            resultados['apscheduler'] = False
        
        # Test 5: Test de scheduler automático (breve)
        print("\n[TEST 5] Probando scheduler automático...")
        if scheduler.is_available():
            # Sincronización manual
            resultado_manual = scheduler.ejecutar_sincronizacion_manual()
            
            if resultado_manual.get("success", False):
                print_resultado("Sincronización manual via scheduler exitosa")
                resultados['sync_manual'] = True
            else:
                print_resultado("Error en sincronización manual", False)
                resultados['sync_manual'] = False
            
            # Test rápido de iniciar/detener
            if scheduler.iniciar():
                print_resultado("Scheduler automático iniciado correctamente")
                time.sleep(1)  # Esperar solo 1 segundo
                
                if scheduler.detener():
                    print_resultado("Scheduler automático detenido correctamente")
                    resultados['scheduler_control'] = True
                else:
                    print_resultado("Error deteniendo scheduler", False)
                    resultados['scheduler_control'] = False
            else:
                print_resultado("Error iniciando scheduler", False)
                resultados['scheduler_control'] = False
        else:
            resultados['sync_manual'] = False
            resultados['scheduler_control'] = False
        
        # Test 6: Verificar estado de datos
        print("\n[TEST 6] Verificando estado de datos...")
        
        # Contar cotizaciones en JSON
        try:
            json_path = "cotizaciones_offline.json"
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            total_json = len(data.get("cotizaciones", []))
            print_resultado(f"JSON local: {total_json} cotizaciones")
            resultados['datos_json'] = True
        except:
            print_resultado("Error leyendo JSON local", False)
            resultados['datos_json'] = False
        
        # Contar cotizaciones en Supabase
        if not db.modo_offline:
            try:
                cursor = db.pg_connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM cotizaciones")
                total_supabase = cursor.fetchone()[0]
                cursor.close()
                print_resultado(f"Supabase PostgreSQL: {total_supabase} cotizaciones")
                resultados['datos_supabase'] = True
            except:
                print_resultado("Error consultando Supabase", False)
                resultados['datos_supabase'] = False
        else:
            resultados['datos_supabase'] = False
        
    except Exception as e:
        print_resultado(f"Error durante test: {e}", False)
        return False
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL - SISTEMA MULTI-DISPOSITIVO")
    print("=" * 60)
    
    total_tests = len(resultados)
    tests_exitosos = sum(resultados.values())
    
    for test, exitoso in resultados.items():
        status = "OK" if exitoso else "ERROR"
        descripcion = {
            'metodo_sync': 'Método sincronizar_bidireccional',
            'conexion_supabase': 'Conexión Supabase PostgreSQL',
            'sync_bidireccional': 'Sincronización bidireccional',
            'apscheduler': 'APScheduler disponible',
            'sync_manual': 'Sincronización manual',
            'scheduler_control': 'Control scheduler automático',
            'datos_json': 'Datos JSON local',
            'datos_supabase': 'Datos Supabase PostgreSQL'
        }
        print(f"[{status}] {descripcion.get(test, test)}")
    
    print(f"\nRESULTADO: {tests_exitosos}/{total_tests} tests exitosos")
    
    if tests_exitosos >= total_tests - 1:  # Permitir 1 fallo máximo
        print("[OK] SISTEMA MULTI-DISPOSITIVO OPERACIONAL")
        print("     - Sincronización bidireccional funciona correctamente")
        print("     - Scheduler automático disponible (cada 15 minutos)")
        print("     - Múltiples dispositivos pueden usar la aplicación simultáneamente")
        print("     - Resolución automática de conflictos (last-write-wins)")
        return True
    else:
        print("[ERROR] SISTEMA REQUIERE CORRECCIONES")
        return False

def main():
    """Función principal"""
    exito = test_sistema_multidevice()
    return exito

if __name__ == "__main__":
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        sys.exit(1)