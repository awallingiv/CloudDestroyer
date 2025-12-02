#!/usr/bin/env python3

"""
Simple test to check what links exist on Bubba's 33 menu page
"""

import undetected_chromedriver as uc
import time

def simple_link_test():
    print("🔍 Simple link detection test for Bubba's 33...")
    print("=" * 60)
    
    try:
        driver = uc.Chrome()
        print("✅ Chrome driver created")
        
        print("🌐 Navigating to https://bubbas33.com/menu...")
        driver.get("https://bubbas33.com/menu")
        
        print("⏳ Waiting for page to load...")
        time.sleep(8)  # Give page time to fully load
        
        print(f"📄 Page title: {driver.title}")
        print(f"🔗 Current URL: {driver.current_url}")
        
        # Get all links
        all_links = driver.execute_script("""
            const links = Array.from(document.querySelectorAll('a'));
            return links.map(link => ({
                text: (link.textContent || '').trim(),
                href: link.href || '',
                id: link.id || '',
                className: link.className || ''
            }));
        """)
        
        print(f"\n📊 Found {len(all_links)} total links")
        
        # Filter for menu-related links
        menu_links = [link for link in all_links if '/menu/' in link['href']]
        print(f"🍽️  Found {len(menu_links)} links with '/menu/' in href:")
        
        for i, link in enumerate(menu_links[:20]):  # Show first 20
            print(f"   {i+1}. '{link['text'][:50]}' -> {link['href']}")
            if link['className']:
                print(f"      Class: {link['className']}")
        
        # Check for category-related text in links
        category_words = ['appetizer', 'wing', 'pizza', 'burger', 'pasta', 'salad', 'dinner', 'dessert', 'beverage', 'side', 'kid', 'meal']
        category_links = []
        
        for link in all_links:
            text = link['text'].lower()
            for word in category_words:
                if word in text and len(text) > 3 and len(text) < 50:
                    category_links.append(link)
                    break
        
        print(f"\n🏷️  Found {len(category_links)} links with category text:")
        for i, link in enumerate(category_links[:10]):
            print(f"   {i+1}. '{link['text']}' -> {link['href']}")
        
        # Check page source for Angular router links
        page_source = driver.page_source
        if 'routerLink' in page_source:
            print(f"\n🅰️  Page contains Angular routerLink directives")
        if 'ng-' in page_source:
            print(f"🅰️  Page contains Angular directives")
        if 'ion-' in page_source:
            print(f"📱 Page contains Ionic components")
            
        # Look for specific elements
        category_elements = driver.execute_script("""
            const categoryCards = Array.from(document.querySelectorAll('.category-card, .our-menu-category, [class*="category"], [class*="menu-item"]'));
            return categoryCards.map(el => ({
                tagName: el.tagName,
                className: el.className,
                text: (el.textContent || '').trim().substring(0, 100),
                hasLink: !!el.querySelector('a'),
                linkHref: el.querySelector('a') ? el.querySelector('a').href : ''
            }));
        """)
        
        print(f"\n🃏 Found {len(category_elements)} category-like elements:")
        for i, elem in enumerate(category_elements[:10]):
            print(f"   {i+1}. {elem['tagName']} ({elem['className'][:50]})")
            print(f"      Text: {elem['text']}")
            if elem['hasLink']:
                print(f"      Link: {elem['linkHref']}")
        
        driver.quit()
        print("\n✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_link_test()