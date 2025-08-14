"""
MÓDULO DE VALIDACIÓN Y SEGURIDAD CWS
Funciones para validar y sanitizar datos en el backend
"""

import re
import html
import decimal
from typing import Any, Dict, Optional, Union
import logging

# Configurar logger de seguridad
security_logger = logging.getLogger('SECURITY')
security_logger.setLevel(logging.WARNING)

class SecurityValidator:
    """Validador de seguridad para datos de cotizaciones"""
    
    # Expresiones regulares para validación
    REGEX_NUMERO_COTIZACION = re.compile(r'^[A-Z0-9_-]{1,20}$')
    REGEX_NOMBRE_CLIENTE = re.compile(r'^[a-zA-Z0-9\s\.\-&]{1,100}$')
    REGEX_DESCRIPCION = re.compile(r'^[a-zA-Z0-9\s\.\-_/()]{1,200}$')
    
    # Rangos válidos para datos financieros
    MIN_PRECIO = 0.01
    MAX_PRECIO = 1000000.00
    MIN_CANTIDAD = 0.01
    MAX_CANTIDAD = 100000.00
    MIN_PESO = 0.01
    MAX_PESO = 50000.00
    MIN_TIPO_CAMBIO = 1.00
    MAX_TIPO_CAMBIO = 50.00

    @staticmethod
    def escape_html(text: str) -> str:
        """Escapa caracteres HTML para prevenir XSS"""
        if not isinstance(text, str):
            return ""
        return html.escape(text, quote=True)

    @staticmethod
    def sanitize_string(text: str, max_length: int = 100) -> str:
        """Sanitiza y valida strings de entrada"""
        if not isinstance(text, str):
            return ""
        
        # Remover caracteres de control y espacios extra
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Truncar si es necesario
        if len(sanitized) > max_length:
            security_logger.warning(f"String truncado de {len(sanitized)} a {max_length} caracteres")
            sanitized = sanitized[:max_length]
        
        return SecurityValidator.escape_html(sanitized)

    @staticmethod
    def validate_financial_number(value: Any, min_val: float, max_val: float, 
                                field_name: str = "number") -> decimal.Decimal:
        """Valida números financieros con precisión decimal"""
        try:
            # Convertir a decimal para precisión financiera
            if isinstance(value, str):
                # Remover caracteres no numéricos excepto punto y coma
                value = re.sub(r'[^\d\.\-]', '', value)
            
            decimal_val = decimal.Decimal(str(value))
            
            # Validar rango
            if decimal_val < decimal.Decimal(str(min_val)) or decimal_val > decimal.Decimal(str(max_val)):
                security_logger.warning(
                    f"Valor {field_name} fuera de rango: {decimal_val} "
                    f"(válido: {min_val}-{max_val})"
                )
                return decimal.Decimal('0.00')
            
            # Redondear a 2 decimales
            return decimal_val.quantize(decimal.Decimal('0.01'))
            
        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            security_logger.warning(f"Error validando {field_name}: {e}")
            return decimal.Decimal('0.00')

    @classmethod
    def validate_peso_estructura(cls, peso: Any) -> decimal.Decimal:
        """Valida peso de estructura para cotización por peso"""
        return cls.validate_financial_number(
            peso, cls.MIN_PESO, cls.MAX_PESO, "peso_estructura"
        )

    @classmethod
    def validate_precio_kg(cls, precio: Any) -> decimal.Decimal:
        """Valida precio por kilogramo"""
        return cls.validate_financial_number(
            precio, cls.MIN_PRECIO, cls.MAX_PRECIO, "precio_kg"
        )

    @classmethod
    def validate_tipo_cambio(cls, tipo_cambio: Any) -> decimal.Decimal:
        """Valida tipo de cambio USD"""
        return cls.validate_financial_number(
            tipo_cambio, cls.MIN_TIPO_CAMBIO, cls.MAX_TIPO_CAMBIO, "tipo_cambio"
        )

    @classmethod
    def validate_material_data(cls, material: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida y sanitiza datos de material completos
        Reemplaza la función validate_material_data original con seguridad mejorada
        """
        if not isinstance(material, dict):
            security_logger.error("Material no es un diccionario válido")
            return {
                'descripcion': 'Material inválido',
                'peso': decimal.Decimal('0.00'),
                'cantidad': decimal.Decimal('0.00'),
                'precio': decimal.Decimal('0.00'),
                'subtotal': decimal.Decimal('0.00'),
                'es_cotizar_por_peso': False
            }

        # Sanitizar descripción
        descripcion = cls.sanitize_string(
            material.get('descripcion') or material.get('material', ''), 
            max_length=200
        )

        # Detectar si es cotización por peso
        es_cotizar_por_peso = (
            descripcion == 'COTIZAR_POR_PESO' or 
            material.get('tipoCotizacion') == 'peso'
        )

        if es_cotizar_por_peso:
            # Validar campos específicos de cotización por peso
            peso_estructura = cls.validate_peso_estructura(
                material.get('pesoEstructura', 0)
            )
            precio_kg = cls.validate_precio_kg(
                material.get('precioKg', 0)
            )
            subtotal = peso_estructura * precio_kg
            
            return {
                'descripcion': 'COTIZAR_POR_PESO',
                'pesoEstructura': peso_estructura,
                'precioKg': precio_kg,
                'subtotal': subtotal,
                'es_cotizar_por_peso': True,
                # Campos tradicionales en 0 para compatibilidad
                'peso': decimal.Decimal('0.00'),
                'cantidad': decimal.Decimal('0.00'),
                'precio': decimal.Decimal('0.00')
            }
        else:
            # Validar campos tradicionales
            peso = cls.validate_financial_number(
                material.get('peso', 1), cls.MIN_PESO, cls.MAX_PESO, "peso"
            )
            cantidad = cls.validate_financial_number(
                material.get('cantidad', 0), cls.MIN_CANTIDAD, cls.MAX_CANTIDAD, "cantidad"
            )
            precio = cls.validate_financial_number(
                material.get('precio', 0), cls.MIN_PRECIO, cls.MAX_PRECIO, "precio"
            )
            
            subtotal = peso * cantidad * precio
            
            return {
                'descripcion': descripcion,
                'peso': peso,
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': subtotal,
                'es_cotizar_por_peso': False
            }

    @classmethod
    def validate_cotizacion_completa(cls, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos completos de cotización"""
        resultado = {
            'valida': True,
            'errores': [],
            'datos_sanitizados': {}
        }

        try:
            # Validar datos generales
            datos_generales = datos.get('datosGenerales', {})
            
            # Cliente
            cliente = cls.sanitize_string(datos_generales.get('cliente', ''), 100)
            if not cliente or len(cliente) < 2:
                resultado['errores'].append("Nombre de cliente inválido")
            
            # Vendedor
            vendedor = cls.sanitize_string(datos_generales.get('vendedor', ''), 100)
            if not vendedor:
                resultado['errores'].append("Vendedor requerido")
            
            # Tipo de cambio si es USD
            moneda = datos_generales.get('moneda', 'MXN')
            tipo_cambio = decimal.Decimal('1.00')
            
            if moneda == 'USD':
                tipo_cambio = cls.validate_tipo_cambio(
                    datos_generales.get('tipoCambio', 0)
                )
                if tipo_cambio <= decimal.Decimal('1.00'):
                    resultado['errores'].append("Tipo de cambio USD inválido")

            # Validar items y materiales
            items_validados = []
            items = datos.get('items', [])
            
            for i, item in enumerate(items):
                item_validado = {
                    'descripcion': cls.sanitize_string(item.get('descripcion', ''), 200),
                    'materiales': [],
                    'otrosMateriales': []
                }
                
                # Validar materiales
                for material in item.get('materiales', []):
                    material_validado = cls.validate_material_data(material)
                    item_validado['materiales'].append(material_validado)
                
                # Validar otros materiales
                for material in item.get('otrosMateriales', []):
                    material_validado = cls.validate_material_data(material)
                    item_validado['otrosMateriales'].append(material_validado)
                
                items_validados.append(item_validado)

            # Construir datos sanitizados
            resultado['datos_sanitizados'] = {
                'datosGenerales': {
                    'cliente': cliente,
                    'vendedor': vendedor,
                    'proyecto': cls.sanitize_string(datos_generales.get('proyecto', ''), 200),
                    'moneda': moneda,
                    'tipoCambio': float(tipo_cambio)
                },
                'items': items_validados
            }

            if resultado['errores']:
                resultado['valida'] = False

        except Exception as e:
            security_logger.error(f"Error validando cotización: {e}")
            resultado['valida'] = False
            resultado['errores'].append("Error interno de validación")

        return resultado

# Funciones para reemplazar las existentes en app.py
def safe_float(value: Any, default: float = 0.0) -> float:
    """Reemplazo seguro para la función safe_float original"""
    try:
        decimal_val = SecurityValidator.validate_financial_number(
            value, 0, 1000000, "numeric_value"
        )
        return float(decimal_val)
    except:
        return default

def validate_material_data_secure(material: Dict[str, Any], 
                                item_index: int = 0, 
                                material_index: int = 0) -> Dict[str, Any]:
    """Reemplazo seguro para validate_material_data"""
    # Log seguro sin exponer datos sensibles
    security_logger.info(f"Validando material {material_index} del item {item_index}")
    
    return SecurityValidator.validate_material_data(material)