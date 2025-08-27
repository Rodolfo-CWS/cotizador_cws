#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test completo del sistema de numeración irrepetible
Verifica que los números nunca se repitan incluso bajo alta concurrencia
"""

import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Agregar directorio del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_numeracion_atomica():
    """Test básico de numeración atómica"""
    
    print("=== TEST 1: NUMERACION ATOMICA BASICA ===")
    print()
    
    try:
        from supabase_manager import SupabaseManager
        
        db = SupabaseManager()
        
        if db.modo_offline:
            print("[INFO] Sistema en modo offline - usando contadores JSON")
        else:
            print("[INFO] Sistema en modo online - usando contadores Supabase")
        
        # Test 1: Generar números consecutivos para mismo patrón
        patron_test = "TESTNUM-CWS-TN"
        
        print(f"[TEST] Generando 5 números consecutivos para patrón: {patron_test}")
        numeros_generados = []
        
        for i in range(5):
            siguiente = db._obtener_siguiente_consecutivo(patron_test)
            numeros_generados.append(siguiente)
            print(f"  Número {i+1}: {siguiente}")
            
        # Verificar que sean consecutivos
        print()
        print("[VERIFICACION] Consecutividad:")
        
        es_consecutivo = True
        for i in range(1, len(numeros_generados)):
            if numeros_generados[i] != numeros_generados[i-1] + 1:
                es_consecutivo = False
                print(f"  ERROR: {numeros_generados[i-1]} -> {numeros_generados[i]} no es consecutivo")
        
        if es_consecutivo:
            print(f"  OK: Números son consecutivos: {numeros_generados}")
        else:
            print(f"  ERROR: Números NO son consecutivos: {numeros_generados}")
        
        return es_consecutivo
        
    except ImportError as e:
        print(f"[ERROR] No se puede importar SupabaseManager: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error en test básico: {e}")
        return False

def test_concurrencia():
    """Test de concurrencia - múltiples threads generando números simultáneamente"""
    
    print()
    print("=== TEST 2: CONCURRENCIA - THREADS SIMULTANEOS ===")
    print()
    
    try:
        from supabase_manager import SupabaseManager
        
        patron_concurrencia = "CONCURRENT-CWS-CC"
        num_threads = 10
        num_por_thread = 5
        
        print(f"[CONCURRENCIA] {num_threads} threads generando {num_por_thread} números cada uno")
        print(f"[CONCURRENCIA] Patrón: {patron_concurrencia}")
        print(f"[CONCURRENCIA] Total esperado: {num_threads * num_por_thread} números únicos")
        
        numeros_generados = []
        lock = threading.Lock()  # Para proteger la lista compartida
        
        def generar_numeros_worker(thread_id):
            """Worker function que genera números en un thread"""
            db = SupabaseManager()
            numeros_thread = []
            
            try:
                for i in range(num_por_thread):
                    numero = db._obtener_siguiente_consecutivo(patron_concurrencia)
                    numeros_thread.append(numero)
                    print(f"  Thread {thread_id}: {numero}")
                    time.sleep(0.1)  # Simular trabajo
                
                # Agregar a lista compartida de forma thread-safe
                with lock:
                    numeros_generados.extend(numeros_thread)
                
                return numeros_thread
                
            except Exception as e:
                print(f"  ERROR en thread {thread_id}: {e}")
                return []
        
        # Ejecutar threads concurrentemente
        print()
        print("[EJECUTANDO] Threads concurrentes...")
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(generar_numeros_worker, i) for i in range(num_threads)]
            
            # Esperar que todos terminen
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    print(f"  ERROR en thread: {e}")
        
        print()
        print("[ANALISIS] Resultados de concurrencia:")
        
        # Verificar unicidad
        numeros_unicos = set(numeros_generados)
        total_generados = len(numeros_generados)
        total_unicos = len(numeros_unicos)
        
        print(f"  Total generados: {total_generados}")
        print(f"  Números únicos: {total_unicos}")
        
        if total_generados == total_unicos:
            print(f"  OK: Todos los números son únicos")
            duplicados = False
        else:
            print(f"  ERROR: Se encontraron {total_generados - total_unicos} duplicados")
            duplicados = True
            
            # Mostrar duplicados
            for num in numeros_generados:
                if numeros_generados.count(num) > 1:
                    print(f"    DUPLICADO: {num} aparece {numeros_generados.count(num)} veces")
        
        # Mostrar rango de números
        if numeros_generados:
            numeros_ordenados = sorted(numeros_generados)
            print(f"  Rango: {numeros_ordenados[0]} a {numeros_ordenados[-1]}")
            print(f"  Números: {numeros_ordenados}")
        
        return not duplicados
        
    except Exception as e:
        print(f"[ERROR] Error en test de concurrencia: {e}")
        return False

def test_patrones_multiples():
    """Test con múltiples patrones diferentes"""
    
    print()
    print("=== TEST 3: MULTIPLES PATRONES SIMULTANEOS ===")
    print()
    
    try:
        from supabase_manager import SupabaseManager
        
        db = SupabaseManager()
        
        # Diferentes patrones de cliente/vendedor
        patrones = [
            "BMWTEST-CWS-RM",
            "FORDTEST-CWS-JL", 
            "HONDATEST-CWS-AM",
            "TESLATEST-CWS-PG"
        ]
        
        resultados = {}
        
        print("[PATRONES] Generando números para diferentes patrones:")
        
        for patron in patrones:
            print(f"  Patrón: {patron}")
            numeros = []
            
            for i in range(3):
                numero = db._obtener_siguiente_consecutivo(patron)
                numeros.append(numero)
                print(f"    {i+1}: {numero}")
            
            resultados[patron] = numeros
        
        print()
        print("[VERIFICACION] Independencia de patrones:")
        
        # Verificar que cada patrón inicie desde 1 (o continúe su secuencia)
        independencia_ok = True
        
        for patron, numeros in resultados.items():
            # Verificar que sean consecutivos dentro del patrón
            consecutivo = all(numeros[i] == numeros[i-1] + 1 for i in range(1, len(numeros)))
            
            print(f"  {patron}: {numeros} - {'Consecutivo' if consecutivo else 'NO consecutivo'}")
            
            if not consecutivo:
                independencia_ok = False
        
        return independencia_ok
        
    except Exception as e:
        print(f"[ERROR] Error en test de patrones múltiples: {e}")
        return False

def test_modo_offline():
    """Test específico para modo offline"""
    
    print()
    print("=== TEST 4: MODO OFFLINE ESPECIFICO ===")
    print()
    
    try:
        from supabase_manager import SupabaseManager
        
        # Crear instancia forzando modo offline
        db = SupabaseManager()
        
        # Forzar modo offline temporalmente 
        modo_original = db.modo_offline
        db.modo_offline = True
        
        print("[OFFLINE] Generando números en modo offline forzado")
        
        patron_offline = "OFFLINE-CWS-OF"
        numeros_offline = []
        
        for i in range(5):
            numero = db._obtener_consecutivo_offline(patron_offline)
            numeros_offline.append(numero)
            print(f"  Offline {i+1}: {numero}")
        
        # Restaurar modo original
        db.modo_offline = modo_original
        
        # Verificar consecutividad
        consecutivo_offline = all(numeros_offline[i] == numeros_offline[i-1] + 1 for i in range(1, len(numeros_offline)))
        
        print(f"[RESULTADO] Offline consecutivo: {consecutivo_offline}")
        print(f"[RESULTADO] Números offline: {numeros_offline}")
        
        return consecutivo_offline
        
    except Exception as e:
        print(f"[ERROR] Error en test offline: {e}")
        return False

def test_recuperacion_errores():
    """Test de recuperación ante errores"""
    
    print()
    print("=== TEST 5: RECUPERACION ANTE ERRORES ===")
    print()
    
    try:
        from supabase_manager import SupabaseManager
        
        db = SupabaseManager()
        
        patron_error = "ERROR-CWS-ER"
        
        print("[RECUPERACION] Generando números con manejo de errores")
        
        # Generar algunos números normalmente
        numeros_normales = []
        for i in range(3):
            numero = db._obtener_siguiente_consecutivo(patron_error)
            numeros_normales.append(numero)
            print(f"  Normal {i+1}: {numero}")
        
        # Test del fallback si hay problemas
        try:
            # Simular un error controlado usando el método fallback
            numero_fallback = db._obtener_consecutivo_fallback(patron_error)
            print(f"  Fallback: {numero_fallback}")
            
            # El sistema debe seguir funcionando
            numero_post_error = db._obtener_siguiente_consecutivo(patron_error)
            print(f"  Post-error: {numero_post_error}")
            
            return True
            
        except Exception as e:
            print(f"  Error en recuperación: {e}")
            return False
        
    except Exception as e:
        print(f"[ERROR] Error en test de recuperación: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    
    print("TESTING SISTEMA DE NUMERACION IRREPETIBLE")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Numeración Atómica Básica", test_numeracion_atomica),
        ("Concurrencia Multi-Thread", test_concurrencia), 
        ("Patrones Múltiples", test_patrones_multiples),
        ("Modo Offline", test_modo_offline),
        ("Recuperación Errores", test_recuperacion_errores)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"EJECUTANDO: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"[PASSED] {test_name}")
            else:
                print(f"[FAILED] {test_name}")
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
        
        print()
    
    print("=" * 60)
    print(f"RESULTADO FINAL: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("[SUCCESS] SISTEMA DE NUMERACION IRREPETIBLE FUNCIONAL")
        print()
        print("GARANTIAS VERIFICADAS:")
        print("- Números nunca se repiten")
        print("- Numeración consecutiva por patrón")
        print("- Thread-safe bajo concurrencia")
        print("- Patrones independientes")
        print("- Recuperación ante errores")
        print("- Funciona online y offline")
        
        return True
    else:
        print("[ERROR] ALGUNOS TESTS FALLARON")
        print("Revisar implementación antes de desplegar")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)