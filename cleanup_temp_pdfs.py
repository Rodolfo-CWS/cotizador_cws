# -*- coding: utf-8 -*-
"""
Limpieza automática de PDFs temporales
=======================================

Elimina PDFs de análisis de OCs que tengan más de 1 hora de antigüedad.

Autor: CWS Company
Fecha: 2025-01-13
"""

import os
import time
from pathlib import Path

# Configuración
TEMP_DIR = Path(__file__).parent / 'static' / 'temp'
MAX_AGE_HOURS = 1


def limpiar_pdfs_antiguos():
    """
    Elimina PDFs temporales más antiguos de MAX_AGE_HOURS
    """
    try:
        # Crear directorio si no existe
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        now = time.time()
        max_age_seconds = MAX_AGE_HOURS * 3600
        archivos_eliminados = 0

        for pdf_file in TEMP_DIR.glob('*.pdf'):
            try:
                # Obtener tiempo de modificación del archivo
                file_age = now - pdf_file.stat().st_mtime

                if file_age > max_age_seconds:
                    pdf_file.unlink()
                    archivos_eliminados += 1
                    print(f"[CLEANUP] Eliminado: {pdf_file.name} (antigüedad: {file_age/3600:.1f} horas)")

            except Exception as e:
                print(f"[CLEANUP] Error eliminando {pdf_file.name}: {e}")
                continue

        if archivos_eliminados > 0:
            print(f"[CLEANUP] Total archivos eliminados: {archivos_eliminados}")
        else:
            print(f"[CLEANUP] No hay PDFs temporales para eliminar")

    except Exception as e:
        print(f"[CLEANUP] Error en limpieza automática: {e}")


if __name__ == '__main__':
    limpiar_pdfs_antiguos()
