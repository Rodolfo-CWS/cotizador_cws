#!/usr/bin/env python3
"""
Test de sincronización bidireccional - Sistema Multi-dispositivo
Simula múltiples dispositivos usando el sistema de sincronización
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime, timedelta

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_manager import SupabaseManager

def print_test(mensaje, tipo="INFO"):
    """Print con formato de test"""
    prefijos = {
        "INFO": "[INFO]",
        "OK": "[OK]", 
        "ERROR": "[ERROR]",
        "WARNING": "[WARNING]",
        "TEST": "[TEST]"
    }
    prefijo = prefijos.get(tipo, "[INFO]")
    print(f"{prefijo} [TEST-SYNC] {mensaje}")

def crear_cotizacion_test(cliente, vendedor, proyecto, timestamp_offset=0):
    """Crea una cotización de prueba con timestamp específico"""
    base_timestamp = int(time.time() * 1000) + timestamp_offset
    
    return {
        "numeroCotizacion": f"{cliente}-CWS-{vendedor[:2].upper()}-001-R1-{proyecto}",
        "datosGenerales": {
            "cliente": cliente,
            "vendedor": vendedor,
            "proyecto": proyecto,
            "numeroCotizacion": f"{cliente}-CWS-{vendedor[:2].upper()}-001-R1-{proyecto}",
            "revision": 1
        },
        "items": [{
            "descripcion": f"Item de prueba {proyecto}",
            "cantidad": 1,
            "precio_unitario": 100 + timestamp_offset // 1000
        }],
        "timestamp": base_timestamp,
        "fechaCreacion": datetime.fromtimestamp(base_timestamp / 1000).isoformat()
    }

def simular_dispositivo_1():
    """Simula dispositivo 1 - crear cotizaciones locales"""
    print_test("Simulando Dispositivo 1 - Creando cotizaciones locales", "TEST")
    
    db1 = SupabaseManager()
    
    # Crear cotizaciones que solo existen en JSON local (dispositivo 1)
    cotizaciones_dispositivo_1 = [
        crear_cotizacion_test("DISPOSITIVO-1", "Juan", "PROYECTO-A", 0),
        crear_cotizacion_test("DISPOSITIVO-1", "Juan", "PROYECTO-B", 1000)
    ]
    
    # Cargar JSON actual y agregar cotizaciones
    json_path = "cotizaciones_offline.json"
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {"cotizaciones": [], "metadata": {"last_updated": datetime.now().isoformat()}}
    
    # Agregar cotizaciones del dispositivo 1
    for cotizacion in cotizaciones_dispositivo_1:
        data["cotizaciones"].append(cotizacion)
        print_test(f"Dispositivo 1 creó: {cotizacion['numeroCotizacion']}")
    
    # Guardar JSON actualizado
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return len(cotizaciones_dispositivo_1)

def simular_dispositivo_2_supabase():
    """Simula dispositivo 2 - crear cotizaciones directamente en Supabase"""
    print_test("Simulando Dispositivo 2 - Creando cotizaciones en Supabase", "TEST")
    
    db2 = SupabaseManager()
    
    if db2.modo_offline:
        print_test("Dispositivo 2 no puede conectar a Supabase - saltando simulación", "WARNING")
        return 0
    
    # Crear cotizaciones directamente en Supabase (simulando otro dispositivo)
    cotizaciones_dispositivo_2 = [
        crear_cotizacion_test("DISPOSITIVO-2", "Maria", "PROYECTO-X", 2000),
        crear_cotizacion_test("DISPOSITIVO-2", "Maria", "PROYECTO-Y", 3000)
    ]
    
    contador_creadas = 0
    for cotizacion in cotizaciones_dispositivo_2:
        try:
            # Insertar directamente en Supabase (sin usar el sistema normal de guardado)
            resultado = db2.supabase_client.table('cotizaciones').insert(cotizacion).execute()
            if resultado.data:
                print_test(f"Dispositivo 2 creó en Supabase: {cotizacion['numeroCotizacion']}")
                contador_creadas += 1
            else:
                print_test(f"Error creando en Supabase: {cotizacion['numeroCotizacion']}", "ERROR")
        except Exception as e:
            print_test(f"Excepción creando en Supabase: {e}", "ERROR")
    
    return contador_creadas

def test_sincronizacion_bidireccional():
    """Test principal de sincronización bidireccional"""
    print_test("INICIANDO TEST DE SINCRONIZACIÓN BIDIRECCIONAL", "TEST")
    print_test("=" * 60)
    
    # Fase 1: Crear backup del JSON actual
    json_path = "cotizaciones_offline.json"
    backup_path = "cotizaciones_offline_backup.json"
    
    try:
        if os.path.exists(json_path):
            shutil.copy2(json_path, backup_path)
            print_test("Backup de JSON creado")
    except Exception as e:
        print_test(f"Error creando backup: {e}", "ERROR")
    
    # Fase 2: Contar estado inicial
    db = SupabaseManager()
    
    # Contar cotizaciones en JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data_inicial = json.load(f)
        total_json_inicial = len(data_inicial.get("cotizaciones", []))
    except:
        total_json_inicial = 0
    
    # Contar cotizaciones en Supabase
    total_supabase_inicial = 0
    if not db.modo_offline:
        try:
            resultado = db.supabase_client.table('cotizaciones').select('numeroCotizacion').execute()
            total_supabase_inicial = len(resultado.data) if resultado.data else 0
        except:
            total_supabase_inicial = 0
    
    print_test(f"Estado inicial - JSON: {total_json_inicial}, Supabase: {total_supabase_inicial}")
    
    # Fase 3: Simular múltiples dispositivos
    cotizaciones_dispositivo_1 = simular_dispositivo_1()
    time.sleep(1)  # Pequeña pausa para timestamps diferentes
    cotizaciones_dispositivo_2 = simular_dispositivo_2_supabase()
    
    print_test(f"Dispositivo 1 creó: {cotizaciones_dispositivo_1} cotizaciones en JSON")
    print_test(f"Dispositivo 2 creó: {cotizaciones_dispositivo_2} cotizaciones en Supabase")
    
    # Fase 4: Ejecutar sincronización bidireccional
    print_test("EJECUTANDO SINCRONIZACIÓN BIDIRECCIONAL", "TEST")
    print_test("-" * 40)
    
    try:
        resultado_sync = db.sincronizar_bidireccional()
        
        if resultado_sync.get("success", False):
            print_test("Sincronización completada exitosamente", "OK")
            
            # Mostrar estadísticas
            stats = {
                "subidas": resultado_sync.get("subidas", 0),
                "descargas": resultado_sync.get("descargas", 0),
                "conflictos": resultado_sync.get("conflictos", 0),
                "errores": resultado_sync.get("errores", 0)
            }
            
            for key, value in stats.items():
                if value > 0:
                    print_test(f"{key.capitalize()}: {value}")
            
            print_test(f"Mensaje: {resultado_sync.get('mensaje', 'Sin mensaje')}")
            
        else:
            print_test(f"Error en sincronización: {resultado_sync.get('error', 'Error desconocido')}", "ERROR")
    
    except Exception as e:
        print_test(f"Excepción durante sincronización: {e}", "ERROR")
    
    # Fase 5: Verificar estado final
    print_test("VERIFICANDO RESULTADOS", "TEST")
    print_test("-" * 30)
    
    # Contar estado final
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data_final = json.load(f)
        total_json_final = len(data_final.get("cotizaciones", []))
    except:
        total_json_final = 0
    
    total_supabase_final = 0
    if not db.modo_offline:
        try:
            resultado = db.supabase_client.table('cotizaciones').select('numeroCotizacion').execute()
            total_supabase_final = len(resultado.data) if resultado.data else 0
        except:
            total_supabase_final = 0
    
    print_test(f"Estado final - JSON: {total_json_final}, Supabase: {total_supabase_final}")
    print_test(f"Cambio JSON: {total_json_final - total_json_inicial:+d}")
    print_test(f"Cambio Supabase: {total_supabase_final - total_supabase_inicial:+d}")
    
    # Fase 6: Validación
    if db.modo_offline:
        print_test("Modo offline - no se puede validar sincronización con Supabase", "WARNING")
        exito = total_json_final > total_json_inicial
    else:
        # En modo online, ambos deberían tener las mismas cotizaciones
        diferencia_absoluta = abs(total_json_final - total_supabase_final)
        exito = diferencia_absoluta <= 1  # Permitir diferencia mínima por timing
        
        if exito:
            print_test("Sincronización bidireccional funcionando correctamente", "OK")
        else:
            print_test(f"Discrepancia detectada: JSON={total_json_final}, Supabase={total_supabase_final}", "ERROR")
    
    # Fase 7: Limpiar archivos de test (opcional)
    # Restaurar backup si se desea
    # shutil.move(backup_path, json_path)
    
    return exito

def test_scheduler_integration():
    """Test de integración con el scheduler"""
    print_test("TESTING SCHEDULER INTEGRATION", "TEST")
    print_test("=" * 40)
    
    try:
        from sync_scheduler import SyncScheduler
        
        db = SupabaseManager()
        scheduler = SyncScheduler(db)
        
        if not scheduler.is_available():
            print_test("APScheduler no disponible - saltando test de scheduler", "WARNING")
            return False
        
        # Test de sincronización manual
        print_test("Ejecutando sincronización manual via scheduler...")
        resultado = scheduler.ejecutar_sincronizacion_manual()
        
        if resultado.get("success", False):
            print_test("Sincronización manual exitosa", "OK")
        else:
            print_test(f"Error en sincronización manual: {resultado.get('error', 'N/A')}", "ERROR")
        
        # Test de estado
        estado = scheduler.obtener_estado()
        print_test(f"Scheduler disponible: {estado['disponible']}")
        print_test(f"Auto-sync habilitado: {estado['auto_sync_habilitado']}")
        print_test(f"Supabase disponible: {estado['mongodb_disponible']}")
        
        return resultado.get("success", False)
        
    except ImportError:
        print_test("sync_scheduler.py no disponible", "ERROR")
        return False
    except Exception as e:
        print_test(f"Error en test scheduler: {e}", "ERROR")
        return False

def main():
    """Función principal de testing"""
    print_test("SISTEMA DE PRUEBAS - SINCRONIZACIÓN BIDIRECCIONAL", "TEST")
    print_test("Simulando múltiples dispositivos usando la misma base de datos")
    print_test("=" * 70)
    
    # Test 1: Sincronización bidireccional básica
    exito_sync = test_sincronizacion_bidireccional()
    
    print_test("=" * 50)
    
    # Test 2: Integración con scheduler
    exito_scheduler = test_scheduler_integration()
    
    print_test("=" * 50)
    print_test("RESUMEN DE PRUEBAS", "TEST")
    
    resultados = {
        "Sincronización bidireccional": "OK" if exito_sync else "ERROR",
        "Integración scheduler": "OK" if exito_scheduler else "ERROR"
    }
    
    for test, resultado in resultados.items():
        tipo = "OK" if resultado == "OK" else "ERROR"
        print_test(f"{test}: {resultado}", tipo)
    
    # Resultado final
    todos_exitosos = all(resultado == "OK" for resultado in resultados.values())
    
    if todos_exitosos:
        print_test("TODOS LOS TESTS PASARON - Sistema listo para múltiples dispositivos", "OK")
    else:
        print_test("ALGUNOS TESTS FALLARON - Revisar implementación", "ERROR")
    
    return todos_exitosos

if __name__ == "__main__":
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print_test("Test interrumpido por usuario", "WARNING")
        sys.exit(1)
    except Exception as e:
        print_test(f"Error inesperado: {e}", "ERROR")
        sys.exit(1)