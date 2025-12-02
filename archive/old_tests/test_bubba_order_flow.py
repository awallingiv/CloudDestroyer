#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.core.cloud_destroyer import CloudDestroyer
from api import RestaurantMenuScraper

def test_bubba_order_flow():
    """Test what happens when we click Order buttons on Bubba's 33"""
    
    print("=" * 80)
    print("TESTING BUBBA'S 33 ORDER FLOW")
    print("=" * 80)
    
    destroyer = CloudDestroyer()
    scraper = RestaurantMenuScraper()
    scraper.cloud_destroyer = destroyer
    
    # Get the menu page first
    url = "https://bubbas33.com/menu"
    print(f"Getting menu page: {url}")
    
    try:
        response = destroyer.get(url)
        if not response or response.status_code != 200:
            print(f"❌ Failed to get page: {response.status_code if response else 'No response'}")
            return
            
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"✓ Page loaded: {soup.title.get_text().strip()}")
        
        # Now use a separate selenium session to interact with the page
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import undetected_chromedriver as uc
        
        # Setup Chrome options
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = uc.Chrome(options=options)
        driver.get(url)
        print("✓ Got Selenium driver access")
        
        # Wait for JavaScript to load
        print("⏳ Waiting for page to fully load...")
        time.sleep(5)
        
        # Look for Order buttons and category links
        analysis_script = """
        console.log('=== ANALYZING PAGE CONTENT ===');
        console.log('Page title:', document.title);
        console.log('Page URL:', window.location.href);
        
        // First, let's see what's actually on the page
        console.log('All elements with "order" text:');
        const allElements = Array.from(document.querySelectorAll('*'));
        const orderElements = allElements.filter(el => {
            const text = el.textContent || '';
            return text.toLowerCase().includes('order');
        });
        
        console.log('Elements containing "order":', orderElements.length);
        orderElements.slice(0, 10).forEach((el, i) => {
            console.log(`  ${i}: ${el.tagName} - "${el.textContent.substring(0, 50)}" - classes: ${el.className}`);
        });
        
        // Look for any buttons
        const allButtons = document.querySelectorAll('button, [role="button"], .btn, input[type="button"]');
        console.log('All buttons found:', allButtons.length);
        allButtons.forEach((btn, i) => {
            if (i < 10) {
                console.log(`  Button ${i}: ${btn.tagName} - "${btn.textContent.substring(0, 30)}" - classes: ${btn.className}`);
            }
        });
        
        // Look for any links
        const allLinks = document.querySelectorAll('a[href]');
        console.log('All links found:', allLinks.length);
        allLinks.forEach((link, i) => {
            if (i < 10 && link.textContent.trim()) {
                console.log(`  Link ${i}: "${link.textContent.substring(0, 30)}" - href: ${link.href}`);
            }
        });
        
        // Look specifically for menu-related elements
        const menuElements = document.querySelectorAll('[class*="menu"], [class*="category"], [id*="menu"], [id*="category"]');
        console.log('Menu-related elements:', menuElements.length);
        menuElements.forEach((el, i) => {
            if (i < 5) {
                console.log(`  Menu ${i}: ${el.tagName} - classes: ${el.className} - id: ${el.id} - text: "${el.textContent.substring(0, 50)}"`);
            }
        });
        
        return {
            orderElements: orderElements.length,
            allButtons: allButtons.length,
            allLinks: allLinks.length,
            menuElements: menuElements.length,
            currentUrl: window.location.href,
            pageTitle: document.title
        };
        """
        
        result = driver.execute_script(analysis_script)
        print(f"Analysis result: {result}")
        
        # Now that we know there are buttons and links, let's try clicking them
        if result.get('allButtons') > 0 or result.get('allLinks') > 0:
            print(f"\n=== FOUND {result.get('allButtons')} BUTTONS AND {result.get('allLinks')} LINKS ===")
            
            click_script = """
            console.log('=== LOOKING FOR CLICKABLE ORDER ELEMENTS ===');
            
            // Find buttons or links with "order" in their text or that look like category buttons
            const allClickable = Array.from(document.querySelectorAll('button, a, [role="button"]'));
            
            // Look for Order-related buttons first
            const orderButtons = allClickable.filter(el => {
                const text = (el.textContent || '').toLowerCase();
                return text.includes('order') || text.includes('add to cart') || text.includes('select');
            });
            
            console.log('Order-related clickable elements:', orderButtons.length);
            orderButtons.forEach((btn, i) => {
                if (i < 5) {
                    console.log(`  Order ${i}: ${btn.tagName} - "${btn.textContent.substring(0, 40)}" - href: ${btn.href || 'none'}`);
                }
            });
            
            // Look for category buttons (appetizers, wings, etc.)
            const categoryButtons = allClickable.filter(el => {
                const text = (el.textContent || '').toLowerCase();
                return text.includes('appetizer') || text.includes('wing') || text.includes('pizza') || 
                       text.includes('burger') || text.includes('pasta') || text.includes('salad');
            });
            
            console.log('Category clickable elements:', categoryButtons.length);
            categoryButtons.forEach((btn, i) => {
                if (i < 5) {
                    console.log(`  Category ${i}: ${btn.tagName} - "${btn.textContent.substring(0, 40)}" - href: ${btn.href || 'none'}`);
                }
            });
            
            // Try clicking the first order button if available
            if (orderButtons.length > 0) {
                const btn = orderButtons[0];
                console.log('Attempting to click Order button:', btn.textContent.substring(0, 40));
                btn.click();
                return { clicked: 'order', text: btn.textContent.substring(0, 40), href: btn.href };
            }
            
            // Try clicking the first category button as fallback
            if (categoryButtons.length > 0) {
                const btn = categoryButtons[0];
                console.log('Attempting to click Category button:', btn.textContent.substring(0, 40));
                btn.click();
                return { clicked: 'category', text: btn.textContent.substring(0, 40), href: btn.href };
            }
            
            return { clicked: 'none', orderButtons: orderButtons.length, categoryButtons: categoryButtons.length };
            """
            
            click_result = driver.execute_script(click_script)
            print(f"Click attempt result: {click_result}")
            
            # Wait for any navigation or content changes
            time.sleep(4)
            
            # Check what happened after the click
            new_url = driver.current_url
            new_title = driver.title
            
            print(f"\n=== AFTER CLICK ===")
            print(f"New URL: {new_url}")
            print(f"New Title: {new_title}")
            
            # Look for menu items with prices on the new page
            menu_check_script = """
            console.log('=== SEARCHING FOR MENU ITEMS WITH PRICES ===');
            
            const allElements = Array.from(document.querySelectorAll('*'));
            const itemsWithPrices = allElements.filter(el => {
                const text = el.textContent || '';
                return /\\$\\d+(?:\\.\\d{2})?/.test(text) && text.length > 10 && text.length < 500;
            });
            
            console.log('Items with prices found:', itemsWithPrices.length);
            
            itemsWithPrices.slice(0, 10).forEach((item, i) => {
                console.log(`  Item ${i}: "${item.textContent.substring(0, 80)}" - ${item.tagName}.${item.className}`);
            });
            
            return {
                itemsWithPrices: itemsWithPrices.length,
                samples: itemsWithPrices.slice(0, 5).map(item => ({
                    text: item.textContent.substring(0, 100),
                    className: item.className,
                    tagName: item.tagName
                }))
            };
            """
            
            menu_result = driver.execute_script(menu_check_script)
            print(f"\n🎯 MENU ITEMS FOUND: {menu_result}")
            
            if menu_result.get('itemsWithPrices', 0) > 0:
                print("\n🎉 SUCCESS! Found menu items with prices!")
            else:
                print("\n❌ Still no menu items found on this page")
                    
        else:
            print("❌ No clickable elements found")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        destroyer.cleanup()

if __name__ == "__main__":
    test_bubba_order_flow()