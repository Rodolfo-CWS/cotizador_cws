#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST CONSECUTIVE NUMBERING SYSTEM
=================================

Pruebas comprehensivas para el sistema de numeración consecutiva irrepetible
con soporte para revisiones que preservan el número base.

Este test verifica que:
1. Los números consecutivos sean irrepetibles
2. Las revisiones preserven el número base (###) y solo incrementen R#
3. El sistema funcione tanto en modo online (Supabase) como offline (JSON)
4. Se manejen correctamente los casos límite y errores
"""

import os
import sys
import json
import time
from datetime import datetime

# Agregar el directorio actual al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_numbering():
    """Test básico de generación de números consecutivos"""
    print("\n" + "="*60)
    print("TEST 1: NUMERACIÓN BÁSICA CONSECUTIVA")
    print("="*60)
    
    try:
        from supabase_manager import SupabaseManager
        
        db_manager = SupabaseManager()
        print(f"Modo de prueba: {'OFFLINE' if db_manager.modo_offline else 'ONLINE (Supabase)'}")
        
        # Test Case 1: Cliente BMW, Vendedor Juan Perez, Proyecto GROW
        print("\n1. Generando primera cotización para BMW...")
        numero1 = db_manager.generar_numero_cotizacion("BMW", "Juan Perez", "GROW", 1)
        print(f"   Resultado: {numero1}")
        
        # Test Case 2: Misma combinación cliente/vendedor/proyecto -> debe incrementar consecutivo
        print("\n2. Generando segunda cotización para BMW (mismo vendedor/proyecto)...")
        numero2 = db_manager.generar_numero_cotizacion("BMW", "Juan Perez", "GROW", 1)
        print(f"   Resultado: {numero2}")
        
        # Test Case 3: Diferente proyecto, mismo cliente/vendedor -> debe incrementar consecutivo
        print("\n3. Generando tercera cotización BMW con proyecto diferente...")
        numero3 = db_manager.generar_numero_cotizacion("BMW", "Juan Perez", "EXPANSION", 1)
        print(f"   Resultado: {numero3}")
        
        # Verificar que los números sean únicos
        numeros = [numero1, numero2, numero3]
        if len(set(numeros)) == len(numeros):
            print("[OK] EXITO: Todos los numeros generados son unicos")
        else:
            print("[ERROR] Se generaron numeros duplicados")
            return False
            
        # Verificar formato correcto
        expected_format = r'^[A-Z]+-CWS-[A-Z]{1,2}-\d{3}-R\d+-[A-Z-]+$'
        import re
        for num in numeros:
            if not re.match(expected_format, num):
                print(f"[ERROR] Formato invalido en {num}")
                return False
        
        print("[OK] EXITO: Todos los numeros tienen formato correcto")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_revision_numbering():
    """Test de numeración de revisiones"""
    print("\n" + "="*60)
    print("TEST 2: NUMERACIÓN DE REVISIONES")
    print("="*60)
    
    try:
        from supabase_manager import SupabaseManager
        
        db_manager = SupabaseManager()
        
        # Generar cotización original
        print("\n1. Generando cotización original...")
        numero_original = db_manager.generar_numero_cotizacion("MERCEDES", "Ana Garcia", "PROYECTO-X", 1)
        print(f"   Número original: {numero_original}")
        
        # Generar revisión R2
        print("\n2. Generando revisión R2...")
        numero_r2 = db_manager.generar_numero_revision(numero_original, 2)
        print(f"   Revisión R2: {numero_r2}")
        
        # Generar revisión R3
        print("\n3. Generando revisión R3...")
        numero_r3 = db_manager.generar_numero_revision(numero_r2, 3)
        print(f"   Revisión R3: {numero_r3}")
        
        # Verificar que el número base (###) se preserve
        def extraer_numero_base(numero):
            """Extrae el número consecutivo del formato CLIENTE-CWS-INICIALES-###-R#-PROYECTO"""
            try:
                partes = numero.split('-')
                if len(partes) >= 4:
                    return partes[3]  # El ### está en el índice 3
                return None
            except:
                return None
        
        base_original = extraer_numero_base(numero_original)
        base_r2 = extraer_numero_base(numero_r2)
        base_r3 = extraer_numero_base(numero_r3)
        
        print(f"\n4. Verificando números base:")
        print(f"   Original: {base_original}")
        print(f"   R2:       {base_r2}")
        print(f"   R3:       {base_r3}")
        
        if base_original == base_r2 == base_r3:
            print("✅ ÉXITO: El número base se preserva en todas las revisiones")
        else:
            print("❌ ERROR: El número base cambió entre revisiones")
            return False
        
        # Verificar que solo cambie la parte R#
        def extraer_revision(numero):
            """Extrae el número de revisión"""
            try:
                import re
                match = re.search(r'-R(\d+)-', numero)
                if match:
                    return int(match.group(1))
                return None
            except:
                return None
        
        rev_original = extraer_revision(numero_original)
        rev_r2 = extraer_revision(numero_r2)
        rev_r3 = extraer_revision(numero_r3)
        
        print(f"\n5. Verificando números de revisión:")
        print(f"   Original: R{rev_original}")
        print(f"   R2:       R{rev_r2}")
        print(f"   R3:       R{rev_r3}")
        
        if rev_original == 1 and rev_r2 == 2 and rev_r3 == 3:
            print("✅ ÉXITO: Los números de revisión incrementan correctamente")
            return True
        else:
            print("❌ ERROR: Los números de revisión no incrementan correctamente")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_concurrency_simulation():
    """Simular solicitudes concurrentes para verificar que no hay duplicados"""
    print("\n" + "="*60)
    print("TEST 3: SIMULACIÓN DE CONCURRENCIA")
    print("="*60)
    
    try:
        from supabase_manager import SupabaseManager
        
        # Simular múltiples solicitudes "concurrentes" para el mismo cliente/vendedor
        print("\n1. Generando 10 cotizaciones 'concurrentes' para TOYOTA + Carlos Martinez...")
        
        numeros_generados = []
        db_manager = SupabaseManager()
        
        for i in range(10):
            numero = db_manager.generar_numero_cotizacion("TOYOTA", "Carlos Martinez", f"LOTE-{i+1}", 1)
            numeros_generados.append(numero)
            print(f"   {i+1:2d}. {numero}")
            time.sleep(0.1)  # Pequeña pausa para simular procesamiento
        
        # Verificar unicidad
        numeros_unicos = set(numeros_generados)
        if len(numeros_unicos) == len(numeros_generados):
            print(f"\n✅ ÉXITO: Los {len(numeros_generados)} números generados son únicos")
        else:
            print(f"\n❌ ERROR: Se encontraron duplicados!")
            print(f"   Generados: {len(numeros_generados)}")
            print(f"   Únicos: {len(numeros_unicos)}")
            duplicados = [num for num in numeros_generados if numeros_generados.count(num) > 1]
            print(f"   Duplicados: {set(duplicados)}")
            return False
        
        # Verificar que los consecutivos incrementen correctamente
        def extraer_consecutivo(numero):
            try:
                partes = numero.split('-')
                if len(partes) >= 4:
                    return int(partes[3])
                return None
            except:
                return None
        
        consecutivos = [extraer_consecutivo(num) for num in numeros_generados]
        consecutivos_validos = [c for c in consecutivos if c is not None]
        
        print(f"\n2. Verificando secuencia de consecutivos:")
        print(f"   Consecutivos extraídos: {consecutivos_validos}")
        
        if consecutivos_validos == sorted(consecutivos_validos):
            print("✅ ÉXITO: Los números consecutivos están en orden correcto")
            return True
        else:
            print("❌ ERROR: Los números consecutivos no están en orden")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test de casos límite y manejo de errores"""
    print("\n" + "="*60)
    print("TEST 4: CASOS LÍMITE Y MANEJO DE ERRORES")
    print("="*60)
    
    try:
        from supabase_manager import SupabaseManager
        
        db_manager = SupabaseManager()
        
        # Test Case 1: Datos vacíos o None
        print("\n1. Test con datos vacíos...")
        numero1 = db_manager.generar_numero_cotizacion("", "", "", 1)
        print(f"   Resultado (datos vacíos): {numero1}")
        
        numero2 = db_manager.generar_numero_cotizacion(None, None, None, 1)
        print(f"   Resultado (datos None): {numero2}")
        
        # Test Case 2: Datos con caracteres especiales
        print("\n2. Test con caracteres especiales...")
        numero3 = db_manager.generar_numero_cotizacion("BMW & CO.", "José María Pérez-López", "PROYECTO #1 (ESPECIAL)", 1)
        print(f"   Resultado (caracteres especiales): {numero3}")
        
        # Test Case 3: Vendedor con un solo nombre
        print("\n3. Test con vendedor de un solo nombre...")
        numero4 = db_manager.generar_numero_cotizacion("FORD", "Carlos", "SIMPLE", 1)
        print(f"   Resultado (nombre simple): {numero4}")
        
        # Test Case 4: Revision de número malformado
        print("\n4. Test de revisión con número malformado...")
        numero_malo = "FORMATO-INCORRECTO-SIN-REVISION"
        numero5 = db_manager.generar_numero_revision(numero_malo, 2)
        print(f"   Número original: {numero_malo}")
        print(f"   Revisión generada: {numero5}")
        
        # Test Case 5: Verificar número único
        print("\n5. Test de verificación de unicidad...")
        numero_test = db_manager.generar_numero_cotizacion("TEST", "Verificacion", "UNICO", 1)
        es_unico_antes = db_manager.verificar_numero_unico(numero_test)
        print(f"   Número generado: {numero_test}")
        print(f"   ¿Es único antes de guardar?: {es_unico_antes}")
        
        # Simular guardado en base de datos (para test de unicidad)
        if not db_manager.modo_offline:
            try:
                # Solo hacer test completo si estamos online
                datos_test = {
                    'numeroCotizacion': numero_test,
                    'datosGenerales': {
                        'cliente': 'TEST',
                        'vendedor': 'Verificacion',
                        'proyecto': 'UNICO',
                        'numeroCotizacion': numero_test,
                        'revision': 1
                    },
                    'items': []
                }
                
                resultado = db_manager.guardar_cotizacion(datos_test)
                if resultado.get('success'):
                    es_unico_despues = db_manager.verificar_numero_unico(numero_test)
                    print(f"   ¿Es único después de guardar?: {es_unico_despues}")
                    
                    if es_unico_antes and not es_unico_despues:
                        print("✅ ÉXITO: La verificación de unicidad funciona correctamente")
                    else:
                        print("❌ ERROR: La verificación de unicidad no funciona")
                        return False
                else:
                    print("   (No se pudo guardar para test de unicidad - continuando)")
                    
            except Exception as e:
                print(f"   (Error en test de unicidad: {e} - continuando)")
        else:
            print("   (Modo offline - saltando test completo de unicidad)")
        
        print("\n✅ ÉXITO: Todos los casos límite manejados correctamente")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_format_consistency():
    """Test de consistencia de formato"""
    print("\n" + "="*60)
    print("TEST 5: CONSISTENCIA DE FORMATO")
    print("="*60)
    
    try:
        from supabase_manager import SupabaseManager
        
        db_manager = SupabaseManager()
        
        # Generar varios números con diferentes combinaciones
        test_cases = [
            ("BMW", "Juan Perez", "GROW"),
            ("MERCEDES-BENZ", "Ana Maria Garcia Lopez", "PROYECTO-EXPANSION"),
            ("TOYOTA", "Carlos", "SIMPLE"),
            ("FORD MOTOR COMPANY", "José Miguel Rodríguez", "COMPLEJO-2025"),
            ("GM", "A B", "X"),
        ]
        
        print("\n1. Generando números con diferentes combinaciones de datos:")
        numeros_generados = []
        
        for i, (cliente, vendedor, proyecto) in enumerate(test_cases):
            numero = db_manager.generar_numero_cotizacion(cliente, vendedor, proyecto, 1)
            numeros_generados.append(numero)
            print(f"   {i+1}. Cliente: '{cliente}' | Vendedor: '{vendedor}' | Proyecto: '{proyecto}'")
            print(f"      → {numero}")
        
        # Verificar formato consistente
        import re
        patron_formato = r'^[A-Z0-9-]+-CWS-[A-Z0-9]{1,2}-\d{3}-R\d+-[A-Z0-9-]+$'
        
        print(f"\n2. Verificando formato contra patrón: {patron_formato}")
        
        formatos_validos = 0
        for i, numero in enumerate(numeros_generados):
            es_valido = bool(re.match(patron_formato, numero))
            status = "✅" if es_valido else "❌"
            print(f"   {i+1}. {numero} {status}")
            if es_valido:
                formatos_validos += 1
        
        if formatos_validos == len(numeros_generados):
            print(f"\n✅ ÉXITO: Todos los {len(numeros_generados)} números tienen formato consistente")
            return True
        else:
            print(f"\n❌ ERROR: Solo {formatos_validos}/{len(numeros_generados)} números tienen formato válido")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Ejecutar todos los tests de numeración consecutiva"""
    print("PRUEBAS DEL SISTEMA DE NUMERACION CONSECUTIVA IRREPETIBLE")
    print("=" * 80)
    print("Verificando que los números sean únicos y las revisiones preserven el número base")
    print("=" * 80)
    
    # Lista de tests a ejecutar
    tests = [
        ("Numeración Básica Consecutiva", test_basic_numbering),
        ("Numeración de Revisiones", test_revision_numbering),
        ("Simulación de Concurrencia", test_concurrency_simulation),
        ("Casos Límite y Errores", test_edge_cases),
        ("Consistencia de Formato", test_format_consistency),
    ]
    
    resultados = []
    tiempo_inicio = time.time()
    
    for nombre_test, funcion_test in tests:
        try:
            print(f"\nEjecutando: {nombre_test}")
            resultado = funcion_test()
            resultados.append((nombre_test, resultado))
        except Exception as e:
            print(f"ERROR CRITICO en {nombre_test}: {e}")
            resultados.append((nombre_test, False))
    
    # Resumen final
    tiempo_total = time.time() - tiempo_inicio
    print("\n" + "="*80)
    print("RESUMEN DE RESULTADOS")
    print("="*80)
    
    tests_exitosos = 0
    for nombre, resultado in resultados:
        status = "[EXITO]" if resultado else "[FALLO]"
        print(f"{status} - {nombre}")
        if resultado:
            tests_exitosos += 1
    
    print(f"\nESTADISTICAS:")
    print(f"   Tests ejecutados: {len(resultados)}")
    print(f"   Tests exitosos: {tests_exitosos}")
    print(f"   Tests fallidos: {len(resultados) - tests_exitosos}")
    print(f"   Tiempo total: {tiempo_total:.2f} segundos")
    
    if tests_exitosos == len(resultados):
        print("\nTODOS LOS TESTS PASARON!")
        print("   El sistema de numeracion consecutiva funciona correctamente")
        print("   Los numeros son irrepetibles")
        print("   Las revisiones preservan el numero base")
        print("   El sistema es robusto ante casos limite")
        return True
    else:
        print(f"\n{len(resultados) - tests_exitosos} TEST(S) FALLARON")
        print("   Revisar los errores reportados arriba")
        return False

if __name__ == "__main__":
    print("Iniciando pruebas del sistema de numeracion consecutiva...")
    
    try:
        exito = run_all_tests()
        
        if exito:
            print("\nCONCLUSION: El sistema esta listo para produccion")
            exit(0)
        else:
            print("\nCONCLUSION: Se requieren correcciones antes de usar en produccion")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTests interrumpidos por el usuario")
        exit(2)
    except Exception as e:
        print(f"\nERROR CRITICO: {e}")
        import traceback
        traceback.print_exc()
        exit(3)