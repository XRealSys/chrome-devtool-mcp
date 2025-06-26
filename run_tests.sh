#!/bin/bash
# Run tests for Chrome DevTools MCP Server

echo "Running Chrome DevTools MCP Tests..."
echo "===================================="
echo ""

# Check if server is running
if ! curl -s http://localhost:12524/health > /dev/null 2>&1; then
    echo "Starting MCP server..."
    python3 src/chrome_devtools_mcp.py &
    SERVER_PID=$!
    sleep 3
    STARTED_SERVER=true
else
    echo "MCP server already running"
    STARTED_SERVER=false
fi

# Run tests
echo "Running test suite..."
python3 tests/test_mcp_tools.py

# Clean up
if [ "$STARTED_SERVER" = true ]; then
    echo ""
    echo "Stopping MCP server..."
    kill $SERVER_PID 2>/dev/null
fi

echo ""
echo "Tests completed!"