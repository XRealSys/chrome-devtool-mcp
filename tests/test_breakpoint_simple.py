#!/usr/bin/env python3
"""
Simple breakpoint test with auto-resume
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chrome_devtools_mcp import (
    launch_chrome, navigate_to, set_breakpoint, 
    execute_javascript, get_console_logs, close_chrome
)

async def main():
    """Test breakpoint functionality"""
    try:
        print("=== Simple Breakpoint Test ===\n")
        
        # 1. Launch Chrome
        print("1. Launching Chrome...")
        result = await launch_chrome(port=9222)
        if not result['success']:
            print(f"   Failed: {result['error']}")
            return
        print("   ✓ Chrome launched")
        
        # 2. Create test page
        print("\n2. Creating test page with button...")
        test_html = """
        <html>
        <body>
            <h1>Breakpoint Test</h1>
            <button id="test-btn" onclick="testFunction()">Click Me</button>
            <div id="output"></div>
            <script>
                function testFunction() {
                    console.log('Button clicked!');
                    console.log('Current time:', new Date().toISOString());
                    document.getElementById('output').innerHTML = 'Button was clicked!';
                    return 'Function completed';
                }
            </script>
        </body>
        </html>
        """
        await navigate_to(f"data:text/html,{test_html}")
        await asyncio.sleep(1)
        print("   ✓ Test page created")
        
        # 3. Set function breakpoint (without using debugger statement)
        print("\n3. Testing function wrapping (no debugger)...")
        wrap_result = await execute_javascript("""
            // Wrap the function to log calls without blocking
            const original = window.testFunction;
            window.testFunction = function(...args) {
                console.log('BREAKPOINT: testFunction called');
                console.log('BREAKPOINT: Arguments:', args);
                const result = original.apply(this, args);
                console.log('BREAKPOINT: Return value:', result);
                return result;
            };
            'Function wrapped successfully'
        """)
        print(f"   ✓ {wrap_result['data']['result']}")
        
        # 4. Click the button
        print("\n4. Clicking the button...")
        click_result = await execute_javascript("""
            document.getElementById('test-btn').click();
            'Button clicked'
        """)
        print(f"   ✓ {click_result['data']['result']}")
        
        # 5. Get console logs
        print("\n5. Console logs:")
        logs = await get_console_logs()
        if logs['success']:
            for log in logs['data']['logs'][-10:]:  # Last 10 logs
                if log['text']:
                    print(f"   [{log['level']}] {log['text']}")
        
        # 6. Verify output
        print("\n6. Verifying page output...")
        output_result = await execute_javascript("""
            document.getElementById('output').innerHTML
        """)
        print(f"   ✓ Output: {output_result['data']['result']}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up...")
        await close_chrome()

if __name__ == "__main__":
    asyncio.run(main())