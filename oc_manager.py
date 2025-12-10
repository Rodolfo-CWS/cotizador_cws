#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OC MANAGER - Gestión de Órdenes de Compra
=========================================

Administrador de órdenes de compra con integración a Supabase.
Crea automáticamente proyectos vinculados a cada OC.

Características:
- Gestión completa de OCs (CRUD)
- Upload de PDFs a Supabase Storage
- Creación automática de proyectos
- Búsqueda y filtrado optimizado
- Notificaciones automáticas
"""

import os
import json
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

class OCManager:
    """Administrador de Órdenes de Compra"""

    def __init__(self):
        """Inicializar manager con conexión a Supabase"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.database_url = os.getenv('DATABASE_URL')

        self.supabase_client: Optional[Client] = None
        self.pg_connection = None

        # Inicializar conexión
        self._inicializar_conexion()

    def _inicializar_conexion(self):
        """Establecer conexión a Supabase"""
        try:
            if self.supabase_url and self.supabase_key:
                self.supabase_client = create_client(self.supabase_url, self.supabase_key)
                print("[OC_MANAGER] Cliente Supabase inicializado")

            if self.database_url:
                try:
                    self.pg_connection = psycopg2.connect(self.database_url)
                    print("[OC_MANAGER] Conexión PostgreSQL establecida")
                except Exception as pg_error:
                    print(f"[OC_MANAGER] PostgreSQL no disponible (continuando sin conexión directa): {pg_error}")
                    self.pg_connection = None

        except Exception as e:
            print(f"[OC_MANAGER] Error iniciando conexión: {e}")
            # Continuar sin fallar - app debe poder iniciar aunque managers fallen

    def _get_cursor(self):
        """Obtener cursor de base de datos con manejo de errores"""
        try:
            if not self.pg_connection or self.pg_connection.closed:
                if not self.database_url:
                    raise Exception("DATABASE_URL no configurado")
                self.pg_connection = psycopg2.connect(self.database_url)
            return self.pg_connection.cursor(cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"[OC_MANAGER] Error obteniendo cursor: {e}")
            raise Exception(f"Base de datos no disponible: {str(e)}")

    # ========================================
    # CRUD DE ÓRDENES DE COMPRA
    # ========================================

    def crear_oc(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear nueva orden de compra

        Args:
            datos: {
                'numero_oc': str,
                'cliente': str,
                'monto_total': float,
                'moneda': 'MXN' | 'USD',
                'fecha_recepcion': str (YYYY-MM-DD),
                'archivo_pdf': str (URL),
                'notas': str
            }

        Returns:
            {'success': bool, 'oc_id': int, 'proyecto_id': int, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            # Validar que no exista OC con mismo número
            cursor.execute(
                "SELECT id FROM ordenes_compra WHERE numero_oc = %s",
                (datos['numero_oc'],)
            )
            if cursor.fetchone():
                return {
                    'success': False,
                    'message': f"Ya existe una OC con el número {datos['numero_oc']}"
                }

            # Insertar OC
            cursor.execute("""
                INSERT INTO ordenes_compra
                (numero_oc, cliente, fecha_recepcion, monto_total, moneda, archivo_pdf, notas, estatus)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'activa')
                RETURNING id
            """, (
                datos['numero_oc'],
                datos['cliente'],
                datos.get('fecha_recepcion', date.today()),
                datos['monto_total'],
                datos.get('moneda', 'MXN'),
                datos.get('archivo_pdf'),
                datos.get('notas', '')
            ))

            oc_id = cursor.fetchone()['id']

            # Crear proyecto automáticamente
            nombre_proyecto = f"{datos['cliente']} - {datos['numero_oc']}"

            cursor.execute("""
                INSERT INTO proyectos
                (nombre, oc_id, fecha_inicio, monto_presupuestado, estatus)
                VALUES (%s, %s, %s, %s, 'activo')
                RETURNING id
            """, (
                nombre_proyecto,
                oc_id,
                datos.get('fecha_recepcion', date.today()),
                datos['monto_total']
            ))

            proyecto_id = cursor.fetchone()['id']

            self.pg_connection.commit()
            cursor.close()

            print(f"[OC_MANAGER] OC creada exitosamente: {datos['numero_oc']} (ID: {oc_id})")
            print(f"[OC_MANAGER] Proyecto creado automáticamente (ID: {proyecto_id})")

            return {
                'success': True,
                'oc_id': oc_id,
                'proyecto_id': proyecto_id,
                'message': 'Orden de compra y proyecto creados exitosamente'
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[OC_MANAGER] Error creando OC: {e}")
            return {
                'success': False,
                'message': f'Error al crear OC: {str(e)}'
            }

    def obtener_oc(self, oc_id: int) -> Optional[Dict[str, Any]]:
        """Obtener orden de compra por ID"""
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                SELECT
                    oc.*,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    p.estatus as proyecto_estatus
                FROM ordenes_compra oc
                LEFT JOIN proyectos p ON oc.id = p.oc_id
                WHERE oc.id = %s
            """, (oc_id,))

            resultado = cursor.fetchone()
            cursor.close()

            if resultado:
                return dict(resultado)
            return None

        except Exception as e:
            print(f"[OC_MANAGER] Error obteniendo OC {oc_id}: {e}")
            return None

    def obtener_oc_por_numero(self, numero_oc: str) -> Optional[Dict[str, Any]]:
        """Obtener orden de compra por número de OC"""
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                SELECT
                    oc.*,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    p.estatus as proyecto_estatus
                FROM ordenes_compra oc
                LEFT JOIN proyectos p ON oc.id = p.oc_id
                WHERE oc.numero_oc = %s
            """, (numero_oc,))

            resultado = cursor.fetchone()
            cursor.close()

            if resultado:
                return dict(resultado)
            return None

        except Exception as e:
            print(f"[OC_MANAGER] Error obteniendo OC por número {numero_oc}: {e}")
            return None

    def actualizar_oc(self, oc_id: int, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar orden de compra existente

        Args:
            oc_id: ID de la OC
            datos: Campos a actualizar

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # Construir query dinámicamente según campos proporcionados
            campos_permitidos = ['cliente', 'monto_total', 'moneda', 'archivo_pdf', 'notas', 'estatus']
            campos_actualizar = []
            valores = []

            for campo in campos_permitidos:
                if campo in datos:
                    campos_actualizar.append(f"{campo} = %s")
                    valores.append(datos[campo])

            if not campos_actualizar:
                return {'success': False, 'message': 'No hay campos para actualizar'}

            valores.append(oc_id)

            cursor = self._get_cursor()
            query = f"""
                UPDATE ordenes_compra
                SET {', '.join(campos_actualizar)}
                WHERE id = %s
            """

            cursor.execute(query, tuple(valores))

            # Si se actualiza el monto, actualizar también el presupuesto del proyecto
            if 'monto_total' in datos:
                cursor.execute("""
                    UPDATE proyectos
                    SET monto_presupuestado = %s
                    WHERE oc_id = %s
                """, (datos['monto_total'], oc_id))

            self.pg_connection.commit()
            cursor.close()

            print(f"[OC_MANAGER] OC {oc_id} actualizada exitosamente")

            return {
                'success': True,
                'message': 'Orden de compra actualizada exitosamente'
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[OC_MANAGER] Error actualizando OC {oc_id}: {e}")
            return {
                'success': False,
                'message': f'Error al actualizar OC: {str(e)}'
            }

    def eliminar_oc(self, oc_id: int) -> Dict[str, Any]:
        """
        Eliminar orden de compra (y proyecto asociado por CASCADE)

        Args:
            oc_id: ID de la OC a eliminar

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            # Verificar que la OC exista
            cursor.execute("SELECT numero_oc FROM ordenes_compra WHERE id = %s", (oc_id,))
            oc = cursor.fetchone()

            if not oc:
                cursor.close()
                return {'success': False, 'message': 'OC no encontrada'}

            # Eliminar OC (el proyecto se eliminará automáticamente por CASCADE)
            cursor.execute("DELETE FROM ordenes_compra WHERE id = %s", (oc_id,))
            self.pg_connection.commit()
            cursor.close()

            print(f"[OC_MANAGER] OC {oc['numero_oc']} eliminada exitosamente")

            return {
                'success': True,
                'message': f"OC {oc['numero_oc']} y su proyecto eliminados exitosamente"
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[OC_MANAGER] Error eliminando OC {oc_id}: {e}")
            return {
                'success': False,
                'message': f'Error al eliminar OC: {str(e)}'
            }

    # ========================================
    # BÚSQUEDA Y LISTADO
    # ========================================

    def listar_ocs(self, filtros: Optional[Dict[str, Any]] = None,
                   ordenar_por: str = 'fecha_recepcion',
                   orden: str = 'DESC',
                   limite: int = 100) -> List[Dict[str, Any]]:
        """
        Listar órdenes de compra con filtros opcionales

        Args:
            filtros: {
                'cliente': str,
                'estatus': str,
                'moneda': str,
                'fecha_desde': str,
                'fecha_hasta': str
            }
            ordenar_por: Campo por el que ordenar
            orden: 'ASC' o 'DESC'
            limite: Máximo de resultados

        Returns:
            Lista de OCs con información del proyecto
        """
        try:
            cursor = self._get_cursor()

            # Base query
            query = """
                SELECT
                    oc.*,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    p.estatus as proyecto_estatus,
                    vr.monto_gastado,
                    vr.monto_disponible,
                    vr.progreso_porcentaje
                FROM ordenes_compra oc
                LEFT JOIN proyectos p ON oc.id = p.oc_id
                LEFT JOIN vista_resumen_proyectos vr ON p.id = vr.id
                WHERE 1=1
            """

            params = []

            # Aplicar filtros
            if filtros:
                if 'cliente' in filtros:
                    query += " AND oc.cliente ILIKE %s"
                    params.append(f"%{filtros['cliente']}%")

                if 'estatus' in filtros:
                    query += " AND oc.estatus = %s"
                    params.append(filtros['estatus'])

                if 'moneda' in filtros:
                    query += " AND oc.moneda = %s"
                    params.append(filtros['moneda'])

                if 'fecha_desde' in filtros:
                    query += " AND oc.fecha_recepcion >= %s"
                    params.append(filtros['fecha_desde'])

                if 'fecha_hasta' in filtros:
                    query += " AND oc.fecha_recepcion <= %s"
                    params.append(filtros['fecha_hasta'])

            # Ordenamiento
            campos_ordenamiento = ['fecha_recepcion', 'cliente', 'monto_total', 'estatus', 'numero_oc']
            if ordenar_por in campos_ordenamiento:
                query += f" ORDER BY oc.{ordenar_por} {orden}"
            else:
                query += f" ORDER BY oc.fecha_recepcion DESC"

            query += f" LIMIT {limite}"

            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in resultados]

        except Exception as e:
            print(f"[OC_MANAGER] Error listando OCs: {e}")
            return []

    def buscar_ocs(self, query: str) -> List[Dict[str, Any]]:
        """
        Buscar órdenes de compra por texto

        Args:
            query: Texto a buscar (número OC, cliente, proyecto)

        Returns:
            Lista de OCs que coinciden con la búsqueda
        """
        try:
            cursor = self._get_cursor()

            sql = """
                SELECT
                    oc.*,
                    p.id as proyecto_id,
                    p.nombre as proyecto_nombre,
                    p.estatus as proyecto_estatus,
                    vr.progreso_porcentaje
                FROM ordenes_compra oc
                LEFT JOIN proyectos p ON oc.id = p.oc_id
                LEFT JOIN vista_resumen_proyectos vr ON p.id = vr.id
                WHERE
                    oc.numero_oc ILIKE %s OR
                    oc.cliente ILIKE %s OR
                    p.nombre ILIKE %s OR
                    oc.notas ILIKE %s
                ORDER BY oc.fecha_recepcion DESC
                LIMIT 50
            """

            busqueda = f"%{query}%"
            cursor.execute(sql, (busqueda, busqueda, busqueda, busqueda))
            resultados = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in resultados]

        except Exception as e:
            print(f"[OC_MANAGER] Error buscando OCs: {e}")
            return []

    # ========================================
    # ESTADÍSTICAS Y REPORTES
    # ========================================

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtener estadísticas generales de órdenes de compra"""
        try:
            cursor = self._get_cursor()

            # Total de OCs por estatus
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE estatus = 'activa') as activas,
                    COUNT(*) FILTER (WHERE estatus = 'en_proceso') as en_proceso,
                    COUNT(*) FILTER (WHERE estatus = 'completada') as completadas,
                    COUNT(*) FILTER (WHERE estatus = 'cancelada') as canceladas,
                    COUNT(*) as total,
                    SUM(monto_total) FILTER (WHERE estatus IN ('activa', 'en_proceso')) as monto_activo,
                    SUM(monto_total) as monto_total_historico
                FROM ordenes_compra
            """)

            stats = dict(cursor.fetchone())
            cursor.close()

            return stats

        except Exception as e:
            print(f"[OC_MANAGER] Error obteniendo estadísticas: {e}")
            return {
                'activas': 0,
                'en_proceso': 0,
                'completadas': 0,
                'canceladas': 0,
                'total': 0,
                'monto_activo': 0,
                'monto_total_historico': 0
            }

    def __del__(self):
        """Cerrar conexiones al destruir objeto"""
        if self.pg_connection and not self.pg_connection.closed:
            self.pg_connection.close()
            print("[OC_MANAGER] Conexión cerrada")
