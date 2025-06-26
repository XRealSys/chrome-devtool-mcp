#!/usr/bin/env python3
"""
Chrome DevTools MCP Server - Production Version
A Model Context Protocol server for Chrome DevTools control
Tested and verified to work with Cursor
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
import base64
import tempfile
import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
import websockets
import aiohttp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP
mcp = FastMCP("chrome-devtools-mcp")

# Create a router for MCP endpoints
mcp_router = APIRouter()

# Initialize SSE transport
sse = SseServerTransport("/messages/")


class ChromeInstance:
    """Manages a Chrome browser instance with CDP connection"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_url: Optional[str] = None
        self.message_id = 0
        self.pending_messages: Dict[int, asyncio.Future] = {}
        self.event_handlers = {}
        self.console_logs: List[Dict] = []
        self.network_logs: List[Dict] = []
        self.debugging_port: int = 9222
        
    async def launch(self, headless: bool = False, port: int = 9222) -> Dict[str, Any]:
        """Launch Chrome with remote debugging enabled"""
        if self.process and self.process.poll() is None:
            logger.info(f"Chrome already running on port {self.debugging_port}")
            return {"status": "already_running", "port": self.debugging_port, "ws_url": self.ws_url}
        
        self.debugging_port = port
        
        chrome_args = [
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={tempfile.mkdtemp()}",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection"
        ]
        
        if headless:
            chrome_args.extend(["--headless", "--disable-gpu"])
            
        # Try different Chrome executables
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
            "/usr/bin/google-chrome",  # Linux
            "/usr/bin/chromium-browser",  # Linux Chromium
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",  # Windows 32-bit
        ]
        
        # Add paths from environment
        if "CHROME_PATH" in os.environ:
            chrome_paths.insert(0, os.environ["CHROME_PATH"])
            
        chrome_executable = None
        for path in chrome_paths:
            try:
                if os.path.exists(path):
                    chrome_executable = path
                    break
                # Try to run it to see if it's in PATH
                result = subprocess.run([path, "--version"], capture_output=True, timeout=2)
                if result.returncode == 0:
                    chrome_executable = path
                    break
            except:
                continue
                
        if not chrome_executable:
            raise Exception("Chrome executable not found. Set CHROME_PATH environment variable.")
            
        logger.info(f"Launching Chrome from: {chrome_executable}")
        self.process = subprocess.Popen([chrome_executable] + chrome_args)
        
        # Wait for Chrome to start and be ready
        await asyncio.sleep(3)
        
        # Connect to Chrome DevTools
        async with aiohttp.ClientSession() as session:
            max_retries = 5
            for i in range(max_retries):
                try:
                    # Get the list of pages
                    async with session.get(f"http://localhost:{port}/json/list") as resp:
                        pages = await resp.json()
                        
                    # Find a suitable page or create new one
                    target_page = None
                    for page in pages:
                        if page.get('type') == 'page' and 'devtools' not in page.get('url', ''):
                            target_page = page
                            break
                            
                    if not target_page:
                        # Create a new page
                        async with session.put(f"http://localhost:{port}/json/new") as resp:
                            target_page = await resp.json()
                            
                    self.ws_url = target_page['webSocketDebuggerUrl']
                    logger.info(f"Connecting to page: {target_page.get('url', 'about:blank')}")
                    break
                    
                except Exception as e:
                    if i < max_retries - 1:
                        logger.warning(f"Chrome not ready yet, retrying... ({i+1}/{max_retries})")
                        await asyncio.sleep(2)
                    else:
                        raise Exception(f"Failed to connect to Chrome: {e}")
                        
        await self._connect_websocket()
        
        return {
            "status": "launched",
            "port": port,
            "ws_url": self.ws_url,
            "pid": self.process.pid
        }
        
    async def _connect_websocket(self):
        """Connect to Chrome DevTools WebSocket"""
        self.ws = await websockets.connect(self.ws_url, max_size=None)
        
        # Start message listener
        self._listener_task = asyncio.create_task(self._message_listener())
        
        # Enable necessary domains
        try:
            await self._send_command("Runtime.enable")
            await self._send_command("Page.enable")
            await self._send_command("Network.enable")
            await self._send_command("DOM.enable")
            await self._send_command("Console.enable")
            logger.info("Successfully enabled all Chrome DevTools domains")
        except Exception as e:
            logger.error(f"Error enabling Chrome DevTools domains: {e}")
            raise
        
        # Set up event handlers
        self.event_handlers['Console.messageAdded'] = self._handle_console_message
        self.event_handlers['Network.requestWillBeSent'] = self._handle_network_request
        self.event_handlers['Network.responseReceived'] = self._handle_network_response
        
    async def _message_listener(self):
        """Listen for messages from Chrome DevTools"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                if 'id' in data:
                    # Response to a command
                    msg_id = data['id']
                    if msg_id in self.pending_messages:
                        self.pending_messages[msg_id].set_result(data)
                        
                elif 'method' in data:
                    # Event from Chrome
                    method = data['method']
                    if method in self.event_handlers:
                        try:
                            await self.event_handlers[method](data.get('params', {}))
                        except Exception as e:
                            logger.error(f"Error handling event {method}: {e}")
                            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket listener error: {e}")
            
    async def _send_command(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Send a command to Chrome DevTools"""
        if not self.ws:
            raise Exception("Not connected to Chrome DevTools")
            
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": method
        }
        
        if params:
            message["params"] = params
            
        future = asyncio.Future()
        self.pending_messages[self.message_id] = future
        
        try:
            await self.ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send command {method}: {e}")
            self.pending_messages.pop(self.message_id, None)
            raise
        
        # Wait for response with timeout (longer for certain commands)
        timeout_seconds = 30.0 if method in ["Page.captureScreenshot", "Page.printToPDF"] else 10.0
        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            self.pending_messages.pop(self.message_id, None)
            logger.error(f"Timeout waiting for response to {method}")
            raise Exception(f"Timeout waiting for response to {method}")
        finally:
            self.pending_messages.pop(self.message_id, None)
        
        if 'error' in result:
            raise Exception(f"Chrome DevTools error: {result['error']}")
            
        return result.get('result', {})
        
    async def _handle_console_message(self, params: Dict):
        """Handle console messages"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": params.get('level', 'log'),
            "text": params.get('text', '')
        }
        
        # Try to extract text from args if text is empty
        if not entry['text'] and 'args' in params:
            args_text = []
            for arg in params['args']:
                if 'value' in arg:
                    args_text.append(str(arg['value']))
                elif 'description' in arg:
                    args_text.append(arg['description'])
            if args_text:
                entry['text'] = ' '.join(args_text)
                
        self.console_logs.append(entry)
        
        # Keep only last 1000 logs
        if len(self.console_logs) > 1000:
            self.console_logs = self.console_logs[-1000:]
        
    async def _handle_network_request(self, params: Dict):
        """Handle network requests"""
        request = params.get('request', {})
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "url": request.get('url', ''),
            "method": request.get('method', ''),
            "headers": request.get('headers', {})
        }
        self.network_logs.append(entry)
        
        # Keep only last 1000 logs
        if len(self.network_logs) > 1000:
            self.network_logs = self.network_logs[-1000:]
        
    async def _handle_network_response(self, params: Dict):
        """Handle network responses"""
        response = params.get('response', {})
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "url": response.get('url', ''),
            "status": response.get('status', 0),
            "statusText": response.get('statusText', ''),
            "headers": response.get('headers', {})
        }
        self.network_logs.append(entry)
        
        # Keep only last 1000 logs
        if len(self.network_logs) > 1000:
            self.network_logs = self.network_logs[-1000:]
        
    async def close(self):
        """Close Chrome instance and WebSocket connection"""
        if hasattr(self, '_listener_task'):
            self._listener_task.cancel()
            
        if self.ws:
            await self.ws.close()
            self.ws = None
            
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            
        logger.info("Chrome instance closed")
            
    async def ensure_connected(self):
        """Ensure we're connected to Chrome DevTools"""
        # Check if websocket is connected
        ws_closed = False
        if not self.ws:
            ws_closed = True
        else:
            try:
                # Try to ping the websocket
                pong = await self.ws.ping()
                await asyncio.wait_for(pong, timeout=1.0)
            except:
                ws_closed = True
                
        if ws_closed:
            # Try to reconnect
            logger.info("WebSocket disconnected, attempting to reconnect...")
            async with aiohttp.ClientSession() as session:
                try:
                    # Get the list of pages
                    async with session.get(f"http://localhost:{self.debugging_port}/json/list") as resp:
                        pages = await resp.json()
                        
                    if pages:
                        # Use the first available page
                        page = pages[0]
                        self.ws_url = page['webSocketDebuggerUrl']
                        await self._connect_websocket()
                        logger.info(f"Reconnected to page: {page.get('url', 'about:blank')}")
                    else:
                        raise Exception("No pages available in Chrome")
                except Exception as e:
                    logger.error(f"Failed to reconnect: {e}")
                    raise Exception(f"Chrome connection lost: {e}")
            

