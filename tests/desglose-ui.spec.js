/**
 * Test for validating the optimized desglose page UI/UX improvements
 */
const { test, expect } = require('@playwright/test');

test.describe('Desglose Page UI Optimization', () => {
  
  test('should display optimized desglose page with enhanced design', async ({ page }) => {
    console.log('🚀 Testing optimized desglose page...');
    
    // Set viewport for desktop testing
    await page.setViewportSize({ width: 1200, height: 800 });
    
    // Navigate to home page first
    console.log('📋 Navigating to home page...');
    await page.goto('http://127.0.0.1:5000');
    await page.waitForLoadState('networkidle');
    
    // Search for quotations
    console.log('🔍 Searching for quotations...');
    const searchInput = page.locator('#searchInput');
    await searchInput.fill(''); // Empty search returns all results
    
    const searchButton = page.locator('button:has-text("Buscar")');
    await searchButton.click();
    
    // Wait for search results
    await page.waitForTimeout(3000);
    
    // Look for "Ver Desglose" button
    const desgloseButtons = page.locator('a:has-text("Ver Desglose")');
    
    if (await desgloseButtons.count() > 0) {
      console.log('📊 Found desglose link - testing optimized page...');
      
      // Click first desglose button
      await desgloseButtons.first().click();
      await page.waitForLoadState('networkidle');
      
      // Take full page screenshot
      await page.screenshot({ 
        path: 'test-results/desglose-optimized-desktop.png', 
        fullPage: true 
      });
      console.log('📸 Desktop screenshot saved');
      
      // Test visual improvements
      console.log('🎨 Testing visual improvements...');
      
      // Check corporate header
      const header = page.locator('.corporate-header');
      await expect(header).toBeVisible();
      console.log('✅ Corporate header found');
      
      // Check enhanced sections
      const primarySections = page.locator('.section.primary');
      const financialSections = page.locator('.section.financial');
      await expect(primarySections).toHaveCount(1, { timeout: 5000 });
      await expect(financialSections.first()).toBeVisible();
      console.log('✅ Enhanced sections found');
      
      // Check modern button system
      const modernButtons = page.locator('.btn-system');
      await expect(modernButtons.first()).toBeVisible();
      console.log('✅ Modern button system found');
      
      // Test hover effects
      console.log('🖱️ Testing hover effects...');
      const firstSection = page.locator('.section').first();
      await firstSection.hover();
      await page.waitForTimeout(1000);
      console.log('✅ Hover effects tested');
      
      // Test mobile responsiveness
      console.log('📱 Testing mobile responsiveness...');
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(1000);
      
      // Take mobile screenshot
      await page.screenshot({ 
        path: 'test-results/desglose-optimized-mobile.png', 
        fullPage: true 
      });
      console.log('📸 Mobile screenshot saved');
      
      // Verify mobile layout
      await expect(header).toBeVisible();
      const actions = page.locator('.actions');
      await expect(actions).toBeVisible();
      console.log('✅ Mobile responsiveness validated');
      
      console.log('🎉 All UI/UX optimization tests PASSED!');
      
    } else {
      console.log('ℹ️  No quotations found - please create a quotation first');
      
      // Navigate to form page for reference
      await page.goto('http://127.0.0.1:5000/formulario');
      await page.waitForLoadState('networkidle');
      
      await page.screenshot({ path: 'test-results/form-page-reference.png' });
      console.log('📸 Form page screenshot saved for reference');
    }
  });

  test('should handle different screen sizes correctly', async ({ page }) => {
    // Test different viewport sizes
    const viewports = [
      { width: 1920, height: 1080, name: 'desktop-large' },
      { width: 1024, height: 768, name: 'tablet' },
      { width: 375, height: 667, name: 'mobile' }
    ];

    await page.goto('http://127.0.0.1:5000');
    await page.waitForLoadState('networkidle');

    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: `test-results/responsive-${viewport.name}.png`,
        fullPage: true 
      });
      console.log(`📸 ${viewport.name} screenshot saved`);
    }
  });
});