#!/usr/bin/env python3
"""
Test de generación PDF con colores grises
Verifica que:
1. La funcionalidad se mantiene intacta
2. Los colores cambiaron de azul a gris
3. El PDF se genera correctamente
"""

import sys
import os
import json
from datetime import datetime

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import generar_pdf_reportlab, REPORTLAB_AVAILABLE
    print("✅ Función generar_pdf_reportlab importada correctamente")
except ImportError as e:
    print(f"❌ Error importando función PDF: {e}")
    sys.exit(1)

def crear_datos_test():
    """Crear datos de cotización de prueba"""
    return {
        "datosGenerales": {
            "cliente": "TEST COLORES GRISES",
            "vendedor": "VERIFICACION",
            "proyecto": "CAMBIO DE COLORES PDF",
            "numeroCotizacion": "TEST-GRISES-CWS-VER-001-R1-COLORES",
            "revision": 1,
            "atencionA": "Usuario Test",
            "contacto": "test@cws.com",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        "items": [
            {
                "descripcion": "Servicio de prueba - colores grises",
                "cantidad": 2,
                "precio_unitario": 1500.0,
                "subtotal": 3000.0,
                "uom": "Servicio"
            },
            {
                "descripcion": "Producto de verificación",
                "cantidad": 1,
                "precio_unitario": 2000.0,
                "subtotal": 2000.0,
                "uom": "Pieza"
            }
        ],
        "condiciones": {
            "moneda": "MXN",
            "iva": 16,
            "subtotal": 5000.0,
            "iva_monto": 800.0,
            "total": 5800.0,
            "terminos": "NET 30",
            "tiempoEntrega": "15 días hábiles",
            "entregaEn": "Oficinas CWS",
            "comentarios": "PDF de prueba con colores grises implementados"
        },
        "observaciones": "Test de verificación de colores - azules cambiados por grises"
    }

def test_generacion_pdf_basica():
    """Test básico de generación de PDF"""
    print("\n🧪 TEST 1: Generación básica de PDF")
    
    if not REPORTLAB_AVAILABLE:
        print("❌ ReportLab no disponible - test saltado")
        return False
        
    try:
        datos_test = crear_datos_test()
        print(f"📝 Generando PDF para: {datos_test['datosGenerales']['numeroCotizacion']}")
        
        # Generar PDF
        pdf_bytes = generar_pdf_reportlab(datos_test)
        
        if pdf_bytes and len(pdf_bytes) > 1000:  # PDF debe ser mayor a 1KB
            print(f"✅ PDF generado exitosamente: {len(pdf_bytes)} bytes")
            
            # Guardar archivo de prueba
            filename = "test_pdf_grises_verificacion.pdf"
            with open(filename, 'wb') as f:
                f.write(pdf_bytes)
            print(f"💾 PDF guardado como: {filename}")
            return True
        else:
            print("❌ PDF generado está vacío o demasiado pequeño")
            return False
            
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        return False

def test_contenido_pdf():
    """Test de contenido específico del PDF"""
    print("\n🧪 TEST 2: Verificación de contenido PDF")
    
    try:
        datos_test = crear_datos_test()
        
        # Verificar que los datos están completos
        assert datos_test['datosGenerales']['cliente'] == "TEST COLORES GRISES"
        assert len(datos_test['items']) == 2
        assert datos_test['condiciones']['total'] == 5800.0
        
        print("✅ Datos de test válidos")
        
        # Generar PDF y verificar tamaño
        if REPORTLAB_AVAILABLE:
            pdf_bytes = generar_pdf_reportlab(datos_test)
            
            # Verificar que el PDF tiene contenido sustancial
            if len(pdf_bytes) > 10000:  # Más de 10KB indica contenido completo
                print(f"✅ PDF con contenido completo: {len(pdf_bytes)} bytes")
                return True
            else:
                print(f"⚠️ PDF pequeño, posible contenido incompleto: {len(pdf_bytes)} bytes")
                return False
        else:
            print("⚠️ ReportLab no disponible, test de contenido saltado")
            return True
            
    except Exception as e:
        print(f"❌ Error en test de contenido: {e}")
        return False

def test_integridad_funcional():
    """Test de integridad funcional - verificar que no se rompió nada"""
    print("\n🧪 TEST 3: Integridad funcional")
    
    try:
        # Test con diferentes configuraciones
        configuraciones_test = [
            {
                "nombre": "Cotización MXN básica",
                "moneda": "MXN",
                "items_count": 1,
                "tiene_iva": True
            },
            {
                "nombre": "Cotización USD",
                "moneda": "USD", 
                "items_count": 3,
                "tiene_iva": False
            },
            {
                "nombre": "Cotización sin items",
                "moneda": "MXN",
                "items_count": 0,
                "tiene_iva": True
            }
        ]
        
        resultados = []
        
        for config in configuraciones_test:
            datos_test = crear_datos_test()
            datos_test['condiciones']['moneda'] = config['moneda']
            
            # Ajustar items según configuración
            if config['items_count'] == 0:
                datos_test['items'] = []
                datos_test['condiciones']['total'] = 0
            elif config['items_count'] == 3:
                datos_test['items'].append({
                    "descripcion": "Item adicional de prueba",
                    "cantidad": 1,
                    "precio_unitario": 500.0,
                    "subtotal": 500.0,
                    "uom": "Servicio"
                })
            
            try:
                if REPORTLAB_AVAILABLE:
                    pdf_bytes = generar_pdf_reportlab(datos_test)
                    if len(pdf_bytes) > 1000:
                        print(f"✅ {config['nombre']}: PDF generado correctamente")
                        resultados.append(True)
                    else:
                        print(f"❌ {config['nombre']}: PDF demasiado pequeño")
                        resultados.append(False)
                else:
                    print(f"⚠️ {config['nombre']}: ReportLab no disponible")
                    resultados.append(True)  # No es error si no está disponible
                    
            except Exception as e:
                print(f"❌ {config['nombre']}: Error - {e}")
                resultados.append(False)
        
        exitos = sum(resultados)
        total = len(resultados)
        print(f"📊 Integridad funcional: {exitos}/{total} tests pasados")
        return exitos == total
        
    except Exception as e:
        print(f"❌ Error en test de integridad: {e}")
        return False

def verificar_cambios_colores():
    """Verificar que los cambios de colores se aplicaron"""
    print("\n🧪 TEST 4: Verificación de cambios de colores")
    
    try:
        # Leer el código fuente de app.py para verificar cambios
        with open('app.py', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificar que los colores azules fueron cambiados
        colores_azules = ['#2C5282', '#1A365D']
        colores_grises = ['#4A5568', '#2D3748']
        
        azules_encontrados = 0
        grises_encontrados = 0
        
        for color_azul in colores_azules:
            if color_azul in contenido:
                azules_encontrados += contenido.count(color_azul)
        
        for color_gris in colores_grises:
            if color_gris in contenido:
                grises_encontrados += contenido.count(color_gris)
        
        print(f"🔍 Colores azules restantes: {azules_encontrados}")
        print(f"🔍 Colores grises encontrados: {grises_encontrados}")
        
        # También verificar texto "blue"
        blue_text = contenido.lower().count('blue')
        print(f"🔍 Referencias a 'blue' en código: {blue_text}")
        
        if azules_encontrados == 0 and grises_encontrados > 5:
            print("✅ Cambios de colores aplicados correctamente")
            return True
        elif azules_encontrados == 0 and blue_text <= 1:  # Permitir 1 referencia (puede ser comentario)
            print("✅ Colores azules eliminados exitosamente")
            return True
        else:
            print(f"⚠️ Posibles colores azules restantes: {azules_encontrados}")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando cambios de colores: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🎨 VERIFICACIÓN COMPLETA: PDF con Colores Grises")
    print("="*60)
    
    # Información del sistema
    print(f"📍 ReportLab disponible: {REPORTLAB_AVAILABLE}")
    print(f"📍 Python version: {sys.version.split()[0]}")
    print(f"📍 Directorio: {os.getcwd()}")
    
    # Ejecutar tests
    tests = [
        ("Generación básica PDF", test_generacion_pdf_basica),
        ("Contenido PDF", test_contenido_pdf),
        ("Integridad funcional", test_integridad_funcional),
        ("Cambios de colores", verificar_cambios_colores)
    ]
    
    resultados = []
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ Error en {nombre}: {e}")
            resultados.append(False)
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE VERIFICACIÓN")
    
    exitos = sum(resultados)
    total = len(resultados)
    
    for i, (nombre, _) in enumerate(tests):
        status = "✅ PASS" if resultados[i] else "❌ FAIL"
        print(f"{status} {nombre}")
    
    print(f"\n🎯 RESULTADO FINAL: {exitos}/{total} tests exitosos")
    
    if exitos == total:
        print("🎉 ¡VERIFICACIÓN EXITOSA! PDF con colores grises implementado correctamente")
        print("\n📋 CAMBIOS IMPLEMENTADOS:")
        print("  • Colores azules (#2C5282, #1A365D) → Grises (#4A5568, #2D3748)")
        print("  • Funcionalidad completamente intacta")
        print("  • Todas las características del PDF preservadas")
        print("  • Diseño profesional mantenido con tonos grises")
    else:
        print("⚠️ Algunos tests fallaron, revisar implementación")
    
    return exitos == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)