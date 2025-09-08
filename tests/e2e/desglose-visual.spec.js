// tests/e2e/desglose-visual.spec.js
import { test, expect } from '@playwright/test';

test.describe('Desglose Visual - Formato y Alineación', () => {

  test('capturar screenshot del desglose actual para revisar formato', async ({ page }) => {
    // Ir a la página principal para buscar una cotización existente
    await page.goto('/');
    
    // Realizar búsqueda vacía para mostrar todas las cotizaciones
    await page.getByRole('button', { name: /buscar/i }).click();
    
    // Esperar a que aparezcan los resultados
    await page.waitForTimeout(2000);
    
    // Buscar el primer enlace "Ver" o "Desglose"
    const verLinks = page.locator('a:has-text("Ver"), button:has-text("Desglose"), a[href*="/desglose/"]');
    
    if (await verLinks.count() > 0) {
      // Hacer clic en el primer desglose disponible
      await verLinks.first().click();
      
      // Esperar a que cargue la página de desglose
      await page.waitForLoadState('networkidle');
      
      // Verificar que estamos en la página de desglose
      await expect(page.locator('h1')).toContainText(['Cotización', 'Desglose']);
      
      // Capturar screenshot completo de la página
      await page.screenshot({ 
        path: 'screenshots/desglose-actual.png',
        fullPage: true 
      });
      
      // Analizar elementos específicos del formato
      await test.step('analizar layout general', async () => {
        // Verificar que existe el contenedor principal
        const container = page.locator('.container, .main-content, [data-testid="desglose-container"]');
        await expect(container.first()).toBeVisible();
        
        console.log('✓ Contenedor principal encontrado');
      });
      
      await test.step('analizar secciones principales', async () => {
        // Verificar secciones principales
        const secciones = page.locator('.section, .datos-generales, .items-section');
        const conteoSecciones = await secciones.count();
        
        console.log(`✓ Encontradas ${conteoSecciones} secciones principales`);
        
        // Capturar screenshots individuales de cada sección
        for (let i = 0; i < Math.min(conteoSecciones, 5); i++) {
          await secciones.nth(i).screenshot({ 
            path: `screenshots/seccion-${i + 1}.png` 
          });
        }
      });
      
      await test.step('analizar campos de datos', async () => {
        // Verificar campos individuales
        const campos = page.locator('.field, .form-group, .data-field');
        const conteoCampos = await campos.count();
        
        console.log(`✓ Encontrados ${conteoCampos} campos de datos`);
        
        // Verificar alineación de etiquetas
        const etiquetas = page.locator('.field strong, .label, .field-label');
        if (await etiquetas.count() > 0) {
          const primeraEtiqueta = etiquetas.first();
          const boundingBox = await primeraEtiqueta.boundingBox();
          
          console.log(`✓ Primera etiqueta en posición: x=${boundingBox?.x}, width=${boundingBox?.width}`);
        }
      });
      
      await test.step('analizar tabla de items', async () => {
        // Buscar tabla o lista de items
        const tablaItems = page.locator('table, .items-table, .items-list, .item');
        
        if (await tablaItems.count() > 0) {
          await tablaItems.first().screenshot({ 
            path: 'screenshots/tabla-items.png' 
          });
          
          console.log('✓ Tabla de items encontrada y capturada');
        } else {
          console.log('⚠️ No se encontró tabla de items');
        }
      });
      
      await test.step('analizar botones de acción', async () => {
        // Verificar botones de acción
        const botones = page.locator('.btn, .button, .action-button');
        const conteoBotones = await botones.count();
        
        console.log(`✓ Encontrados ${conteoBotones} botones de acción`);
        
        if (conteoBotones > 0) {
          // Capturar screenshot de la sección de botones
          const seccionBotones = page.locator('.actions, .button-section, .footer-actions');
          if (await seccionBotones.count() > 0) {
            await seccionBotones.first().screenshot({ 
              path: 'screenshots/botones-accion.png' 
            });
          }
        }
      });
      
    } else {
      console.log('⚠️ No se encontraron cotizaciones para revisar desglose');
      
      // Si no hay cotizaciones, crear una para poder probar
      await test.step('crear cotización de prueba para desglose', async () => {
        await page.goto('/formulario');
        
        // Llenar formulario básico
        await page.fill('#cliente', 'TEST VISUAL');
        await page.fill('#vendedor', 'FORMATO');
        await page.fill('#proyecto', 'DESGLOSE TEST');
        
        // Agregar un ítem
        await page.getByRole('button', { name: /agregar ítem/i }).click();
        await page.fill('[name="items[0][descripcion]"]', 'Item para test visual');
        await page.fill('[name="items[0][cantidad]"]', '1');
        await page.fill('[name="items[0][precio_unitario]"]', '1000.00');
        
        // Enviar formulario
        await page.getByRole('button', { name: /generar cotización/i }).click();
        
        // Esperar procesamiento
        await page.waitForTimeout(3000);
        
        console.log('✓ Cotización de prueba creada');
      });
    }
  });
  
  test('revisar responsive del desglose en diferentes tamaños', async ({ page }) => {
    // Primero buscar una cotización
    await page.goto('/');
    await page.getByRole('button', { name: /buscar/i }).click();
    await page.waitForTimeout(2000);
    
    const verLinks = page.locator('a:has-text("Ver"), a[href*="/desglose/"]');
    
    if (await verLinks.count() > 0) {
      await verLinks.first().click();
      await page.waitForLoadState('networkidle');
      
      // Desktop
      await page.setViewportSize({ width: 1200, height: 800 });
      await page.screenshot({ 
        path: 'screenshots/desglose-desktop.png',
        fullPage: true 
      });
      
      // Tablet
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.screenshot({ 
        path: 'screenshots/desglose-tablet.png',
        fullPage: true 
      });
      
      // Mobile
      await page.setViewportSize({ width: 375, height: 667 });
      await page.screenshot({ 
        path: 'screenshots/desglose-mobile.png',
        fullPage: true 
      });
      
      console.log('✓ Screenshots responsive capturados');
    }
  });
  
  test('analizar problemas específicos de alineación', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /buscar/i }).click();
    await page.waitForTimeout(2000);
    
    const verLinks = page.locator('a:has-text("Ver"), a[href*="/desglose/"]');
    
    if (await verLinks.count() > 0) {
      await verLinks.first().click();
      await page.waitForLoadState('networkidle');
      
      // Analizar problemas comunes de alineación
      const problemas = [];
      
      // 1. Verificar ancho inconsistente de etiquetas
      const etiquetas = page.locator('.field strong, .label');
      if (await etiquetas.count() > 1) {
        const anchos = [];
        for (let i = 0; i < Math.min(5, await etiquetas.count()); i++) {
          const bbox = await etiquetas.nth(i).boundingBox();
          if (bbox) anchos.push(bbox.width);
        }
        
        const maxWidth = Math.max(...anchos);
        const minWidth = Math.min(...anchos);
        
        if (maxWidth - minWidth > 20) {
          problemas.push(`Etiquetas con anchos inconsistentes: ${minWidth}-${maxWidth}px`);
        }
      }
      
      // 2. Verificar alineación vertical
      const campos = page.locator('.field');
      if (await campos.count() > 1) {
        const posicionesX = [];
        for (let i = 0; i < Math.min(3, await campos.count()); i++) {
          const bbox = await campos.nth(i).boundingBox();
          if (bbox) posicionesX.push(bbox.x);
        }
        
        const variacionX = Math.max(...posicionesX) - Math.min(...posicionesX);
        if (variacionX > 5) {
          problemas.push(`Campos desalineados horizontalmente: variación ${variacionX}px`);
        }
      }
      
      // 3. Verificar espaciado consistente
      const secciones = page.locator('.section');
      if (await secciones.count() > 1) {
        const espacios = [];
        for (let i = 0; i < await secciones.count() - 1; i++) {
          const bbox1 = await secciones.nth(i).boundingBox();
          const bbox2 = await secciones.nth(i + 1).boundingBox();
          if (bbox1 && bbox2) {
            espacios.push(bbox2.y - (bbox1.y + bbox1.height));
          }
        }
        
        if (espacios.length > 0) {
          const maxEspacio = Math.max(...espacios);
          const minEspacio = Math.min(...espacios);
          
          if (maxEspacio - minEspacio > 10) {
            problemas.push(`Espaciado inconsistente entre secciones: ${minEspacio}-${maxEspacio}px`);
          }
        }
      }
      
      // Reportar problemas encontrados
      console.log('=== ANÁLISIS DE PROBLEMAS DE FORMATO ===');
      if (problemas.length > 0) {
        problemas.forEach((problema, i) => {
          console.log(`${i + 1}. ${problema}`);
        });
      } else {
        console.log('✓ No se detectaron problemas obvios de alineación');
      }
      
      // Capturar screenshot con overlay para mostrar problemas
      await page.addStyleTag({
        content: `
          .field strong { outline: 1px solid red !important; }
          .section { outline: 2px solid blue !important; }
          .field { outline: 1px solid green !important; }
        `
      });
      
      await page.screenshot({ 
        path: 'screenshots/desglose-debug.png',
        fullPage: true 
      });
      
      console.log('✓ Screenshot de debug generado con outlines');
    }
  });
});

