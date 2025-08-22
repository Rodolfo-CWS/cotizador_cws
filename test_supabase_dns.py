#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de conectividad DNS y PostgreSQL para Supabase
"""

import os
import sys
import socket
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_dns_resolution():
    """Test básico de resolución DNS"""
    print("=== TEST DNS RESOLUTION ===")
    
    database_url = os.getenv('DATABASE_URL', '')
    print(f"DATABASE_URL configurada: {bool(database_url)}")
    
    if database_url:
        # Extraer host de la URL
        try:
            # postgresql://postgres:DwFPdF3XUJ%40@db.qxzxtmvjrcacysmjcjhx.supabase.co:6543/postgres
            parts = database_url.split('@')
            if len(parts) > 1:
                host_port = parts[1].split('/')[0]
                host = host_port.split(':')[0]
                port = int(host_port.split(':')[1])
                
                print(f"Host extraido: {host}")
                print(f"Puerto extraido: {port}")
                
                # Test DNS
                try:
                    print("Probando resolucion DNS...")
                    ip = socket.gethostbyname(host)
                    print(f"DNS OK - IP resuelta: {ip}")
                    
                    # Test TCP connection
                    print("Probando conexion TCP...")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    if result == 0:
                        print("TCP OK - Puerto accesible")
                        return True
                    else:
                        print(f"TCP FAIL - Puerto no accesible: {result}")
                        return False
                        
                except socket.gaierror as e:
                    print(f"DNS FAIL - Error resolucion: {e}")
                    return False
                except Exception as e:
                    print(f"TCP FAIL - Error conexion: {e}")
                    return False
                    
        except Exception as e:
            print(f"ERROR - Parsing URL: {e}")
            return False
    else:
        print("ERROR - DATABASE_URL no configurada")
        return False

def test_postgresql_connection():
    """Test directo de conexión PostgreSQL"""
    print("\n=== TEST POSTGRESQL CONNECTION ===")
    
    database_url = os.getenv('DATABASE_URL', '')
    
    if not database_url:
        print("ERROR - DATABASE_URL no configurada")
        return False
    
    try:
        print("Intentando conexion PostgreSQL...")
        print(f"URL (primeros 50 chars): {database_url[:50]}...")
        
        conn = psycopg2.connect(
            database_url,
            connect_timeout=10,
            application_name="CWS_Test_DNS"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"POSTGRESQL OK - Version: {version[:100]}...")
        return True
        
    except Exception as e:
        print(f"POSTGRESQL FAIL - Error: {e}")
        return False

def main():
    """Test principal"""
    print("DIAGNOSTICO SUPABASE - DNS Y CONECTIVIDAD")
    print("=" * 50)
    
    # Test DNS
    dns_ok = test_dns_resolution()
    
    # Test PostgreSQL si DNS funciona
    if dns_ok:
        pg_ok = test_postgresql_connection()
        
        if pg_ok:
            print("\n*** RESULTADO: CONEXION EXITOSA ***")
            print("Supabase deberia funcionar correctamente")
        else:
            print("\n*** RESULTADO: PROBLEMA POSTGRESQL ***")
            print("DNS funciona pero PostgreSQL falla")
    else:
        print("\n*** RESULTADO: PROBLEMA DNS ***")
        print("No se puede resolver el host de Supabase")
        print("Posibles causas:")
        print("1. URL incorrecta en .env")
        print("2. Proyecto Supabase pausado o eliminado")
        print("3. Problema de red/firewall")

if __name__ == "__main__":
    main()