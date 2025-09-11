#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Limpiar Cotizaciones de Mazda - Eliminar automáticamente todas las cotizaciones de Mazda
====================================================================================
"""

import json
from datetime import datetime

def limpiar_cotizaciones_mazda():
    """Eliminar todas las cotizaciones de Mazda"""
    
    # Hacer backup automático
    backup_filename = f'cotizaciones_backup_mazda_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear backup
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'[OK] Backup creado: {backup_filename}')
    
    cotizaciones = data.get('cotizaciones', [])
    cotizaciones_mazda = []
    cotizaciones_otras = []
    
    for cotizacion in cotizaciones:
        numero = cotizacion.get('numeroCotizacion', '')
        cliente = cotizacion.get('datosGenerales', {}).get('cliente', '')
        
        # Verificar si es cotización de Mazda
        if 'MAZDA' in numero.upper() or 'MAZDA' in cliente.upper():
            cotizaciones_mazda.append(cotizacion)
            print(f'[MAZDA] {numero} - {cliente}')
        else:
            cotizaciones_otras.append(cotizacion)
            print(f'[OTRAS] {numero} - {cliente}')
    
    print(f'\nRESUMEN:')
    print(f'  Cotizaciones de Mazda encontradas: {len(cotizaciones_mazda)}')
    print(f'  Otras cotizaciones: {len(cotizaciones_otras)}')
    
    if cotizaciones_mazda:
        # Actualizar el archivo eliminando las de Mazda
        data['cotizaciones'] = cotizaciones_otras
        
        with open('cotizaciones_offline.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f'\n[OK] LIMPIEZA DE MAZDA COMPLETADA:')
        print(f'  Cotizaciones de Mazda eliminadas: {len(cotizaciones_mazda)}')
        print(f'  Otras cotizaciones conservadas: {len(cotizaciones_otras)}')
        print(f'  Total antes: {len(cotizaciones)}')
        print(f'  Total después: {len(cotizaciones_otras)}')
        
        print(f'\nCOTIZACIONES DE MAZDA ELIMINADAS:')
        for cotizacion in cotizaciones_mazda:
            numero = cotizacion.get('numeroCotizacion', 'N/A')
            fecha = cotizacion.get('fechaCreacion', 'N/A')[:10] if cotizacion.get('fechaCreacion') else 'N/A'
            print(f'  [X] {numero} ({fecha})')
            
        if cotizaciones_otras:
            print(f'\nOTRAS COTIZACIONES CONSERVADAS:')
            for cotizacion in cotizaciones_otras:
                numero = cotizacion.get('numeroCotizacion', 'N/A')
                cliente = cotizacion.get('datosGenerales', {}).get('cliente', 'N/A')
                print(f'  [OK] {numero} - {cliente}')
        else:
            print(f'\n[INFO] No quedan otras cotizaciones - archivo completamente limpio')
    else:
        print(f'\nNo se encontraron cotizaciones de Mazda para eliminar')

if __name__ == "__main__":
    print("ELIMINACION AUTOMATICA DE COTIZACIONES DE MAZDA")
    print("=" * 50)
    limpiar_cotizaciones_mazda()