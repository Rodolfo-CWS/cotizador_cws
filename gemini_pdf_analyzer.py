# -*- coding: utf-8 -*-
"""
Gemini PDF Analyzer - Sistema de análisis de PDFs para extracción de BOMs
=======================================================================

Implementa la estrategia específica de análisis de PDFs con Gemini:

1. Análisis por página individual del PDF
2. Extracción de tablas de materiales por página (Item ID, cantidad, UDM, descripción, dimensiones, espesor, clasificación)
3. Repetir proceso en cada página
4. Consolidar tablas en tabla master con subtotales dimensionales
5. Clasificar materiales repetidos y generar grand total

Autor: CWS Company
Fecha: 2025-08-29
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import tempfile
from dataclasses import dataclass
import re

try:
    import google.generativeai as genai
    from pdf2image import convert_from_path
    import PyPDF2
    GEMINI_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Gemini dependencies no disponibles: {e}")
    GEMINI_AVAILABLE = False

# Configuración específica para Windows - Poppler path
POPPLER_PATH = None
if os.name == 'nt':  # Windows
    # Buscar poppler en ubicaciones comunes de Windows
    possible_poppler_paths = [
        r"C:\Users\SDS\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-24.08.0\Library\bin",
        r"C:\Program Files\poppler\bin",
        r"C:\poppler\bin",
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-24.08.0\Library\bin")
    ]
    
    for path in possible_poppler_paths:
        if os.path.exists(os.path.join(path, "pdftoppm.exe")):
            POPPLER_PATH = path
            print(f"[POPPLER] Encontrado en: {POPPLER_PATH}")
            break
    
    if not POPPLER_PATH:
        print("[POPPLER] WARNING: No se encontró poppler en ubicaciones conocidas")

def normalize_path(path: str) -> str:
    """Normaliza rutas de archivo para diferentes sistemas operativos"""
    if not path:
        return ""
    
    # Convertir a Path object para normalización automática
    normalized = Path(path).resolve()
    
    # En Windows, asegurar que usamos barras invertidas
    if os.name == 'nt':
        return str(normalized).replace('/', '\\')
    else:
        return str(normalized)

def validar_pdf_antes_analisis(ruta_pdf: str) -> Dict[str, Any]:
    """
    Valida un PDF antes del análisis BOM
    
    Returns:
        Dict con información de validación: 
        {
            "valido": bool,
            "errores": List[str],
            "advertencias": List[str],
            "info": Dict
        }
    """
    resultado = {
        "valido": False,
        "errores": [],
        "advertencias": [],
        "info": {}
    }
    
    try:
        # 1. Verificar que el archivo existe
        ruta_normalizada = normalize_path(ruta_pdf)
        if not os.path.exists(ruta_normalizada):
            resultado["errores"].append(f"Archivo no encontrado: {ruta_normalizada}")
            return resultado
        
        # 2. Verificar que es un archivo (no directorio)
        if not os.path.isfile(ruta_normalizada):
            resultado["errores"].append(f"La ruta no es un archivo válido: {ruta_normalizada}")
            return resultado
        
        # 3. Verificar extensión
        if not ruta_normalizada.lower().endswith('.pdf'):
            resultado["errores"].append(f"El archivo no tiene extensión PDF: {ruta_normalizada}")
            return resultado
        
        # 4. Verificar tamaño del archivo
        tamano_bytes = os.path.getsize(ruta_normalizada)
        tamano_mb = tamano_bytes / (1024 * 1024)
        resultado["info"]["tamano_mb"] = round(tamano_mb, 2)
        
        if tamano_bytes == 0:
            resultado["errores"].append("El archivo PDF está vacío")
            return resultado
        
        if tamano_mb > 100:  # Límite de 100MB
            resultado["advertencias"].append(f"Archivo muy grande ({tamano_mb:.1f}MB), el análisis puede ser lento")
        
        # 5. Verificar que se puede abrir con PyPDF2
        try:
            with open(ruta_normalizada, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_paginas = len(reader.pages)
                resultado["info"]["num_paginas"] = num_paginas
                
                if num_paginas == 0:
                    resultado["errores"].append("El PDF no contiene páginas")
                    return resultado
                
                if num_paginas > 50:
                    resultado["advertencias"].append(f"PDF con muchas páginas ({num_paginas}), considere dividirlo")
                
                # 6. Verificar que al menos una página tiene contenido
                tiene_contenido = False
                for i, page in enumerate(reader.pages[:3]):  # Revisar solo las primeras 3 páginas
                    try:
                        texto = page.extract_text()
                        if texto and len(texto.strip()) > 50:  # Al menos 50 caracteres
                            tiene_contenido = True
                            break
                    except:
                        continue
                
                if not tiene_contenido:
                    resultado["advertencias"].append("No se detectó texto extraíble en las primeras páginas")
                
                resultado["info"]["tiene_texto_extraible"] = tiene_contenido
                
        except Exception as e:
            resultado["errores"].append(f"Error leyendo PDF: {str(e)}")
            return resultado
        
        # 7. Verificar permisos de lectura
        if not os.access(ruta_normalizada, os.R_OK):
            resultado["errores"].append("Sin permisos de lectura para el archivo")
            return resultado
        
        # Si llegamos aquí, el PDF es válido
        resultado["valido"] = len(resultado["errores"]) == 0
        resultado["info"]["ruta_normalizada"] = ruta_normalizada
        
        return resultado
        
    except Exception as e:
        resultado["errores"].append(f"Error en validación: {str(e)}")
        return resultado

@dataclass
class BOMItem:
    """Representa un item individual del BOM"""
    item_id: str
    cantidad: float
    udm: str  # Unidad de medida
    descripcion: str
    largo: Optional[float] = None
    ancho: Optional[float] = None
    espesor: Optional[float] = None
    clasificacion: str = ""
    pagina_origen: int = 1
    
    def get_key_consolidacion(self) -> str:
        """Genera clave única para consolidación de materiales repetidos"""
        return f"{self.item_id}_{self.descripcion}_{self.largo}_{self.ancho}_{self.espesor}".lower()

@dataclass
class PaginaBOM:
    """Representa los materiales encontrados en una página específica"""
    numero_pagina: int
    items: List[BOMItem]
    tabla_detectada: bool
    contenido_texto: str = ""

class GeminiPDFAnalyzer:
    """Analizador de PDFs usando Gemini para extracción de BOMs"""
    
    def __init__(self, api_key: str = None):
        """
        Inicializa el analizador Gemini
        
        Args:
            api_key: API key de Google Gemini. Si no se proporciona, usa variable de entorno
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("Dependencias de Gemini no están disponibles. Instalar: pip install google-generativeai pdf2image PyPDF2")
        
        # Configurar API key
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("API key de Gemini requerida. Configurar GOOGLE_GEMINI_API_KEY en variables de entorno")
        
        # Configurar Gemini
        genai.configure(api_key=self.api_key)
        # Usar modelos actualizados y más eficientes
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')  # Modelo rápido para análisis de imágenes
        self.model_text = genai.GenerativeModel('gemini-1.5-flash-latest')    # Modelo rápido para procesamiento
        
        print(f"[GEMINI] Analizador inicializado correctamente")
        print(f"[GEMINI] Modelo vision: gemini-1.5-flash-latest")
        print(f"[GEMINI] Modelo texto: gemini-1.5-flash-latest")
    
    def analizar_pdf_completo(self, ruta_pdf: str, numero_cotizacion: str = None) -> Dict:
        """
        Ejecuta el proceso completo de análisis de PDF siguiendo los 5 pasos específicos
        
        Args:
            ruta_pdf: Ruta al archivo PDF a analizar
            numero_cotizacion: Número de cotización (opcional)
            
        Returns:
            Dict con resultados completos del análisis BOM
        """
        try:
            print(f"[GEMINI_ANALYSIS] === INICIANDO ANÁLISIS COMPLETO DE PDF ===")
            print(f"[GEMINI_ANALYSIS] PDF Original: {ruta_pdf}")
            print(f"[GEMINI_ANALYSIS] Cotización: {numero_cotizacion}")
            
            # VALIDACIÓN PREVIA DEL PDF
            print(f"[VALIDACIÓN] Validando PDF antes del análisis...")
            validacion = validar_pdf_antes_analisis(ruta_pdf)
            
            if not validacion["valido"]:
                print(f"[VALIDACIÓN] FALLÓ: {validacion['errores']}")
                resultado["errores"].extend(validacion["errores"])
                resultado["errores"].extend(validacion["advertencias"])
                return resultado
            
            # Usar la ruta normalizada de la validación
            ruta_pdf = validacion["info"]["ruta_normalizada"]
            print(f"[VALIDACIÓN] EXITOSA: {validacion['info']}")
            
            if validacion["advertencias"]:
                print(f"[VALIDACIÓN] Advertencias: {validacion['advertencias']}")
            
            print(f"[GEMINI_ANALYSIS] PDF Normalizado: {ruta_pdf}")
            
            resultado = {
                "numero_cotizacion": numero_cotizacion,
                "ruta_pdf": ruta_pdf,
                "fecha_analisis": datetime.datetime.now().isoformat(),
                "paso_1_paginas": [],
                "paso_2_tablas_por_pagina": [],
                "paso_3_consolidacion_completa": True,
                "paso_4_tabla_master": [],
                "paso_5_grand_total": {},
                "estadisticas": {},
                "errores": [],
                "exito": False
            }
            
            # PASO 1: Análisis por página individual del PDF
            print(f"[PASO_1] Analizando páginas individuales...")
            try:
                paginas_bom = self._paso_1_analizar_paginas_individuales(ruta_pdf)
            except Exception as e:
                print(f"[PASO_1] Fallo principal, intentando fallback: {e}")
                if "Invalid argument" in str(e) or "[Errno 22]" in str(e):
                    print("[PASO_1] Usando sistema fallback (solo texto) debido a problemas con pdf2image")
                    paginas_bom = self._paso_1_analizar_paginas_individuales_fallback(ruta_pdf)
                else:
                    raise  # Re-lanzar si no es el error conocido
            resultado["paso_1_paginas"] = [
                {
                    "numero_pagina": p.numero_pagina,
                    "items_encontrados": len(p.items),
                    "tabla_detectada": p.tabla_detectada
                } for p in paginas_bom
            ]
            
            # PASO 2: Extracción de tablas por página (ya incluido en paso 1)
            print(f"[PASO_2] Procesando tablas por página...")
            resultado["paso_2_tablas_por_pagina"] = [
                {
                    "pagina": p.numero_pagina,
                    "items": [
                        {
                            "item_id": item.item_id,
                            "cantidad": item.cantidad,
                            "udm": item.udm,
                            "descripcion": item.descripcion,
                            "largo": item.largo,
                            "ancho": item.ancho,
                            "espesor": item.espesor,
                            "clasificacion": item.clasificacion
                        } for item in p.items
                    ]
                } for p in paginas_bom
            ]
            
            # PASO 3: Verificar que se procesaron todas las páginas
            total_paginas = len(paginas_bom)
            print(f"[PASO_3] Procesamiento completo: {total_paginas} páginas analizadas")
            
            # PASO 4: Consolidar tablas en tabla master con subtotales dimensionales
            print(f"[PASO_4] Consolidando tabla master...")
            tabla_master = self._paso_4_consolidar_tabla_master(paginas_bom)
            resultado["paso_4_tabla_master"] = tabla_master
            
            # PASO 5: Identificar materiales repetidos y generar grand total
            print(f"[PASO_5] Generando grand total...")
            grand_total = self._paso_5_generar_grand_total(tabla_master)
            resultado["paso_5_grand_total"] = grand_total
            
            # Estadísticas finales
            total_items_unicos = len(tabla_master)
            total_items_consolidados = len(grand_total.get("materiales_consolidados", []))
            
            resultado["estadisticas"] = {
                "total_paginas_analizadas": total_paginas,
                "total_items_encontrados": sum(len(p.items) for p in paginas_bom),
                "total_items_unicos": total_items_unicos,
                "total_items_consolidados": total_items_consolidados,
                "paginas_con_tablas": sum(1 for p in paginas_bom if p.tabla_detectada),
                "tiempo_procesamiento": "completo"
            }
            
            resultado["exito"] = True
            print(f"[GEMINI_ANALYSIS] === ANÁLISIS COMPLETADO EXITOSAMENTE ===")
            print(f"[GEMINI_ANALYSIS] Items encontrados: {resultado['estadisticas']['total_items_encontrados']}")
            print(f"[GEMINI_ANALYSIS] Items únicos: {total_items_unicos}")
            print(f"[GEMINI_ANALYSIS] Items consolidados: {total_items_consolidados}")
            
            return resultado
            
        except Exception as e:
            print(f"[GEMINI_ANALYSIS] ERROR en análisis completo: {e}")
            resultado["errores"].append(f"Error general: {str(e)}")
            resultado["exito"] = False
            return resultado
    
    def _paso_1_analizar_paginas_individuales_fallback(self, ruta_pdf: str) -> List[PaginaBOM]:
        """
        FALLBACK: Análisis usando solo texto extraído del PDF (sin conversión a imagen)
        Se usa cuando pdf2image falla en Windows
        """
        print(f"[PASO_1_FALLBACK] Iniciando análisis usando solo extracción de texto")
        paginas_bom = []
        
        try:
            # Normalizar ruta del PDF
            ruta_pdf_normalizada = normalize_path(ruta_pdf)
            print(f"[PASO_1_FALLBACK] Procesando PDF: {ruta_pdf_normalizada}")
            
            with open(ruta_pdf_normalizada, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                print(f"[PASO_1_FALLBACK] PDF cargado: {len(reader.pages)} páginas")
                
                for num_pagina, page in enumerate(reader.pages, 1):
                    print(f"[PASO_1_FALLBACK] Procesando página {num_pagina}/{len(reader.pages)}")
                    
                    try:
                        # Extraer texto de la página
                        texto_pagina = page.extract_text()
                        
                        if texto_pagina.strip():
                            print(f"[PASO_1_FALLBACK] Página {num_pagina}: {len(texto_pagina)} caracteres extraídos")
                            # Analizar texto con Gemini (modo texto)
                            items_pagina = self._analizar_texto_pagina(texto_pagina, num_pagina)
                        else:
                            print(f"[PASO_1_FALLBACK] Página {num_pagina}: Sin texto extraíble")
                            items_pagina = []
                        
                        # Crear objeto PaginaBOM
                        pagina_bom = PaginaBOM(
                            numero_pagina=num_pagina,
                            items=items_pagina,
                            tabla_detectada=len(items_pagina) > 0
                        )
                        paginas_bom.append(pagina_bom)
                        
                    except Exception as e:
                        print(f"[PASO_1_FALLBACK] ERROR procesando página {num_pagina}: {e}")
                        # Crear página vacía
                        pagina_bom = PaginaBOM(
                            numero_pagina=num_pagina,
                            items=[],
                            tabla_detectada=False
                        )
                        paginas_bom.append(pagina_bom)
                
                print(f"[PASO_1_FALLBACK] Análisis completado: {len(paginas_bom)} páginas procesadas")
                return paginas_bom
                
        except Exception as e:
            print(f"[PASO_1_FALLBACK] ERROR en análisis fallback: {e}")
            return []

    def _paso_1_analizar_paginas_individuales(self, ruta_pdf: str) -> List[PaginaBOM]:
        """
        PASO 1: Análisis por página individual del PDF
        Convierte cada página a imagen y la analiza con Gemini
        """
        print(f"[PASO_1] Iniciando análisis por páginas individuales")
        paginas_bom = []
        
        try:
            # Normalizar ruta del PDF
            ruta_pdf_normalizada = normalize_path(ruta_pdf)
            print(f"[PASO_1] Ruta PDF normalizada: {ruta_pdf_normalizada}")
            
            # Convertir PDF a imágenes (una por página)
            print(f"[PASO_1] Convirtiendo PDF a imágenes...")
            convert_kwargs = {"dpi": 200}
            
            # Agregar poppler_path si está disponible (Windows)
            if POPPLER_PATH:
                convert_kwargs["poppler_path"] = POPPLER_PATH
                print(f"[PASO_1] Usando poppler desde: {POPPLER_PATH}")
            
            imagenes_paginas = convert_from_path(ruta_pdf_normalizada, **convert_kwargs)
            print(f"[PASO_1] PDF convertido: {len(imagenes_paginas)} páginas")
            
            # Analizar cada página
            for num_pagina, imagen in enumerate(imagenes_paginas, 1):
                print(f"[PASO_1] Analizando página {num_pagina}/{len(imagenes_paginas)}")
                
                try:
                    # Guardar imagen temporalmente
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                        imagen.save(temp_img.name, 'PNG')
                        temp_img_path = temp_img.name
                    
                    # Analizar página con Gemini
                    items_pagina = self._analizar_pagina_individual(temp_img_path, num_pagina)
                    
                    # Crear objeto PaginaBOM
                    pagina_bom = PaginaBOM(
                        numero_pagina=num_pagina,
                        items=items_pagina,
                        tabla_detectada=len(items_pagina) > 0
                    )
                    
                    paginas_bom.append(pagina_bom)
                    print(f"[PASO_1] Página {num_pagina}: {len(items_pagina)} items encontrados")
                    
                    # Limpiar archivo temporal
                    try:
                        os.unlink(temp_img_path)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"[PASO_1] ERROR analizando página {num_pagina}: {e}")
                    # Crear página vacía en caso de error
                    pagina_bom = PaginaBOM(
                        numero_pagina=num_pagina,
                        items=[],
                        tabla_detectada=False
                    )
                    paginas_bom.append(pagina_bom)
            
            print(f"[PASO_1] Análisis individual completado: {len(paginas_bom)} páginas procesadas")
            return paginas_bom
            
        except Exception as e:
            error_msg = str(e)
            print(f"[PASO_1] ERROR en análisis por páginas: {error_msg}")
            
            # Mensajes de error específicos para Windows
            if "Invalid argument" in error_msg or "[Errno 22]" in error_msg:
                print("[PASO_1] ERROR WINDOWS: Problema con rutas de archivos o poppler")
                print(f"[PASO_1] Verifica que poppler esté instalado correctamente")
                print(f"[PASO_1] Ruta poppler configurada: {POPPLER_PATH}")
                if POPPLER_PATH:
                    print(f"[PASO_1] Verificando pdftoppm.exe: {os.path.exists(os.path.join(POPPLER_PATH, 'pdftoppm.exe'))}")
                
            elif "Permission denied" in error_msg:
                print("[PASO_1] ERROR: Permisos insuficientes para acceder al archivo PDF")
                
            elif "No such file or directory" in error_msg:
                print(f"[PASO_1] ERROR: Archivo PDF no encontrado en la ruta especificada")
                
            return []
    
    def _analizar_texto_pagina(self, texto_pagina: str, numero_pagina: int) -> List[BOMItem]:
        """
        Analiza texto extraído del PDF usando Gemini (modo texto, sin imagen)
        Fallback cuando pdf2image no funciona
        """
        try:
            # Prompt especializado para análisis de texto de BOM
            prompt = f"""
Eres un experto en análisis de planos de ingeniería estructural y Bill of Materials (BOM).

Analiza el siguiente texto extraído de la página {numero_pagina} de un plano de ingeniería:

TEXTO DE LA PÁGINA:
{texto_pagina}

Tu tarea es identificar y extraer información de materiales estructurales. Busca:

1. PERFILES ESTRUCTURALES:
   - IPR, PTR, HSS, canales (C), ángulos (L), vigas I
   - Ejemplos: "IPR 6x4x3/8", "PTR 4x4x1/4", "HSS 8x8x1/2"

2. PLACAS Y LÁMINAS:
   - Placas (PL): "PL 1/2 x 8 x 10"
   - Láminas con espesores

3. CANTIDADES Y DIMENSIONES:
   - Números que indican cantidades
   - Longitudes en pies/pulgadas: "12'-0", "10'-6", "8'-0"
   - Medidas: "x 8 x 10", "@ 12'-0 LONG"

FORMATO DE SALIDA - Devuelve SOLO JSON válido:
{{
  "items": [
    {{
      "item_id": "número de item o identificador",
      "cantidad": número_decimal,
      "udm": "pcs|lbs|ft|EA|etc",
      "descripcion": "descripción completa del material",
      "largo": número_en_mm_si_aplica,
      "ancho": número_en_mm_si_aplica,
      "espesor": número_en_mm_si_aplica,
      "clasificacion": "perfil_estructural|placa|lamina|conexion|sin_clasificar"
    }}
  ]
}}

CONVERSIONES:
- Pies a mm: multiplica por 304.8
- Pulgadas a mm: multiplica por 25.4
- Fracciones: 1/2=12.7mm, 3/8=9.525mm, 1/4=6.35mm, 5/8=15.875mm

Si no encuentras materiales estructurales, devuelve: {{"items": []}}
"""

            # Llamar a Gemini con el texto
            response = self.model.generate_content(prompt)
            respuesta_texto = response.text.strip()
            
            # Limpiar respuesta
            respuesta_texto = respuesta_texto.replace('```json', '').replace('```', '').strip()
            
            try:
                data = json.loads(respuesta_texto)
                items = []
                
                for item_data in data.get("items", []):
                    try:
                        item = BOMItem(
                            item_id=str(item_data.get("item_id", f"T{numero_pagina}-{len(items)+1}")),
                            cantidad=float(item_data.get("cantidad", 1.0)),
                            udm=str(item_data.get("udm", "EA")),
                            descripcion=str(item_data.get("descripcion", "")),
                            largo=float(item_data["largo"]) if item_data.get("largo") else None,
                            ancho=float(item_data["ancho"]) if item_data.get("ancho") else None,
                            espesor=float(item_data["espesor"]) if item_data.get("espesor") else None,
                            clasificacion=str(item_data.get("clasificacion", "sin_clasificar")),
                            pagina_origen=numero_pagina
                        )
                        
                        # Solo agregar si tiene descripción válida
                        if item.descripcion and item.descripcion.strip():
                            items.append(item)
                            
                    except (ValueError, KeyError) as e:
                        print(f"[TEXTO] ERROR procesando item en página {numero_pagina}: {e}")
                        continue
                
                print(f"[TEXTO] Página {numero_pagina}: {len(items)} items extraídos del texto")
                return items
                
            except json.JSONDecodeError as e:
                print(f"[TEXTO] ERROR decodificando JSON en página {numero_pagina}: {e}")
                print(f"[TEXTO] Respuesta: {respuesta_texto[:200]}...")
                return []
                
        except Exception as e:
            print(f"[TEXTO] ERROR analizando texto de página {numero_pagina}: {e}")
            return []
    
    def _analizar_pagina_individual(self, ruta_imagen: str, numero_pagina: int) -> List[BOMItem]:
        """
        Analiza una página individual usando Gemini Vision
        """
        try:
            # Prompt específico y mejorado para análisis de BOM de planos de ingeniería
            prompt = """
            Analiza esta imagen de un plano de ingeniería o documento técnico que puede contener información de materiales y componentes estructurales.

            Busca TODA la información de materiales presente en la imagen, incluyendo:

            📋 TABLAS DE MATERIALES:
            - Listas de materiales estructurales
            - Especificaciones de perfiles
            - Cantidades de componentes
            - Dimensiones y medidas

            🔍 ELEMENTOS ESTRUCTURALES EN DIBUJOS:
            - Perfiles metálicos (IPR, PTR, canales, etc.)
            - Placas y láminas
            - Pernos, soldaduras, conexiones
            - Cualquier anotación con dimensiones

            📏 INFORMACIÓN A EXTRAER:
            1. Descripción detallada del material (ej: "IPR 6x4x3/8", "PTR 2x2x1/4", "Placa 1/2")
            2. Cantidad exacta
            3. Unidad de medida (pcs, ft, lb, kg, etc.)
            4. Dimensiones específicas (largo, ancho, espesor)
            5. Tipo/clasificación de material
            6. Cualquier código o referencia

            INSTRUCCIONES CRÍTICAS:
            - Examina TODA la imagen cuidadosamente
            - Incluye información tanto de tablas como de anotaciones en dibujos
            - Si ves medidas como "2'-6", "10.5ft", "1/2 inch", inclúyelas
            - Para perfiles como "IPR 6x4x3/8", extrae dimensiones: altura=6, ancho=4, espesor=3/8
            - Si no encuentras información específica, responde tabla_detectada: false
            - NO inventes datos, solo extrae lo que realmente ves

            Formato JSON EXACTO:
            {
                "tabla_detectada": true/false,
                "items": [
                    {
                        "item_id": "referencia o código si existe",
                        "cantidad": 1.0,
                        "udm": "pcs/ft/lb/kg/etc",
                        "descripcion": "descripción completa del material",
                        "largo": 120.5,
                        "ancho": 60.0,
                        "espesor": 6.0,
                        "clasificacion": "perfil/placa/conexion/etc"
                    }
                ]
            }

            EJEMPLO para "4 IPR 6x4x3/8 @ 12'-0 LONG":
            {
                "tabla_detectada": true,
                "items": [
                    {
                        "item_id": "IPR-01",
                        "cantidad": 4.0,
                        "udm": "pcs",
                        "descripcion": "IPR 6x4x3/8 @ 12'-0 LONG",
                        "largo": 144.0,
                        "ancho": 6.0,
                        "espesor": 0.375,
                        "clasificacion": "perfil estructural"
                    }
                ]
            }
            """
            
            # Cargar imagen y enviar a Gemini
            with open(ruta_imagen, 'rb') as img_file:
                imagen_data = img_file.read()
            
            # Crear objeto de imagen para Gemini
            imagen_gemini = {
                'mime_type': 'image/png',
                'data': imagen_data
            }
            
            # Enviar solicitud a Gemini con retry
            max_retries = 2
            for retry in range(max_retries):
                try:
                    response = self.model.generate_content([prompt, imagen_gemini])
                    
                    # Procesar respuesta
                    if response and response.text:
                        # Limpiar respuesta y extraer JSON
                        respuesta_texto = response.text.strip()
                        print(f"[GEMINI] Página {numero_pagina} - Respuesta: {respuesta_texto[:200]}...")
                        
                        # Buscar JSON en la respuesta
                        json_match = re.search(r'\{.*\}', respuesta_texto, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            try:
                                data = json.loads(json_str)
                                
                                # Convertir a objetos BOMItem
                                items = []
                                if data.get("tabla_detectada", False) and "items" in data:
                                    for item_data in data["items"]:
                                        try:
                                            # Procesar dimensiones con más cuidado
                                            largo = None
                                            ancho = None
                                            espesor = None
                                            
                                            if item_data.get("largo") is not None:
                                                try:
                                                    largo = float(item_data["largo"])
                                                except (ValueError, TypeError):
                                                    largo = None
                                            
                                            if item_data.get("ancho") is not None:
                                                try:
                                                    ancho = float(item_data["ancho"])
                                                except (ValueError, TypeError):
                                                    ancho = None
                                            
                                            if item_data.get("espesor") is not None:
                                                try:
                                                    espesor = float(item_data["espesor"])
                                                except (ValueError, TypeError):
                                                    espesor = None
                                            
                                            item = BOMItem(
                                                item_id=str(item_data.get("item_id", f"ITEM-{numero_pagina}-{len(items)+1}")),
                                                cantidad=float(item_data.get("cantidad", 0)),
                                                udm=str(item_data.get("udm", "pcs")),
                                                descripcion=str(item_data.get("descripcion", "Material no especificado")),
                                                largo=largo,
                                                ancho=ancho,
                                                espesor=espesor,
                                                clasificacion=str(item_data.get("clasificacion", "sin clasificar")),
                                                pagina_origen=numero_pagina
                                            )
                                            
                                            # Solo agregar si tiene información útil
                                            if item.descripcion and item.descripcion != "Material no especificado":
                                                items.append(item)
                                            
                                        except Exception as e:
                                            print(f"[GEMINI] ERROR procesando item en página {numero_pagina}: {e}")
                                            continue
                                
                                print(f"[GEMINI] Página {numero_pagina}: {len(items)} items válidos extraídos")
                                return items
                                
                            except json.JSONDecodeError as e:
                                print(f"[GEMINI] ERROR decodificando JSON en página {numero_pagina}: {e}")
                                print(f"[GEMINI] Respuesta recibida: {respuesta_texto[:200]}...")
                                if retry == max_retries - 1:
                                    return []
                                else:
                                    print(f"[GEMINI] Reintentando página {numero_pagina}...")
                                    continue
                        else:
                            print(f"[GEMINI] No se encontró JSON válido en respuesta de página {numero_pagina}")
                            if retry == max_retries - 1:
                                return []
                            else:
                                continue
                    else:
                        print(f"[GEMINI] No se recibió respuesta para página {numero_pagina}")
                        if retry == max_retries - 1:
                            return []
                        else:
                            continue
                            
                except Exception as gemini_error:
                    print(f"[GEMINI] ERROR en llamada a Gemini para página {numero_pagina} (intento {retry+1}): {gemini_error}")
                    if "quota" in str(gemini_error).lower() or "429" in str(gemini_error):
                        print(f"[GEMINI] Límite de cuota alcanzado - esperando antes de reintentar...")
                        import time
                        time.sleep(10)
                    
                    if retry == max_retries - 1:
                        print(f"[GEMINI] Máximo número de reintentos alcanzado para página {numero_pagina}")
                        return []
                    else:
                        continue
                
        except Exception as e:
            print(f"[GEMINI] ERROR analizando página {numero_pagina}: {e}")
            return []
    
    def _paso_4_consolidar_tabla_master(self, paginas_bom: List[PaginaBOM]) -> List[Dict]:
        """
        PASO 4: Consolidar las tablas de cada página en una tabla master
        Genera subtotales dimensionales de cada item
        """
        print(f"[PASO_4] Iniciando consolidación de tabla master")
        
        # Recopilar todos los items de todas las páginas
        todos_items = []
        for pagina in paginas_bom:
            todos_items.extend(pagina.items)
        
        print(f"[PASO_4] Total items encontrados en todas las páginas: {len(todos_items)}")
        
        # Crear tabla master con subtotales por ítem único
        tabla_master = []
        items_procesados = set()
        
        for item in todos_items:
            key = item.get_key_consolidacion()
            
            if key not in items_procesados:
                # Buscar todos los items similares
                items_similares = [i for i in todos_items if i.get_key_consolidacion() == key]
                
                # Calcular subtotales
                cantidad_total = sum(i.cantidad for i in items_similares)
                paginas_origen = list(set(i.pagina_origen for i in items_similares))
                
                # Calcular subtotales dimensionales
                subtotal_dimensional = {}
                if item.largo and item.ancho:
                    area_unitaria = item.largo * item.ancho
                    area_total = area_unitaria * cantidad_total
                    subtotal_dimensional = {
                        "area_unitaria_mm2": area_unitaria,
                        "area_total_mm2": area_total,
                        "largo_mm": item.largo,
                        "ancho_mm": item.ancho
                    }
                    
                    if item.espesor:
                        volumen_unitario = area_unitaria * item.espesor
                        volumen_total = volumen_unitario * cantidad_total
                        subtotal_dimensional.update({
                            "espesor_mm": item.espesor,
                            "volumen_unitario_mm3": volumen_unitario,
                            "volumen_total_mm3": volumen_total
                        })
                
                # Crear registro master
                registro_master = {
                    "item_id": item.item_id,
                    "descripcion": item.descripcion,
                    "cantidad_total": cantidad_total,
                    "udm": item.udm,
                    "clasificacion": item.clasificacion,
                    "largo": item.largo,
                    "ancho": item.ancho,
                    "espesor": item.espesor,
                    "subtotales_dimensionales": subtotal_dimensional,
                    "paginas_origen": paginas_origen,
                    "ocurrencias": len(items_similares)
                }
                
                tabla_master.append(registro_master)
                items_procesados.add(key)
        
        print(f"[PASO_4] Tabla master consolidada: {len(tabla_master)} items únicos")
        return tabla_master
    
    def _paso_5_generar_grand_total(self, tabla_master: List[Dict]) -> Dict:
        """
        PASO 5: Clasificar e identificar materiales repetidos para generar grand total
        """
        print(f"[PASO_5] Generando grand total y clasificación final")
        
        # Clasificar materiales por tipo
        clasificacion_materiales = {}
        materiales_consolidados = []
        
        # Totales generales
        totales = {
            "total_items_unicos": len(tabla_master),
            "total_cantidad_items": 0,
            "total_area_mm2": 0,
            "total_volumen_mm3": 0
        }
        
        for item in tabla_master:
            # Sumar totales generales
            totales["total_cantidad_items"] += item["cantidad_total"]
            
            if "subtotales_dimensionales" in item:
                subtotales = item["subtotales_dimensionales"]
                if "area_total_mm2" in subtotales:
                    totales["total_area_mm2"] += subtotales["area_total_mm2"]
                if "volumen_total_mm3" in subtotales:
                    totales["total_volumen_total_mm3"] += subtotales["volumen_total_mm3"]
            
            # Clasificar por tipo de material
            clasificacion = item.get("clasificacion", "Sin clasificar")
            if clasificacion not in clasificacion_materiales:
                clasificacion_materiales[clasificacion] = {
                    "items": [],
                    "total_cantidad": 0,
                    "total_area": 0,
                    "total_volumen": 0
                }
            
            clasificacion_materiales[clasificacion]["items"].append(item)
            clasificacion_materiales[clasificacion]["total_cantidad"] += item["cantidad_total"]
            
            if "subtotales_dimensionales" in item:
                subtotales = item["subtotales_dimensionales"]
                if "area_total_mm2" in subtotales:
                    clasificacion_materiales[clasificacion]["total_area"] += subtotales["area_total_mm2"]
                if "volumen_total_mm3" in subtotales:
                    clasificacion_materiales[clasificacion]["total_volumen"] += subtotales["volumen_total_mm3"]
            
            # Agregar a materiales consolidados
            material_consolidado = {
                **item,
                "consolidado": item["ocurrencias"] > 1,
                "total_final": item["cantidad_total"]
            }
            materiales_consolidados.append(material_consolidado)
        
        # Identificar materiales más repetidos
        materiales_repetidos = [item for item in tabla_master if item["ocurrencias"] > 1]
        materiales_repetidos.sort(key=lambda x: x["ocurrencias"], reverse=True)
        
        grand_total = {
            "totales_generales": totales,
            "clasificacion_por_tipo": clasificacion_materiales,
            "materiales_consolidados": materiales_consolidados,
            "materiales_mas_repetidos": materiales_repetidos[:10],  # Top 10
            "resumen": {
                "total_clasificaciones": len(clasificacion_materiales),
                "materiales_repetidos": len(materiales_repetidos),
                "material_mas_repetido": materiales_repetidos[0] if materiales_repetidos else None
            }
        }
        
        print(f"[PASO_5] Grand total generado:")
        print(f"  - Total items: {totales['total_items_unicos']}")
        print(f"  - Total cantidad: {totales['total_cantidad_items']}")
        print(f"  - Materiales repetidos: {len(materiales_repetidos)}")
        print(f"  - Clasificaciones: {len(clasificacion_materiales)}")
        
        return grand_total
    
    def obtener_estadisticas_rapidas(self, ruta_pdf: str) -> Dict:
        """
        Obtiene estadísticas rápidas del PDF sin análisis completo
        """
        try:
            # Información básica del PDF
            with open(ruta_pdf, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_paginas = len(pdf_reader.pages)
                
                # Extraer texto de primera página para análisis rápido
                primera_pagina_texto = ""
                if num_paginas > 0:
                    primera_pagina_texto = pdf_reader.pages[0].extract_text()[:1000]
            
            return {
                "numero_paginas": num_paginas,
                "tamaño_archivo": os.path.getsize(ruta_pdf),
                "preview_texto": primera_pagina_texto,
                "analizable": num_paginas > 0,
                "gemini_disponible": GEMINI_AVAILABLE
            }
            
        except Exception as e:
            return {
                "error": f"Error obteniendo estadísticas: {str(e)}",
                "analizable": False,
                "gemini_disponible": GEMINI_AVAILABLE
            }