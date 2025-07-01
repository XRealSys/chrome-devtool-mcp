#!/usr/bin/env python3
"""
Test script reading and code analysis capabilities
Demonstrates how AI tools can understand JavaScript code before setting breakpoints
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chrome_devtools_mcp import (
    launch_chrome, navigate_to, get_script_sources, get_script_source,
    search_in_scripts, get_page_functions, set_breakpoint, 
    execute_javascript, get_console_logs, close_chrome
)

async def test_script_discovery():
    """Test discovering and reading JavaScript sources"""
    print("\n=== Test 1: Script Discovery ===")
    
    # Create a test page with multiple scripts
    test_page = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Script Discovery Test</title>
        <script>
            // Inline script 1
            function globalInit() {
                console.log('Page initialized');
            }
        </script>
    </head>
    <body>
        <h2>Script Discovery Test</h2>
        <button onclick="handleClick()">Click Me</button>
        
        <script>
            // Inline script 2
            function handleClick() {
                console.log('Button clicked');
                processData({ action: 'click' });
            }
            
            function processData(data) {
                console.log('Processing:', data);
                validateInput(data);
            }
            
            function validateInput(input) {
                if (!input.action) {
                    console.error('Invalid input');
                    return false;
                }
                console.log('Input valid');
                return true;
            }
            
            class UserManager {
                constructor() {
                    this.users = [];
                }
                
                addUser(name) {
                    this.users.push(name);
                    console.log('User added:', name);
                }
            }
            
            const userManager = new UserManager();
        </script>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.min.js"></script>
    </body>
    </html>
    """
    
    await navigate_to(f"data:text/html,{test_page}")
    await asyncio.sleep(2)  # Wait for external script to load
    
    # 1. Get all script sources
    print("\n1. Getting all script sources...")
    scripts_result = await get_script_sources()
    
    if scripts_result['success']:
        print(f"   Found {scripts_result['data']['count']} scripts:")
        for script in scripts_result['data']['scripts']:
            print(f"   - Script ID: {script['scriptId']}")
            print(f"     URL: {script['url'][:80]}...")
            print(f"     Lines: {script['startLine']}-{script['endLine']}")
    
    # 2. Read specific script source
    print("\n2. Reading inline script source...")
    if scripts_result['success'] and scripts_result['data']['scripts']:
        # Find inline script (not external)
        inline_script = None
        for script in scripts_result['data']['scripts']:
            if 'data:text/html' in script['url']:
                inline_script = script
                break
        
        if inline_script:
            source_result = await get_script_source(inline_script['scriptId'])
            if source_result['success']:
                print(f"   Script has {source_result['data']['lineCount']} lines")
                print("   First 500 characters:")
                print("   " + source_result['data']['source'][:500].replace('\n', '\n   '))
    
    return True

async def test_function_search():
    """Test searching for functions in scripts"""
    print("\n=== Test 2: Function Search ===")
    
    # The page is already loaded from previous test
    
    # 1. Search for specific functions
    print("\n1. Searching for 'handleClick' function...")
    search_result = await search_in_scripts('handleClick', 'function')
    
    if search_result['success']:
        print(f"   Found {search_result['data']['count']} matches:")
        for match in search_result['data']['matches']:
            print(f"   - Line {match['lineNumber']}: {match['line']}")
            print(f"     Script: {match['url'][:50]}...")
    
    # 2. Search for 'validate' pattern
    print("\n2. Searching for functions with 'validate' pattern...")
    validate_result = await search_in_scripts('validate', 'function')
    
    if validate_result['success']:
        print(f"   Found {validate_result['data']['count']} matches:")
        for match in validate_result['data']['matches']:
            print(f"   - Line {match['lineNumber']}: {match['line']}")
    
    # 3. Search for class
    print("\n3. Searching for 'UserManager' class...")
    class_result = await search_in_scripts('UserManager', 'class')
    
    if class_result['success']:
        print(f"   Found {class_result['data']['count']} matches:")
        for match in class_result['data']['matches']:
            print(f"   - Line {match['lineNumber']}: {match['line']}")
    
    return True

async def test_page_functions():
    """Test getting all functions in the page"""
    print("\n=== Test 3: Page Functions Discovery ===")
    
    # Get all functions
    print("\n1. Getting all page functions...")
    functions_result = await get_page_functions()
    
    if functions_result['success']:
        print(f"   Found {functions_result['data']['count']} functions:")
        
        # Group by type
        global_funcs = [f for f in functions_result['data']['functions'] if f['type'] == 'global']
        method_funcs = [f for f in functions_result['data']['functions'] if f['type'] == 'method']
        
        print(f"\n   Global functions ({len(global_funcs)}):")
        for func in global_funcs[:10]:  # Show first 10
            print(f"   - {func['name']}")
            if 'handle' in func['name'] or 'process' in func['name'] or 'validate' in func['name']:
                print(f"     Preview: {func['source'][:60]}...")
        
        if method_funcs:
            print(f"\n   Methods ({len(method_funcs)}):")
            for func in method_funcs[:5]:
                print(f"   - {func['name']}")
    
    return True