# Global Chrome instance
chrome = ChromeInstance()


# Tool definitions
@mcp.tool(description="Launch a Chrome browser instance for development and debugging. This is the starting point for frontend development debugging.")
async def launch_chrome(headless: bool = False, port: int = 9222) -> Dict[str, Any]:
    """Launch Chrome with remote debugging enabled"""
    try:
        result = await chrome.launch(headless=headless, port=port)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Navigate to a specific URL in the Chrome browser")
async def navigate_to(url: str) -> Dict[str, Any]:
    """Navigate Chrome to a specific URL"""
    try:
        await chrome.ensure_connected()
        
        result = await chrome._send_command("Page.navigate", {"url": url})
        
        # Wait for page to start loading
        await asyncio.sleep(0.5)
        
        # Wait for page to finish loading (with timeout)
        try:
            await chrome._send_command("Page.waitForLoadEventFired")
        except:
            # Page might already be loaded or timeout
            pass
            
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Navigation error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Get the DOM tree structure of the current page. Useful for understanding page structure and debugging.")
async def get_dom_tree(depth: int = 3) -> Dict[str, Any]:
    """Get DOM tree structure"""
    try:
        await chrome.ensure_connected()
        
        # Get document
        doc = await chrome._send_command("DOM.getDocument", {"depth": depth})
        
        if not doc or 'root' not in doc:
            return {
                "success": False,
                "error": "Failed to get document"
            }
        
        # Get outer HTML of the root
        root_node_id = doc['root']['nodeId']
        html = await chrome._send_command("DOM.getOuterHTML", {"nodeId": root_node_id})
        
        html_content = html.get('outerHTML', '')
        
        return {
            "success": True,
            "data": {
                "nodeInfo": doc['root'],
                "html": html_content[:1000] + "..." if len(html_content) > 1000 else html_content
            }
        }
    except Exception as e:
        logger.error(f"Failed to get DOM tree: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Query DOM elements using CSS selectors. Returns element information and content.")
