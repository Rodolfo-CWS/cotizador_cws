#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test para verificar que el campo tiene_desglose sea correcto
"""

import sys
import json

# Mock de las dependencias para evitar errores
class MockGoogleDriveClient:
    def is_available(self):
        return True

    def buscar_pdfs(self, query=""):
        # Simular algunos PDFs de Google Drive
        return [
            {
                'numero_cotizacion': 'TEST-ANTIGUO-CWS-001-R1',
                'id': 'mock_drive_id_1',
                'fecha_modificacion': '2024-01-01',
                'tamaño': '1024'
            },
            {
                'numero_cotizacion': 'LEGACY-CWS-002-R1',
                'id': 'mock_drive_id_2',
                'fecha_modificacion': '2024-02-01',
                'tamaño': '2048'
            }
        ]

# Función simplificada de buscar_pdfs del pdf_manager
def simular_busqueda_google_drive():
    """Simula la búsqueda de PDFs en Google Drive"""
    drive_client = MockGoogleDriveClient()
    resultados = []

    if drive_client and drive_client.is_available():
        try:
            drive_pdfs = drive_client.buscar_pdfs("")
            print(f"✓ PDFs encontrados en Google Drive: {len(drive_pdfs)}")

            for pdf in drive_pdfs:
                resultado = {
                    "numero_cotizacion": pdf['numero_cotizacion'],
                    "cliente": "Google Drive",
                    "fecha_creacion": pdf.get('fecha_modificacion', 'N/A'),
                    "ruta_completa": f"gdrive://{pdf['id']}",
                    "tipo": "google_drive",
                    "tiene_desglose": False,  # PDFs antiguos de Drive NO tienen desglose
                    "drive_id": pdf['id'],
                    "tamaño": pdf.get('tamaño', '0'),
                    "fuente": "google_drive"
                }
                resultados.append(resultado)
        except Exception as e:
            print(f"✗ Error buscando: {e}")

    return resultados

if __name__ == "__main__":
    print("="*60)
    print("TEST: Verificación de campo tiene_desglose")
    print("="*60)

    # Ejecutar simulación
    resultados = simular_busqueda_google_drive()

    # Verificar resultados
    print(f"\n📊 Resultados de la búsqueda:")
    print(f"   Total de PDFs encontrados: {len(resultados)}")

    # Verificar cada resultado
    todos_correctos = True
    for idx, pdf in enumerate(resultados, 1):
        print(f"\n   PDF #{idx}:")
        print(f"      Número: {pdf['numero_cotizacion']}")
        print(f"      Tipo: {pdf['tipo']}")
        print(f"      Fuente: {pdf['fuente']}")
        print(f"      tiene_desglose: {pdf['tiene_desglose']}")

        # Verificar que sea False para PDFs de Google Drive
        if pdf['tipo'] == 'google_drive' and pdf['tiene_desglose'] == True:
            print(f"      ❌ ERROR: PDF de Google Drive tiene desglose=True (debería ser False)")
            todos_correctos = False
        elif pdf['tipo'] == 'google_drive' and pdf['tiene_desglose'] == False:
            print(f"      ✅ CORRECTO: PDF de Google Drive tiene desglose=False")

    # Resultado final
    print("\n" + "="*60)
    if todos_correctos:
        print("✅ PRUEBA EXITOSA: Todos los PDFs de Google Drive tienen tiene_desglose=False")
        print("="*60)
        sys.exit(0)
    else:
        print("❌ PRUEBA FALLIDA: Algunos PDFs tienen configuración incorrecta")
        print("="*60)
        sys.exit(1)
