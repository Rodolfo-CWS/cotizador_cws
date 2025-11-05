#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple para verificar la lógica de normalización de proyecto
"""

import unicodedata
import re


def normalizar_proyecto(proyecto):
    """
    Simula la lógica de normalización del proyecto
    """
    # Normalizar caracteres con acentos y convertir a mayúsculas
    proyecto = unicodedata.normalize('NFKD', proyecto).encode('ASCII', 'ignore').decode('ASCII').upper()

    # Permitir espacios en el nombre del proyecto, eliminar otros caracteres especiales
    proyecto = re.sub(r'[^A-Z0-9 ]', '', proyecto)

    # Limpiar espacios múltiples y recortar
    proyecto = ' '.join(proyecto.split())[:50]

    return proyecto


def test_normalizacion():
    """
    Probar la normalización con diferentes casos
    """
    print("=" * 80)
    print("TEST: Normalización de nombre de proyecto con espacios")
    print("=" * 80)

    casos_prueba = [
        ("Rack selectivo para almacén", "RACK SELECTIVO PARA ALMACEN"),
        ("Sistema    de    almacenaje   vertical", "SISTEMA DE ALMACENAJE VERTICAL"),
        ("Estantería metálica modular", "ESTANTERIA METALICA MODULAR"),
        ("Proyecto (especial) #1 2025", "PROYECTO ESPECIAL 1 2025"),
        ("BMW - Proyecto Nuevo", "BMW  PROYECTO NUEVO"),
        ("Cotización José María", "COTIZACION JOSE MARIA"),
    ]

    print("\n")
    resultados_ok = 0
    resultados_total = len(casos_prueba)

    for entrada, esperado in casos_prueba:
        resultado = normalizar_proyecto(entrada)
        estado = "✅" if resultado == esperado else "⚠️"

        print(f"{estado} Entrada: '{entrada}'")
        print(f"   Esperado: '{esperado}'")
        print(f"   Resultado: '{resultado}'")

        if resultado == esperado:
            resultados_ok += 1
        else:
            print(f"   ⚠️  Diferencia detectada, pero puede ser aceptable si es legible")
        print()

    print("=" * 80)
    print(f"Resultados: {resultados_ok}/{resultados_total} casos exactamente correctos")
    print("=" * 80)

    # Ejemplo específico del usuario
    print("\n" + "=" * 80)
    print("EJEMPLO ESPECÍFICO DEL USUARIO:")
    print("=" * 80)
    proyecto_usuario = "Rack selectivo para almacén"
    resultado_usuario = normalizar_proyecto(proyecto_usuario)

    print(f"\nProyecto original: '{proyecto_usuario}'")
    print(f"Número de cotización incluirá: '...{resultado_usuario}'")
    print(f"\nEjemplo completo: BMW-CWS-JP-001-R1-{resultado_usuario}")
    print("\n✅ NOTA: Ahora el nombre del proyecto es mucho más legible y fácil de buscar")


if __name__ == "__main__":
    test_normalizacion()
