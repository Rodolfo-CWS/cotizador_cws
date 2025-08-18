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
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def safe_str(value, default=""):
    """Convierte valor a string de forma segura (compatible con Unicode)"""
    if value is None:
        return default
    try:
        return str(value).encode('utf-8', errors='ignore').decode('utf-8')
    except:
        return default

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
        self.ultima_conexion = None
        
        # Archivo JSON para fallback offline
        self.archivo_offline = os.path.join(os.getcwd(), "cotizaciones_offline.json")
        
        # Inicializar conexión
        self._inicializar_conexion()
    
    def _inicializar_conexion(self):
        """Inicializar conexión a Supabase"""
        print("[SUPABASE] Inicializando conexion...")
        
        # Validar configuración
        if not self.supabase_url or not self.database_url:
            print("[SUPABASE] Variables de entorno faltantes - modo offline")
            print("   Necesitas: SUPABASE_URL, DATABASE_URL")
            self.modo_offline = True
            return
        
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
            self.pg_connection = psycopg2.connect(
                self.database_url,
                cursor_factory=RealDictCursor,
                connect_timeout=10,
                application_name="CWS_Cotizador"
            )
            
            # Test de conexión
            cursor = self.pg_connection.cursor()
            cursor.execute("SELECT 1 as test;")
            result = cursor.fetchone()
            cursor.close()
            
            if result['test'] == 1:
                self.modo_offline = False
                self.ultima_conexion = datetime.now()
                print("[SUPABASE] Conectado a PostgreSQL exitosamente")
                print(f"[SUPABASE] URL: {self.supabase_url}")
            else:
                raise Exception("Test de conexión falló")
                
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[SUPABASE] Error conectando: {error_msg}")
            print("[SUPABASE] Activando modo offline")
            self.modo_offline = True
            
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
        """Obtener estadísticas de la base de datos"""
        if self.modo_offline:
            # Estadísticas desde JSON
            data = self._cargar_datos_offline()
            cotizaciones = data.get("cotizaciones", [])
            
            return {
                "total_cotizaciones": len(cotizaciones),
                "modo": "offline",
                "fuente": "JSON local",
                "archivo": self.archivo_offline
            }
        else:
            try:
                cursor = self.pg_connection.cursor()
                
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
                print(f"[SUPABASE] Error obteniendo estadísticas: {safe_str(e)}")
                return {"error": safe_str(e)}
    
    def guardar_cotizacion(self, datos: Dict) -> Dict:
        """
        Guardar cotización en Supabase (online) o JSON (offline)
        Mantiene API compatible con DatabaseManager
        """
        try:
            numero_cotizacion = datos.get('numeroCotizacion')
            if not numero_cotizacion:
                return {"success": False, "error": "Número de cotización requerido"}
            
            print(f"[GUARDAR] Procesando cotización: {numero_cotizacion}")
            
            # Intentar guardar en Supabase si estamos online
            if not self.modo_offline:
                try:
                    resultado_online = self._guardar_cotizacion_supabase(datos)
                    
                    # También guardar en JSON como backup
                    self._guardar_cotizacion_offline(datos)
                    
                    return resultado_online
                    
                except Exception as e:
                    print(f"[SUPABASE] Error guardando online: {safe_str(e)}")
                    print("[SUPABASE] 🔄 Fallback a modo offline")
                    self.modo_offline = True
            
            # Guardar en JSON (modo offline o fallback)
            return self._guardar_cotizacion_offline(datos)
            
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[GUARDAR] Error general: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _guardar_cotizacion_supabase(self, datos: Dict) -> Dict:
        """Guardar cotización en Supabase PostgreSQL"""
        try:
            cursor = self.pg_connection.cursor()
            
            # Extraer datos
            numero_cotizacion = datos.get('numeroCotizacion')
            datos_generales = datos.get('datosGenerales', {})
            items = datos.get('items', [])
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
                Json(datos_generales),  # JSONB
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
            
            print(f"[SUPABASE] ✅ Cotización guardada: ID={cotizacion_id}")
            
            return {
                "success": True,
                "id": cotizacion_id,
                "numero_cotizacion": numero_cotizacion,
                "modo": "online",
                "mensaje": "Guardado en Supabase PostgreSQL"
            }
            
        except Exception as e:
            # Rollback en caso de error
            try:
                self.pg_connection.rollback()
            except:
                pass
            
            error_msg = safe_str(e)
            print(f"[SUPABASE] ❌ Error guardando: {error_msg}")
            raise e
    
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
                print(f"[OFFLINE] 🔄 Cotización actualizada: {numero_cotizacion}")
            else:
                cotizaciones.append(datos)
                print(f"[OFFLINE] ➕ Nueva cotización: {numero_cotizacion}")
            
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
            if self.modo_offline:
                return self._buscar_cotizaciones_offline(query, page, per_page)
            else:
                try:
                    return self._buscar_cotizaciones_supabase(query, page, per_page)
                except Exception as e:
                    print(f"[SUPABASE] Error en búsqueda online: {safe_str(e)}")
                    print("[SUPABASE] 🔄 Fallback a búsqueda offline")
                    return self._buscar_cotizaciones_offline(query, page, per_page)
                    
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[BUSCAR] Error general: {error_msg}")
            return {"error": error_msg}
    
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
            
            print(f"[SUPABASE] 🔍 Encontradas {len(cotizaciones)} de {total} cotizaciones")
            
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
            data = self._cargar_datos_offline()
            cotizaciones = data.get("cotizaciones", [])
            
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
            
            print(f"[OFFLINE] 🔍 Encontradas {len(resultados_pagina)} de {total} cotizaciones")
            
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
            if self.modo_offline:
                return self._obtener_cotizacion_offline(numero_cotizacion)
            else:
                try:
                    return self._obtener_cotizacion_supabase(numero_cotizacion)
                except Exception as e:
                    print(f"[SUPABASE] Error obteniendo cotización: {safe_str(e)}")
                    return self._obtener_cotizacion_offline(numero_cotizacion)
        
        except Exception as e:
            error_msg = safe_str(e)
            print(f"[OBTENER] Error general: {error_msg}")
            return {"error": error_msg, "encontrado": False}
    
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
            cliente = safe_str(datos_generales.get('cliente', 'CLIENTE')).upper()
            vendedor = safe_str(datos_generales.get('vendedor', 'VEND')).upper()
            proyecto = safe_str(datos_generales.get('proyecto', 'PROYECTO')).upper()
            
            # Limpiar caracteres especiales
            import re
            cliente = re.sub(r'[^A-Z0-9]', '-', cliente)[:10]
            vendedor = re.sub(r'[^A-Z0-9]', '', vendedor)[:3]
            proyecto = re.sub(r'[^A-Z0-9]', '-', proyecto)[:15]
            
            # Contar cotizaciones existentes para este vendedor
            if self.modo_offline:
                data = self._cargar_datos_offline()
                cotizaciones = data.get("cotizaciones", [])
                count = len([c for c in cotizaciones 
                           if c.get('datosGenerales', {}).get('vendedor', '').upper() == vendedor])
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