async def query_elements(selector: str) -> Dict[str, Any]:
    """Query DOM elements by CSS selector"""
    try:
        await chrome.ensure_connected()
        
        # Execute JavaScript to query elements
        result = await chrome._send_command("Runtime.evaluate", {
            "expression": f"""
                Array.from(document.querySelectorAll('{selector}')).map(el => ({{
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className,
                    textContent: el.textContent.trim().substring(0, 100),
                    attributes: Array.from(el.attributes).reduce((acc, attr) => {{
                        acc[attr.name] = attr.value;
                        return acc;
                    }}, {{}})
                }}))
            """,
            "returnByValue": True
        })
        
        elements = []
        if result and 'result' in result and 'value' in result['result']:
            elements = result['result']['value']
        
        return {
            "success": True,
            "data": {
                "selector": selector,
                "elements": elements,
                "count": len(elements)
            }
        }
    except Exception as e:
        logger.error(f"Failed to query elements: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Get network request logs including requests and responses. Useful for debugging API calls and network issues.")
async def get_network_logs(filter_url: Optional[str] = None) -> Dict[str, Any]:
    """Get network request logs"""
    try:
        logs = chrome.network_logs
        
        if filter_url:
            logs = [log for log in logs if filter_url in log.get('url', '')]
            
        return {
            "success": True,
            "data": {
                "logs": logs[-50:],  # Return last 50 logs
                "total": len(logs)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get network logs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Get console output logs including errors, warnings, and log messages. Essential for debugging JavaScript issues.")
async def get_console_logs(level: Optional[str] = None) -> Dict[str, Any]:
    """Get console logs"""
    try:
        logs = chrome.console_logs
        
        if level:
            logs = [log for log in logs if log.get('level') == level]
            
        return {
            "success": True,
            "data": {
                "logs": logs[-50:],  # Return last 50 logs
                "total": len(logs)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get console logs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Execute JavaScript code in the page context. Can be used to interact with the page, modify DOM, or test functionality.")
async def execute_javascript(code: str) -> Dict[str, Any]:
    """Execute JavaScript in the page context"""
    try:
        await chrome.ensure_connected()
        
        result = await chrome._send_command("Runtime.evaluate", {
            "expression": code,
            "returnByValue": True,
            "awaitPromise": True
        })
        
        response_data = {
            "result": None,
            "type": "undefined"
        }
        
        if result and 'result' in result:
            response_data["result"] = result['result'].get('value')
            response_data["type"] = result['result'].get('type', 'undefined')
            
        return {
            "success": True,
            "data": response_data
        }
    except Exception as e:
        logger.error(f"Failed to execute JavaScript: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Take a screenshot of the current page. Useful for visual debugging and verification.")
async def take_screenshot(full_page: bool = False) -> Dict[str, Any]:
    """Take a screenshot of the current page"""
    try:
        await chrome.ensure_connected()
        
        # Navigate to a simple page first if on extension page
        current_url = await chrome._send_command("Runtime.evaluate", {
            "expression": "window.location.href",
            "returnByValue": True
        })
        
        if current_url and 'result' in current_url:
            url = current_url['result'].get('value', '')
            if 'chrome-extension://' in url or url == 'about:blank':
                # Navigate to a simple page first
                await chrome._send_command("Page.navigate", {"url": "data:text/html,<h1>Ready for screenshot</h1>"})
                await asyncio.sleep(1)
        
        screenshot_params = {"format": "png"}
        
        if full_page:
            # Get page metrics for full page screenshot
            metrics = await chrome._send_command("Page.getLayoutMetrics")
            width = int(metrics['contentSize']['width'])
            height = int(metrics['contentSize']['height'])
            
            # Set viewport to full size
            await chrome._send_command("Emulation.setDeviceMetricsOverride", {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            
            screenshot_params["captureBeyondViewport"] = True
            
        # Capture screenshot
        screenshot = await chrome._send_command("Page.captureScreenshot", screenshot_params)
        
        # Reset viewport if full page
        if full_page:
            await chrome._send_command("Emulation.clearDeviceMetricsOverride")
            
        # Save screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        
        with open(filename, "wb") as f:
            f.write(base64.b64decode(screenshot['data']))
            
        return {
            "success": True,
            "data": {
                "filename": os.path.abspath(filename),
                "size": len(screenshot['data'])
            }
        }
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Get basic page information including title, URL, and meta tags")
async def get_page_info() -> Dict[str, Any]:
    """Get current page information"""
    try:
        await chrome.ensure_connected()
        
        # Get page info using JavaScript
        result = await chrome._send_command("Runtime.evaluate", {
            "expression": """
                ({
                    title: document.title,
                    url: window.location.href,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    meta: Array.from(document.querySelectorAll('meta')).map(m => ({
                        name: m.name || m.getAttribute('property') || m.getAttribute('http-equiv'),
                        content: m.content
                    })).filter(m => m.name)
                })
            """,
            "returnByValue": True
        })
        
        page_info = {}
        if result and 'result' in result and 'value' in result['result']:
            page_info = result['result']['value']
            
        return {
            "success": True,
            "data": page_info
        }
    except Exception as e:
        logger.error(f"Failed to get page info: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Close the Chrome browser instance")
async def close_chrome() -> Dict[str, Any]:
    """Close Chrome browser"""
    try:
        await chrome.close()
        return {
            "success": True,
            "data": {"message": "Chrome closed successfully"}
        }
    except Exception as e:
        logger.error(f"Failed to close Chrome: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# SSE endpoint handlers
async def handle_sse(request: Request):
    """Handle SSE connections"""
    try:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    except Exception as e:
        logger.error(f"SSE error: {e}")
        raise


async def handle_post_message(request: Request):
    """Handle POST messages for SSE"""
    try:
        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            return {}

        await sse.handle_post_message(request.scope, receive, send)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        return {"status": "error", "error": str(e)}


def setup_mcp_server(app: FastAPI):
    """Setup MCP server with the FastAPI application"""
    mcp._mcp_server.name = "chrome-devtools-mcp"
    
    # Add SSE endpoints directly to app
    app.add_api_route("/sse", handle_sse, methods=["GET"])
    app.add_api_route("/messages/", handle_post_message, methods=["POST"])


# Create FastAPI app
app = FastAPI(
    title="Chrome DevTools MCP Server",
    description="MCP server for controlling Chrome browser through DevTools Protocol",
    version="1.0.0"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chrome-devtools-mcp", "version": "1.0.0"}

# Setup MCP server
setup_mcp_server(app)


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("MCP_PORT", "12524"))
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    
    logger.info(f"Starting Chrome DevTools MCP server on {host}:{port}")
    logger.info("Tools available: launch_chrome, navigate_to, get_dom_tree, query_elements, get_network_logs, get_console_logs, execute_javascript, take_screenshot, get_page_info, close_chrome")
    
    uvicorn.run(app, host=host, port=port)