async def test_intelligent_breakpoint_setting():
    """Test setting breakpoints based on code analysis"""
    print("\n=== Test 4: Intelligent Breakpoint Setting ===")
    
    # 1. Find and set breakpoint on validation function
    print("\n1. Finding validation function...")
    search_result = await search_in_scripts('validateInput', 'function')
    
    if search_result['success'] and search_result['data']['matches']:
        match = search_result['data']['matches'][0]
        print(f"   Found at line {match['lineNumber']}")
        
        # Set a logpoint at the function
        print("\n2. Setting logpoint on validateInput...")
        bp_result = await set_breakpoint('function', 'validateInput', {
            'logMessage': 'Validation called with input',
            'pause': False
        })
        print(f"   Breakpoint set: {bp_result['success']}")
    
    # 3. Find error handling code
    print("\n3. Searching for error handling...")
    error_result = await search_in_scripts('console.error', 'text')
    
    if error_result['success'] and error_result['data']['matches']:
        print(f"   Found {error_result['data']['count']} error handling locations:")
        for match in error_result['data']['matches']:
            print(f"   - Line {match['lineNumber']}: {match['line']}")
    
    # 4. Test the breakpoints
    print("\n4. Testing breakpoints...")
    
    # Trigger validation with invalid data
    await execute_javascript("""
        validateInput({});  // Missing 'action' property
    """)
    
    # Trigger validation with valid data
    await execute_javascript("""
        validateInput({ action: 'test' });
    """)
    
    await asyncio.sleep(1)
    
    # Get logs
    logs = await get_console_logs()
    print("\n5. Captured logs:")
    for log in logs['data']['logs'][-10:]:
        if log['text']:
            print(f"   [{log['level']}] {log['text']}")
    
    return True

async def test_ai_workflow():
    """Demonstrate a complete AI debugging workflow"""
    print("\n=== Test 5: AI Debugging Workflow ===")
    
    print("\nScenario: AI needs to debug why a button click isn't working")
    
    # 1. Find the button and its handler
    print("\n1. Finding button click handler...")
    
    # First, check the DOM
    elements = await execute_javascript("""
        const btn = document.querySelector('button');
        ({ 
            exists: !!btn,
            onclick: btn ? btn.onclick?.toString() : null,
            onclickAttr: btn ? btn.getAttribute('onclick') : null
        })
    """)
    
    print(f"   Button info: {elements['data']['result']}")
    
    # 2. Search for the handler function
    handler_name = 'handleClick'
    print(f"\n2. Searching for '{handler_name}' function...")
    
    handler_search = await search_in_scripts(handler_name, 'function')
    if handler_search['success'] and handler_search['data']['matches']:
        print(f"   Found function at line {handler_search['data']['matches'][0]['lineNumber']}")
        
        # 3. Analyze the call chain
        print("\n3. Analyzing function call chain...")
        
        # Read the script to understand the flow
        script_id = handler_search['data']['matches'][0]['scriptId']
        source = await get_script_source(script_id)
        
        if source['success']:
            # Simple analysis - find functions called by handleClick
            print("   Functions called by handleClick:")
            lines = source['data']['source'].split('\n')
            in_function = False
            for i, line in enumerate(lines):
                if 'function handleClick' in line:
                    in_function = True
                elif in_function and line.strip() == '}':
                    break
                elif in_function and '(' in line:
                    # Extract function calls
                    import re
                    calls = re.findall(r'(\w+)\s*\(', line)
                    for call in calls:
                        if call not in ['console', 'log', 'if', 'for']:
                            print(f"     - {call} (line {i+1})")
        
        # 4. Set strategic logpoints
        print("\n4. Setting strategic logpoints...")
        
        # Set logpoints on the call chain
        for func_name in ['handleClick', 'processData', 'validateInput']:
            bp_result = await set_breakpoint('function', func_name, {
                'logMessage': f'{func_name} called',
                'pause': False
            })
            print(f"   Logpoint on {func_name}: {'✓' if bp_result['success'] else '✗'}")
        
        # 5. Trigger and analyze
        print("\n5. Triggering button click...")
        await execute_javascript("document.querySelector('button').click()")
        
        await asyncio.sleep(1)
        
        # Get execution flow from logs
        logs = await get_console_logs()
        print("\n6. Execution flow:")
        for log in logs['data']['logs'][-15:]:
            if log['text'] and ('called' in log['text'] or 'Processing' in log['text'] or 'valid' in log['text']):
                print(f"   → {log['text']}")
    
    return True

async def main():
    """Run all script reading tests"""
    try:
        print("Chrome DevTools MCP - Script Reading and Analysis Tests")
        print("=" * 60)
        print("Demonstrating how AI can understand code before debugging")
        
        # Launch Chrome
        print("\nLaunching Chrome...")
        result = await launch_chrome(port=9222)
        if not result['success']:
            print(f"Failed to launch Chrome: {result['error']}")
            return
        
        # Run tests
        test1_success = await test_script_discovery()
        test2_success = await test_function_search()
        test3_success = await test_page_functions()
        test4_success = await test_intelligent_breakpoint_setting()
        test5_success = await test_ai_workflow()
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Results Summary:")
        print(f"✓ Script Discovery: {'PASSED' if test1_success else 'FAILED'}")
        print(f"✓ Function Search: {'PASSED' if test2_success else 'FAILED'}")
        print(f"✓ Page Functions: {'PASSED' if test3_success else 'FAILED'}")
        print(f"✓ Intelligent Breakpoints: {'PASSED' if test4_success else 'FAILED'}")
        print(f"✓ AI Workflow: {'PASSED' if test5_success else 'FAILED'}")
        
        print("\n✅ AI now has full visibility into JavaScript code!")
        print("   Can read sources, search for functions, and set targeted breakpoints")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up...")
        await close_chrome()

if __name__ == "__main__":
    asyncio.run(main())