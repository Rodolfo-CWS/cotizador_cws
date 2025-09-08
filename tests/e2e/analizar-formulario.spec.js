// tests/e2e/analizar-formulario.spec.js
import { test, expect } from '@playwright/test';

test.describe('Análisis de Formato - Formulario de Cotización', () => {

  test('capturar formato actual del formulario en producción', async ({ page }) => {
    const urlFormulario = 'https://cotizador-cws.onrender.com/formulario';
    
    console.log(`📝 Analizando formulario en: ${urlFormulario}`);
    
    // Ir al formulario
    await page.goto(urlFormulario);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Capturar screenshot completo del formulario
    await page.screenshot({ 
      path: 'screenshots/formulario-actual.png',
      fullPage: true 
    });
    console.log('✓ Screenshot del formulario actual capturado');
    
    // Analizar estructura del formulario
    await test.step('analizar campos del formulario', async () => {
      
      // Buscar diferentes tipos de campos
      const inputFields = await page.locator('input').all();
      const selectFields = await page.locator('select').all();
      const textareaFields = await page.locator('textarea').all();
      const labels = await page.locator('label').all();
      
      console.log(`📊 Campos encontrados:`);
      console.log(`  - Inputs: ${inputFields.length}`);
      console.log(`  - Selects: ${selectFields.length}`);
      console.log(`  - Textareas: ${textareaFields.length}`);
      console.log(`  - Labels: ${labels.length}`);
      
      // Capturar sección de datos generales
      const datosGenerales = page.locator('.form-section, .datos-generales, [class*="form"], [class*="datos"]').first();
      if (await datosGenerales.isVisible()) {
        await datosGenerales.screenshot({ 
          path: 'screenshots/formulario-datos-generales.png'
        });
        console.log('✓ Sección de datos generales capturada');
      } else {
        // Capturar primeros campos si no hay sección específica
        const formContainer = page.locator('form, .container, .form-container').first();
        if (await formContainer.isVisible()) {
          await formContainer.screenshot({ 
            path: 'screenshots/formulario-contenedor.png'
          });
        }
      }
      
      // Analizar estilos de campos específicos
      if (inputFields.length > 0) {
        const primerInput = inputFields[0];
        const estilosInput = await primerInput.evaluate(el => {
          const computedStyle = window.getComputedStyle(el);
          const parent = el.parentElement;
          const parentStyles = parent ? window.getComputedStyle(parent) : null;
          
          return {
            campo: {
              width: computedStyle.width,
              padding: computedStyle.padding,
              margin: computedStyle.margin,
              border: computedStyle.border
            },
            contenedor: parentStyles ? {
              display: parentStyles.display,
              flexDirection: parentStyles.flexDirection,
              alignItems: parentStyles.alignItems,
              gap: parentStyles.gap,
              gridTemplateColumns: parentStyles.gridTemplateColumns
            } : null
          };
        });
        
        console.log('🔍 Estilos de campo input:', JSON.stringify(estilosInput, null, 2));
      }
      
      // Analizar labels y su alineación
      if (labels.length > 0) {
        const primerLabel = labels[0];
        const estilosLabel = await primerLabel.evaluate(el => {
          const computedStyle = window.getComputedStyle(el);
          return {
            width: computedStyle.width,
            textAlign: computedStyle.textAlign,
            display: computedStyle.display,
            marginBottom: computedStyle.marginBottom
          };
        });
        
        console.log('🏷️ Estilos de label:', JSON.stringify(estilosLabel, null, 2));
      }
    });
    
    // Analizar sección de items si existe
    await test.step('analizar sección de items', async () => {
      const seccionItems = page.locator('.items-section, .items-container, [class*="items"]');
      
      if (await seccionItems.isVisible()) {
        await seccionItems.screenshot({ 
          path: 'screenshots/formulario-items.png'
        });
        console.log('✓ Sección de items capturada');
        
        // Analizar botones de agregar/eliminar
        const botonesItems = await page.locator('button:has-text("Agregar"), button:has-text("Eliminar"), input[type="button"]').all();
        console.log(`🔘 Botones de items encontrados: ${botonesItems.length}`);
      }
    });
    
    // Analizar botones principales
    await test.step('analizar botones principales', async () => {
      const botones = await page.locator('button, input[type="submit"], input[type="button"]').all();
      console.log(`🔘 Total de botones: ${botones.length}`);
      
      if (botones.length > 0) {
        // Capturar área de botones
        const ultimoBoton = botones[botones.length - 1];
        const contenedorBotones = page.locator('form').last();
        
        if (await contenedorBotones.isVisible()) {
          const boundingBox = await contenedorBotones.boundingBox();
          if (boundingBox) {
            await page.screenshot({
              path: 'screenshots/formulario-botones.png',
              clip: { 
                x: 0, 
                y: Math.max(0, boundingBox.y + boundingBox.height - 200), 
                width: boundingBox.width, 
                height: 200 
              }
            });
          }
        }
      }
    });
  });
  
  test('análisis responsive del formulario', async ({ page }) => {
    await page.goto('https://cotizador-cws.onrender.com/formulario');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    const viewports = [
      { width: 1200, height: 800, name: 'desktop-formulario' },
      { width: 900, height: 700, name: 'desktop-medium-formulario' },
      { width: 768, height: 1024, name: 'tablet-formulario' },
      { width: 375, height: 667, name: 'mobile-formulario' }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(1500);
      
      await page.screenshot({ 
        path: `screenshots/formulario-responsive-${viewport.name}.png`,
        fullPage: true 
      });
      console.log(`✓ Screenshot formulario ${viewport.name} capturado`);
    }
  });
  
  test('interacción con formulario para análisis completo', async ({ page }) => {
    await page.goto('https://cotizador-cws.onrender.com/formulario');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Llenar algunos campos para ver el comportamiento
    console.log('📝 Llenando campos para análisis...');
    
    try {
      // Buscar y llenar campos comunes
      const clienteInput = page.locator('input[name*="cliente"], #cliente').first();
      if (await clienteInput.isVisible()) {
        await clienteInput.fill('ANÁLISIS VISUAL');
        console.log('✓ Campo cliente llenado');
      }
      
      const vendedorInput = page.locator('input[name*="vendedor"], #vendedor, select[name*="vendedor"]').first();
      if (await vendedorInput.isVisible()) {
        if (await vendedorInput.getAttribute('type') !== null) {
          await vendedorInput.fill('FORMATO');
        } else {
          await vendedorInput.selectOption({ index: 1 }); // Seleccionar primera opción
        }
        console.log('✓ Campo vendedor configurado');
      }
      
      const proyectoInput = page.locator('input[name*="proyecto"], #proyecto').first();
      if (await proyectoInput.isVisible()) {
        await proyectoInput.fill('MEJORA FORMULARIO');
        console.log('✓ Campo proyecto llenado');
      }
      
      // Capturar formulario con datos
      await page.screenshot({ 
        path: 'screenshots/formulario-con-datos.png',
        fullPage: true 
      });
      console.log('✓ Formulario con datos capturado');
      
      // Intentar agregar un item si existe el botón
      const botonAgregar = page.locator('button:has-text("Agregar"), input[value*="Agregar"]').first();
      if (await botonAgregar.isVisible()) {
        await botonAgregar.click();
        await page.waitForTimeout(1000);
        
        await page.screenshot({ 
          path: 'screenshots/formulario-con-item.png',
          fullPage: true 
        });
        console.log('✓ Formulario con item agregado capturado');
      }
      
    } catch (error) {
      console.log('⚠️ Algunos campos no pudieron llenarse:', error.message);
    }
  });

});