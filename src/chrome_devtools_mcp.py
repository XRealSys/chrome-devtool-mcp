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
        
    async def connect_remote(self, host: str = "localhost", port: int = 9222) -> Dict[str, Any]:
        """Connect to a remote Chrome/Chromium instance via CDP"""
        self.debugging_port = port
        remote_url = f"http://{host}:{port}"
        
        try:
            # Connect to remote Chrome DevTools
            async with aiohttp.ClientSession() as session:
                # Get the list of pages
                async with session.get(f"{remote_url}/json/list") as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to connect to remote Chrome at {remote_url}")
                    pages = await resp.json()
                    
                # Find a suitable page or use the first one
                target_page = None
                for page in pages:
                    if page.get('type') == 'page' and 'devtools' not in page.get('url', ''):
                        target_page = page
                        break
                        
                if not target_page and pages:
                    target_page = pages[0]
                    
                if not target_page:
                    raise Exception("No pages available in remote Chrome")
                    
                self.ws_url = target_page['webSocketDebuggerUrl']
                # Replace localhost with the actual host if needed
                if host != "localhost" and "ws://localhost" in self.ws_url:
                    self.ws_url = self.ws_url.replace("ws://localhost", f"ws://{host}")
                    
                logger.info(f"Connecting to remote page: {target_page.get('url', 'about:blank')}")
                
            await self._connect_websocket()
            
            return {
                "status": "connected",
                "host": host,
                "port": port,
                "ws_url": self.ws_url,
                "page_url": target_page.get('url', 'about:blank')
            }
            
        except Exception as e:
            logger.error(f"Failed to connect to remote Chrome at {remote_url}: {e}")
            raise
    
    async def connect_with_websocket_url(self, ws_url: str) -> Dict[str, Any]:
        """Connect directly using a WebSocket debugger URL"""
        try:
            self.ws_url = ws_url
            logger.info(f"Connecting directly to WebSocket URL: {ws_url}")
            
            await self._connect_websocket()
            
            # Try to get page info
            page_info = {}
            try:
                result = await self._send_command("Runtime.evaluate", {
                    "expression": "({url: window.location.href, title: document.title})",
                    "returnByValue": True
                })
                if result and 'result' in result and 'value' in result['result']:
                    page_info = result['result']['value']
            except:
                pass
            
            return {
                "status": "connected",
                "ws_url": self.ws_url,
                "page_url": page_info.get('url', 'unknown'),
                "page_title": page_info.get('title', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to connect via WebSocket URL {ws_url}: {e}")
            raise
    
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
        
    async def _disconnect_websocket(self):
        """Disconnect current WebSocket connection if exists"""
        if hasattr(self, '_listener_task') and self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            
        if self.ws:
            await self.ws.close()
            self.ws = None
            
        # Clear state
        self.pending_messages.clear()
        self.console_logs.clear()
        self.network_logs.clear()
        if hasattr(self, 'breakpoints'):
            self.breakpoints.clear()
        if hasattr(self, 'scripts'):
            self.scripts.clear()
        if hasattr(self, 'paused_data'):
            self.paused_data = None
            
        logger.info("Disconnected from Chrome DevTools")
    
    async def _connect_websocket(self):
        """Connect to Chrome DevTools WebSocket"""
        # Disconnect any existing connection
        await self._disconnect_websocket()
        
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
        
        # Enable Debugger domain for breakpoints
        try:
            await self._send_command("Debugger.enable")
            logger.info("Successfully enabled Debugger domain")
        except Exception as e:
            logger.warning(f"Could not enable Debugger domain: {e}")
        
        # Set up event handlers
        self.event_handlers['Console.messageAdded'] = self._handle_console_message
        self.event_handlers['Network.requestWillBeSent'] = self._handle_network_request
        self.event_handlers['Network.responseReceived'] = self._handle_network_response
        self.event_handlers['Debugger.paused'] = self._handle_debugger_paused
        self.event_handlers['Debugger.scriptParsed'] = self._handle_script_parsed
        
        # Storage for breakpoints and scripts
        self.breakpoints = {}
        self.scripts = {}
        self.paused_data = None
        self.auto_resume = False
        
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
    
    async def _handle_debugger_paused(self, params: Dict):
        """Handle debugger pause events"""
        self.paused_data = params
        logger.info(f"Debugger paused at {params.get('reason', 'unknown reason')}")
        
        # Auto-resume if configured
        if hasattr(self, 'auto_resume') and self.auto_resume:
            await asyncio.sleep(0.1)  # Brief pause to allow data collection
            await self._send_command("Debugger.resume")
    
    async def _handle_script_parsed(self, params: Dict):
        """Handle script parsed events"""
        script_id = params.get('scriptId')
        url = params.get('url', '')
        if script_id and url:
            self.scripts[script_id] = {
                'url': url,
                'scriptId': script_id,
                'startLine': params.get('startLine', 0),
                'startColumn': params.get('startColumn', 0),
                'endLine': params.get('endLine', 0),
                'endColumn': params.get('endColumn', 0)
            }
        
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
@mcp.tool(description="Connect to a remote Chrome/Chromium instance (e.g., Electron app) via Chrome DevTools Protocol. Use this instead of launching a new Chrome when debugging an already running application.")
async def connect_remote_chrome(host: str = "localhost", port: int = 9222) -> Dict[str, Any]:
    """Connect to a remote Chrome/Chromium instance via CDP"""
    try:
        result = await chrome.connect_remote(host=host, port=port)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to connect to remote Chrome: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Connect directly to Chrome DevTools using a WebSocket debugger URL. This allows switching between different tabs/pages or connecting to specific debugging sessions.")
async def connect_websocket_url(ws_url: str) -> Dict[str, Any]:
    """Connect directly using a WebSocket debugger URL
    
    Args:
        ws_url: WebSocket URL like 'ws://localhost:9222/devtools/page/ABC123'
    """
    try:
        result = await chrome.connect_with_websocket_url(ws_url=ws_url)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to connect via WebSocket URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="List all available Chrome tabs/pages with their WebSocket URLs. Useful for switching between different debugging targets.")
async def list_available_targets(host: str = "localhost", port: int = 9222) -> Dict[str, Any]:
    """List all available debugging targets (tabs/pages)
    
    Args:
        host: Chrome host address
        port: Chrome debugging port
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{host}:{port}/json/list") as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to get targets from Chrome at {host}:{port}")
                targets = await resp.json()
                
        # Format the targets for easier reading
        formatted_targets = []
        for target in targets:
            formatted_targets.append({
                "title": target.get("title", ""),
                "url": target.get("url", ""),
                "type": target.get("type", ""),
                "id": target.get("id", ""),
                "webSocketDebuggerUrl": target.get("webSocketDebuggerUrl", "")
            })
                
        return {
            "success": True,
            "data": {
                "targets": formatted_targets,
                "count": len(formatted_targets),
                "current_ws_url": chrome.ws_url if chrome.ws else None
            }
        }
    except Exception as e:
        logger.error(f"Failed to list targets: {e}")
        return {
            "success": False,
            "error": str(e)
        }


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


@mcp.tool(description="Set a JavaScript breakpoint at a specific location. Can break on DOM events, function calls, or specific code lines.")
async def set_breakpoint(breakpoint_type: str, target: str, options: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Set a breakpoint in JavaScript code.
    
    Args:
        breakpoint_type: Type of breakpoint - 'dom', 'event', 'function', 'xhr', 'line'
        target: Target for the breakpoint (e.g., selector for DOM, function name, URL:line for line)
        options: Additional options like conditions, actions, etc.
    """
    try:
        await chrome.ensure_connected()
        options = options or {}
        
        if breakpoint_type == 'dom':
            # Set DOM breakpoint using event listener breakpoint
            result = await chrome._send_command("DOMDebugger.setEventListenerBreakpoint", {
                "eventName": "click",
                "targetName": target
            })
            
            # Also inject a mutation observer for DOM changes
            await chrome._send_command("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const targetElement = document.querySelector('{target}');
                        if (targetElement) {{
                            targetElement.addEventListener('click', function(e) {{
                                console.log('Breakpoint hit: Click on', e.target);
                                debugger;
                            }}, true);
                        }}
                    }})()
                """
            })
            
        elif breakpoint_type == 'event':
            # Set event listener breakpoint
            result = await chrome._send_command("DOMDebugger.setEventListenerBreakpoint", {
                "eventName": target
            })
            
        elif breakpoint_type == 'function':
            # Set breakpoint on function call
            condition = f"this.name === '{target}' || arguments.callee.name === '{target}'"
            if options.get('condition'):
                condition = f"({condition}) && ({options['condition']})"
                
            await chrome._send_command("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const originalFunc = window['{target}'] || eval('{target}');
                        if (typeof originalFunc === 'function') {{
                            const wrapped = function(...args) {{
                                console.log('Breakpoint: Function {target} called with', args);
                                debugger;
                                return originalFunc.apply(this, args);
                            }};
                            if (window['{target}']) {{
                                window['{target}'] = wrapped;
                            }}
                        }}
                    }})()
                """
            })
            
        elif breakpoint_type == 'xhr':
            # Set XHR/fetch breakpoint
            url_pattern = target
            result = await chrome._send_command("DOMDebugger.setXHRBreakpoint", {
                "url": url_pattern
            })
            
        elif breakpoint_type == 'line':
            # Set line breakpoint
            # Format: "url:lineNumber" or "scriptId:lineNumber"
            parts = target.split(':')
            if len(parts) == 2:
                location = parts[0]
                line = int(parts[1]) - 1  # Convert to 0-based
                
                # Try to find script by URL
                script_id = None
                for sid, script in chrome.scripts.items():
                    if location in script['url'] or sid == location:
                        script_id = sid
                        break
                        
                if script_id:
                    result = await chrome._send_command("Debugger.setBreakpoint", {
                        "location": {
                            "scriptId": script_id,
                            "lineNumber": line
                        },
                        "condition": options.get('condition', '')
                    })
                    
                    if 'breakpointId' in result:
                        chrome.breakpoints[result['breakpointId']] = {
                            'type': 'line',
                            'location': target,
                            'actualLocation': result.get('actualLocation')
                        }
                else:
                    # Set by URL pattern
                    result = await chrome._send_command("Debugger.setBreakpointByUrl", {
                        "lineNumber": line,
                        "urlRegex": f".*{location}.*",
                        "condition": options.get('condition', '')
                    })
        
        return {
            "success": True,
            "data": {
                "type": breakpoint_type,
                "target": target,
                "message": f"Breakpoint set on {breakpoint_type}: {target}"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to set breakpoint: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="List all active breakpoints")
async def list_breakpoints() -> Dict[str, Any]:
    """List all currently set breakpoints"""
    try:
        return {
            "success": True,
            "data": {
                "breakpoints": list(chrome.breakpoints.values()),
                "count": len(chrome.breakpoints)
            }
        }
    except Exception as e:
        logger.error(f"Failed to list breakpoints: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Remove a breakpoint")
async def remove_breakpoint(breakpoint_id: str) -> Dict[str, Any]:
    """Remove a specific breakpoint"""
    try:
        await chrome.ensure_connected()
        
        if breakpoint_id in chrome.breakpoints:
            await chrome._send_command("Debugger.removeBreakpoint", {
                "breakpointId": breakpoint_id
            })
            del chrome.breakpoints[breakpoint_id]
            
        return {
            "success": True,
            "data": {"message": f"Breakpoint {breakpoint_id} removed"}
        }
        
    except Exception as e:
        logger.error(f"Failed to remove breakpoint: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Get information about the paused state when debugger is paused")
async def get_paused_info() -> Dict[str, Any]:
    """Get information about current paused state"""
    try:
        if chrome.paused_data:
            return {
                "success": True,
                "data": chrome.paused_data
            }
        else:
            return {
                "success": True,
                "data": {"message": "Debugger is not currently paused"}
            }
            
    except Exception as e:
        logger.error(f"Failed to get paused info: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Resume execution when debugger is paused")
async def resume_execution() -> Dict[str, Any]:
    """Resume execution from a breakpoint"""
    try:
        await chrome.ensure_connected()
        await chrome._send_command("Debugger.resume")
        chrome.paused_data = None
        
        return {
            "success": True,
            "data": {"message": "Execution resumed"}
        }
        
    except Exception as e:
        logger.error(f"Failed to resume execution: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(description="Step over the current line when debugger is paused")
async def step_over() -> Dict[str, Any]:
    """Step over the current line"""
    try:
        await chrome.ensure_connected()
        await chrome._send_command("Debugger.stepOver")
        
        return {
            "success": True,
            "data": {"message": "Stepped over"}
        }
        
    except Exception as e:
        logger.error(f"Failed to step over: {e}")
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
    logger.info("Tools available: launch_chrome, connect_remote_chrome, connect_websocket_url, list_available_targets, navigate_to, get_dom_tree, query_elements, get_network_logs, get_console_logs, execute_javascript, take_screenshot, get_page_info, set_breakpoint, list_breakpoints, remove_breakpoint, get_paused_info, resume_execution, step_over, close_chrome")
    
    uvicorn.run(app, host=host, port=port)