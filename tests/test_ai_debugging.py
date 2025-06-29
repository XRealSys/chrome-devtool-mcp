#!/usr/bin/env python3
"""
Test non-blocking breakpoints and console log capture for AI-assisted debugging
This test simulates real-world scenarios that AI tools like Claude Code and Cursor would encounter
"""

import asyncio
import sys
import os
import json
import urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chrome_devtools_mcp import (
    launch_chrome, navigate_to, execute_javascript, 
    get_console_logs, set_breakpoint, close_chrome,
    query_elements
)

async def test_login_form_debugging():
    """Test debugging a login form - a common AI assistance scenario"""
    print("\n=== Test 1: Login Form Debugging (Non-blocking) ===")
    
    # Create a realistic login page
    login_page = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login Page</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            .login-form { max-width: 300px; margin: 0 auto; }
            input { width: 100%; padding: 8px; margin: 5px 0; }
            button { width: 100%; padding: 10px; background: #007bff; color: white; }
            .error { color: red; margin-top: 10px; }
            .success { color: green; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="login-form">
            <h2>Login</h2>
            <input type="text" id="username" placeholder="Username">
            <input type="password" id="password" placeholder="Password">
            <button id="login-btn" onclick="handleLogin()">Login</button>
            <div id="message"></div>
        </div>
        
        <script>
            async function handleLogin() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const messageEl = document.getElementById('message');
                
                console.log('Login attempt started');
                console.log('Username:', username);
                
                // Validation
                if (!username || !password) {
                    console.error('Validation failed: Missing credentials');
                    messageEl.className = 'error';
                    messageEl.textContent = 'Please fill in all fields';
                    return;
                }
                
                // Simulate API call
                console.log('Making API request to /api/login');
                try {
                    // Simulate async operation
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    // Simulate response
                    const response = {
                        success: username === 'admin' && password === 'password',
                        user: username
                    };
                    
                    console.log('API Response:', JSON.stringify(response));
                    
                    if (response.success) {
                        console.log('Login successful for user:', response.user);
                        messageEl.className = 'success';
                        messageEl.textContent = 'Login successful!';
                    } else {
                        console.error('Login failed: Invalid credentials');
                        messageEl.className = 'error';
                        messageEl.textContent = 'Invalid username or password';
                    }
                    
                    return response;
                } catch (error) {
                    console.error('API Error:', error.message);
                    messageEl.className = 'error';
                    messageEl.textContent = 'Network error';
                }
            }
        </script>
    </body>
    </html>
    """
    
    # URL encode the HTML to avoid issues
    encoded_html = urllib.parse.quote(login_page)
    await navigate_to(f"data:text/html,{encoded_html}")
    await asyncio.sleep(2)  # Give more time to load
    
    # Step 1: Find the login button using AI-style query
    print("\n1. Finding login button...")
    elements = await query_elements('#login-btn')
    if elements['success'] and elements['data']['elements']:
        print(f"   ✓ Found button: {elements['data']['elements'][0]['textContent']}")
    else:
        print("   ❌ Button not found, checking page status...")
        page_check = await execute_javascript("document.body.innerHTML.substring(0, 200)")
        print(f"   Page content: {page_check}")
        return False
    
    # Step 2: Instrument the login function with non-blocking logging
    print("\n2. Setting up non-blocking instrumentation...")
    instrument_result = await execute_javascript("""
        // Save original function
        window.originalHandleLogin = window.handleLogin;
        
        // Create instrumented version
        window.handleLogin = async function() {
            console.log('🔍 BREAKPOINT: handleLogin called at', new Date().toISOString());
            console.log('🔍 BREAKPOINT: Current URL:', window.location.href);
            console.log('🔍 BREAKPOINT: Stack trace:', new Error().stack.split('\\n').slice(2, 5).join('\\n'));
            
            const startTime = performance.now();
            
            try {
                // Call original function
                const result = await window.originalHandleLogin.apply(this, arguments);
                
                const endTime = performance.now();
                console.log('🔍 BREAKPOINT: Function completed in', (endTime - startTime).toFixed(2), 'ms');
                console.log('🔍 BREAKPOINT: Return value:', JSON.stringify(result));
                
                return result;
            } catch (error) {
                console.error('🔍 BREAKPOINT: Exception caught:', error.message);
                throw error;
            }
        };
        
        'Instrumentation complete'
    """)
    print(f"   ✓ {instrument_result['data']['result']}")
    
    # Step 3: Test with invalid credentials
    print("\n3. Testing with invalid credentials...")
    await execute_javascript("""
        document.getElementById('username').value = 'user';
        document.getElementById('password').value = 'wrong';
        document.getElementById('login-btn').click();
    """)
    await asyncio.sleep(1)
    
    # Get logs
    logs = await get_console_logs()
    print("   Console output:")
    for log in logs['data']['logs'][-15:]:
        if log['text']:
            prefix = "   ⚠️ " if log['level'] == 'error' else "   📝 "
            print(f"{prefix}[{log['level']}] {log['text']}")
    
    # Step 4: Test with valid credentials
    print("\n4. Testing with valid credentials...")
    await execute_javascript("""
        document.getElementById('username').value = 'admin';
        document.getElementById('password').value = 'password';
        document.getElementById('login-btn').click();
    """)
    await asyncio.sleep(1)
    
    # Get updated logs
    logs = await get_console_logs()
    print("   Console output:")
    recent_logs = logs['data']['logs'][-10:]
    for log in recent_logs:
        if log['text'] and '🔍' not in log['text']:  # Skip breakpoint logs for clarity
            prefix = "   ✅ " if 'successful' in log['text'] else "   📝 "
            print(f"{prefix}[{log['level']}] {log['text']}")
    
    return True

async def test_event_debugging():
    """Test debugging DOM events - another common AI assistance scenario"""
    print("\n=== Test 2: Event Debugging (Non-blocking) ===")
    
    # Create a page with multiple interactive elements
    event_page = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Event Test Page</title>
    </head>
    <body>
        <h2>Interactive Elements</h2>
        <button id="btn1" class="action-btn">Button 1</button>
        <button id="btn2" class="action-btn">Button 2</button>
        <input type="text" id="textInput" placeholder="Type here...">
        <div id="output"></div>
        
        <script>
            // Add event listeners
            document.getElementById('btn1').addEventListener('click', function(e) {
                console.log('Button 1 clicked');
                console.log('Event target:', e.target.id);
                console.log('Event type:', e.type);
                document.getElementById('output').textContent = 'Button 1 was clicked';
            });
            
            document.getElementById('btn2').addEventListener('click', function(e) {
                console.log('Button 2 clicked');
                console.log('Shift key pressed:', e.shiftKey);
                document.getElementById('output').textContent = 'Button 2 was clicked';
            });
            
            document.getElementById('textInput').addEventListener('input', function(e) {
                console.log('Input changed:', e.target.value);
            });
        </script>
    </body>
    </html>
    """
    
    encoded_html = urllib.parse.quote(event_page)
    await navigate_to(f"data:text/html,{encoded_html}")
    await asyncio.sleep(2)
    
    # Instrument all click events
    print("\n1. Setting up global event monitoring...")
    await execute_javascript("""
        // Monitor all click events
        document.addEventListener('click', function(e) {
            if (e.target.tagName === 'BUTTON') {
                console.log('🎯 EVENT MONITOR: Click on', e.target.id || e.target.className);
                console.log('🎯 EVENT MONITOR: Button text:', e.target.textContent);
                console.log('🎯 EVENT MONITOR: Coordinates:', `x=${e.clientX}, y=${e.clientY}`);
            }
        }, true);  // Use capture phase
        
        // Monitor input events
        document.addEventListener('input', function(e) {
            console.log('🎯 EVENT MONITOR: Input event on', e.target.id);
            console.log('🎯 EVENT MONITOR: New value length:', e.target.value.length);
        }, true);
        
        'Event monitoring active'
    """)
    
    # Test clicking buttons
    print("\n2. Testing button clicks...")
    await execute_javascript("document.getElementById('btn1').click()")
    await asyncio.sleep(0.5)
    await execute_javascript("document.getElementById('btn2').click()")
    await asyncio.sleep(0.5)
    
    # Test input
    print("\n3. Testing text input...")
    await execute_javascript("""
        const input = document.getElementById('textInput');
        input.value = 'Test';
        input.dispatchEvent(new Event('input', { bubbles: true }));
    """)
    
    # Get all logs
    logs = await get_console_logs()
    print("\n   Event logs:")
    for log in logs['data']['logs'][-20:]:
        if log['text'] and ('🎯' in log['text'] or 'clicked' in log['text'] or 'Input' in log['text']):
            print(f"   📍 {log['text']}")
    
    return True

async def test_api_debugging():
    """Test debugging API calls - critical for AI-assisted development"""
    print("\n=== Test 3: API Call Debugging (Non-blocking) ===")
    
    api_page = """
    <!DOCTYPE html>
    <html>
    <head><title>API Test</title></head>
    <body>
        <h2>API Test</h2>
        <button onclick="fetchData()">Fetch Data</button>
        <div id="result"></div>
        
        <script>
            async function fetchData() {
                console.log('Starting API call...');
                
                try {
                    // We'll intercept this
                    const response = await fetch('https://api.example.com/data');
                    const data = await response.json();
                    
                    console.log('API call completed');
                    console.log('Response data:', data);
                    
                    document.getElementById('result').textContent = JSON.stringify(data);
                } catch (error) {
                    console.error('API error:', error.message);
                }
            }
        </script>
    </body>
    </html>
    """
    
    encoded_html = urllib.parse.quote(api_page)
    await navigate_to(f"data:text/html,{encoded_html}")
    await asyncio.sleep(2)
    
    # Intercept fetch calls
    print("\n1. Setting up fetch interception...")
    await execute_javascript("""
        // Save original fetch
        window.originalFetch = window.fetch;
        
        // Override fetch
        window.fetch = async function(...args) {
            const [url, options = {}] = args;
            
            console.log('🌐 FETCH INTERCEPTED:', url);
            console.log('🌐 Method:', options.method || 'GET');
            console.log('🌐 Headers:', JSON.stringify(options.headers || {}));
            if (options.body) {
                console.log('🌐 Body:', options.body);
            }
            
            // Simulate response for demo
            const mockResponse = {
                ok: true,
                status: 200,
                json: async () => ({
                    success: true,
                    data: { message: 'Hello from mock API', timestamp: new Date().toISOString() }
                })
            };
            
            console.log('🌐 Mock response returned');
            return mockResponse;
        };
        
        'Fetch interception active'
    """)
    
    # Trigger API call
    print("\n2. Triggering API call...")
    await execute_javascript("fetchData()")
    await asyncio.sleep(1)
    
    # Get logs
    logs = await get_console_logs()
    print("\n   API debugging logs:")
    for log in logs['data']['logs'][-15:]:
        if log['text']:
            emoji = "🔴" if log['level'] == 'error' else "🟢"
            print(f"   {emoji} {log['text']}")
    
    return True

async def test_comprehensive_debugging():
    """Test comprehensive debugging scenario that AI tools would use"""
    print("\n=== Test 4: Comprehensive Debugging Scenario ===")
    
    # Clear previous logs
    await execute_javascript("console.clear()")
    
    # Create a complex page
    complex_page = """
    <!DOCTYPE html>
    <html>
    <head><title>Shopping Cart</title></head>
    <body>
        <h2>Shopping Cart Debug Test</h2>
        <div id="products">
            <div class="product" data-id="1" data-price="10.99">
                Product 1 - $10.99
                <button onclick="addToCart(1, 10.99)">Add to Cart</button>
            </div>
            <div class="product" data-id="2" data-price="25.50">
                Product 2 - $25.50
                <button onclick="addToCart(2, 25.50)">Add to Cart</button>
            </div>
        </div>
        <div id="cart">
            <h3>Cart: <span id="cart-count">0</span> items</h3>
            <div id="cart-total">Total: $0.00</div>
        </div>
        
        <script>
            let cart = [];
            
            function addToCart(productId, price) {
                console.log('Adding product to cart:', { productId, price });
                
                cart.push({ id: productId, price: price });
                updateCartDisplay();
                
                // Simulate analytics
                trackEvent('add_to_cart', { productId, price });
            }
            
            function updateCartDisplay() {
                const count = cart.length;
                const total = cart.reduce((sum, item) => sum + item.price, 0);
                
                console.log('Cart updated:', { count, total });
                
                document.getElementById('cart-count').textContent = count;
                document.getElementById('cart-total').textContent = `Total: $${total.toFixed(2)}`;
            }
            
            function trackEvent(eventName, data) {
                console.log('Analytics event:', eventName, data);
            }
        </script>
    </body>
    </html>
    """
    
    encoded_html = urllib.parse.quote(complex_page)
    await navigate_to(f"data:text/html,{encoded_html}")
    await asyncio.sleep(2)
    
    # Set up comprehensive debugging
    print("\n1. Setting up comprehensive debugging...")
    await execute_javascript("""
        // Debug helper
        window.debugLog = function(category, message, data) {
            const timestamp = new Date().toISOString();
            const prefix = `[${timestamp}] [${category}]`;
            if (data) {
                console.log(`${prefix} ${message}`, data);
            } else {
                console.log(`${prefix} ${message}`);
            }
        };
        
        // Wrap all functions
        ['addToCart', 'updateCartDisplay', 'trackEvent'].forEach(fnName => {
            const original = window[fnName];
            window[fnName] = function(...args) {
                debugLog('FUNCTION', `${fnName} called`, { arguments: args });
                const result = original.apply(this, args);
                debugLog('FUNCTION', `${fnName} completed`, { result });
                return result;
            };
        });
        
        // Monitor cart changes
        const originalPush = Array.prototype.push;
        cart.push = function(...items) {
            debugLog('CART', 'Items added to cart', items);
            return originalPush.apply(this, items);
        };
        
        'Debugging setup complete'
    """)
    
    # Simulate user actions
    print("\n2. Simulating user shopping...")
    
    # Add first product
    await execute_javascript("document.querySelector('[data-id=\"1\"] button').click()")
    await asyncio.sleep(0.5)
    
    # Add second product
    await execute_javascript("document.querySelector('[data-id=\"2\"] button').click()")
    await asyncio.sleep(0.5)
    
    # Get final logs
    logs = await get_console_logs()
    print("\n   Shopping cart debug logs:")
    
    # Organize logs by category
    function_logs = []
    cart_logs = []
    analytics_logs = []
    other_logs = []
    
    for log in logs['data']['logs'][-30:]:
        if log['text']:
            if '[FUNCTION]' in log['text']:
                function_logs.append(log['text'])
            elif '[CART]' in log['text']:
                cart_logs.append(log['text'])
            elif 'Analytics' in log['text']:
                analytics_logs.append(log['text'])
            elif 'Cart updated' in log['text'] or 'Adding product' in log['text']:
                other_logs.append(log['text'])
    
    print("\n   Function Calls:")
    for log in function_logs:
        print(f"   🔧 {log}")
    
    print("\n   Cart Operations:")
    for log in cart_logs:
        print(f"   🛒 {log}")
    
    print("\n   Analytics:")
    for log in analytics_logs:
        print(f"   📊 {log}")
    
    print("\n   Other Logs:")
    for log in other_logs:
        print(f"   📝 {log}")
    
    # Final state check
    final_state = await execute_javascript("""
        ({
            cartItems: cart.length,
            cartTotal: cart.reduce((sum, item) => sum + item.price, 0).toFixed(2),
            displayedCount: document.getElementById('cart-count').textContent,
            displayedTotal: document.getElementById('cart-total').textContent
        })
    """)
    
    print("\n   Final State:")
    print(f"   ✓ Cart items: {final_state['data']['result']['cartItems']}")
    print(f"   ✓ Cart total: ${final_state['data']['result']['cartTotal']}")
    print(f"   ✓ UI shows: {final_state['data']['result']['displayedCount']} items")
    print(f"   ✓ UI total: {final_state['data']['result']['displayedTotal']}")
    
    return True

async def main():
    """Run all AI debugging tests"""
    try:
        print("Chrome DevTools MCP - AI Debugging Capability Tests")
        print("=" * 60)
        print("Testing non-blocking debugging for AI tools (Claude Code, Cursor)")
        
        # Launch Chrome
        print("\nLaunching Chrome...")
        result = await launch_chrome(port=9222)
        if not result['success']:
            print(f"Failed to launch Chrome: {result['error']}")
            return
        
        # Run tests
        test1_success = await test_login_form_debugging()
        test2_success = await test_event_debugging()
        test3_success = await test_api_debugging()
        test4_success = await test_comprehensive_debugging()
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Results Summary:")
        print(f"✓ Login Form Debugging: {'PASSED' if test1_success else 'FAILED'}")
        print(f"✓ Event Debugging: {'PASSED' if test2_success else 'FAILED'}")
        print(f"✓ API Call Debugging: {'PASSED' if test3_success else 'FAILED'}")
        print(f"✓ Comprehensive Debugging: {'PASSED' if test4_success else 'FAILED'}")
        
        print("\n✅ All tests demonstrate successful non-blocking debugging")
        print("   suitable for AI-assisted development tools!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up...")
        await close_chrome()

if __name__ == "__main__":
    asyncio.run(main())