#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUPABASE MANAGER - REEMPLAZO DE DATABASE MANAGER
===============================================

Administrador de base de datos usando Supabase PostgreSQL en lugar de MongoDB.
Mantiene la misma API que DatabaseManager para compatibilidad con el código existente.

Características:
- Conectividad robusta a PostgreSQL/Supabase
- Fallback automático a JSON offline si falla la conexión
- APIs idénticas a DatabaseManager
- Almacenamiento de PDFs como BLOB en base de datos
- Búsquedas optimizadas con índices PostgreSQL
"""

import json
import os
import sys
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def safe_str(value, default=""):
    """Convierte valor a string de forma segura y simple"""
    if value is None:
        return default
    return str(value).strip()

class SupabaseManager:
    """
    Administrador de Supabase PostgreSQL que reemplaza DatabaseManager de MongoDB
    """
    
    def __init__(self):
        # Configuración Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY') 
        self.database_url = os.getenv('DATABASE_URL')
        
        # Cliente Supabase (para APIs automáticas)
        self.supabase_client: Optional[Client] = None
        
        # Conexión PostgreSQL directa (para operaciones complejas)
        self.pg_connection = None
        
        # Control de estado
        self.modo_offline = True
        self.postgresql_disponible = False  # Control específico de PostgreSQL
        self.ultima_conexion = None
        self.estado_anterior = None  # Para detectar cambios de estado
        self.callbacks_cambio_estado = []  # Callbacks para cambios online/offline
        
        # Archivo JSON para fallback offline
        self.archivo_offline = os.path.join(os.getcwd(), "cotizaciones_offline.json")
        
        # Inicializar conexión
        self._inicializar_conexion()
    
    def _inicializar_conexion(self):
        """Inicializar conexión a Supabase"""
        print("[SUPABASE] Inicializando conexion...")
        
        # Debug de variables de entorno
        service_key = os.getenv('SUPABASE_SERVICE_KEY')
        print(f"[SUPABASE] Variables disponibles:")
        print(f"   SUPABASE_URL: {'Configurada' if self.supabase_url else 'Faltante'}")
        print(f"   SUPABASE_ANON_KEY: {'Configurada' if self.supabase_key else 'Faltante'}")
        print(f"   SUPABASE_SERVICE_KEY: {'Configurada' if service_key else '⚠️  FALTANTE - Requerida para escritura'}")
        print(f"   DATABASE_URL: {'Configurada' if self.database_url else 'Faltante'}")
        
        # Validar configuración
        if not self.supabase_url or not self.database_url:
            print("[SUPABASE] Variables de entorno faltantes - modo offline")
            print("   Necesitas: SUPABASE_URL, DATABASE_URL")
            self.modo_offline = True
            return
        
        # Advertir sobre SERVICE_KEY faltante (crítico para escritura en producción)
        if not service_key:
            print("[SUPABASE] ⚠️  ADVERTENCIA: SUPABASE_SERVICE_KEY no configurada")
            print("[SUPABASE] ⚠️  Esto puede causar fallos de escritura en producción")
            print("[SUPABASE] ⚠️  ANON_KEY tiene permisos limitados por RLS")
        
        try:
            # Cliente Supabase (APIs automáticas)
            if self.supabase_key:
                try:
                    # Crear cliente Supabase
                    self.supabase_client = create_client(self.supabase_url, self.supabase_key)
                    print("[SUPABASE] Cliente Supabase inicializado")
                except Exception as supabase_error:
                    print(f"[SUPABASE] Warning - Cliente Supabase falló: {supabase_error}")
                    self.supabase_client = None
            
            # Conexión PostgreSQL directa
            print(f"[SUPABASE] Intentando conexión PostgreSQL...")
            print(f"[SUPABASE] DATABASE_URL (primeros 50 chars): {self.database_url[:50]}...")
            
            self.pg_connection = psycopg2.connect(
                self.database_url,
                cursor_factory=RealDictCursor,
                connect_timeout=10,
                application_name="CWS_Cotizador"
            )
            
            print(f"[SUPABASE] Conexión PostgreSQL establecida")
            
            # Test de conexión
            cursor = self.pg_connection.cursor()
            cursor.execute("SELECT 1 as test;")
            result = cursor.fetchone()
            cursor.close()
            
            if result['test'] == 1:
                # Detectar cambio de estado (offline → online)
                estado_cambio = self.modo_offline and (self.estado_anterior != "online")
                
                self.postgresql_disponible = True
                self.modo_offline = False
                self.ultima_conexion = datetime.now()
                print("[SUPABASE] Conectado a PostgreSQL exitosamente")
                print(f"[SUPABASE] URL: {self.supabase_url}")
                
                # Notificar cambio de estado si es necesario
                if estado_cambio:
                    print("[ESTADO_CAMBIO] Supabase RECUPERADO - offline -> online")
                    self._notificar_cambio_estado("offline", "online")
                
                self.estado_anterior = "online"
                
                # Test adicional: verificar si existen las tablas
                try:
                    cursor = self.pg_connection.cursor()
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                    tablas = cursor.fetchall()
                    cursor.close()
                    print(f"[SUPABASE] Tablas disponibles: {[t['table_name'] for t in tablas]}")
                except Exception as table_error:
                    print(f"[SUPABASE] Error verificando tablas: {table_error}")
                    
            else:
                raise Exception("Test de conexión falló")
                
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SUPABASE] Error conectando: {error_msg}")
            print("[SUPABASE] Activando modo offline")
            
            # IMPORTANTE: PostgreSQL puede fallar, pero SDK REST aún puede funcionar
            # NO activar modo offline permanente solo por fallo PostgreSQL
            print("[SUPABASE] PostgreSQL falló, pero SDK REST puede seguir funcionando")
            print("[SUPABASE] Manteniendo disponibilidad de SDK REST para operaciones")
            
            # Solo marcar PostgreSQL como no disponible, no todo el sistema offline
            self.postgresql_disponible = False
            
            # Notificar cambio de estado si es necesario
            if estado_cambio:
                print("[ESTADO_CAMBIO] Supabase PERDIDO - online -> offline")
                self._notificar_cambio_estado("online", "offline")
            
            self.estado_anterior = "offline"
            
            if self.pg_connection:
                try:
                    self.pg_connection.close()
                except:
                    pass
                self.pg_connection = None
    
    def _reconectar_si_es_necesario(self) -> bool:
        """Intentar reconectar si estamos offline"""
        if not self.modo_offline:
            return True
        
        print("[SUPABASE] Intentando reconexion...")
        self._inicializar_conexion()
        return not self.modo_offline
    
    def _ejecutar_con_reintentos(self, operacion, max_reintentos=3, descripcion="operación"):
        """
        Ejecutar operación de base de datos con reintentos automáticos para errores SSL
        
        Args:
            operacion: Función que ejecuta la operación
            max_reintentos: Número máximo de reintentos
            descripcion: Descripción de la operación para logs
            
        Returns:
            Resultado de la operación o None si fallan todos los reintentos
        """
        ultimo_error = None
        
        for intento in range(max_reintentos + 1):
            try:
                # Verificar conexión antes de cada intento
                if not self._verificar_conexion_activa():
                    if intento < max_reintentos:
                        print(f"[REINTENTOS] Intento {intento + 1}/{max_reintentos + 1}: Reconectando para {descripcion}")
                        continue
                    else:
                        print(f"[REINTENTOS] {descripcion} FALLO: Sin conexión después de {max_reintentos} reintentos")
                        self.modo_offline = True
                        return None
                
                # Ejecutar operación
                print(f"[REINTENTOS] Ejecutando {descripcion} (intento {intento + 1})")
                resultado = operacion()
                
                if intento > 0:
                    print(f"[REINTENTOS] {descripcion} ÉXITO en intento {intento + 1}")
                    
                return resultado
                
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                error_msg = str(e).lower()
                ultimo_error = e
                
                if 'ssl connection has been closed' in error_msg or 'connection closed' in error_msg:
                    print(f"[REINTENTOS] Intento {intento + 1}: Error SSL - {str(e)}")
                    
                    # Cerrar conexión problemática
                    if self.pg_connection:
                        try:
                            self.pg_connection.close()
                        except:
                            pass
                        self.pg_connection = None
                    
                    if intento < max_reintentos:
                        import time
                        tiempo_espera = (intento + 1) * 2  # Backoff exponencial: 2s, 4s, 6s
                        print(f"[REINTENTOS] Esperando {tiempo_espera}s antes del siguiente intento...")
                        time.sleep(tiempo_espera)
                        
                        # Intentar reconectar
                        try:
                            self._inicializar_conexion()
                        except Exception as reconect_error:
                            print(f"[REINTENTOS] Error reconectando: {reconect_error}")
                            continue
                    else:
                        print(f"[REINTENTOS] {descripcion} FALLO DEFINITIVO: {str(e)}")
                        self.modo_offline = True
                        break
                else:
                    # Error que no es SSL - no reintentar
                    print(f"[REINTENTOS] {descripcion} error no-SSL: {str(e)}")
                    raise e
                    
            except Exception as e:
                # Otros errores - no reintentar
                print(f"[REINTENTOS] {descripcion} error inesperado: {str(e)}")
                raise e
        
        print(f"[REINTENTOS] {descripcion} FALLO FINAL después de {max_reintentos + 1} intentos")
        if ultimo_error:
            raise ultimo_error
        return None
    
    def _verificar_conexion_activa(self) -> bool:
        """
        Verificar si la conexión PostgreSQL sigue activa y reconectar si es necesario
        Returns: True si la conexión está activa, False si no se pudo establecer
        """
        if self.modo_offline or not self.pg_connection:
            return self._reconectar_si_es_necesario()
        
        try:
            # Test ping simple para verificar conexión
            cursor = self.pg_connection.cursor()
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            cursor.close()
            
            if not result or result[0] != 1:
                raise Exception("Test ping falló")
            
            return True
            
        except (psycopg2.OperationalError, psycopg2.InterfaceError, Exception) as e:
            print(f"[SUPABASE] Conexión perdida: {safe_str(e)}")
            print("[SUPABASE] Intentando reconexión automática...")
            
            # Cerrar conexión problemática
            if self.pg_connection:
                try:
                    self.pg_connection.close()
                except:
                    pass
                self.pg_connection = None
            
            # Marcar como offline y intentar reconectar
            self.modo_offline = True
            return self._reconectar_si_es_necesario()
    
    def registrar_callback_cambio_estado(self, callback):
        """
        Registrar callback para cambios de estado online/offline
        
        Args:
            callback: Función que recibe (estado_anterior, estado_nuevo)
        """
        if callback not in self.callbacks_cambio_estado:
            self.callbacks_cambio_estado.append(callback)
            print(f"[CALLBACKS] Callback registrado: {callback.__name__ if hasattr(callback, '__name__') else 'función'}")
    
    def _notificar_cambio_estado(self, estado_anterior: str, estado_nuevo: str):
        """Notificar a todos los callbacks sobre cambio de estado"""
        print(f"[CALLBACKS] Notificando cambio: {estado_anterior} -> {estado_nuevo}")
        
        for callback in self.callbacks_cambio_estado:
            try:
                callback(estado_anterior, estado_nuevo)
            except Exception as e:
                print(f"[CALLBACKS] Error ejecutando callback: {e}")
    
    def health_check(self) -> dict:
        """
        Verificar el estado actual de Supabase y detectar cambios
        
        Returns:
            dict: Estado actual con información detallada
        """
        estado_anterior_temp = self.estado_anterior
        
        # Intentar reconectar si estamos offline
        if self.modo_offline:
            self._reconectar_si_es_necesario()
        else:
            # Si estamos online, verificar que la conexión siga activa
            try:
                cursor = self.pg_connection.cursor()
                cursor.execute("SELECT 1;")
                cursor.fetchone()
                cursor.close()
            except:
                print("[HEALTH_CHECK] Conexión perdida, reactivando modo offline")
                estado_cambio = not self.modo_offline
                self.modo_offline = True
                if estado_cambio:
                    self._notificar_cambio_estado("online", "offline")
                self.estado_anterior = "offline"
        
        return {
            "online": not self.modo_offline,
            "estado_actual": "online" if not self.modo_offline else "offline",
            "estado_anterior": estado_anterior_temp,
            "cambio_detectado": estado_anterior_temp != self.estado_anterior,
            "ultima_conexion": self.ultima_conexion.isoformat() if self.ultima_conexion else None,
            "url": self.supabase_url
        }
    
    def _cargar_datos_offline(self) -> Dict:
        """Cargar datos desde archivo JSON offline"""
        try:
            if os.path.exists(self.archivo_offline):
                with open(self.archivo_offline, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data
            else:
                return {"cotizaciones": []}
        except Exception as e:
            print(f"[OFFLINE] Error cargando JSON: {safe_str(e)}")
            return {"cotizaciones": []}
    
    def _guardar_datos_offline(self, data: Dict) -> bool:
        """Guardar datos en archivo JSON offline"""
        try:
            with open(self.archivo_offline, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[OFFLINE] Error guardando JSON: {safe_str(e)}")
            return False
    
    def obtener_estadisticas(self) -> Dict:
        """Obtener estadísticas de la base de datos - SISTEMA HÍBRIDO"""
        # SISTEMA HÍBRIDO TRIPLE LAYER:
        # 1. Intentar PostgreSQL directo (más rápido)
        if not self.modo_offline:
            def _operacion_estadisticas():
                """Operación de estadísticas que será ejecutada con reintentos"""
                cursor = self.pg_connection.cursor()
                
                try:
                    # Contar cotizaciones
                    cursor.execute("SELECT COUNT(*) as total FROM cotizaciones;")
                    total = cursor.fetchone()['total']
                    
                    # Contar PDFs
                    cursor.execute("SELECT COUNT(*) as total FROM pdf_storage WHERE pdf_data IS NOT NULL;")
                    pdfs = cursor.fetchone()['total']
                    
                    cursor.close()
                    
                    return {
                        "total_cotizaciones": total,
                        "total_pdfs": pdfs,
                        "modo": "online",
                        "fuente": "Supabase PostgreSQL",
                        "url": self.supabase_url
                    }
                except Exception as e:
                    cursor.close()
                    raise e
            
            # Ejecutar con reintentos automáticos
            resultado = self._ejecutar_con_reintentos(
                _operacion_estadisticas,
                max_reintentos=3,
                descripcion="obtener estadísticas"
            )
            
            if resultado is None:
                # PostgreSQL falló - intentar SDK REST
                print("[ESTADISTICAS] PostgreSQL falló, intentando SDK REST...")
                
                # 2. Fallback a SDK REST (estable)
                if self.supabase_client:
                    try:
                        return self._obtener_estadisticas_sdk()
                    except Exception as sdk_error:
                        print(f"[SDK_REST] Error obteniendo estadísticas: {safe_str(sdk_error)}")
                        print("[SDK_REST] Fallback a modo offline")
                
                # 3. Último recurso: JSON offline
                data = self._cargar_datos_offline()
                cotizaciones = data.get("cotizaciones", [])
                
                return {
                    "total_cotizaciones": len(cotizaciones),
                    "modo": "offline_fallback",
                    "fuente": "JSON local (después de fallos PostgreSQL + SDK)",
                    "archivo": self.archivo_offline
                }
            
            return resultado
        
        # Si modo_offline está activado, intentar SDK antes de JSON
        if self.supabase_client:
            try:
                return self._obtener_estadisticas_sdk()
            except Exception as sdk_error:
                print(f"[SDK_REST] Error obteniendo estadísticas offline: {safe_str(sdk_error)}")
        
        # Último recurso: JSON offline
        data = self._cargar_datos_offline()
        cotizaciones = data.get("cotizaciones", [])
        
        return {
            "total_cotizaciones": len(cotizaciones),
            "modo": "offline",
            "fuente": "JSON local",
            "archivo": self.archivo_offline
        }
    
    def _obtener_estadisticas_sdk(self) -> Dict:
        """Obtener estadísticas usando Supabase SDK REST"""
        try:
            if not self.supabase_client:
                raise Exception("SDK de Supabase no disponible")
            
            # Contar cotizaciones
            response = self.supabase_client.table('cotizaciones').select('*', count='exact').execute()
            total_cotizaciones = response.count
            
            print(f"[SDK_REST] Estadísticas obtenidas: {total_cotizaciones} cotizaciones")
            
            return {
                "total_cotizaciones": total_cotizaciones,
                "modo": "sdk_rest",
                "fuente": "Supabase SDK REST",
                "url": self.supabase_url
            }
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SDK_REST] Error obteniendo estadísticas: {error_msg}")
            raise e
    
    def guardar_cotizacion(self, datos: Dict) -> Dict:
        """
        Guardar cotización en Supabase (online) o JSON (offline)
        Mantiene API compatible con DatabaseManager
        """
        try:
            # FIX ISSUE #1: SIEMPRE priorizar número en datosGenerales.numeroCotizacion
            numero_cotizacion = None
            
            print(f"[DEBUG_ISSUE1] === INICIO DEBUG GUARDAR_COTIZACION ===")
            print(f"[DEBUG_ISSUE1] datos['numeroCotizacion']: '{datos.get('numeroCotizacion', 'VACIO')}'")
            print(f"[DEBUG_ISSUE1] datos['numeroCotizacionHidden']: '{datos.get('numeroCotizacionHidden', 'VACIO')}'")
            print(f"[DEBUG_ISSUE1] datosGenerales['numeroCotizacion']: '{datos.get('datosGenerales', {}).get('numeroCotizacion', 'VACIO')}'")
            
            # Verificar PRIMERO si hay número en datosGenerales (caso de revisiones)
            if 'datosGenerales' in datos and 'numeroCotizacion' in datos['datosGenerales']:
                if datos['datosGenerales']['numeroCotizacion'] and datos['datosGenerales']['numeroCotizacion'].strip():
                    numero_cotizacion = datos['datosGenerales']['numeroCotizacion']
                    print(f"[REVISIÓN] Usando número de datosGenerales: {numero_cotizacion}")
                    datos['numeroCotizacion'] = numero_cotizacion
            
            # Si no hay en datosGenerales, verificar numeroCotizacionHidden (desde formulario)
            if not numero_cotizacion:
                numero_hidden = datos.get('numeroCotizacionHidden')
                if numero_hidden and numero_hidden.strip():
                    numero_cotizacion = numero_hidden
                    print(f"[REVISIÓN] Usando número de numeroCotizacionHidden: {numero_cotizacion}")
                    datos['numeroCotizacion'] = numero_cotizacion
            
            # Si no hay en Hidden, usar el del nivel raíz
            if not numero_cotizacion:
                numero_cotizacion = datos.get('numeroCotizacion')
            
            if not numero_cotizacion:
                # Extraer datos para análisis
                datos_generales = datos.get('datosGenerales', {})
                revision = datos_generales.get('revision', 1)
                
                # FIX ISSUE #1: NUNCA generar nuevo número secuencial para revisiones (R2+)
                if isinstance(revision, str):
                    try:
                        revision = int(revision)
                    except (ValueError, TypeError):
                        revision = 1
                
                if revision > 1:
                    # ES UNA REVISIÓN - ERROR CRÍTICO: no debería llegar aquí sin número
                    error_msg = f"[CRÍTICO] Revisión R{revision} sin número de cotización base. Esto NO debe ocurrir."
                    print(error_msg)
                    return {"success": False, "error": f"Issue #1 - Revisión sin número base: R{revision}"}
                else:
                    # Es una nueva cotización (R1) - generar número consecutivo
                    print("[GUARDAR] Nueva cotización (R1), generando número consecutivo...")
                    
                    # Extraer datos necesarios para generación consecutiva
                    cliente = datos_generales.get('cliente', 'CLIENTE')
                    vendedor = datos_generales.get('vendedor', 'VENDEDOR')  
                    proyecto = datos_generales.get('proyecto', 'PROYECTO')
                    
                    print(f"[GUARDAR] Generando consecutivo para: Cliente='{cliente}', Vendedor='{vendedor}', Proyecto='{proyecto}', Rev={revision}")
                    
                    # Usar el método consecutivo irrepetible solo para NUEVAS cotizaciones
                    numero_cotizacion = self.generar_numero_cotizacion(cliente, vendedor, proyecto, revision)
                    datos['numeroCotizacion'] = numero_cotizacion
                    
                    # Actualizar también en datosGenerales para consistencia
                    datos['datosGenerales']['numeroCotizacion'] = numero_cotizacion
                    print(f"[GUARDAR] Número consecutivo generado: {numero_cotizacion}")
            
            print(f"[GUARDAR] Procesando cotización: {numero_cotizacion}")
            
            # SISTEMA HÍBRIDO TRIPLE LAYER (REORDENADO PARA ESTABILIDAD):
            # 1. PRIORIDAD: SDK REST de Supabase (funciona independiente de PostgreSQL)
            if self.supabase_client:
                print("[HIBRIDO] PRIORIDAD 1: Intentando SDK REST de Supabase...")
                resultado_sdk = self._guardar_cotizacion_sdk(datos)
                
                # Verificar si SDK REST realmente funcionó
                if resultado_sdk.get('success'):
                    print("[HIBRIDO] SDK REST exitoso - operación completada")
                    # También guardar en JSON como backup
                    self._guardar_cotizacion_offline(datos)
                    return resultado_sdk
                else:
                    print(f"[HIBRIDO] SDK REST falló: {resultado_sdk.get('error', 'unknown')}")
                    print(f"[HIBRIDO] SDK REST resultado completo: {json.dumps(resultado_sdk, default=str, indent=2)}")
                    print("[HIBRIDO] Intentando fallback a PostgreSQL directo...")
            
            # 2. FALLBACK: PostgreSQL directo (solo si está disponible)  
            if self.postgresql_disponible:
                try:
                    print("[HIBRIDO] FALLBACK: Intentando PostgreSQL directo...")
                    resultado_online = self._guardar_cotizacion_supabase(datos)
                    
                    # También guardar en JSON como backup
                    self._guardar_cotizacion_offline(datos)
                    
                    return resultado_online
                    
                except Exception as pg_error:
                    print(f"[POSTGRES] Error guardando: {safe_str(pg_error)}")
                    print("[POSTGRES] Activando modo offline...")
                    self.modo_offline = True
            
            # Guardar en JSON (modo offline o fallback)
            return self._guardar_cotizacion_offline(datos)
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[GUARDAR] Error general: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _guardar_cotizacion_sdk(self, datos: Dict) -> Dict:
        """Guardar cotización usando Supabase SDK REST (fallback estable)"""
        try:
            print(f"[SDK_REST] INICIO - Guardando cotización via SDK REST")
            print(f"[SDK_REST] Cliente disponible: {'Sí' if self.supabase_client else 'No'}")
            
            if not self.supabase_client:
                raise Exception("SDK de Supabase no disponible")
            
            numero_cotizacion = datos.get('numeroCotizacion')
            datos_generales = datos.get('datosGenerales', {})
            items = datos.get('items', [])
            revision = datos.get('revision', 1)
            version = datos.get('version', '1.0.0')
            usuario = datos.get('usuario')
            observaciones = datos.get('observaciones')
            
            print(f"[SDK_REST] Datos extraídos - Número: {numero_cotizacion}, Items: {len(items)}, Revisión: {revision}")
            
            # Timestamp y fecha
            timestamp = datos.get('timestamp', int(time.time() * 1000))
            fecha_creacion = datos.get('fechaCreacion')
            if isinstance(fecha_creacion, str):
                try:
                    datetime.fromisoformat(fecha_creacion.replace('Z', '+00:00'))
                except:
                    fecha_creacion = datetime.now().isoformat()
            else:
                fecha_creacion = datetime.now().isoformat()
            
            print(f"[SDK_REST] Fecha procesada: {fecha_creacion}")
            
            # Preparar datos para SDK
            sdk_data = {
                'numero_cotizacion': numero_cotizacion,
                'datos_generales': datos_generales,
                'items': items,
                'revision': revision,
                'version': version,
                'fecha_creacion': fecha_creacion,
                'timestamp': timestamp,
                'usuario': usuario,
                'observaciones': observaciones
            }
            
            print(f"[SDK_REST] Datos SDK preparados, verificando si cotización existe...")
            
            # Verificar si existe (para UPDATE vs INSERT)
            try:
                existing = self.supabase_client.table('cotizaciones').select('id').eq('numero_cotizacion', numero_cotizacion).execute()
                print(f"[SDK_REST] Verificación existencia: {'Encontrada' if existing.data else 'Nueva'}")
            except Exception as check_error:
                print(f"[SDK_REST] Error verificando existencia: {safe_str(check_error)}")
                raise Exception(f"Error verificando cotización existente: {safe_str(check_error)}")
            
            if existing.data:
                # UPDATE existente
                cotizacion_id = existing.data[0]['id']
                print(f"[SDK_REST] Ejecutando UPDATE para ID {cotizacion_id}...")
                try:
                    response = self.supabase_client.table('cotizaciones').update(sdk_data).eq('id', cotizacion_id).execute()
                    print(f"[SDK_REST] UPDATE exitoso - Cotización actualizada: {numero_cotizacion}")
                except Exception as update_error:
                    print(f"[SDK_REST] Error en UPDATE: {safe_str(update_error)}")
                    raise Exception(f"Error actualizando cotización: {safe_str(update_error)}")
            else:
                # INSERT nueva
                print(f"[SDK_REST] Ejecutando INSERT nueva cotización...")
                try:
                    response = self.supabase_client.table('cotizaciones').insert(sdk_data).execute()
                    cotizacion_id = response.data[0]['id'] if response.data else None
                    print(f"[SDK_REST] INSERT exitoso - ID asignado: {cotizacion_id}")
                except Exception as insert_error:
                    print(f"[SDK_REST] Error en INSERT: {safe_str(insert_error)}")
                    print(f"[SDK_REST] Datos que causaron error: {json.dumps(sdk_data, default=str, indent=2)}")
                    raise Exception(f"Error insertando cotización: {safe_str(insert_error)}")
            
            # Verificar que el guardado fue exitoso
            print(f"[SDK_REST] Verificando guardado exitoso...")
            try:
                verify_response = self.supabase_client.table('cotizaciones').select('id').eq('numero_cotizacion', numero_cotizacion).execute()
                if verify_response.data:
                    print(f"[SDK_REST] VERIFICACIÓN OK - Cotización confirmada en Supabase")
                else:
                    print(f"[SDK_REST] VERIFICACIÓN FALLÓ - Cotización no encontrada después del guardado")
                    raise Exception("Cotización no encontrada después del guardado - operación falló")
            except Exception as verify_error:
                print(f"[SDK_REST] Error en verificación: {safe_str(verify_error)}")
                raise Exception(f"Error verificando guardado: {safe_str(verify_error)}")
            
            resultado = {
                "success": True,
                "id": cotizacion_id,
                "numero_cotizacion": numero_cotizacion,
                "modo": "sdk_rest",
                "mensaje": "Guardado via Supabase SDK REST"
            }
            
            print(f"[SDK_REST] ÉXITO - Operación completada: {numero_cotizacion}")
            return resultado
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SDK_REST] ERROR CRÍTICO guardando: {error_msg}")
            print(f"[SDK_REST] Tipo de error: {type(e).__name__}")
            # NO hacer raise aquí - permitir que el sistema use el siguiente fallback
            return {
                "success": False,
                "error": error_msg,
                "modo": "sdk_rest_failed",
                "numero_cotizacion": datos.get('numeroCotizacion', 'unknown')
            }

    def _guardar_cotizacion_supabase(self, datos: Dict) -> Dict:
        """Guardar cotización en Supabase PostgreSQL con reintentos automáticos"""
        
        # Extraer datos fuera del método de reintentos
        numero_cotizacion = datos.get('numeroCotizacion')
        datos_generales = datos.get('datosGenerales', {})
        items = datos.get('items', [])
        condiciones = datos.get('condiciones', {})
        revision = datos.get('revision', 1)
        version = datos.get('version', '1.0.0')
        usuario = datos.get('usuario')
        observaciones = datos.get('observaciones')
        
        # Generar timestamp si no existe
        timestamp = datos.get('timestamp', int(time.time() * 1000))
        fecha_creacion = datos.get('fechaCreacion')
        
        # Convertir fecha_creacion si es string
        fecha_dt = datetime.now()
        if fecha_creacion:
            if isinstance(fecha_creacion, str):
                try:
                    fecha_dt = datetime.fromisoformat(fecha_creacion.replace('Z', '+00:00'))
                except:
                    fecha_dt = datetime.now()
        
        # NOTA: Condiciones se guardan dentro de datos_generales temporalmente
        if condiciones:
            datos_generales['condiciones'] = condiciones
        
        def _operacion_guardar():
            """Operación de guardado que será ejecutada con reintentos"""
            cursor = self.pg_connection.cursor()
            
            try:
                # Query de inserción/actualización
                query = """
                    INSERT INTO cotizaciones (
                        numero_cotizacion, datos_generales, items, revision, 
                        version, fecha_creacion, timestamp, usuario, observaciones
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (numero_cotizacion) DO UPDATE SET
                        datos_generales = EXCLUDED.datos_generales,
                        items = EXCLUDED.items,
                        revision = EXCLUDED.revision,
                        version = EXCLUDED.version,
                        usuario = EXCLUDED.usuario,
                        observaciones = EXCLUDED.observaciones,
                        updated_at = NOW()
                    RETURNING id, numero_cotizacion;
                """
                
                cursor.execute(query, (
                    numero_cotizacion,
                    Json(datos_generales),  # JSONB (ahora incluye condiciones)
                    Json(items),  # JSONB
                    revision,
                    version,
                    fecha_dt,
                    timestamp,
                    usuario,
                    observaciones
                ))
                
                resultado = cursor.fetchone()
                cotizacion_id = resultado['id']
                
                # Commit
                self.pg_connection.commit()
                cursor.close()
                
                print(f"[SUPABASE] Cotizacion guardada: ID={cotizacion_id}")
                
                return {
                    "success": True,
                    "id": cotizacion_id,
                    "numero_cotizacion": numero_cotizacion,
                    "modo": "online",
                    "mensaje": "Guardado en Supabase PostgreSQL con reintentos"
                }
                
            except Exception as e:
                # Rollback en caso de error
                try:
                    self.pg_connection.rollback()
                except:
                    pass
                cursor.close()
                raise e
        
        # Ejecutar con reintentos automáticos
        resultado = self._ejecutar_con_reintentos(
            _operacion_guardar,
            max_reintentos=3,
            descripcion=f"guardar cotización {numero_cotizacion}"
        )
        
        if resultado is None:
            # Los reintentos fallaron - el sistema ya está en modo offline
            raise Exception("Falló después de reintentos automáticos - modo offline activado")
        
        return resultado
    
    def _guardar_cotizacion_offline(self, datos: Dict) -> Dict:
        """Guardar cotización en JSON (modo offline)"""
        try:
            # Cargar datos existentes
            data = self._cargar_datos_offline()
            cotizaciones = data.get("cotizaciones", [])
            
            numero_cotizacion = datos.get('numeroCotizacion')
            
            # Buscar si ya existe (para actualizar)
            indice_existente = None
            for i, cot in enumerate(cotizaciones):
                if cot.get('numeroCotizacion') == numero_cotizacion:
                    indice_existente = i
                    break
            
            # Agregar timestamp si no existe
            if 'timestamp' not in datos:
                datos['timestamp'] = int(time.time() * 1000)
            
            if 'fechaCreacion' not in datos:
                datos['fechaCreacion'] = datetime.now().isoformat()
            
            # Actualizar o agregar
            if indice_existente is not None:
                cotizaciones[indice_existente] = datos
                print(f"[OFFLINE] Cotizacion actualizada: {numero_cotizacion}")
            else:
                cotizaciones.append(datos)
                print(f"[OFFLINE] Nueva cotizacion: {numero_cotizacion}")
            
            # Guardar archivo
            data["cotizaciones"] = cotizaciones
            if self._guardar_datos_offline(data):
                return {
                    "success": True,
                    "numero_cotizacion": numero_cotizacion,
                    "modo": "offline",
                    "total_cotizaciones": len(cotizaciones),
                    "mensaje": "Guardado en JSON local"
                }
            else:
                return {"success": False, "error": "Error guardando archivo JSON"}
                
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[OFFLINE] Error guardando: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def buscar_cotizaciones(self, query: str, page: int = 1, per_page: int = 20) -> Dict:
        """
        Buscar cotizaciones con paginación
        API compatible con DatabaseManager
        """
        try:
            # SISTEMA HÍBRIDO TRIPLE LAYER:
            # 1. Intentar PostgreSQL directo (más rápido)
            if not self.modo_offline:
                try:
                    return self._buscar_cotizaciones_supabase(query, page, per_page)
                except Exception as pg_error:
                    print(f"[POSTGRES] Error en búsqueda: {safe_str(pg_error)}")
                    print("[POSTGRES] Intentando fallback a SDK REST...")
            
            # 2. Fallback a SDK REST (estable)
            if self.supabase_client:
                try:
                    return self._buscar_cotizaciones_sdk(query, page, per_page)
                except Exception as sdk_error:
                    print(f"[SDK_REST] Error en búsqueda: {safe_str(sdk_error)}")
                    print("[SDK_REST] Fallback a modo offline")
            
            # 3. Último recurso: JSON offline
            return self._buscar_cotizaciones_offline(query, page, per_page)
                    
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[BUSCAR] Error general: {error_msg}")
            return {"error": error_msg}
    
    def _buscar_cotizaciones_sdk(self, query: str, page: int, per_page: int) -> Dict:
        """Buscar cotizaciones usando Supabase SDK REST"""
        try:
            if not self.supabase_client:
                raise Exception("SDK de Supabase no disponible")
            
            # Construir query base
            base_query = self.supabase_client.table('cotizaciones').select('*')
            
            # Aplicar filtros si hay query
            if query and query.strip():
                # SDK REST usa filtros separados, no ILIKE múltiple como PostgreSQL
                # Buscar por los campos más comunes primero
                filtered_query = base_query.or_(f'numero_cotizacion.ilike.%{query}%,datos_generales->>cliente.ilike.%{query}%,datos_generales->>vendedor.ilike.%{query}%,datos_generales->>proyecto.ilike.%{query}%')
            else:
                filtered_query = base_query
            
            # Aplicar ordenamiento y paginación
            start = (page - 1) * per_page
            end = start + per_page - 1
            
            ordered_query = filtered_query.order('fecha_creacion', desc=True).range(start, end)
            
            # Ejecutar query
            response = ordered_query.execute()
            resultados_raw = response.data
            
            # Obtener total count (requiere query separada)
            if query and query.strip():
                count_query = self.supabase_client.table('cotizaciones').select('*', count='exact').or_(f'numero_cotizacion.ilike.%{query}%,datos_generales->>cliente.ilike.%{query}%,datos_generales->>vendedor.ilike.%{query}%,datos_generales->>proyecto.ilike.%{query}%')
            else:
                count_query = self.supabase_client.table('cotizaciones').select('*', count='exact')
            
            count_response = count_query.execute()
            total = count_response.count
            
            # Convertir a formato compatible con PostgreSQL response
            cotizaciones = []
            for row in resultados_raw:
                cotizacion = {
                    "_id": str(row['id']),
                    "numeroCotizacion": row['numero_cotizacion'],
                    "datosGenerales": row['datos_generales'],
                    "items": row['items'],
                    "revision": row['revision'],
                    "fechaCreacion": row['fecha_creacion'],
                    "timestamp": row['timestamp'],
                    "usuario": row['usuario'],
                    "observaciones": row['observaciones']
                }
                cotizaciones.append(cotizacion)
            
            total_pages = (total + per_page - 1) // per_page
            
            print(f"[SDK_REST] Encontradas {len(cotizaciones)} de {total} cotizaciones")
            
            return {
                "resultados": cotizaciones,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": total_pages,
                "modo": "sdk_rest"
            }
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SDK_REST] Error en búsqueda: {error_msg}")
            raise e

    def _buscar_cotizaciones_supabase(self, query: str, page: int, per_page: int) -> Dict:
        """Buscar cotizaciones en Supabase PostgreSQL"""
        try:
            cursor = self.pg_connection.cursor()
            
            # Construir query de búsqueda
            if not query:
                # Sin filtro - obtener todas
                count_query = "SELECT COUNT(*) as total FROM cotizaciones;"
                search_query = """
                    SELECT id, numero_cotizacion, datos_generales, items, 
                           revision, fecha_creacion, timestamp, usuario, observaciones
                    FROM cotizaciones 
                    ORDER BY fecha_creacion DESC 
                    LIMIT %s OFFSET %s;
                """
                count_params = ()
                search_params = (per_page, (page - 1) * per_page)
            else:
                # Con filtro - buscar en múltiples campos
                search_conditions = """
                    numero_cotizacion ILIKE %s OR
                    datos_generales->>'cliente' ILIKE %s OR
                    datos_generales->>'vendedor' ILIKE %s OR
                    datos_generales->>'proyecto' ILIKE %s OR
                    datos_generales->>'atencionA' ILIKE %s OR
                    datos_generales->>'contacto' ILIKE %s
                """
                
                query_pattern = f"%{query}%"
                
                count_query = f"""
                    SELECT COUNT(*) as total FROM cotizaciones 
                    WHERE {search_conditions};
                """
                
                search_query = f"""
                    SELECT id, numero_cotizacion, datos_generales, items, 
                           revision, fecha_creacion, timestamp, usuario, observaciones
                    FROM cotizaciones 
                    WHERE {search_conditions}
                    ORDER BY fecha_creacion DESC 
                    LIMIT %s OFFSET %s;
                """
                
                count_params = tuple([query_pattern] * 6)
                search_params = tuple([query_pattern] * 6) + (per_page, (page - 1) * per_page)
            
            # Ejecutar conteo
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['total']
            
            # Ejecutar búsqueda
            cursor.execute(search_query, search_params)
            resultados = cursor.fetchall()
            
            # Convertir a formato compatible
            cotizaciones = []
            for row in resultados:
                cotizacion = {
                    "_id": str(row['id']),
                    "numeroCotizacion": row['numero_cotizacion'],
                    "datosGenerales": row['datos_generales'],
                    "items": row['items'],
                    "revision": row['revision'],
                    "fechaCreacion": row['fecha_creacion'].isoformat() if row['fecha_creacion'] else None,
                    "timestamp": row['timestamp'],
                    "usuario": row['usuario'],
                    "observaciones": row['observaciones']
                }
                cotizaciones.append(cotizacion)
            
            cursor.close()
            
            total_pages = (total + per_page - 1) // per_page
            
            print(f"[SUPABASE] Encontradas {len(cotizaciones)} de {total} cotizaciones")
            
            return {
                "resultados": cotizaciones,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": total_pages,
                "modo": "online"
            }
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SUPABASE] Error en búsqueda: {error_msg}")
            raise e
    
    def _buscar_cotizaciones_offline(self, query: str, page: int, per_page: int) -> Dict:
        """Buscar cotizaciones en JSON offline"""
        try:
            print(f"[OFFLINE] Iniciando busqueda offline con query: '{query}'")
            data = self._cargar_datos_offline()
            cotizaciones = data.get("cotizaciones", [])
            print(f"[OFFLINE] Cargadas {len(cotizaciones)} cotizaciones del JSON")
            
            if len(cotizaciones) > 0:
                print(f"[OFFLINE] Primera cotizacion: {list(cotizaciones[0].keys())}")
                if 'datosGenerales' in cotizaciones[0]:
                    dg = cotizaciones[0]['datosGenerales']
                    print(f"[OFFLINE] datosGenerales: {list(dg.keys())}")
                    print(f"[OFFLINE] Cliente: '{dg.get('cliente', 'N/A')}'")
                    print(f"[OFFLINE] numeroCotizacion (root): '{cotizaciones[0].get('numeroCotizacion', 'N/A')}'")
                else:
                    print(f"[OFFLINE] No hay datosGenerales en primera cotizacion")
            
            if not query:
                resultados = cotizaciones
            else:
                # Filtrar por query
                resultados = []
                query_lower = query.lower()
                
                for cot in cotizaciones:
                    datos_generales = cot.get("datosGenerales", {})
                    
                    # Buscar en múltiples campos
                    if (query_lower in safe_str(cot.get("numeroCotizacion", "")).lower() or
                        query_lower in safe_str(datos_generales.get("cliente", "")).lower() or
                        query_lower in safe_str(datos_generales.get("vendedor", "")).lower() or
                        query_lower in safe_str(datos_generales.get("atencionA", "")).lower() or
                        query_lower in safe_str(datos_generales.get("proyecto", "")).lower() or
                        query_lower in safe_str(datos_generales.get("contacto", "")).lower()):
                        resultados.append(cot)
            
            # Ordenar por timestamp (más recientes primero)
            resultados.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            # Paginación
            total = len(resultados)
            start = (page - 1) * per_page
            end = start + per_page
            resultados_pagina = resultados[start:end]
            
            total_pages = (total + per_page - 1) // per_page
            
            print(f"[OFFLINE] Encontradas {len(resultados_pagina)} de {total} cotizaciones")
            
            return {
                "resultados": resultados_pagina,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": total_pages,
                "modo": "offline"
            }
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[OFFLINE] Error en búsqueda: {error_msg}")
            return {"error": error_msg}
    
    def obtener_cotizacion(self, numero_cotizacion: str) -> Dict:
        """
        Obtener cotización específica por número
        API compatible con DatabaseManager
        """
        try:
            # SISTEMA HÍBRIDO TRIPLE LAYER (REORDENADO PARA ESTABILIDAD):
            # 1. PRIORIDAD: SDK REST de Supabase (funciona independiente de PostgreSQL) 
            if self.supabase_client:
                try:
                    print("[HIBRIDO_GET] PRIORIDAD 1: Intentando SDK REST para obtener cotización...")
                    return self._obtener_cotizacion_sdk(numero_cotizacion)
                except Exception as sdk_error:
                    print(f"[SDK_REST] Error obteniendo cotización: {safe_str(sdk_error)}")
                    print("[SDK_REST] Intentando fallback a PostgreSQL directo...")
            
            # 2. FALLBACK: PostgreSQL directo (solo si está disponible)
            if self.postgresql_disponible:
                try:
                    print("[HIBRIDO_GET] FALLBACK: Intentando PostgreSQL directo...")
                    return self._obtener_cotizacion_supabase(numero_cotizacion)
                except Exception as pg_error:
                    print(f"[POSTGRES] Error obteniendo cotización: {safe_str(pg_error)}")
                    print("[POSTGRES] Activando modo offline para búsqueda...")
                    print("[SDK_REST] Fallback a modo offline")
            
            # 3. Último recurso: JSON offline
            return self._obtener_cotizacion_offline(numero_cotizacion)
        
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[OBTENER] Error general: {error_msg}")
            return {"error": error_msg, "encontrado": False}
    
    def _obtener_cotizacion_sdk(self, numero_cotizacion: str) -> Dict:
        """Obtener cotización específica usando Supabase SDK REST"""
        try:
            if not self.supabase_client:
                raise Exception("SDK de Supabase no disponible")
            
            response = self.supabase_client.table('cotizaciones').select('*').eq('numero_cotizacion', numero_cotizacion).execute()
            
            if not response.data:
                return {"encontrado": False, "error": "Cotización no encontrada"}
            
            row = response.data[0]
            
            # Extraer condiciones de datos_generales si existen (compatibilidad)
            datos_generales = row['datos_generales'] or {}
            condiciones = datos_generales.pop('condiciones', {}) if isinstance(datos_generales, dict) else {}
            
            cotizacion = {
                "_id": str(row['id']),
                "numeroCotizacion": row['numero_cotizacion'],
                "datosGenerales": datos_generales,
                "items": row['items'],
                "condiciones": condiciones,
                "revision": row['revision'],
                "fechaCreacion": row['fecha_creacion'],
                "timestamp": row['timestamp'],
                "usuario": row['usuario'],
                "observaciones": row['observaciones']
            }
            
            print(f"[SDK_REST] Cotización obtenida: {numero_cotizacion}")
            return {"encontrado": True, "item": cotizacion}
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SDK_REST] Error obteniendo cotización: {error_msg}")
            raise e

    def _obtener_cotizacion_supabase(self, numero_cotizacion: str) -> Dict:
        """Obtener cotización desde Supabase"""
        try:
            cursor = self.pg_connection.cursor()
            
            query = """
                SELECT id, numero_cotizacion, datos_generales, items,
                       revision, fecha_creacion, timestamp, usuario, observaciones
                FROM cotizaciones 
                WHERE numero_cotizacion = %s;
            """
            
            cursor.execute(query, (numero_cotizacion,))
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return {"encontrado": False, "error": "Cotización no encontrada"}
            
            # Extraer condiciones de datos_generales si existen
            datos_generales = row['datos_generales'] or {}
            condiciones = datos_generales.pop('condiciones', {}) if isinstance(datos_generales, dict) else {}
            
            cotizacion = {
                "_id": str(row['id']),
                "numeroCotizacion": row['numero_cotizacion'],
                "datosGenerales": datos_generales,
                "items": row['items'],
                "condiciones": condiciones,  # Extraídas de datos_generales
                "revision": row['revision'],
                "fechaCreacion": row['fecha_creacion'].isoformat() if row['fecha_creacion'] else None,
                "timestamp": row['timestamp'],
                "usuario": row['usuario'],
                "observaciones": row['observaciones']
            }
            
            return {"encontrado": True, "item": cotizacion}
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SUPABASE] Error obteniendo cotización: {error_msg}")
            raise e
    
    def _obtener_cotizacion_offline(self, numero_cotizacion: str) -> Dict:
        """Obtener cotización desde JSON offline"""
        try:
            data = self._cargar_datos_offline()
            cotizaciones = data.get("cotizaciones", [])
            
            for cot in cotizaciones:
                if cot.get('numeroCotizacion') == numero_cotizacion:
                    return {"encontrado": True, "item": cot}
            
            return {"encontrado": False, "error": "Cotización no encontrada"}
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[OFFLINE] Error obteniendo cotización: {error_msg}")
            return {"error": error_msg, "encontrado": False}
    
    def obtener_todas_cotizaciones(self, page: int = 1, per_page: int = 20) -> Dict:
        """
        Obtener todas las cotizaciones con paginación
        API compatible con DatabaseManager
        """
        return self.buscar_cotizaciones("", page, per_page)
    
    def generar_numero_automatico(self, datos_generales: Dict) -> str:
        """
        Generar número automático de cotización
        Formato: CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO
        """
        try:
            print(f"[NUMERO] Datos generales recibidos: {datos_generales}")
            
            # Obtener valores con fallbacks robustos
            cliente = safe_str(datos_generales.get('cliente', 'CLIENTE')).upper()
            vendedor = safe_str(datos_generales.get('vendedor', 'VEND')).upper()
            proyecto = safe_str(datos_generales.get('proyecto', 'PROYECTO')).upper()
            
            # Validar que no estén vacíos después de safe_str
            if not cliente or cliente.strip() == '':
                cliente = 'CLIENTE'
            if not vendedor or vendedor.strip() == '':
                vendedor = 'VEND'
            if not proyecto or proyecto.strip() == '':
                proyecto = 'PROYECTO'
            
            print(f"[NUMERO] Valores procesados - Cliente: '{cliente}', Vendedor: '{vendedor}', Proyecto: '{proyecto}'")
            
            # Limpiar caracteres especiales
            cliente = re.sub(r'[^A-Z0-9]', '-', cliente)[:10]
            # Extraer primeras letras de cada nombre (máximo 2 letras)
            palabras_vendedor = vendedor.split()
            vendedor = ''.join([palabra[0] for palabra in palabras_vendedor if palabra])[:2]
            proyecto = re.sub(r'[^A-Z0-9]', '-', proyecto)[:15]
            
            print(f"[NUMERO] Valores limpiados - Cliente: '{cliente}', Vendedor: '{vendedor}', Proyecto: '{proyecto}'")
            
            # Contar cotizaciones existentes para este vendedor
            if self.modo_offline:
                print(f"[NUMERO] Modo offline - generando número para vendedor: {vendedor}")
                data = self._cargar_datos_offline()
                cotizaciones = data.get("cotizaciones", [])
                print(f"[NUMERO] Cotizaciones cargadas: {len(cotizaciones)}")
                count = len([c for c in cotizaciones 
                           if c.get('datosGenerales', {}).get('vendedor', '').upper() == vendedor])
                print(f"[NUMERO] Count para vendedor {vendedor}: {count}")
            else:
                try:
                    cursor = self.pg_connection.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) as total FROM cotizaciones 
                        WHERE datos_generales->>'vendedor' ILIKE %s;
                    """, (f"%{vendedor}%",))
                    count = cursor.fetchone()['total']
                    cursor.close()
                except:
                    count = 0
            
            # Generar número
            numero = count + 1
            numero_cotizacion = f"{cliente}-CWS-{vendedor}-{numero:03d}-R1-{proyecto}"
            
            print(f"[NUMERO] Generado: {numero_cotizacion}")
            return numero_cotizacion
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[NUMERO] Error generando: {error_msg}")
            # Fallback simple
            timestamp = int(time.time())
            return f"CWS-AUTO-{timestamp}-R1"
    
    def generar_numero_cotizacion(self, cliente, vendedor, proyecto, revision=1):
        """
        Genera un número de cotización automáticamente con el formato:
        CLIENTE-CWS-INICIALES_VENDEDOR-###-R#-PROYECTO
        
        Con numeración consecutiva irrepetible usando PostgreSQL atomic operations
        """
        try:
            print(f"[NUMERO_COTIZACION] Generando para: Cliente='{cliente}', Vendedor='{vendedor}', Proyecto='{proyecto}', Revision={revision}")
            
            # Normalizar datos de entrada
            cliente = cliente.upper().replace(" ", "")[:10] if cliente else "CLIENTE"
            proyecto = proyecto.upper().replace(" ", "")[:10] if proyecto else "PROYECTO"
            
            # Obtener las iniciales del vendedor (máximo 2 letras)
            iniciales_vendedor = ""
            if vendedor:
                palabras = vendedor.strip().split()
                for palabra in palabras[:2]:  # Máximo 2 palabras
                    if palabra and palabra[0].isalpha():
                        iniciales_vendedor += palabra[0].upper()
                if len(iniciales_vendedor) < 2 and len(palabras) > 0:
                    # Si solo hay una palabra, tomar las primeras 2 letras
                    primera_palabra = palabras[0]
                    iniciales_vendedor = primera_palabra[:2].upper()
            
            if not iniciales_vendedor:
                iniciales_vendedor = "XX"
            
            print(f"[NUMERO_COTIZACION] Normalizados - Cliente: '{cliente}', Iniciales: '{iniciales_vendedor}', Proyecto: '{proyecto}'")
            
            # Generar patrón base para buscar números consecutivos
            patron_base = f"{cliente}-CWS-{iniciales_vendedor}"
            numero_consecutivo = self._obtener_siguiente_consecutivo(patron_base)
            
            # Formatear número completo
            numero_cotizacion = f"{cliente}-CWS-{iniciales_vendedor}-{numero_consecutivo:03d}-R{revision}-{proyecto}"
            
            print(f"[NUMERO_COTIZACION] Generado: {numero_cotizacion}")
            return numero_cotizacion
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[NUMERO_COTIZACION] Error generando: {error_msg}")
            # Fallback a número único basado en timestamp
            timestamp = int(time.time())
            return f"CWS-{timestamp}-R{revision}"
    
    def generar_numero_revision(self, numero_cotizacion_original, nueva_revision):
        """
        Genera un número de cotización para una nueva revisión manteniendo 
        el mismo número base pero actualizando la revisión
        Formato: CLIENTE-CWS-INICIALES-###-R#-PROYECTO
        """
        try:
            print(f"[NUMERO_REVISION] Original: '{numero_cotizacion_original}', Nueva revisión: {nueva_revision}")
            
            # Patrón para encontrar la revisión: -R seguida de uno o más dígitos-
            patron = r'-R\d+-'
            match = re.search(patron, numero_cotizacion_original)
            
            if match:
                # Extraer la parte antes de -R y después de -R#-
                inicio_revision = match.start()
                final_revision = match.end()
                
                base = numero_cotizacion_original[:inicio_revision]
                proyecto_parte = numero_cotizacion_original[final_revision:]
                
                # Generar nuevo número con la nueva revisión
                nuevo_numero = f"{base}-R{nueva_revision}-{proyecto_parte}"
                print(f"[NUMERO_REVISION] Generado: {nuevo_numero}")
                return nuevo_numero
            else:
                # Si no tiene el formato esperado, intentar agregar la revisión
                print(f"[NUMERO_REVISION] Formato no reconocido, agregando revisión al final")
                nuevo_numero = f"{numero_cotizacion_original}-R{nueva_revision}"
                print(f"[NUMERO_REVISION] Generado (fallback): {nuevo_numero}")
                return nuevo_numero
                
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[NUMERO_REVISION] Error generando: {error_msg}")
            return f"{numero_cotizacion_original}-R{nueva_revision}"
    
    def _obtener_siguiente_consecutivo(self, patron_base):
        """
        Obtiene el siguiente número consecutivo para un patrón base dado
        Implementa lógica atómica para evitar números duplicados
        """
        try:
            print(f"[CONSECUTIVO] Buscando siguiente para patrón: '{patron_base}'")
            
            if self.modo_offline:
                return self._obtener_consecutivo_offline(patron_base)
            else:
                return self._obtener_consecutivo_supabase(patron_base)
                
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[CONSECUTIVO] Error obteniendo: {error_msg}")
            return 1
    
    def _obtener_consecutivo_supabase(self, patron_base):
        """Obtener consecutivo usando tabla de contadores atómica - 100% irrepetible"""
        try:
            cursor = self.pg_connection.cursor()
            
            print(f"[CONTADOR_ATOMICO] Obteniendo siguiente para patrón: '{patron_base}'")
            
            # Operación atómica usando ON CONFLICT para increment
            query = """
                INSERT INTO cotizacion_counters (patron, ultimo_numero, descripcion) 
                VALUES (%s, 1, %s)
                ON CONFLICT (patron) 
                DO UPDATE SET 
                    ultimo_numero = cotizacion_counters.ultimo_numero + 1,
                    updated_at = NOW()
                RETURNING ultimo_numero;
            """
            
            descripcion = f"Contador automático para {patron_base}"
            cursor.execute(query, (patron_base, descripcion))
            
            # Obtener el número asignado
            resultado = cursor.fetchone()
            siguiente = resultado['ultimo_numero']
            
            # Commit inmediato para liberar el lock
            self.pg_connection.commit()
            cursor.close()
            
            print(f"[CONTADOR_ATOMICO] Número asignado: {siguiente} para patrón '{patron_base}'")
            
            return siguiente
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[CONTADOR_ATOMICO] Error: {error_msg}")
            
            # Rollback en caso de error
            try:
                self.pg_connection.rollback()
            except:
                pass
                
            # Fallback a método legacy
            print(f"[CONTADOR_ATOMICO] Usando fallback legacy para patrón: {patron_base}")
            return self._obtener_consecutivo_legacy(patron_base)
    
    def _obtener_consecutivo_legacy(self, patron_base):
        """Método legacy de consecutivos (fallback)"""
        try:
            cursor = self.pg_connection.cursor()
            
            # Usar FOR UPDATE para prevenir race conditions
            query = """
                SELECT numero_cotizacion FROM cotizaciones 
                WHERE numero_cotizacion LIKE %s 
                ORDER BY numero_cotizacion DESC
                FOR UPDATE;
            """
            
            # Buscar cotizaciones que coincidan con el patrón
            patron_sql = f"{patron_base}%"
            cursor.execute(query, (patron_sql,))
            resultados = cursor.fetchall()
            
            # Extraer números consecutivos existentes
            numeros_existentes = []
            for resultado in resultados:
                numero_cot = resultado['numero_cotizacion']
                if numero_cot.startswith(patron_base):
                    try:
                        # Extraer el número consecutivo del formato: CLIENTE-CWS-INICIALES-###-R#-PROYECTO
                        partes = numero_cot.split('-')
                        if len(partes) >= 4:  # Debe tener al menos: CLIENTE-CWS-INICIALES-###
                            num_parte = partes[3]  # La parte ### está en el índice 3
                            if num_parte.isdigit():
                                num_consecutivo = int(num_parte)
                                numeros_existentes.append(num_consecutivo)
                    except (ValueError, IndexError):
                        continue
            
            cursor.close()
            
            # Encontrar el siguiente número disponible
            if not numeros_existentes:
                siguiente = 1
            else:
                siguiente = max(numeros_existentes) + 1
            
            print(f"[CONSECUTIVO_LEGACY] Números existentes: {sorted(numeros_existentes)}")
            print(f"[CONSECUTIVO_LEGACY] Siguiente: {siguiente}")
            
            return siguiente
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[CONSECUTIVO_LEGACY] Error: {error_msg}")
            # Fallback a modo offline
            return self._obtener_consecutivo_offline(patron_base)
    
    def _obtener_consecutivo_offline(self, patron_base):
        """Obtener consecutivo usando contadores JSON (modo offline) - Sincronizado con Supabase"""
        try:
            data = self._cargar_datos_offline()
            
            # Inicializar sección de contadores si no existe
            if "contadores" not in data:
                data["contadores"] = {}
            
            contadores = data["contadores"]
            
            print(f"[CONTADOR_OFFLINE] Obteniendo siguiente para patrón: '{patron_base}'")
            
            # Obtener y incrementar contador para este patrón
            if patron_base in contadores:
                siguiente = contadores[patron_base]["ultimo_numero"] + 1
                contadores[patron_base]["ultimo_numero"] = siguiente
                contadores[patron_base]["updated_at"] = datetime.now().isoformat()
                print(f"[CONTADOR_OFFLINE] Incrementado contador existente: {siguiente-1} -> {siguiente}")
            else:
                # Nuevo patrón: analizar cotizaciones existentes para sincronizar
                print(f"[CONTADOR_OFFLINE] Nuevo patrón, analizando cotizaciones existentes...")
                
                cotizaciones = data.get("cotizaciones", [])
                numeros_existentes = []
                
                for cotizacion in cotizaciones:
                    numero_cot = cotizacion.get("numeroCotizacion", "")
                    if numero_cot.startswith(patron_base):
                        try:
                            # Extraer el número consecutivo del formato: CLIENTE-CWS-INICIALES-###-R#-PROYECTO
                            partes = numero_cot.split('-')
                            if len(partes) >= 4:  # Debe tener al menos: CLIENTE-CWS-INICIALES-###
                                num_parte = partes[3]  # La parte ### está en el índice 3
                                if num_parte.isdigit():
                                    num_consecutivo = int(num_parte)
                                    numeros_existentes.append(num_consecutivo)
                        except (ValueError, IndexError):
                            continue
                
                # Establecer contador basado en máximo existente
                if numeros_existentes:
                    ultimo_usado = max(numeros_existentes)
                    siguiente = ultimo_usado + 1
                    print(f"[CONTADOR_OFFLINE] Números existentes: {sorted(numeros_existentes)}, máximo: {ultimo_usado}")
                else:
                    siguiente = 1
                    print(f"[CONTADOR_OFFLINE] No hay números existentes, iniciando en 1")
                
                # Crear entrada de contador
                contadores[patron_base] = {
                    "ultimo_numero": siguiente,
                    "descripcion": f"Contador offline para {patron_base}",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            
            # Guardar datos actualizados
            if self._guardar_datos_offline(data):
                print(f"[CONTADOR_OFFLINE] Número asignado: {siguiente} para patrón '{patron_base}'")
                return siguiente
            else:
                print(f"[CONTADOR_OFFLINE] Error guardando contador, usando fallback")
                return self._obtener_consecutivo_fallback(patron_base)
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[CONTADOR_OFFLINE] Error: {error_msg}")
            return self._obtener_consecutivo_fallback(patron_base)
    
    def _obtener_consecutivo_fallback(self, patron_base):
        """Último recurso: generar número usando timestamp"""
        try:
            timestamp = int(time.time())
            # Usar últimos 4 dígitos del timestamp como número
            siguiente = timestamp % 10000
            if siguiente == 0:
                siguiente = 1
            
            print(f"[CONTADOR_FALLBACK] Número generado: {siguiente} para patrón '{patron_base}'")
            return siguiente
            
        except Exception:
            print(f"[CONTADOR_FALLBACK] Error crítico, usando 1")
            return 1
    
    def verificar_numero_unico(self, numero_cotizacion):
        """
        Verifica que un número de cotización no exista ya en la base de datos
        Devuelve True si es único, False si ya existe
        """
        try:
            if self.modo_offline:
                data = self._cargar_datos_offline()
                cotizaciones = data.get("cotizaciones", [])
                for cot in cotizaciones:
                    if cot.get("numeroCotizacion") == numero_cotizacion:
                        return False
                return True
            else:
                try:
                    cursor = self.pg_connection.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) as total FROM cotizaciones 
                        WHERE numero_cotizacion = %s;
                    """, (numero_cotizacion,))
                    count = cursor.fetchone()['total']
                    cursor.close()
                    return count == 0
                except Exception as e:
                    print(f"[VERIFICAR_UNICO] Error en Supabase: {safe_str(e)}")
                    # Fallback a offline
                    data = self._cargar_datos_offline()
                    cotizaciones = data.get("cotizaciones", [])
                    for cot in cotizaciones:
                        if cot.get("numeroCotizacion") == numero_cotizacion:
                            return False
                    return True
                    
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[VERIFICAR_UNICO] Error: {error_msg}")
            return True  # Si hay error, asumir que es único para no bloquear
    
    def sincronizar_bidireccional(self) -> dict:
        """
        Sincronización bidireccional mejorada: JSON ↔ Supabase PostgreSQL
        Adaptado de la lógica original de MongoDB para múltiples dispositivos
        
        Estrategia:
        1. JSON a Supabase: Subir cambios locales
        2. Supabase a JSON: Descargar cambios remotos  
        3. Resolución de conflictos: Last-write-wins basado en timestamp
        
        Returns:
            Dict con resultado detallado de la sincronización
        """
        if self.modo_offline:
            return {
                "success": False,
                "error": "Supabase no disponible - en modo offline",
                "subidas": 0,
                "descargas": 0,
                "conflictos": 0
            }
        
        print("[SYNC_BIDIRECCIONAL] Iniciando sincronización bidireccional...")
        
        try:
            # Cargar datos JSON local
            datos_offline = self._cargar_datos_offline()
            cotizaciones_json = {cot.get("numeroCotizacion"): cot for cot in datos_offline.get("cotizaciones", []) if cot.get("numeroCotizacion")}
            
            # Obtener todas las cotizaciones de Supabase PostgreSQL
            cotizaciones_supabase = {}
            try:
                cursor = self.pg_connection.cursor()
                cursor.execute("SELECT * FROM cotizaciones ORDER BY numero_cotizacion;")
                resultados = cursor.fetchall()
                
                for row in resultados:
                    # Reconstruir estructura de cotización desde PostgreSQL
                    numero = row['numero_cotizacion']
                    cotizacion = {
                        'numeroCotizacion': numero,
                        'datosGenerales': row['datos_generales'],  # JSONB field
                        'items': row['items'],  # JSONB field
                        'revision': row['revision'],
                        'version': row['version'],
                        'timestamp': row['timestamp'],
                        'fechaCreacion': row['fecha_creacion'].isoformat() if row['fecha_creacion'] else None,
                        'usuario': row['usuario'],
                        'observaciones': row['observaciones'],
                        'id': row['id']
                    }
                    cotizaciones_supabase[numero] = cotizacion
                
                cursor.close()
                print(f"[SYNC] Supabase: {len(cotizaciones_supabase)} cotizaciones")
            except Exception as e:
                print(f"[SYNC] Error leyendo Supabase: {e}")
                return {"success": False, "error": str(e)}
            
            print(f"[SYNC] JSON local: {len(cotizaciones_json)} cotizaciones")
            
            # Contadores
            subidas = 0      # JSON a Supabase
            descargas = 0    # Supabase a JSON  
            conflictos = 0   # Resueltos por timestamp
            errores = 0
            
            # FASE 1: JSON a Supabase (subir cambios locales)
            print("[SYNC_FASE_1] JSON a Supabase")
            
            for numero, cot_json in cotizaciones_json.items():
                try:
                    cot_supabase = cotizaciones_supabase.get(numero)
                    
                    if not cot_supabase:
                        # No existe en Supabase, subir
                        cot_limpia = self._limpiar_cotizacion_para_supabase(cot_json)
                        resultado_guardado = self._guardar_cotizacion_supabase(cot_limpia)
                        
                        if resultado_guardado.get("success"):
                            subidas += 1
                            print(f"[SUBIDA] Nueva: {numero}")
                        else:
                            print(f"[SUBIDA_ERROR] {numero}: {resultado_guardado.get('error', 'Error desconocido')}")
                            errores += 1
                        
                    else:
                        # Existe en ambos, verificar timestamps
                        ts_json = cot_json.get("timestamp", 0)
                        ts_supabase = cot_supabase.get("timestamp", 0)
                        
                        if ts_json > ts_supabase:
                            # JSON más reciente, actualizar Supabase
                            cot_limpia = self._limpiar_cotizacion_para_supabase(cot_json)
                            
                            # Actualizar en Supabase usando UPDATE
                            cursor = self.pg_connection.cursor()
                            cursor.execute("""
                                UPDATE cotizaciones 
                                SET datos_generales = %s, items = %s, revision = %s, 
                                    version = %s, timestamp = %s, usuario = %s, 
                                    observaciones = %s, updated_at = NOW()
                                WHERE numero_cotizacion = %s
                            """, (
                                Json(cot_limpia['datosGenerales']),
                                Json(cot_limpia['items']),
                                cot_limpia['revision'],
                                cot_limpia['version'],
                                cot_limpia['timestamp'],
                                cot_limpia.get('usuario'),
                                cot_limpia.get('observaciones'),
                                numero
                            ))
                            self.pg_connection.commit()
                            cursor.close()
                            
                            subidas += 1
                            conflictos += 1
                            print(f"[CONFLICTO] JSON más reciente: {numero}")
                            
                except Exception as e:
                    print(f"[SUBIDA_ERROR] {numero}: {e}")
                    errores += 1
            
            # FASE 2: Supabase a JSON (descargar cambios remotos)  
            print("[SYNC_FASE_2] Supabase a JSON")
            
            cotizaciones_json_actualizadas = cotizaciones_json.copy()
            
            for numero, cot_supabase in cotizaciones_supabase.items():
                try:
                    cot_json = cotizaciones_json.get(numero)
                    
                    if not cot_json:
                        # No existe en JSON, descargar
                        cot_limpia = self._limpiar_cotizacion_para_json(cot_supabase)
                        cotizaciones_json_actualizadas[numero] = cot_limpia
                        descargas += 1
                        print(f"[DESCARGA] Nueva: {numero}")
                        
                    else:
                        # Existe en ambos, verificar timestamps
                        ts_json = cot_json.get("timestamp", 0)
                        ts_supabase = cot_supabase.get("timestamp", 0)
                        
                        if ts_supabase > ts_json:
                            # Supabase más reciente, actualizar JSON
                            cot_limpia = self._limpiar_cotizacion_para_json(cot_supabase)
                            cotizaciones_json_actualizadas[numero] = cot_limpia
                            descargas += 1
                            conflictos += 1
                            print(f"[CONFLICTO] Supabase más reciente: {numero}")
                            
                except Exception as e:
                    print(f"[DESCARGA_ERROR] {numero}: {e}")
                    errores += 1
            
            # FASE 3: Guardar JSON actualizado
            if descargas > 0:
                print("[SYNC_FASE_3] Guardando JSON actualizado...")
                datos_offline["cotizaciones"] = list(cotizaciones_json_actualizadas.values())
                datos_offline["ultima_sincronizacion"] = datetime.now().isoformat()
                datos_offline["sincronizaciones"] = datos_offline.get("sincronizaciones", 0) + 1
                
                self._guardar_datos_offline(datos_offline)
            
            resultado = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "subidas": subidas,      # JSON a Supabase
                "descargas": descargas,  # Supabase a JSON
                "conflictos": conflictos,
                "errores": errores,
                "total_json": len(cotizaciones_json_actualizadas),
                "total_supabase": len(cotizaciones_supabase),
                "mensaje": f"Sincronización completada: subidas:{subidas} descargas:{descargas} conflictos:{conflictos} errores:{errores}"
            }
            
            print(f"[SYNC_RESULTADO] {resultado['mensaje']}")
            return resultado
            
        except Exception as e:
            error_msg = f"Error en sincronización bidireccional: {safe_str(e)}"
            print(f"[SYNC_ERROR] {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _limpiar_cotizacion_para_supabase(self, cotizacion: dict) -> dict:
        """Limpia cotización para insertar en Supabase PostgreSQL"""
        cot_limpia = cotizacion.copy()
        
        # Remover campos específicos del JSON offline que no van a Supabase
        campos_a_remover = ["id", "respaldo_de_mongodb", "fecha_respaldo", "sincronizada", "fecha_sincronizacion"]
        for campo in campos_a_remover:
            cot_limpia.pop(campo, None)
        
        # Asegurar estructura correcta para Supabase
        if 'datosGenerales' not in cot_limpia:
            cot_limpia['datosGenerales'] = {}
        if 'items' not in cot_limpia:
            cot_limpia['items'] = []
        
        # Valores por defecto
        cot_limpia.setdefault('revision', 1)
        cot_limpia.setdefault('version', '1.0.0')
        cot_limpia.setdefault('timestamp', int(time.time() * 1000))
        
        return cot_limpia
    
    def _limpiar_cotizacion_para_json(self, cotizacion: dict) -> dict:
        """Limpia cotización para insertar en JSON offline"""
        cot_limpia = cotizacion.copy()
        
        # Convertir ID de Supabase a string si existe
        if "id" in cot_limpia:
            cot_limpia["_id"] = str(cot_limpia["id"])
        
        # Marcar como sincronizada
        cot_limpia["sincronizada"] = True
        cot_limpia["fecha_sincronizacion"] = datetime.now().isoformat()
        
        # Asegurar que fechaCreacion sea string si es datetime
        if "fechaCreacion" in cot_limpia and hasattr(cot_limpia["fechaCreacion"], "isoformat"):
            cot_limpia["fechaCreacion"] = cot_limpia["fechaCreacion"].isoformat()
        
        return cot_limpia
    
    def obtener_estado_sincronizacion(self):
        """Obtiene información del estado de sincronización"""
        try:
            datos_offline = self._cargar_datos_offline()
            cotizaciones = datos_offline.get("cotizaciones", [])
            
            total = len(cotizaciones)
            sincronizadas = sum(1 for c in cotizaciones if c.get("sincronizada", False))
            pendientes = total - sincronizadas
            
            return {
                "total": total,
                "sincronizadas": sincronizadas,
                "pendientes": pendientes,
                "ultima_sincronizacion": datos_offline.get("ultima_sincronizacion"),
                "total_sincronizaciones": datos_offline.get("sincronizaciones", 0),
                "modo_offline": self.modo_offline
            }
            
        except Exception as e:
            return {
                "error": safe_str(e),
                "total": 0,
                "sincronizadas": 0,
                "pendientes": 0
            }
    
    def close(self):
        """Cerrar conexiones"""
        if self.pg_connection:
            try:
                self.pg_connection.close()
                print("[SUPABASE] Conexión PostgreSQL cerrada")
            except:
                pass
        
        # El cliente Supabase no necesita cierre explícito
        print("[SUPABASE] SupabaseManager cerrado")
    
    def cerrar_conexion(self):
        """Alias para close() - compatibilidad con código existente"""
        self.close()

# Alias para compatibilidad con código existente
DatabaseManager = SupabaseManager