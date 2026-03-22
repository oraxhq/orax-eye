"""ORAX Eye — See and control any macOS app through the Accessibility API.

The screen reader for AI agents. Uses the same API that lets blind users
navigate their Mac — now repurposed as AI's eyes and hands.

Zero screenshots, zero tokens, millisecond response.
"""

import time
import subprocess
from dataclasses import dataclass, field

# --- pyobjc imports (macOS only) ---
try:
    from ApplicationServices import (
        AXUIElementCreateSystemWide,
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
        AXUIElementCopyActionNames,
        AXUIElementPerformAction,
        AXUIElementSetAttributeValue,
        AXIsProcessTrusted,
    )
    from Quartz import (
        CGEventCreateMouseEvent,
        CGEventPost,
        CGEventCreateScrollWheelEvent2,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGEventRightMouseDown,
        kCGEventRightMouseUp,
        kCGHIDEventTap,
        kCGEventMouseMoved,
        kCGScrollEventUnitLine,
        CGPointMake,
    )
    import Cocoa

    _HAS_PYOBJC = True
except ImportError:
    _HAS_PYOBJC = False


# --- Data types ---

@dataclass
class UIElement:
    """A single UI element from the Accessibility tree."""
    role: str = ""
    title: str = ""
    value: str = ""
    identifier: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    enabled: bool = True
    focused: bool = False
    actions: list[str] = field(default_factory=list)
    children_count: int = 0
    app_name: str = ""
    _ref: object = None  # AXUIElement reference (not serializable)

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "title": self.title,
            "value": self.value,
            "identifier": self.identifier,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "enabled": self.enabled,
            "focused": self.focused,
            "actions": self.actions,
            "children_count": self.children_count,
            "app_name": self.app_name,
        }


@dataclass
class AppWindow:
    """An application window."""
    app_name: str
    pid: int
    window_title: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    focused: bool = False


# --- Core Eye class ---