test.describe('Propuestas de Mejora Visual', () => {
  
  test('generar mockup de formato mejorado', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /buscar/i }).click();
    await page.waitForTimeout(2000);
    
    const verLinks = page.locator('a:has-text("Ver"), a[href*="/desglose/"]');
    
    if (await verLinks.count() > 0) {
      await verLinks.first().click();
      await page.waitForLoadState('networkidle');
      
      // Aplicar mejoras CSS temporales para mostrar formato mejorado
      await page.addStyleTag({
        content: `
          /* Mejoras de formato propuestas */
          .container { 
            max-width: 900px !important; 
            margin: 20px auto !important;
            padding: 40px !important;
          }
          
          .field { 
            display: grid !important;
            grid-template-columns: 200px 1fr !important;
            gap: 15px !important;
            align-items: center !important;
            margin-bottom: 15px !important;
            padding: 10px 0 !important;
            border-bottom: 1px solid #f0f0f0 !important;
          }
          
          .field strong { 
            width: auto !important;
            color: #2c3e50 !important;
            font-weight: 600 !important;
            font-size: 14px !important;
          }
          
          .field span {
            background: white !important;
            padding: 12px 16px !important;
            border: 1px solid #ddd !important;
            border-radius: 6px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
          }
          
          .section {
            margin-bottom: 30px !important;
            padding: 25px !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
          }
          
          .section h3 {
            font-size: 18px !important;
            color: #2c3e50 !important;
            margin-bottom: 20px !important;
            padding-bottom: 10px !important;
            border-bottom: 2px solid #3498db !important;
          }
          
          /* Mejorar tabla de items si existe */
          table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin-top: 15px !important;
          }
          
          table th, table td {
            padding: 12px 15px !important;
            text-align: left !important;
            border-bottom: 1px solid #ddd !important;
          }
          
          table th {
            background-color: #f8f9fa !important;
            font-weight: 600 !important;
            color: #2c3e50 !important;
          }
          
          /* Mejorar botones */
          .btn {
            padding: 12px 24px !important;
            margin: 10px !important;
            font-weight: 500 !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
          }
          
          .btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
          }
          
          /* Responsive mejorado */
          @media (max-width: 768px) {
            .field {
              grid-template-columns: 1fr !important;
              gap: 8px !important;
            }
            
            .field strong {
              font-size: 13px !important;
              margin-bottom: 5px !important;
            }
          }
        `
      });
      
      // Capturar el formato mejorado
      await page.screenshot({ 
        path: 'screenshots/desglose-mejorado.png',
        fullPage: true 
      });
      
      console.log('✓ Mockup de formato mejorado generado');
      
      // También capturar versiones responsive del formato mejorado
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.screenshot({ 
        path: 'screenshots/desglose-mejorado-tablet.png',
        fullPage: true 
      });
      
      await page.setViewportSize({ width: 375, height: 667 });
      await page.screenshot({ 
        path: 'screenshots/desglose-mejorado-mobile.png',
        fullPage: true 
      });
    }
  });
});