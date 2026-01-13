# -*- coding: utf-8 -*-
"""
Parser de Órdenes de Compra - Extracción de datos de PDFs
==========================================================

Extrae información de PDFs de órdenes de compra usando PyPDF2 y pdfplumber.
Tolerante a diferentes formatos de PDF.

Autor: CWS Company
Fecha: 2025-01-13
"""

import re
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    import PyPDF2
    import pdfplumber
    PDF_LIBS_AVAILABLE = True
except ImportError:
    PDF_LIBS_AVAILABLE = False
    print("[OC_PARSER] WARNING: PyPDF2 o pdfplumber no disponibles")


def validar_pdf(file_path: str) -> Tuple[bool, str]:
    """
    Valida que el archivo sea un PDF válido

    Args:
        file_path: Ruta al archivo PDF

    Returns:
        Tupla (es_valido, mensaje_error)
    """
    if not PDF_LIBS_AVAILABLE:
        return False, "Librerías de PDF no disponibles. Instalar PyPDF2 y pdfplumber."

    try:
        # Verificar que existe
        if not os.path.exists(file_path):
            return False, f"Archivo no encontrado: {file_path}"

        # Verificar extensión
        if not file_path.lower().endswith('.pdf'):
            return False, "El archivo no es un PDF"

        # Intentar abrir con PyPDF2
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)

            if num_pages == 0:
                return False, "El PDF no contiene páginas"

        return True, "PDF válido"

    except Exception as e:
        return False, f"Error validando PDF: {str(e)}"


def extraer_texto_completo(pdf_path: str) -> str:
    """
    Extrae todo el texto del PDF

    Args:
        pdf_path: Ruta al archivo PDF

    Returns:
        Texto completo del PDF
    """
    try:
        texto_completo = ""

        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            # Extraer texto de todas las páginas
            for page in reader.pages:
                texto_completo += page.extract_text() + "\n"

        return texto_completo

    except Exception as e:
        print(f"[OC_PARSER] Error extrayendo texto: {e}")
        return ""


def detectar_cliente(texto: str) -> Optional[str]:
    """
    Busca el nombre del cliente usando patrones regex

    Args:
        texto: Texto extraído del PDF

    Returns:
        Nombre del cliente o None
    """
    # Patrones para detectar cliente
    patrones = [
        r"Cliente[:\s]+([A-ZÁ-Ú][A-ZÁ-Úa-zá-ú\s.,]+(?:S\.?A\.?(?:\s+de\s+C\.?V\.?)?)?)",
        r"Empresa[:\s]+([A-ZÁ-Ú][A-ZÁ-Úa-zá-ú\s.,]+(?:S\.?A\.?(?:\s+de\s+C\.?V\.?)?)?)",
        r"Razón\s+Social[:\s]+([A-ZÁ-Ú][A-ZÁ-Úa-zá-ú\s.,]+(?:S\.?A\.?(?:\s+de\s+C\.?V\.?)?)?)",
        r"Comprador[:\s]+([A-ZÁ-Ú][A-ZÁ-Úa-zá-ú\s.,]+(?:S\.?A\.?(?:\s+de\s+C\.?V\.?)?)?)",
        r"A favor de[:\s]+([A-ZÁ-Ú][A-ZÁ-Úa-zá-ú\s.,]+(?:S\.?A\.?(?:\s+de\s+C\.?V\.?)?)?)",
    ]

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            cliente = match.group(1).strip()
            # Limpiar espacios múltiples
            cliente = re.sub(r'\s+', ' ', cliente)
            # Validar que no sea muy corto o muy largo
            if 3 < len(cliente) < 100:
                return cliente

    return None


def detectar_proyecto(texto: str) -> Optional[str]:
    """
    Busca el nombre/descripción del proyecto

    Args:
        texto: Texto extraído del PDF

    Returns:
        Nombre del proyecto o None
    """
    # Patrones para detectar proyecto
    patrones = [
        r"Proyecto[:\s]+([A-ZÁ-Úa-zá-ú0-9\s\-.,/]+)",
        r"Obra[:\s]+([A-ZÁ-Úa-zá-ú0-9\s\-.,/]+)",
        r"Descripción[:\s]+([A-ZÁ-Úa-zá-ú0-9\s\-.,/]+)",
        r"Referencia[:\s]+([A-ZÁ-Úa-zá-ú0-9\s\-.,/]+)",
        r"Asunto[:\s]+([A-ZÁ-Úa-zá-ú0-9\s\-.,/]+)",
    ]

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            proyecto = match.group(1).strip()
            # Limpiar
            proyecto = re.sub(r'\s+', ' ', proyecto)
            # Tomar solo la primera línea si hay múltiples
            proyecto = proyecto.split('\n')[0]
            # Validar longitud
            if 3 < len(proyecto) < 200:
                return proyecto

    return None


