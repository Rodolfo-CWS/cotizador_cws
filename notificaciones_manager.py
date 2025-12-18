#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTIFICACIONES MANAGER - Sistema de Notificaciones In-App
=========================================================

Sistema de notificaciones para usuarios del módulo de proyectos.
Notifica eventos importantes como aprobaciones, rechazos, nuevas OCs, etc.

Características:
- Notificaciones in-app para usuarios
- Sistema de lectura/no leída
- Tipos de notificación categorizados
- Metadata flexible para información adicional
- Limpieza automática de notificaciones antiguas
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv

load_dotenv()

class NotificacionesManager:
    """Administrador de Notificaciones In-App"""

    # Tipos de notificación disponibles
    TIPO_GASTO_PENDIENTE = 'gasto_pendiente'
    TIPO_GASTO_APROBADO = 'gasto_aprobado'
    TIPO_GASTO_RECHAZADO = 'gasto_rechazado'
    TIPO_OC_NUEVA = 'oc_nueva'
    TIPO_PRESUPUESTO_EXCEDIDO = 'presupuesto_excedido'
    TIPO_GASTO_ORDENADO = 'gasto_ordenado'
    TIPO_GASTO_RECIBIDO = 'gasto_recibido'

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
                    print("[NOTIFICACIONES_MANAGER] Conexión PostgreSQL establecida")
                except Exception as pg_error:
                    print(f"[NOTIFICACIONES_MANAGER] PostgreSQL no disponible (continuando sin conexión directa): {pg_error}")
                    self.pg_connection = None
        except Exception as e:
            print(f"[NOTIFICACIONES_MANAGER] Error iniciando conexión: {e}")
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
            print(f"[NOTIFICACIONES_MANAGER] Error obteniendo cursor: {e}")
            raise Exception(f"Base de datos no disponible: {str(e)}")

    # ========================================
    # CREAR NOTIFICACIONES
    # ========================================

    def crear_notificacion(self,
                          usuario: str,
                          tipo: str,
                          titulo: str,
                          mensaje: str,
                          enlace: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Crear nueva notificación para un usuario

        Args:
            usuario: Nombre del usuario destinatario
            tipo: Tipo de notificación (usar constantes TIPO_*)
            titulo: Título de la notificación
            mensaje: Mensaje descriptivo
            enlace: URL para ir al recurso (opcional)
            metadata: Datos adicionales en formato dict (opcional)

        Returns:
            {'success': bool, 'notificacion_id': int, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            cursor.execute("""
                INSERT INTO notificaciones
                (usuario_destinatario, tipo, titulo, mensaje, enlace, metadata, leida)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                RETURNING id
            """, (
                usuario,
                tipo,
                titulo,
                mensaje,
                enlace,
                Json(metadata) if metadata else None
            ))

            notificacion_id = cursor.fetchone()['id']
            self.pg_connection.commit()
            cursor.close()

            print(f"[NOTIFICACIONES] Notificación creada para {usuario}: {titulo}")

            return {
                'success': True,
                'notificacion_id': notificacion_id,
                'message': 'Notificación creada exitosamente'
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[NOTIFICACIONES] Error creando notificación: {e}")
            return {
                'success': False,
                'message': f'Error al crear notificación: {str(e)}'
            }

    # ========================================
    # NOTIFICACIONES ESPECÍFICAS DE NEGOCIO
    # ========================================

    def notificar_gasto_pendiente(self, gasto_id: int, gasto_info: Dict[str, Any],
                                  aprobador: str) -> Dict[str, Any]:
        """
        Notificar que hay un gasto pendiente de aprobación

        Args:
            gasto_id: ID del gasto
            gasto_info: Información del gasto (concepto, monto, proyecto, etc.)
            aprobador: Usuario que debe aprobar

        Returns:
            Resultado de crear_notificacion
        """
        titulo = "⏳ Gasto pendiente de aprobación"
        mensaje = f"Proyecto: {gasto_info.get('proyecto_nombre', 'N/A')}\n"
        mensaje += f"Concepto: {gasto_info.get('concepto', 'N/A')}\n"
        mensaje += f"Monto: ${gasto_info.get('subtotal', 0):,.2f}"

        enlace = f"/proyecto/{gasto_info.get('proyecto_id')}"

        metadata = {
            'gasto_id': gasto_id,
            'proyecto_id': gasto_info.get('proyecto_id'),
            'monto': float(gasto_info.get('subtotal', 0))
        }

        return self.crear_notificacion(
            usuario=aprobador,
            tipo=self.TIPO_GASTO_PENDIENTE,
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
            metadata=metadata
        )

    def notificar_gasto_aprobado(self, gasto_id: int, gasto_info: Dict[str, Any],
                                aprobador: str, solicitante: str) -> Dict[str, Any]:
        """
        Notificar que un gasto fue aprobado

        Args:
            gasto_id: ID del gasto
            gasto_info: Información del gasto
            aprobador: Usuario que aprobó
            solicitante: Usuario que creó el gasto

        Returns:
            Resultado de crear_notificacion
        """
        titulo = "✅ Gasto aprobado"
        mensaje = f"Tu gasto '{gasto_info.get('concepto', 'N/A')}' fue aprobado por {aprobador}\n"
        mensaje += f"Monto: ${gasto_info.get('subtotal', 0):,.2f}\n"
        mensaje += f"Proyecto: {gasto_info.get('proyecto_nombre', 'N/A')}"

        enlace = f"/proyecto/{gasto_info.get('proyecto_id')}"

        metadata = {
            'gasto_id': gasto_id,
            'proyecto_id': gasto_info.get('proyecto_id'),
            'aprobador': aprobador,
            'monto': float(gasto_info.get('subtotal', 0))
        }

        return self.crear_notificacion(
            usuario=solicitante,
            tipo=self.TIPO_GASTO_APROBADO,
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
            metadata=metadata
        )

    def notificar_gasto_rechazado(self, gasto_id: int, gasto_info: Dict[str, Any],
                                  motivo: str, solicitante: str) -> Dict[str, Any]:
        """
        Notificar que un gasto fue rechazado

        Args:
            gasto_id: ID del gasto
            gasto_info: Información del gasto
            motivo: Razón del rechazo
            solicitante: Usuario que creó el gasto

        Returns:
            Resultado de crear_notificacion
        """
        titulo = "❌ Gasto rechazado"
        mensaje = f"Tu gasto '{gasto_info.get('concepto', 'N/A')}' fue rechazado\n"
        mensaje += f"Motivo: {motivo}\n"
        mensaje += f"Proyecto: {gasto_info.get('proyecto_nombre', 'N/A')}"

        enlace = f"/proyecto/{gasto_info.get('proyecto_id')}"

        metadata = {
            'gasto_id': gasto_id,
            'proyecto_id': gasto_info.get('proyecto_id'),
            'motivo': motivo
        }

        return self.crear_notificacion(
            usuario=solicitante,
            tipo=self.TIPO_GASTO_RECHAZADO,
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
            metadata=metadata
        )

    def notificar_oc_nueva(self, oc_info: Dict[str, Any], responsable: str) -> Dict[str, Any]:
        """
        Notificar sobre una nueva orden de compra

        Args:
            oc_info: Información de la OC (numero_oc, cliente, monto)
            responsable: Usuario responsable del proyecto

        Returns:
            Resultado de crear_notificacion
        """
        print(f"[NOTIF_OC] Creando notificación para OC: {oc_info.get('numero_oc')}")
        print(f"[NOTIF_OC] Proyecto ID recibido: {oc_info.get('proyecto_id')}")

        titulo = "📦 Nueva Orden de Compra"
        mensaje = f"OC: {oc_info.get('numero_oc', 'N/A')}\n"
        mensaje += f"Cliente: {oc_info.get('cliente', 'N/A')}\n"
        mensaje += f"Monto: ${oc_info.get('monto_total', 0):,.2f} {oc_info.get('moneda', 'MXN')}"

        # Enlace al proyecto creado automáticamente (si existe)
        proyecto_id = oc_info.get('proyecto_id')
        if proyecto_id:
            enlace = f"/proyecto/{proyecto_id}"
            print(f"[NOTIF_OC] Enlace a proyecto: {enlace}")
        else:
            # Fallback a la OC si no hay proyecto
            enlace = f"/ordenes-compra/{oc_info.get('id')}"
            print(f"[NOTIF_OC] Sin proyecto_id, enlace a OC: {enlace}")

        metadata = {
            'oc_id': oc_info.get('id'),
            'proyecto_id': oc_info.get('proyecto_id'),
            'numero_oc': oc_info.get('numero_oc')
        }

        return self.crear_notificacion(
            usuario=responsable,
            tipo=self.TIPO_OC_NUEVA,
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
            metadata=metadata
        )

    def notificar_presupuesto_excedido(self, proyecto_info: Dict[str, Any],
                                      responsable: str) -> Dict[str, Any]:
        """
        Notificar que un proyecto está excediendo su presupuesto

        Args:
            proyecto_info: Información del proyecto
            responsable: Usuario responsable

        Returns:
            Resultado de crear_notificacion
        """
        titulo = "⚠️ Presupuesto excedido"
        mensaje = f"Proyecto: {proyecto_info.get('nombre', 'N/A')}\n"
        mensaje += f"Presupuesto: ${proyecto_info.get('monto_presupuestado', 0):,.2f}\n"
        mensaje += f"Gastado: ${proyecto_info.get('monto_gastado', 0):,.2f}"

        enlace = f"/proyecto/{proyecto_info.get('id')}"

        metadata = {
            'proyecto_id': proyecto_info.get('id'),
            'monto_presupuestado': float(proyecto_info.get('monto_presupuestado', 0)),
            'monto_gastado': float(proyecto_info.get('monto_gastado', 0))
        }

        return self.crear_notificacion(
            usuario=responsable,
            tipo=self.TIPO_PRESUPUESTO_EXCEDIDO,
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
            metadata=metadata
        )

    # ========================================
    # LEER Y GESTIONAR NOTIFICACIONES
    # ========================================

    def obtener_notificaciones_usuario(self, usuario: str,
                                       solo_no_leidas: bool = False,
                                       limite: int = 50) -> List[Dict[str, Any]]:
        """
        Obtener notificaciones de un usuario

        Args:
            usuario: Nombre del usuario
            solo_no_leidas: Si True, solo devuelve notificaciones no leídas
            limite: Máximo de notificaciones a devolver

        Returns:
            Lista de notificaciones ordenadas por fecha (más recientes primero)
        """
        try:
            cursor = self._get_cursor()

            query = """
                SELECT *
                FROM notificaciones
                WHERE usuario_destinatario = %s
            """

            params = [usuario]

            if solo_no_leidas:
                query += " AND leida = FALSE"

            query += f" ORDER BY created_at DESC LIMIT {limite}"

            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in resultados]

        except Exception as e:
            print(f"[NOTIFICACIONES] Error obteniendo notificaciones para {usuario}: {e}")
            return []

    def contar_no_leidas(self, usuario: str) -> int:
        """
        Contar notificaciones no leídas de un usuario

        Args:
            usuario: Nombre del usuario

        Returns:
            Número de notificaciones no leídas
        """
        try:
            cursor = self._get_cursor()

            cursor.execute("""
                SELECT COUNT(*) as total
                FROM notificaciones
                WHERE usuario_destinatario = %s AND leida = FALSE
            """, (usuario,))

            resultado = cursor.fetchone()
            cursor.close()

            return resultado['total'] if resultado else 0

        except Exception as e:
            print(f"[NOTIFICACIONES] Error contando notificaciones: {e}")
            return 0

    def marcar_como_leida(self, notificacion_id: int) -> Dict[str, Any]:
        """
        Marcar notificación como leída

        Args:
            notificacion_id: ID de la notificación

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            cursor.execute("""
                UPDATE notificaciones
                SET leida = TRUE
                WHERE id = %s AND leida = FALSE
            """, (notificacion_id,))

            self.pg_connection.commit()
            cursor.close()

            return {'success': True, 'message': 'Notificación marcada como leída'}

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[NOTIFICACIONES] Error marcando como leída: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def marcar_todas_como_leidas(self, usuario: str) -> Dict[str, Any]:
        """
        Marcar todas las notificaciones de un usuario como leídas

        Args:
            usuario: Nombre del usuario

        Returns:
            {'success': bool, 'total_marcadas': int, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            cursor.execute("""
                UPDATE notificaciones
                SET leida = TRUE
                WHERE usuario_destinatario = %s AND leida = FALSE
            """, (usuario,))

            total_marcadas = cursor.rowcount
            self.pg_connection.commit()
            cursor.close()

            print(f"[NOTIFICACIONES] {total_marcadas} notificaciones marcadas como leídas para {usuario}")

            return {
                'success': True,
                'total_marcadas': total_marcadas,
                'message': f'{total_marcadas} notificaciones marcadas como leídas'
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[NOTIFICACIONES] Error marcando todas como leídas: {e}")
            return {'success': False, 'total_marcadas': 0, 'message': f'Error: {str(e)}'}

    def eliminar_notificacion(self, notificacion_id: int) -> Dict[str, Any]:
        """
        Eliminar una notificación

        Args:
            notificacion_id: ID de la notificación

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            cursor.execute("DELETE FROM notificaciones WHERE id = %s", (notificacion_id,))
            self.pg_connection.commit()
            cursor.close()

            return {'success': True, 'message': 'Notificación eliminada'}

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[NOTIFICACIONES] Error eliminando notificación: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    # ========================================
    # LIMPIEZA Y MANTENIMIENTO
    # ========================================

    def limpiar_notificaciones_antiguas(self, dias: int = 30) -> Dict[str, Any]:
        """
        Eliminar notificaciones leídas más antiguas que X días

        Args:
            dias: Número de días (default: 30)

        Returns:
            {'success': bool, 'total_eliminadas': int, 'message': str}
        """
        try:
            cursor = self._get_cursor()

            fecha_limite = datetime.now() - timedelta(days=dias)

            cursor.execute("""
                DELETE FROM notificaciones
                WHERE leida = TRUE AND created_at < %s
            """, (fecha_limite,))

            total_eliminadas = cursor.rowcount
            self.pg_connection.commit()
            cursor.close()

            print(f"[NOTIFICACIONES] {total_eliminadas} notificaciones antiguas eliminadas")

            return {
                'success': True,
                'total_eliminadas': total_eliminadas,
                'message': f'{total_eliminadas} notificaciones antiguas eliminadas'
            }

        except Exception as e:
            if self.pg_connection:
                self.pg_connection.rollback()
            print(f"[NOTIFICACIONES] Error limpiando notificaciones antiguas: {e}")
            return {'success': False, 'total_eliminadas': 0, 'message': f'Error: {str(e)}'}

    def __del__(self):
        """Cerrar conexiones al destruir objeto"""
        if self.pg_connection and not self.pg_connection.closed:
            self.pg_connection.close()
            print("[NOTIFICACIONES_MANAGER] Conexión cerrada")
