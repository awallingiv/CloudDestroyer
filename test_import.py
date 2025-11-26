#!/usr/bin/env python3
"""
Test CloudDestroyer import
"""

import sys
from pathlib import Path

print("Current directory:", Path.cwd())
print("Python path before:", sys.path[:3])

# Add the src directory to the path
src_path = Path(__file__).parent / 'src'
print("Adding to path:", src_path)
print("Src path exists:", src_path.exists())

sys.path.insert(0, str(src_path))
print("Python path after:", sys.path[:3])

try:
    from core.cloud_destroyer import CloudDestroyer
    print("✅ CloudDestroyer import successful!")
    
    # Try to create an instance
    destroyer = CloudDestroyer()
    print("✅ CloudDestroyer instance created successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")