#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para eliminar TODOS los registros de la colección MongoDB
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
    """Conectar a MongoDB usando las mismas configuraciones que la app"""
    try:
        # Detectar entorno
        es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
        es_produccion = os.getenv('FLASK_ENV') == 'production' or es_render
        
        print(f"Entorno detectado: {'Render/Producción' if es_produccion else 'Desarrollo local'}")
        
        # Obtener URI
        mongodb_uri = os.getenv('MONGODB_URI')
        
        if mongodb_uri:
            print("Usando MONGODB_URI de variables de entorno")
            mongo_uri = mongodb_uri.strip()
            # Extraer nombre de base de datos
            if '/cotizaciones' in mongodb_uri:
                database_name = 'cotizaciones'
            else:
                database_name = 'cotizaciones'  # fallback
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
        print(f"URI (primeros 50 chars): {mongo_uri[:50]}...")
        
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
        print("✅ Conexión a MongoDB exitosa")
        
        db = client[database_name]
        collection = db["cotizacions"]
        
        return client, db, collection
        
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}")
        return None, None, None

def mostrar_info_coleccion(collection):
    """Mostrar información actual de la colección"""
    try:
        total_docs = collection.count_documents({})
        print(f"\n📊 INFORMACIÓN ACTUAL:")
        print(f"   Total de documentos: {total_docs}")
        
        if total_docs > 0:
            # Mostrar algunos ejemplos
            print(f"\n📋 EJEMPLOS DE DOCUMENTOS (primeros 3):")
            ejemplos = list(collection.find().limit(3))
            for i, doc in enumerate(ejemplos, 1):
                numero_cot = doc.get('numeroCotizacion', 'Sin número')
                cliente = doc.get('datosGenerales', {}).get('cliente', 'Sin cliente')
                fecha = doc.get('fechaCreacion', 'Sin fecha')
                print(f"   {i}. Nº: {numero_cot} | Cliente: {cliente} | Fecha: {fecha[:10]}")
        
        return total_docs
        
    except Exception as e:
        print(f"❌ Error obteniendo información: {e}")
        return 0

def confirmar_eliminacion(total_docs):
    """Solicitar confirmación del usuario"""
    print(f"\n⚠️  ADVERTENCIA CRÍTICA:")
    print(f"   Estás a punto de ELIMINAR PERMANENTEMENTE {total_docs} documentos")
    print(f"   de la colección 'cotizacions' en la base de datos 'cotizaciones'")
    print(f"   Esta acción NO SE PUEDE DESHACER")
    
    print(f"\nPara confirmar, escribe exactamente: ELIMINAR TODOS")
    confirmacion = input("Confirmación: ").strip()
    
    return confirmacion == "ELIMINAR TODOS"

def eliminar_todos_registros(collection):
    """Eliminar todos los documentos de la colección"""
    try:
        print(f"\n🗑️  ELIMINANDO TODOS LOS REGISTROS...")
        
        # Usar deleteMany({}) para eliminar todos los documentos
        resultado = collection.delete_many({})
        
        print(f"✅ ELIMINACIÓN COMPLETADA:")
        print(f"   Documentos eliminados: {resultado.deleted_count}")
        print(f"   Timestamp: {datetime.datetime.now().isoformat()}")
        
        # Verificar que la colección esté vacía
        documentos_restantes = collection.count_documents({})
        print(f"   Documentos restantes: {documentos_restantes}")
        
        if documentos_restantes == 0:
            print(f"✅ ÉXITO: La colección está ahora completamente vacía")
        else:
            print(f"⚠️  ADVERTENCIA: Aún quedan {documentos_restantes} documentos")
        
        return resultado.deleted_count
        
    except Exception as e:
        print(f"❌ Error eliminando registros: {e}")
        return 0

def main():
    """Función principal"""
    print("🗑️  ELIMINADOR DE REGISTROS MONGODB")
    print("=" * 50)
    
    # Conectar a MongoDB
    client, db, collection = conectar_mongodb()
    
    if not client:
        print("❌ No se pudo conectar a MongoDB")
        return False
    
    try:
        # Mostrar información actual
        total_docs = mostrar_info_coleccion(collection)
        
        if total_docs == 0:
            print("✅ La colección ya está vacía")
            return True
        
        # Solicitar confirmación
        if not confirmar_eliminacion(total_docs):
            print("❌ Operación cancelada por el usuario")
            return False
        
        # Eliminar todos los registros
        eliminados = eliminar_todos_registros(collection)
        
        print(f"\n📊 RESUMEN FINAL:")
        print(f"   Total eliminados: {eliminados}")
        print(f"   Operación exitosa: {'Sí' if eliminados == total_docs else 'Parcial'}")
        
        return eliminados > 0
        
    finally:
        # Cerrar conexión
        if client:
            client.close()
            print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n❌ Operación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)