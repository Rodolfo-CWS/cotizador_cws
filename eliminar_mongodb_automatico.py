#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script automático para eliminar TODOS los registros de MongoDB
Base de datos: cotizaciones
Colección: cotizacions
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
import datetime

# Cargar variables de entorno
load_dotenv()

def conectar_mongodb():
    """Conectar a MongoDB"""
    try:
        # Detectar entorno
        es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
        es_produccion = os.getenv('FLASK_ENV') == 'production' or es_render
        
        print(f"Entorno detectado: {'Produccion' if es_produccion else 'Desarrollo local'}")
        
        # Obtener URI
        mongodb_uri = os.getenv('MONGODB_URI')
        
        if mongodb_uri:
            print("Usando MONGODB_URI de variables de entorno")
            mongo_uri = mongodb_uri.strip()
            database_name = 'cotizaciones'
        else:
            # Usar variables separadas
            import urllib.parse
            usuario = os.getenv('MONGO_USERNAME', 'admin')
            contraseña = os.getenv('MONGO_PASSWORD', 'ADMIN123')
            cluster = os.getenv('MONGO_CLUSTER', 'cluster0.t4e0tp8.mongodb.net')
            database = os.getenv('MONGO_DATABASE', 'cotizaciones')
            
            usuario_encoded = urllib.parse.quote_plus(usuario)
            contraseña_encoded = urllib.parse.quote_plus(contraseña)
            
            timeout = "30000" if es_produccion else "10000"
            mongo_uri = f"mongodb+srv://{usuario_encoded}:{contraseña_encoded}@{cluster}/{database}?retryWrites=true&w=majority&appName=Cluster0&connectTimeoutMS={timeout}&serverSelectionTimeoutMS={timeout}"
            database_name = database
        
        print(f"Base de datos: {database_name}")
        
        # Crear cliente
        timeout_ms = 30000 if es_produccion else 10000
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms,
            socketTimeoutMS=timeout_ms,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        
        # Verificar conexión
        client.admin.command('ping')
        print("Conexion a MongoDB exitosa")
        
        db = client[database_name]
        collection = db["cotizacions"]
        
        return client, db, collection
        
    except Exception as e:
        print(f"Error conectando a MongoDB: {e}")
        return None, None, None

def main():
    """Función principal - ejecuta automáticamente"""
    print("ELIMINADOR AUTOMATICO DE REGISTROS MONGODB")
    print("=" * 45)
    
    # Conectar a MongoDB
    client, db, collection = conectar_mongodb()
    
    if not client:
        print("No se pudo conectar a MongoDB")
        return False
    
    try:
        # Contar documentos actuales
        total_docs = collection.count_documents({})
        print(f"Total de documentos encontrados: {total_docs}")
        
        if total_docs == 0:
            print("La coleccion ya esta vacia")
            return True
        
        # Mostrar algunos ejemplos
        print(f"\nMostrando ejemplos de {min(5, total_docs)} documentos:")
        ejemplos = list(collection.find().limit(5))
        for i, doc in enumerate(ejemplos, 1):
            numero_cot = doc.get('numeroCotizacion', 'Sin numero')
            cliente = doc.get('datosGenerales', {}).get('cliente', 'Sin cliente')
            fecha = doc.get('fechaCreacion', 'Sin fecha')[:10] if doc.get('fechaCreacion') else 'Sin fecha'
            print(f"  {i}. {numero_cot} | {cliente} | {fecha}")
        
        # Ejecutar eliminación automática
        print(f"\nEjecutando eliminacion automatica de {total_docs} documentos...")
        resultado = collection.delete_many({})
        
        print(f"\n--- RESULTADO ---")
        print(f"Documentos eliminados: {resultado.deleted_count}")
        print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificar que la colección esté vacía
        documentos_restantes = collection.count_documents({})
        print(f"Documentos restantes: {documentos_restantes}")
        
        if documentos_restantes == 0:
            print("EXITO: La coleccion MongoDB esta ahora completamente vacia")
        else:
            print(f"ADVERTENCIA: Aun quedan {documentos_restantes} documentos")
        
        return resultado.deleted_count > 0
        
    finally:
        # Cerrar conexión
        if client:
            client.close()
            print("\nConexion MongoDB cerrada")

if __name__ == "__main__":
    try:
        exito = main()
        if exito:
            print("\n✓ Eliminacion completada exitosamente")
            print("Tu coleccion de MongoDB ahora esta vacia")
        else:
            print("\n✗ No se pudo completar la eliminacion")
    except Exception as e:
        print(f"\nError: {e}")

# Mensaje final
print("\nNota: Este script elimino SOLO los registros de MongoDB.")
print("Si tambien tienes registros en archivo JSON local, estos permanecen intactos.")