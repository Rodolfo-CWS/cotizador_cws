// tests/e2e/verificar-mejoras-final.spec.js
import { test, expect } from '@playwright/test';

test.describe('Verificación Final de Mejoras CSS Grid', () => {

  test('verificar aplicación del CSS Grid en producción', async ({ page }) => {
    // Dar tiempo para que el deployment se complete
    console.log('⏳ Esperando 3 minutos para que complete el deployment...');
    await page.waitForTimeout(180000); // 3 minutos
    
    const numeroCotizacion = 'EMPRESAVIS-CWS-FO-001-R1-REVISIONDE';
    const urlDesglose = `https://cotizador-cws.onrender.com/desglose/${numeroCotizacion}`;
    
    console.log(`🔍 Verificando mejoras en: ${urlDesglose}`);
    
    // Ir al desglose con parámetros para evitar caché
    await page.goto(`${urlDesglose}?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000); // Tiempo extra para asegurar carga completa
    
    // Capturar screenshot "después de las mejoras"
    await page.screenshot({ 
      path: 'screenshots/desglose-mejorado-final.png',
      fullPage: true 
    });
    console.log('✅ Screenshot del desglose mejorado capturado');
    
    // Verificar que se aplicó el CSS Grid
    await test.step('verificar CSS Grid aplicado', async () => {
      const campos = await page.locator('.field').all();
      console.log(`📊 Encontrados ${campos.length} campos para verificar`);
      
      if (campos.length > 0) {
        // Verificar primeros 3 campos
        for (let i = 0; i < Math.min(3, campos.length); i++) {
          const campo = campos[i];
          
          const estilos = await campo.evaluate(el => {
            const computedStyle = window.getComputedStyle(el);
            return {
              display: computedStyle.display,
              gridTemplateColumns: computedStyle.gridTemplateColumns,
              gap: computedStyle.gap,
              alignItems: computedStyle.alignItems
            };
          });
          
          console.log(`✅ Campo ${i + 1} estilos mejorados:`, JSON.stringify(estilos, null, 2));
          
          // Verificaciones específicas
          if (estilos.display === 'grid') {
            console.log(`✅ Campo ${i + 1}: CSS Grid aplicado correctamente`);
          } else {
            console.log(`❌ Campo ${i + 1}: CSS Grid NO aplicado (display: ${estilos.display})`);
          }
          
          if (estilos.gridTemplateColumns.includes('200px')) {
            console.log(`✅ Campo ${i + 1}: Grid columns configurado correctamente`);
          } else {
            console.log(`❌ Campo ${i + 1}: Grid columns incorrecto (${estilos.gridTemplateColumns})`);
          }
        }
        
        // Capturar ejemplo de campo mejorado
        await campos[0].screenshot({ 
          path: 'screenshots/campo-grid-mejorado.png'
        });
        console.log('✅ Ejemplo de campo con Grid capturado');
        
        // Verificar alineación de etiquetas
        const primeraEtiqueta = campos[0].locator('strong').first();
        const estiloEtiqueta = await primeraEtiqueta.evaluate(el => {
          const computedStyle = window.getComputedStyle(el);
          return {
            textAlign: computedStyle.textAlign,
            width: computedStyle.width
          };
        });
        
        console.log('🏷️ Estilo de etiqueta:', JSON.stringify(estiloEtiqueta, null, 2));
        
        if (estiloEtiqueta.textAlign === 'right') {
          console.log('✅ Etiquetas alineadas a la derecha correctamente');
        } else {
          console.log(`❌ Etiquetas NO alineadas correctamente (${estiloEtiqueta.textAlign})`);
        }
      }
    });
    
    // Comparación visual - capturar sección específica
    await test.step('capturar comparación visual', async () => {
      const primeraSeccion = page.locator('.section').first();
      if (await primeraSeccion.isVisible()) {
        await primeraSeccion.screenshot({ 
          path: 'screenshots/seccion-grid-mejorada.png'
        });
        console.log('✅ Sección con Grid layout capturada');
      }
      
      // Capturar múltiples campos para comparación
      const informacionGeneral = page.locator('.section').first();
      if (await informacionGeneral.isVisible()) {
        await informacionGeneral.screenshot({
          path: 'screenshots/informacion-general-grid.png'
        });
        console.log('✅ Información General con Grid capturada');
      }
    });
  });
  
  test('verificar responsive con CSS Grid', async ({ page }) => {
    const numeroCotizacion = 'EMPRESAVIS-CWS-FO-001-R1-REVISIONDE';
    const urlDesglose = `https://cotizador-cws.onrender.com/desglose/${numeroCotizacion}?v=${Date.now()}`;
    
    await page.goto(urlDesglose);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Verificar responsive design mejorado
    const viewports = [
      { width: 1200, height: 800, name: 'desktop-mejorado' },
      { width: 768, height: 1024, name: 'tablet-mejorado' },
      { width: 375, height: 667, name: 'mobile-mejorado' }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(2000);
      
      await page.screenshot({ 
        path: `screenshots/responsive-${viewport.name}.png`,
        fullPage: true 
      });
      
      // Verificar que el Grid se mantiene en diferentes tamaños
      const campo = page.locator('.field').first();
      if (await campo.isVisible()) {
        const estilos = await campo.evaluate(el => {
          const computedStyle = window.getComputedStyle(el);
          return {
            display: computedStyle.display,
            gridTemplateColumns: computedStyle.gridTemplateColumns
          };
        });
        
        console.log(`📱 ${viewport.name}: Display=${estilos.display}, Grid=${estilos.gridTemplateColumns}`);
      }
    }
  });

});