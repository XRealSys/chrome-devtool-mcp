#!/usr/bin/env python3
"""
Simple test to verify partial domain enablement works
"""

import asyncio
import sys
sys.path.insert(0, '/Users/sky/Desktop/Code/QBNET.TECH/chrome-devtool-mcp/src')

from chrome_devtools_mcp import chrome

async def test_partial_domains():
    """Test that MCP works with partial domain enablement"""
    
    print("=== Testing Chrome DevTools MCP with Partial Domain Support ===\n")
    
    # Launch Chrome
    print("1. Launching Chrome...")
    result = await chrome.launch(headless=False)
    print(f"   Launch result: {result.get('success', False)}")
    
    if result.get('success', False):
        # Check enabled domains
        print("\n2. Checking enabled domains...")
        enabled_domains = chrome.get_enabled_domains()
        print("   Enabled domains:")
        for domain, enabled in enabled_domains.items():
            status = "✓" if enabled else "✗"
            print(f"     {status} {domain}")
        
        # Count enabled domains
        enabled_count = sum(1 for enabled in enabled_domains.values() if enabled)
        print(f"\n   Total enabled: {enabled_count}/{len(enabled_domains)}")
        
        # Test Runtime domain (usually enabled)
        print("\n3. Testing Runtime domain...")
        js_result = await chrome.execute_javascript("1 + 1")
        if js_result['success']:
            print(f"   ✓ JavaScript execution works: 1 + 1 = {js_result['data']['result']}")
        else:
            print(f"   ✗ JavaScript execution failed: {js_result['error']}")
        
        # Test Page domain
        print("\n4. Testing Page domain...")
        nav_result = await chrome.navigate_to("https://example.com")
        if nav_result['success']:
            print("   ✓ Navigation works")
        else:
            print(f"   ✗ Navigation failed: {nav_result['error']}")
        
        # Test Console domain
        print("\n5. Testing Console domain...")
        console_result = await chrome.get_console_logs()
        if console_result['success']:
            print(f"   ✓ Console logs available: {console_result['data']['total']} logs")
        else:
            print(f"   ✗ Console logs not available: {console_result['error']}")
        
        # Test Network domain
        print("\n6. Testing Network domain...")
        network_result = await chrome.get_network_logs()
        if network_result['success']:
            print(f"   ✓ Network logs available: {network_result['data']['total']} logs")
        else:
            print(f"   ✗ Network logs not available: {network_result['error']}")
        
        # Test DOM domain
        print("\n7. Testing DOM domain...")
        dom_result = await chrome.get_dom_tree(depth=1)
        if dom_result['success']:
            print("   ✓ DOM access works")
        else:
            print(f"   ✗ DOM access failed: {dom_result['error']}")
        
        # Test Debugger domain
        print("\n8. Testing Debugger domain...")
        scripts_result = await chrome.get_script_sources()
        if scripts_result['success']:
            print(f"   ✓ Debugger access works: {scripts_result['data']['count']} scripts")
        else:
            print(f"   ✗ Debugger access failed: {scripts_result['error']}")
        
        # Summary
        print("\n=== Summary ===")
        print("The Chrome DevTools MCP now supports partial domain enablement.")
        print("Tools will gracefully handle cases where specific domains are not available.")
        
        # Close Chrome
        print("\nClosing Chrome...")
        await chrome.close()
        print("Done!")
    else:
        print(f"Failed to launch Chrome: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_partial_domains())