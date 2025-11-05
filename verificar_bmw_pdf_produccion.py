"""
Script para verificar el estado del PDF BMW en producción
Consulta directamente la URL de producción para diagnosticar el problema
"""

import requests
import json

BASE_URL = "https://cotizador-cws.onrender.com"

print("=" * 80)
print("VERIFICACIÓN PDF BMW EN PRODUCCIÓN")
print("=" * 80)
print()

# 1. Buscar la cotización
print("1. BÚSQUEDA DE LA COTIZACIÓN")
print("-" * 80)

numero_cotizacion = "BMW-CWS-FM-002-R1-INSTALACIÓ"

try:
    # Buscar usando el endpoint de búsqueda
    response = requests.post(
        f"{BASE_URL}/buscar",
        json={"query": "BMW-CWS-FM-002"},
        timeout=10
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Búsqueda exitosa")
        print(f"  Resultados encontrados: {data.get('total', 0)}")

        if data.get('resultados'):
            print("\n  Primeros resultados:")
            for i, resultado in enumerate(data['resultados'][:3], 1):
                print(f"    {i}. {resultado.get('numero_cotizacion', 'N/A')}")
                print(f"       Cliente: {resultado.get('cliente', 'N/A')}")
                print(f"       URL PDF: {resultado.get('url', 'N/A') or resultado.get('ruta_completa', 'N/A')}")

                # Si encontramos el BMW, guardar la info
                if 'BMW' in resultado.get('numero_cotizacion', ''):
                    bmw_info = resultado
                    print(f"\n  ✓ ENCONTRADO PDF BMW:")
                    print(f"    Número: {bmw_info.get('numero_cotizacion')}")
                    print(f"    Tipo: {bmw_info.get('tipo', 'N/A')}")
                    print(f"    URL: {bmw_info.get('url', 'N/A')}")
                    print(f"    Ruta completa: {bmw_info.get('ruta_completa', 'N/A')}")
                    print(f"    Tiene desglose: {bmw_info.get('tiene_desglose', False)}")
    else:
        print(f"✗ Error en búsqueda: {response.status_code}")
        print(f"  Response: {response.text[:200]}")

except Exception as e:
    print(f"✗ Excepción en búsqueda: {e}")

print()

# 2. Intentar obtener el PDF directamente
print("2. INTENTAR OBTENER PDF DIRECTAMENTE")
print("-" * 80)

# Variaciones posibles del nombre
variaciones = [
    "BMW-CWS-FM-002-R1-INSTALACIÓ",
    "BMW-CWS-FM-002-R1-INSTALACIO",
    "Cotizacion_BMW-CWS-FM-002-R1-INSTALACIÓ",
    "Cotizacion_BMW-CWS-FM-002-R1-INSTALACIO",
]

pdf_encontrado = False

for variacion in variaciones:
    print(f"\nProbando: {variacion}")

    try:
        # URL encode el nombre
        from urllib.parse import quote
        variacion_encoded = quote(variacion, safe='')

        url_pdf = f"{BASE_URL}/pdf/{variacion_encoded}"
        print(f"  URL: {url_pdf}")

        response = requests.get(url_pdf, timeout=10, allow_redirects=True)

        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"  Content-Length: {response.headers.get('Content-Length', 'N/A')}")

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')

            if 'application/pdf' in content_type:
                print(f"  ✓ PDF ENCONTRADO!")
                print(f"  Tamaño: {len(response.content)} bytes")

                # Verificar que es un PDF válido
                if response.content.startswith(b'%PDF'):
                    print(f"  ✓ PDF VÁLIDO (firma %PDF encontrada)")
                    pdf_encontrado = True
                else:
                    print(f"  ✗ Contenido no parece ser PDF válido")
                    print(f"  Primeros bytes: {response.content[:20]}")
            elif 'application/json' in content_type:
                # Probablemente un error JSON
                try:
                    error_data = response.json()
                    print(f"  ✗ Error JSON: {error_data}")
                except:
                    print(f"  ✗ Response JSON inválido: {response.text[:200]}")
            else:
                print(f"  ✗ Content-Type inesperado")
                print(f"  Contenido: {response.text[:200]}")

        elif response.status_code == 404:
            print(f"  ✗ PDF no encontrado (404)")

        elif response.status_code == 500:
            print(f"  ✗ Error del servidor (500)")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('error', 'Unknown')}")
            except:
                print(f"  Response: {response.text[:200]}")

        else:
            print(f"  ✗ Status code inesperado: {response.status_code}")
            print(f"  Response: {response.text[:200]}")

        if pdf_encontrado:
            break

    except Exception as e:
        print(f"  ✗ Excepción: {e}")

print()

# 3. Verificar endpoint de desglose
print("3. VERIFICAR ENDPOINT DE DESGLOSE")
print("-" * 80)

try:
    # Intentar obtener el desglose
    from urllib.parse import quote
    numero_encoded = quote("BMW-CWS-FM-002-R1-INSTALACIÓ", safe='')

    url_desglose = f"{BASE_URL}/desglose/{numero_encoded}"
    print(f"URL: {url_desglose}")

    response = requests.get(url_desglose, timeout=10)

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        print(f"✓ Desglose accesible")

        # Verificar si hay un enlace al PDF en el HTML
        if 'href="/pdf/' in response.text:
            print("✓ Encontrado enlace a PDF en el desglose")

            # Extraer el enlace
            import re
            matches = re.findall(r'href="/pdf/([^"]+)"', response.text)
            if matches:
                print(f"  Enlace(s) encontrado(s):")
                for match in matches:
                    print(f"    /pdf/{match}")
        else:
            print("✗ No se encontró enlace a PDF en el desglose")
    else:
        print(f"✗ Error accediendo desglose: {response.status_code}")

except Exception as e:
    print(f"✗ Excepción verificando desglose: {e}")

print()

# Resumen
print("=" * 80)
print("RESUMEN")
print("=" * 80)

if pdf_encontrado:
    print("✓ El PDF existe y es accesible desde producción")
    print("\nPróximos pasos:")
    print("1. Verificar el enlace exacto en la interfaz de usuario")
    print("2. Revisar JavaScript/eventos de click en el frontend")
    print("3. Verificar console del navegador por errores")
else:
    print("✗ El PDF NO se pudo acceder desde producción")
    print("\nPosibles causas:")
    print("1. El PDF se creó antes de configurar SUPABASE_SERVICE_KEY")
    print("2. El PDF se perdió en un redeploy (solo estaba local)")
    print("3. El nombre del archivo tiene problemas de encoding (Ó vs O)")
    print("4. El PDF nunca se subió a Supabase Storage exitosamente")
    print("\nSolución recomendada:")
    print("1. Crear una nueva revisión (R2) del PDF BMW")
    print("2. Verificar en logs que se suba a Supabase Storage")
    print("3. Confirmar que la nueva revisión se puede abrir")

print("=" * 80)
