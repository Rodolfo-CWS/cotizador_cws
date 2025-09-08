#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agregar columna condiciones directamente desde Python
Alternativa cuando SQL Editor tiene timeout
"""

import os
import sys
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def agregar_columna_condiciones():
    """Agregar columna condiciones a tabla cotizaciones"""
    
    print("=== AGREGAR COLUMNA CONDICIONES ===")
    print()
    
    # Obtener DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("[ERROR] DATABASE_URL no encontrado en variables de entorno")
        return False
    
    try:
        print("[CONEXION] Conectando a Supabase PostgreSQL...")
        
        # Conexión con timeout corto para evitar cuelgues
        connection = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            connect_timeout=30,
            sslmode='require'
        )
        
        # Configurar timeout de statement
        connection.autocommit = True  # Para DDL statements
        cursor = connection.cursor()
        
        print("[OK] Conectado exitosamente")
        print()
        
        # 1. Verificar si la columna ya existe
        print("[VERIFICAR] Verificando si columna 'condiciones' existe...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'cotizaciones' 
                AND column_name = 'condiciones'
                AND table_schema = 'public'
            );
        """)
        
        existe = cursor.fetchone()[0]
        
        if existe:
            print("[SKIP] La columna 'condiciones' ya existe")
            print("[OK] No se necesita hacer nada")
            
            # Verificar el tipo de la columna
            cursor.execute("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'cotizaciones' 
                AND column_name = 'condiciones'
                AND table_schema = 'public';
            """)
            tipo = cursor.fetchone()[0]
            print(f"[INFO] Tipo actual: {tipo}")
            
            cursor.close()
            connection.close()
            return True
        
        print("[AGREGAR] La columna no existe, agregando...")
        
        # 2. Contar registros para estimar tiempo
        print("[INFO] Contando registros existentes...")
        cursor.execute("SELECT COUNT(*) FROM cotizaciones;")
        total_registros = cursor.fetchone()[0]
        print(f"[INFO] Total registros: {total_registros}")
        
        if total_registros > 10000:
            print("[WARNING] Muchos registros, esto puede tardar varios minutos...")
        
        # 3. Agregar la columna con optimizaciones
        print("[EJECUTAR] Agregando columna 'condiciones' tipo JSONB...")
        
        start_time = time.time()
        
        # Usar ADD COLUMN con DEFAULT para mayor eficiencia
        cursor.execute("""
            ALTER TABLE cotizaciones 
            ADD COLUMN condiciones JSONB DEFAULT '{}'::jsonb;
        """)
        
        elapsed_time = time.time() - start_time
        print(f"[OK] Columna agregada en {elapsed_time:.2f} segundos")
        
        # 4. Agregar comentario
        print("[COMENTARIO] Agregando documentación...")
        cursor.execute("""
            COMMENT ON COLUMN cotizaciones.condiciones 
            IS 'JSON con condiciones comerciales: moneda, tipoCambio, tiempoEntrega, terminos, etc.';
        """)
        
        # 5. Verificar resultado final
        print("[VERIFICAR] Verificando resultado...")
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'cotizaciones' 
            AND column_name = 'condiciones'
            AND table_schema = 'public';
        """)
        
        resultado = cursor.fetchone()
        if resultado:
            print(f"[EXITO] Columna creada correctamente:")
            print(f"   Nombre: {resultado['column_name']}")
            print(f"   Tipo: {resultado['data_type']}")
            print(f"   Default: {resultado['column_default']}")
        else:
            print("[ERROR] No se pudo verificar la columna")
            return False
        
        # Cerrar conexiones
        cursor.close()
        connection.close()
        
        print()
        print("[EXITO] ¡COLUMNA 'CONDICIONES' AGREGADA EXITOSAMENTE!")
        print()
        print("PRÓXIMO PASO:")
        print("   Probar la aplicación - debería guardar en Supabase DB ahora")
        print("   python -c \"from supabase_manager import SupabaseManager; print('Test OK')\"")
        
        return True
        
    except psycopg2.OperationalError as e:
        if "timeout" in str(e).lower():
            print(f"[TIMEOUT] Operación tardó demasiado: {e}")
            print()
            print("ALTERNATIVAS:")
            print("1. Intentar en horario de menos uso")
            print("2. Usar SQL Editor de Supabase con script más simple")
            print("3. Contactar soporte de Supabase si persiste")
        else:
            print(f"[ERROR] Error de conexión: {e}")
        return False
        
    except psycopg2.Error as e:
        print(f"[ERROR] Error PostgreSQL: {e}")
        return False
        
    except Exception as e:
        print(f"[ERROR] Error general: {e}")
        return False

def main():
    """Función principal"""
    print("AGREGAR COLUMNA CONDICIONES - MÉTODO PYTHON")
    print("=" * 50)
    print()
    
    success = agregar_columna_condiciones()
    
    if success:
        print()
        print("[VALIDAR] Probando que funcione...")
        try:
            from supabase_manager import SupabaseManager
            db = SupabaseManager()
            
            # Test simple sin condiciones
            datos_test = {
                'datosGenerales': {'cliente': 'TEST-COLUMN', 'vendedor': 'Python', 'proyecto': 'VALIDATION'},
                'items': [{'descripcion': 'Test', 'cantidad': 1, 'precio_unitario': 100}],
                'observaciones': 'Test después de agregar columna'
            }
            
            resultado = db.guardar_cotizacion(datos_test)
            
            if resultado.get('success') and resultado.get('modo') == 'online':
                print("[EXITO] ¡APLICACIÓN FUNCIONANDO CON SUPABASE DB!")
                print(f"   Modo: {resultado.get('modo')}")
                print(f"   ID: {resultado.get('id')}")
            else:
                print(f"[PARCIAL] Guardado pero aún en modo: {resultado.get('modo')}")
                print("   Puede necesitar reiniciar la aplicación")
            
        except Exception as e:
            print(f"[INFO] No se pudo probar inmediatamente: {e}")
            print("   Probar manualmente después")
        
        return True
    else:
        print()
        print("[FALLO] No se pudo agregar la columna")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)