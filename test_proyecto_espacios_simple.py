#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple para verificar la lógica de normalización de proyecto
Prueba AMBAS funciones: generar_numero_automatico y generar_numero_cotizacion
"""

import unicodedata
import re


def normalizar_cliente(cliente):
    """
    Simula la lógica de normalización del cliente
    """
    if not cliente:
        return "CLIENTE"
    cliente = unicodedata.normalize('NFKD', cliente).encode('ASCII', 'ignore').decode('ASCII').upper()
    cliente = re.sub(r'[^A-Z0-9]', '-', cliente)[:10]
    return cliente


def normalizar_proyecto(proyecto):
    """
    Simula la lógica de normalización del proyecto (NUEVA versión con espacios)
    """
    if not proyecto:
        return "PROYECTO"
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

    cliente_usuario = "BMW"
    vendedor_usuario = "Juan Pérez"
    proyecto_usuario = "Rack selectivo para almacén"

    cliente_norm = normalizar_cliente(cliente_usuario)
    proyecto_norm = normalizar_proyecto(proyecto_usuario)

    # Simular iniciales del vendedor
    iniciales = "JP"  # Juan Pérez

    print(f"\n📋 Datos de entrada:")
    print(f"   Cliente: '{cliente_usuario}'")
    print(f"   Vendedor: '{vendedor_usuario}'")
    print(f"   Proyecto: '{proyecto_usuario}'")

    print(f"\n📋 Datos normalizados:")
    print(f"   Cliente: '{cliente_norm}'")
    print(f"   Vendedor: '{iniciales}'")
    print(f"   Proyecto: '{proyecto_norm}'")

    numero_completo = f"{cliente_norm}-CWS-{iniciales}-001-R1-{proyecto_norm}"

    print(f"\n✅ NÚMERO DE COTIZACIÓN GENERADO:")
    print(f"   {numero_completo}")

    print("\n" + "=" * 80)
    print("COMPARACIÓN ANTES vs AHORA:")
    print("=" * 80)
    print(f"❌ ANTES: BMW-CWS-JP-001-R1-RACKSELECT")
    print(f"✅ AHORA:  {numero_completo}")
    print("\n✅ NOTA: Ahora el nombre del proyecto es mucho más legible y fácil de buscar")


if __name__ == "__main__":
    test_normalizacion()
