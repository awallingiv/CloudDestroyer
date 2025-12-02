#!/usr/bin/env python3

"""
Debug script to test category URL detection for Bubba's 33
"""

import logging
from api import RestaurantMenuScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

def test_category_url_detection():
    """Test category URL detection specifically"""
    
    scraper = RestaurantMenuScraper()
    
    print("🔍 Testing category URL detection for Bubba's 33...")
    print("=" * 80)
    
    try:
        # Use our scraper's method to get a proper driver
        result = scraper._extract_js_menu_with_navigation("https://bubbas33.com/menu")
        
        if not result.get('success'):
            print(f"❌ Failed to get driver: {result.get('error', 'Unknown error')}")
            return
            
        # The method doesn't return the driver, so let's use the bypass orchestrator directly
        from src.bypass.bypass_orchestrator import BypassOrchestrator
        import undetected_chromedriver as uc
        
        # Create driver directly for debugging
        print("🚀 Creating Selenium driver directly...")
        driver = uc.Chrome()
        driver.get("https://bubbas33.com/menu")
            
        print("✅ Successfully bypassed Cloudflare")
        print(f"📄 Page title: {driver.title}")
        print(f"🔗 Current URL: {driver.current_url}")
        
        # Wait for page to load
        import time
        time.sleep(5)
        
        # Test our category detection JavaScript
        print("\n🔎 Testing category URL detection script...")
        
        categories = driver.execute_script("""
            console.log('Starting category detection...');
            
            // Look for direct category navigation links
            const allLinks = Array.from(document.querySelectorAll('a'));
            console.log(`Found ${allLinks.length} total links`);
            
            const categoryLinks = allLinks.filter(link => {
                const href = link.href || '';
                const text = (link.textContent || '').toLowerCase().trim();
                
                console.log(`Checking link: "${text}" -> ${href}`);
                
                // Look for menu category patterns in URLs and text
                const hasMenuInUrl = href.includes('/menu/') && href.includes(window.location.hostname);
                const hasCategory = /appetizer|wing|pizza|burger|pasta|salad|dinner|dessert|beverage|handhold|side|kid|meal|feast/i.test(text);
                
                if (hasMenuInUrl) {
                    console.log(`  Has menu URL: ${href}`);
                }
                if (hasCategory) {
                    console.log(`  Has category text: ${text}`);
                }
                
                return hasMenuInUrl && hasCategory && text.length > 3 && text.length < 50;
            });
            
            console.log(`Found ${categoryLinks.length} category links`);
            
            const categoryData = categoryLinks.map((link, i) => ({
                index: i,
                text: link.textContent.trim(),
                href: link.href,
                url: link.href
            }));
            
            // Also check for any /menu/ URLs regardless of text
            const menuUrls = allLinks.filter(link => {
                const href = link.href || '';
                return href.includes('/menu/') && href.includes(window.location.hostname);
            });
            
            console.log(`Found ${menuUrls.length} /menu/ URLs total:`);
            menuUrls.forEach((link, i) => {
                if (i < 20) {  // Log first 20
                    console.log(`  ${i+1}. "${link.textContent.trim()}" -> ${link.href}`);
                }
            });
            
            return {
                categoryData: categoryData,
                totalLinks: allLinks.length,
                menuUrlsFound: menuUrls.length,
                allMenuUrls: menuUrls.map(l => ({text: l.textContent.trim(), url: l.href})).slice(0, 20)
            };
        """)
        
        print(f"\n📊 Category Detection Results:")
        print(f"   Total links found: {categories['totalLinks']}")
        print(f"   Menu URLs found: {categories['menuUrlsFound']}")
        print(f"   Category links matched: {len(categories['categoryData'])}")
        
        print(f"\n🔗 First 10 Menu URLs found:")
        for i, url_info in enumerate(categories['allMenuUrls'][:10]):
            print(f"   {i+1}. '{url_info['text']}' -> {url_info['url']}")
        
        if categories['categoryData']:
            print(f"\n✅ Category links that matched our filter:")
            for cat in categories['categoryData']:
                print(f"   • {cat['text']} -> {cat['url']}")
        else:
            print(f"\n❌ No category links matched our filter!")
            
        # Try a simpler approach - just find any /menu/ links
        simple_categories = driver.execute_script("""
            const links = Array.from(document.querySelectorAll('a[href*="/menu/"]'));
            return links.map(link => ({
                text: link.textContent.trim(),
                href: link.href,
                className: link.className
            }));
        """)
        
        print(f"\n🔍 Simple /menu/ link detection found {len(simple_categories)} links:")
        for i, cat in enumerate(simple_categories[:10]):
            print(f"   {i+1}. '{cat['text']}' -> {cat['href']}")
            if cat['className']:
                print(f"       Class: {cat['className']}")
        
        driver.quit()
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_category_url_detection()