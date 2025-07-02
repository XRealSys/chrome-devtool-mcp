#!/usr/bin/env python3
"""
Test script to verify Chrome DevTools MCP works with partial domain enablement
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockDevToolsServer:
    """Mock Chrome DevTools server that only enables certain domains"""
    
    def __init__(self, enabled_domains=None):
        self.enabled_domains = enabled_domains or ['Runtime', 'Console']  # Only enable Runtime and Console by default
        self.message_id_counter = 0
        
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
        logger.info(f"Client connected: {path}")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                msg_id = data.get('id')
                method = data.get('method')
                
                logger.info(f"Received: {method}")
                
                # Prepare response
                response = {
                    "id": msg_id,
                }
                
                # Handle domain enable/disable
                if method and method.endswith('.enable'):
                    domain = method.split('.')[0]
                    if domain in self.enabled_domains:
                        response["result"] = {}
                        logger.info(f"Enabled domain: {domain}")
                    else:
                        response["error"] = {
                            "code": -32601,
                            "message": f"Domain {domain} is not available"
                        }
                        logger.warning(f"Domain not available: {domain}")
                        
                # Handle other commands based on enabled domains
                elif method == "Runtime.evaluate":
                    if 'Runtime' in self.enabled_domains:
                        response["result"] = {
                            "result": {
                                "type": "string",
                                "value": "Test response"
                            }
                        }
                    else:
                        response["error"] = {
                            "code": -32601,
                            "message": "Runtime domain is not enabled"
                        }
                        
                elif method == "Page.navigate":
                    if 'Page' in self.enabled_domains:
                        response["result"] = {"frameId": "test-frame"}
                    else:
                        response["error"] = {
                            "code": -32601,
                            "message": "Page domain is not enabled"
                        }
                        
                else:
                    # Default response for other methods
                    response["result"] = {}
                
                await websocket.send(json.dumps(response))
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
            
    async def start_server(self, host='localhost', port=9223):
        """Start the mock DevTools server"""
        logger.info(f"Starting mock DevTools server on {host}:{port}")
        logger.info(f"Enabled domains: {self.enabled_domains}")
        
        async with websockets.serve(self.handle_client, host, port):
            await asyncio.Future()  # Run forever


async def test_mcp_client():
    """Test the MCP client with partial domain enablement"""
    import aiohttp
    
    # Start with a server that only has Runtime and Console enabled
    logger.info("\n=== Test 1: Server with only Runtime and Console domains ===")
    
    # Create mock HTTP endpoint for /json/list
    from aiohttp import web
    
    async def handle_json_list(request):
        return web.json_response([{
            "description": "",
            "devtoolsFrontendUrl": "",
            "id": "test-page-id",
            "title": "Test Page",
            "type": "page",
            "url": "http://example.com",
            "webSocketDebuggerUrl": "ws://localhost:9223/devtools/page/test-page-id"
        }])
    
    app = web.Application()
    app.router.add_get('/json/list', handle_json_list)
    
    # Start HTTP server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9222)
    await site.start()
    
    logger.info("Mock HTTP server started on port 9222")
    
    # Start WebSocket server with limited domains
    server1 = MockDevToolsServer(enabled_domains=['Runtime', 'Console'])
    server_task = asyncio.create_task(server1.start_server(port=9223))
    
    # Give servers time to start
    await asyncio.sleep(1)
    
    # Now test connecting with the MCP client
    logger.info("\nConnecting MCP client to mock server...")
    
    # Import and use the actual MCP client
    import sys
    sys.path.insert(0, '/Users/sky/Desktop/Code/QBNET.TECH/chrome-devtool-mcp/src')
    from chrome_devtools_mcp import chrome
    
    try:
        # Connect to the mock server
        result = await chrome.connect_remote(host='localhost', port=9222)
        logger.info(f"Connection result: {result}")
        
        # Check enabled domains
        enabled = chrome.get_enabled_domains()
        logger.info(f"Enabled domains: {enabled}")
        
        # Try to use a Runtime command (should work)
        logger.info("\nTrying Runtime.evaluate (should work)...")
        js_result = await chrome._send_command("Runtime.evaluate", {
            "expression": "1 + 1",
            "returnByValue": True
        })
        logger.info(f"JavaScript result: {js_result}")
        
        # Try to use a Page command (should fail)
        logger.info("\nTrying Page.navigate (should fail)...")
        try:
            nav_result = await chrome._send_command("Page.navigate", {
                "url": "http://example.com"
            })
            logger.info(f"Navigation result: {nav_result}")
        except Exception as e:
            logger.warning(f"Navigation failed as expected: {e}")
            
    finally:
        # Clean up
        await chrome.close()
        await runner.cleanup()
        server_task.cancel()
        
    logger.info("\n=== Test completed ===")


if __name__ == "__main__":
    asyncio.run(test_mcp_client())