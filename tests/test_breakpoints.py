#!/usr/bin/env python3
"""
Test script for new breakpoint and remote connection features
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chrome_devtools_mcp import (
    launch_chrome, connect_remote_chrome, navigate_to, 
    query_elements, set_breakpoint, get_console_logs,
    execute_javascript, list_breakpoints, remove_breakpoint,
    get_paused_info, resume_execution, close_chrome
)

async def test_remote_connection():
    """Test connecting to a remote Chrome instance"""
    print("\n=== Testing Remote Connection ===")
    
    # First launch a Chrome instance
    print("1. Launching Chrome instance...")
    result = await launch_chrome(port=9222)
    print(f"   Result: {result}")
    
    # Navigate to a test page
    print("2. Navigating to test page...")
    await navigate_to("https://example.com")
    
    # Now test connecting to it remotely
    print("3. Testing remote connection...")
    result = await connect_remote_chrome(host="localhost", port=9222)
    print(f"   Result: {result}")
    
    # Verify we can still control it
    print("4. Verifying control...")
    page_info = await execute_javascript("{ title: document.title, url: window.location.href }")
    print(f"   Page info: {page_info}")
    
    return True

async def test_breakpoints():
    """Test breakpoint functionality"""
    print("\n=== Testing Breakpoints ===")
    
    # Create a test page with buttons
    print("1. Creating test page...")
    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Breakpoint Test</title></head>
    <body>
        <button id="test-btn" onclick="handleClick()">Test Button</button>
        <button id="login-btn" onclick="login()">Login</button>
        <script>
            function handleClick() {
                console.log('Button clicked!');
                console.log('Performing action...');
                return 'Click handled';
            }
            
            function login() {
                console.log('Login button clicked');
                const username = 'testuser';
                console.log('Logging in as:', username);
                // Simulate API call
                fetch('/api/login', {
                    method: 'POST',
                    body: JSON.stringify({ username })
                });
                return 'Login initiated';
            }
        </script>
    </body>
    </html>
    """
    
    await navigate_to(f"data:text/html,{test_html}")
    await asyncio.sleep(1)
    
    # Test DOM breakpoint
    print("2. Setting DOM breakpoint on #test-btn...")
    result = await set_breakpoint('dom', '#test-btn')
    print(f"   Result: {result}")
    
    # Test function breakpoint
    print("3. Setting function breakpoint on handleClick...")
    result = await set_breakpoint('function', 'handleClick')
    print(f"   Result: {result}")
    
    # Test XHR breakpoint
    print("4. Setting XHR breakpoint on /api/login...")
    result = await set_breakpoint('xhr', '/api/login')
    print(f"   Result: {result}")
    
    # List breakpoints
    print("5. Listing all breakpoints...")
    result = await list_breakpoints()
    print(f"   Breakpoints: {result}")
    
    # Test clicking button (will trigger breakpoint)
    print("6. Simulating button click...")
    await execute_javascript("document.getElementById('test-btn').click()")
    
    # Get console logs
    print("7. Getting console logs...")
    logs = await get_console_logs()
    print(f"   Console logs: {logs}")
    
    return True

async def test_login_button_scenario():
    """Test the login button debugging scenario mentioned in requirements"""
    print("\n=== Testing Login Button Scenario ===")
    
    # Create a more realistic login page
    login_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Login Page</title></head>
    <body>
        <div id="login-form">
            <input type="text" id="username" placeholder="Username">
            <input type="password" id="password" placeholder="Password">
            <button id="login-button" onclick="performLogin()">Login</button>
        </div>
        <div id="output"></div>
        <script>
            function performLogin() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                console.log('Login attempt for user:', username);
                console.log('Validating credentials...');
                
                // Simulate validation
                if (username && password) {
                    console.log('Credentials valid, logging in...');
                    document.getElementById('output').innerText = 'Login successful!';
                } else {
                    console.error('Invalid credentials');
                    document.getElementById('output').innerText = 'Login failed!';
                }
                
                return { username, success: !!username && !!password };
            }
        </script>
    </body>
    </html>
    """
    
    print("1. Loading login page...")
    await navigate_to(f"data:text/html,{login_html}")
    await asyncio.sleep(1)
    
    print("2. Finding login button...")
    elements = await query_elements('#login-button')
    print(f"   Found elements: {elements}")
    
    print("3. Setting breakpoint on login button click...")
    result = await set_breakpoint('dom', '#login-button')
    print(f"   Breakpoint set: {result}")
    
    print("4. Filling form and clicking login...")
    await execute_javascript("""
        document.getElementById('username').value = 'testuser';
        document.getElementById('password').value = 'testpass';
        document.getElementById('login-button').click();
    """)
    
    print("5. Getting console output...")
    logs = await get_console_logs()
    print("   Console logs after login:")
    for log in logs.get('data', {}).get('logs', [])[-5:]:  # Last 5 logs
        print(f"     [{log.get('level')}] {log.get('text')}")
    
    return True

async def main():
    """Run all tests"""
    try:
        print("Chrome DevTools MCP - New Features Test Suite")
        print("=" * 50)
        
        # Test 1: Remote connection
        success = await test_remote_connection()
        print(f"\nRemote connection test: {'PASSED' if success else 'FAILED'}")
        
        # Test 2: Breakpoints
        success = await test_breakpoints()
        print(f"\nBreakpoint test: {'PASSED' if success else 'FAILED'}")
        
        # Test 3: Login button scenario
        success = await test_login_button_scenario()
        print(f"\nLogin button scenario test: {'PASSED' if success else 'FAILED'}")
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        print("\nCleaning up...")
        await close_chrome()

if __name__ == "__main__":
    asyncio.run(main())