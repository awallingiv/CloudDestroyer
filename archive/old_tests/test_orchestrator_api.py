#!/usr/bin/env python3
"""
Test the orchestrator API integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.cloud_destroyer import CloudDestroyer
from src.bypass.bypass_orchestrator import BypassOrchestrator, BypassStrategy
from src.bypass.session_manager import SessionManager
from src.bypass.detectors.challenge_detector import ChallengeDetector, ChallengeType

def test_orchestrator_directly():
    """Test the orchestrator bypass directly"""
    print("Testing BypassOrchestrator directly...")
    
    try:
        # Initialize orchestrator
        orchestrator = BypassOrchestrator(max_retries=3, strategy_timeout=60)
        
        # Test URL
        test_url = "https://bubbas33.com/menu"
        
        print(f"Testing bypass for: {test_url}")
        
        # Try bypass
        response, metadata = orchestrator.bypass_cloudflare(test_url)
        
        if response:
            print(f"Success! Status: {response.status_code}")
            print(f"Strategy used: {metadata.get('strategy', 'unknown')}")
            print(f"Challenge type: {metadata.get('challenge_type', 'none')}")
            print(f"Content length: {len(response.text) if hasattr(response, 'text') else 'N/A'}")
            
            # Check for menu content
            content = response.text if hasattr(response, 'text') else str(response)
            menu_indicators = ['appetizer', 'entree', 'burger', 'pizza', 'menu']
            found_indicators = [word for word in menu_indicators if word.lower() in content.lower()]
            print(f"Menu indicators found: {found_indicators}")
            
        else:
            print("Bypass failed - no response")
            
    except Exception as e:
        print(f"Error testing orchestrator: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_orchestrator_directly()