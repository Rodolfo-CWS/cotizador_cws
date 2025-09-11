#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico PDF Production - Identificar Causa Falla PDF
========================================================

Diagnosticar por qué la generación de PDF está fallando en producción
mientras que el guardado de cotizaciones funciona correctamente.
"""

import requests
import json
from datetime import datetime

def test_pdf_system_diagnostics():
    """Test de diagnósticos del sistema PDF"""
    
    print("DIAGNOSTIC PDF PRODUCTION SYSTEM")
    print("=" * 40)
    
    base_url = "https://cotizador-cws.onrender.com"
    
    # Test 1: Verificar estado del sistema
    print("Test 1: Verificando estado del sistema...")
    try:
        response = requests.get(f"{base_url}/diagnosticos", timeout=10)
        if response.status_code == 200:
            diag = response.json()
            
            # Check PDF components
            pdf_info = diag.get('pdf', {})
            print(f"ReportLab disponible: {pdf_info.get('reportlab_disponible')}")
            print(f"WeasyPrint disponible: {pdf_info.get('weasyprint_disponible')}")
            print(f"PDFManager inicializado: {pdf_info.get('pdf_manager_inicializado')}")
            
            # Check database
            db_info = diag.get('supabase', {})
            print(f"Supabase modo: {db_info.get('modo', 'unknown')}")
            print(f"Supabase conexión: {db_info.get('conectado', 'unknown')}")
            
        else:
            print(f"Error obteniendo diagnósticos: {response.status_code}")
            
    except Exception as e:
        print(f"Error en diagnósticos: {e}")
        
    print("\nTest 2: Verificar cotización recién creada...")
    
    # Test 2: Buscar la cotización que no generó PDF
    numero_problematico = "CLIENTE-PR-CWS-TE-001-R2-VERIFICACI"
    
    try:
        search_response = requests.post(
            f"{base_url}/buscar",
            json={"query": numero_problematico},
            timeout=10
        )
        
        if search_response.status_code == 200:
            results = search_response.json()
            cotizaciones = results.get('resultados', [])
            
            if cotizaciones:
                print(f"Cotización encontrada: {len(cotizaciones)} resultado(s)")
                cotizacion = cotizaciones[0]
                print(f"Cliente: {cotizacion.get('cliente', 'N/A')}")
                print(f"Número: {cotizacion.get('numero_cotizacion', 'N/A')}")
                print(f"Tiene PDF: {cotizacion.get('url') is not None}")
                
                # Test manual de PDF
                print(f"\nTest 3: Intentar generar PDF manualmente...")
                
                pdf_data = {
                    "numeroCotizacion": numero_problematico
                }
                
                pdf_response = requests.post(
                    f"{base_url}/generar_pdf",
                    json=pdf_data,
                    timeout=30
                )
                
                print(f"Generación PDF manual: HTTP {pdf_response.status_code}")
                
                if pdf_response.status_code == 200:
                    print("PDF generado manualmente con éxito")
                else:
                    print(f"Error generando PDF: {pdf_response.text[:300]}")
                    
            else:
                print("Cotización no encontrada en búsqueda")
                
        else:
            print(f"Error buscando cotización: {search_response.status_code}")
            
    except Exception as e:
        print(f"Error buscando cotización: {e}")
        
    print("\nTest 4: Probar nueva cotización con PDF...")
    
    # Test 4: Crear nueva cotización y verificar PDF
    new_quotation = {
        "datosGenerales": {
            "cliente": "TEST-PDF-DEBUG",
            "vendedor": "PDF-TEST", 
            "proyecto": "DIAGNOSTIC-PDF",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        "items": [{
            "descripcion": "Item test PDF diagnostic", 
            "cantidad": 1,
            "precio_unitario": 50.00
        }],
        "condiciones": {"moneda": "MXN"},
        "observaciones": "Test específico para diagnosticar PDF"
    }
    
    try:
        create_response = requests.post(
            f"{base_url}/formulario",
            json=new_quotation,
            timeout=30
        )
        
        print(f"Nueva cotización: HTTP {create_response.status_code}")
        
        if create_response.status_code == 200:
            result = create_response.json()
            print(f"Cotización creada: {result.get('numeroCotizacion')}")
            print(f"PDF generado: {result.get('pdf_generado')}")
            
            pdf_mensaje = result.get('pdf_mensaje', result.get('pdf_info', {}).get('mensaje', 'N/A'))
            print(f"PDF mensaje: {pdf_mensaje}")
            
            if not result.get('pdf_generado'):
                print("PROBLEMA CONFIRMADO: PDF no se genera en nueva cotización")
            else:
                print("PDF se generó correctamente en nueva cotización")
                
        else:
            print(f"Error creando nueva cotización: {create_response.text[:200]}")
            
    except Exception as e:
        print(f"Error creando nueva cotización: {e}")
        
    print("\n" + "=" * 40)
    print("CONCLUSIONES DIAGNÓSTICO:")
    print("- Si ReportLab/WeasyPrint no disponibles → Instalar en producción")
    print("- Si PDFManager no inicializado → Error en dependencias")  
    print("- Si cotización no encontrada → Problema en db_manager.obtener_cotizacion")
    print("- Si error en generar_pdf_reportlab → Problema en función PDF")
    print("=" * 40)

if __name__ == "__main__":
    test_pdf_system_diagnostics()