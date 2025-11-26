"""
Advanced CloudDestroyer Usage Examples

Demonstrates advanced features like batch processing, session management,
and custom configurations for different use cases.
"""

import sys
import os
import time

# Add the project root directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.cloud_destroyer import CloudDestroyer
from loguru import logger
import json

def batch_scraping_example():
    """Example of batch scraping multiple URLs"""
    
    print("Batch Scraping Example")
    print("=" * 30)
    
    urls = [
        "https://httpbin.org/ip",
        "https://httpbin.org/user-agent", 
        "https://httpbin.org/headers",
        "https://httpbin.org/cookies"
    ]
    
    with CloudDestroyer(headless=True, session_persistence=True) as scraper:
        
        print(f"Scraping {len(urls)} URLs in batch...")
        
        # Batch requests
        responses = scraper.batch_requests(urls)
        
        for i, (url, response) in enumerate(zip(urls, responses), 1):
            if response:
                print(f"\n{i}. {url}")
                print(f"   Status: {getattr(response, 'status_code', 'N/A')}")
                print(f"   Length: {len(getattr(response, 'text', ''))} chars")
            else:
                print(f"\n{i}. {url} - FAILED")

def session_management_example():
    """Example of session management and persistence"""
    
    print("\nSession Management Example")
    print("=" * 30)
    
    test_domain = "httpbin.org"
    test_url = f"https://{test_domain}/cookies"
    
    with CloudDestroyer(session_persistence=True) as scraper:
        
        print(f"Testing session persistence with {test_domain}")
        
        # First request - will create session
        print("\n1. First request (creating session)...")
        response1 = scraper.get(test_url)
        
        # Check session info
        session_info = scraper.get_session_info(test_domain)
        print(f"   Session exists: {session_info.get('domain_session', {}).get('exists', False)}")
        
        # Second request - should use existing session
        print("\n2. Second request (using existing session)...")
        response2 = scraper.get(test_url)
        
        # Show session stats
        session_info = scraper.get_session_info()
        if 'session_stats' in session_info:
            stats = session_info['session_stats']
            print(f"   Total sessions: {stats['total_sessions']}")
            print(f"   Success rate: {stats['success_rate']:.2%}")
        
        # Clear session
        print("\n3. Clearing session...")
        scraper.clear_session(test_domain)
        
        session_info = scraper.get_session_info(test_domain)
        print(f"   Session exists after clear: {session_info.get('domain_session', {}).get('exists', False)}")

def fingerprint_rotation_example():
    """Example of fingerprint rotation for stealth"""
    
    print("\nFingerprint Rotation Example")
    print("=" * 30)
    
    test_url = "https://httpbin.org/user-agent"
    
    with CloudDestroyer() as scraper:
        
        print("Making requests with different fingerprints...")
        
        for i in range(3):
            print(f"\nRequest {i+1}:")
            
            # Generate new fingerprint
            scraper.fingerprint_manager.rotate_fingerprint()
            
            response = scraper.get(test_url)
            
            if response:
                try:
                    # Parse JSON response to see user agent
                    content = json.loads(response.text)
                    user_agent = content.get('user-agent', 'Unknown')
                    print(f"   User-Agent: {user_agent[:80]}...")
                except:
                    print(f"   Response length: {len(response.text)} chars")
            
            # Small delay between requests
            time.sleep(2)

def performance_monitoring_example():
    """Example of monitoring bypass performance"""
    
    print("\nPerformance Monitoring Example")
    print("=" * 30)
    
    test_urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2", 
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/404"
    ]
    
    with CloudDestroyer() as scraper:
        
        print("Testing performance across multiple requests...")
        
        for url in test_urls:
            print(f"\nTesting: {url}")
            
            # Test bypass performance
            result = scraper.test_bypass(url)
            
            print(f"   Success: {result['success']}")
            print(f"   Duration: {result['duration']}s")
            print(f"   Status: {result.get('status_code', 'N/A')}")
        
        # Show overall statistics
        print("\nOverall Statistics:")
        print("-" * 20)
        
        stats = scraper.get_session_info()['orchestrator_stats']
        print(f"Total attempts: {stats['total_attempts']}")
        print(f"Success rate: {stats['success_rate']:.2%}")
        print(f"Average duration: {stats['average_duration']:.2f}s")
        
        # Show recent attempts
        if 'recent_attempts' in stats:
            print("\nRecent attempts:")
            for attempt in stats['recent_attempts'][-5:]:  # Last 5
                print(f"   {attempt['strategy']}: {attempt['success']} ({attempt['duration']}s)")

def custom_configuration_example():
    """Example of custom CloudDestroyer configurations"""
    
    print("\nCustom Configuration Example")
    print("=" * 30)
    
    # High-performance configuration
    print("1. High-performance configuration (fast, less stealth):")
    with CloudDestroyer(
        headless=True,
        session_persistence=True,
        max_retries=2,           # Fewer retries for speed
        timeout=30,              # Shorter timeout
        delay_range=(0.5, 1.5)   # Shorter delays
    ) as fast_scraper:
        
        result = fast_scraper.test_bypass("https://httpbin.org/ip")
        print(f"   Fast scraper duration: {result['duration']}s")
    
    # Stealth configuration  
    print("\n2. Stealth configuration (slower, more careful):")
    with CloudDestroyer(
        headless=True,
        session_persistence=True,
        max_retries=5,           # More retries for reliability
        timeout=120,             # Longer timeout
        delay_range=(3, 8)       # Longer delays between requests
    ) as stealth_scraper:
        
        result = stealth_scraper.test_bypass("https://httpbin.org/ip")
        print(f"   Stealth scraper duration: {result['duration']}s")
    
    print("\nConfiguration comparison complete!")

def main():
    """Run all advanced examples"""
    
    # Configure logging
    logger.add("advanced_examples.log", rotation="1 MB", level="INFO")
    
    print("CloudDestroyer Advanced Examples")
    print("=" * 40)
    
    try:
        batch_scraping_example()
        session_management_example()
        fingerprint_rotation_example()
        performance_monitoring_example()
        custom_configuration_example()
        
        print("\n" + "=" * 40)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"\nExample failed with error: {e}")
        logger.error(f"Advanced examples error: {e}")

if __name__ == "__main__":
    main()