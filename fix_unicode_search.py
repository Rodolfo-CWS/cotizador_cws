#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIX UNICODE SEARCH - CWS COTIZADOR
=================================

Script para probar búsqueda sin errores de Unicode en Windows
"""

import pymongo
import json
from urllib.parse import quote_plus
import os
import sys

# Configurar codificación para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

def buscar_mongo_directo(termino):
    """Buscar directamente en MongoDB sin errores Unicode"""
    
    # Conectar a MongoDB
    username = quote_plus('admin')
    password = quote_plus('ADMIN123')
    cluster = 'cluster0.t4e0tp8.mongodb.net'
    database = 'cotizaciones'

    uri = f'mongodb+srv://{username}:{password}@{cluster}/{database}?retryWrites=true&w=majority'

    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
        db = client[database]
        collection = db['cotizacions']
        
        # Buscar por múltiples campos
        query = {
            "$or": [
                {"numeroCotizacion": {"$regex": termino, "$options": "i"}},
                {"datosGenerales.cliente": {"$regex": termino, "$options": "i"}},
                {"datosGenerales.vendedor": {"$regex": termino, "$options": "i"}},
                {"datosGenerales.proyecto": {"$regex": termino, "$options": "i"}}
            ]
        }
        
        resultados = list(collection.find(query).sort("fechaCreacion", -1))
        
        print(f"Busqueda: '{termino}' - {len(resultados)} resultados")
        
        for resultado in resultados:
            numero = resultado.get('numeroCotizacion', 'Sin numero')
            datos_gen = resultado.get('datosGenerales', {})
            cliente = datos_gen.get('cliente', 'Sin cliente')
            vendedor = datos_gen.get('vendedor', 'Sin vendedor')
            proyecto = datos_gen.get('proyecto', 'Sin proyecto')
            
            print(f"  - {numero}")
            print(f"    Cliente: {cliente}")
            print(f"    Vendedor: {vendedor}")
            print(f"    Proyecto: {proyecto}")
            
            # Si es MONGO, mostrar info del PDF
            if 'MONGO' in numero:
                print(f"    *** PDF DISPONIBLE ***")
                print(f"    URL: https://res.cloudinary.com/dvexwdihj/raw/upload/v1755641876/cotizaciones/nuevas/MONGO-CWS-CHR-001-R1-BOBY.pdf")
            print()
        
        return resultados

    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    print("=== BUSQUEDA DIRECTA SIN ERRORES UNICODE ===")
    print()
    
    # Probar búsquedas
    terminos = ['MONGO', 'CHR', 'BOBY', 'Chris']
    
    for termino in terminos:
        buscar_mongo_directo(termino)
        print("-" * 50)

if __name__ == "__main__":
    main()