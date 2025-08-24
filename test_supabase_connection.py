import os
import psycopg2
from dotenv import load_dotenv

def test_connection():
    """
    Carga las variables de entorno y prueba la conexión a la base de datos de Supabase.
    """
    print("--- Iniciando prueba de conexión a Supabase ---")
    
    # Cargar variables desde .env
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: La variable de entorno DATABASE_URL no se encontró en el archivo .env.")
        return

    print(f"✅ Variable DATABASE_URL encontrada.")
    # No imprimimos la URL completa por seguridad.

    try:
        print("\n🔌 Intentando conectar a la base de datos PostgreSQL...")
        
        # Intentar conectar
        conn = psycopg2.connect(
            database_url,
            connect_timeout=10
        )
        
        print("✅ ¡Conexión exitosa!")
        
        # Realizar una consulta simple para verificar
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test;")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            print("✅ Consulta de prueba exitosa. La base de datos respondió correctamente.")
        else:
            print("⚠️ ADVERTENCIA: La conexión se estableció, pero la consulta de prueba falló.")
            
        cursor.close()
        conn.close()
        print("🔌 Conexión cerrada.")
        
    except psycopg2.OperationalError as e:
        print("\n❌ ERROR DE CONEXIÓN OPERACIONAL:")
        print("   Este error usualmente indica un problema de red, firewall o credenciales incorrectas.")
        print(f"   Detalles: {e}")
        
    except Exception as e:
        print(f"\n❌ Ocurrió un error inesperado: {e}")

    print("\n--- Prueba de conexión finalizada ---")

if __name__ == "__main__":
    test_connection()
