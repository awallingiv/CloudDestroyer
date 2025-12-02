#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

def debug_bubba_buttons():
    """Debug what buttons are actually available on Bubba's 33"""
    
    print("=" * 80)
    print("DEBUGGING BUBBA'S 33 BUTTON STRUCTURE")
    print("=" * 80)
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = uc.Chrome(options=options)
    
    try:
        url = "https://bubbas33.com/menu"
        print(f"Loading: {url}")
        
        driver.get(url)
        time.sleep(5)  # Wait for page to load
        
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Comprehensive button analysis
        analysis_script = """
        console.log('=== COMPREHENSIVE BUTTON ANALYSIS ===');
        
        // Find actual clickable elements (not just all elements)
        const allClickable = Array.from(document.querySelectorAll('a, button, [role="button"], [onclick], .btn, .button'));
        
        // Also find elements with cursor pointer
        const cursorPointers = Array.from(document.querySelectorAll('*')).filter(el => {
            const styles = window.getComputedStyle(el);
            return styles.cursor === 'pointer' && (el.textContent || '').trim().length > 0 && (el.textContent || '').trim().length < 100;
        });
        
        // Combine and deduplicate
        const combinedClickable = [...new Set([...allClickable, ...cursorPointers])];
        
        console.log('Direct clickable elements found:', allClickable.length);
        console.log('Cursor pointer elements found:', cursorPointers.length);
        console.log('Total combined clickable elements found:', combinedClickable.length);
        
        // Analyze each clickable element
        const analysis = [];
        combinedClickable.forEach((el, i) => {
            if (i < 20) { // Analyze first 20 elements
                const text = (el.textContent || '').trim();
                analysis.push({
                    index: i,
                    tag: el.tagName,
                    classes: el.className,
                    text: text.substring(0, 50),
                    href: el.href || null,
                    hasOrderText: text.toLowerCase().includes('order'),
                    hasCategoryText: /appetizer|wing|pizza|burger|pasta|salad|dinner|dessert|beverage/i.test(text)
                });
                
                console.log(`Element ${i}: ${el.tagName}.${el.className} - "${text.substring(0, 30)}" - Order: ${text.toLowerCase().includes('order')}`);
            }
        });
        
        // Look specifically for category cards
        const categoryCards = document.querySelectorAll('.category-card, [class*="category"]');
        console.log('Category cards found:', categoryCards.length);
        
        categoryCards.forEach((card, i) => {
            if (i < 10) {
                console.log(`Category card ${i}:`, card.className, '-', card.textContent.substring(0, 50));
                
                // Look for buttons/links within each card
                const buttons = card.querySelectorAll('a, button, [role="button"]');
                buttons.forEach((btn, j) => {
                    console.log(`  Button ${j}:`, btn.tagName, '-', btn.textContent.substring(0, 30));
                });
            }
        });
        
        // Look for Order buttons specifically
        const orderButtons = Array.from(combinedClickable).filter(el => {
            const text = (el.textContent || '').toLowerCase();
            return text.includes('order') && text.length < 50;
        });
        
        console.log('Order buttons found:', orderButtons.length);
        orderButtons.forEach((btn, i) => {
            if (i < 5) {
                console.log(`Order button ${i}:`, btn.tagName, '-', btn.textContent.substring(0, 40));
            }
        });
        
        return {
            totalClickable: combinedClickable.length,
            directClickable: allClickable.length,
            cursorPointers: cursorPointers.length,
            categoryCards: categoryCards.length,
            orderButtons: orderButtons.length,
            analysis: analysis
        };
        """
        
        result = driver.execute_script(analysis_script)
        print(f"\nAnalysis Result: {result}")
        
        # Also get browser console logs
        print("\n=== BROWSER CONSOLE LOGS ===")
        logs = driver.get_log('browser')
        for log in logs[-30:]:  # Show last 30 log entries
            print(f"[{log['level']}] {log['message']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_bubba_buttons()