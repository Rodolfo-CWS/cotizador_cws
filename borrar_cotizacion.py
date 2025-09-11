#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Borrar Cotización - Script para eliminar cotizaciones del JSON
============================================================
"""

import json
import sys
from datetime import datetime

def listar_cotizaciones():
    """Mostrar todas las cotizaciones disponibles"""
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cotizaciones = data.get('cotizaciones', [])
    print(f'COTIZACIONES DISPONIBLES: {len(cotizaciones)}')
    print('=' * 60)
    
    for i, cotizacion in enumerate(cotizaciones, 1):
        numero = cotizacion.get('numeroCotizacion', 'N/A')
        cliente = cotizacion.get('datosGenerales', {}).get('cliente', 'N/A')
        fecha = cotizacion.get('fechaCreacion', 'N/A')[:10] if cotizacion.get('fechaCreacion') else 'N/A'
        
        print(f'{i:2d}. {numero} - {cliente} ({fecha})')

def borrar_cotizacion(numero_buscar):
    """Borrar una cotización específica"""
    
    # Hacer backup automático
    backup_filename = f'cotizaciones_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear backup
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Backup creado: {backup_filename}')
    
    cotizaciones = data.get('cotizaciones', [])
    cotizaciones_filtradas = []
    cotizacion_eliminada = None
    
    for cotizacion in cotizaciones:
        numero = cotizacion.get('numeroCotizacion', '')
        if numero_buscar.upper() in numero.upper():
            cotizacion_eliminada = cotizacion
            print(f'ENCONTRADA: {numero}')
            print(f'Cliente: {cotizacion.get("datosGenerales", {}).get("cliente", "N/A")}')
            
            confirmacion = input('¿Estás seguro de eliminarla? (si/no): ')
            if confirmacion.lower() in ['si', 'sí', 'yes', 'y', 's']:
                print(f'Eliminando cotización: {numero}')
            else:
                print('Cancelado')
                cotizaciones_filtradas.append(cotizacion)
        else:
            cotizaciones_filtradas.append(cotizacion)
    
    if cotizacion_eliminada and len(cotizaciones_filtradas) < len(cotizaciones):
        # Actualizar el archivo
        data['cotizaciones'] = cotizaciones_filtradas
        
        with open('cotizaciones_offline.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f'✓ Cotización eliminada exitosamente')
        print(f'Total de cotizaciones: {len(cotizaciones)} → {len(cotizaciones_filtradas)}')
    elif not cotizacion_eliminada:
        print(f'No se encontró cotización con "{numero_buscar}"')

def borrar_por_cliente(cliente_buscar):
    """Borrar todas las cotizaciones de un cliente"""
    
    # Hacer backup automático
    backup_filename = f'cotizaciones_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear backup
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Backup creado: {backup_filename}')
    
    cotizaciones = data.get('cotizaciones', [])
    cotizaciones_cliente = []
    cotizaciones_filtradas = []
    
    for cotizacion in cotizaciones:
        cliente = cotizacion.get('datosGenerales', {}).get('cliente', '')
        if cliente_buscar.upper() in cliente.upper():
            cotizaciones_cliente.append(cotizacion)
        else:
            cotizaciones_filtradas.append(cotizacion)
    
    if cotizaciones_cliente:
        print(f'COTIZACIONES ENCONTRADAS PARA "{cliente_buscar}": {len(cotizaciones_cliente)}')
        for i, cotizacion in enumerate(cotizaciones_cliente, 1):
            numero = cotizacion.get('numeroCotizacion', 'N/A')
            fecha = cotizacion.get('fechaCreacion', 'N/A')[:10] if cotizacion.get('fechaCreacion') else 'N/A'
            print(f'  {i}. {numero} ({fecha})')
        
        confirmacion = input(f'¿Eliminar TODAS las {len(cotizaciones_cliente)} cotizaciones? (si/no): ')
        if confirmacion.lower() in ['si', 'sí', 'yes', 'y', 's']:
            # Actualizar el archivo
            data['cotizaciones'] = cotizaciones_filtradas
            
            with open('cotizaciones_offline.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f'✓ {len(cotizaciones_cliente)} cotizaciones eliminadas exitosamente')
            print(f'Total de cotizaciones: {len(cotizaciones)} → {len(cotizaciones_filtradas)}')
        else:
            print('Cancelado')
    else:
        print(f'No se encontraron cotizaciones para cliente "{cliente_buscar}"')

def limpiar_todas():
    """Limpiar todas las cotizaciones (mantener estructura)"""
    
    # Hacer backup automático
    backup_filename = f'cotizaciones_backup_completo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear backup
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Backup completo creado: {backup_filename}')
    
    cotizaciones_actuales = len(data.get('cotizaciones', []))
    
    print(f'ADVERTENCIA: Esto eliminará TODAS las {cotizaciones_actuales} cotizaciones')
    confirmacion = input('¿Estás ABSOLUTAMENTE seguro? Escribe "ELIMINAR TODO": ')
    
    if confirmacion == "ELIMINAR TODO":
        # Limpiar cotizaciones pero mantener estructura
        data['cotizaciones'] = []
        data['contadores'] = {}
        
        with open('cotizaciones_offline.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f'✓ Todas las cotizaciones han sido eliminadas')
        print(f'✓ Archivo limpio manteniendo estructura JSON')
    else:
        print('Cancelado - Texto no coincide')

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("GESTOR DE ELIMINACIÓN DE COTIZACIONES")
        print("=" * 40)
        print("Opciones:")
        print("  python borrar_cotizacion.py listar                    # Ver todas")
        print("  python borrar_cotizacion.py MAZDA-CWS-RM-001         # Borrar por número")
        print("  python borrar_cotizacion.py cliente Mazda            # Borrar por cliente")
        print("  python borrar_cotizacion.py limpiar                  # BORRAR TODAS")
        print()
        listar_cotizaciones()
        
    elif sys.argv[1] == "listar":
        listar_cotizaciones()
        
    elif sys.argv[1] == "limpiar":
        limpiar_todas()
        
    elif len(sys.argv) == 3 and sys.argv[1] == "cliente":
        borrar_por_cliente(sys.argv[2])
        
    elif len(sys.argv) == 2:
        borrar_cotizacion(sys.argv[1])
        
    else:
        print("Comando no válido. Usa sin argumentos para ver opciones.")