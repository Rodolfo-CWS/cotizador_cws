"""
Test script for validating the optimized desglose page UI/UX improvements
"""
from playwright.sync_api import sync_playwright
import time
import os

def test_desglose_ui_optimization():
    """Test the optimized desglose page design"""
    
    with sync_playwright() as p:
        # Launch browser in visible mode to see the changes
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()
        
        # Set viewport for desktop testing
        page.set_viewport_size({"width": 1200, "height": 800})
        
        try:
            print("🚀 Testing optimized desglose page...")
            
            # First, go to home page to search for a quotation
            print("📋 Navigating to home page...")
            page.goto("http://127.0.0.1:5000")
            page.wait_for_load_state("networkidle")
            
            # Search for any quotation to get a desglose link
            print("🔍 Searching for quotations...")
            search_input = page.locator("#searchInput")
            search_input.fill("")  # Empty search returns all results
            
            search_button = page.locator("button:has-text('Buscar')")
            search_button.click()
            
            # Wait for search results
            page.wait_for_timeout(2000)
            
            # Look for any "Ver Desglose" button
            desglose_buttons = page.locator("a:has-text('Ver Desglose')")
            if desglose_buttons.count() > 0:
                print("📊 Found desglose link - clicking to view optimized page...")
                desglose_buttons.first.click()
                page.wait_for_load_state("networkidle")
                
                # Take screenshot of optimized desglose page
                screenshot_path = "screenshots/desglose_optimized.png"
                os.makedirs("screenshots", exist_ok=True)
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Screenshot saved: {screenshot_path}")
                
                # Test visual elements
                print("🎨 Testing visual improvements...")
                
                # Check for corporate header
                header = page.locator(".corporate-header")
                assert header.is_visible(), "Corporate header should be visible"
                print("✅ Corporate header found")
                
                # Check for enhanced sections
                primary_sections = page.locator(".section.primary")
                financial_sections = page.locator(".section.financial") 
                assert primary_sections.count() > 0, "Primary sections should exist"
                assert financial_sections.count() > 0, "Financial sections should exist"
                print(f"✅ Found {primary_sections.count()} primary sections and {financial_sections.count()} financial sections")
                
                # Check for modern buttons
                modern_buttons = page.locator(".btn-system")
                assert modern_buttons.count() > 0, "Modern button system should be present"
                print(f"✅ Found {modern_buttons.count()} modern buttons")
                
                # Check for enhanced materials table if present
                materials_tables = page.locator(".materials-table")
                if materials_tables.count() > 0:
                    print(f"✅ Found {materials_tables.count()} enhanced materials tables")
                
                # Check for cost breakdown cards
                cost_items = page.locator(".cost-item")
                if cost_items.count() > 0:
                    print(f"✅ Found {cost_items.count()} cost breakdown items")
                
                # Test hover effects by hovering over sections
                print("🖱️ Testing hover effects...")
                sections = page.locator(".section")
                if sections.count() > 0:
                    sections.first.hover()
                    page.wait_for_timeout(1000)
                    print("✅ Section hover effect tested")
                
                # Test mobile responsiveness
                print("📱 Testing mobile responsiveness...")
                page.set_viewport_size({"width": 375, "height": 667})
                page.wait_for_timeout(1000)
                
                # Take mobile screenshot
                mobile_screenshot = "screenshots/desglose_mobile_optimized.png"
                page.screenshot(path=mobile_screenshot, full_page=True)
                print(f"📸 Mobile screenshot saved: {mobile_screenshot}")
                
                # Check that elements are still visible on mobile
                header = page.locator(".corporate-header")
                assert header.is_visible(), "Header should be visible on mobile"
                
                actions = page.locator(".actions")
                assert actions.is_visible(), "Actions section should be visible on mobile"
                print("✅ Mobile responsiveness validated")
                
                print("🎉 All UI/UX optimization tests PASSED!")
                
                # Keep browser open for manual inspection
                print("🔍 Browser will stay open for 30 seconds for manual inspection...")
                page.wait_for_timeout(30000)
                
            else:
                print("❌ No quotations found - creating a test quotation first...")
                # Navigate to form to create a test quotation
                page.goto("http://127.0.0.1:5000/formulario")
                page.wait_for_load_state("networkidle")
                
                # Take screenshot of the form page for reference
                page.screenshot(path="screenshots/form_page.png")
                print("📸 Form page screenshot saved for reference")
                
                print("ℹ️  Please create a quotation first, then run this test again")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            page.screenshot(path="screenshots/error_state.png")
            raise
            
        finally:
            browser.close()
            print("🏁 Test completed")

if __name__ == "__main__":
    test_desglose_ui_optimization()