// tests/e2e/desglose-directo-prod.spec.js
import { test, expect } from '@playwright/test';

test.describe('Análisis Directo del Desglose - Producción', () => {

  test('acceso directo a desglose específico en producción', async ({ page }) => {
    // Usar la cotización que creé específicamente para análisis visual
    const numeroCotizacion = 'EMPRESAVIS-CWS-FO-001-R1-REVISIONDE';
    const urlDesglose = `https://cotizador-cws.onrender.com/desglose/${numeroCotizacion}`;
    
    console.log(`🎯 Accediendo directamente al desglose: ${urlDesglose}`);
    
    // Ir directamente al desglose
    await page.goto(urlDesglose);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000); // Dar tiempo extra para que cargue completamente
    
    // Capturar el desglose actual completo
    await page.screenshot({ 
      path: 'screenshots/desglose-actual-produccion.png',
      fullPage: true 
    });
    console.log('✓ Screenshot del desglose actual capturado');
    
    // Verificar si cargó correctamente (no es 404)
    const pageTitle = await page.title();
    const bodyText = await page.textContent('body');
    
    if (pageTitle.includes('404') || bodyText.includes('404') || bodyText.includes('no encontrada')) {
      console.log('⚠️ Desglose no encontrado, probando con otra cotización...');
      
      // Probar con cotización BMW que existe en el JSON
      const cotizacionAlternativa = 'BMW-CWS-CM-008-R2-GROW';
      await page.goto(`https://cotizador-cws.onrender.com/desglose/${cotizacionAlternativa}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
      
      await page.screenshot({ 
        path: 'screenshots/desglose-bmw-produccion.png',
        fullPage: true 
      });
      console.log('✓ Screenshot desglose BMW capturado como alternativa');
    }
    
    // Analizar estructura específica de campos
    await test.step('análisis detallado de campos', async () => {
      
      // Buscar diferentes posibles selectores de campos
      const posiblesCampos = [
        '.field',
        '.campo', 
        '[class*="field"]',
        '[class*="campo"]',
        '.cotizacion-field',
        '.dato',
        'p:has(strong)',
        'div:has(strong)'
      ];
      
      let camposEncontrados = [];
      
      for (const selector of posiblesCampos) {
        const campos = await page.locator(selector).all();
        if (campos.length > 0) {
          console.log(`📊 Encontrados ${campos.length} campos con selector: ${selector}`);
          camposEncontrados.push({ selector, cantidad: campos.length });
          
          // Capturar algunos ejemplos
          if (campos.length > 0) {
            await campos[0].screenshot({ 
              path: `screenshots/campo-ejemplo-${selector.replace(/[^a-zA-Z0-9]/g, '')}.png`
            });
          }
        }
      }
      
      // Si encontramos campos, analizar su estilo
      if (camposEncontrados.length > 0) {
        const mejorSelector = camposEncontrados[0].selector;
        const campos = await page.locator(mejorSelector).all();
        
        console.log(`🔍 Analizando estilo de campos con selector: ${mejorSelector}`);
        
        // Analizar estilos de los primeros 3 campos
        for (let i = 0; i < Math.min(3, campos.length); i++) {
          const campo = campos[i];
          
          const estilos = await campo.evaluate(el => {
            const computedStyle = window.getComputedStyle(el);
            return {
              display: computedStyle.display,
              gridTemplateColumns: computedStyle.gridTemplateColumns,
              flexDirection: computedStyle.flexDirection,
              alignItems: computedStyle.alignItems,
              width: computedStyle.width,
              padding: computedStyle.padding,
              margin: computedStyle.margin
            };
          });
          
          console.log(`Campo ${i + 1} estilos:`, JSON.stringify(estilos, null, 2));
        }
        
        // Capturar sección completa de campos
        const primeraSeccion = page.locator('.section, [class*="section"]').first();
        if (await primeraSeccion.isVisible()) {
          await primeraSeccion.screenshot({ 
            path: 'screenshots/seccion-campos-actual.png'
          });
          console.log('✓ Sección de campos capturada para análisis');
        }
      } else {
        console.log('⚠️ No se encontraron campos con ningún selector estándar');
        
        // Capturar toda la página para análisis manual
        await page.screenshot({ 
          path: 'screenshots/pagina-completa-para-analisis.png',
          fullPage: true 
        });
      }
    });
  });
  
  test('análisis responsive del desglose en producción', async ({ page }) => {
    const numeroCotizacion = 'EMPRESAVIS-CWS-FO-001-R1-REVISIONDE';
    const urlDesglose = `https://cotizador-cws.onrender.com/desglose/${numeroCotizacion}`;
    
    await page.goto(urlDesglose);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Si no carga, probar con BMW
    const bodyText = await page.textContent('body');
    if (bodyText.includes('404')) {
      await page.goto('https://cotizador-cws.onrender.com/desglose/BMW-CWS-CM-008-R2-GROW');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
    }
    
    // Diferentes tamaños de pantalla
    const viewports = [
      { width: 1200, height: 800, name: 'desktop-wide' },
      { width: 900, height: 700, name: 'desktop-standard' },
      { width: 768, height: 1024, name: 'tablet-portrait' },
      { width: 1024, height: 768, name: 'tablet-landscape' },
      { width: 375, height: 667, name: 'mobile-portrait' },
      { width: 667, height: 375, name: 'mobile-landscape' }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(1500);
      
      await page.screenshot({ 
        path: `screenshots/desglose-responsive-${viewport.name}.png`,
        fullPage: true 
      });
      console.log(`✓ Screenshot responsive ${viewport.name} (${viewport.width}x${viewport.height}) capturado`);
    }
  });

});