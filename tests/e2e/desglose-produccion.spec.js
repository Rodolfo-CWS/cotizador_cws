// tests/e2e/desglose-produccion.spec.js
import { test, expect } from '@playwright/test';

test.describe('Análisis de Formato - Desglose Producción', () => {

  test('capturar formato actual del desglose en producción', async ({ page }) => {
    // Ir directamente a la aplicación en producción
    console.log('🌐 Conectando a producción: https://cotizador-cws.onrender.com');
    await page.goto('https://cotizador-cws.onrender.com');
    await page.waitForLoadState('networkidle');
    
    // Capturar homepage
    await page.screenshot({ 
      path: 'screenshots/produccion-home.png',
      fullPage: true 
    });
    console.log('✓ Screenshot homepage de producción capturado');
    
    // Buscar una cotización existente
    const searchBox = page.locator('input[type="text"], input[name*="search"], input[id*="search"]').first();
    if (await searchBox.isVisible()) {
      await searchBox.fill('');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(2000);
    }
    
    // Capturar resultados de búsqueda
    await page.screenshot({ 
      path: 'screenshots/produccion-busqueda.png',
      fullPage: true 
    });
    console.log('✓ Screenshot búsqueda de producción capturado');
    
    // Buscar enlaces de "Ver Desglose" o similares
    const desgloseLinks = await page.locator('a:has-text("Ver"), a:has-text("Desglose"), a[href*="/desglose/"], a[href*="/ver/"]').all();
    
    if (desgloseLinks.length > 0) {
      console.log(`📋 Encontrados ${desgloseLinks.length} enlaces de desglose`);
      
      // Hacer clic en el primer enlace de desglose
      await desgloseLinks[0].click();
      await page.waitForLoadState('networkidle');
      
      // Capturar el desglose actual
      await page.screenshot({ 
        path: 'screenshots/produccion-desglose-actual.png',
        fullPage: true 
      });
      console.log('✓ Screenshot desglose actual capturado');
      
      // Analizar la estructura del desglose
      await test.step('analizar estructura de campos', async () => {
        const campos = await page.locator('.field, .campo, [class*="field"], [class*="campo"]').all();
        console.log(`📊 Encontrados ${campos.length} campos en el desglose`);
        
        // Capturar algunos campos específicos para análisis
        if (campos.length > 0) {
          await campos[0].screenshot({ 
            path: 'screenshots/produccion-campo-ejemplo.png'
          });
          console.log('✓ Ejemplo de campo capturado para análisis');
        }
        
        // Verificar alineación actual
        for (let i = 0; i < Math.min(3, campos.length); i++) {
          const campo = campos[i];
          const boundingBox = await campo.boundingBox();
          console.log(`Campo ${i + 1}: width=${boundingBox?.width}, height=${boundingBox?.height}`);
        }
      });
      
    } else {
      console.log('⚠️ No se encontraron enlaces de desglose. Capturando página actual para análisis');
      await page.screenshot({ 
        path: 'screenshots/produccion-no-desglose.png',
        fullPage: true 
      });
    }
    
  });

  test('análisis responsive del desglose', async ({ page }) => {
    // Conectar a producción
    await page.goto('https://cotizador-cws.onrender.com');
    await page.waitForLoadState('networkidle');
    
    // Buscar y acceder a un desglose
    const searchBox = page.locator('input[type="text"]').first();
    if (await searchBox.isVisible()) {
      await searchBox.fill('');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(2000);
      
      const desgloseLink = page.locator('a:has-text("Ver"), a:has-text("Desglose")').first();
      if (await desgloseLink.isVisible()) {
        await desgloseLink.click();
        await page.waitForLoadState('networkidle');
      }
    }
    
    // Test diferentes tamaños de pantalla
    const viewports = [
      { width: 1200, height: 800, name: 'desktop' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 375, height: 667, name: 'mobile' }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: `screenshots/produccion-desglose-${viewport.name}.png`,
        fullPage: true 
      });
      console.log(`✓ Screenshot ${viewport.name} capturado`);
    }
  });

});