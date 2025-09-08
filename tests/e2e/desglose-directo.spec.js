// tests/e2e/desglose-directo.spec.js
import { test, expect } from '@playwright/test';

test.describe('Desglose - Revisión Visual Directa', () => {

  test('navegar desde búsqueda al desglose', async ({ page }) => {
    // Ir a la página principal
    await page.goto('/');
    
    // Esperar a que cargue
    await page.waitForLoadState('networkidle');
    
    console.log('✓ Navegando a página principal...');
    
    // Capturar screenshot de la página principal para debugging
    await page.screenshot({ 
      path: 'screenshots/pagina-principal.png',
      fullPage: true 
    });
    
    // Buscar el campo de búsqueda
    const campoBusqueda = page.locator('input[type="search"], input[name="query"], #busqueda');
    
    if (await campoBusqueda.count() > 0) {
      // Buscar por "EMPRESA"
      await campoBusqueda.fill('EMPRESA');
      
      // Hacer clic en buscar
      await page.getByRole('button', { name: /buscar/i }).click();
      
      // Esperar resultados
      await page.waitForTimeout(3000);
      
      // Capturar resultados de búsqueda
      await page.screenshot({ 
        path: 'screenshots/resultados-busqueda.png',
        fullPage: true 
      });
      
      // Buscar enlaces "Ver" o "Desglose"
      const enlacesVer = page.locator('a:has-text("Ver"), a:has-text("Desglose"), a[href*="/desglose/"]');
      
      if (await enlacesVer.count() > 0) {
        console.log(`✓ Encontrados ${await enlacesVer.count()} enlaces de desglose`);
        
        // Hacer clic en el primer enlace
        await enlacesVer.first().click();
        
        // Esperar a que cargue el desglose
        await page.waitForLoadState('networkidle');
        
        // Verificar que estamos en el desglose
        const titulo = page.locator('h1, .header h1, .title');
        await expect(titulo).toBeVisible();
        
        console.log('✓ Navegación al desglose exitosa');
        
        // Capturar el desglose actual
        await page.screenshot({ 
          path: 'screenshots/desglose-real.png',
          fullPage: true 
        });
        
        // Analizar el formato actual
        await test.step('analizar formato actual', async () => {
          // Verificar estructura de secciones
          const secciones = page.locator('.section, .card, .panel');
          const cantidadSecciones = await secciones.count();
          
          console.log(`✓ Encontradas ${cantidadSecciones} secciones`);
          
          // Analizar campos de datos
          const campos = page.locator('.field, .form-group, .data-row');
          const cantidadCampos = await campos.count();
          
          console.log(`✓ Encontrados ${cantidadCampos} campos de datos`);
          
          // Capturar secciones individuales
          for (let i = 0; i < Math.min(cantidadSecciones, 3); i++) {
            await secciones.nth(i).screenshot({ 
              path: `screenshots/seccion-${i + 1}-real.png`
            });
          }
        });
        
        // Aplicar mejoras visuales
        await test.step('aplicar mejoras visuales', async () => {
          await page.addStyleTag({
            content: `
              /* MEJORAS VISUALES PROPUESTAS */
              
              .container, .main-content {
                max-width: 900px !important;
                margin: 20px auto !important;
                padding: 30px !important;
                background: white !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
              }
              
              .section, .card, .panel {
                margin-bottom: 25px !important;
                padding: 25px !important;
                background: #ffffff !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 10px !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
              }
              
              .section h3, .card-header, .panel-title {
                font-size: 18px !important;
                font-weight: 600 !important;
                color: #1e293b !important;
                margin-bottom: 20px !important;
                padding-bottom: 12px !important;
                border-bottom: 2px solid #3b82f6 !important;
              }
              
              /* MEJORA PRINCIPAL: Layout Grid para campos */
              .field, .form-group, .data-row {
                display: grid !important;
                grid-template-columns: 180px 1fr !important;
                gap: 15px !important;
                align-items: start !important;
                padding: 12px 0 !important;
                margin: 0 !important;
                border-bottom: 1px solid #f1f5f9 !important;
              }
              
              .field:last-child, .form-group:last-child, .data-row:last-child {
                border-bottom: none !important;
              }
              
              .field strong, .form-group label, .data-row .label {
                color: #475569 !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                text-align: right !important;
                padding-right: 10px !important;
              }
              
              .field span, .form-group .value, .data-row .value {
                background: #f8fafc !important;
                border: 1px solid #cbd5e1 !important;
                border-radius: 6px !important;
                padding: 10px 15px !important;
                color: #1e293b !important;
                font-size: 14px !important;
                line-height: 1.4 !important;
              }
              
              /* Estilos especiales para diferentes tipos */
              .field strong:contains("Total") + span,
              .field strong:contains("Subtotal") + span {
                background: #fef3c7 !important;
                border-color: #f59e0b !important;
                font-weight: 600 !important;
              }
              
              .field strong:contains("Cliente") + span {
                background: #dbeafe !important;
                border-color: #3b82f6 !important;
              }
              
              /* Mejorar tabla de items si existe */
              table {
                width: 100% !important;
                border-collapse: collapse !important;
                margin: 15px 0 !important;
                background: white !important;
                border-radius: 8px !important;
                overflow: hidden !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
              }
              
              table th {
                background: #f1f5f9 !important;
                color: #374151 !important;
                font-weight: 600 !important;
                padding: 12px 15px !important;
                text-align: left !important;
                border-bottom: 2px solid #e5e7eb !important;
              }
              
              table td {
                padding: 12px 15px !important;
                border-bottom: 1px solid #f3f4f6 !important;
                color: #374151 !important;
              }
              
              table tr:hover {
                background: #f9fafb !important;
              }
              
              /* Mejorar botones */
              .btn, .button {
                padding: 12px 24px !important;
                margin: 8px !important;
                border-radius: 8px !important;
                font-weight: 500 !important;
                font-size: 14px !important;
                transition: all 0.3s ease !important;
                cursor: pointer !important;
                border: 1px solid #d1d5db !important;
                text-decoration: none !important;
              }
              
              .btn:hover, .button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
              }
              
              .btn.primary, .btn-primary {
                background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
                color: white !important;
                border-color: #1d4ed8 !important;
              }
              
              /* Responsive */
              @media (max-width: 768px) {
                .field, .form-group, .data-row {
                  grid-template-columns: 1fr !important;
                  gap: 5px !important;
                }
                
                .field strong, .form-group label, .data-row .label {
                  text-align: left !important;
                  padding-right: 0 !important;
                  margin-bottom: 5px !important;
                }
                
                .container, .main-content {
                  margin: 10px !important;
                  padding: 20px !important;
                }
              }
            `
          });
          
          // Capturar el diseño mejorado
          await page.screenshot({ 
            path: 'screenshots/desglose-mejorado-real.png',
            fullPage: true 
          });
          
          console.log('✓ Diseño mejorado aplicado y capturado');
        });
        
      } else {
        console.log('⚠️ No se encontraron enlaces de desglose en los resultados');
      }
    } else {
      console.log('⚠️ No se encontró campo de búsqueda en la página');
      
      // Intentar navegar directamente a la URL del desglose
      await page.goto('/desglose/EMPRESAVIS-CWS-FO-001-R1-REVISIONDE');
      await page.waitForLoadState('networkidle');
      
      await page.screenshot({ 
        path: 'screenshots/desglose-directo.png',
        fullPage: true 
      });
    }
  });
});