#!/usr/bin/env python3
"""
Test script for WebSocket URL connection feature
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chrome_devtools_mcp import (
    launch_chrome, connect_websocket_url, list_available_targets,
    navigate_to, execute_javascript, get_page_info, close_chrome
)

async def test_websocket_url_connection():
    """Test connecting via WebSocket URL and switching between tabs"""
    print("\n=== Testing WebSocket URL Connection ===")
    
    try:
        # Step 1: Launch Chrome
        print("1. Launching Chrome...")
        launch_result = await launch_chrome(port=9222)
        print(f"   Launch result: {launch_result}")
        
        # Step 2: Open multiple tabs
        print("\n2. Opening multiple tabs...")
        
        # First tab - already open, navigate to example.com
        await navigate_to("https://example.com")
        await asyncio.sleep(2)
        
        # Open second tab
        await execute_javascript("window.open('https://github.com', '_blank')")
        await asyncio.sleep(2)
        
        # Open third tab
        await execute_javascript("window.open('https://google.com', '_blank')")
        await asyncio.sleep(2)
        
        # Step 3: List all available targets
        print("\n3. Listing all available targets...")
        targets_result = await list_available_targets()
        
        if targets_result['success']:
            targets = targets_result['data']['targets']
            current_ws = targets_result['data']['current_ws_url']
            
            print(f"   Found {len(targets)} targets:")
            for i, target in enumerate(targets):
                print(f"   [{i}] {target['title'][:50]}...")
                print(f"       URL: {target['url']}")
                print(f"       Type: {target['type']}")
                print(f"       WebSocket: {target['webSocketDebuggerUrl']}")
                if target['webSocketDebuggerUrl'] == current_ws:
                    print("       ^ Currently connected")
                print()
        
        # Step 4: Switch between tabs using WebSocket URLs
        print("\n4. Testing tab switching...")
        
        # Find GitHub tab
        github_ws_url = None
        google_ws_url = None
        
        for target in targets:
            if 'github.com' in target['url']:
                github_ws_url = target['webSocketDebuggerUrl']
            elif 'google.com' in target['url']:
                google_ws_url = target['webSocketDebuggerUrl']
        
        if github_ws_url:
            print(f"   Switching to GitHub tab...")
            switch_result = await connect_websocket_url(github_ws_url)
            print(f"   Switch result: {switch_result}")
            
            # Verify we're on GitHub
            page_info = await get_page_info()
            print(f"   Current page: {page_info['data']['title']}")
            
            # Execute some JS on GitHub page
            js_result = await execute_javascript("""
                document.querySelector('h1')?.textContent || 'No h1 found'
            """)
            print(f"   Page h1: {js_result}")
        
        if google_ws_url:
            print(f"\n   Switching to Google tab...")
            switch_result = await connect_websocket_url(google_ws_url)
            print(f"   Switch result: {switch_result}")
            
            # Verify we're on Google
            page_info = await get_page_info()
            print(f"   Current page: {page_info['data']['title']}")
            
            # Execute some JS on Google page
            js_result = await execute_javascript("""
                document.querySelector('input[name="q"]')?.placeholder || 'Search box not found'
            """)
            print(f"   Search box placeholder: {js_result}")
        
        # Step 5: Test connecting with non-existent WebSocket URL
        print("\n5. Testing error handling with invalid WebSocket URL...")
        invalid_result = await connect_websocket_url("ws://localhost:9222/devtools/page/invalid-id")
        print(f"   Result: {invalid_result}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_remote_websocket_scenario():
    """Test scenario where user provides WebSocket URL from external source"""
    print("\n=== Testing Remote WebSocket URL Scenario ===")
    
    try:
        # This simulates a scenario where user gets WebSocket URL from another tool
        # or from Chrome DevTools directly
        
        print("1. User provides WebSocket URL from external source...")
        print("   (In real scenario, this would come from user input)")
        
        # First, let's get the actual WebSocket URL from a running Chrome
        targets_result = await list_available_targets()
        if not targets_result['success'] or not targets_result['data']['targets']:
            print("   No Chrome instance found. Please ensure Chrome is running with --remote-debugging-port=9222")
            return False
        
        # Simulate user providing the first target's WebSocket URL
        user_provided_ws_url = targets_result['data']['targets'][0]['webSocketDebuggerUrl']
        print(f"   User provides: {user_provided_ws_url}")
        
        print("\n2. Connecting using provided WebSocket URL...")
        connect_result = await connect_websocket_url(user_provided_ws_url)
        print(f"   Connection result: {connect_result}")
        
        if connect_result['success']:
            print("\n3. Verifying connection...")
            page_info = await get_page_info()
            print(f"   Connected to: {page_info['data']['title']}")
            print(f"   URL: {page_info['data']['url']}")
            
            print("\n4. Performing operations on connected page...")
            # Inject a message into the page
            await execute_javascript("""
                console.log('Connected via WebSocket URL!');
                document.body.style.border = '5px solid red';
            """)
            print("   Injected visual indicator (red border)")
            
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all WebSocket connection tests"""
    print("Chrome DevTools MCP - WebSocket URL Connection Tests")
    print("=" * 60)
    
    try:
        # Test 1: Basic WebSocket URL connection and tab switching
        result1 = await test_websocket_url_connection()
        print(f"\nWebSocket URL connection test: {'PASSED' if result1 else 'FAILED'}")
        
        # Test 2: Remote WebSocket URL scenario
        result2 = await test_remote_websocket_scenario()
        print(f"\nRemote WebSocket scenario test: {'PASSED' if result2 else 'FAILED'}")
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        
    finally:
        # Clean up
        print("\nCleaning up...")
        await close_chrome()

if __name__ == "__main__":
    asyncio.run(main())