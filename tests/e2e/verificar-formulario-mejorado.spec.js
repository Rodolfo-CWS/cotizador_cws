// tests/e2e/verificar-formulario-mejorado.spec.js
import { test, expect } from '@playwright/test';

test.describe('Verificación de Mejoras del Formulario', () => {

  test('comparar formulario antes y después de mejoras', async ({ page }) => {
    // Primero probar localmente (puerto 5001) donde están las mejoras
    console.log('🔍 Probando formulario mejorado localmente...');
    await page.goto('http://localhost:5001/formulario');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Capturar formulario mejorado
    await page.screenshot({ 
      path: 'screenshots/formulario-mejorado-local.png',
      fullPage: true 
    });
    console.log('✓ Formulario mejorado local capturado');
    
    // Verificar que se aplicaron las mejoras CSS
    await test.step('verificar CSS Grid aplicado en formulario', async () => {
      const contenedoresCampos = await page.locator('.form-field-container').all();
      console.log(`📊 Contenedores de campos encontrados: ${contenedoresCampos.length}`);
      
      if (contenedoresCampos.length > 0) {
        // Verificar primer contenedor
        const primerContenedor = contenedoresCampos[0];
        
        const estilos = await primerContenedor.evaluate(el => {
          const computedStyle = window.getComputedStyle(el);
          return {
            display: computedStyle.display,
            gridTemplateColumns: computedStyle.gridTemplateColumns,
            gap: computedStyle.gap,
            alignItems: computedStyle.alignItems
          };
        });
        
        console.log('🎨 Estilos del contenedor de campo:', JSON.stringify(estilos, null, 2));
        
        if (estilos.display === 'grid') {
          console.log('✅ CSS Grid aplicado correctamente en formulario');
        } else {
          console.log(`❌ CSS Grid no aplicado (display: ${estilos.display})`);
        }
        
        if (estilos.gridTemplateColumns.includes('140px')) {
          console.log('✅ Grid columns configurado correctamente (140px 1fr)');
        } else {
          console.log(`❌ Grid columns incorrecto: ${estilos.gridTemplateColumns}`);
        }
        
        // Capturar ejemplo de campo mejorado
        await primerContenedor.screenshot({ 
          path: 'screenshots/campo-formulario-mejorado.png'
        });
      }
      
      // Verificar headers mejorados
      const headersEnhanced = await page.locator('.section-header-enhanced').all();
      console.log(`📋 Headers mejorados encontrados: ${headersEnhanced.length}`);
      
      if (headersEnhanced.length > 0) {
        await headersEnhanced[0].screenshot({ 
          path: 'screenshots/header-formulario-mejorado.png'
        });
        console.log('✓ Header mejorado capturado');
      }
      
      // Verificar alineación de labels
      const labels = await page.locator('.form-field-container label').all();
      if (labels.length > 0) {
        const estiloLabel = await labels[0].evaluate(el => {
          const computedStyle = window.getComputedStyle(el);
          return {
            textAlign: computedStyle.textAlign,
            fontWeight: computedStyle.fontWeight
          };
        });
        
        console.log('🏷️ Estilo de labels:', JSON.stringify(estiloLabel, null, 2));
        
        if (estiloLabel.textAlign === 'right') {
          console.log('✅ Labels alineados a la derecha correctamente');
        } else {
          console.log(`❌ Labels no alineados correctamente: ${estiloLabel.textAlign}`);
        }
      }
    });
    
    // Llenar algunos campos para ver el comportamiento mejorado
    await test.step('probar interacción con campos mejorados', async () => {
      console.log('📝 Llenando campos para probar interacción...');
      
      // Llenar campos de datos generales
      await page.fill('#vendedor', 'FORMATO MEJORADO');
      await page.fill('#proyecto', 'ALINEACION PERFECTA');
      await page.fill('#cliente', 'DISEÑO CWS');
      await page.fill('#atencionA', 'Usuario Test');
      await page.fill('#contacto', 'test@cws.com');
      
      // Configurar términos y condiciones
      await page.selectOption('#moneda', 'MXN');
      await page.fill('#tiempoEntrega', '15 días hábiles');
      await page.fill('#entregaEn', 'Oficinas CWS');
      await page.fill('#terminos', 'NET 30');
      
      // Capturar formulario con datos
      await page.screenshot({ 
        path: 'screenshots/formulario-mejorado-con-datos.png',
        fullPage: true 
      });
      console.log('✓ Formulario mejorado con datos capturado');
    });
  });
  
  test('verificar responsive del formulario mejorado', async ({ page }) => {
    await page.goto('http://localhost:5001/formulario');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    const viewports = [
      { width: 1200, height: 800, name: 'desktop-form-mejorado' },
      { width: 768, height: 1024, name: 'tablet-form-mejorado' },
      { width: 375, height: 667, name: 'mobile-form-mejorado' }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(1500);
      
      await page.screenshot({ 
        path: `screenshots/formulario-responsive-${viewport.name}.png`,
        fullPage: true 
      });
      
      // Verificar que el Grid se adapta en mobile
      if (viewport.width <= 768) {
        const contenedorCampo = page.locator('.form-field-container').first();
        if (await contenedorCampo.isVisible()) {
          const estilos = await contenedorCampo.evaluate(el => {
            const computedStyle = window.getComputedStyle(el);
            return {
              gridTemplateColumns: computedStyle.gridTemplateColumns
            };
          });
          
          console.log(`📱 ${viewport.name}: Grid columns = ${estilos.gridTemplateColumns}`);
          
          if (estilos.gridTemplateColumns === 'none' || estilos.gridTemplateColumns.includes('1fr')) {
            console.log(`✅ ${viewport.name}: Grid adaptado correctamente para mobile`);
          }
        }
      }
      
      console.log(`✓ Screenshot ${viewport.name} capturado`);
    }
  });
  
  test('comparar con producción una vez deployado', async ({ page }) => {
    console.log('🌐 Comparando con producción...');
    
    // Esperar unos segundos para posible deployment
    await page.waitForTimeout(5000);
    
    try {
      await page.goto('https://cotizador-cws.onrender.com/formulario');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
      
      // Capturar formulario en producción
      await page.screenshot({ 
        path: 'screenshots/formulario-produccion-actualizado.png',
        fullPage: true 
      });
      
      // Verificar si las mejoras están aplicadas
      const contenedoresCampos = await page.locator('.form-field-container').all();
      console.log(`📊 Contenedores mejorados en producción: ${contenedoresCampos.length}`);
      
      if (contenedoresCampos.length > 0) {
        console.log('✅ Mejoras aplicadas en producción');
        
        await contenedoresCampos[0].screenshot({ 
          path: 'screenshots/campo-produccion-mejorado.png'
        });
      } else {
        console.log('⏳ Mejoras aún no desplegadas en producción');
      }
      
    } catch (error) {
      console.log('⚠️ Error accediendo a producción:', error.message);
    }
  });

});