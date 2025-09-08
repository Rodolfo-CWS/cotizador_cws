#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SIMPLE PARA REVISAR DESGLOSE
=================================

Script para crear una cotización y luego navegar al desglose
para que podamos revisarlo con Playwright después.
"""

import sys
import os
from datetime import datetime

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.abspath('.'))

from supabase_manager import SupabaseManager

def crear_cotizacion_para_desglose():
    """Crear una cotización específica para revisar el desglose"""
    print("=" * 60)
    print("CREANDO COTIZACIÓN PARA REVISAR DESGLOSE")
    print("=" * 60)
    
    db = SupabaseManager()
    
    # Crear cotización con datos variados para probar el formato
    datos_test = {
        'datosGenerales': {
            'cliente': 'EMPRESA VISUAL TEST SA DE CV',
            'vendedor': 'FORMATO',
            'proyecto': 'REVISION DESGLOSE UI/UX',
            'revision': '1',
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'moneda': 'MXN',
            'observaciones': 'Cotización creada específicamente para revisar el formato visual del desglose. Incluye múltiples items con diferentes tipos de datos para probar la alineación y presentación.'
        },
        'items': [
            {
                'descripcion': 'Servicio de consultoría técnica especializada en sistemas empresariales',
                'cantidad': 2,
                'precio_unitario': 15000.00,
                'subtotal': 30000.00
            },
            {
                'descripcion': 'Licencia de software',
                'cantidad': 1,
                'precio_unitario': 5000.00,
                'subtotal': 5000.00
            },
            {
                'descripcion': 'Capacitación del personal (40 horas)',
                'cantidad': 40,
                'precio_unitario': 800.00,
                'subtotal': 32000.00
            },
            {
                'descripcion': 'Soporte técnico mensual',
                'cantidad': 12,
                'precio_unitario': 2500.00,
                'subtotal': 30000.00
            }
        ],
        'condiciones': {
            'moneda': 'MXN',
            'iva': 16,
            'subtotal': 97000.00,
            'iva_monto': 15520.00,
            'total': 112520.00,
            'forma_pago': 'Transferencia bancaria',
            'tiempo_entrega': '15 días hábiles',
            'validez_oferta': '30 días naturales',
            'condiciones_adicionales': 'Precios sujetos a cambios sin previo aviso. Se requiere el 50% de anticipo para iniciar los trabajos.'
        }
    }
    
    resultado = db.guardar_cotizacion(datos_test)
    
    if resultado.get('success'):
        numero = resultado.get('numeroCotizacion') or resultado.get('numero_cotizacion')
        print(f"[OK] Cotización creada exitosamente: {numero}")
        print(f"    Para ver el desglose: http://127.0.0.1:5000/desglose/{numero}")
        print(f"    Para buscar: http://127.0.0.1:5000/")
        return numero
    else:
        print(f"[ERROR] No se pudo crear la cotización: {resultado.get('error')}")
        return None

if __name__ == "__main__":
    numero = crear_cotizacion_para_desglose()
    
    if numero:
        print(f"\n" + "=" * 60)
        print("COTIZACIÓN LISTA PARA REVISAR")
        print("=" * 60)
        print("1. Inicia el servidor Flask:")
        print("   python app.py")
        print("")
        print("2. Ve al desglose en tu navegador:")
        print(f"   http://127.0.0.1:5000/desglose/{numero}")
        print("")
        print("3. O busca desde la página principal:")
        print("   http://127.0.0.1:5000/")
        print("   Busca: 'EMPRESA VISUAL' o 'FORMATO'")
    else:
        print("No se pudo crear la cotización para probar")