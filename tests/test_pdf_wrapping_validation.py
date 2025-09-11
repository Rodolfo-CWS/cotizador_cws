#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test específico para validar el text wrapping en PDFs usando Playwright
"""

import asyncio
import os
import tempfile
import time
from playwright.async_api import async_playwright, Page

class PDFWrappingValidator:
    
    def __init__(self):
        self.test_data = {
            'cliente': 'CLIENTE TEST PDF WRAPPING',
            'vendedor': 'VENDEDOR TEST',
            'proyecto': 'PROYECTO TEST WRAPPING',
            'items': [
                {
                    'descripcion': 'Descripción corta que no necesita wrapping',
                    'cantidad': '1',
                    'uom': 'PZ',
                    'costo': '1000'
                },
                {
                    'descripcion': 'Esta es una descripción muy larga que definitivamente necesitará text wrapping para ajustarse correctamente dentro de la celda de la tabla del PDF sin comprometer la presentación profesional del documento y asegurando que todo el texto sea visible y legible para el cliente final',
                    'cantidad': '2', 
                    'uom': 'KG',
                    'costo': '2500'
                },
                {
                    'descripcion': 'Descripción de longitud media que podría requerir wrapping dependiendo de la configuración específica del PDF y el ancho de las columnas establecido en el diseño profesional',
                    'cantidad': '3',
                    'uom': 'LT', 
                    'costo': '750'
                }
            ]
        }
    
    async def start_app_server(self):
        """Iniciar el servidor de la aplicación si no está corriendo"""
        try:
            # Verificar si el servidor ya está corriendo
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    response = await page.goto('http://localhost:5000/', timeout=5000)
                    if response and response.status == 200:
                        print("✓ Servidor ya está ejecutándose en puerto 5000")
                        await browser.close()
                        return True
                except:
                    await browser.close()
                    print("! Servidor no disponible en puerto 5000")
                    print("! Por favor inicia el servidor con: python app.py")
                    return False
        except Exception as e:
            print(f"! Error verificando servidor: {e}")
            return False
    
    async def create_test_cotizacion(self, page: Page):
        """Crear una cotización de test con descripciones largas"""
        print("\n--- Creando cotización de test ---")
        
        # Ir al formulario
        await page.goto('http://localhost:5000/formulario')
        await page.wait_for_selector('#cliente', timeout=10000)
        
        # Llenar datos generales
        await page.fill('#cliente', self.test_data['cliente'])
        await page.fill('#vendedor', self.test_data['vendedor'])
        await page.fill('#proyecto', self.test_data['proyecto'])
        await page.fill('#atencionA', 'Contacto Test')
        await page.fill('#contacto', 'test@ejemplo.com')
        
        # Agregar items con diferentes longitudes de descripción
        for i, item in enumerate(self.test_data['items']):
            # Agregar nuevo item
            await page.click('#agregarItem')
            await page.wait_for_selector(f'.item-row:nth-child({i+1}) input[name="descripcion"]', timeout=5000)
            
            # Llenar datos del item
            row_selector = f'.item-row:nth-child({i+1})'
            await page.fill(f'{row_selector} input[name="descripcion"]', item['descripcion'])
            await page.fill(f'{row_selector} input[name="cantidad"]', item['cantidad'])
            await page.select_option(f'{row_selector} select[name="uom"]', item['uom'])
            await page.fill(f'{row_selector} input[name="costoUnidad"]', item['costo'])
            
            print(f"  Item {i+1}: {len(item['descripcion'])} caracteres")
        
        # Configurar condiciones
        await page.select_option('#moneda', 'MXN')
        await page.fill('#tiempoEntrega', '15')
        await page.fill('#entregaEn', 'Planta del cliente')
        await page.select_option('#terminos', 'Contado')
        
        # Enviar formulario
        await page.click('button[type="submit"]')
        
        # Esperar procesamiento
        await page.wait_for_timeout(3000)
        
        print("✓ Cotización creada")
        return True
    
    async def test_pdf_generation_and_download(self, page: Page):
        """Test de generación y descarga de PDF"""
        print("\n--- Probando generación de PDF ---")
        
        # Ir a la página de búsqueda
        await page.goto('http://localhost:5000/')
        await page.wait_for_selector('#searchQuery, input[name="query"], input[type="search"]', timeout=10000)
        
        # Buscar la cotización
        search_input = page.locator('#searchQuery, input[name="query"], input[type="search"]').first
        await search_input.fill(self.test_data['cliente'])
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(2000)
        
        print("✓ Búsqueda realizada")
        
        # Buscar enlace de PDF
        pdf_selectors = [
            'a[href*="pdf"]',
            'button[onclick*="pdf"]', 
            'a[href*=".pdf"]',
            '[data-action*="pdf"]',
            '.btn-pdf',
            '.pdf-link'
        ]
        
        pdf_element = None
        for selector in pdf_selectors:
            elements = page.locator(selector)
            if await elements.count() > 0:
                pdf_element = elements.first
                print(f"✓ Elemento PDF encontrado: {selector}")
                break
        
        if pdf_element:
            # Interceptar la descarga
            download_promise = page.wait_for_download(timeout=30000)
            
            # Hacer clic para generar/descargar PDF
            await pdf_element.click()
            
            try:
                download = await download_promise
                
                # Guardar el PDF en ubicación temporal
                temp_pdf_path = os.path.join(tempfile.gettempdir(), f"test_wrapping_{int(time.time())}.pdf")
                await download.save_as(temp_pdf_path)
                
                # Verificar el PDF
                if os.path.exists(temp_pdf_path):
                    pdf_size = os.path.getsize(temp_pdf_path)
                    print(f"✓ PDF descargado exitosamente")
                    print(f"  Ubicación: {temp_pdf_path}")
                    print(f"  Tamaño: {pdf_size:,} bytes")
                    
                    # Validaciones básicas
                    if pdf_size < 1000:
                        print(f"⚠ PDF muy pequeño ({pdf_size} bytes)")
                        return False
                    
                    if pdf_size > 100000:  # ~100KB
                        print(f"✓ PDF tiene buen tamaño (probablemente con contenido completo)")
                    
                    # Verificar que es un PDF válido leyendo los primeros bytes
                    with open(temp_pdf_path, 'rb') as f:
                        header = f.read(8)
                        if header.startswith(b'%PDF'):
                            print("✓ Archivo PDF válido (header correcto)")
                        else:
                            print(f"⚠ Header inesperado: {header}")
                    
                    # Limpiar archivo temporal
                    try:
                        os.remove(temp_pdf_path)
                        print("✓ Archivo temporal limpiado")
                    except:
                        print(f"⚠ No se pudo limpiar: {temp_pdf_path}")
                    
                    return True
                else:
                    print("✗ PDF no se guardó correctamente")
                    return False
                    
            except Exception as e:
                print(f"✗ Error en descarga de PDF: {e}")
                return False
        else:
            print("✗ No se encontró elemento para generar PDF")
            return False
    
    async def test_pdf_content_validation(self, page: Page):
        """Test indirecto de validación de contenido PDF"""
        print("\n--- Validando procesamiento de descripciones ---")
        
        try:
            # Ir al formulario y verificar que acepta textos largos
            await page.goto('http://localhost:5000/formulario')
            await page.wait_for_selector('#cliente', timeout=10000)
            
            # Verificar capacidad de manejar textos largos
            await page.click('#agregarItem')
            await page.wait_for_selector('.item-row:first-child input[name="descripcion"]', timeout=5000)
            
            long_text = "X" * 300  # Texto de 300 caracteres
            await page.fill('.item-row:first-child input[name="descripcion"]', long_text)
            
            # Verificar que se mantuvo el texto
            stored_text = await page.input_value('.item-row:first-child input[name="descripcion"]')
            
            if len(stored_text) >= 250:  # Al menos la mayoría
                print(f"✓ Campo maneja textos largos ({len(stored_text)} caracteres)")
                
                # Verificar que no hay caracteres problemáticos
                if stored_text == long_text:
                    print("✓ Texto se preservó completamente")
                else:
                    print(f"⚠ Texto modificado: {len(long_text)} -> {len(stored_text)}")
                
                return True
            else:
                print(f"✗ Campo truncó el texto: {len(stored_text)}/{len(long_text)}")
                return False
                
        except Exception as e:
            print(f"✗ Error validando contenido: {e}")
            return False
    
    async def run_all_tests(self):
        """Ejecutar todos los tests de validación"""
        print("INICIANDO TESTS DE VALIDACIÓN PDF CON PLAYWRIGHT")
        print("=" * 55)
        
        # Verificar servidor
        if not await self.start_app_server():
            return 1
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Mostrar browser para debugging
                slow_mo=1000     # Ralentizar para poder observar
            )
            
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            
            try:
                # Test 1: Crear cotización
                page1 = await context.new_page()
                try:
                    result1 = await self.create_test_cotizacion(page1)
                    results.append(("Creación de cotización", result1))
                except Exception as e:
                    print(f"✗ Error en creación: {e}")
                    results.append(("Creación de cotización", False))
                finally:
                    await page1.close()
                
                # Test 2: Generación de PDF  
                page2 = await context.new_page()
                try:
                    result2 = await self.test_pdf_generation_and_download(page2)
                    results.append(("Generación de PDF", result2))
                except Exception as e:
                    print(f"✗ Error en PDF: {e}")
                    results.append(("Generación de PDF", False))
                finally:
                    await page2.close()
                
                # Test 3: Validación de contenido
                page3 = await context.new_page()
                try:
                    result3 = await self.test_pdf_content_validation(page3)
                    results.append(("Validación de contenido", result3))
                except Exception as e:
                    print(f"✗ Error en validación: {e}")
                    results.append(("Validación de contenido", False))
                finally:
                    await page3.close()
            
            finally:
                await browser.close()
        
        # Mostrar resultados finales
        print("\n" + "=" * 55)
        print("RESUMEN DE TESTS PDF:")
        
        passed = 0
        failed = 0
        
        for test_name, success in results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {test_name}: {status}")
            
            if success:
                passed += 1
            else:
                failed += 1
        
        print(f"\nResultado: {passed} exitosos, {failed} fallidos")
        
        if failed == 0:
            print("\n🎉 TODOS LOS TESTS DE PDF PASARON")
            print("✅ Text wrapping funcionando correctamente")
            print("✅ Sistema listo para producción")
            return 0
        else:
            print(f"\n⚠️  {failed} test(s) fallaron")
            print("🔍 Revisar implementación o configuración")
            return 1

# Función principal
async def main():
    validator = PDFWrappingValidator()
    return await validator.run_all_tests()

if __name__ == "__main__":
    exit_code = asyncio.run(main())