def extraer_items(pdf_path: str) -> List[Dict]:
    """
    Extrae items con descripciones y cantidades usando pdfplumber

    Args:
        pdf_path: Ruta al archivo PDF

    Returns:
        Lista de diccionarios con {descripcion, cantidad}
    """
    items = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Intentar extraer tablas
                tables = page.extract_tables()

                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    # Intentar identificar columnas de Cantidad y Descripción
                    header = [str(cell).lower() if cell else "" for cell in table[0]]

                    # Buscar índices de columnas
                    cantidad_idx = None
                    descripcion_idx = None

                    for idx, col_name in enumerate(header):
                        if any(word in col_name for word in ['cantidad', 'qty', 'cant', 'piezas']):
                            cantidad_idx = idx
                        if any(word in col_name for word in ['descripcion', 'description', 'desc', 'articulo', 'item', 'producto']):
                            descripcion_idx = idx

                    # Procesar filas
                    for row in table[1:]:  # Saltar header
                        if not row or len(row) == 0:
                            continue

                        try:
                            # Intentar extraer cantidad
                            cantidad = None
                            if cantidad_idx is not None and cantidad_idx < len(row):
                                cantidad_str = str(row[cantidad_idx]) if row[cantidad_idx] else ""
                                # Buscar números
                                cantidad_match = re.search(r'(\d+(?:[.,]\d+)?)', cantidad_str)
                                if cantidad_match:
                                    cantidad = float(cantidad_match.group(1).replace(',', '.'))

                            # Intentar extraer descripción
                            descripcion = None
                            if descripcion_idx is not None and descripcion_idx < len(row):
                                descripcion = str(row[descripcion_idx]) if row[descripcion_idx] else ""
                                descripcion = descripcion.strip()

                            # Si no encontramos con índices, buscar en toda la fila
                            if not descripcion:
                                # Tomar la celda más larga como descripción
                                for cell in row:
                                    if cell and len(str(cell)) > 10:
                                        descripcion = str(cell).strip()
                                        break

                            if not cantidad:
                                # Buscar números en toda la fila
                                for cell in row:
                                    if cell:
                                        num_match = re.search(r'^(\d+(?:[.,]\d+)?)$', str(cell))
                                        if num_match:
                                            cantidad = float(num_match.group(1).replace(',', '.'))
                                            break

                            # Agregar item si tiene información válida
                            if descripcion and len(descripcion) > 3:
                                items.append({
                                    'descripcion': descripcion[:200],  # Limitar longitud
                                    'cantidad': cantidad if cantidad else 1.0
                                })

                        except Exception as e:
                            print(f"[OC_PARSER] Error procesando fila: {e}")
                            continue

        # Si no encontramos items con tablas, intentar con texto plano
        if len(items) == 0:
            texto = extraer_texto_completo(pdf_path)
            items = _extraer_items_desde_texto(texto)

        return items

    except Exception as e:
        print(f"[OC_PARSER] Error extrayendo items: {e}")
        return []


def _extraer_items_desde_texto(texto: str) -> List[Dict]:
    """
    Fallback: Extrae items desde texto plano cuando no hay tablas

    Args:
        texto: Texto del PDF

    Returns:
        Lista de items extraídos
    """
    items = []

    # Buscar líneas que parezcan items (número + descripción)
    patron = r'(\d+(?:[.,]\d+)?)\s+([A-ZÁ-Úa-zá-ú0-9\s\-.,/()]+)'
    matches = re.finditer(patron, texto, re.MULTILINE)

    for match in matches:
        try:
            cantidad = float(match.group(1).replace(',', '.'))
            descripcion = match.group(2).strip()

            # Filtrar descripciones muy cortas o que parezcan fechas/montos
            if len(descripcion) > 10 and not re.search(r'^\d+[/-]\d+[/-]\d+$', descripcion):
                items.append({
                    'descripcion': descripcion[:200],
                    'cantidad': cantidad
                })
        except:
            continue

    return items


