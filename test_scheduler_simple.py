#!/usr/bin/env python3
"""
Test simple del scheduler automático para verificar que el método sincronizar_bidireccional existe
"""

import os
import sys
import time
import json
from datetime import datetime

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_scheduler_basic():
    """Test básico del scheduler sin emojis Unicode"""
    print("[TEST] Iniciando test básico del scheduler...")
    
    try:
        from supabase_manager import SupabaseManager
        from sync_scheduler import SyncScheduler
        
        # Crear instancias
        print("[TEST] Creando instancias...")
        db = SupabaseManager()
        scheduler = SyncScheduler(db)
        
        # Verificar que el método existe
        if hasattr(db, 'sincronizar_bidireccional'):
            print("[OK] Método sincronizar_bidireccional existe en SupabaseManager")
        else:
            print("[ERROR] Método sincronizar_bidireccional NO existe en SupabaseManager")
            return False
        
        # Verificar scheduler disponible
        if scheduler.is_available():
            print("[OK] APScheduler disponible")
        else:
            print("[WARNING] APScheduler no disponible")
            return False
        
        # Test de sincronización manual (sin iniciar scheduler automático)
        print("[TEST] Ejecutando sincronización manual...")
        resultado = scheduler.ejecutar_sincronizacion_manual()
        
        if resultado.get("success", False):
            print("[OK] Sincronización manual exitosa")
            print(f"[INFO] Mensaje: {resultado.get('mensaje', 'Sin mensaje')}")
        else:
            print(f"[ERROR] Sincronización falló: {resultado.get('error', 'Error desconocido')}")
            return False
        
        # Test de estado
        estado = scheduler.obtener_estado()
        print(f"[INFO] Scheduler disponible: {estado['disponible']}")
        print(f"[INFO] Auto-sync habilitado: {estado['auto_sync_habilitado']}")
        print(f"[INFO] Supabase disponible: {estado['mongodb_disponible']}")
        
        # Test de iniciar/detener scheduler (muy breve)
        print("[TEST] Test rápido de iniciar/detener scheduler...")
        if scheduler.iniciar():
            print("[OK] Scheduler iniciado correctamente")
            time.sleep(2)  # Esperar solo 2 segundos
            
            if scheduler.detener():
                print("[OK] Scheduler detenido correctamente")
            else:
                print("[WARNING] Error deteniendo scheduler")
        else:
            print("[WARNING] Error iniciando scheduler")
        
        print("[OK] Todos los tests del scheduler pasaron")
        return True
        
    except Exception as e:
        print(f"[ERROR] Excepción durante test: {e}")
        return False

def main():
    """Función principal"""
    print("TEST SCHEDULER BASICO - Verificacion de sincronizacion bidireccional")
    print("=" * 70)
    
    exito = test_scheduler_basic()
    
    print("=" * 50)
    if exito:
        print("[OK] TEST COMPLETADO - Scheduler listo para funcionar")
    else:
        print("[ERROR] TEST FALLIDO - Revisar implementación")
    
    return exito

if __name__ == "__main__":
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        sys.exit(1)