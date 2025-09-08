// tests/e2e/revisar-desglose.spec.js
import { test, expect } from '@playwright/test';

test.describe('Revisión Visual del Desglose', () => {

  test('capturar y analizar desglose actual', async ({ page }) => {
    // Ir directamente al desglose que acabamos de crear
    await page.goto('/desglose/EMPRESAVIS-CWS-FO-001-R1-REVISIONDE');
    
    // Esperar a que cargue completamente
    await page.waitForLoadState('networkidle');
    
    console.log('✓ Navegando al desglose específico...');
    
    // Verificar que la página cargó correctamente
    await expect(page.locator('h1, .header')).toBeVisible();
    
    // Capturar screenshot del estado actual
    await page.screenshot({ 
      path: 'screenshots/desglose-actual-completo.png',
      fullPage: true 
    });
    
    console.log('✓ Screenshot completo capturado');
    
    // Analizar secciones específicas
    await test.step('analizar datos generales', async () => {
      const datosGenerales = page.locator('.section').first();
      if (await datosGenerales.isVisible()) {
        await datosGenerales.screenshot({ 
          path: 'screenshots/seccion-datos-generales.png'
        });
        console.log('✓ Sección datos generales capturada');
      }
    });
    
    await test.step('analizar tabla de items', async () => {
      // Buscar la sección de items
      const itemsSection = page.locator('.section').nth(1);
      if (await itemsSection.isVisible()) {
        await itemsSection.screenshot({ 
          path: 'screenshots/seccion-items.png'
        });
        console.log('✓ Sección items capturada');
      }
    });
    
    await test.step('analizar condiciones', async () => {
      // Buscar sección de condiciones o totales
      const condicionesSection = page.locator('.section').last();
      if (await condicionesSection.isVisible()) {
        await condicionesSection.screenshot({ 
          path: 'screenshots/seccion-condiciones.png'
        });
        console.log('✓ Sección condiciones capturada');
      }
    });
    
    // Analizar problemas de alineación específicos
    await test.step('detectar problemas de formato', async () => {
      // Agregar bordes para visualizar mejor la alineación
      await page.addStyleTag({
        content: `
          .field { border: 1px dashed red !important; margin: 2px !important; }
          .field strong { background: rgba(255,0,0,0.1) !important; border: 1px solid red !important; }
          .field span { background: rgba(0,255,0,0.1) !important; border: 1px solid green !important; }
          .section { border: 2px solid blue !important; margin: 5px !important; }
        `
      });
      
      await page.screenshot({ 
        path: 'screenshots/desglose-debug-alineacion.png',
        fullPage: true 
      });
      
      console.log('✓ Screenshot de debug con bordes capturado');
    });
  });

  test('proponer mejoras visuales', async ({ page }) => {
    await page.goto('/desglose/EMPRESAVIS-CWS-FO-001-R1-REVISIONDE');
    await page.waitForLoadState('networkidle');
    
    // Aplicar mejoras CSS propuestas
    await page.addStyleTag({
      content: `
        /* MEJORAS PROPUESTAS PARA EL DESGLOSE */
        
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
          background-color: #f8fafc !important;
          line-height: 1.6 !important;
        }
        
        .container {
          max-width: 1000px !important;
          margin: 0 auto !important;
          padding: 30px !important;
          background: white !important;
          border-radius: 12px !important;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
          border: 1px solid #e2e8f0 !important;
        }
        
        .header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
          color: white !important;
          padding: 25px !important;
          border-radius: 8px !important;
          margin-bottom: 30px !important;
          text-align: center !important;
        }
        
        .header h1 {
          color: white !important;
          font-size: 24px !important;
          font-weight: 600 !important;
          margin: 0 !important;
        }
        
        .section {
          margin-bottom: 25px !important;
          padding: 25px !important;
          background: #ffffff !important;
          border: 1px solid #e2e8f0 !important;
          border-radius: 8px !important;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
        }
        
        .section h3 {
          color: #1e293b !important;
          font-size: 18px !important;
          font-weight: 600 !important;
          margin: 0 0 20px 0 !important;
          padding-bottom: 10px !important;
          border-bottom: 2px solid #3b82f6 !important;
          display: flex !important;
          align-items: center !important;
        }
        
        .section h3::before {
          content: "📋" !important;
          margin-right: 10px !important;
        }
        
        /* MEJORA PRINCIPAL: Grid layout para campos */
        .field {
          display: grid !important;
          grid-template-columns: 200px 1fr !important;
          gap: 15px !important;
          align-items: center !important;
          padding: 12px 0 !important;
          border-bottom: 1px solid #f1f5f9 !important;
          margin: 0 !important;
        }
        
        .field:last-child {
          border-bottom: none !important;
        }
        
        .field strong {
          color: #475569 !important;
          font-weight: 600 !important;
          font-size: 14px !important;
          width: auto !important;
          display: block !important;
          text-align: right !important;
        }
        
        .field span {
          background: #f8fafc !important;
          border: 1px solid #cbd5e1 !important;
          border-radius: 6px !important;
          padding: 10px 15px !important;
          color: #1e293b !important;
          font-size: 14px !important;
          box-shadow: inset 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
        }
        
        /* Estilos especiales para diferentes tipos de campos */
        .field strong:contains("Total") + span,
        .field strong:contains("Subtotal") + span {
          background: #fef3c7 !important;
          border-color: #fbbf24 !important;
          font-weight: 600 !important;
        }
        
        .field strong:contains("Cliente") + span {
          background: #dbeafe !important;
          border-color: #3b82f6 !important;
        }
        
        /* Mejoras para botones */
        .btn {
          padding: 12px 20px !important;
          margin: 8px !important;
          border-radius: 8px !important;
          font-weight: 500 !important;
          font-size: 14px !important;
          transition: all 0.2s ease !important;
          cursor: pointer !important;
          border: 1px solid #d1d5db !important;
        }
        
        .btn:hover {
          transform: translateY(-1px) !important;
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12) !important;
        }
        
        .btn.primary {
          background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
          color: white !important;
          border-color: #1d4ed8 !important;
        }
        
        .actions {
          margin-top: 30px !important;
          padding: 20px !important;
          background: #f8fafc !important;
          border-radius: 8px !important;
          text-align: center !important;
        }
        
        /* Responsive improvements */
        @media (max-width: 768px) {
          .field {
            grid-template-columns: 1fr !important;
            gap: 5px !important;
          }
          
          .field strong {
            text-align: left !important;
            font-size: 13px !important;
            margin-bottom: 5px !important;
          }
          
          .container {
            margin: 10px !important;
            padding: 20px !important;
          }
        }
        
        /* Agregar iconos visuales */
        .field strong:contains("Cliente")::before { content: "👤 "; }
        .field strong:contains("Proyecto")::before { content: "📁 "; }
        .field strong:contains("Fecha")::before { content: "📅 "; }
        .field strong:contains("Total")::before { content: "💰 "; }
        .field strong:contains("Moneda")::before { content: "💱 "; }
        .field strong:contains("Vendedor")::before { content: "👨‍💼 "; }
      `
    });
    
    // Capturar el diseño mejorado
    await page.screenshot({ 
      path: 'screenshots/desglose-mejorado-final.png',
      fullPage: true 
    });
    
    console.log('✓ Propuesta de diseño mejorado capturada');
    
    // Capturar versiones responsive
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
    
    console.log('✓ Versiones responsive capturadas');
  });

  test('comparación lado a lado', async ({ page }) => {
    await page.goto('/desglose/EMPRESAVIS-CWS-FO-001-R1-REVISIONDE');
    await page.waitForLoadState('networkidle');
    
    // Capturar original
    await page.screenshot({ 
      path: 'screenshots/original.png',
      fullPage: true,
      clip: { x: 0, y: 0, width: 600, height: 800 }
    });
    
    // Aplicar mejoras
    await page.addStyleTag({
      content: `
        .field {
          display: grid !important;
          grid-template-columns: 180px 1fr !important;
          gap: 12px !important;
          padding: 10px 0 !important;
          border-bottom: 1px solid #eee !important;
        }
        .field strong { 
          text-align: right !important;
          color: #555 !important; 
        }
        .field span { 
          background: #f9f9f9 !important;
          padding: 8px 12px !important;
          border-radius: 4px !important;
          border: 1px solid #ddd !important;
        }
        .section { 
          box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
          border-radius: 8px !important;
          margin-bottom: 20px !important;
        }
      `
    });
    
    // Capturar mejorado
    await page.screenshot({ 
      path: 'screenshots/mejorado.png',
      fullPage: true,
      clip: { x: 0, y: 0, width: 600, height: 800 }
    });
    
    console.log('✓ Comparación lado a lado lista');
  });
});