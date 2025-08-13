#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar que todos los registros fueron eliminados
Verifica tanto MongoDB como archivo JSON local
"""

import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def verificar_mongodb():
    """Verificar que MongoDB esté vacío"""
    try:
        # Obtener URI
        mongodb_uri = os.getenv('MONGODB_URI')
        if mongodb_uri:
            mongo_uri = mongodb_uri.strip()
        else:
            import urllib.parse
            usuario = os.getenv('MONGO_USERNAME', 'admin')
            contraseña = os.getenv('MONGO_PASSWORD', 'ADMIN123')
            cluster = os.getenv('MONGO_CLUSTER', 'cluster0.t4e0tp8.mongodb.net')
            database = os.getenv('MONGO_DATABASE', 'cotizaciones')
            
            usuario_encoded = urllib.parse.quote_plus(usuario)
            contraseña_encoded = urllib.parse.quote_plus(contraseña)
            
            mongo_uri = f"mongodb+srv://{usuario_encoded}:{contraseña_encoded}@{cluster}/{database}?retryWrites=true&w=majority&appName=Cluster0"
        
        # Conectar
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
        
        db = client['cotizaciones']
        collection = db['cotizacions']
        
        # Contar documentos
        total_mongo = collection.count_documents({})
        client.close()
        
        return total_mongo, None
        
    except Exception as e:
        return None, str(e)

def verificar_json():
    """Verificar que el archivo JSON esté vacío"""
    try:
        with open('cotizaciones_offline.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        cotizaciones = datos.get('cotizaciones', [])
        total_json = len(cotizaciones)
        
        return total_json, None
        
    except Exception as e:
        return None, str(e)

def main():
    """Función principal"""
    print("VERIFICACION DE LIMPIEZA COMPLETA")
    print("=" * 35)
    
    # Verificar MongoDB
    print("\n1. VERIFICANDO MONGODB...")
    total_mongo, error_mongo = verificar_mongodb()
    
    if error_mongo:
        print(f"   Error verificando MongoDB: {error_mongo}")
    else:
        print(f"   MongoDB registros: {total_mongo}")
        if total_mongo == 0:
            print("   MongoDB: VACIO - OK")
        else:
            print(f"   MongoDB: AUN TIENE {total_mongo} REGISTROS")
    
    # Verificar JSON
    print("\n2. VERIFICANDO ARCHIVO JSON...")
    total_json, error_json = verificar_json()
    
    if error_json:
        print(f"   Error verificando JSON: {error_json}")
    else:
        print(f"   JSON registros: {total_json}")
        if total_json == 0:
            print("   JSON: VACIO - OK")
        else:
            print(f"   JSON: AUN TIENE {total_json} REGISTROS")
    
    # Resultado final
    print("\n" + "=" * 35)
    print("RESULTADO FINAL:")
    
    limpieza_completa = True
    
    if error_mongo is None and total_mongo == 0:
        print("✓ MongoDB completamente limpio")
    else:
        print("✗ MongoDB no está limpio")
        limpieza_completa = False
    
    if error_json is None and total_json == 0:
        print("✓ Archivo JSON completamente limpio")
    else:
        print("✗ Archivo JSON no está limpio")
        limpieza_completa = False
    
    if limpieza_completa:
        print("\n🎉 LIMPIEZA COMPLETA EXITOSA")
        print("Todas las cotizaciones han sido eliminadas de todos los almacenamientos")
    else:
        print("\n⚠️  LIMPIEZA PARCIAL")
        print("Algunos registros pueden permanecer en algún almacenamiento")

if __name__ == "__main__":
    main()