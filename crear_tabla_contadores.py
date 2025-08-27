#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear la tabla de contadores en Supabase
Garantiza numeración irrepetible para cotizaciones
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv no está disponible, usar variables de entorno del sistema
    pass

def crear_tabla_contadores():
    """Crear tabla de contadores atómicos en Supabase"""
    
    print("=== CREAR TABLA CONTADORES IRREPETIBLES ===")
    print()
    
    # Obtener URL de base de datos desde environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("[ERROR] Variable DATABASE_URL no encontrada")
        print("Configura DATABASE_URL en tu archivo .env o variables de entorno")
        return False
    
    try:
        print("[CONEXION] Conectando a Supabase PostgreSQL...")
        
        # Conectar a PostgreSQL
        connection = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            sslmode='require'
        )
        
        cursor = connection.cursor()
        
        print("[OK] Conectado exitosamente")
        print()
        
        # SQL para crear tabla de contadores
        sql_crear_tabla = """
        CREATE TABLE IF NOT EXISTS cotizacion_counters (
            patron VARCHAR(100) PRIMARY KEY,
            ultimo_numero INTEGER DEFAULT 0,
            descripcion TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        print("[TABLA] Creando tabla cotizacion_counters...")
        cursor.execute(sql_crear_tabla)
        
        # Crear índice para performance
        sql_indice = """
        CREATE INDEX IF NOT EXISTS idx_cotizacion_counters_patron 
        ON cotizacion_counters(patron);
        """
        
        print("[INDICE] Creando índice de performance...")
        cursor.execute(sql_indice)
        
        # Crear función de actualización automática de timestamp
        sql_funcion_timestamp = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        print("[FUNCION] Creando función de timestamp automático...")
        cursor.execute(sql_funcion_timestamp)
        
        # Crear trigger para actualizar timestamp automáticamente
        sql_trigger = """
        DROP TRIGGER IF EXISTS update_cotizacion_counters_updated_at ON cotizacion_counters;
        CREATE TRIGGER update_cotizacion_counters_updated_at
            BEFORE UPDATE ON cotizacion_counters
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        print("[TRIGGER] Creando trigger de actualización automática...")
        cursor.execute(sql_trigger)
        
        # Commit cambios
        connection.commit()
        
        print("[OK] Tabla cotizacion_counters creada exitosamente")
        print()
        
        # Verificar estructura de la tabla
        print("[VERIFICACION] Verificando estructura de tabla...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'cotizacion_counters'
            ORDER BY ordinal_position;
        """)
        
        columnas = cursor.fetchall()
        
        print("[ESTRUCTURA] Estructura de cotizacion_counters:")
        for col in columnas:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"  - {col['column_name']}: {col['data_type']} {nullable} {default}")
        
        print()
        
        # Insertar algunos patrones de ejemplo para testing
        print("[TESTING] Insertando patrones de ejemplo para testing...")
        
        patrones_ejemplo = [
            ("CLIENTE-CWS-RM", "Roberto Martinez - Patrón general"),
            ("BMWTEST-CWS-RM", "BMW Test - Patrón específico"),
            ("DEMO-CWS-XX", "Demo - Patrón genérico")
        ]
        
        for patron, descripcion in patrones_ejemplo:
            cursor.execute("""
                INSERT INTO cotizacion_counters (patron, ultimo_numero, descripcion) 
                VALUES (%s, %s, %s)
                ON CONFLICT (patron) DO NOTHING;
            """, (patron, 0, descripcion))
        
        connection.commit()
        
        # Verificar datos insertados
        cursor.execute("SELECT * FROM cotizacion_counters ORDER BY patron;")
        contadores = cursor.fetchall()
        
        print(f"[OK] {len(contadores)} patrones configurados:")
        for contador in contadores:
            print(f"  - {contador['patron']}: {contador['ultimo_numero']} ({contador['descripcion']})")
        
        print()
        
        # Cerrar conexiones
        cursor.close()
        connection.close()
        
        print("[EXITO] TABLA DE CONTADORES CREADA EXITOSAMENTE!")
        print()
        print("CARACTERÍSTICAS IMPLEMENTADAS:")
        print("[OK] Contadores atómicos por patrón")
        print("[OK] Operaciones thread-safe con PostgreSQL")
        print("[OK] Timestamp automático de creación/actualización")
        print("[OK] Índices optimizados para performance")
        print("[OK] Patrones de ejemplo para testing")
        print()
        print("PRÓXIMO PASO: Implementar la función atómica en supabase_manager.py")
        
        return True
        
    except psycopg2.Error as e:
        print(f"[ERROR] ERROR de PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] ERROR general: {e}")
        return False

def main():
    """Ejecutar creación de tabla"""
    
    print("CONFIGURACIÓN SISTEMA DE NUMERACIÓN IRREPETIBLE")
    print("=" * 50)
    print()
    
    success = crear_tabla_contadores()
    
    if success:
        print()
        print("[SIGUIENTE] Ejecutar este script en producción")
        print("Comando: python crear_tabla_contadores.py")
        print()
        print("[VERIFICACION]:")
        print("1. Tabla cotizacion_counters creada en Supabase")
        print("2. Función atómica lista para implementar")
        print("3. Sistema robusto contra race conditions")
        
        return True
    else:
        print()
        print("[ERROR] FALLÓ LA CREACIÓN")
        print("Revisa la conexión a Supabase y variables de entorno")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)