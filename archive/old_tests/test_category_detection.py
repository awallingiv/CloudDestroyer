#!/usr/bin/env python3

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_category_detection():
    print("Testing category detection logic...")
    
    driver = uc.Chrome()
    try:
        driver.get("https://bubbas33.com/menu")
        time.sleep(5)  # Wait for page load
        
        # Test the category detection JavaScript
        result = driver.execute_script("""
            // Look for direct category navigation links
            const categoryLinks = Array.from(document.querySelectorAll('a')).filter(link => {
                const href = link.href || '';
                const text = (link.textContent || '').toLowerCase().trim();
                
                console.log(`Link: ${text} -> ${href}`);
                
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
                console.log(`Category ${i}: ${cat.text} -> ${cat.url}`);
            });
            
            return categoryData;
        """)
        
        print(f"JavaScript returned {len(result)} categories:")
        for i, cat in enumerate(result):
            print(f"  {i}: {cat['text']} -> {cat['url']}")
            
        # Also test simple link counting
        simple_count = driver.execute_script("""
            const menuLinks = Array.from(document.querySelectorAll('a')).filter(link => {
                const href = link.href || '';
                return href.includes('/menu/');
            });
            console.log('Menu links found:', menuLinks.length);
            return {
                count: menuLinks.length,
                samples: menuLinks.slice(0, 5).map(l => ({ text: l.textContent.trim(), href: l.href }))
            };
        """)
        
        print(f"\nSimple menu link count: {simple_count['count']}")
        print("Sample links:")
        for link in simple_count['samples']:
            print(f"  {link['text']} -> {link['href']}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    test_category_detection()