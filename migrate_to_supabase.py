#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRACIÓN DE DATOS: JSON → SUPABASE POSTGRESQL
=============================================

Este script migra las cotizaciones existentes desde cotizaciones_offline.json
hacia la nueva base de datos Supabase PostgreSQL.

Uso:
    python migrate_to_supabase.py --preview    # Ver qué se va a migrar (sin cambios)
    python migrate_to_supabase.py --migrate    # Ejecutar migración real
    python migrate_to_supabase.py --validate   # Validar migración post-ejecución
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SupabaseMigrator:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.database_url = os.getenv('DATABASE_URL')
        self.json_file_path = 'cotizaciones_offline.json'
        self.connection = None
        
        # Validar configuración
        if not self.database_url:
            print("❌ ERROR: DATABASE_URL no configurada")
            print("   Configura las variables de entorno de Supabase:")
            print("   - SUPABASE_URL=https://tu-proyecto.supabase.co")
            print("   - DATABASE_URL=postgresql://postgres:password@...")
            sys.exit(1)
    
    def connect_to_supabase(self) -> bool:
        """Conectar a Supabase PostgreSQL"""
        try:
            print("🔗 Conectando a Supabase...")
            self.connection = psycopg2.connect(self.database_url)
            self.connection.autocommit = False  # Transacciones manuales
            
            # Test de conexión
            cursor = self.connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Conectado a PostgreSQL: {version[:50]}...")
            cursor.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Error conectando a Supabase: {e}")
            return False
    
    def load_json_data(self) -> Optional[Dict]:
        """Cargar datos desde JSON"""
        try:
            if not os.path.exists(self.json_file_path):
                print(f"❌ Archivo {self.json_file_path} no encontrado")
                return None
            
            print(f"📖 Cargando {self.json_file_path}...")
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cotizaciones = data.get('cotizaciones', [])
            print(f"✅ Cargadas {len(cotizaciones)} cotizaciones desde JSON")
            
            return data
            
        except Exception as e:
            print(f"❌ Error cargando JSON: {e}")
            return None
    
    def validate_schema(self) -> bool:
        """Validar que el schema existe en Supabase"""
        try:
            cursor = self.connection.cursor()
            
            # Verificar tabla cotizaciones
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'cotizaciones'
                );
            """)
            tabla_existe = cursor.fetchone()[0]
            
            if not tabla_existe:
                print("❌ Tabla 'cotizaciones' no existe")
                print("   Ejecuta primero supabase_schema.sql en tu proyecto Supabase")
                cursor.close()
                return False
            
            # Verificar columnas principales
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'cotizaciones' 
                AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            columnas = [row[0] for row in cursor.fetchall()]
            expected_columns = ['id', 'numero_cotizacion', 'datos_generales', 'items']
            
            missing = [col for col in expected_columns if col not in columnas]
            if missing:
                print(f"❌ Columnas faltantes: {missing}")
                cursor.close()
                return False
            
            print("✅ Schema validado correctamente")
            cursor.close()
            return True
            
        except Exception as e:
            print(f"❌ Error validando schema: {e}")
            return False
    
    def preview_migration(self, data: Dict) -> None:
        """Mostrar preview de lo que se va a migrar"""
        cotizaciones = data.get('cotizaciones', [])
        
        print(f"\n📊 PREVIEW DE MIGRACIÓN")
        print(f"{'='*50}")
        print(f"Total de cotizaciones: {len(cotizaciones)}")
        
        if not cotizaciones:
            print("⚠️  No hay cotizaciones para migrar")
            return
        
        # Estadísticas
        clientes = set()
        vendedores = set()
        proyectos = set()
        revisiones = 0
        
        print(f"\n📋 MUESTRA DE COTIZACIONES:")
        for i, cot in enumerate(cotizaciones[:5]):  # Mostrar primeras 5
            dg = cot.get('datosGenerales', {})
            numero = cot.get('numeroCotizacion', 'N/A')
            cliente = dg.get('cliente', 'N/A')
            vendedor = dg.get('vendedor', 'N/A')
            proyecto = dg.get('proyecto', 'N/A')
            revision = cot.get('revision', 1)
            
            print(f"  {i+1}. {numero}")
            print(f"     Cliente: {cliente}")
            print(f"     Vendedor: {vendedor}")
            print(f"     Proyecto: {proyecto}")
            print(f"     Revisión: R{revision}")
            print()
            
            # Acumular estadísticas
            clientes.add(cliente)
            vendedores.add(vendedor)
            proyectos.add(proyecto)
            if revision > 1:
                revisiones += 1
        
        if len(cotizaciones) > 5:
            print(f"  ... y {len(cotizaciones) - 5} más")
        
        print(f"\n📈 ESTADÍSTICAS:")
        print(f"  Clientes únicos: {len(clientes)}")
        print(f"  Vendedores únicos: {len(vendedores)}")
        print(f"  Proyectos únicos: {len(proyectos)}")
        print(f"  Revisiones (R2+): {revisiones}")
        
    def migrate_data(self, data: Dict) -> bool:
        """Ejecutar migración real"""
        cotizaciones = data.get('cotizaciones', [])
        
        if not cotizaciones:
            print("⚠️  No hay cotizaciones para migrar")
            return True
        
        try:
            cursor = self.connection.cursor()
            
            print(f"\n🚀 INICIANDO MIGRACIÓN DE {len(cotizaciones)} COTIZACIONES")
            print("="*60)
            
            migradas = 0
            errores = []
            
            for i, cotizacion in enumerate(cotizaciones, 1):
                try:
                    # Extraer datos
                    numero_cotizacion = cotizacion.get('numeroCotizacion')
                    datos_generales = cotizacion.get('datosGenerales', {})
                    items = cotizacion.get('items', [])
                    revision = cotizacion.get('revision', 1)
                    version = cotizacion.get('version', '1.0.0')
                    fecha_creacion = cotizacion.get('fechaCreacion')
                    timestamp = cotizacion.get('timestamp')
                    usuario = cotizacion.get('usuario')
                    observaciones = cotizacion.get('observaciones')
                    
                    # Validar datos mínimos
                    if not numero_cotizacion:
                        errores.append(f"Cotización {i}: Sin número de cotización")
                        continue
                    
                    # Insertar en PostgreSQL
                    insert_query = """
                        INSERT INTO cotizaciones (
                            numero_cotizacion, datos_generales, items, revision, 
                            version, fecha_creacion, timestamp, usuario, observaciones
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (numero_cotizacion) DO UPDATE SET
                            datos_generales = EXCLUDED.datos_generales,
                            items = EXCLUDED.items,
                            revision = EXCLUDED.revision,
                            updated_at = NOW()
                        RETURNING id;
                    """
                    
                    # Convertir fecha_creacion si es string
                    fecha_dt = None
                    if fecha_creacion:
                        if isinstance(fecha_creacion, str):
                            try:
                                fecha_dt = datetime.fromisoformat(fecha_creacion.replace('Z', '+00:00'))
                            except:
                                fecha_dt = None
                    
                    cursor.execute(insert_query, (
                        numero_cotizacion,
                        Json(datos_generales),  # JSONB
                        Json(items),  # JSONB
                        revision,
                        version,
                        fecha_dt,
                        timestamp,
                        usuario,
                        observaciones
                    ))
                    
                    cotizacion_id = cursor.fetchone()[0]
                    migradas += 1
                    
                    # Progress indicator
                    if i % 10 == 0 or i == len(cotizaciones):
                        print(f"✅ Progreso: {i}/{len(cotizaciones)} ({migradas} exitosas)")
                
                except Exception as e:
                    error_msg = f"Cotización {i} ({numero_cotizacion}): {str(e)}"
                    errores.append(error_msg)
                    print(f"❌ {error_msg}")
            
            # Commit de la transacción
            self.connection.commit()
            cursor.close()
            
            # Reporte final
            print(f"\n🎉 MIGRACIÓN COMPLETADA")
            print("="*40)
            print(f"✅ Cotizaciones migradas: {migradas}")
            print(f"❌ Errores: {len(errores)}")
            
            if errores:
                print(f"\n⚠️  ERRORES ENCONTRADOS:")
                for error in errores[:10]:  # Mostrar primeros 10
                    print(f"   - {error}")
                if len(errores) > 10:
                    print(f"   ... y {len(errores) - 10} errores más")
            
            return len(errores) == 0
            
        except Exception as e:
            print(f"❌ Error durante migración: {e}")
            self.connection.rollback()
            return False
    
    def validate_migration(self) -> bool:
        """Validar que la migración fue exitosa"""
        try:
            cursor = self.connection.cursor()
            
            print(f"\n🔍 VALIDANDO MIGRACIÓN")
            print("="*30)
            
            # Contar registros en PostgreSQL
            cursor.execute("SELECT COUNT(*) FROM cotizaciones;")
            count_pg = cursor.fetchone()[0]
            
            # Contar registros en JSON
            data = self.load_json_data()
            if not data:
                return False
            count_json = len(data.get('cotizaciones', []))
            
            print(f"📊 Registros en JSON: {count_json}")
            print(f"📊 Registros en PostgreSQL: {count_pg}")
            
            if count_pg != count_json:
                print(f"❌ DISCREPANCIA: JSON={count_json}, PostgreSQL={count_pg}")
                return False
            
            # Validar algunos registros aleatorios
            cursor.execute("""
                SELECT numero_cotizacion, datos_generales->>'cliente', 
                       datos_generales->>'vendedor' 
                FROM cotizaciones 
                ORDER BY RANDOM() 
                LIMIT 3;
            """)
            
            muestra = cursor.fetchall()
            print(f"\n📋 MUESTRA DE DATOS MIGRADOS:")
            for numero, cliente, vendedor in muestra:
                print(f"   {numero} | {cliente} | {vendedor}")
            
            cursor.close()
            print(f"\n✅ VALIDACIÓN EXITOSA: {count_pg} registros migrados correctamente")
            return True
            
        except Exception as e:
            print(f"❌ Error validando migración: {e}")
            return False
    
    def close_connection(self):
        """Cerrar conexión"""
        if self.connection:
            self.connection.close()
            print("🔌 Conexión cerrada")

def main():
    parser = argparse.ArgumentParser(description='Migración JSON → Supabase')
    parser.add_argument('--preview', action='store_true', 
                       help='Ver preview de migración (sin cambios)')
    parser.add_argument('--migrate', action='store_true', 
                       help='Ejecutar migración real')
    parser.add_argument('--validate', action='store_true', 
                       help='Validar migración existente')
    parser.add_argument('--production', action='store_true', 
                       help='Modo producción (para Render)')
    
    args = parser.parse_args()
    
    if not any([args.preview, args.migrate, args.validate]):
        print("❌ Especifica una acción: --preview, --migrate, o --validate")
        parser.print_help()
        sys.exit(1)
    
    # Crear migrator
    migrator = SupabaseMigrator()
    
    # Conectar a Supabase
    if not migrator.connect_to_supabase():
        sys.exit(1)
    
    # Validar schema
    if not migrator.validate_schema():
        migrator.close_connection()
        sys.exit(1)
    
    try:
        if args.preview or args.migrate:
            # Cargar datos JSON
            data = migrator.load_json_data()
            if not data:
                migrator.close_connection()
                sys.exit(1)
        
        if args.preview:
            migrator.preview_migration(data)
        
        elif args.migrate:
            if not migrator.migrate_data(data):
                print("❌ Migración falló")
                migrator.close_connection()
                sys.exit(1)
        
        elif args.validate:
            if not migrator.validate_migration():
                print("❌ Validación falló")
                migrator.close_connection()
                sys.exit(1)
        
        print(f"\n🎉 Operación completada exitosamente")
        
    finally:
        migrator.close_connection()

if __name__ == '__main__':
    main()