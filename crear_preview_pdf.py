#!/usr/bin/env python3
"""
Generador de Preview PDF con colores grises
Crea PDFs de muestra para visualizar los cambios
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import generar_pdf_reportlab, REPORTLAB_AVAILABLE
    print("OK: Sistema PDF importado correctamente")
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

def crear_preview_basico():
    """Crear preview basico con datos minimos"""
    return {
        "datosGenerales": {
            "cliente": "PREVIEW CLIENTE SA DE CV",
            "vendedor": "DISENO PREVIEW", 
            "proyecto": "MUESTRA COLORES GRISES",
            "numeroCotizacion": "PREVIEW-CWS-DIS-001-R1-COLORES-GRISES",
            "revision": 1,
            "atencionA": "Director de Compras",
            "contacto": "compras@cliente.com"
        },
        "items": [
            {
                "descripcion": "Estructura metalica principal",
                "cantidad": 5,
                "precio_unitario": 2500.0,
                "subtotal": 12500.0,
                "uom": "Pieza"
            },
            {
                "descripcion": "Sistema de anclaje especializado",
                "cantidad": 10,
                "precio_unitario": 850.0,
                "subtotal": 8500.0,
                "uom": "Kit"
            },
            {
                "descripcion": "Recubrimiento anticorrosivo premium",
                "cantidad": 1,
                "precio_unitario": 3200.0,
                "subtotal": 3200.0,
                "uom": "Servicio"
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "iva": 16,
            "subtotal": 24200.0,
            "iva_monto": 3872.0,
            "total": 28072.0,
            "terminos": "50% anticipo, 50% contra entrega",
            "tiempoEntrega": "20 dias habiles",
            "entregaEn": "Planta Industrial - Zona Norte",
            "comentarios": "Incluye supervision tecnica durante instalacion"
        },
        "observaciones": "PREVIEW: Este PDF muestra el nuevo diseno con colores grises corporativos"
    }

def crear_preview_completo():
    """Crear preview completo con muchos elementos"""
    return {
        "datosGenerales": {
            "cliente": "EMPRESA INDUSTRIAL PREVIEW LTDA",
            "vendedor": "CARLOS PREVIEW MANAGER",
            "proyecto": "SISTEMA COMPLETO - DEMO COLORES GRISES",
            "numeroCotizacion": "EMPRESA-IND-CWS-CPM-001-R2-SISTEMA-COMPLETO",
            "revision": 2,
            "atencionA": "Ing. Maria Gonzalez - Jefa de Proyectos",
            "contacto": "maria.gonzalez@empresaindustrial.com",
            "actualizacionRevision": "Revision 2: Actualizacion de especificaciones tecnicas y precios"
        },
        "items": [
            {
                "descripcion": "Modulo A: Estructura base con refuerzo sismico",
                "cantidad": 8,
                "precio_unitario": 4500.0,
                "subtotal": 36000.0,
                "uom": "Modulo"
            },
            {
                "descripcion": "Modulo B: Sistema de ventilacion industrial",
                "cantidad": 4,
                "precio_unitario": 6200.0,
                "subtotal": 24800.0,
                "uom": "Sistema"
            },
            {
                "descripcion": "Kit de conectores especializados alta resistencia",
                "cantidad": 25,
                "precio_unitario": 320.0,
                "subtotal": 8000.0,
                "uom": "Kit"
            },
            {
                "descripcion": "Servicio de instalacion y puesta en marcha",
                "cantidad": 1,
                "precio_unitario": 12000.0,
                "subtotal": 12000.0,
                "uom": "Servicio"
            },
            {
                "descripcion": "Capacitacion tecnica del personal (40 horas)",
                "cantidad": 40,
                "precio_unitario": 450.0,
                "subtotal": 18000.0,
                "uom": "Hora"
            },
            {
                "descripcion": "Garantia extendida y mantenimiento (12 meses)",
                "cantidad": 12,
                "precio_unitario": 800.0,
                "subtotal": 9600.0,
                "uom": "Mes"
            }
        ],
        "condiciones": {
            "moneda": "USD",
            "tipoCambio": 18.5,
            "iva": 0,  # USD sin IVA
            "subtotal": 108400.0,
            "iva_monto": 0.0,
            "total": 108400.0,
            "terminos": "30% anticipo, 40% avance 50%, 30% contra entrega",
            "tiempoEntrega": "45 dias habiles despues de confirmacion",
            "entregaEn": "Complejo Industrial Zona Franca - San Luis Potosi",
            "comentarios": "Cotizacion valida por 60 dias. Precios en USD. Incluye todos los permisos y certificaciones requeridas."
        },
        "observaciones": "PREVIEW COMPLETO: Muestra todos los elementos del PDF con el nuevo esquema de colores grises. Incluye multiples items, USD, revisiones y campos completos."
    }

def generar_previews():
    """Generar multiples previews"""
    print("GENERADOR DE PREVIEWS PDF - COLORES GRISES")
    print("=" * 60)
    
    if not REPORTLAB_AVAILABLE:
        print("ERROR: ReportLab no disponible")
        return False
    
    previews = [
        {
            "nombre": "Preview Basico (MXN)",
            "datos": crear_preview_basico(),
            "archivo": "preview_pdf_basico_grises.pdf"
        },
        {
            "nombre": "Preview Completo (USD)",
            "datos": crear_preview_completo(), 
            "archivo": "preview_pdf_completo_grises.pdf"
        }
    ]
    
    archivos_generados = []
    
    for preview in previews:
        try:
            print(f"\nGenerando: {preview['nombre']}")
            
            pdf_bytes = generar_pdf_reportlab(preview['datos'])
            
            if pdf_bytes and len(pdf_bytes) > 5000:
                with open(preview['archivo'], 'wb') as f:
                    f.write(pdf_bytes)
                
                print(f"   OK Archivo: {preview['archivo']}")
                print(f"   OK Tamano: {len(pdf_bytes):,} bytes")
                print(f"   OK Cliente: {preview['datos']['datosGenerales']['cliente']}")
                print(f"   OK Total: ${preview['datos']['condiciones']['total']:,.2f} {preview['datos']['condiciones']['moneda']}")
                
                archivos_generados.append(preview['archivo'])
            else:
                print(f"   ERROR: PDF muy pequeno o vacio")
                
        except Exception as e:
            print(f"   ERROR generando {preview['nombre']}: {e}")
    
    print(f"\nARCHIVOS GENERADOS:")
    for archivo in archivos_generados:
        print(f"   - {archivo}")
    
    return len(archivos_generados) > 0

def main():
    """Funcion principal"""
    print("GENERADOR DE PREVIEWS - COLORES GRISES")
    print("Este script genera PDFs de muestra para ver los nuevos colores")
    print("=" * 60)
    
    # Generar previews
    if generar_previews():
        print("\nPREVIEWS GENERADOS EXITOSAMENTE")
        
        print(f"\nDIFERENCIAS PRINCIPALES:")
        print(f"   • Headers con colores grises (#4A5568) en lugar de azul")
        print(f"   • Bordes y lineas en tonos grises (#2D3748)")
        print(f"   • Diseno mas sobrio y profesional")
        print(f"   • Misma funcionalidad, mejor estetica")
        
    else:
        print("\nERROR: No se pudieron generar los previews")
        return False
    
    print(f"\nPROCESO COMPLETADO!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)