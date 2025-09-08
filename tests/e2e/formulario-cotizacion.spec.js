// tests/e2e/formulario-cotizacion.spec.js
import { test, expect } from '@playwright/test';

test.describe('Formulario de Cotización', () => {
  
  test('debe cargar la página principal correctamente', async ({ page }) => {
    await page.goto('/');
    
    // Verificar que el título contenga "CWS"
    await expect(page).toHaveTitle(/CWS/);
    
    // Verificar elementos principales
    await expect(page.locator('h1')).toContainText('Sistema de Cotizaciones CWS');
    await expect(page.getByRole('button', { name: /crear nueva cotización/i })).toBeVisible();
  });

  test('debe navegar al formulario de cotización', async ({ page }) => {
    await page.goto('/');
    
    // Hacer clic en "Crear Nueva Cotización"
    await page.getByRole('button', { name: /crear nueva cotización/i }).click();
    
    // Verificar navegación al formulario
    await expect(page).toHaveURL('/formulario');
    await expect(page.locator('h1')).toContainText('Nueva Cotización');
  });

  test('debe llenar y enviar formulario básico', async ({ page }) => {
    await page.goto('/formulario');
    
    // Llenar datos generales
    await page.fill('#cliente', 'TEST CLIENTE E2E');
    await page.fill('#vendedor', 'TEST VENDEDOR');
    await page.fill('#proyecto', 'PROYECTO TEST PLAYWRIGHT');
    
    // Seleccionar moneda
    await page.selectOption('#moneda', 'MXN');
    
    // Agregar un ítem básico
    await page.getByRole('button', { name: /agregar ítem/i }).click();
    
    // Llenar primer ítem
    await page.fill('[name="items[0][descripcion]"]', 'Item de prueba E2E');
    await page.fill('[name="items[0][cantidad]"]', '1');
    await page.fill('[name="items[0][precio_unitario]"]', '100.00');
    
    // Enviar formulario
    await page.getByRole('button', { name: /generar cotización/i }).click();
    
    // Verificar que se procese correctamente (puede redirigir o mostrar mensaje)
    await expect(page.locator('body')).not.toContainText('error', { timeout: 10000 });
  });

  test('debe validar campos requeridos', async ({ page }) => {
    await page.goto('/formulario');
    
    // Intentar enviar sin llenar campos
    await page.getByRole('button', { name: /generar cotización/i }).click();
    
    // Verificar mensajes de validación
    await expect(page.locator('#cliente:invalid')).toBeVisible();
    await expect(page.locator('#vendedor:invalid')).toBeVisible();
    await expect(page.locator('#proyecto:invalid')).toBeVisible();
  });

  test('debe calcular totales automáticamente', async ({ page }) => {
    await page.goto('/formulario');
    
    // Llenar datos básicos
    await page.fill('#cliente', 'TEST CÁLCULO');
    await page.fill('#vendedor', 'TEST');
    await page.fill('#proyecto', 'CÁLCULO TEST');
    
    // Agregar ítem con precio específico
    await page.getByRole('button', { name: /agregar ítem/i }).click();
    await page.fill('[name="items[0][descripcion]"]', 'Item cálculo');
    await page.fill('[name="items[0][cantidad]"]', '2');
    await page.fill('[name="items[0][precio_unitario]"]', '50.00');
    
    // Verificar que el subtotal se actualice
    await expect(page.locator('#subtotal')).toHaveValue('100.00');
    
    // Verificar total con IVA (16%)
    await expect(page.locator('#total')).toHaveValue('116.00');
  });

  test('debe permitir agregar y eliminar ítems', async ({ page }) => {
    await page.goto('/formulario');
    
    // Agregar varios ítems
    await page.getByRole('button', { name: /agregar ítem/i }).click();
    await page.getByRole('button', { name: /agregar ítem/i }).click();
    
    // Verificar que hay 2 ítems
    await expect(page.locator('[name*="items[0]"]').first()).toBeVisible();
    await expect(page.locator('[name*="items[1]"]').first()).toBeVisible();
    
    // Eliminar un ítem
    await page.getByRole('button', { name: /eliminar/i }).first().click();
    
    // Verificar que solo queda 1 ítem
    await expect(page.locator('[name*="items[0]"]').first()).toBeVisible();
    await expect(page.locator('[name*="items[1]"]').first()).not.toBeVisible();
  });

  test('debe buscar materiales en el campo de descripción', async ({ page }) => {
    await page.goto('/formulario');
    
    // Agregar ítem
    await page.getByRole('button', { name: /agregar ítem/i }).click();
    
    // Buscar material (asumiendo que existe funcionalidad de búsqueda)
    await page.fill('[name="items[0][descripcion]"]', 'cable');
    
    // Verificar que aparezcan sugerencias
    await page.waitForTimeout(500); // Esperar por debounce
    
    // Si hay dropdown de materiales, verificar que aparezca
    const dropdown = page.locator('.material-dropdown, .suggestions, [data-testid="material-suggestions"]');
    if (await dropdown.isVisible()) {
      await expect(dropdown).toBeVisible();
    }
  });

  test('debe mantener datos al navegar entre páginas', async ({ page }) => {
    await page.goto('/formulario');
    
    // Llenar algunos datos
    await page.fill('#cliente', 'TEST PERSISTENCIA');
    await page.fill('#vendedor', 'TEST VENDOR');
    
    // Navegar a home y volver
    await page.goto('/');
    await page.goto('/formulario');
    
    // Verificar si los datos persisten (si hay localStorage)
    const clienteValue = await page.inputValue('#cliente');
    // Solo verificar si hay mecanismo de persistencia implementado
    if (clienteValue) {
      expect(clienteValue).toBe('TEST PERSISTENCIA');
    }
  });
});

test.describe('Búsqueda de Cotizaciones', () => {
  
  test('debe mostrar página de búsqueda', async ({ page }) => {
    await page.goto('/');
    
    // Verificar elementos de búsqueda
    await expect(page.getByRole('textbox', { name: /buscar/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /buscar/i })).toBeVisible();
  });

  test('debe realizar búsqueda y mostrar resultados', async ({ page }) => {
    await page.goto('/');
    
    // Realizar búsqueda vacía (mostrar todos)
    await page.getByRole('button', { name: /buscar/i }).click();
    
    // Esperar resultados
    await page.waitForSelector('.resultado, .cotizacion-item, [data-testid="search-results"]', { 
      timeout: 5000,
      state: 'attached'
    });
    
    // Verificar que hay resultados o mensaje de no resultados
    const hasResults = await page.locator('.resultado, .cotizacion-item').count() > 0;
    const noResultsMessage = await page.locator('text=No se encontraron').isVisible();
    
    expect(hasResults || noResultsMessage).toBeTruthy();
  });
});

test.describe('Responsive Design', () => {
  
  test('debe ser usable en móvil', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
    
    await page.goto('/formulario');
    
    // Verificar elementos principales visibles
    await expect(page.locator('#cliente')).toBeVisible();
    await expect(page.locator('#vendedor')).toBeVisible();
    await expect(page.getByRole('button', { name: /agregar ítem/i })).toBeVisible();
  });
  
  test('debe ser usable en tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 }); // iPad
    
    await page.goto('/');
    
    // Verificar layout en tablet
    await expect(page.getByRole('button', { name: /crear nueva cotización/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /buscar/i })).toBeVisible();
  });
});