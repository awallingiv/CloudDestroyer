"""
CloudDestroyer Example Usage

This example demonstrates how to use CloudDestroyer to bypass Cloudflare
protection and scrape protected websites.
"""

import sys
import os

# Add the project root directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.cloud_destroyer import CloudDestroyer
from loguru import logger

def main():
    """Main example function"""
    
    # Configure logging
    logger.add("cloudflare_bypass.log", rotation="1 MB")
    logger.info("Starting CloudDestroyer example")
    
    # Initialize CloudDestroyer
    with CloudDestroyer(
        headless=True,           # Run browsers in headless mode
        session_persistence=True, # Enable session persistence
        max_retries=3,           # Max retries per strategy
        timeout=60               # Request timeout
    ) as scraper:
        
        print("CloudDestroyer initialized successfully!")
        print("=" * 50)
        
        # Test URLs (replace with actual Cloudflare-protected sites)
        test_urls = [
            "https://httpbin.org/user-agent",  # Simple test URL
            "https://httpbin.org/headers",     # Headers test
            # Add your target URLs here
        ]
        
        for url in test_urls:
            print(f"\nTesting bypass for: {url}")
            print("-" * 30)
            
            try:
                # Test the bypass capabilities
                test_result = scraper.test_bypass(url)
                
                print(f"Success: {test_result['success']}")
                print(f"Duration: {test_result['duration']}s")
                print(f"Status Code: {test_result['status_code']}")
                print(f"Content Length: {test_result['content_length']} chars")
                
                if test_result['success']:
                    # Get the actual content
                    response = scraper.get(url)
                    
                    print(f"\nFirst 500 chars of content:")
                    print("-" * 30)
                    content = response.text if hasattr(response, 'text') else str(response)
                    print(content[:500] + "..." if len(content) > 500 else content)
                    
                else:
                    print("Bypass failed!")
                    if 'error' in test_result:
                        print(f"Error: {test_result['error']}")
                        
            except Exception as e:
                print(f"Error testing {url}: {e}")
        
        # Show session information
        print("\n" + "=" * 50)
        print("Session Information:")
        print("-" * 20)
        session_info = scraper.get_session_info()
        
        if 'session_stats' in session_info:
            stats = session_info['session_stats']
            print(f"Total Sessions: {stats['total_sessions']}")
            print(f"Success Rate: {stats['success_rate']:.2%}")
            print(f"Sessions with Clearance: {stats['sessions_with_clearance']}")
        
        if 'orchestrator_stats' in session_info:
            orch_stats = session_info['orchestrator_stats']
            print(f"Total Attempts: {orch_stats['total_attempts']}")
            print(f"Success Rate: {orch_stats['success_rate']:.2%}")
            print(f"Average Duration: {orch_stats['average_duration']:.2f}s")
            
            if 'strategy_success_rates' in orch_stats:
                print("\nStrategy Success Rates:")
                for strategy, rate in orch_stats['strategy_success_rates'].items():
                    print(f"  {strategy}: {rate:.2%}")

if __name__ == "__main__":
    main()