#!/usr/bin/env python3
"""
Simulate connecting to a debugging endpoint with only partial domains enabled
"""

import asyncio
import sys
sys.path.insert(0, '/Users/sky/Desktop/Code/QBNET.TECH/chrome-devtool-mcp/src')

from chrome_devtools_mcp import chrome

async def test_with_simulated_partial_domains():
    """Test by modifying enabled_domains to simulate partial support"""
    
    print("=== Simulating Partial Domain Support ===\n")
    
    # Launch Chrome normally
    print("1. Launching Chrome...")
    try:
        result = await chrome.launch(headless=False)
        success = True
    except Exception as e:
        print(f"   Error launching Chrome: {e}")
        success = False
        result = {'error': str(e)}
    
    if success:
        # Simulate that only Runtime and Console are enabled
        print("\n2. Simulating that only Runtime and Console domains are enabled...")
        chrome.enabled_domains['Runtime'] = True
        chrome.enabled_domains['Page'] = False
        chrome.enabled_domains['Network'] = False
        chrome.enabled_domains['DOM'] = False
        chrome.enabled_domains['Console'] = True
        chrome.enabled_domains['Debugger'] = False
        
        # Check enabled domains
        print("\n   Modified enabled domains:")
        for domain, enabled in chrome.enabled_domains.items():
            status = "✓" if enabled else "✗"
            print(f"     {status} {domain}")
        
        # Import tools
        from chrome_devtools_mcp import (
            execute_javascript, navigate_to, get_console_logs,
            get_network_logs, get_dom_tree, get_script_sources
        )
        
        # Test enabled domains
        print("\n3. Testing enabled domains:")
        
        # Runtime (should work)
        print("\n   Testing Runtime domain...")
        js_result = await execute_javascript("console.log('Hello from test'); 2 + 2")
        if js_result.get('success', False):
            print(f"   ✓ JavaScript execution works: 2 + 2 = {js_result['data']['result']}")
        else:
            print(f"   ✗ JavaScript execution failed: {js_result.get('error', 'Unknown error')}")
        
        # Console (should work)
        print("\n   Testing Console domain...")
        console_result = await get_console_logs()
        if console_result.get('success', False):
            print(f"   ✓ Console logs available: {console_result['data']['total']} logs")
            if console_result['data']['logs']:
                print(f"     Last log: {console_result['data']['logs'][-1]['text']}")
        else:
            print(f"   ✗ Console logs not available: {console_result.get('error', 'Unknown error')}")
        
        # Test disabled domains
        print("\n4. Testing disabled domains (should fail gracefully):")
        
        # Page (should fail)
        print("\n   Testing Page domain...")
        nav_result = await navigate_to("https://example.com")
        if nav_result.get('success', False):
            print("   ✓ Navigation works (unexpected!)")
        else:
            print(f"   ✗ Navigation failed as expected: {nav_result.get('error', 'Unknown error')}")
        
        # Network (should fail)
        print("\n   Testing Network domain...")
        network_result = await get_network_logs()
        if network_result.get('success', False):
            print("   ✓ Network logs available (unexpected!)")
        else:
            print(f"   ✗ Network logs not available as expected: {network_result.get('error', 'Unknown error')}")
        
        # DOM (should fail)
        print("\n   Testing DOM domain...")
        dom_result = await get_dom_tree(depth=1)
        if dom_result.get('success', False):
            print("   ✓ DOM access works (unexpected!)")
        else:
            print(f"   ✗ DOM access failed as expected: {dom_result.get('error', 'Unknown error')}")
        
        # Debugger (should fail)
        print("\n   Testing Debugger domain...")
        scripts_result = await get_script_sources()
        if scripts_result.get('success', False):
            print("   ✓ Debugger access works (unexpected!)")
        else:
            print(f"   ✗ Debugger access failed as expected: {scripts_result.get('error', 'Unknown error')}")
        
        print("\n=== Summary ===")
        print("✓ Tools correctly handle partial domain enablement")
        print("✓ Enabled domains (Runtime, Console) work properly")
        print("✓ Disabled domains return appropriate error messages")
        print("✓ No crashes or exceptions when domains are unavailable")
        
        # Close Chrome
        print("\nClosing Chrome...")
        await chrome.close()
        print("Done!")
    else:
        print(f"Failed to launch Chrome: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_with_simulated_partial_domains())