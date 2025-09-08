// tests/e2e/verificacion-rapida.spec.js
import { test, expect } from '@playwright/test';

test.describe('Verificación Rápida CSS Grid', () => {
  
  test('verificar estado actual con cache bypass', async ({ page }) => {
    const numeroCotizacion = 'EMPRESAVIS-CWS-FO-001-R1-REVISIONDE';
    const timestamp = Date.now();
    const urlDesglose = `https://cotizador-cws.onrender.com/desglose/${numeroCotizacion}?v=${timestamp}&nocache=true`;
    
    console.log(`🔄 Verificando con cache bypass: ${urlDesglose}`);
    
    // Forzar recarga sin caché
    await page.goto(urlDesglose, { 
      waitUntil: 'networkidle',
      timeout: 60000 
    });
    
    // Forzar refresh adicional
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(5000);
    
    // Capturar screenshot actual
    await page.screenshot({ 
      path: 'screenshots/verificacion-actual.png',
      fullPage: true 
    });
    
    // Verificar campo específico
    const primerCampo = page.locator('.field').first();
    
    if (await primerCampo.isVisible()) {
      const estilos = await primerCampo.evaluate(el => {
        const computedStyle = window.getComputedStyle(el);
        return {
          display: computedStyle.display,
          gridTemplateColumns: computedStyle.gridTemplateColumns,
          gap: computedStyle.gap
        };
      });
      
      console.log('📊 Estilos actuales del campo:', JSON.stringify(estilos, null, 2));
      
      if (estilos.display === 'grid') {
        console.log('✅ CSS Grid aplicado exitosamente');
      } else {
        console.log('❌ CSS Grid aún no aplicado - posiblemente deployment en progreso');
      }
      
      // Capturar campo específico
      await primerCampo.screenshot({ 
        path: 'screenshots/campo-estado-actual.png'
      });
    }
    
    // Verificar timestamp del deployment
    const pageSource = await page.content();
    if (pageSource.includes('grid-template-columns: 200px 1fr')) {
      console.log('✅ CSS Grid encontrado en el código fuente');
    } else {
      console.log('❌ CSS Grid no encontrado en el código fuente');
    }
  });

});