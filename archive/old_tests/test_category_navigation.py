#!/usr/bin/env python3

import undetected_chromedriver as uc
import time

def test_category_navigation():
    print("Testing category navigation...")
    
    driver = uc.Chrome()
    try:
        # Navigate to menu page first
        driver.get("https://bubbas33.com/menu")
        time.sleep(10)  # Wait for complete load
        
        # Get categories
        categories = driver.execute_script("""
            const categoryLinks = Array.from(document.querySelectorAll('a')).filter(link => {
                const href = link.href || '';
                const text = (link.textContent || '').toLowerCase().trim();
                const hasMenuInUrl = href.includes('/menu/') && (href.includes('bubbas33.com') || href.includes(window.location.hostname) || link.getAttribute('href')?.startsWith('/menu/'));
                const hasCategory = /appetizer|wing|pizza|burger|pasta|salad|dinner|dessert|beverage|handhold|side|kid|meal|feast/i.test(text);
                return hasMenuInUrl && hasCategory && text.length > 3 && text.length < 50;
            });
            
            return categoryLinks.slice(0, 3).map((link, i) => ({
                index: i,
                text: link.textContent.trim(),
                href: link.href,
                url: link.href
            }));
        """)
        
        print(f"Found {len(categories)} categories to test:")
        
        for category in categories:
            print(f"\nTesting category: {category['text']} -> {category['url']}")
            
            # Navigate to category URL
            driver.get(category['url'])
            time.sleep(5)
            
            # Check what we get
            result = driver.execute_script("""
                return {
                    title: document.title,
                    url: window.location.href,
                    hasMenuItems: document.querySelectorAll('[data-testid*="item"], .menu-item, .item').length > 0,
                    itemCount: document.querySelectorAll('[data-testid*="item"], .menu-item, .item').length,
                    bodyText: document.body.innerText.substring(0, 200)
                };
            """)
            
            print(f"  Page title: {result['title']}")
            print(f"  Current URL: {result['url']}")
            print(f"  Has menu items: {result['hasMenuItems']}")
            print(f"  Item elements found: {result['itemCount']}")
            print(f"  Page preview: {result['bodyText'][:100]}...")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    test_category_navigation()