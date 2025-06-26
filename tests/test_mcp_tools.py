#!/usr/bin/env python3
"""
Test suite for Chrome DevTools MCP Server
Tests all tools to ensure they work correctly
"""

import asyncio
import httpx
import json
import time
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
MCP_SERVER_URL = "http://localhost:12524"
TEST_URL = "https://example.com"

async def send_mcp_request(method: str, params: dict = None):
    """Send an MCP request to the server"""
    async with httpx.AsyncClient() as client:
        # First, we need to establish SSE connection
        # For testing, we'll send direct tool calls
        
        # This simulates what Cursor would do
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": f"tools/{method}",
            "params": params or {}
        }
        
        # For direct testing, we'll call the tools directly
        # In production, this goes through SSE
        return request_data

async def test_launch_chrome():
    """Test launching Chrome"""
    print("\n=== Testing launch_chrome ===")
    
    # Import the module to test directly
    from src.chrome_devtools_mcp import launch_chrome
    
    result = await launch_chrome(headless=False, port=9222)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, "Failed to launch Chrome"
    assert "data" in result, "No data in result"
    assert "pid" in result["data"], "No PID in result"
    
    print("✓ Chrome launched successfully")
    return result

async def test_navigate_to():
    """Test navigating to a URL"""
    print("\n=== Testing navigate_to ===")
    
    from src.chrome_devtools_mcp import navigate_to
    
    result = await navigate_to(url=TEST_URL)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to navigate: {result.get('error')}"
    print("✓ Navigation successful")
    return result

async def test_get_page_info():
    """Test getting page info"""
    print("\n=== Testing get_page_info ===")
    
    from src.chrome_devtools_mcp import get_page_info
    
    # Wait a bit for page to fully load
    await asyncio.sleep(2)
    
    result = await get_page_info()
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to get page info: {result.get('error')}"
    assert "data" in result, "No data in result"
    assert "title" in result["data"], "No title in page info"
    assert "url" in result["data"], "No URL in page info"
    
    print("✓ Page info retrieved successfully")
    return result

async def test_get_dom_tree():
    """Test getting DOM tree"""
    print("\n=== Testing get_dom_tree ===")
    
    from src.chrome_devtools_mcp import get_dom_tree
    
    result = await get_dom_tree(depth=2)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to get DOM tree: {result.get('error')}"
    assert "data" in result, "No data in result"
    assert "html" in result["data"], "No HTML in result"
    
    print("✓ DOM tree retrieved successfully")
    return result

async def test_query_elements():
    """Test querying elements"""
    print("\n=== Testing query_elements ===")
    
    from src.chrome_devtools_mcp import query_elements
    
    # Query for common elements
    result = await query_elements(selector="h1")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to query elements: {result.get('error')}"
    assert "data" in result, "No data in result"
    assert "elements" in result["data"], "No elements in result"
    assert "count" in result["data"], "No count in result"
    
    print(f"✓ Found {result['data']['count']} h1 elements")
    return result

async def test_execute_javascript():
    """Test executing JavaScript"""
    print("\n=== Testing execute_javascript ===")
    
    from src.chrome_devtools_mcp import execute_javascript
    
    # Simple JS execution
    result = await execute_javascript(code="document.title")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to execute JS: {result.get('error')}"
    assert "data" in result, "No data in result"
    assert "result" in result["data"], "No result in data"
    
    print("✓ JavaScript executed successfully")
    return result

async def test_get_console_logs():
    """Test getting console logs"""
    print("\n=== Testing get_console_logs ===")
    
    from src.chrome_devtools_mcp import execute_javascript, get_console_logs
    
    # First, create some console logs
    await execute_javascript(code='console.log("Test log message")')
    await execute_javascript(code='console.error("Test error message")')
    
    # Wait a bit for logs to be captured
    await asyncio.sleep(1)
    
    result = await get_console_logs()
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to get console logs: {result.get('error')}"
    assert "data" in result, "No data in result"
    assert "logs" in result["data"], "No logs in result"
    
    print(f"✓ Retrieved {len(result['data']['logs'])} console logs")
    return result

async def test_get_network_logs():
    """Test getting network logs"""
    print("\n=== Testing get_network_logs ===")
    
    from src.chrome_devtools_mcp import get_network_logs
    
    result = await get_network_logs()
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to get network logs: {result.get('error')}"
    assert "data" in result, "No data in result"
    assert "logs" in result["data"], "No logs in result"
    
    print(f"✓ Retrieved {len(result['data']['logs'])} network logs")
    return result

async def test_take_screenshot():
    """Test taking screenshot"""
    print("\n=== Testing take_screenshot ===")
    
    from src.chrome_devtools_mcp import take_screenshot
    
    result = await take_screenshot(full_page=False)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to take screenshot: {result.get('error')}"
    assert "data" in result, "No data in result"
    assert "filename" in result["data"], "No filename in result"
    
    # Check if file exists
    filename = result["data"]["filename"]
    assert os.path.exists(filename), f"Screenshot file not found: {filename}"
    
    print(f"✓ Screenshot saved to {filename}")
    
    # Clean up
    os.remove(filename)
    return result

async def test_close_chrome():
    """Test closing Chrome"""
    print("\n=== Testing close_chrome ===")
    
    from src.chrome_devtools_mcp import close_chrome
    
    result = await close_chrome()
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["success"] == True, f"Failed to close Chrome: {result.get('error')}"
    print("✓ Chrome closed successfully")
    return result

async def test_server_endpoints():
    """Test server HTTP endpoints"""
    print("\n=== Testing Server Endpoints ===")
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        try:
            response = await client.get(f"{MCP_SERVER_URL}/health")
            print(f"Health check: {response.status_code} - {response.json()}")
            assert response.status_code == 200, "Health check failed"
            print("✓ Health endpoint working")
        except Exception as e:
            print(f"✗ Health endpoint failed: {e}")
            
        # Test SSE endpoint exists
        try:
            response = await client.get(f"{MCP_SERVER_URL}/sse", timeout=1.0)
            # SSE will timeout, but we just want to know it exists
        except httpx.TimeoutException:
            print("✓ SSE endpoint exists (timeout expected)")
        except Exception as e:
            print(f"✗ SSE endpoint error: {e}")

async def run_all_tests():
    """Run all tests in sequence"""
    print("Starting Chrome DevTools MCP Server Tests")
    print("=" * 50)
    
    try:
        # Test server endpoints first
        await test_server_endpoints()
        
        # Test Chrome tools
        await test_launch_chrome()
        await test_navigate_to()
        await test_get_page_info()
        await test_get_dom_tree()
        await test_query_elements()
        await test_execute_javascript()
        await test_get_console_logs()
        await test_get_network_logs()
        await test_take_screenshot()
        await test_close_chrome()
        
        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED!")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        # Still try to close Chrome
        try:
            from src.chrome_devtools_mcp import close_chrome
            await close_chrome()
        except:
            pass
        raise
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        # Still try to close Chrome
        try:
            from src.chrome_devtools_mcp import close_chrome
            await close_chrome()
        except:
            pass
        raise

if __name__ == "__main__":
    # Check if server is running
    import sys
    
    async def check_server():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{MCP_SERVER_URL}/health", timeout=2.0)
                return response.status_code == 200
            except:
                return False
    
    if not asyncio.run(check_server()):
        print("ERROR: MCP server is not running!")
        print("Start it with: ./start.sh")
        sys.exit(1)
    
    # Run tests
    asyncio.run(run_all_tests())