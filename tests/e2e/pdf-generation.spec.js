// tests/e2e/pdf-generation.spec.js
import { test, expect } from '@playwright/test';

test.describe('Generación de PDFs', () => {
  
  test('debe generar PDF después de crear cotización', async ({ page }) => {
    await page.goto('/formulario');
    
    // Llenar formulario completo
    await page.fill('#cliente', 'TEST PDF CLIENT');
    await page.fill('#vendedor', 'PDF VENDOR');
    await page.fill('#proyecto', 'PROYECTO PDF TEST');
    await page.selectOption('#moneda', 'MXN');
    
    // Agregar ítem
    await page.getByRole('button', { name: /agregar ítem/i }).click();
    await page.fill('[name="items[0][descripcion]"]', 'Item para PDF');
    await page.fill('[name="items[0][cantidad]"]', '1');
    await page.fill('[name="items[0][precio_unitario]"]', '1000.00');
    
    // Enviar formulario
    await page.getByRole('button', { name: /generar cotización/i }).click();
    
    // Esperar procesamiento (puede tomar unos segundos)
    await page.waitForTimeout(3000);
    
    // Verificar que no hay errores visibles
    await expect(page.locator('body')).not.toContainText('error');
    await expect(page.locator('body')).not.toContainText('Error');
  });

  test('debe permitir visualizar PDF generado', async ({ page }) => {
    // Primero ir a la página principal para buscar PDFs
    await page.goto('/');
    
    // Realizar búsqueda para encontrar PDFs
    await page.getByRole('button', { name: /buscar/i }).click();
    
    // Esperar resultados
    await page.waitForTimeout(2000);
    
    // Buscar enlaces de PDF
    const pdfLinks = page.locator('a[href*="/pdf/"], button:has-text("Ver PDF"), [data-action="view-pdf"]');
    
    if (await pdfLinks.count() > 0) {
      // Hacer clic en el primer enlace de PDF
      await pdfLinks.first().click();
      
      // Verificar que se abre/descarga el PDF
      // (El comportamiento puede variar según la implementación)
      await page.waitForTimeout(2000);
      
      // Verificar que no hay errores de PDF
      await expect(page.locator('body')).not.toContainText('Error del PDF');
      await expect(page.locator('body')).not.toContainText('PDF no disponible');
    } else {
      console.log('No se encontraron PDFs para probar visualización');
    }
  });

  test('debe manejar errores de PDF gracefully', async ({ page }) => {
    // Intentar acceder a un PDF que no existe
    await page.goto('/pdf/NONEXISTENT-PDF-ID');
    
    // Verificar manejo de errores
    const bodyText = await page.textContent('body');
    const hasErrorHandling = 
      bodyText.includes('no encontrado') || 
      bodyText.includes('no existe') || 
      bodyText.includes('404') ||
      bodyText.includes('Error');
    
    expect(hasErrorHandling).toBeTruthy();
  });
});

test.describe('Flujo Completo de Cotización', () => {
  
  test('debe completar flujo end-to-end: crear → buscar → visualizar', async ({ page }) => {
    const clienteTest = `E2E-CLIENT-${Date.now()}`;
    
    // 1. Crear cotización
    await page.goto('/formulario');
    await page.fill('#cliente', clienteTest);
    await page.fill('#vendedor', 'E2E VENDOR');
    await page.fill('#proyecto', 'PROYECTO E2E COMPLETO');
    await page.selectOption('#moneda', 'USD');
    
    // Agregar ítem
    await page.getByRole('button', { name: /agregar ítem/i }).click();
    await page.fill('[name="items[0][descripcion]"]', 'Servicio E2E Test');
    await page.fill('[name="items[0][cantidad]"]', '2');
    await page.fill('[name="items[0][precio_unitario]"]', '500.00');
    
    // Generar cotización
    await page.getByRole('button', { name: /generar cotización/i }).click();
    await page.waitForTimeout(3000);
    
    // 2. Buscar cotización creada
    await page.goto('/');
    await page.fill('input[type="search"], input[name="query"], #busqueda', clienteTest);
    await page.getByRole('button', { name: /buscar/i }).click();
    await page.waitForTimeout(2000);
    
    // Verificar que aparece en resultados
    await expect(page.locator('body')).toContainText(clienteTest);
    
    // 3. Ver desglose/detalles
    const detalleLinks = page.locator('a:has-text("Ver"), button:has-text("Desglose"), a[href*="/desglose/"]');
    if (await detalleLinks.count() > 0) {
      await detalleLinks.first().click();
      await page.waitForTimeout(1000);
      
      // Verificar que se muestran los datos correctos
      await expect(page.locator('body')).toContainText(clienteTest);
      await expect(page.locator('body')).toContainText('E2E VENDOR');
    }
  });
});

test.describe('Performance y Carga', () => {
  
  test('debe cargar formulario en menos de 3 segundos', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/formulario');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;
    
    console.log(`Tiempo de carga del formulario: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(3000);
  });
  
  test('debe manejar múltiples ítems sin problemas de performance', async ({ page }) => {
    await page.goto('/formulario');
    
    // Llenar datos básicos
    await page.fill('#cliente', 'PERFORMANCE TEST');
    await page.fill('#vendedor', 'PERF');
    await page.fill('#proyecto', 'MULTIPLE ITEMS');
    
    // Agregar muchos ítems
    for (let i = 0; i < 10; i++) {
      await page.getByRole('button', { name: /agregar ítem/i }).click();
      await page.fill(`[name="items[${i}][descripcion]"]`, `Item ${i + 1}`);
      await page.fill(`[name="items[${i}][cantidad]"]`, '1');
      await page.fill(`[name="items[${i}][precio_unitario]"]`, '100.00');
    }
    
    // Verificar que todos los campos están presentes y los cálculos son correctos
    await expect(page.locator('#subtotal')).toHaveValue('1000.00');
    await expect(page.locator('#total')).toHaveValue('1160.00'); // Con 16% IVA
  });
});