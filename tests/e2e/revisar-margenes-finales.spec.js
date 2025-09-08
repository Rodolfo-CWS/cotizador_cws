// tests/e2e/revisar-margenes-finales.spec.js
import { test, expect } from '@playwright/test';

test.describe('Revisión Final de Márgenes y Alineación', () => {

  test('verificar márgenes perfectos después de deployment', async ({ page }) => {
    console.log('📏 Verificando márgenes y alineación final...');
    
    // Esperar un poco más para que el deployment se complete
    await page.waitForTimeout(30000); // 30 segundos adicionales
    
    // PARTE 1: Revisar márgenes del FORMULARIO
    await test.step('analizar márgenes del formulario', async () => {
      const urlFormulario = `https://cotizador-cws.onrender.com/formulario?v=${Date.now()}&nocache=true`;
      console.log(`📝 Analizando márgenes del formulario: ${urlFormulario}`);
      
      await page.goto(urlFormulario);
      await page.waitForLoadState('networkidle');
      await page.reload({ waitUntil: 'networkidle' });
      await page.waitForTimeout(5000);
      
      // Capturar screenshot para análisis
      await page.screenshot({ 
        path: 'screenshots/MARGENES-formulario-final.png',
        fullPage: true 
      });
      
      // Analizar márgenes específicos de los contenedores
      const contenedoresCampos = await page.locator('.form-field-container').all();
      console.log(`📊 Contenedores para analizar: ${contenedoresCampos.length}`);
      
      if (contenedoresCampos.length > 0) {
        // Analizar los primeros 5 contenedores para verificar consistencia
        for (let i = 0; i < Math.min(5, contenedoresCampos.length); i++) {
          const contenedor = contenedoresCampos[i];
          
          const medidas = await contenedor.evaluate(el => {
            const rect = el.getBoundingClientRect();
            const computedStyle = window.getComputedStyle(el);
            const label = el.querySelector('label');
            const input = el.querySelector('input, select, textarea');
            
            let labelMedidas = null;
            let inputMedidas = null;
            
            if (label) {
              const labelRect = label.getBoundingClientRect();
              const labelStyle = window.getComputedStyle(label);
              labelMedidas = {
                width: labelRect.width,
                textAlign: labelStyle.textAlign,
                paddingRight: labelStyle.paddingRight
              };
            }
            
            if (input) {
              const inputRect = input.getBoundingClientRect();
              inputMedidas = {
                width: inputRect.width,
                marginLeft: window.getComputedStyle(input).marginLeft
              };
            }
            
            return {
              contenedor: {
                width: rect.width,
                height: rect.height,
                display: computedStyle.display,
                gridTemplateColumns: computedStyle.gridTemplateColumns,
                gap: computedStyle.gap,
                marginBottom: computedStyle.marginBottom,
                padding: computedStyle.padding
              },
              label: labelMedidas,
              input: inputMedidas
            };
          });
          
          console.log(`🔍 Campo ${i + 1} medidas:`, JSON.stringify(medidas, null, 2));
          
          // Verificar que el grid está aplicado correctamente
          if (medidas.contenedor.display === 'grid') {
            console.log(`✅ Campo ${i + 1}: CSS Grid aplicado`);
            
            if (medidas.contenedor.gridTemplateColumns.includes('140px')) {
              console.log(`✅ Campo ${i + 1}: Columnas correctas (140px 1fr)`);
            } else {
              console.log(`⚠️ Campo ${i + 1}: Columnas incorrectas: ${medidas.contenedor.gridTemplateColumns}`);
            }
            
            if (medidas.label && medidas.label.textAlign === 'right') {
              console.log(`✅ Campo ${i + 1}: Label alineado a la derecha`);
            } else {
              console.log(`⚠️ Campo ${i + 1}: Label no alineado correctamente`);
            }
          } else {
            console.log(`❌ Campo ${i + 1}: CSS Grid NO aplicado (display: ${medidas.contenedor.display})`);
          }
        }
        
        // Capturar ejemplo específico de campo bien alineado
        await contenedoresCampos[0].screenshot({ 
          path: 'screenshots/MARGENES-campo-ejemplo.png'
        });
        console.log('✅ Ejemplo de campo capturado para análisis de márgenes');
      }
      
      // Verificar headers mejorados
      const headers = await page.locator('.section-header-enhanced').all();
      if (headers.length > 0) {
        console.log(`📋 Headers mejorados encontrados: ${headers.length}`);
        await headers[0].screenshot({ 
          path: 'screenshots/MARGENES-header-gradiente.png'
        });
      } else {
        console.log('⚠️ Headers mejorados no encontrados - posible problema de deployment');
      }
    });
    
    // PARTE 2: Revisar márgenes del DESGLOSE
    await test.step('analizar márgenes del desglose', async () => {
      const numeroCotizacion = 'EMPRESAVIS-CWS-FO-001-R1-REVISIONDE';
      const urlDesglose = `https://cotizador-cws.onrender.com/desglose/${numeroCotizacion}?v=${Date.now()}&nocache=true`;
      console.log(`📋 Analizando márgenes del desglose: ${urlDesglose}`);
      
      await page.goto(urlDesglose);
      await page.waitForLoadState('networkidle');
      await page.reload({ waitUntil: 'networkidle' });
      await page.waitForTimeout(5000);
      
      // Capturar screenshot para análisis
      await page.screenshot({ 
        path: 'screenshots/MARGENES-desglose-final.png',
        fullPage: true 
      });
      
      // Analizar campos del desglose
      const camposDesglose = await page.locator('.field').all();
      console.log(`📊 Campos desglose para analizar: ${camposDesglose.length}`);
      
      if (camposDesglose.length > 0) {
        // Analizar los primeros 5 campos del desglose
        for (let i = 0; i < Math.min(5, camposDesglose.length); i++) {
          const campo = camposDesglose[i];
          
          const medidas = await campo.evaluate(el => {
            const rect = el.getBoundingClientRect();
            const computedStyle = window.getComputedStyle(el);
            const strong = el.querySelector('strong');
            const span = el.querySelector('span');
            
            let strongMedidas = null;
            let spanMedidas = null;
            
            if (strong) {
              const strongRect = strong.getBoundingClientRect();
              const strongStyle = window.getComputedStyle(strong);
              strongMedidas = {
                width: strongRect.width,
                textAlign: strongStyle.textAlign
              };
            }
            
            if (span) {
              const spanRect = span.getBoundingClientRect();
              spanMedidas = {
                width: spanRect.width,
                padding: window.getComputedStyle(span).padding
              };
            }
            
            return {
              campo: {
                width: rect.width,
                display: computedStyle.display,
                gridTemplateColumns: computedStyle.gridTemplateColumns,
                gap: computedStyle.gap,
                alignItems: computedStyle.alignItems,
                borderBottom: computedStyle.borderBottom
              },
              strong: strongMedidas,
              span: spanMedidas
            };
          });
          
          console.log(`🔍 Campo desglose ${i + 1}:`, JSON.stringify(medidas, null, 2));
          
          // Verificar alineación del desglose
          if (medidas.campo.display === 'grid') {
            console.log(`✅ Desglose ${i + 1}: CSS Grid aplicado`);
            
            if (medidas.campo.gridTemplateColumns.includes('200px')) {
              console.log(`✅ Desglose ${i + 1}: Columnas correctas (200px 1fr)`);
            } else {
              console.log(`⚠️ Desglose ${i + 1}: Columnas incorrectas: ${medidas.campo.gridTemplateColumns}`);
            }
          } else {
            console.log(`❌ Desglose ${i + 1}: CSS Grid NO aplicado (display: ${medidas.campo.display})`);
          }
        }
        
        // Capturar ejemplo específico de campo de desglose
        await camposDesglose[0].screenshot({ 
          path: 'screenshots/MARGENES-campo-desglose.png'
        });
        console.log('✅ Ejemplo de campo desglose capturado');
      }
    });
    
    // PARTE 3: Análisis comparativo de alineación
    await test.step('análisis comparativo de alineación', async () => {
      console.log('📐 Realizando análisis comparativo de alineación...');
      
      // Volver al formulario para análisis de consistency
      await page.goto(`https://cotizador-cws.onrender.com/formulario?v=${Date.now()}`);
      await page.waitForLoadState('networkidle');
      
      // Llenar algunos campos para ver alineación en uso
      await page.fill('#vendedor', 'TEST MARGENES');
      await page.fill('#cliente', 'VERIFICACION ALINEACION');
      await page.fill('#proyecto', 'ANALISIS FINAL');
      
      // Capturar con datos para ver alineación real
      await page.screenshot({ 
        path: 'screenshots/MARGENES-formulario-con-datos.png',
        fullPage: true 
      });
      
      console.log('✅ Formulario con datos capturado para análisis final');
      
      // Resumen de análisis
      const summary = {
        formulario_esperado: 'CSS Grid 140px 1fr con labels alineados derecha',
        desglose_esperado: 'CSS Grid 200px 1fr con etiquetas alineadas derecha',
        responsive: 'Colapso a single column en mobile',
        iconos: 'Iconos contextuales para mejor UX'
      };
      
      console.log('📊 RESUMEN DE ANÁLISIS:', JSON.stringify(summary, null, 2));
    });
  });

});