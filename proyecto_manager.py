#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROYECTO MANAGER - Gestión de Proyectos y Gastos
================================================

Administrador de proyectos vinculados a OCs y sus gastos asociados.
Maneja aprobaciones, estatus de compra y cálculos financieros.

Características:
- Gestión de proyectos vinculados a OCs
- CRUD de gastos con validación de presupuesto
- Sistema de aprobaciones
- Control de estatus de compra (pendiente, ordenado, recibido)
- Cálculos financieros automáticos
- Integración con notificaciones
"""

import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

class ProyectoManager:
    """Administrador de Proyectos y Gastos"""

    def __init__(self):
        """Inicializar manager con conexión a Supabase"""
        self.database_url = os.getenv('DATABASE_URL')
        self.pg_connection = None

        # Inicializar conexión
        self._inicializar_conexion()

    def _inicializar_conexion(self):
        """Establecer conexión a PostgreSQL"""
        try:
            if self.database_url:
                try:
                    self.pg_connection = psycopg2.connect(self.database_url)
                    print("[PROYECTO_MANAGER] Conexión PostgreSQL establecida")
                except Exception as pg_error:
                    print(f"[PROYECTO_MANAGER] PostgreSQL no disponible (continuando sin conexión directa): {pg_error}")
                    self.pg_connection = None
        except Exception as e:
            print(f"[PROYECTO_MANAGER] Error iniciando conexión: {e}")
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
            print(f"[PROYECTO_MANAGER] Error obteniendo cursor: {e}")
            raise Exception(f"Base de datos no disponible: {str(e)}")

    # ========================================
    # GESTIÓN DE PROYECTOS
    # ========================================

    def obtener_proyecto(self, proyecto_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener proyecto con información completa

        Returns:
            Proyecto con datos de OC y resumen financiero
        """
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                SELECT
                    p.*,
                    oc.numero_oc,
                    oc.cliente,
                    oc.monto_total as oc_monto_total,
                    oc.moneda,
                    oc.archivo_pdf as oc_archivo_pdf,
                    vr.monto_gastado,
                    vr.monto_disponible,
                    vr.total_gastos,
                    vr.gastos_aprobados,
                    vr.gastos_ordenados,
                    vr.gastos_recibidos,
                    vr.progreso_porcentaje
                FROM proyectos p
                INNER JOIN ordenes_compra oc ON p.oc_id = oc.id
                LEFT JOIN vista_resumen_proyectos vr ON p.id = vr.id
                WHERE p.id = %s
            """, (proyecto_id,))

            resultado = cursor.fetchone()
            cursor.close()

            if resultado:
                return dict(resultado)
            return None

        except Exception as e:
            print(f"[PROYECTO_MANAGER] Error obteniendo proyecto {proyecto_id}: {e}")
            return None

    def obtener_proyecto_por_oc(self, oc_id: int) -> Optional[Dict[str, Any]]:
        """Obtener proyecto vinculado a una OC"""
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                SELECT id FROM proyectos WHERE oc_id = %s
            """, (oc_id,))

            resultado = cursor.fetchone()
            cursor.close()

            if resultado:
                return self.obtener_proyecto(resultado['id'])
            return None

        except Exception as e:
            print(f"[PROYECTO_MANAGER] Error obteniendo proyecto por OC {oc_id}: {e}")
            return None

    def actualizar_proyecto(self, proyecto_id: int, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar información del proyecto

        Args:
            proyecto_id: ID del proyecto
            datos: Campos a actualizar ('nombre', 'estatus', 'monto_presupuestado')

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            campos_permitidos = ['nombre', 'estatus', 'monto_presupuestado']
            campos_actualizar = []
            valores = []

            for campo in campos_permitidos:
                if campo in datos:
                    campos_actualizar.append(f"{campo} = %s")
                    valores.append(datos[campo])

            if not campos_actualizar:
                return {'success': False, 'message': 'No hay campos para actualizar'}

            valores.append(proyecto_id)

            cursor = self._get_cursor()
            query = f"""
                UPDATE proyectos
                SET {', '.join(campos_actualizar)}
                WHERE id = %s
            """

            cursor.execute(query, tuple(valores))
            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Proyecto {proyecto_id} actualizado")

            return {'success': True, 'message': 'Proyecto actualizado exitosamente'}

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error actualizando proyecto {proyecto_id}: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    # ========================================
    # GESTIÓN DE GASTOS
    # ========================================

    def crear_gasto(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear nuevo gasto en proyecto

        Args:
            datos: {
                'proyecto_id': int,
                'concepto': str,
                'proveedor': str,
                'cantidad': float,
                'unidad': str,
                'precio_unitario': float,
                'notas': str (opcional)
            }

        Returns:
            {'success': bool, 'gasto_id': int, 'message': str}
        """
        try:
            # Validar presupuesto disponible
            proyecto = self.obtener_proyecto(datos['proyecto_id'])
            if not proyecto:
                return {'success': False, 'message': 'Proyecto no encontrado'}

            subtotal = Decimal(str(datos['cantidad'])) * Decimal(str(datos['precio_unitario']))
            monto_disponible = Decimal(str(proyecto['monto_disponible'] or proyecto['monto_presupuestado']))

            if subtotal > monto_disponible:
                return {
                    'success': False,
                    'message': f'Presupuesto insuficiente. Disponible: ${monto_disponible:,.2f}, Solicitado: ${subtotal:,.2f}'
                }

            # Insertar gasto
            cursor = self._get_cursor()
            cursor.execute("""
                INSERT INTO gastos_proyecto
                (proyecto_id, concepto, proveedor, cantidad, unidad, precio_unitario, notas)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                datos['proyecto_id'],
                datos['concepto'],
                datos.get('proveedor', ''),
                datos['cantidad'],
                datos.get('unidad', 'pieza'),
                datos['precio_unitario'],
                datos.get('notas', '')
            ))

            gasto_id = cursor.fetchone()['id']
            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Gasto creado: {datos['concepto']} (ID: {gasto_id})")

            return {
                'success': True,
                'gasto_id': gasto_id,
                'message': 'Gasto creado exitosamente',
                'requiere_aprobacion': True
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error creando gasto: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def obtener_gasto(self, gasto_id: int) -> Optional[Dict[str, Any]]:
        """Obtener información completa de un gasto"""
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                SELECT
                    g.*,
                    p.nombre as proyecto_nombre,
                    p.oc_id,
                    oc.numero_oc,
                    oc.cliente
                FROM gastos_proyecto g
                INNER JOIN proyectos p ON g.proyecto_id = p.id
                INNER JOIN ordenes_compra oc ON p.oc_id = oc.id
                WHERE g.id = %s
            """, (gasto_id,))

            resultado = cursor.fetchone()
            cursor.close()

            if resultado:
                return dict(resultado)
            return None

        except Exception as e:
            print(f"[PROYECTO_MANAGER] Error obteniendo gasto {gasto_id}: {e}")
            return None

    def listar_gastos_proyecto(self, proyecto_id: int,
                               filtro_estatus: Optional[str] = None,
                               filtro_aprobado: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Listar gastos de un proyecto

        Args:
            proyecto_id: ID del proyecto
            filtro_estatus: Filtrar por estatus de compra
            filtro_aprobado: Filtrar por aprobación (True/False/None)

        Returns:
            Lista de gastos
        """
        try:
            cursor = self._get_cursor()

            query = """
                SELECT *
                FROM gastos_proyecto
                WHERE proyecto_id = %s
            """

            params = [proyecto_id]

            if filtro_estatus:
                query += " AND estatus_compra = %s"
                params.append(filtro_estatus)

            if filtro_aprobado is not None:
                query += " AND aprobado = %s"
                params.append(filtro_aprobado)

            query += " ORDER BY created_at DESC"

            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in resultados]

        except Exception as e:
            print(f"[PROYECTO_MANAGER] Error listando gastos del proyecto {proyecto_id}: {e}")
            return []

    def actualizar_gasto(self, gasto_id: int, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar gasto existente

        Args:
            gasto_id: ID del gasto
            datos: Campos a actualizar

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # Verificar que el gasto no esté ordenado o recibido
            gasto = self.obtener_gasto(gasto_id)
            if not gasto:
                return {'success': False, 'message': 'Gasto no encontrado'}

            if gasto['estatus_compra'] in ['ordenado', 'recibido']:
                return {
                    'success': False,
                    'message': f"No se puede editar un gasto {gasto['estatus_compra']}"
                }

            # Campos permitidos para actualizar
            campos_permitidos = ['concepto', 'proveedor', 'cantidad', 'unidad', 'precio_unitario', 'notas']
            campos_actualizar = []
            valores = []

            for campo in campos_permitidos:
                if campo in datos:
                    campos_actualizar.append(f"{campo} = %s")
                    valores.append(datos[campo])

            if not campos_actualizar:
                return {'success': False, 'message': 'No hay campos para actualizar'}

            valores.append(gasto_id)

            cursor = self._get_cursor()
            query = f"""
                UPDATE gastos_proyecto
                SET {', '.join(campos_actualizar)}
                WHERE id = %s
            """

            cursor.execute(query, tuple(valores))
            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Gasto {gasto_id} actualizado")

            return {'success': True, 'message': 'Gasto actualizado exitosamente'}

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error actualizando gasto {gasto_id}: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def eliminar_gasto(self, gasto_id: int) -> Dict[str, Any]:
        """
        Eliminar gasto (solo si no está ordenado o recibido)

        Args:
            gasto_id: ID del gasto

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            gasto = self.obtener_gasto(gasto_id)
            if not gasto:
                return {'success': False, 'message': 'Gasto no encontrado'}

            if gasto['estatus_compra'] in ['ordenado', 'recibido']:
                return {
                    'success': False,
                    'message': f"No se puede eliminar un gasto {gasto['estatus_compra']}"
                }

            cursor = self._get_cursor()
            cursor.execute("DELETE FROM gastos_proyecto WHERE id = %s", (gasto_id,))
            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Gasto {gasto_id} eliminado")

            return {'success': True, 'message': 'Gasto eliminado exitosamente'}

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error eliminando gasto {gasto_id}: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    # ========================================
    # SISTEMA DE APROBACIONES
    # ========================================

    def aprobar_gasto(self, gasto_id: int, aprobador: str) -> Dict[str, Any]:
        """
        Aprobar gasto

        Args:
            gasto_id: ID del gasto
            aprobador: Nombre del usuario que aprueba

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                UPDATE gastos_proyecto
                SET
                    aprobado = TRUE,
                    aprobado_por = %s,
                    fecha_aprobacion = NOW()
                WHERE id = %s AND aprobado = FALSE
                RETURNING proyecto_id
            """, (aprobador, gasto_id))

            resultado = cursor.fetchone()

            if not resultado:
                cursor.close()
                return {'success': False, 'message': 'Gasto no encontrado o ya aprobado'}

            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Gasto {gasto_id} aprobado por {aprobador}")

            return {
                'success': True,
                'message': 'Gasto aprobado exitosamente',
                'proyecto_id': resultado['proyecto_id']
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error aprobando gasto {gasto_id}: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def rechazar_gasto(self, gasto_id: int, motivo: Optional[str] = None) -> Dict[str, Any]:
        """
        Rechazar gasto (lo marca como cancelado)

        Args:
            gasto_id: ID del gasto
            motivo: Razón del rechazo

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            notas_rechazo = f"RECHAZADO: {motivo}" if motivo else "RECHAZADO"

            cursor.execute("""
                UPDATE gastos_proyecto
                SET
                    estatus_compra = 'cancelado',
                    notas = CONCAT(COALESCE(notas, ''), '\n', %s)
                WHERE id = %s AND aprobado = FALSE
                RETURNING proyecto_id
            """, (notas_rechazo, gasto_id))

            resultado = cursor.fetchone()

            if not resultado:
                cursor.close()
                return {'success': False, 'message': 'Gasto no encontrado o ya aprobado'}

            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Gasto {gasto_id} rechazado")

            return {
                'success': True,
                'message': 'Gasto rechazado',
                'proyecto_id': resultado['proyecto_id']
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error rechazando gasto {gasto_id}: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    # ========================================
    # CONTROL DE ESTATUS DE COMPRA
    # ========================================

    def marcar_como_ordenado(self, gasto_id: int, numero_orden: str, fecha_orden: Optional[date] = None) -> Dict[str, Any]:
        """
        Marcar gasto como ordenado

        Args:
            gasto_id: ID del gasto
            numero_orden: Número de orden de compra
            fecha_orden: Fecha de la orden (opcional, default hoy)

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # Verificar que el gasto esté aprobado
            gasto = self.obtener_gasto(gasto_id)
            if not gasto:
                return {'success': False, 'message': 'Gasto no encontrado'}

            if not gasto['aprobado']:
                return {'success': False, 'message': 'El gasto debe estar aprobado primero'}

            cursor = self._get_cursor()
            cursor.execute("""
                UPDATE gastos_proyecto
                SET
                    estatus_compra = 'ordenado',
                    numero_orden = %s,
                    fecha_orden = %s
                WHERE id = %s
            """, (numero_orden, fecha_orden or date.today(), gasto_id))

            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Gasto {gasto_id} marcado como ordenado (Orden: {numero_orden})")

            return {'success': True, 'message': 'Gasto marcado como ordenado'}

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error marcando gasto como ordenado: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def marcar_como_recibido(self, gasto_id: int) -> Dict[str, Any]:
        """
        Marcar gasto como recibido

        Args:
            gasto_id: ID del gasto

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # Verificar que el gasto esté ordenado
            gasto = self.obtener_gasto(gasto_id)
            if not gasto:
                return {'success': False, 'message': 'Gasto no encontrado'}

            if gasto['estatus_compra'] != 'ordenado':
                return {'success': False, 'message': 'El gasto debe estar ordenado primero'}

            cursor = self._get_cursor()
            cursor.execute("""
                UPDATE gastos_proyecto
                SET estatus_compra = 'recibido'
                WHERE id = %s
            """, (gasto_id,))

            self.pg_connection.commit()
            cursor.close()

            print(f"[PROYECTO_MANAGER] Gasto {gasto_id} marcado como recibido")

            return {'success': True, 'message': 'Gasto marcado como recibido'}

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[PROYECTO_MANAGER] Error marcando gasto como recibido: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    # ========================================
    # ESTADÍSTICAS Y REPORTES
    # ========================================

    def obtener_gastos_pendientes_aprobacion(self, usuario: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtener gastos pendientes de aprobación

        Args:
            usuario: Filtrar por usuario (opcional)

        Returns:
            Lista de gastos pendientes con información del proyecto
        """
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                SELECT *
                FROM vista_gastos_pendientes
                ORDER BY horas_pendiente DESC
            """)

            resultados = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in resultados]

        except Exception as e:
            print(f"[PROYECTO_MANAGER] Error obteniendo gastos pendientes: {e}")
            return []

    def __del__(self):
        """Cerrar conexiones al destruir objeto"""
        if self.pg_connection and not self.pg_connection.closed:
            self.pg_connection.close()
            print("[PROYECTO_MANAGER] Conexión cerrada")
