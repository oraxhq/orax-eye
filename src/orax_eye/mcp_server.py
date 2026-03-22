"""ORAX Eye MCP Server — Expose macOS Accessibility API as MCP tools.

Lets AI agents (Claude Code, Cursor, etc.) see and control any macOS app
through the Model Context Protocol.

Usage:
    python -m orax_eye
    # or
    orax-eye
"""

from mcp.server.fastmcp import FastMCP

from .core import OraxEye

mcp = FastMCP(
    "orax-eye",
    instructions="See and control any macOS app through the Accessibility API. "
    "Zero screenshots, zero tokens, millisecond response.",
)

eye = OraxEye()


@mcp.tool()
def check_permission() -> dict:
    """Check if this process has macOS Accessibility permission.

    If not permitted, the user needs to grant access in:
    System Settings > Privacy & Security > Accessibility
    """
    ok = eye.check_permission()
    return {
        "permitted": ok,
        "message": "OK" if ok else (
            "Not permitted. Grant access in: "
            "System Settings > Privacy & Security > Accessibility"
        ),
    }


@mcp.tool()
def list_apps() -> dict:
    """List all running GUI applications with their names and PIDs.

    Returns every app visible in the Dock or app switcher.
    """
    apps = eye.list_apps()
    return {"apps": apps, "count": len(apps)}


@mcp.tool()
def activate_app(app_name: str) -> dict:
    """Bring an application to the foreground.

    Args:
        app_name: Application name (case-insensitive, partial match supported).
                  Examples: "Safari", "Chrome", "Terminal", "Finder"
    """
    return eye.activate_app(app_name)


@mcp.tool()
def scan_app(app_name: str, max_depth: int = 3, max_elements: int = 200) -> dict:
    """Scan an app's UI tree and return all visible elements.

    Returns every button, text field, menu item, label — with exact positions,
    roles, and available actions. This is the primary "seeing" tool.

    Args:
        app_name: Application name (case-insensitive, partial match)
        max_depth: How deep to traverse the UI tree (default 3)
        max_elements: Maximum elements to return (default 200)
    """
    try:
        elements = eye.scan_app(app_name, max_depth=max_depth, max_elements=max_elements)
        return {"elements": elements, "count": len(elements)}
    except Exception as e:
        return {"error": str(e), "elements": [], "count": 0}


@mcp.tool()
def find_elements(
    app_name: str,
    query: str = "",
    role: str = "",
    max_results: int = 20,
) -> dict:
    """Find UI elements matching criteria in an app.

    Search by text content, AX role, or both. More targeted than scan_app.

    Args:
        app_name: Application name
        query: Text to match against element title, value, or identifier
        role: Filter by AX role (e.g. "AXButton", "AXTextField", "AXStaticText")
        max_results: Maximum results to return (default 20)
    """
    try:
        elements = eye.find_elements(
            app_name, query=query, role=role, max_results=max_results
        )
        return {
            "elements": [e.to_dict() for e in elements],
            "count": len(elements),
        }
    except Exception as e:
        return {"error": str(e), "elements": [], "count": 0}


@mcp.tool()
def click_element(app_name: str, query: str, role: str = "") -> dict:
    """Find a UI element and click it.

    Tries the native AXPress action first (most reliable), falls back
    to clicking at the element's center coordinates.

    Args:
        app_name: Application name
        query: Text to identify the element (matches title, value, identifier)
        role: Optional AX role filter (e.g. "AXButton")
    """
    kwargs = {}
    if role:
        kwargs["role"] = role
    return eye.click_element(app_name, query, **kwargs)


@mcp.tool()
def type_text(text: str) -> dict:
    """Type text at the current cursor position.

    Handles Unicode, CJK characters, and emoji via AppleScript.
    Make sure an input field is focused before calling this.

    Args:
        text: The text to type
    """
    try:
        eye.type_text(text)
        return {"ok": True, "typed": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def press_key(key: str) -> dict:
    """Press a special key.

    Args:
        key: Key name — one of: return, tab, escape, delete, space,
             up, down, left, right. Or any single character.
    """
    try:
        eye.press_key(key)
        return {"ok": True, "key": key}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def get_screen_map() -> dict:
    """Get a complete map of everything visible on screen.

    Returns all running apps, their windows with positions and sizes,
    and which window is currently focused. The full picture.
    """
    return eye.get_screen_map()


@mcp.tool()
def set_value(app_name: str, query: str, value: str, role: str = "") -> dict:
    """Set the value of a text field directly.

    Finds a text field and sets its value through the Accessibility API.
    More reliable than type_text for filling form fields.

    Args:
        app_name: Application name
        query: Text to identify the element
        value: The value to set
        role: Optional AX role filter
    """
    kwargs = {}
    if role:
        kwargs["role"] = role
    return eye.set_value(app_name, query, value, **kwargs)


@mcp.tool()
def focus_element(app_name: str, query: str, role: str = "") -> dict:
    """Find an element and focus it.

    Useful for focusing text fields before using type_text.

    Args:
        app_name: Application name
        query: Text to identify the element
        role: Optional AX role filter
    """
    kwargs = {}
    if role:
        kwargs["role"] = role
    return eye.focus_element(app_name, query, **kwargs)


@mcp.tool()
def key_combo(keys: list[str]) -> dict:
    """Press a keyboard shortcut.

    Send modifier+key combinations like Cmd+C, Cmd+V, Cmd+Z.

    Args:
        keys: List of keys to press together.
              Examples: ["cmd", "c"] for copy, ["cmd", "shift", "s"] for save-as.
              Modifiers: cmd, ctrl, alt/option, shift
    """
    try:
        eye.key_combo(*keys)
        return {"ok": True, "combo": "+".join(keys)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def scroll(x: int, y: int, direction: str = "down", amount: int = 3) -> dict:
    """Scroll at a screen position.

    Args:
        x: Screen x coordinate
        y: Screen y coordinate
        direction: "up", "down", "left", or "right"
        amount: Scroll units (default 3)
    """
    try:
        eye.scroll(x, y, direction, amount)
        return {"ok": True, "direction": direction, "amount": amount}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def right_click(x: int, y: int) -> dict:
    """Right-click at screen coordinates to open a context menu.

    Args:
        x: Screen x coordinate
        y: Screen y coordinate
    """
    try:
        eye.right_click(x, y)
        return {"ok": True, "x": x, "y": y}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def double_click(x: int, y: int) -> dict:
    """Double-click at screen coordinates.

    Args:
        x: Screen x coordinate
        y: Screen y coordinate
    """
    try:
        eye.double_click(x, y)
        return {"ok": True, "x": x, "y": y}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def get_clipboard() -> dict:
    """Read the current clipboard content."""
    text = eye.get_clipboard()
    return {"text": text}


@mcp.tool()
def set_clipboard(text: str) -> dict:
    """Set the clipboard content.

    Args:
        text: Text to copy to clipboard
    """
    try:
        eye.set_clipboard(text)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def get_focused_app() -> dict:
    """Get the currently focused (frontmost) application.

    Returns the app name, PID, and bundle ID.
    """
    return eye.get_focused_app()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