class OraxEye:
    """See and control any macOS app through the Accessibility API.

    Uses the same API that powers VoiceOver for blind users.
    Reads the full UI tree — every button, text field, menu item —
    with exact positions, roles, and available actions.

    No screenshots. No vision models. No tokens. Just the truth.
    """

    def __init__(self):
        if not _HAS_PYOBJC:
            raise RuntimeError(
                "pyobjc not installed. Run: pip install pyobjc-framework-ApplicationServices "
                "pyobjc-framework-Quartz pyobjc-framework-Cocoa"
            )
        self._system = AXUIElementCreateSystemWide()
        self._app_cache: dict[str, int] = {}  # app_name -> pid

    # ------------------------------------------------------------------
    # Permission check
    # ------------------------------------------------------------------

    def check_permission(self, prompt: bool = False) -> bool:
        """Check if this process has macOS Accessibility permission.

        Args:
            prompt: If True and permission not granted, automatically show
                    the macOS system dialog asking user to grant access.

        If False, grant access in: System Settings > Privacy & Security > Accessibility
        """
        if prompt:
            try:
                from ApplicationServices import AXIsProcessTrustedWithOptions
                options = {
                    "AXTrustedCheckOptionPrompt": True
                }
                return bool(AXIsProcessTrustedWithOptions(options))
            except ImportError:
                pass
        return bool(AXIsProcessTrusted())

    # ------------------------------------------------------------------
    # App discovery
    # ------------------------------------------------------------------

    def list_apps(self) -> list[dict]:
        """List all running GUI applications with their names and PIDs."""
        workspace = Cocoa.NSWorkspace.sharedWorkspace()
        apps = workspace.runningApplications()
        result = []
        for app in apps:
            if app.activationPolicy() == 0:  # NSApplicationActivationPolicyRegular
                name = app.localizedName()
                pid = app.processIdentifier()
                self._app_cache[name] = pid
                result.append({"name": name, "pid": pid})
        return result

    def _get_pid(self, app_name: str) -> int | None:
        """Get PID for an app by name (case-insensitive partial match)."""
        if not self._app_cache:
            self.list_apps()

        app_lower = app_name.lower()
        # Exact match first
        for name, pid in self._app_cache.items():
            if name.lower() == app_lower:
                return pid
        # Partial match
        for name, pid in self._app_cache.items():
            if app_lower in name.lower():
                return pid
        # Refresh cache and retry
        self.list_apps()
        for name, pid in self._app_cache.items():
            if app_lower in name.lower():
                return pid
        return None

    def _get_ax_app(self, app_name: str):
        """Get AXUIElement for an app."""
        pid = self._get_pid(app_name)
        if pid is None:
            return None
        return AXUIElementCreateApplication(pid)

    # ------------------------------------------------------------------
    # Reading the UI tree
    # ------------------------------------------------------------------

    def _read_element(self, element, app_name: str = "", depth: int = 0) -> UIElement | None:
        """Read a single AXUIElement into a UIElement dataclass."""
        try:
            ui = UIElement(app_name=app_name, _ref=element)

            # Role
            err, val = AXUIElementCopyAttributeValue(element, "AXRole", None)
            if err == 0 and val:
                ui.role = str(val)

            # Title
            err, val = AXUIElementCopyAttributeValue(element, "AXTitle", None)
            if err == 0 and val:
                ui.title = str(val)

            # Value
            err, val = AXUIElementCopyAttributeValue(element, "AXValue", None)
            if err == 0 and val:
                ui.value = str(val)[:500]

            # Identifier
            err, val = AXUIElementCopyAttributeValue(element, "AXIdentifier", None)
            if err == 0 and val:
                ui.identifier = str(val)

            # Position
            err, val = AXUIElementCopyAttributeValue(element, "AXPosition", None)
            if err == 0 and val:
                try:
                    from ApplicationServices import AXValueGetValue, kAXValueTypeCGPoint
                    success, point = AXValueGetValue(val, kAXValueTypeCGPoint, None)
                    if success:
                        ui.x, ui.y = int(point.x), int(point.y)
                except Exception:
                    pass

            # Size
            err, val = AXUIElementCopyAttributeValue(element, "AXSize", None)
            if err == 0 and val:
                try:
                    from ApplicationServices import AXValueGetValue, kAXValueTypeCGSize
                    success, size = AXValueGetValue(val, kAXValueTypeCGSize, None)
                    if success:
                        ui.width, ui.height = int(size.width), int(size.height)
                except Exception:
                    pass

            # Enabled
            err, val = AXUIElementCopyAttributeValue(element, "AXEnabled", None)
            if err == 0 and val is not None:
                ui.enabled = bool(val)

            # Focused
            err, val = AXUIElementCopyAttributeValue(element, "AXFocused", None)
            if err == 0 and val is not None:
                ui.focused = bool(val)

            # Actions
            err, actions = AXUIElementCopyActionNames(element, None)
            if err == 0 and actions:
                ui.actions = list(actions)

            # Children count
            err, val = AXUIElementCopyAttributeValue(element, "AXChildren", None)
            if err == 0 and val:
                ui.children_count = len(val)

            return ui
        except Exception:
            return None

    def _get_children(self, element) -> list:
        """Get children AXUIElements."""
        err, children = AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and children:
            return list(children)
        return []

    def _get_windows(self, ax_app) -> list:
        """Get window AXUIElements for an app."""
        err, windows = AXUIElementCopyAttributeValue(ax_app, "AXWindows", None)
        if err == 0 and windows:
            return list(windows)
        return []

    def scan_app(self, app_name: str, max_depth: int = 3, max_elements: int = 200) -> list[dict]:
        """Scan an app's UI tree and return all elements.

        Returns a flat list of element dicts with role, title, value,
        position, size, and available actions.
        """
        ax_app = self._get_ax_app(app_name)
        if not ax_app:
            return []

        results = []
        windows = self._get_windows(ax_app)

        def _recurse(el, depth):
            if depth > max_depth or len(results) >= max_elements:
                return
            ui = self._read_element(el, app_name=app_name, depth=depth)
            if ui and (ui.role or ui.title or ui.value):
                results.append(ui)
            for child in self._get_children(el):
                _recurse(child, depth + 1)

        for win in windows:
            _recurse(win, 0)

        return [e.to_dict() for e in results]

    # ------------------------------------------------------------------
    # Finding elements
    # ------------------------------------------------------------------

    def find_elements(
        self,
        app_name: str,
        query: str = "",
        role: str = "",
        identifier: str = "",
        max_depth: int = 5,
        max_results: int = 20,
    ) -> list[UIElement]:
        """Find elements matching criteria in an app's UI tree.

        Args:
            app_name: Application name (case-insensitive partial match)
            query: Text to match against title, value, or identifier
            role: Filter by AX role (e.g. "AXButton", "AXTextField")
            identifier: Filter by exact identifier
            max_depth: Maximum tree depth to search
            max_results: Maximum number of results to return
        """
        ax_app = self._get_ax_app(app_name)
        if not ax_app:
            return []

        matches = []
        query_lower = query.lower() if query else ""

        def _search(el, depth):
            if depth > max_depth or len(matches) >= max_results:
                return
            ui = self._read_element(el, app_name=app_name, depth=depth)
            if ui:
                match = True
                if query_lower:
                    text = f"{ui.title} {ui.value} {ui.identifier}".lower()
                    match = query_lower in text
                if role and ui.role != role:
                    match = False
                if identifier and ui.identifier != identifier:
                    match = False
                if match and (ui.title or ui.value or ui.identifier):
                    matches.append(ui)
            for child in self._get_children(el):
                _search(child, depth + 1)

        for win in self._get_windows(ax_app):
            _search(win, 0)

        return matches

    def find_element(self, app_name: str, query: str, **kwargs) -> UIElement | None:
        """Find the first matching element."""
        results = self.find_elements(app_name, query=query, max_results=1, **kwargs)
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Actions: click, type, press
    # ------------------------------------------------------------------

    def click(self, x: int, y: int):
        """Click at screen coordinates using CGEvent."""
        point = CGPointMake(float(x), float(y))
        move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
        CGEventPost(kCGHIDEventTap, move)
        time.sleep(0.05)
        down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
        CGEventPost(kCGHIDEventTap, down)
        time.sleep(0.05)
        up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
        CGEventPost(kCGHIDEventTap, up)

    def click_element(self, app_name: str, query: str, **kwargs) -> dict:
        """Find an element and click it. Tries AXPress first, falls back to coordinates."""
        el = self.find_element(app_name, query, **kwargs)
        if not el:
            return {"ok": False, "error": f"Element not found: {query}"}

        if el._ref and "AXPress" in el.actions:
            err = AXUIElementPerformAction(el._ref, "AXPress")
            if err == 0:
                return {"ok": True, "method": "AXPress", "element": el.to_dict()}

        self.click(el.center_x, el.center_y)
        return {"ok": True, "method": "coordinate_click", "element": el.to_dict()}

    def focus_element(self, app_name: str, query: str, **kwargs) -> dict:
        """Find an element and focus it (useful for text fields before typing)."""
        el = self.find_element(app_name, query, **kwargs)
        if not el:
            return {"ok": False, "error": f"Element not found: {query}"}

        if el._ref:
            AXUIElementSetAttributeValue(el._ref, "AXFocused", True)
            return {"ok": True, "element": el.to_dict()}
        return {"ok": False, "error": "No element reference"}

    def type_text(self, text: str):
        """Type text at current cursor position. Handles Unicode/CJK via AppleScript."""
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        script = f'tell application "System Events" to keystroke "{escaped}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)

    def press_key(self, key: str):
        """Press a special key (return, tab, escape, delete, arrows, etc.)."""
        key_map = {
            "return": 36, "enter": 36,
            "tab": 48,
            "escape": 53, "esc": 53,
            "delete": 51, "backspace": 51,
            "space": 49,
            "up": 126, "down": 125, "left": 123, "right": 124,
        }
        key_lower = key.lower()
        if key_lower in key_map:
            script = f'tell application "System Events" to key code {key_map[key_lower]}'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        else:
            self.type_text(key)

    def key_combo(self, *keys: str):
        """Press a keyboard shortcut (e.g. key_combo("cmd", "c") for Cmd+C).

        Supports: cmd/command, ctrl/control, alt/option, shift, plus any key.
        Examples:
            key_combo("cmd", "c")       # Copy
            key_combo("cmd", "v")       # Paste
            key_combo("cmd", "z")       # Undo
            key_combo("cmd", "shift", "s")  # Save As
        """
        modifier_map = {
            "cmd": "command down", "command": "command down",
            "ctrl": "control down", "control": "control down",
            "alt": "option down", "option": "option down",
            "shift": "shift down",
        }
        modifiers = []
        key_char = ""
        for k in keys:
            k_lower = k.lower()
            if k_lower in modifier_map:
                modifiers.append(modifier_map[k_lower])
            else:
                key_char = k
        if not key_char:
            return
        mod_str = ", ".join(modifiers)
        escaped = key_char.replace("\\", "\\\\").replace('"', '\\"')
        if mod_str:
            script = f'tell application "System Events" to keystroke "{escaped}" using {{{mod_str}}}'
        else:
            script = f'tell application "System Events" to keystroke "{escaped}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)

    def scroll(self, x: int, y: int, direction: str = "down", amount: int = 3):
        """Scroll at a screen position.

        Args:
            x: Screen x coordinate
            y: Screen y coordinate
            direction: "up", "down", "left", or "right"
            amount: Number of scroll units (default 3)
        """
        point = CGPointMake(float(x), float(y))
        # Move mouse to position first
        move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
        CGEventPost(kCGHIDEventTap, move)
        time.sleep(0.05)

        if direction in ("up", "down"):
            dy = amount if direction == "up" else -amount
            scroll_event = CGEventCreateScrollWheelEvent2(
                None, kCGScrollEventUnitLine, 1, dy, 0
            )
        else:
            dx = amount if direction == "right" else -amount
            scroll_event = CGEventCreateScrollWheelEvent2(
                None, kCGScrollEventUnitLine, 2, 0, dx
            )
        CGEventPost(kCGHIDEventTap, scroll_event)

    def right_click(self, x: int, y: int):
        """Right-click at screen coordinates (opens context menu)."""
        point = CGPointMake(float(x), float(y))
        move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
        CGEventPost(kCGHIDEventTap, move)
        time.sleep(0.05)
        down = CGEventCreateMouseEvent(None, kCGEventRightMouseDown, point, 0)
        CGEventPost(kCGHIDEventTap, down)
        time.sleep(0.05)
        up = CGEventCreateMouseEvent(None, kCGEventRightMouseUp, point, 0)
        CGEventPost(kCGHIDEventTap, up)

    def double_click(self, x: int, y: int):
        """Double-click at screen coordinates."""
        point = CGPointMake(float(x), float(y))
        move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
        CGEventPost(kCGHIDEventTap, move)
        time.sleep(0.05)
        for _ in range(2):
            down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
            CGEventPost(kCGHIDEventTap, down)
            time.sleep(0.02)
            up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
            CGEventPost(kCGHIDEventTap, up)
            time.sleep(0.05)

    def get_clipboard(self) -> str:
        """Read the current clipboard content."""
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        return result.stdout

    def set_clipboard(self, text: str):
        """Set the clipboard content."""
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), timeout=5)

    def get_focused_app(self) -> dict:
        """Get the currently focused (frontmost) application."""
        workspace = Cocoa.NSWorkspace.sharedWorkspace()
        app = workspace.frontmostApplication()
        if app:
            return {
                "name": app.localizedName(),
                "pid": app.processIdentifier(),
                "bundle_id": str(app.bundleIdentifier() or ""),
            }
        return {"name": "", "pid": 0, "bundle_id": ""}

    def set_value(self, app_name: str, query: str, value: str, **kwargs) -> dict:
        """Set the value of a text field directly via Accessibility API."""
        el = self.find_element(app_name, query, **kwargs)
        if not el:
            return {"ok": False, "error": f"Element not found: {query}"}
        if el._ref:
            err = AXUIElementSetAttributeValue(el._ref, "AXValue", value)
            if err == 0:
                return {"ok": True, "element": el.to_dict()}
            # Fallback: focus and type
            AXUIElementSetAttributeValue(el._ref, "AXFocused", True)
            time.sleep(0.1)
            self.type_text(value)
            return {"ok": True, "method": "focus_and_type", "element": el.to_dict()}
        return {"ok": False, "error": "Cannot set value"}

    # ------------------------------------------------------------------
    # App control
    # ------------------------------------------------------------------

    def activate_app(self, app_name: str) -> dict:
        """Bring an application to the foreground."""
        workspace = Cocoa.NSWorkspace.sharedWorkspace()
        apps = workspace.runningApplications()
        app_lower = app_name.lower()
        for app in apps:
            if app.activationPolicy() == 0:
                name = app.localizedName()
                if name and app_lower in name.lower():
                    app.activateWithOptions_(Cocoa.NSApplicationActivateIgnoringOtherApps)
                    time.sleep(0.3)
                    return {"ok": True, "app": name, "pid": app.processIdentifier()}
        return {"ok": False, "error": f"App not found: {app_name}"}

    # ------------------------------------------------------------------
    # Screen map
    # ------------------------------------------------------------------

    def get_screen_map(self) -> dict:
        """Get a complete map of everything visible on screen.

        Returns all running apps, their windows with positions and sizes,
        and which window is currently focused.
        """
        apps = self.list_apps()
        windows = []
        for app_info in apps:
            app_name = app_info["name"]
            ax_app = AXUIElementCreateApplication(app_info["pid"])
            for win in self._get_windows(ax_app):
                win_el = self._read_element(win, app_name=app_name)
                if win_el:
                    windows.append({
                        "app": app_name,
                        "pid": app_info["pid"],
                        "title": win_el.title,
                        "x": win_el.x,
                        "y": win_el.y,
                        "width": win_el.width,
                        "height": win_el.height,
                        "focused": win_el.focused,
                    })
        return {
            "timestamp": time.time(),
            "apps": apps,
            "windows": windows,
            "permission": self.check_permission(),
        }


# --- Singleton ---
_eye: OraxEye | None = None


def get_eye() -> OraxEye:
    """Get or create the global OraxEye instance."""
    global _eye
    if _eye is None:
        _eye = OraxEye()
    return _eye
