#!/usr/bin/env python3

import undetected_chromedriver as uc
import time

def test_category_extraction_context():
    print("Testing category extraction in context...")
    
    driver = uc.Chrome()
    try:
        # Navigate to menu page
        driver.get("https://bubbas33.com/menu")
        time.sleep(10)  # Wait longer for complete load
        
        print("Page loaded. Running category detection...")
        
        # Run the exact same JavaScript as in the main function
        categories = driver.execute_script("""
            // Look for direct category navigation links
            const categoryLinks = Array.from(document.querySelectorAll('a')).filter(link => {
                const href = link.href || '';
                const text = (link.textContent || '').toLowerCase().trim();
                
                console.log(`Checking link: "${text}" -> "${href}"`);
                
                // Look for menu category patterns in URLs and text
                const hasMenuInUrl = href.includes('/menu/') && (href.includes('bubbas33.com') || href.includes(window.location.hostname) || link.getAttribute('href')?.startsWith('/menu/'));
                const hasCategory = /appetizer|wing|pizza|burger|pasta|salad|dinner|dessert|beverage|handhold|side|kid|meal|feast/i.test(text);
                
                console.log(`  hasMenuInUrl: ${hasMenuInUrl}, hasCategory: ${hasCategory}`);
                
                return hasMenuInUrl && hasCategory && text.length > 3 && text.length < 50;
            });
            
            console.log('Found category URLs:', categoryLinks.length);
            
            const categoryData = categoryLinks.map((link, i) => ({
                index: i,
                text: link.textContent.trim(),
                href: link.href,
                url: link.href
            }));
            
            categoryData.forEach((cat, i) => {
                if (i < 10) {
                    console.log(`Category ${i}: ${cat.text} -> ${cat.url}`);
                }
            });
            
            return categoryData;
        """)
        
        print(f"Categories found: {len(categories)}")
        for i, cat in enumerate(categories[:10]):
            print(f"  {i}: {cat['text']} -> {cat['url']}")
            
        if len(categories) == 0:
            print("\nNo categories found. Let's debug...")
            
            # Check what's on the page
            debug_info = driver.execute_script("""
                const allLinks = Array.from(document.querySelectorAll('a'));
                const menuLinks = allLinks.filter(link => link.href.includes('/menu/'));
                
                return {
                    totalLinks: allLinks.length,
                    menuLinks: menuLinks.length,
                    menuSamples: menuLinks.slice(0, 5).map(l => ({ 
                        text: l.textContent.trim(), 
                        href: l.href,
                        visible: l.offsetParent !== null 
                    })),
                    pageTitle: document.title,
                    url: window.location.href,
                    hostname: window.location.hostname
                };
            """)
            
            print(f"Debug info:")
            print(f"  Total links: {debug_info['totalLinks']}")
            print(f"  Menu links: {debug_info['menuLinks']}")
            print(f"  Page title: {debug_info['pageTitle']}")
            print(f"  Current URL: {debug_info['url']}")
            print(f"  Hostname: {debug_info['hostname']}")
            print(f"  Menu link samples:")
            for sample in debug_info['menuSamples']:
                print(f"    '{sample['text']}' -> {sample['href']} (visible: {sample['visible']})")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    test_category_extraction_context()