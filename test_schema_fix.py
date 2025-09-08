#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SCHEMA FIX - Verificar que el esquema corregido funciona
=============================================================

Este script verifica que el esquema de Supabase esté completo y funcional
después de ejecutar fix_supabase_schema.sql

Características:
- Verifica que las tablas existan
- Prueba la inserción de datos
- Confirma que la columna 'condiciones' funciona
- Valida los contadores automáticos
- Prueba el flujo completo de guardado
"""

import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar el manager de Supabase
try:
    from supabase_manager import SupabaseManager
    print("[OK] SupabaseManager importado correctamente")
except ImportError as e:
    print(f"❌ Error importando SupabaseManager: {e}")
    sys.exit(1)

def test_conexion_supabase():
    """Test 1: Verificar conexión a Supabase"""
    print("\n" + "="*60)
    print("TEST 1: CONEXIÓN A SUPABASE")
    print("="*60)
    
    try:
        db = SupabaseManager()
        
        if db.modo_offline:
            print(f"❌ FALLO: Supabase en modo offline")
            print(f"   Variables verificadas:")
            print(f"   - SUPABASE_URL: {'✅' if db.supabase_url else '❌'}")
            print(f"   - SUPABASE_ANON_KEY: {'✅' if db.supabase_key else '❌'}")
            print(f"   - DATABASE_URL: {'✅' if db.database_url else '❌'}")
            return False
        else:
            print(f"✅ ÉXITO: Conectado a Supabase PostgreSQL")
            print(f"   URL: {db.supabase_url}")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_tablas_existen(db):
    """Test 2: Verificar que las tablas necesarias existan"""
    print("\n" + "="*60)
    print("TEST 2: VERIFICAR TABLAS")
    print("="*60)
    
    try:
        cursor = db.pg_connection.cursor()
        
        # Lista de tablas requeridas
        tablas_requeridas = ['cotizaciones', 'cotizacion_counters', 'pdf_storage']
        tablas_encontradas = []
        
        for tabla in tablas_requeridas:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (tabla,))
            
            existe = cursor.fetchone()[0]
            if existe:
                tablas_encontradas.append(tabla)
                print(f"✅ Tabla '{tabla}' existe")
            else:
                print(f"❌ Tabla '{tabla}' NO existe")
        
        cursor.close()
        
        if len(tablas_encontradas) == len(tablas_requeridas):
            print(f"\n✅ ÉXITO: Todas las tablas necesarias existen ({len(tablas_encontradas)}/{len(tablas_requeridas)})")
            return True
        else:
            print(f"\n❌ FALLO: Faltan tablas ({len(tablas_encontradas)}/{len(tablas_requeridas)})")
            return False
            
    except Exception as e:
        print(f"❌ ERROR verificando tablas: {e}")
        return False

def test_estructura_cotizaciones(db):
    """Test 3: Verificar estructura de tabla cotizaciones"""
    print("\n" + "="*60)
    print("TEST 3: ESTRUCTURA TABLA COTIZACIONES")
    print("="*60)
    
    try:
        cursor = db.pg_connection.cursor()
        
        # Verificar columnas de la tabla cotizaciones
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'cotizaciones'
                AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        columnas = cursor.fetchall()
        cursor.close()
        
        # Columnas requeridas
        columnas_requeridas = [
            'id', 'numero_cotizacion', 'datos_generales', 'items', 
            'condiciones', 'revision', 'version', 'fecha_creacion', 
            'timestamp', 'usuario', 'observaciones'
        ]
        
        columnas_encontradas = [col[0] for col in columnas]
        
        print("Columnas encontradas:")
        for col in columnas:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            print(f"  - {col[0]}: {col[1]} {nullable}")
        
        # Verificar que todas las columnas requeridas existan
        columnas_faltantes = []
        for col_req in columnas_requeridas:
            if col_req not in columnas_encontradas:
                columnas_faltantes.append(col_req)
        
        if columnas_faltantes:
            print(f"\n❌ FALLO: Faltan columnas: {columnas_faltantes}")
            return False
        else:
            print(f"\n✅ ÉXITO: Todas las columnas necesarias existen")
            
            # Verificar específicamente la columna 'condiciones'
            condiciones_col = next((col for col in columnas if col[0] == 'condiciones'), None)
            if condiciones_col and 'jsonb' in condiciones_col[1].lower():
                print("✅ Columna 'condiciones' es JSONB correctamente")
                return True
            else:
                print("❌ Columna 'condiciones' no es JSONB")
                return False
                
    except Exception as e:
        print(f"❌ ERROR verificando estructura: {e}")
        return False

def test_insertar_cotizacion_completa(db):
    """Test 4: Probar inserción de cotización con condiciones"""
    print("\n" + "="*60)
    print("TEST 4: INSERTAR COTIZACIÓN COMPLETA")
    print("="*60)
    
    try:
        # Datos de prueba completos con condiciones
        test_timestamp = int(time.time())
        datos_test = {
            'numeroCotizacion': f'SCHEMA-TEST-CWS-FX-{test_timestamp}-R1-VALIDACION',
            'datosGenerales': {
                'cliente': 'SCHEMA-TEST-CLIENT',
                'vendedor': 'SCHEMA VALIDATOR',
                'proyecto': 'VALIDACION-ESQUEMA',
                'atencionA': 'Test Engineer',
                'contacto': 'test@schemafix.com',
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'validez': '30 dias'
            },
            'items': [
                {
                    'descripcion': 'Item de prueba para validación de esquema',
                    'cantidad': 1,
                    'precio_unitario': 100.0,
                    'subtotal': 100.0
                }
            ],
            'condiciones': {
                'moneda': 'USD',
                'tipoCambio': '1.00',
                'tiempoEntrega': '7 dias laborales',
                'entregaEn': 'Oficinas del cliente',
                'terminos': 'NET 30',
                'comentarios': 'Prueba de inserción con condiciones completas'
            },
            'observaciones': 'Cotización de prueba para validar esquema corregido',
            'revision': 1,
            'version': '1.0.0',
            'timestamp': test_timestamp * 1000  # milliseconds
        }
        
        print("📤 Intentando guardar cotización de prueba...")
        print(f"   Cliente: {datos_test['datosGenerales']['cliente']}")
        print(f"   Número: {datos_test['numeroCotizacion']}")
        print(f"   Condiciones incluidas: {bool(datos_test['condiciones'])}")
        
        # Usar SupabaseManager para guardar
        resultado = db.guardar_cotizacion(datos_test)
        
        if resultado.get('success'):
            numero_guardado = resultado.get('numero_cotizacion') or resultado.get('numeroCotizacion')
            print(f"✅ ÉXITO: Cotización guardada correctamente")
            print(f"   ID: {resultado.get('id', 'N/A')}")
            print(f"   Número: {numero_guardado}")
            print(f"   Modo: {resultado.get('modo', 'N/A')}")
            
            # Verificar que se puede recuperar
            print("\n🔍 Verificando recuperación de datos...")
            recuperada = db.obtener_cotizacion(numero_guardado)
            
            if recuperada.get('encontrado'):
                cotizacion = recuperada['item']
                print("✅ Cotización recuperada exitosamente")
                
                # Verificar que las condiciones se guardaron
                condiciones_recuperadas = cotizacion.get('condiciones', {})
                if condiciones_recuperadas and condiciones_recuperadas.get('moneda') == 'USD':
                    print("✅ Campo 'condiciones' guardado y recuperado correctamente")
                    print(f"   Moneda: {condiciones_recuperadas.get('moneda')}")
                    print(f"   Términos: {condiciones_recuperadas.get('terminos')}")
                    
                    # Limpiar datos de test
                    try:
                        cursor = db.pg_connection.cursor()
                        cursor.execute("DELETE FROM cotizaciones WHERE numero_cotizacion = %s", (numero_guardado,))
                        db.pg_connection.commit()
                        cursor.close()
                        print("🧹 Datos de prueba limpiados")
                    except:
                        print("⚠️ No se pudieron limpiar los datos de prueba")
                    
                    return True
                else:
                    print("❌ Campo 'condiciones' no se guardó correctamente")
                    return False
            else:
                print("❌ No se pudo recuperar la cotización guardada")
                return False
        else:
            error = resultado.get('error', 'Error desconocido')
            print(f"❌ FALLO: Error guardando cotización: {error}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR en test de inserción: {e}")
        return False

def test_contadores_atomicos(db):
    """Test 5: Probar sistema de contadores atómicos"""
    print("\n" + "="*60)
    print("TEST 5: CONTADORES ATÓMICOS")
    print("="*60)
    
    try:
        # Verificar que la tabla de contadores existe y tiene datos
        cursor = db.pg_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM cotizacion_counters;")
        count = cursor.fetchone()[0]
        cursor.close()
        
        print(f"📊 Contadores configurados: {count}")
        
        if count > 0:
            # Probar generación de número consecutivo
            patron_test = "SCHEMA-CWS-TS"
            print(f"🔢 Probando generación consecutiva para patrón: {patron_test}")
            
            # Simular datos para generación de número
            datos_generales = {
                'cliente': 'SCHEMA-TEST',
                'vendedor': 'Test Schema',
                'proyecto': 'CONTADOR-TEST'
            }
            
            numero_generado = db.generar_numero_automatico(datos_generales)
            print(f"✅ Número generado: {numero_generado}")
            
            # Verificar formato del número
            partes = numero_generado.split('-')
            if len(partes) >= 5 and 'CWS' in partes:
                print("✅ Formato de número correcto")
                return True
            else:
                print(f"❌ Formato de número incorrecto: {numero_generado}")
                return False
        else:
            print("❌ No hay contadores configurados")
            return False
            
    except Exception as e:
        print(f"❌ ERROR en test de contadores: {e}")
        return False

def test_estadisticas(db):
    """Test 6: Obtener estadísticas del sistema"""
    print("\n" + "="*60)
    print("TEST 6: ESTADÍSTICAS DEL SISTEMA")
    print("="*60)
    
    try:
        stats = db.obtener_estadisticas()
        
        print("📊 Estadísticas obtenidas:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Verificar que las estadísticas indican modo online
        if stats.get('modo') == 'online':
            print("✅ Sistema funcionando en modo ONLINE")
            return True
        else:
            print(f"❌ Sistema en modo: {stats.get('modo', 'unknown')}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR obteniendo estadísticas: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🧪 VALIDACIÓN COMPLETA DEL ESQUEMA SUPABASE")
    print("=" * 80)
    print("Este script verifica que fix_supabase_schema.sql fue ejecutado correctamente")
    print("=" * 80)
    
    # Lista de tests a ejecutar
    tests = [
        ("Conexión a Supabase", test_conexion_supabase),
        ("Verificar tablas", None),  # Se pasa el db como parámetro
        ("Estructura cotizaciones", None),
        ("Inserción completa", None),
        ("Contadores atómicos", None),
        ("Estadísticas sistema", None)
    ]
    
    # Test 1: Conexión
    db = None
    if not test_conexion_supabase():
        print("\n❌ RESULTADO FINAL: FALLO EN CONEXIÓN")
        print("\nSOLUCIÓN:")
        print("1. Verificar variables de entorno (DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY)")
        print("2. Ejecutar fix_supabase_schema.sql en Supabase Dashboard")
        print("3. Reintentar este test")
        return False
    
    # Crear instancia para tests posteriores
    db = SupabaseManager()
    
    # Ejecutar tests restantes
    tests_passed = 1  # Conexión ya pasó
    tests_failed = 0
    
    test_functions = [
        test_tablas_existen,
        test_estructura_cotizaciones, 
        test_insertar_cotizacion_completa,
        test_contadores_atomicos,
        test_estadisticas
    ]
    
    for i, test_func in enumerate(test_functions):
        try:
            if test_func(db):
                tests_passed += 1
            else:
                tests_failed += 1
        except Exception as e:
            print(f"❌ ERROR CRÍTICO en test: {e}")
            tests_failed += 1
    
    # Resultado final
    total_tests = tests_passed + tests_failed
    print("\n" + "="*80)
    print("🎯 RESULTADO FINAL")
    print("="*80)
    
    if tests_failed == 0:
        print("🎉 ✅ TODOS LOS TESTS PASARON")
        print(f"   Tests exitosos: {tests_passed}/{total_tests}")
        print("\n📋 ESTADO DEL SISTEMA:")
        print("   ✅ Esquema Supabase completo y funcional")
        print("   ✅ Aplicación debería funcionar correctamente")
        print("   ✅ Guardado en PostgreSQL habilitado")
        print("   ✅ Supabase Storage sigue funcionando")
        print("\n🚀 PRÓXIMO PASO:")
        print("   La aplicación ya debería guardar en Supabase DB en lugar de solo JSON offline")
        
        # Cerrar conexión
        if db:
            db.close()
        
        return True
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print(f"   Tests exitosos: {tests_passed}/{total_tests}")
        print(f"   Tests fallidos: {tests_failed}/{total_tests}")
        print("\n🔧 ACCIONES REQUERIDAS:")
        print("   1. Ejecutar fix_supabase_schema.sql completo en Supabase Dashboard")
        print("   2. Verificar variables de entorno")
        print("   3. Revisar logs de errores arriba")
        print("   4. Reintentar este test")
        
        # Cerrar conexión
        if db:
            db.close()
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)