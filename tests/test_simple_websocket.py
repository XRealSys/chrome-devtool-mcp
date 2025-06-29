#!/usr/bin/env python3
"""
Simple test for WebSocket URL connection feature
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chrome_devtools_mcp import (
    launch_chrome, connect_websocket_url, list_available_targets,
    navigate_to, execute_javascript, get_page_info, close_chrome
)

async def main():
    """Simple test of WebSocket URL functionality"""
    try:
        print("=== Simple WebSocket URL Test ===\n")
        
        # 1. Launch Chrome
        print("1. Launching Chrome...")
        result = await launch_chrome(port=9222)
        if result['success']:
            print(f"   ✓ Chrome launched successfully")
            print(f"   WebSocket URL: {result['data']['ws_url']}")
        else:
            print(f"   ✗ Failed to launch Chrome: {result['error']}")
            return
        
        # 2. Navigate to a test page
        print("\n2. Navigating to test page...")
        nav_result = await navigate_to("https://example.com")
        if nav_result['success']:
            print("   ✓ Navigation successful")
        
        # 3. Get current page info
        print("\n3. Getting current page info...")
        info = await get_page_info()
        if info['success']:
            print(f"   ✓ Current page: {info['data']['title']}")
            print(f"   URL: {info['data']['url']}")
        
        # 4. List available targets
        print("\n4. Listing all available targets...")
        targets_result = await list_available_targets()
        if targets_result['success']:
            print(f"   ✓ Found {targets_result['data']['count']} targets")
            current_ws = targets_result['data']['current_ws_url']
            print(f"   Current WebSocket: {current_ws}")
            
            # Show first few targets
            for i, target in enumerate(targets_result['data']['targets'][:3]):
                print(f"\n   Target {i+1}:")
                print(f"     Title: {target['title'][:50]}...")
                print(f"     URL: {target['url']}")
                print(f"     WebSocket: {target['webSocketDebuggerUrl']}")
        
        # 5. Test WebSocket URL connection (reconnect to same page)
        print("\n5. Testing WebSocket URL connection...")
        ws_url = result['data']['ws_url']
        print(f"   Reconnecting to: {ws_url}")
        
        reconnect_result = await connect_websocket_url(ws_url)
        if reconnect_result['success']:
            print("   ✓ Successfully reconnected via WebSocket URL")
            print(f"   Page: {reconnect_result['data']['page_title']}")
        else:
            print(f"   ✗ Failed to reconnect: {reconnect_result['error']}")
        
        # 6. Execute JavaScript to verify connection
        print("\n6. Verifying connection with JavaScript...")
        js_result = await execute_javascript("""
            document.body.style.backgroundColor = 'lightblue';
            'Background changed to lightblue'
        """)
        if js_result['success']:
            print(f"   ✓ JavaScript executed: {js_result['data']['result']}")
        else:
            print(f"   ✗ JavaScript failed: {js_result['error']}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up...")
        await close_chrome()

if __name__ == "__main__":
    asyncio.run(main())