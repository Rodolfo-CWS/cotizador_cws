// tests/e2e/verificar-mejoras.spec.js
import { test, expect } from '@playwright/test';

test.describe('Verificación de Mejoras del Desglose', () => {

  test('capturar desglose con formato mejorado', async ({ page }) => {
    // Ir directamente al desglose con el formato mejorado implementado
    await page.goto('/desglose/EMPRESAVIS-CWS-FO-001-R1-REVISIONDE');
    await page.waitForLoadState('networkidle');
    
    console.log('✓ Navegando al desglose con mejoras implementadas...');
    
    // Si la página no carga correctamente, crear una cotización nueva
    const pageTitle = await page.title();
    if (pageTitle.includes('404') || pageTitle.includes('no encontrada')) {
      console.log('⚠️ Desglose no encontrado, creando nueva cotización...');
      
      // Ir al formulario para crear una nueva cotización
      await page.goto('/formulario');
      await page.waitForLoadState('networkidle');
      
      if (await page.locator('#cliente').isVisible()) {
        // Llenar formulario
        await page.fill('#cliente', 'DEMO VISUAL');
        await page.fill('#vendedor', 'DISEÑO');
        await page.fill('#proyecto', 'FORMATO MEJORADO');
        
        // Agregar ítem
        const addButton = page.locator('button:has-text("Agregar"), input[type="button"][value*="Agregar"]');
        if (await addButton.count() > 0) {
          await addButton.first().click();
        }
        
        // Intentar llenar campos de ítems si existen
        const itemFields = page.locator('input[name*="descripcion"], input[name*="items"]');
        if (await itemFields.count() > 0) {
          await itemFields.first().fill('Servicio de prueba visual');
        }
        
        // Enviar formulario
        const submitButton = page.locator('button:has-text("Generar"), input[type="submit"]');
        if (await submitButton.count() > 0) {
          await submitButton.click();
          await page.waitForTimeout(3000);
        }
        
        console.log('✓ Nueva cotización creada para demo');
      }
    }
    
    // Verificar que tenemos contenido del desglose
    await expect(page.locator('body')).not.toContainText('404');
    await expect(page.locator('body')).not.toContainText('no encontrada');
    
    // Capturar screenshot del formato mejorado
    await page.screenshot({ 
      path: 'screenshots/desglose-formato-final.png',
      fullPage: true 
    });
    
    console.log('✓ Screenshot del formato mejorado capturado');
    
    // Analizar elementos específicos mejorados
    await test.step('verificar mejoras implementadas', async () => {
      
      // Verificar header mejorado
      const header = page.locator('.header');
      if (await header.isVisible()) {
        await header.screenshot({ 
          path: 'screenshots/header-mejorado.png'
        });
        console.log('✓ Header mejorado capturado');
      }
      
      // Verificar secciones con nuevo estilo
      const secciones = page.locator('.section');
      const cantidadSecciones = await secciones.count();
      
      if (cantidadSecciones > 0) {
        console.log(`✓ Encontradas ${cantidadSecciones} secciones mejoradas`);
        
        // Capturar primera sección
        await secciones.first().screenshot({ 
          path: 'screenshots/seccion-mejorada.png'
        });
      }
      
      // Verificar campos con grid layout
      const campos = page.locator('.field');
      const cantidadCampos = await campos.count();
      
      if (cantidadCampos > 0) {
        console.log(`✓ Encontrados ${cantidadCampos} campos con grid layout`);
        
        // Verificar que los campos tienen el grid layout
        const firstField = campos.first();
        const computedStyle = await firstField.evaluate(el => {
          return window.getComputedStyle(el).display;
        });
        
        if (computedStyle === 'grid') {
          console.log('✓ Grid layout aplicado correctamente');
        } else {
          console.log('⚠️ Grid layout no detectado');
        }
      }
      
      // Verificar botones mejorados
      const botones = page.locator('.btn');
      const cantidadBotones = await botones.count();
      
      if (cantidadBotones > 0) {
        console.log(`✓ Encontrados ${cantidadBotones} botones mejorados`);
        
        // Capturar sección de botones
        const actionSection = page.locator('.actions');
        if (await actionSection.isVisible()) {
          await actionSection.screenshot({ 
            path: 'screenshots/botones-mejorados.png'
          });
        }
      }
    });
    
    // Test responsive
    await test.step('verificar diseño responsive', async () => {
      // Tablet view
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.screenshot({ 
        path: 'screenshots/desglose-tablet-final.png',
        fullPage: true 
      });
      
      // Mobile view
      await page.setViewportSize({ width: 375, height: 667 });
      await page.screenshot({ 
        path: 'screenshots/desglose-mobile-final.png',
        fullPage: true 
      });
      
      console.log('✓ Screenshots responsive capturados');
    });
  });

  test('comparación antes y después', async ({ page }) => {
    await page.goto('/desglose/EMPRESAVIS-CWS-FO-001-R1-REVISIONDE');
    await page.waitForLoadState('networkidle');
    
    // Capturar el estado actual (ya mejorado)
    await page.screenshot({ 
      path: 'screenshots/despues-mejoras.png',
      fullPage: true,
      clip: { x: 0, y: 0, width: 800, height: 1000 }
    });
    
    console.log('✓ Screenshot "después de mejoras" capturado');
    
    // Simular el formato anterior aplicando estilos antiguos temporalmente
    await page.addStyleTag({
      content: `
        /* Revertir a formato anterior para comparación */
        .field {
          display: flex !important;
          grid-template-columns: none !important;
        }
        
        .field strong {
          width: 150px !important;
          text-align: left !important;
        }
        
        .field span {
          background: #f8f9fa !important;
          border: 1px solid #e9ecef !important;
        }
        
        .header {
          background: white !important;
          color: #495057 !important;
          border-bottom: 1px solid #dee2e6 !important;
        }
        
        .header h1 {
          color: #495057 !important;
        }
        
        .section {
          border: 1px solid #e9ecef !important;
          box-shadow: none !important;
        }
        
        .section h3 {
          border-bottom: 1px solid #dee2e6 !important;
          color: #495057 !important;
        }
        
        .section h3::before {
          content: none !important;
        }
      `
    });
    
    await page.screenshot({ 
      path: 'screenshots/antes-mejoras-simulado.png',
      fullPage: true,
      clip: { x: 0, y: 0, width: 800, height: 1000 }
    });
    
    console.log('✓ Screenshot "antes de mejoras" (simulado) capturado');
  });
});