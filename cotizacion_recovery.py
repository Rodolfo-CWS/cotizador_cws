#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COTIZACION RECOVERY SYSTEM
==========================

Sistema de recuperación de cotizaciones perdidas desde PDFs y metadatos.
Permite reconstruir datos de cotización cuando se pierden en contenedores efímeros.
"""

import os
import json
import re
import tempfile
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Para PDF processing
try:
    import PyPDF2
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False

logger = logging.getLogger(__name__)

class CotizacionRecovery:
    def __init__(self, cloudinary_manager=None, pdf_manager=None):
        """
        Inicializa el sistema de recuperación de cotizaciones
        
        Args:
            cloudinary_manager: Manager de Cloudinary para descargas
            pdf_manager: Manager de PDFs para metadatos
        """
        self.cloudinary_manager = cloudinary_manager
        self.pdf_manager = pdf_manager
        
    def recuperar_cotizacion(self, numero_cotizacion: str) -> Dict:
        """
        Recupera datos de cotización usando múltiples métodos
        
        Args:
            numero_cotizacion: Número de la cotización a recuperar
            
        Returns:
            Dict con datos recuperados de la cotización
        """
        print(f"[RECOVERY] Iniciando recuperación para: '{numero_cotizacion}'")
        
        # PASO 1: Extraer información del número de cotización
        datos_basicos = self._extraer_datos_del_numero(numero_cotizacion)
        
        # PASO 2: Intentar obtener PDF desde Cloudinary
        pdf_data = self._descargar_pdf_cloudinary(numero_cotizacion)
        
        # PASO 3: Extraer metadatos del PDF si está disponible
        if pdf_data:
            metadatos_pdf = self._extraer_metadatos_pdf(pdf_data)
            datos_basicos = self._combinar_datos(datos_basicos, metadatos_pdf)
        
        # PASO 4: Enriquecer con información adicional
        datos_completos = self._enriquecer_cotizacion(datos_basicos, numero_cotizacion)
        
        print(f"[RECOVERY] Recuperación completada para: '{numero_cotizacion}'")
        return datos_completos
    
    def _extraer_datos_del_numero(self, numero_cotizacion: str) -> Dict:
        """
        Extrae información básica del formato de número de cotización
        Formato: CLIENTE-CWS-VENDEDOR-###-R#-PROYECTO
        """
        print(f"[RECOVERY] Extrayendo datos del número: '{numero_cotizacion}'")
        
        try:
            partes = numero_cotizacion.split('-')
            
            if len(partes) >= 6:
                cliente = partes[0]
                empresa = partes[1] 
                vendedor = partes[2]
                numero_seq = partes[3]
                revision = partes[4]
                proyecto = '-'.join(partes[5:])  # El resto es el proyecto
                
                datos = {
                    'datosGenerales': {
                        'cliente': cliente,
                        'vendedor': vendedor,
                        'proyecto': proyecto,
                        'numeroCotizacion': numero_cotizacion,
                        'revision': int(revision.replace('R', '')) if revision.startswith('R') else 1,
                        'empresa': empresa,
                        'atencionA': f'Contacto {cliente}',
                        'contacto': f'{cliente.lower()}@contacto.com',
                        'fecha': datetime.now().strftime('%Y-%m-%d'),
                        'validez': '30 días'
                    },
                    'items': [],
                    'observaciones': f'Cotización recuperada automáticamente. Número: {numero_cotizacion}',
                    'numeroCotizacion': numero_cotizacion,
                    'revision': int(revision.replace('R', '')) if revision.startswith('R') else 1,
                    'fechaCreacion': datetime.now().isoformat(),
                    'estado': 'recuperada_automaticamente',
                    'tipo_recuperacion': 'numero_cotizacion'
                }
                
                print(f"[RECOVERY] Datos extraídos: Cliente={cliente}, Vendedor={vendedor}, Proyecto={proyecto}")
                return datos
            else:
                print(f"[RECOVERY] Formato de número no reconocido, usando datos mínimos")
                return self._crear_estructura_minima(numero_cotizacion)
                
        except Exception as e:
            print(f"[RECOVERY] Error extrayendo datos del número: {e}")
            return self._crear_estructura_minima(numero_cotizacion)
    
    def _crear_estructura_minima(self, numero_cotizacion: str) -> Dict:
        """Crea estructura mínima cuando no se puede parsear el número"""
        return {
            'datosGenerales': {
                'cliente': 'Cliente',
                'vendedor': 'Vendedor', 
                'proyecto': 'Proyecto',
                'numeroCotizacion': numero_cotizacion,
                'revision': 1,
                'empresa': 'CWS',
                'atencionA': 'Contacto',
                'contacto': 'contacto@empresa.com',
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'validez': '30 días'
            },
            'items': [],
            'observaciones': f'Cotización recuperada (estructura mínima). Número: {numero_cotizacion}',
            'numeroCotizacion': numero_cotizacion,
            'revision': 1,
            'fechaCreacion': datetime.now().isoformat(),
            'estado': 'recuperada_estructura_minima',
            'tipo_recuperacion': 'estructura_minima'
        }
    
    def _descargar_pdf_cloudinary(self, numero_cotizacion: str) -> Optional[bytes]:
        """
        Descarga PDF desde Cloudinary si está disponible
        """
        print(f"[RECOVERY] Intentando descargar PDF desde Cloudinary...")
        
        try:
            if not self.cloudinary_manager or not self.cloudinary_manager.is_available():
                print(f"[RECOVERY] Cloudinary no disponible")
                return None
            
            # Construir URL del PDF en Cloudinary
            # Formato: cotizaciones/nuevas/NUMERO-COTIZACION.pdf
            public_id = f"cotizaciones/nuevas/{numero_cotizacion}"
            
            # Obtener URL de descarga
            import cloudinary.utils
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type="raw",
                type="upload"
            )[0]
            
            print(f"[RECOVERY] URL construida: {url}")
            
            # Descargar PDF
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                print(f"[RECOVERY] PDF descargado exitosamente ({len(response.content)} bytes)")
                return response.content
            else:
                print(f"[RECOVERY] Error descargando PDF: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[RECOVERY] Error descargando PDF de Cloudinary: {e}")
            return None
    
    def _extraer_metadatos_pdf(self, pdf_data: bytes) -> Dict:
        """
        Extrae metadatos y datos embebidos del PDF
        """
        print(f"[RECOVERY] Extrayendo metadatos del PDF...")
        metadatos = {}
        
        if not PDF_PROCESSING_AVAILABLE:
            print(f"[RECOVERY] PyPDF2 no disponible, saltando extracción de metadatos")
            return metadatos
            
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_data)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Metadatos básicos del PDF
                    if pdf_reader.metadata:
                        pdf_metadata = pdf_reader.metadata
                        metadatos.update({
                            'titulo': pdf_metadata.get('/Title', ''),
                            'autor': pdf_metadata.get('/Author', ''),
                            'asunto': pdf_metadata.get('/Subject', ''),
                            'creador': pdf_metadata.get('/Creator', ''),
                            'fecha_creacion': pdf_metadata.get('/CreationDate', ''),
                            'fecha_modificacion': pdf_metadata.get('/ModDate', '')
                        })
                    
                    # Intentar extraer texto de la primera página para buscar datos
                    if len(pdf_reader.pages) > 0:
                        primera_pagina = pdf_reader.pages[0]
                        texto = primera_pagina.extract_text()
                        
                        # Buscar patrones en el texto
                        datos_texto = self._extraer_datos_del_texto(texto)
                        metadatos.update(datos_texto)
                    
                    print(f"[RECOVERY] Metadatos extraídos: {list(metadatos.keys())}")
                    
            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            print(f"[RECOVERY] Error extrayendo metadatos del PDF: {e}")
            
        return metadatos
    
    def _extraer_datos_del_texto(self, texto: str) -> Dict:
        """
        Extrae datos específicos del texto del PDF usando patrones
        """
        datos = {}
        
        if not texto:
            return datos
            
        texto_clean = texto.replace('\n', ' ').replace('\r', ' ')
        
        try:
            # Buscar patrones comunes del PDF CWS
            patrones = {
                'cliente': r'Cliente[:\s]+([A-Za-z0-9\s]+)(?:\s|$)',
                'vendedor': r'Vendedor[:\s]+([A-Za-z0-9\s]+)(?:\s|$)', 
                'proyecto': r'Proyecto[:\s]+([A-Za-z0-9\s\-]+)(?:\s|$)',
                'atencion_a': r'Atención a[:\s]+([A-Za-z0-9\s]+)(?:\s|$)',
                'contacto': r'Contacto[:\s]+([A-Za-z0-9@\.\s]+)(?:\s|$)',
                'fecha': r'Fecha[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}\/\d{2}\/\d{4})',
                'validez': r'Validez[:\s]+([0-9]+\s*días?)'
            }
            
            for campo, patron in patrones.items():
                match = re.search(patron, texto_clean, re.IGNORECASE)
                if match:
                    datos[campo] = match.group(1).strip()
                    print(f"[RECOVERY] Extraído del texto - {campo}: {datos[campo]}")
            
        except Exception as e:
            print(f"[RECOVERY] Error extrayendo datos del texto: {e}")
            
        return datos
    
    def _combinar_datos(self, datos_basicos: Dict, metadatos_pdf: Dict) -> Dict:
        """
        Combina datos básicos con metadatos del PDF
        """
        if not metadatos_pdf:
            return datos_basicos
            
        print(f"[RECOVERY] Combinando datos básicos con metadatos del PDF")
        
        # Actualizar datos generales con información del PDF si está disponible
        datos_generales = datos_basicos.get('datosGenerales', {})
        
        # Mapeo de campos del PDF a estructura de cotización
        mapeo = {
            'cliente': metadatos_pdf.get('cliente'),
            'vendedor': metadatos_pdf.get('vendedor'),  
            'proyecto': metadatos_pdf.get('proyecto'),
            'atencionA': metadatos_pdf.get('atencion_a'),
            'contacto': metadatos_pdf.get('contacto'),
            'fecha': metadatos_pdf.get('fecha'),
            'validez': metadatos_pdf.get('validez')
        }
        
        # Actualizar solo campos que tengan valor válido
        for campo, valor in mapeo.items():
            if valor and valor.strip():
                datos_generales[campo] = valor.strip()
                print(f"[RECOVERY] Actualizado {campo} desde PDF: {valor}")
        
        datos_basicos['datosGenerales'] = datos_generales
        datos_basicos['tipo_recuperacion'] = 'numero_cotizacion_con_pdf'
        
        return datos_basicos
    
    def _enriquecer_cotizacion(self, datos: Dict, numero_cotizacion: str) -> Dict:
        """
        Enriquece los datos de cotización con información adicional y estructura completa
        """
        print(f"[RECOVERY] Enriqueciendo cotización recuperada")
        
        # Asegurar que tenga items (aunque sea un placeholder)
        if not datos.get('items'):
            datos['items'] = [
                {
                    'descripcion': '⚠️ Items de cotización no disponibles - Ver PDF completo',
                    'cantidad': 1,
                    'precio_unitario': 0.00,
                    'subtotal': 0.00,
                    'nota': 'Datos no recuperables automáticamente'
                }
            ]
        
        # Agregar información de recuperación
        datos['metadata_recuperacion'] = {
            'fecha_recuperacion': datetime.now().isoformat(),
            'metodo_recuperacion': datos.get('tipo_recuperacion', 'automatico'),
            'completitud': 'basica',
            'requiere_pdf_para_detalles': True
        }
        
        # Asegurar campos requeridos
        datos.setdefault('condiciones', {
            'moneda': 'MXN',
            'tipo_cambio': 1.0,
            'iva_porcentaje': 16,
            'descuento_porcentaje': 0
        })
        
        datos.setdefault('totales', {
            'subtotal': 0.00,
            'iva': 0.00,
            'total': 0.00,
            'nota': 'Totales no disponibles - Ver PDF'
        })
        
        # ID único para tracking
        datos['_id'] = f"recovered_{numero_cotizacion.replace('-', '_')}"
        
        print(f"[RECOVERY] Cotización enriquecida completamente")
        return datos

def recuperar_cotizacion_perdida(numero_cotizacion: str, cloudinary_manager=None, pdf_manager=None) -> Dict:
    """
    Función helper para recuperar una cotización perdida
    
    Args:
        numero_cotizacion: Número de la cotización
        cloudinary_manager: Manager de Cloudinary (opcional)
        pdf_manager: Manager de PDFs (opcional)
        
    Returns:
        Dict con estructura de cotización recuperada
    """
    recovery = CotizacionRecovery(cloudinary_manager, pdf_manager)
    return recovery.recuperar_cotizacion(numero_cotizacion)