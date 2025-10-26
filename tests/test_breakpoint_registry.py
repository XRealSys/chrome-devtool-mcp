import pytest

from src.chrome_devtools_mcp import chrome, set_breakpoint


@pytest.fixture(autouse=True)
def restore_chrome_state():
    """Ensure global chrome state is restored after each test."""
    had_breakpoints = hasattr(chrome, "breakpoints")
    if had_breakpoints:
        original_breakpoints = chrome.breakpoints.copy()
    else:
        chrome.breakpoints = {}
        original_breakpoints = None

    had_scripts = hasattr(chrome, "scripts")
    if had_scripts:
        original_scripts = chrome.scripts.copy()
    else:
        chrome.scripts = {}
        original_scripts = None

    original_domains = chrome.enabled_domains.copy()

    try:
        yield
    finally:
        chrome.enabled_domains.clear()
        chrome.enabled_domains.update(original_domains)

        if had_breakpoints:
            chrome.breakpoints.clear()
            chrome.breakpoints.update(original_breakpoints)
        else:
            delattr(chrome, "breakpoints")

        if had_scripts:
            chrome.scripts.clear()
            chrome.scripts.update(original_scripts)
        else:
            delattr(chrome, "scripts")


@pytest.mark.asyncio
async def test_url_based_logpoint_persisted(monkeypatch):
    """Logpoints created via setBreakpointByUrl should be persisted with metadata."""

    async def noop():
        return None

    expected_locations = [{"scriptId": "123", "lineNumber": 9}]

    async def fake_send_command(method, params):
        assert method == "Debugger.setBreakpointByUrl"
        assert params["lineNumber"] == 9
        assert params["urlRegex"] == ".*app.js.*"
        assert params.get("condition", "").startswith("console.log")
        return {
            "breakpointId": "url-bp-1",
            "locations": expected_locations,
        }

    monkeypatch.setattr(chrome, "ensure_connected", noop)
    monkeypatch.setattr(chrome, "_send_command", fake_send_command)

    chrome.enabled_domains["Debugger"] = True
    chrome.scripts.clear()
    chrome.breakpoints.clear()

    options = {"pause": False, "logMessage": "Log entry"}

    result = await set_breakpoint("logpoint", "app.js:10", options)

    assert result["success"]
    assert "url-bp-1" in chrome.breakpoints

    stored = chrome.breakpoints["url-bp-1"]
    assert stored["type"] == "logpoint"
    assert stored["location"] == "app.js:10"
    assert stored["logMessage"] == "Log entry"
    assert stored["actualLocation"] == expected_locations
