# -*- coding: utf-8 -*-
"""
BOM Database Manager - Gestor de base de datos para análisis BOM
=============================================================

Maneja todas las operaciones de base de datos relacionadas con
el análisis de PDFs y extracción de BOMs usando Gemini AI.

Autor: CWS Company
Fecha: 2025-08-29
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Any
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

class BOMDatabaseManager:
    """Gestor de base de datos específico para operaciones BOM"""
    
    def __init__(self, database_url: str = None):
        """
        Inicializa el gestor BOM
        
        Args:
            database_url: URL de conexión PostgreSQL/Supabase
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL requerida para BOM Database Manager")
        
        # Verificar conexión inicial
        try:
            self._test_connection()
            print("[BOM_DB] Conexión a base de datos establecida correctamente")
        except Exception as e:
            print(f"[BOM_DB] ERROR en conexión inicial: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones de base de datos"""
        conn = None
        try:
            conn = psycopg2.connect(self.database_url)
            yield conn
        finally:
            if conn:
                conn.close()
    
    def _test_connection(self):
        """Prueba la conexión a la base de datos"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] != 1:
                    raise Exception("Test de conexión falló")
    
    def crear_esquema_bom(self):
        """
        Crea el esquema completo de BOM si no existe
        Ejecuta el script bom_database_schema.sql
        """
        try:
            # Leer el archivo de esquema
            schema_path = os.path.join(os.path.dirname(__file__), 'bom_database_schema.sql')
            
            if not os.path.exists(schema_path):
                print(f"[BOM_DB] Archivo de esquema no encontrado: {schema_path}")
                return False
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Ejecutar el esquema completo
                    cursor.execute(schema_sql)
                    conn.commit()
            
            print("[BOM_DB] Esquema BOM creado exitosamente")
            return True
            
        except Exception as e:
            print(f"[BOM_DB] ERROR creando esquema: {e}")
            return False
    
    def verificar_esquema_existente(self) -> bool:
        """Verifica si las tablas BOM ya existen"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_name IN ('bom_analysis', 'bom_items', 'bom_consolidated')
                        AND table_schema = 'public';
                    """)
                    count = cursor.fetchone()[0]
                    return count >= 3
        except Exception as e:
            print(f"[BOM_DB] ERROR verificando esquema: {e}")
            return False
    
    def guardar_analisis_bom(self, resultado_analisis: Dict) -> int:
        """
        Guarda un análisis BOM completo en la base de datos
        
        Args:
            resultado_analisis: Resultado del análisis Gemini
            
        Returns:
            ID del análisis guardado
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # 1. Crear registro principal de análisis
                    analysis_id = self._crear_registro_analisis(cursor, resultado_analisis)
                    
                    # 2. Guardar información de páginas
                    self._guardar_paginas_analisis(cursor, analysis_id, resultado_analisis)
                    
                    # 3. Guardar items individuales
                    self._guardar_items_bom(cursor, analysis_id, resultado_analisis)
                    
                    # 4. Guardar materiales consolidados
                    self._guardar_materiales_consolidados(cursor, analysis_id, resultado_analisis)
                    
                    # 5. Guardar clasificaciones
                    self._guardar_clasificaciones(cursor, analysis_id, resultado_analisis)
                    
                    conn.commit()
                    print(f"[BOM_DB] Análisis BOM guardado exitosamente con ID: {analysis_id}")
                    return analysis_id
                    
        except Exception as e:
            print(f"[BOM_DB] ERROR guardando análisis: {e}")
            if conn:
                conn.rollback()
            return -1
    
    def _crear_registro_analisis(self, cursor, resultado: Dict) -> int:
        """Crea el registro principal de análisis"""
        estadisticas = resultado.get("estadisticas", {})
        grand_total = resultado.get("paso_5_grand_total", {})
        totales = grand_total.get("totales_generales", {})
        
        cursor.execute("""
            INSERT INTO bom_analysis (
                numero_cotizacion, ruta_pdf, nombre_archivo, 
                total_paginas, total_items_encontrados, total_items_unicos, 
                total_items_consolidados, paginas_con_tablas, 
                estado_analisis, errores_analisis, exito,
                total_cantidad_items, total_area_mm2, total_volumen_mm3,
                configuracion_analisis
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            resultado.get("numero_cotizacion"),
            resultado.get("ruta_pdf"),
            os.path.basename(resultado.get("ruta_pdf", "")),
            estadisticas.get("total_paginas_analizadas", 0),
            estadisticas.get("total_items_encontrados", 0),
            estadisticas.get("total_items_unicos", 0),
            estadisticas.get("total_items_consolidados", 0),
            estadisticas.get("paginas_con_tablas", 0),
            "completado" if resultado.get("exito") else "error",
            resultado.get("errores", []),
            resultado.get("exito", False),
            totales.get("total_cantidad_items", 0),
            totales.get("total_area_mm2", 0),
            totales.get("total_volumen_mm3", 0),
            json.dumps({"gemini_version": "1.0", "proceso": "5_pasos"})
        ))
        
        analysis_id = cursor.fetchone()['id']
        return analysis_id
    
    def _guardar_paginas_analisis(self, cursor, analysis_id: int, resultado: Dict):
        """Guarda información de páginas analizadas"""
        paginas_info = resultado.get("paso_1_paginas", [])
        
        for pagina in paginas_info:
            cursor.execute("""
                INSERT INTO bom_pages (
                    bom_analysis_id, numero_pagina, tabla_detectada, items_encontrados
                ) VALUES (%s, %s, %s, %s);
            """, (
                analysis_id,
                pagina.get("numero_pagina", 1),
                pagina.get("tabla_detectada", False),
                pagina.get("items_encontrados", 0)
            ))
    
    def _guardar_items_bom(self, cursor, analysis_id: int, resultado: Dict):
        """Guarda items BOM individuales"""
        tablas_por_pagina = resultado.get("paso_2_tablas_por_pagina", [])
        
        for tabla_pagina in tablas_por_pagina:
            numero_pagina = tabla_pagina.get("pagina", 1)
            items = tabla_pagina.get("items", [])
            
            for item in items:
                # Calcular subtotales dimensionales
                area_unitaria = None
                area_total = None
                volumen_unitario = None
                volumen_total = None
                
                if item.get("largo") and item.get("ancho"):
                    area_unitaria = item["largo"] * item["ancho"]
                    area_total = area_unitaria * item.get("cantidad", 0)
                    
                    if item.get("espesor"):
                        volumen_unitario = area_unitaria * item["espesor"]
                        volumen_total = volumen_unitario * item.get("cantidad", 0)
                
                # Generar key de consolidación
                key_consolidacion = f"{item.get('item_id', '')}_{item.get('descripcion', '')}_{item.get('largo', '')}_{item.get('ancho', '')}_{item.get('espesor', '')}".lower()
                
                cursor.execute("""
                    INSERT INTO bom_items (
                        bom_analysis_id, item_id, cantidad, udm, descripcion,
                        largo_mm, ancho_mm, espesor_mm, clasificacion, pagina_origen,
                        area_unitaria_mm2, area_total_mm2, volumen_unitario_mm3, 
                        volumen_total_mm3, key_consolidacion
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    analysis_id,
                    item.get("item_id", ""),
                    item.get("cantidad", 0),
                    item.get("udm", ""),
                    item.get("descripcion", ""),
                    item.get("largo"),
                    item.get("ancho"),
                    item.get("espesor"),
                    item.get("clasificacion", ""),
                    numero_pagina,
                    area_unitaria,
                    area_total,
                    volumen_unitario,
                    volumen_total,
                    key_consolidacion
                ))
    
    def _guardar_materiales_consolidados(self, cursor, analysis_id: int, resultado: Dict):
        """Guarda materiales consolidados (Grand Total)"""
        tabla_master = resultado.get("paso_4_tabla_master", [])
        
        for i, material in enumerate(tabla_master):
            subtotales = material.get("subtotales_dimensionales", {})
            
            cursor.execute("""
                INSERT INTO bom_consolidated (
                    bom_analysis_id, item_id, descripcion, clasificacion,
                    cantidad_total, udm, largo_mm, ancho_mm, espesor_mm,
                    area_total_mm2, volumen_total_mm3, ocurrencias_en_pdf,
                    paginas_origen, es_material_repetido, orden_importancia
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                analysis_id,
                material.get("item_id", ""),
                material.get("descripcion", ""),
                material.get("clasificacion", ""),
                material.get("cantidad_total", 0),
                material.get("udm", ""),
                material.get("largo"),
                material.get("ancho"),
                material.get("espesor"),
                subtotales.get("area_total_mm2"),
                subtotales.get("volumen_total_mm3"),
                material.get("ocurrencias", 1),
                material.get("paginas_origen", []),
                material.get("ocurrencias", 1) > 1,
                len(tabla_master) - i  # Orden de importancia inverso
            ))
    
    def _guardar_clasificaciones(self, cursor, analysis_id: int, resultado: Dict):
        """Guarda clasificaciones de materiales"""
        grand_total = resultado.get("paso_5_grand_total", {})
        clasificaciones = grand_total.get("clasificacion_por_tipo", {})
        
        for nombre_clasificacion, info_clasificacion in clasificaciones.items():
            cursor.execute("""
                INSERT INTO bom_classifications (
                    bom_analysis_id, nombre_clasificacion, total_items,
                    total_cantidad, total_area_mm2, total_volumen_mm3
                ) VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                analysis_id,
                nombre_clasificacion,
                len(info_clasificacion.get("items", [])),
                info_clasificacion.get("total_cantidad", 0),
                info_clasificacion.get("total_area", 0),
                info_clasificacion.get("total_volumen", 0)
            ))
    
    def obtener_analisis_bom(self, analysis_id: int) -> Optional[Dict]:
        """Obtiene un análisis BOM completo por ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Obtener información principal
                    cursor.execute("SELECT * FROM bom_analysis WHERE id = %s", (analysis_id,))
                    analisis = cursor.fetchone()
                    
                    if not analisis:
                        return None
                    
                    # Convertir a dict
                    resultado = dict(analisis)
                    
                    # Obtener materiales consolidados
                    cursor.execute("""
                        SELECT * FROM bom_consolidated 
                        WHERE bom_analysis_id = %s 
                        ORDER BY orden_importancia DESC
                    """, (analysis_id,))
                    resultado["materiales_consolidados"] = [dict(row) for row in cursor.fetchall()]
                    
                    # Obtener clasificaciones
                    cursor.execute("""
                        SELECT * FROM bom_classifications 
                        WHERE bom_analysis_id = %s 
                        ORDER BY total_cantidad DESC
                    """, (analysis_id,))
                    resultado["clasificaciones"] = [dict(row) for row in cursor.fetchall()]
                    
                    # Obtener páginas
                    cursor.execute("""
                        SELECT * FROM bom_pages 
                        WHERE bom_analysis_id = %s 
                        ORDER BY numero_pagina
                    """, (analysis_id,))
                    resultado["paginas"] = [dict(row) for row in cursor.fetchall()]
                    
                    return resultado
                    
        except Exception as e:
            print(f"[BOM_DB] ERROR obteniendo análisis {analysis_id}: {e}")
            return None
    
    def buscar_analisis_bom(self, numero_cotizacion: str = None, limit: int = 50) -> List[Dict]:
        """Busca análisis BOM por criterios"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    if numero_cotizacion:
                        cursor.execute("""
                            SELECT * FROM v_bom_analysis_summary 
                            WHERE numero_cotizacion ILIKE %s 
                            ORDER BY fecha_analisis DESC 
                            LIMIT %s
                        """, (f"%{numero_cotizacion}%", limit))
                    else:
                        cursor.execute("""
                            SELECT * FROM v_bom_analysis_summary 
                            ORDER BY fecha_analisis DESC 
                            LIMIT %s
                        """, (limit,))
                    
                    return [dict(row) for row in cursor.fetchall()]
                    
        except Exception as e:
            print(f"[BOM_DB] ERROR en búsqueda: {e}")
            return []
    
    def obtener_estadisticas_generales(self) -> Dict:
        """Obtiene estadísticas generales del sistema BOM"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Estadísticas básicas
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_analisis,
                            COUNT(*) FILTER (WHERE exito = true) as analisis_exitosos,
                            COUNT(*) FILTER (WHERE estado_analisis = 'completado') as analisis_completados,
                            SUM(total_items_encontrados) as total_items_sistema,
                            AVG(total_paginas) as promedio_paginas
                        FROM bom_analysis
                    """)
                    stats_basicas = dict(cursor.fetchone())
                    
                    # Materiales más utilizados
                    cursor.execute("""
                        SELECT * FROM v_materials_ranking LIMIT 10
                    """)
                    materiales_ranking = [dict(row) for row in cursor.fetchall()]
                    
                    return {
                        "estadisticas_basicas": stats_basicas,
                        "materiales_mas_utilizados": materiales_ranking,
                        "fecha_consulta": datetime.datetime.now().isoformat()
                    }
                    
        except Exception as e:
            print(f"[BOM_DB] ERROR obteniendo estadísticas: {e}")
            return {"error": str(e)}
    
    def eliminar_analisis_bom(self, analysis_id: int) -> bool:
        """Elimina un análisis BOM completo"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM bom_analysis WHERE id = %s", (analysis_id,))
                    eliminados = cursor.rowcount
                    conn.commit()
                    
                    print(f"[BOM_DB] Análisis {analysis_id} eliminado (filas afectadas: {eliminados})")
                    return eliminados > 0
                    
        except Exception as e:
            print(f"[BOM_DB] ERROR eliminando análisis {analysis_id}: {e}")
            return False