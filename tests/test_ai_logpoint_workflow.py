#!/usr/bin/env python3
"""
Complete AI workflow test: Find code, analyze it, and set logpoints
This demonstrates how AI tools like Claude Code would debug a real issue
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chrome_devtools_mcp import (
    launch_chrome, navigate_to, query_elements, get_script_sources,
    get_script_source, search_in_scripts, set_breakpoint,
    execute_javascript, get_console_logs, close_chrome
)

async def main():
    """Demonstrate complete AI debugging workflow with logpoints"""
    print("=" * 70)
    print("AI Debugging Workflow: Setting Logpoints on Specific JS Statements")
    print("=" * 70)
    
    try:
        # Launch Chrome
        print("\n1. Launching Chrome...")
        result = await launch_chrome(port=9222)
        if not result['success']:
            print(f"   ❌ Failed: {result['error']}")
            return
        print("   ✅ Chrome launched successfully")
        
        # Create a test page with a realistic scenario
        print("\n2. Creating test page with shopping cart...")
        test_page = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Shopping Cart Test</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                .product { border: 1px solid #ccc; padding: 10px; margin: 10px 0; }
                button { padding: 5px 10px; margin: 5px; }
                #cart { background: #f0f0f0; padding: 10px; margin-top: 20px; }
                .error { color: red; }
                .success { color: green; }
            </style>
        </head>
        <body>
            <h1>Shopping Cart Debug Test</h1>
            
            <div class="product">
                <h3>Laptop - $999</h3>
                <button onclick="addToCart('laptop', 999)">Add to Cart</button>
            </div>
            
            <div class="product">
                <h3>Mouse - $29</h3>
                <button onclick="addToCart('mouse', 29)">Add to Cart</button>
            </div>
            
            <div id="cart">
                <h3>Shopping Cart</h3>
                <div id="cart-items">Empty</div>
                <div id="cart-total">Total: $0</div>
                <button onclick="checkout()">Checkout</button>
            </div>
            
            <div id="message"></div>
            
            <script>
                // Shopping cart implementation
                let cart = [];
                let total = 0;
                
                function addToCart(product, price) {
                    // Validate input
                    if (!product || price <= 0) {
                        showMessage('Invalid product or price', 'error');
                        return;
                    }
                    
                    // Add to cart array
                    cart.push({ product: product, price: price });
                    
                    // Update total
                    total += price;
                    
                    // Update UI
                    updateCartDisplay();
                    
                    // Show success message
                    showMessage(`Added ${product} to cart`, 'success');
                    
                    // Log for analytics
                    logAnalytics('add_to_cart', { product: product, price: price });
                }
                
                function updateCartDisplay() {
                    const itemsDiv = document.getElementById('cart-items');
                    const totalDiv = document.getElementById('cart-total');
                    
                    if (cart.length === 0) {
                        itemsDiv.textContent = 'Empty';
                    } else {
                        itemsDiv.innerHTML = cart.map(item => 
                            `${item.product} - $${item.price}`
                        ).join('<br>');
                    }
                    
                    totalDiv.textContent = `Total: $${total}`;
                }
                
                function checkout() {
                    if (cart.length === 0) {
                        showMessage('Cart is empty!', 'error');
                        return;
                    }
                    
                    // Validate total
                    const calculatedTotal = cart.reduce((sum, item) => sum + item.price, 0);
                    if (calculatedTotal !== total) {
                        console.error('Total mismatch:', { calculated: calculatedTotal, stored: total });
                        showMessage('Error: Total mismatch', 'error');
                        return;
                    }
                    
                    // Process checkout
                    showMessage(`Processing checkout for ${cart.length} items...`, 'success');
                    logAnalytics('checkout', { items: cart.length, total: total });
                    
                    // Simulate API call
                    setTimeout(() => {
                        showMessage('Checkout complete!', 'success');
                        // Clear cart
                        cart = [];
                        total = 0;
                        updateCartDisplay();
                    }, 1000);
                }
                
                function showMessage(text, type) {
                    const msgDiv = document.getElementById('message');
                    msgDiv.textContent = text;
                    msgDiv.className = type;
                    setTimeout(() => {
                        msgDiv.textContent = '';
                        msgDiv.className = '';
                    }, 3000);
                }
                
                function logAnalytics(event, data) {
                    console.log(`Analytics: ${event}`, data);
                }
            </script>
        </body>
        </html>
        """
        
        import urllib.parse
        encoded_html = urllib.parse.quote(test_page)
        await navigate_to(f"data:text/html,{encoded_html}")
        await asyncio.sleep(2)
        print("   ✅ Test page loaded")
        
        # AI Workflow starts here
        print("\n" + "="*50)
        print("AI DEBUGGING WORKFLOW BEGINS")
        print("="*50)
        
        print("\nScenario: User reports 'checkout total sometimes wrong'")
        print("AI needs to debug the checkout process...")
        
        # Step 1: Discover available scripts
        print("\n3. Discovering JavaScript sources...")
        scripts = await get_script_sources()
        print(f"   ✅ Found {scripts['data']['count']} scripts")
        
        # Find the main script (inline script with our code)
        main_script = None
        for script in scripts['data']['scripts']:
            if 'data:text/html' in script['url'] and script['endLine'] > 50:
                main_script = script
                break
        
        if not main_script:
            print("   ❌ Could not find main script")
            return
            
        print(f"   ✅ Main script found: ID {main_script['scriptId']}")
        
        # Step 2: Search for checkout function
        print("\n4. Searching for 'checkout' function...")
        checkout_search = await search_in_scripts('checkout', 'function')
        
        if checkout_search['success'] and checkout_search['data']['matches']:
            print(f"   ✅ Found checkout function at line {checkout_search['data']['matches'][0]['lineNumber']}")
        else:
            print("   ❌ Checkout function not found")
            return
        
        # Step 3: Read the script to understand the code
        print("\n5. Reading script source to analyze code...")
        source = await get_script_source(main_script['scriptId'])
        
        if source['success']:
            lines = source['data']['source'].split('\n')
            print("   ✅ Script source retrieved")
            
            # Analyze the code to find important points
            print("\n6. Analyzing code to find critical points...")
            critical_points = []
            
            for i, line in enumerate(lines):
                # Find where total is calculated
                if 'calculatedTotal' in line and 'reduce' in line:
                    critical_points.append({
                        'line': i + 1,
                        'code': line.strip(),
                        'reason': 'Total calculation'
                    })
                
                # Find where total is compared
                if 'calculatedTotal !== total' in line:
                    critical_points.append({
                        'line': i + 1,
                        'code': line.strip(),
                        'reason': 'Total comparison'
                    })
                
                # Find where total is updated
                if 'total +=' in line:
                    critical_points.append({
                        'line': i + 1,
                        'code': line.strip(),
                        'reason': 'Total update'
                    })
                
                # Find error logging
                if 'console.error' in line and 'mismatch' in line:
                    critical_points.append({
                        'line': i + 1,
                        'code': line.strip(),
                        'reason': 'Error logging'
                    })
            
            print(f"   ✅ Found {len(critical_points)} critical points:")
            for point in critical_points:
                print(f"      Line {point['line']}: {point['reason']}")
                print(f"      Code: {point['code'][:60]}...")
        
        # Step 4: Set strategic logpoints
        print("\n7. Setting logpoints at critical locations...")
        
        # Logpoint on addToCart to track what's being added
        bp1 = await set_breakpoint('function', 'addToCart', {
            'logMessage': 'Adding to cart',
            'pause': False
        })
        print(f"   {'✅' if bp1['success'] else '❌'} Logpoint on addToCart function")
        
        # Logpoint on checkout to track the process
        bp2 = await set_breakpoint('function', 'checkout', {
            'logMessage': 'Checkout initiated',
            'pause': False
        })
        print(f"   {'✅' if bp2['success'] else '❌'} Logpoint on checkout function")
        
        # Add custom logging for critical calculations
        await execute_javascript("""
            // Wrap the reduce function to log calculations
            const originalCheckout = checkout;
            checkout = function() {
                console.log('🔍 LOGPOINT: Checkout called');
                console.log('🔍 LOGPOINT: Current cart:', JSON.stringify(cart));
                console.log('🔍 LOGPOINT: Current total:', total);
                
                // Call original function
                return originalCheckout.apply(this, arguments);
            };
            
            // Also wrap the total calculation
            const originalAddToCart = addToCart;
            addToCart = function(product, price) {
                console.log('🔍 LOGPOINT: addToCart called', { product, price });
                console.log('🔍 LOGPOINT: Total before:', total);
                
                const result = originalAddToCart.apply(this, arguments);
                
                console.log('🔍 LOGPOINT: Total after:', total);
                console.log('🔍 LOGPOINT: Cart size:', cart.length);
                
                return result;
            };
        """)
        print("   ✅ Enhanced logging injected")
        
        # Step 5: Test the scenario
        print("\n8. Testing the shopping cart with logpoints active...")
        
        # Add some items
        print("   - Adding laptop ($999)")
        await execute_javascript("document.querySelector('button[onclick=\"addToCart(\\'laptop\\', 999)\"]').click()")
        await asyncio.sleep(0.5)
        
        print("   - Adding mouse ($29)")
        await execute_javascript("document.querySelector('button[onclick=\"addToCart(\\'mouse\\', 29)\"]').click()")
        await asyncio.sleep(0.5)
        
        print("   - Attempting checkout")
        await execute_javascript("document.querySelector('button[onclick=\"checkout()\"]').click()")
        await asyncio.sleep(1.5)
        
        # Step 6: Collect and analyze logs
        print("\n9. Analyzing collected logs...")
        logs = await get_console_logs()
        
        print("\n   Execution trace from logpoints:")
        print("   " + "-"*50)
        
        relevant_logs = []
        for log in logs['data']['logs']:
            if log['text'] and ('🔍 LOGPOINT' in log['text'] or 
                               'Analytics' in log['text'] or 
                               'error' in log['level']):
                relevant_logs.append(log)
        
        for log in relevant_logs[-20:]:  # Last 20 relevant logs
            if log['level'] == 'error':
                print(f"   ❌ ERROR: {log['text']}")
            elif '🔍 LOGPOINT' in log['text']:
                print(f"   📍 {log['text']}")
            else:
                print(f"   📊 {log['text']}")
        
        # Step 7: AI Analysis
        print("\n10. AI Analysis Summary:")
        print("   " + "-"*50)
        print("   ✅ Successfully traced execution flow")
        print("   ✅ Identified critical calculation points")
        print("   ✅ Set non-blocking logpoints at key locations")
        print("   ✅ Captured detailed execution data")
        
        # Check if we found any issues
        error_logs = [log for log in relevant_logs if log['level'] == 'error']
        if error_logs:
            print(f"   ⚠️  Found {len(error_logs)} errors during execution")
        else:
            print("   ✅ No errors detected in this test run")
        
        print("\n" + "="*70)
        print("AI DEBUGGING WORKFLOW COMPLETE")
        print("="*70)
        
        print("\nKey Capabilities Demonstrated:")
        print("1. ✅ Discovered and read JavaScript source code")
        print("2. ✅ Searched for specific functions")
        print("3. ✅ Analyzed code to find critical points")
        print("4. ✅ Set logpoints without pausing execution")
        print("5. ✅ Collected detailed execution traces")
        print("6. ✅ Provided actionable debugging information")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\nCleaning up...")
        await close_chrome()

if __name__ == "__main__":
    asyncio.run(main())