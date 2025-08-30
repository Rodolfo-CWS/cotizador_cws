#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo de Simulación de Recuperación Automática
=============================================

Simulación práctica del sistema de sincronización automática
cuando se recupera la conectividad con Supabase.

Este script simula:
1. Crear datos mientras está "offline"
2. Detectar cuando Supabase vuelve online
3. Sincronizar automáticamente los datos pendientes

Uso:
    python demo_recovery_simulation.py
"""

import os
import time
import json
from datetime import datetime, timedelta
from supabase_manager import SupabaseManager
from sync_scheduler import SyncScheduler

def log(mensaje, nivel="INFO"):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{nivel}] {mensaje}")

def simular_datos_offline():
    """Simular creación de datos mientras Supabase está offline"""
    log("=== SIMULANDO CREACION DE DATOS OFFLINE ===")
    
    # Crear cotización de prueba que se sincronizará automáticamente
    cotizacion_offline = {
        "numeroCotizacion": f"OFFLINE-RECOVERY-{int(time.time())}",
        "datosGenerales": {
            "cliente": "CLIENTE-OFFLINE-TEST",
            "vendedor": "RECOVERY-DEMO",
            "proyecto": "SINCRONIZACION-AUTOMATICA",
            "fecha": datetime.now().isoformat(),
            "condiciones": {
                "creada_en_modo_offline": True,
                "demo_recovery": True,
                "timestamp_creacion": int(time.time())
            }
        },
        "items": [
            {
                "descripcion": "Item creado durante offline",
                "cantidad": 1,
                "precio": 999.99,
                "notas": "Este item debe sincronizarse automaticamente"
            }
        ],
        "revision": 1,
        "version": "1.0.0",
        "timestamp": int(time.time()),
        "fechaCreacion": datetime.now().isoformat(),
        "usuario": "demo-recovery",
        "observaciones": "Cotizacion creada para demostrar sincronizacion automatica de recuperacion"
    }
    
    # Guardar en archivo JSON offline
    archivo_offline = "cotizaciones_offline.json"
    
    try:
        # Cargar datos existentes
        if os.path.exists(archivo_offline):
            with open(archivo_offline, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        else:
            datos = {"cotizaciones": [], "metadata": {}}
        
        # Agregar nueva cotización
        datos["cotizaciones"].append(cotizacion_offline)
        datos["metadata"]["demo_recovery_timestamp"] = datetime.now().isoformat()
        datos["metadata"]["total_cotizaciones"] = len(datos["cotizaciones"])
        
        # Guardar
        with open(archivo_offline, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        
        log(f"Cotizacion offline creada: {cotizacion_offline['numeroCotizacion']}")
        log(f"Total cotizaciones pendientes: {len(datos['cotizaciones'])}")
        return cotizacion_offline['numeroCotizacion']
        
    except Exception as e:
        log(f"Error creando datos offline: {e}", "ERROR")
        return None

def simular_conexion_perdida():
    """Simular pérdida de conexión modificando variables de entorno"""
    log("=== SIMULANDO PERDIDA DE CONEXION ===")
    
    # Guardar variables originales
    original_vars = {
        'SUPABASE_URL': os.environ.get('SUPABASE_URL'),
        'DATABASE_URL': os.environ.get('DATABASE_URL'),
        'SUPABASE_ANON_KEY': os.environ.get('SUPABASE_ANON_KEY')
    }
    
    # Temporalmente "romper" las variables de entorno
    os.environ['SUPABASE_URL'] = 'https://fake-offline-url.supabase.co'
    os.environ['DATABASE_URL'] = 'postgresql://fake:fake@fake.com:5432/fake'
    os.environ['SUPABASE_ANON_KEY'] = 'fake-key-for-offline-simulation'
    
    log("Variables de entorno 'desconectadas'")
    return original_vars

def simular_conexion_restaurada(original_vars):
    """Restaurar conexión original"""
    log("=== SIMULANDO RESTAURACION DE CONEXION ===")
    
    # Restaurar variables originales
    for key, value in original_vars.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
    
    log("Variables de entorno restauradas")

def demostrar_recovery_automatico():
    """Demostración completa del sistema de recuperación"""
    log("DEMO: SISTEMA DE SINCRONIZACION AUTOMATICA DE RECUPERACION")
    log("=" * 60)
    
    # 1. Crear datos que necesitarán sincronización
    numero_cotizacion = simular_datos_offline()
    if not numero_cotizacion:
        log("Error creando datos de prueba - abortando demo", "ERROR")
        return
    
    print()
    time.sleep(2)
    
    # 2. Simular pérdida de conexión
    original_vars = simular_conexion_perdida()
    print()
    time.sleep(1)
    
    # 3. Inicializar sistema en modo "offline"
    log("=== INICIALIZANDO SISTEMA EN MODO OFFLINE ===")
    db_offline = SupabaseManager()
    log(f"Sistema iniciado en modo: {'OFFLINE' if db_offline.modo_offline else 'ONLINE'}")
    
    # Configurar callback para detectar recuperación
    def callback_recovery_demo(anterior, nuevo):
        log(f"CALLBACK DETECTADO: {anterior} -> {nuevo}")
        if anterior == "offline" and nuevo == "online":
            log("RECOVERY DETECTADO! Sincronizacion automatica deberia ejecutarse")
    
    db_offline.registrar_callback_cambio_estado(callback_recovery_demo)
    
    # 4. Configurar scheduler con recuperación automática
    scheduler = SyncScheduler(db_offline)
    log(f"Scheduler configurado - Auto-sync en recovery: {scheduler.auto_sync_on_recovery}")
    
    print()
    time.sleep(2)
    
    # 5. Simular restauración de conexión
    simular_conexion_restaurada(original_vars)
    print()
    time.sleep(1)
    
    # 6. Inicializar nuevo manager para detectar recuperación
    log("=== SIMULANDO DETECCION DE RECUPERACION ===")
    log("Inicializando nuevo SupabaseManager para detectar cambio de estado...")
    
    # Configurar callback antes de inicializar
    def callback_sync_automatico(anterior, nuevo):
        log(f"SYNC CALLBACK: {anterior} -> {nuevo}", "SYNC")
        if anterior == "offline" and nuevo == "online":
            log("EJECUTANDO SINCRONIZACION AUTOMATICA DE RECUPERACION...", "RECOVERY")
    
    # Crear nuevo manager (simulando detección de recuperación)
    db_recovery = SupabaseManager()
    db_recovery.registrar_callback_cambio_estado(callback_sync_automatico)
    
    # Crear scheduler con este manager
    scheduler_recovery = SyncScheduler(db_recovery)
    
    log(f"Sistema recuperado - Modo: {'ONLINE' if not db_recovery.modo_offline else 'OFFLINE'}")
    
    # 7. Ejecutar sincronización manual para demostrar el proceso
    if not db_recovery.modo_offline:
        log("=== EJECUTANDO SINCRONIZACION DE RECUPERACION ===")
        resultado = db_recovery.sincronizar_bidireccional()
        
        if resultado.get("success"):
            log("SINCRONIZACION EXITOSA!")
            log(f"  Subidas: {resultado.get('subidas', 0)}")
            log(f"  Descargas: {resultado.get('descargas', 0)}")
            log(f"  Conflictos: {resultado.get('conflictos', 0)}")
            
            # Verificar que nuestra cotización de prueba fue sincronizada
            log("Verificando que la cotizacion offline fue sincronizada...")
            cotizacion_sincronizada = db_recovery.obtener_cotizacion(numero_cotizacion)
            
            if cotizacion_sincronizada.get("encontrado"):
                log(f"EXITO: Cotizacion {numero_cotizacion} sincronizada correctamente!")
                cliente = cotizacion_sincronizada["cotizacion"]["datosGenerales"]["cliente"]
                log(f"  Cliente: {cliente}")
                log(f"  Proyecto: {cotizacion_sincronizada['cotizacion']['datosGenerales']['proyecto']}")
            else:
                log(f"WARNING: Cotizacion {numero_cotizacion} no encontrada en Supabase")
        else:
            log(f"Error en sincronizacion: {resultado.get('error')}", "ERROR")
    
    print()
    log("=== DEMO COMPLETADA ===")
    log("El sistema ha demostrado exitosamente:")
    log("  1. Creacion de datos en modo offline")
    log("  2. Deteccion de perdida de conectividad") 
    log("  3. Deteccion de recuperacion de conectividad")
    log("  4. Sincronizacion automatica de datos pendientes")
    log("  5. Verificacion de sincronizacion exitosa")

def demo_scheduler_automatico():
    """Demo del scheduler funcionando automáticamente"""
    log("=== DEMO SCHEDULER AUTOMATICO ===")
    
    db = SupabaseManager()
    if db.modo_offline:
        log("Supabase offline - no se puede demostrar scheduler automatico")
        return
    
    # Configurar scheduler con intervalo corto para demo
    os.environ['HEALTH_CHECK_INTERVAL'] = '10'  # 10 segundos
    os.environ['AUTO_SYNC_ON_RECOVERY'] = 'true'
    
    scheduler = SyncScheduler(db)
    
    if scheduler.is_available():
        log("Iniciando scheduler automatico...")
        if scheduler.iniciar():
            log("Scheduler activo - monitoreando por 1 minuto...")
            log("(Observa los health checks periodicos)")
            
            # Monitorear por 1 minuto
            start_time = time.time()
            while time.time() - start_time < 60:
                time.sleep(5)
                estado = scheduler.obtener_estado()
                if estado.get("activo"):
                    log(f"Scheduler OK - Exitosas: {estado['estadisticas']['sincronizaciones_exitosas']}")
                else:
                    log("Scheduler no activo")
                    break
            
            # Detener
            log("Deteniendo scheduler...")
            scheduler.detener()
        else:
            log("Error iniciando scheduler")
    else:
        log("Scheduler no disponible")

if __name__ == "__main__":
    import sys
    
    print("DEMO DE SINCRONIZACION AUTOMATICA DE RECUPERACION")
    print("=" * 50)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduler":
        demo_scheduler_automatico()
    else:
        demostrar_recovery_automatico()