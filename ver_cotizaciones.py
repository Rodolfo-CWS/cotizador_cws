#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ver Cotizaciones - Script para visualizar cotizaciones en JSON
============================================================
"""

import json
import sys

def ver_resumen():
    """Ver resumen de todas las cotizaciones"""
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cotizaciones = data.get('cotizaciones', [])
    print(f'TOTAL DE COTIZACIONES: {len(cotizaciones)}')
    print('=' * 60)
    
    for i, cotizacion in enumerate(cotizaciones, 1):
        numero = cotizacion.get('numeroCotizacion', 'N/A')
        cliente = cotizacion.get('datosGenerales', {}).get('cliente', 'N/A')
        vendedor = cotizacion.get('datosGenerales', {}).get('vendedor', 'N/A')
        proyecto = cotizacion.get('datosGenerales', {}).get('proyecto', 'N/A')
        fecha = cotizacion.get('fechaCreacion', 'N/A')[:10] if cotizacion.get('fechaCreacion') else 'N/A'
        
        print(f'{i:2d}. {numero}')
        print(f'    Cliente: {cliente}')
        print(f'    Vendedor: {vendedor}')
        print(f'    Proyecto: {proyecto}')
        print(f'    Fecha: {fecha}')
        print()

def ver_detalle(numero_buscar):
    """Ver detalle de una cotización específica"""
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cotizaciones = data.get('cotizaciones', [])
    
    cotizacion_encontrada = None
    for cotizacion in cotizaciones:
        if numero_buscar.upper() in cotizacion.get('numeroCotizacion', '').upper():
            cotizacion_encontrada = cotizacion
            break
    
    if cotizacion_encontrada:
        print(f'DETALLE COTIZACIÓN: {cotizacion_encontrada.get("numeroCotizacion")}')
        print('=' * 60)
        
        datos = cotizacion_encontrada.get('datosGenerales', {})
        print(f'Cliente: {datos.get("cliente", "N/A")}')
        print(f'Vendedor: {datos.get("vendedor", "N/A")}')
        print(f'Proyecto: {datos.get("proyecto", "N/A")}')
        print(f'Contacto: {datos.get("contacto", "N/A")}')
        print(f'Atención a: {datos.get("atencionA", "N/A")}')
        print(f'Revisión: {datos.get("revision", "N/A")}')
        
        condiciones = datos.get('condiciones', {})
        if condiciones:
            print(f'\nCONDICIONES:')
            print(f'  Moneda: {condiciones.get("moneda", "N/A")}')
            print(f'  Términos: {condiciones.get("terminos", "N/A")}')
            print(f'  Entrega en: {condiciones.get("entregaEn", "N/A")}')
            print(f'  Tipo cambio: {condiciones.get("tipoCambio", "N/A")}')
            print(f'  Tiempo entrega: {condiciones.get("tiempoEntrega", "N/A")}')
        
        items = cotizacion_encontrada.get('items', [])
        print(f'\nITEMS: {len(items)} item(s)')
        for i, item in enumerate(items, 1):
            print(f'  {i}. {item.get("descripcion", "N/A")}')
            print(f'     Cantidad: {item.get("cantidad", "N/A")}')
            print(f'     Total: ${item.get("total", "N/A")}')
            
            # Mostrar materiales si existen
            materiales = item.get('materiales', [])
            if materiales:
                print(f'     Materiales: {len(materiales)} material(es)')
                for j, material in enumerate(materiales, 1):
                    mat_nombre = material.get('material', 'N/A')
                    mat_cantidad = material.get('cantidad', 'N/A')
                    mat_subtotal = material.get('subtotal', 'N/A')
                    print(f'       {j}. {mat_nombre} - Qty: {mat_cantidad} - $${mat_subtotal}')
            
        print(f'\nMETADATA:')
        print(f'  ID: {cotizacion_encontrada.get("_id", "N/A")}')
        print(f'  Fecha creación: {cotizacion_encontrada.get("fechaCreacion", "N/A")}')
        print(f'  Sincronizada: {cotizacion_encontrada.get("sincronizada", False)}')
        print(f'  Fecha sincronización: {cotizacion_encontrada.get("fecha_sincronizacion", "N/A")}')
    else:
        print(f'Cotización con "{numero_buscar}" no encontrada')

def buscar_por_cliente(cliente_buscar):
    """Buscar cotizaciones por cliente"""
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cotizaciones = data.get('cotizaciones', [])
    encontradas = []
    
    for cotizacion in cotizaciones:
        cliente = cotizacion.get('datosGenerales', {}).get('cliente', '')
        if cliente_buscar.upper() in cliente.upper():
            encontradas.append(cotizacion)
    
    if encontradas:
        print(f'COTIZACIONES PARA CLIENTE "{cliente_buscar}": {len(encontradas)}')
        print('=' * 60)
        
        for i, cotizacion in enumerate(encontradas, 1):
            numero = cotizacion.get('numeroCotizacion', 'N/A')
            vendedor = cotizacion.get('datosGenerales', {}).get('vendedor', 'N/A')
            proyecto = cotizacion.get('datosGenerales', {}).get('proyecto', 'N/A')
            fecha = cotizacion.get('fechaCreacion', 'N/A')[:10] if cotizacion.get('fechaCreacion') else 'N/A'
            
            print(f'{i}. {numero}')
            print(f'   Vendedor: {vendedor}')
            print(f'   Proyecto: {proyecto}')
            print(f'   Fecha: {fecha}')
            print()
    else:
        print(f'No se encontraron cotizaciones para cliente "{cliente_buscar}"')

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Sin argumentos, mostrar resumen
        ver_resumen()
    elif len(sys.argv) == 2:
        # Un argumento, ver detalle por número
        ver_detalle(sys.argv[1])
    elif len(sys.argv) == 3 and sys.argv[1] == "cliente":
        # Buscar por cliente
        buscar_por_cliente(sys.argv[2])
    else:
        print("Uso:")
        print("  python ver_cotizaciones.py                    # Ver resumen")
        print("  python ver_cotizaciones.py MAZDA              # Ver detalle por número")
        print("  python ver_cotizaciones.py cliente Mazda      # Buscar por cliente")