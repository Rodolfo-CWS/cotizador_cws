#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de Sistema de Sincronización Automática
============================================

Prueba el sistema de detección de recuperación de Supabase y
sincronización automática cuando se recupera la conectividad.

Funcionalidades probadas:
- Detección de cambios de estado Supabase
- Health check periódico
- Callbacks de cambio de estado
- Sincronización automática en recuperación
"""

import os
import time
import json
from datetime import datetime
from supabase_manager import SupabaseManager
from sync_scheduler import SyncScheduler

def print_status(mensaje, tipo="INFO"):
    """Imprimir mensaje con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{tipo}] {mensaje}")

def test_state_detection():
    """Test 1: Detección de cambios de estado"""
    print_status("=== TEST 1: DETECCIÓN DE CAMBIOS DE ESTADO ===")
    
    # Inicializar SupabaseManager
    db = SupabaseManager()
    
    print_status(f"Estado inicial: {'online' if not db.modo_offline else 'offline'}")
    print_status(f"Estado anterior registrado: {db.estado_anterior}")
    
    # Registrar callback de prueba
    def callback_prueba(anterior, nuevo):
        print_status(f"CALLBACK EJECUTADO: {anterior} -> {nuevo}", "CALLBACK")
    
    db.registrar_callback_cambio_estado(callback_prueba)
    
    # Ejecutar health check manual
    print_status("Ejecutando health check manual...")
    status = db.health_check()
    
    print_status("Resultado health check:")
    for key, value in status.items():
        print_status(f"   {key}: {value}")
    
    return db

def test_scheduler_integration():
    """Test 2: Integración con SyncScheduler"""
    print_status("=== TEST 2: INTEGRACIÓN SYNC SCHEDULER ===")
    
    # Crear instancia de database manager
    db = SupabaseManager()
    
    # Crear scheduler
    scheduler = SyncScheduler(db)
    
    print_status(f"Scheduler disponible: {scheduler.is_available()}")
    print_status(f"Auto-sync habilitado: {scheduler.auto_sync_enabled}")
    print_status(f"Sync en recuperación: {scheduler.auto_sync_on_recovery}")
    print_status(f"Health check interval: {scheduler.health_check_interval}s")
    
    if scheduler.is_available():
        print_status("Iniciando scheduler...")
        if scheduler.iniciar():
            print_status("Scheduler iniciado correctamente")
            
            # Dejar correr por unos segundos para ver health checks
            print_status("Monitoreando por 10 segundos...")
            time.sleep(10)
            
            # Obtener estado
            estado = scheduler.obtener_estado()
            print_status("Estado del scheduler:")
            for key, value in estado.items():
                if key != "ultima_sincronizacion_resultado":
                    print_status(f"   {key}: {value}")
            
            # Detener
            print_status("Deteniendo scheduler...")
            scheduler.detener()
            print_status("Scheduler detenido")
            
        else:
            print_status("Error iniciando scheduler")
    else:
        print_status("Scheduler no disponible")
    
    return scheduler

def test_manual_sync_trigger():
    """Test 3: Trigger manual de sincronización"""
    print_status("=== TEST 3: TRIGGER MANUAL DE SINCRONIZACIÓN ===")
    
    db = SupabaseManager()
    
    if not db.modo_offline:
        print_status("Ejecutando sincronización bidireccional manual...")
        resultado = db.sincronizar_bidireccional()
        
        print_status("Resultado sincronización:")
        print_status(f"   success: {resultado.get('success')}")
        print_status(f"   mensaje: {resultado.get('mensaje', resultado.get('error'))}")
        print_status(f"   subidas: {resultado.get('subidas', 0)}")
        print_status(f"   descargas: {resultado.get('descargas', 0)}")
        print_status(f"   conflictos: {resultado.get('conflictos', 0)}")
        
    else:
        print_status("WARNING: Supabase offline - no se puede probar sincronizacion manual")

