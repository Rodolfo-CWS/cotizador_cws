# -*- coding: utf-8 -*-
"""
Ejecutar Migración: Agregar columna referencia_oc
=================================================

Ejecuta la migración SQL para agregar la columna referencia_oc a la tabla cotizaciones.

Uso:
    python run_migration_referencia_oc.py

Autor: CWS Company
Fecha: 2026-01-13
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from supabase_manager import SupabaseManager


def ejecutar_migracion():
    """Ejecuta la migración para agregar columna referencia_oc"""

    print("=" * 60)
    print("MIGRACIÓN: Agregar columna referencia_oc")
    print("=" * 60)

    try:
        # Inicializar SupabaseManager
        print("\n[1/4] Conectando a Supabase...")
        db = SupabaseManager()

        if db.modo_offline:
            print("⚠️  ADVERTENCIA: Sistema en modo offline")
            print("    La migración solo afecta a JSON local, no a Supabase")
            print("\n    Para ejecutar la migración en Supabase:")
            print("    1. Ve al Supabase Dashboard (https://app.supabase.com)")
            print("    2. Selecciona tu proyecto")
            print("    3. Ve a 'SQL Editor'")
            print("    4. Ejecuta el contenido de: migrations/add_referencia_oc_column.sql")
            return False

        print("✓ Conectado a Supabase PostgreSQL")

        # Verificar si la columna ya existe
        print("\n[2/4] Verificando si la columna ya existe...")
        cursor = db.pg_connection.cursor()

        check_query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'cotizaciones' AND column_name = 'referencia_oc';
        """

        cursor.execute(check_query)
        result = cursor.fetchone()

        if result:
            print("✓ La columna 'referencia_oc' ya existe en la tabla")
            cursor.close()
            return True

        print("  La columna no existe, procediendo con la migración...")

        # Ejecutar migración
        print("\n[3/4] Ejecutando migración SQL...")

        migration_query = """
            ALTER TABLE cotizaciones
            ADD COLUMN referencia_oc TEXT;
        """

        cursor.execute(migration_query)
        db.pg_connection.commit()

        print("✓ Migración ejecutada exitosamente")

        # Agregar comentario
        print("\n[4/4] Agregando comentario a la columna...")

        comment_query = """
            COMMENT ON COLUMN cotizaciones.referencia_oc
            IS 'Referencia opcional a la orden de compra original (ej: OC-2025-001)';
        """

        cursor.execute(comment_query)
        db.pg_connection.commit()
        cursor.close()

        print("✓ Comentario agregado exitosamente")

        # Verificar migración
        print("\n[VERIFICACIÓN] Verificando migración...")
        cursor = db.pg_connection.cursor()

        verify_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'cotizaciones' AND column_name = 'referencia_oc';
        """

        cursor.execute(verify_query)
        column_info = cursor.fetchone()
        cursor.close()

        if column_info:
            print(f"✓ Columna verificada:")
            print(f"  - Nombre: {column_info[0]}")
            print(f"  - Tipo: {column_info[1]}")
            print(f"  - Nullable: {column_info[2]}")

            print("\n" + "=" * 60)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            return True
        else:
            print("❌ Error: No se pudo verificar la columna después de la migración")
            return False

    except Exception as e:
        print(f"\n❌ ERROR durante la migración: {e}")
        print("\nSi el error es de conexión, intenta ejecutar la migración manualmente:")
        print("1. Ve al Supabase Dashboard (https://app.supabase.com)")
        print("2. Selecciona tu proyecto")
        print("3. Ve a 'SQL Editor'")
        print("4. Ejecuta: ALTER TABLE cotizaciones ADD COLUMN referencia_oc TEXT;")
        return False


if __name__ == '__main__':
    exito = ejecutar_migracion()
    sys.exit(0 if exito else 1)
