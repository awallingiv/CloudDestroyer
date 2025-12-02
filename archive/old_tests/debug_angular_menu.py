#!/usr/bin/env python3
"""
Debug script to analyze the Angular menu structure at Bubba's 33
and figure out how to extract the actual menu items
"""

import time
import logging
from api import RestaurantMenuScraper

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def debug_angular_menu_structure():
    """Debug the Angular menu structure to understand how to extract items"""
    
    print("=" * 80)
    print("DEBUGGING ANGULAR MENU STRUCTURE")
    print("=" * 80)
    
    try:
        with RestaurantMenuScraper() as scraper:
            # Get the menu page with selenium access
            menu_url = "https://bubbas33.com/menu"
            
            print(f"Getting menu page: {menu_url}")
            
            # Force selenium usage for debugging
            from src.bypass.strategies.selenium_stealth import SeleniumStealth
            selenium_strategy = SeleniumStealth(headless=False, timeout=60)  # Non-headless for debugging
            response = selenium_strategy.get(menu_url)
            
            # Access driver through the selenium_strategy object
            if hasattr(selenium_strategy, 'driver') and selenium_strategy.driver:
                driver = selenium_strategy.driver
                print("✓ Got Selenium driver access")
                
                # Wait for Angular to load
                time.sleep(8)
                
                # Debug JavaScript execution to find menu data
                debug_scripts = [
                    # Check for Angular components
                    """
                    console.log('=== Angular Debug ===');
                    
                    // Check if Angular is present
                    console.log('Angular available:', typeof window.ng !== 'undefined');
                    
                    // Look for menu data in various places
                    console.log('Window keys:', Object.keys(window).filter(k => k.toLowerCase().includes('menu')));
                    
                    // Check Angular elements
                    const ngElements = document.querySelectorAll('[ng-version]');
                    console.log('Angular elements found:', ngElements.length);
                    
                    // Look for category containers
                    const categories = document.querySelectorAll('[class*=\"category\"], [data-cy*=\"category\"], .menu-category');
                    console.log('Category containers:', categories.length);
                    
                    // Look for item containers within categories  
                    categories.forEach((cat, i) => {
                        const items = cat.querySelectorAll('[class*=\"item\"], [class*=\"product\"], .menu-item, li');
                        console.log(`Category ${i} items:`, items.length);
                        if (items.length > 0) {
                            console.log('First item text:', items[0].textContent.substring(0, 100));
                        }
                    });
                    
                    // Look for buttons or links that might load items
                    const buttons = document.querySelectorAll('button, [role=\"button\"], .btn');
                    const menuButtons = Array.from(buttons).filter(btn => 
                        btn.textContent && (btn.textContent.toLowerCase().includes('appetizer') || 
                        btn.textContent.toLowerCase().includes('pizza') || 
                        btn.textContent.toLowerCase().includes('burger'))
                    );
                    console.log('Menu category buttons:', menuButtons.length);
                    
                    return {
                        angularPresent: typeof window.ng !== 'undefined',
                        categoryContainers: categories.length,
                        menuButtons: menuButtons.length
                    };
                    """
                ]
                
                for script in debug_scripts:
                    try:
                        result = driver.execute_script(script)
                        print(f"Debug script result: {result}")
                    except Exception as e:
                        print(f"Debug script failed: {e}")
                
                # Try clicking on category buttons to load menu items
                print("\n=== Trying to interact with menu categories ===")
                
                category_interaction_script = """
                // Try to click on the first category to see if it loads items
                const categoryButtons = document.querySelectorAll('button, [role="button"], .btn, [class*="category"]');
                
                for (let i = 0; i < Math.min(3, categoryButtons.length); i++) {
                    const btn = categoryButtons[i];
                    const text = btn.textContent || '';
                    
                    if (text.toLowerCase().includes('appetizer') || 
                        text.toLowerCase().includes('pizza') || 
                        text.toLowerCase().includes('wings')) {
                        console.log('Clicking category:', text);
                        btn.click();
                        
                        // Wait a bit for content to load
                        setTimeout(() => {
                            // Look for newly loaded items
                            const items = document.querySelectorAll('[class*=\"item\"], .menu-item, [class*=\"product\"]');
                            console.log('Items after click:', items.length);
                            
                            items.forEach((item, idx) => {
                                if (idx < 3) { // Show first 3 items
                                    console.log(`Item ${idx}:`, item.textContent.substring(0, 100));
                                }
                            });
                        }, 2000);
                        
                        break;
                    }
                }
                
                return 'Category interaction attempted';
                """
                
                try:
                    driver.execute_script(category_interaction_script)
                    time.sleep(3)  # Wait for any loading
                    
                    # Check for items again after interaction
                    items_check_script = """
                    const allItems = document.querySelectorAll('[class*=\"item\"], .menu-item, [class*=\"product\"], [class*=\"dish\"]');
                    const itemsWithText = Array.from(allItems).filter(item => {
                        const text = item.textContent || '';
                        return text.length > 10 && text.length < 200;
                    });
                    
                    console.log('Total potential items found:', itemsWithText.length);
                    
                    const sampleItems = itemsWithText.slice(0, 5).map(item => ({
                        text: item.textContent.substring(0, 100),
                        className: item.className,
                        tagName: item.tagName
                    }));
                    
                    return {
                        totalItems: itemsWithText.length,
                        samples: sampleItems
                    };
                    """
                    
                    items_result = driver.execute_script(items_check_script)
                    print(f"Items found after interaction: {items_result}")
                    
                except Exception as e:
                    print(f"Category interaction failed: {e}")
                
                # Final comprehensive search
                print("\n=== Final comprehensive item search ===")
                final_search_script = """
                // Comprehensive search for any element that might contain menu items
                const allElements = document.querySelectorAll('*');
                const potentialItems = [];
                
                allElements.forEach(el => {
                    const text = el.textContent || '';
                    
                    // Look for elements with food-related text and price patterns
                    if (text.length > 15 && text.length < 300) {
                        const hasFood = /(chicken|beef|burger|pizza|wing|salad|pasta|sandwich|fries|cheese)/i.test(text);
                        const hasPrice = /\\$\\d+/i.test(text);
                        
                        if (hasFood || hasPrice) {
                            potentialItems.push({
                                text: text.substring(0, 150),
                                tag: el.tagName,
                                class: el.className.substring(0, 50),
                                hasPrice: hasPrice
                            });
                        }
                    }
                });
                
                return {
                    totalPotential: potentialItems.length,
                    samples: potentialItems.slice(0, 10)
                };
                """
                
                try:
                    final_result = driver.execute_script(final_search_script)
                    print(f"Final comprehensive search: {final_result}")
                except Exception as e:
                    print(f"Final search failed: {e}")
                
                print("\n=== Analysis complete ===")
                
            else:
                print("❌ No Selenium driver access available")
                
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_angular_menu_structure()