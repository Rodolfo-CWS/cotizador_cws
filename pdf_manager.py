"""
PDF Manager - Sistema de gestión de PDFs para cotizaciones CWS
Maneja almacenamiento en Google Drive y índice en MongoDB
"""

import os
import json
import datetime
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Tuple

class PDFManager:
    def __init__(self, database_manager, base_pdf_path: str = None):
        """
        Inicializa el gestor de PDFs
        
        Args:
            database_manager: Instancia de DatabaseManager
            base_pdf_path: Ruta base para almacenar PDFs (Google Drive)
        """
        self.db_manager = database_manager
        
        # Configurar rutas de PDFs
        if base_pdf_path:
            self.base_pdf_path = Path(base_pdf_path)
        else:
            # Intentar detectar Google Drive automáticamente
            self.base_pdf_path = self._detectar_google_drive()
        
        # Crear estructura de carpetas
        self.nuevas_path = self.base_pdf_path / "nuevas"
        self.antiguas_path = self.base_pdf_path / "antiguas"
        
        # Crear carpetas si no existen
        self._crear_estructura_carpetas()
        
        # Colección para índice de PDFs
        self._inicializar_coleccion()
        
        print(f"PDF Manager inicializado:")
        print(f"  Ruta base: {self.base_pdf_path}")
        print(f"  PDFs nuevos: {self.nuevas_path}")
        print(f"  PDFs antiguos: {self.antiguas_path}")
    
    def _inicializar_coleccion(self):
        """Inicializa la colección de PDFs si MongoDB está disponible"""
        if not self.db_manager.modo_offline:
            self.pdf_collection = self.db_manager.db["pdf_index"]
            self._crear_indices_pdf()
            print("PDF Collection inicializada con MongoDB")
        else:
            self.pdf_collection = None
            print("PDF Manager en modo offline - colección no disponible")
    
    def _verificar_conexion_mongodb(self):
        """Verifica conexión MongoDB - no intenta reconectar para evitar errores"""
        # Simplemente verificar el estado actual
        if self.db_manager.modo_offline:
            print("MongoDB en modo offline - usando búsqueda offline")
            return False
        else:
            # Verificar que tengamos colección inicializada
            if not hasattr(self, 'pdf_collection') or not self.pdf_collection:
                self._inicializar_coleccion()
            return True
    
    def _detectar_google_drive(self) -> Path:
        """Detecta automáticamente la ruta de Google Drive"""
        usuario = os.getenv('USERNAME') or os.getenv('USER')
        
        # Verificar si estamos en un entorno en la nube (Render, Heroku, etc.)
        es_nube = os.getenv('RENDER') or os.getenv('DYNO') or os.getenv('PORT')
        
        if es_nube:
            # En la nube, usar carpeta local temporal
            print("Entorno en la nube detectado - usando almacenamiento temporal")
            fallback = Path("./pdfs_cotizaciones")
            fallback.mkdir(parents=True, exist_ok=True)
            print(f"Usando ruta para nube: {fallback.absolute()}")
            return fallback
        
        # Rutas comunes de Google Drive en Windows
        rutas_posibles = [
            "G:/Mi unidad/CWS/CWS_Cotizaciones_PDF",  # Nueva ruta preferida
            f"C:/Users/{usuario}/Google Drive/CWS_Cotizaciones_PDF",
            f"C:/Users/{usuario}/GoogleDrive/CWS_Cotizaciones_PDF", 
            "G:/Mi unidad/CWS_Cotizaciones_PDF",
            "G:/My Drive/CWS_Cotizaciones_PDF",
            # Fallback local si no hay Google Drive
            "./pdfs_cotizaciones"
        ]
        
        for ruta in rutas_posibles:
            path_obj = Path(ruta)
            try:
                # Intentar crear la carpeta para verificar permisos
                path_obj.mkdir(parents=True, exist_ok=True)
                print(f"Usando ruta de PDFs: {path_obj.absolute()}")
                return path_obj
            except:
                continue
        
        # Si nada funciona, usar carpeta local
        fallback = Path("./pdfs_cotizaciones")
        fallback.mkdir(parents=True, exist_ok=True)
        print(f"Usando ruta fallback: {fallback.absolute()}")
        return fallback
    
    def _crear_estructura_carpetas(self):
        """Crea la estructura de carpetas necesaria"""
        try:
            self.nuevas_path.mkdir(parents=True, exist_ok=True)
            self.antiguas_path.mkdir(parents=True, exist_ok=True)
            
            # Crear archivo README en cada carpeta
            readme_nuevas = self.nuevas_path / "README.txt"
            if not readme_nuevas.exists():
                readme_nuevas.write_text(
                    "Esta carpeta contiene PDFs generados automáticamente por el sistema CWS.\n"
                    "Estos PDFs tienen desglose completo disponible en la base de datos.\n"
                    f"Generado: {datetime.datetime.now()}"
                )
            
            readme_antiguas = self.antiguas_path / "README.txt"
            if not readme_antiguas.exists():
                readme_antiguas.write_text(
                    "Esta carpeta contiene PDFs históricos importados manualmente.\n"
                    "Estos PDFs solo están disponibles para visualización.\n"
                    f"Configurado: {datetime.datetime.now()}"
                )
                
        except Exception as e:
            print(f"Error creando estructura de carpetas: {e}")
    
    def _crear_indices_pdf(self):
        """Crea índices para optimizar búsquedas de PDFs"""
        try:
            # Índice por número de cotización
            self.pdf_collection.create_index("numero_cotizacion", unique=True)
            # Índice por cliente
            self.pdf_collection.create_index("cliente")
            # Índice por tipo (nueva/antigua)
            self.pdf_collection.create_index("tipo")
            # Índice por fecha
            self.pdf_collection.create_index("fecha")
            # Índice de texto para búsqueda
            self.pdf_collection.create_index([
                ("numero_cotizacion", "text"),
                ("cliente", "text"),
                ("vendedor", "text"),
                ("proyecto", "text")
            ])
        except Exception as e:
            print(f"Advertencia: Error creando índices PDF: {e}")
    
    def almacenar_pdf_nuevo(self, pdf_content: bytes, cotizacion_data: Dict) -> Dict:
        """
        Almacena un PDF recién generado y registra en el índice
        
        Args:
            pdf_content: Contenido binario del PDF
            cotizacion_data: Datos de la cotización
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Extraer información de la cotización
            numero_cotizacion = cotizacion_data.get('numeroCotizacion', 'Sin_Numero')
            datos_generales = cotizacion_data.get('datosGenerales', {})
            
            # Generar nombre de archivo seguro
            nombre_archivo = self._generar_nombre_archivo(numero_cotizacion)
            ruta_completa = self.nuevas_path / nombre_archivo
            
            # Guardar PDF físicamente
            ruta_completa.write_bytes(pdf_content)
            
            # Registrar en índice de MongoDB
            registro_pdf = {
                "nombre_archivo": nombre_archivo,
                "numero_cotizacion": numero_cotizacion,
                "cliente": datos_generales.get('cliente', ''),
                "vendedor": datos_generales.get('vendedor', ''),
                "proyecto": datos_generales.get('proyecto', ''),
                "fecha": datetime.datetime.now().strftime('%Y-%m-%d'),
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                "tipo": "nueva",
                "tiene_desglose": True,
                "ruta_archivo": f"nuevas/{nombre_archivo}",
                "ruta_completa": str(ruta_completa.absolute()),
                "tamaño_bytes": len(pdf_content)
            }
            
            if not self.db_manager.modo_offline:
                # Upsert en MongoDB (actualizar si existe, crear si no)
                self.pdf_collection.replace_one(
                    {"numero_cotizacion": numero_cotizacion},
                    registro_pdf,
                    upsert=True
                )
            
            return {
                "success": True,
                "mensaje": f"PDF almacenado exitosamente: {nombre_archivo}",
                "ruta": str(ruta_completa),
                "nombre_archivo": nombre_archivo,
                "tamaño": len(pdf_content)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error almacenando PDF: {str(e)}"
            }
    
    def _generar_nombre_archivo(self, numero_cotizacion: str) -> str:
        """Genera un nombre de archivo seguro para el PDF"""
        # Limpiar caracteres especiales
        nombre_limpio = numero_cotizacion.replace('/', '_').replace('\\', '_')
        nombre_limpio = ''.join(c for c in nombre_limpio if c.isalnum() or c in '._-')
        
        # Asegurar que no esté vacío
        if not nombre_limpio:
            nombre_limpio = f"Cotizacion_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return f"Cotizacion_{nombre_limpio}.pdf"
    
    def buscar_pdfs(self, query: str, page: int = 1, per_page: int = 20) -> Dict:
        """
        Busca PDFs por término de búsqueda
        
        Args:
            query: Término de búsqueda
            page: Página de resultados
            per_page: Resultados por página
            
        Returns:
            Dict con resultados de la búsqueda
        """
        try:
            print(f"[BUSCAR PDFs] Iniciando búsqueda: '{query}'")
            print(f"[BUSCAR PDFs] Modo offline actual: {self.db_manager.modo_offline}")
            
            # Verificar y reinicializar conexión si es necesario
            if not self._verificar_conexion_mongodb():
                print(f"[BUSCAR PDFs] Usando búsqueda offline")
                return self._buscar_pdfs_offline(query, page, per_page)
            
            # Verificar que pdf_collection existe
            if not self.pdf_collection:
                return self._buscar_pdfs_offline(query, page, per_page)
            
            # Búsqueda en MongoDB
            skip = (page - 1) * per_page
            
            # Filtro de búsqueda (buscar en múltiples campos)
            filtro = {
                "$or": [
                    {"numero_cotizacion": {"$regex": query, "$options": "i"}},
                    {"cliente": {"$regex": query, "$options": "i"}},
                    {"vendedor": {"$regex": query, "$options": "i"}},
                    {"proyecto": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Ejecutar búsqueda
            resultados = list(
                self.pdf_collection
                .find(filtro)
                .sort("timestamp", -1)
                .skip(skip)
                .limit(per_page)
            )
            
            # Contar total
            total = self.pdf_collection.count_documents(filtro)
            
            # Limpiar ObjectId para JSON
            for resultado in resultados:
                if '_id' in resultado:
                    resultado['_id'] = str(resultado['_id'])
            
            return {
                "resultados": resultados,
                "total": total,
                "pagina": page,
                "por_pagina": per_page,
                "total_paginas": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            print(f"[BUSCAR PDFs] ERROR en búsqueda principal: {e}")
            import traceback
            traceback.print_exc()
            # En caso de cualquier error, usar búsqueda offline
            return self._buscar_pdfs_offline(query, page, per_page)
    
    def _buscar_pdfs_offline(self, query: str, page: int, per_page: int) -> Dict:
        """Búsqueda de PDFs en modo offline"""
        print(f"Búsqueda de PDFs en modo offline: '{query}'")
        
        try:
            # Buscar archivos PDF físicamente en las carpetas
            resultados = []
            
            # Buscar en carpeta de PDFs nuevos
            if self.nuevas_path.exists():
                for pdf_file in self.nuevas_path.glob("*.pdf"):
                    nombre = pdf_file.stem
                    if not query or query.lower() in nombre.lower():
                        resultados.append({
                            "numero_cotizacion": nombre,
                            "cliente": "Cliente (modo offline)",
                            "fecha_creacion": "N/A",
                            "ruta_completa": str(pdf_file),
                            "tipo": "nuevo",
                            "tiene_desglose": False
                        })
            
            # Buscar en carpeta de PDFs antiguos  
            if self.antiguas_path.exists():
                for pdf_file in self.antiguas_path.glob("*.pdf"):
                    nombre = pdf_file.stem
                    if not query or query.lower() in nombre.lower():
                        resultados.append({
                            "numero_cotizacion": nombre,
                            "cliente": "Cliente histórico (modo offline)",
                            "fecha_creacion": "N/A", 
                            "ruta_completa": str(pdf_file),
                            "tipo": "historico",
                            "tiene_desglose": False
                        })
            
            # Paginar resultados
            start = (page - 1) * per_page
            end = start + per_page
            resultados_paginados = resultados[start:end]
            
            print(f"Encontrados {len(resultados)} PDFs offline, mostrando {len(resultados_paginados)}")
            
            return {
                "resultados": resultados_paginados,
                "total": len(resultados),
                "pagina": page,
                "por_pagina": per_page,
                "total_paginas": (len(resultados) + per_page - 1) // per_page,
                "modo": "offline"
            }
            
        except Exception as e:
            print(f"Error en búsqueda offline: {e}")
            return {
                "resultados": [],
                "total": 0,
                "pagina": page,
                "por_pagina": per_page,
                "total_paginas": 0,
                "modo": "offline",
                "error": f"Error en búsqueda offline: {str(e)}"
            }
    
    def obtener_pdf(self, numero_cotizacion: str) -> Dict:
        """
        Obtiene información de un PDF específico
        
        Args:
            numero_cotizacion: Número de cotización a buscar
            
        Returns:
            Dict con información del PDF
        """
        try:
            if self.db_manager.modo_offline:
                return {"error": "No disponible en modo offline"}
            
            # Buscar en índice
            registro = self.pdf_collection.find_one({"numero_cotizacion": numero_cotizacion})
            
            if not registro:
                return {"encontrado": False, "mensaje": "PDF no encontrado"}
            
            # Verificar que el archivo existe físicamente
            ruta_completa = Path(registro["ruta_completa"])
            if not ruta_completa.exists():
                return {
                    "encontrado": False, 
                    "error": f"Archivo PDF no encontrado en: {ruta_completa}",
                    "registro": registro
                }
            
            # Limpiar ObjectId
            if '_id' in registro:
                registro['_id'] = str(registro['_id'])
            
            return {
                "encontrado": True,
                "registro": registro,
                "ruta_completa": str(ruta_completa),
                "existe_archivo": True
            }
            
        except Exception as e:
            return {"error": f"Error obteniendo PDF: {str(e)}"}
    
    def importar_pdf_antiguo(self, ruta_pdf: str, metadata: Dict) -> Dict:
        """
        Importa un PDF antiguo al sistema
        
        Args:
            ruta_pdf: Ruta del PDF a importar
            metadata: Metadatos del PDF (numero, cliente, etc.)
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            origen = Path(ruta_pdf)
            if not origen.exists():
                return {"success": False, "error": f"Archivo no encontrado: {ruta_pdf}"}
            
            # Generar nombre y destino
            numero_cotizacion = metadata.get('numero_cotizacion', origen.stem)
            nombre_archivo = self._generar_nombre_archivo(numero_cotizacion)
            destino = self.antiguas_path / nombre_archivo
            
            # Copiar archivo
            shutil.copy2(origen, destino)
            
            # Registrar en índice
            registro_pdf = {
                "nombre_archivo": nombre_archivo,
                "numero_cotizacion": numero_cotizacion,
                "cliente": metadata.get('cliente', ''),
                "vendedor": metadata.get('vendedor', ''),
                "proyecto": metadata.get('proyecto', ''),
                "fecha": metadata.get('fecha', datetime.datetime.now().strftime('%Y-%m-%d')),
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                "tipo": "antigua",
                "tiene_desglose": False,
                "ruta_archivo": f"antiguas/{nombre_archivo}",
                "ruta_completa": str(destino.absolute()),
                "tamaño_bytes": destino.stat().st_size,
                "importado_desde": str(origen.absolute()),
                "fecha_importacion": datetime.datetime.now().isoformat()
            }
            
            if not self.db_manager.modo_offline:
                self.pdf_collection.replace_one(
                    {"numero_cotizacion": numero_cotizacion},
                    registro_pdf,
                    upsert=True
                )
            
            return {
                "success": True,
                "mensaje": f"PDF antiguo importado: {nombre_archivo}",
                "destino": str(destino)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error importando PDF: {str(e)}"
            }
    
    def listar_todos_pdfs(self) -> Dict:
        """Lista todos los PDFs disponibles"""
        try:
            if self.db_manager.modo_offline:
                return {"error": "No disponible en modo offline"}
            
            # Obtener todos los registros
            registros = list(
                self.pdf_collection
                .find()
                .sort("timestamp", -1)
            )
            
            # Limpiar ObjectIds
            for registro in registros:
                if '_id' in registro:
                    registro['_id'] = str(registro['_id'])
            
            # Estadísticas
            total = len(registros)
            nuevos = sum(1 for r in registros if r.get('tipo') == 'nueva')
            antiguos = sum(1 for r in registros if r.get('tipo') == 'antigua')
            
            return {
                "registros": registros,
                "estadisticas": {
                    "total": total,
                    "nuevos": nuevos,
                    "antiguos": antiguos
                }
            }
            
        except Exception as e:
            return {"error": f"Error listando PDFs: {str(e)}"}
    
    def verificar_integridad(self) -> Dict:
        """Verifica la integridad del sistema de PDFs"""
        try:
            if self.db_manager.modo_offline:
                return {"error": "No disponible en modo offline"}
            
            resultados = {
                "registros_verificados": 0,
                "archivos_encontrados": 0,
                "archivos_faltantes": [],
                "registros_huerfanos": [],
                "errores": []
            }
            
            # Verificar registros en base de datos
            registros = list(self.pdf_collection.find())
            resultados["registros_verificados"] = len(registros)
            
            for registro in registros:
                ruta_completa = Path(registro.get("ruta_completa", ""))
                
                if ruta_completa.exists():
                    resultados["archivos_encontrados"] += 1
                else:
                    resultados["archivos_faltantes"].append({
                        "numero": registro.get("numero_cotizacion"),
                        "archivo": registro.get("nombre_archivo"),
                        "ruta": str(ruta_completa)
                    })
            
            return resultados
            
        except Exception as e:
            return {"error": f"Error verificando integridad: {str(e)}"}