#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para buscar la cotización MONGOS-CWS-CM-001-R1-BOBOX
"""

import os
import sys
import json
import datetime
from dotenv import load_dotenv
from pathlib import Path

# Agregar la ruta del directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
load_dotenv()

def buscar_en_offline():
    """Busca la cotización en el archivo offline"""
    print("=" * 60)
    print("BUSCANDO EN ARCHIVO OFFLINE")
    print("=" * 60)
    
    archivo_offline = "cotizaciones_offline.json"
    if not os.path.exists(archivo_offline):
        print(f"[ERROR] Archivo {archivo_offline} no encontrado")
        return None
    
    try:
        with open(archivo_offline, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        cotizaciones = datos.get("cotizaciones", [])
        numero_buscado = "MONGOS-CWS-CM-001-R1-BOBOX"
        
        print(f"[INFO] Total de cotizaciones en archivo offline: {len(cotizaciones)}")
        print(f"[BUSCAR] Buscando cotizacion: {numero_buscado}")
        print()
        
        # Buscar coincidencia exacta
        for cotizacion in cotizaciones:
            numero_actual = cotizacion.get("numeroCotizacion", "")
            if numero_actual == numero_buscado:
                print("[EXITO] COTIZACION ENCONTRADA EN ARCHIVO OFFLINE!")
                mostrar_detalles_cotizacion(cotizacion, "OFFLINE")
                return cotizacion
        
        # Buscar coincidencias similares
        print("[BUSCAR] Buscando variaciones del numero...")
        coincidencias_similares = []
        
        for cotizacion in cotizaciones:
            numero_actual = cotizacion.get("numeroCotizacion", "").upper()
            
            # Buscar por partes del número
            if any(parte in numero_actual for parte in ["MONGOS", "MONGO", "CM-001", "BOBOX"]):
                coincidencias_similares.append(cotizacion)
        
        if coincidencias_similares:
            print(f"[RESULTADO] Encontradas {len(coincidencias_similares)} cotizaciones similares:")
            for i, cot in enumerate(coincidencias_similares, 1):
                numero = cot.get("numeroCotizacion", "")
                cliente = cot.get("datosGenerales", {}).get("cliente", "N/A")
                vendedor = cot.get("datosGenerales", {}).get("vendedor", "N/A")
                fecha = cot.get("fechaCreacion", "N/A")[:10] if cot.get("fechaCreacion") else "N/A"
                print(f"   {i}. {numero} - Cliente: {cliente} - Vendedor: {vendedor} - Fecha: {fecha}")
        else:
            print(f"[NO ENCONTRADO] Cotizacion {numero_buscado} NO encontrada en archivo offline")
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Error leyendo archivo offline: {e}")
        return None

def buscar_en_mongodb():
    """Busca la cotización en MongoDB"""
    print("=" * 60)
    print("BUSCANDO EN MONGODB")
    print("=" * 60)
    
    try:
        from pymongo import MongoClient
        
        # Configurar conexión
        mongodb_uri = os.getenv('MONGODB_URI')
        if mongodb_uri:
            print("[INFO] Usando MONGODB_URI de variables de entorno")
            mongo_uri = mongodb_uri
            database_name = 'cotizador_cws' if '/cotizador_cws' in mongodb_uri else 'cotizaciones'
        else:
            print("[INFO] Construyendo URI desde variables separadas")
            import urllib.parse
            usuario = os.getenv('MONGO_USERNAME', 'admin')
            contraseña = os.getenv('MONGO_PASSWORD', 'ADMIN123')
            cluster = os.getenv('MONGO_CLUSTER', 'cluster0.t4e0tp8.mongodb.net')
            database = os.getenv('MONGO_DATABASE', 'cotizaciones')
            
            usuario_encoded = urllib.parse.quote_plus(usuario)
            contraseña_encoded = urllib.parse.quote_plus(contraseña)
            
            mongo_uri = f"mongodb+srv://{usuario_encoded}:{contraseña_encoded}@{cluster}/{database}?retryWrites=true&w=majority&appName=Cluster0&connectTimeoutMS=10000&serverSelectionTimeoutMS=10000"
            database_name = database
        
        print(f"[INFO] Base de datos: {database_name}")
        print("[INFO] Conectando a MongoDB...")
        
        # Conectar
        client = MongoClient(mongo_uri)
        db = client[database_name]
        collection = db["cotizacions"]
        
        # Verificar conexión
        client.admin.command('ping')
        print("[EXITO] Conexion a MongoDB exitosa")
        
        numero_buscado = "MONGOS-CWS-CM-001-R1-BOBOX"
        print(f"[BUSCAR] Buscando cotizacion: {numero_buscado}")
        
        # Buscar cotización exacta
        cotizacion = collection.find_one({"numeroCotizacion": numero_buscado})
        
        if cotizacion:
            print("[EXITO] COTIZACION ENCONTRADA EN MONGODB!")
            cotizacion["_id"] = str(cotizacion["_id"])
            mostrar_detalles_cotizacion(cotizacion, "MONGODB")
            client.close()
            return cotizacion
        
        # Buscar variaciones similares
        print("[BUSCAR] Buscando variaciones...")
        
        # Buscar por regex
        import re
        pattern = re.compile("mongos.*cm.*001.*bobox", re.IGNORECASE)
        cotizaciones_similares = list(collection.find({"numeroCotizacion": {"$regex": pattern}}))
        
        if not cotizaciones_similares:
            # Buscar por partes
            filtros = [
                {"numeroCotizacion": {"$regex": "MONGOS", "$options": "i"}},
                {"numeroCotizacion": {"$regex": "MONGO", "$options": "i"}},
                {"numeroCotizacion": {"$regex": "CM-001", "$options": "i"}},
                {"numeroCotizacion": {"$regex": "BOBOX", "$options": "i"}},
                {"datosGenerales.cliente": {"$regex": "MONGO", "$options": "i"}}
            ]
            
            for filtro in filtros:
                resultados = list(collection.find(filtro).limit(10))
                cotizaciones_similares.extend(resultados)
        
        if cotizaciones_similares:
            # Eliminar duplicados
            numeros_vistos = set()
            cotizaciones_unicas = []
            
            for cot in cotizaciones_similares:
                numero = cot.get("numeroCotizacion", "")
                if numero not in numeros_vistos:
                    numeros_vistos.add(numero)
                    cotizaciones_unicas.append(cot)
            
            print(f"[RESULTADO] Encontradas {len(cotizaciones_unicas)} cotizaciones similares:")
            for i, cot in enumerate(cotizaciones_unicas[:10], 1):
                numero = cot.get("numeroCotizacion", "")
                cliente = cot.get("datosGenerales", {}).get("cliente", "N/A")
                vendedor = cot.get("datosGenerales", {}).get("vendedor", "N/A")
                fecha = cot.get("fechaCreacion", "N/A")[:10] if cot.get("fechaCreacion") else "N/A"
                print(f"   {i}. {numero} - Cliente: {cliente} - Vendedor: {vendedor} - Fecha: {fecha}")
        else:
            print(f"[NO ENCONTRADO] Cotizacion {numero_buscado} NO encontrada en MongoDB")
        
        client.close()
        return None
        
    except ImportError:
        print("[ERROR] pymongo no esta instalado. Instalar con: pip install pymongo")
        return None
    except Exception as e:
        print(f"[ERROR] Error conectando a MongoDB: {e}")
        return None

def verificar_pdf_google_drive():
    """Verifica si existe el PDF en Google Drive"""
    print("=" * 60)
    print("VERIFICANDO PDF EN GOOGLE DRIVE")
    print("=" * 60)
    
    try:
        # Verificar directorio de Google Drive
        directorio_nuevas = Path("G:/Mi unidad/CWS/CWS_Cotizaciones_PDF/nuevas")
        
        if not directorio_nuevas.exists():
            print(f"[ERROR] Directorio no encontrado: {directorio_nuevas}")
            print("   Verificar que Google Drive este sincronizado y montado en G:")
            return None
        
        print(f"[INFO] Directorio encontrado: {directorio_nuevas}")
        
        # Buscar archivo PDF
        nombre_pdf = "Cotizacion_MONGOS-CWS-CM-001-R1-BOBOX.pdf"
        archivo_pdf = directorio_nuevas / nombre_pdf
        
        if archivo_pdf.exists():
            print("[EXITO] PDF ENCONTRADO!")
            print(f"[INFO] Archivo: {archivo_pdf}")
            stat = archivo_pdf.stat()
            print(f"[INFO] Tamano: {stat.st_size:,} bytes")
            print(f"[INFO] Fecha modificacion: {datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            return str(archivo_pdf)
        
        # Buscar variaciones
        print("[BUSCAR] Buscando variaciones del PDF...")
        
        patrones = [
            "*MONGOS*BOBOX*.pdf",
            "*MONGO*CM*001*.pdf",
            "*BOBOX*.pdf",
            "*CM-001*.pdf"
        ]
        
        archivos_encontrados = []
        for patron in patrones:
            archivos = list(directorio_nuevas.glob(patron))
            archivos_encontrados.extend(archivos)
        
        if archivos_encontrados:
            archivos_unicos = list(set(archivos_encontrados))
            
            print(f"[RESULTADO] Encontrados {len(archivos_unicos)} archivos PDF similares:")
            for i, archivo in enumerate(archivos_unicos[:10], 1):
                stat = archivo.stat()
                fecha_mod = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   {i}. {archivo.name} - {stat.st_size:,} bytes - {fecha_mod}")
        else:
            print("[NO ENCONTRADO] No se encontraron PDFs relacionados")
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Error verificando Google Drive: {e}")
        return None

def mostrar_detalles_cotizacion(cotizacion, fuente):
    """Muestra los detalles principales de una cotización"""
    print(f"[DETALLES] COTIZACION ({fuente}):")
    print("   " + "─" * 50)
    
    # Datos generales
    datos_generales = cotizacion.get("datosGenerales", {})
    print(f"   Numero: {cotizacion.get('numeroCotizacion', 'N/A')}")
    print(f"   Cliente: {datos_generales.get('cliente', 'N/A')}")
    print(f"   Vendedor: {datos_generales.get('vendedor', 'N/A')}")
    print(f"   Proyecto: {datos_generales.get('proyecto', 'N/A')}")
    print(f"   Atencion a: {datos_generales.get('atencionA', 'N/A')}")
    print(f"   Contacto: {datos_generales.get('contacto', 'N/A')}")
    print(f"   Revision: {datos_generales.get('revision', cotizacion.get('revision', 'N/A'))}")
    
    # Fecha
    fecha_creacion = cotizacion.get("fechaCreacion", "")
    if fecha_creacion:
        try:
            if 'T' in fecha_creacion:
                fecha_obj = datetime.datetime.fromisoformat(fecha_creacion.replace('Z', '+00:00'))
                fecha_formateada = fecha_obj.strftime('%Y-%m-%d %H:%M:%S')
            else:
                fecha_formateada = fecha_creacion
            print(f"   Fecha creacion: {fecha_formateada}")
        except:
            print(f"   Fecha creacion: {fecha_creacion}")
    
    # Items
    items = cotizacion.get("items", [])
    print(f"   Total de items: {len(items)}")
    
    if items:
        print(f"   Primer item: {items[0].get('descripcion', 'N/A')}")
        if len(items) > 1:
            print(f"        ... y {len(items) - 1} item(s) mas")
    
    # Condiciones
    condiciones = cotizacion.get("condiciones", {})
    if condiciones:
        moneda = condiciones.get("moneda", "N/A")
        tiempo_entrega = condiciones.get("tiempoEntrega", "N/A")
        entrega_en = condiciones.get("entregaEn", "N/A")
        print(f"   Moneda: {moneda}")
        print(f"   Tiempo entrega: {tiempo_entrega}")
        print(f"   Entrega en: {entrega_en}")
    
    # Información de respaldo
    if cotizacion.get("respaldo_de_mongodb"):
        print("   [INFO] Respaldada desde MongoDB")
    
    if cotizacion.get("sincronizada"):
        print("   [INFO] Sincronizada con MongoDB")
    
    print()

def main():
    """Función principal"""
    print("BUSCADOR DE COTIZACION CWS")
    print("=" * 60)
    print("Cotizacion a buscar: MONGOS-CWS-CM-001-R1-BOBOX")
    print(f"Fecha de busqueda: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    resultados = {
        "offline": None,
        "mongodb": None,
        "pdf_drive": None
    }
    
    # 1. Buscar en archivo offline
    resultados["offline"] = buscar_en_offline()
    
    # 2. Buscar en MongoDB
    resultados["mongodb"] = buscar_en_mongodb()
    
    # 3. Verificar PDF en Google Drive
    resultados["pdf_drive"] = verificar_pdf_google_drive()
    
    # Resumen final
    print("=" * 60)
    print("RESUMEN FINAL DE BUSQUEDA")
    print("=" * 60)
    
    encontrada_en = []
    
    if resultados["offline"]:
        encontrada_en.append("Archivo offline")
    
    if resultados["mongodb"]:
        encontrada_en.append("MongoDB")
    
    if resultados["pdf_drive"]:
        encontrada_en.append("Google Drive (PDF)")
    
    if encontrada_en:
        print("Cotizacion MONGOS-CWS-CM-001-R1-BOBOX encontrada en:")
        for fuente in encontrada_en:
            print(f"   • {fuente}")
    else:
        print("Cotizacion MONGOS-CWS-CM-001-R1-BOBOX NO encontrada en ninguna fuente")
        print()
        print("POSIBLES CAUSAS:")
        print("   • El numero de cotizacion puede estar mal escrito")
        print("   • La cotizacion puede existir con un numero diferente")
        print("   • Los datos pueden estar en una base de datos diferente")
        print("   • Problemas de conexion con MongoDB")
        print("   • Google Drive no esta sincronizado correctamente")
    
    print()
    print("RECOMENDACIONES:")
    print("   • Verificar el numero exacto de la cotizacion")
    print("   • Revisar las cotizaciones similares encontradas")
    print("   • Comprobar el estado de sincronizacion de Google Drive")
    print("   • Contactar al administrador del sistema si persisten problemas")
    
    return resultados

if __name__ == "__main__":
    try:
        resultados = main()
        
        # Código de salida basado en resultados
        if any(resultados.values()):
            sys.exit(0)  # Encontrada
        else:
            sys.exit(1)  # No encontrada
            
    except KeyboardInterrupt:
        print("\nBusqueda cancelada por el usuario")
        sys.exit(2)
    except Exception as e:
        print(f"\nError inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)