#!/usr/bin/env python3
"""
Test opening Baidu.com with Chrome DevTools MCP
"""

import asyncio
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_open_baidu():
    """Test opening Baidu website"""
    # Import the tools from our server
    from src.chrome_devtools_mcp import launch_chrome, navigate_to, get_page_info, take_screenshot, close_chrome
    
    print("=== Testing Chrome DevTools MCP - Open Baidu ===\n")
    
    try:
        # Step 1: Launch Chrome
        print("1. Launching Chrome...")
        launch_result = await launch_chrome(headless=False, port=9222)
        print(f"Result: {json.dumps(launch_result, indent=2)}")
        
        if not launch_result["success"]:
            print("Failed to launch Chrome!")
            return
        
        print("\n✓ Chrome launched successfully\n")
        
        # Step 2: Navigate to Baidu
        print("2. Navigating to http://www.baidu.com...")
        nav_result = await navigate_to(url="http://www.baidu.com")
        print(f"Result: {json.dumps(nav_result, indent=2)}")
        
        if not nav_result["success"]:
            print("Failed to navigate to Baidu!")
            return
            
        print("\n✓ Successfully navigated to Baidu\n")
        
        # Wait a bit for page to fully load
        await asyncio.sleep(3)
        
        # Step 3: Get page information
        print("3. Getting page information...")
        info_result = await get_page_info()
        print(f"Result: {json.dumps(info_result, indent=2)}")
        
        if info_result["success"]:
            print(f"\nPage Title: {info_result['data'].get('title', 'N/A')}")
            print(f"Page URL: {info_result['data'].get('url', 'N/A')}")
            print("\n✓ Successfully retrieved page information\n")
        
        # Step 4: Take a screenshot
        print("4. Taking a screenshot...")
        screenshot_result = await take_screenshot(full_page=False)
        print(f"Result: {json.dumps(screenshot_result, indent=2)}")
        
        if screenshot_result["success"]:
            print(f"\n✓ Screenshot saved to: {screenshot_result['data']['filename']}\n")
        else:
            print(f"\n✗ Screenshot failed: {screenshot_result.get('error', 'Unknown error')}\n")
        
        # Wait for user to see the browser
        print("\n>>> Browser is open with Baidu loaded. Press Enter to close...")
        input()
        
        # Step 5: Close Chrome
        print("\n5. Closing Chrome...")
        close_result = await close_chrome()
        print(f"Result: {json.dumps(close_result, indent=2)}")
        
        print("\n=== Test completed successfully! ===")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        # Try to close Chrome anyway
        try:
            await close_chrome()
        except:
            pass

if __name__ == "__main__":
    # Check if server is running
    import httpx
    import sys
    
    async def check_server():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:12524/health", timeout=2.0)
                return response.status_code == 200
        except:
            return False
    
    if not asyncio.run(check_server()):
        print("ERROR: MCP server is not running!")
        print("Please start it with: ./start.sh")
        sys.exit(1)
    
    # Run the test
    asyncio.run(test_open_baidu())