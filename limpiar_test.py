#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Limpiar Cotizaciones de Prueba - Eliminar automáticamente cotizaciones de test
============================================================================
"""

import json
from datetime import datetime

def limpiar_cotizaciones_test():
    """Eliminar todas las cotizaciones de prueba/test/debug"""
    
    # Palabras clave que identifican cotizaciones de prueba
    keywords_test = ['TEST', 'DEBUG', 'CLIENTE-PRUEBA', 'PRUEBA', 'VALIDACION', 'VERIFICACION']
    
    # Hacer backup automático
    backup_filename = f'cotizaciones_backup_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear backup
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'[OK] Backup creado: {backup_filename}')
    
    cotizaciones = data.get('cotizaciones', [])
    cotizaciones_test = []
    cotizaciones_produccion = []
    
    for cotizacion in cotizaciones:
        numero = cotizacion.get('numeroCotizacion', '').upper()
        cliente = cotizacion.get('datosGenerales', {}).get('cliente', '').upper()
        proyecto = cotizacion.get('datosGenerales', {}).get('proyecto', '').upper()
        
        # Verificar si es cotización de prueba
        es_test = False
        for keyword in keywords_test:
            if keyword in numero or keyword in cliente or keyword in proyecto:
                es_test = True
                break
        
        if es_test:
            cotizaciones_test.append(cotizacion)
            print(f'[TEST] {cotizacion.get("numeroCotizacion")} - {cotizacion.get("datosGenerales", {}).get("cliente")}')
        else:
            cotizaciones_produccion.append(cotizacion)
            print(f'[PROD] {cotizacion.get("numeroCotizacion")} - {cotizacion.get("datosGenerales", {}).get("cliente")}')
    
    print(f'\nRESUMEN:')
    print(f'  Cotizaciones de prueba encontradas: {len(cotizaciones_test)}')
    print(f'  Cotizaciones de producción: {len(cotizaciones_produccion)}')
    
    if cotizaciones_test:
        # Actualizar el archivo manteniendo solo las de producción
        data['cotizaciones'] = cotizaciones_produccion
        
        with open('cotizaciones_offline.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f'\n[OK] LIMPIEZA COMPLETADA:')
        print(f'  Cotizaciones eliminadas: {len(cotizaciones_test)}')
        print(f'  Cotizaciones conservadas: {len(cotizaciones_produccion)}')
        print(f'  Total antes: {len(cotizaciones)}')
        print(f'  Total después: {len(cotizaciones_produccion)}')
        
        print(f'\nCOTIZACIONES ELIMINADAS:')
        for cotizacion in cotizaciones_test:
            numero = cotizacion.get('numeroCotizacion', 'N/A')
            cliente = cotizacion.get('datosGenerales', {}).get('cliente', 'N/A')
            print(f'  [X] {numero} - {cliente}')
            
        print(f'\nCOTIZACIONES CONSERVADAS:')
        for cotizacion in cotizaciones_produccion:
            numero = cotizacion.get('numeroCotizacion', 'N/A')
            cliente = cotizacion.get('datosGenerales', {}).get('cliente', 'N/A')
            print(f'  [OK] {numero} - {cliente}')
    else:
        print(f'\nNo se encontraron cotizaciones de prueba para eliminar')

if __name__ == "__main__":
    print("LIMPIEZA AUTOMÁTICA DE COTIZACIONES DE PRUEBA")
    print("=" * 50)
    limpiar_cotizaciones_test()