def extraer_subtotal(texto: str) -> Optional[float]:
    """
    Busca el subtotal (antes de IVA) en el PDF

    Args:
        texto: Texto extraído del PDF

    Returns:
        Subtotal como float o None
    """
    # Patrones para detectar subtotal
    patrones = [
        r"Subtotal[:\s]*\$?\s*([\d,]+\.?\d*)",
        r"Sub\s*total[:\s]*\$?\s*([\d,]+\.?\d*)",
        r"Total\s+antes\s+de\s+IVA[:\s]*\$?\s*([\d,]+\.?\d*)",
        r"Importe\s+neto[:\s]*\$?\s*([\d,]+\.?\d*)",
        r"Total\s+sin\s+IVA[:\s]*\$?\s*([\d,]+\.?\d*)",
    ]

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                # Limpiar y convertir a float
                subtotal_str = match.group(1).replace(',', '')
                subtotal = float(subtotal_str)

                # Validar que sea un monto razonable
                if 0 < subtotal < 999999999:
                    return subtotal
            except:
                continue

    return None


def analizar_oc_completo(pdf_path: str) -> Dict:
    """
    Función principal que coordina el análisis completo del PDF

    Args:
        pdf_path: Ruta al archivo PDF

    Returns:
        Diccionario con datos extraídos y metadata
    """
    resultado = {
        'success': False,
        'datos_extraidos': {
            'cliente': '',
            'proyecto': '',
            'items': [],
            'subtotal': 0.0
        },
        'confianza': 'low',
        'advertencias': []
    }

    try:
        # Validar PDF
        es_valido, mensaje = validar_pdf(pdf_path)
        if not es_valido:
            resultado['advertencias'].append(mensaje)
            return resultado

        # Extraer texto completo
        texto = extraer_texto_completo(pdf_path)

        if not texto or len(texto) < 50:
            resultado['advertencias'].append("No se pudo extraer texto del PDF")
            return resultado

        # Detectar cliente
        cliente = detectar_cliente(texto)
        if cliente:
            resultado['datos_extraidos']['cliente'] = cliente
        else:
            resultado['advertencias'].append("No se detectó cliente, verificar manualmente")

        # Detectar proyecto
        proyecto = detectar_proyecto(texto)
        if proyecto:
            resultado['datos_extraidos']['proyecto'] = proyecto
        else:
            resultado['advertencias'].append("No se detectó proyecto, verificar manualmente")

        # Extraer items
        items = extraer_items(pdf_path)
        if items and len(items) > 0:
            resultado['datos_extraidos']['items'] = items
        else:
            resultado['advertencias'].append("No se detectaron items, agregar manualmente")

        # Extraer subtotal
        subtotal = extraer_subtotal(texto)
        if subtotal:
            resultado['datos_extraidos']['subtotal'] = subtotal
        else:
            resultado['advertencias'].append("No se detectó subtotal, verificar manualmente")

        # Calcular nivel de confianza
        campos_detectados = 0
        if cliente:
            campos_detectados += 1
        if proyecto:
            campos_detectados += 1
        if items and len(items) > 0:
            campos_detectados += 1
        if subtotal:
            campos_detectados += 1

        if campos_detectados >= 3:
            resultado['confianza'] = 'high'
        elif campos_detectados >= 2:
            resultado['confianza'] = 'medium'
        else:
            resultado['confianza'] = 'low'

        resultado['success'] = True

        print(f"[OC_PARSER] Análisis completado:")
        print(f"  - Cliente: {cliente if cliente else 'No detectado'}")
        print(f"  - Proyecto: {proyecto if proyecto else 'No detectado'}")
        print(f"  - Items: {len(items)}")
        print(f"  - Subtotal: ${subtotal if subtotal else 'No detectado'}")
        print(f"  - Confianza: {resultado['confianza']}")

        return resultado

    except Exception as e:
        print(f"[OC_PARSER] ERROR en análisis completo: {e}")
        resultado['advertencias'].append(f"Error en análisis: {str(e)}")
        return resultado