def test_recovery_simulation():
    """Test 4: Simulación de recuperación (requiere intervención manual)"""
    print_status("=== TEST 4: SIMULACIÓN DE RECUPERACIÓN ===")
    
    print_status("INFO: Para probar la recuperacion automatica:")
    print_status("   1. Desconecta tu internet/VPN")
    print_status("   2. Ejecuta este script")  
    print_status("   3. Vuelve a conectar internet")
    print_status("   4. Observa los logs de detección y sync automático")
    print_status("")
    print_status("   O modifica temporalmente las variables de entorno")
    print_status("   para simular pérdida/recuperación de conectividad")

def test_offline_data_creation():
    """Test 5: Crear datos en modo offline para probar sync posterior"""
    print_status("=== TEST 5: CREAR DATOS EN MODO OFFLINE ===")
    
    # Cargar datos offline actuales
    archivo_offline = "cotizaciones_offline.json"
    
    try:
        if os.path.exists(archivo_offline):
            with open(archivo_offline, 'r', encoding='utf-8') as f:
                datos_offline = json.load(f)
        else:
            datos_offline = {"cotizaciones": [], "metadata": {}}
        
        # Crear cotización de prueba para sync
        cotizacion_test = {
            "numeroCotizacion": f"TEST-SYNC-AUTO-{int(time.time())}",
            "datosGenerales": {
                "cliente": "TEST-SINCRONIZACION-AUTO",
                "vendedor": "AUTO-SYNC",
                "proyecto": "PRUEBA-RECUPERACION", 
                "fecha": datetime.now().isoformat(),
                "condiciones": {"created_for_sync_test": True}
            },
            "items": [
                {"descripcion": "Item test sync automático", "cantidad": 1, "precio": 1.0}
            ],
            "revision": 1,
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "fechaCreacion": datetime.now().isoformat(),
            "usuario": "test-auto-sync",
            "observaciones": "Cotización creada para probar sincronización automática"
        }
        
        # Agregar a los datos offline
        datos_offline["cotizaciones"].append(cotizacion_test)
        datos_offline["metadata"]["last_test_sync"] = datetime.now().isoformat()
        
        # Guardar
        with open(archivo_offline, 'w', encoding='utf-8') as f:
            json.dump(datos_offline, f, indent=2, ensure_ascii=False)
        
        print_status(f"Cotizacion de prueba agregada: {cotizacion_test['numeroCotizacion']}")
        print_status(f"Total cotizaciones offline: {len(datos_offline['cotizaciones'])}")
        print_status("Esta cotizacion se sincronizara automaticamente cuando Supabase este online")
        
    except Exception as e:
        print_status(f"Error creando datos de prueba: {e}")

def main():
    """Función principal de pruebas"""
    print_status("INICIANDO PRUEBAS DE SINCRONIZACION AUTOMATICA")
    print_status("=" * 60)
    
    try:
        # Test 1: Detección de estado
        db = test_state_detection()
        print()
        
        # Test 2: Scheduler
        scheduler = test_scheduler_integration() 
        print()
        
        # Test 3: Sync manual
        test_manual_sync_trigger()
        print()
        
        # Test 4: Simulación
        test_recovery_simulation()
        print()
        
        # Test 5: Datos offline
        test_offline_data_creation()
        print()
        
        print_status("TODAS LAS PRUEBAS COMPLETADAS")
        print_status("=" * 60)
        
        # Resumen final
        print_status("RESUMEN DEL SISTEMA:")
        print_status(f"   Supabase: {'ONLINE' if not db.modo_offline else 'OFFLINE'}")
        print_status(f"   Health check: {'IMPLEMENTADO' if hasattr(db, 'health_check') else 'FALTA'}")
        print_status(f"   Callbacks: {'FUNCIONANDO' if db.callbacks_cambio_estado else 'VACIO'}")
        print_status(f"   Scheduler: {'DISPONIBLE' if scheduler.is_available() else 'NO DISPONIBLE'}")
        print_status(f"   Auto-sync: {'HABILITADO' if scheduler.auto_sync_on_recovery else 'DESHABILITADO'}")
        
    except Exception as e:
        print_status(f"ERROR DURANTE PRUEBAS: {e}", "ERROR")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()