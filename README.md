# ORAX Eye

**See and control any macOS app through the Accessibility API.**
**The screen reader for AI agents.**

**通过 macOS 辅助功能 API 感知和控制任何应用。AI 的屏幕阅读器。**

[![PyPI](https://img.shields.io/pypi/v/orax-eye)](https://pypi.org/project/orax-eye/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io/)

---

AI agents today take screenshots and spend $0.02 per look. ORAX Eye reads the screen the way blind users do — through the Accessibility API. Same information, zero cost, 50ms instead of 3 seconds.

当前的 AI agent 通过截屏来"看"屏幕，每次花费 $0.02。ORAX Eye 用苹果为盲人开发的辅助功能 API 来读屏 — 同样的信息，零成本，50ms 而不是 3 秒。

## Comparison / 对比

| | Screenshot approach | ORAX Eye |
|---|---|---|
| **Cost per read** | ~$0.01-0.03 | **$0.00** |
| **Latency** | 2-5 seconds | **30-80ms** |
| **Output** | Pixels (needs vision model) | **Structured JSON** |
| **Accuracy** | Guesses coordinates | **Exact positions from OS** |
| **Background apps** | No (needs visible window) | **Yes** |
| **Monthly cost @1000 reads/day** | $300-900 | **$0** |

## Install / 安装

```bash
pip install orax-eye
```

## Quick Start / 快速开始

```python
from orax_eye import OraxEye

eye = OraxEye()

# What's running? / 哪些应用在运行？
print(eye.list_apps())

# What's in Safari? / Safari 里有什么？
elements = eye.scan_app("Safari")
for el in elements[:5]:
    print(f"  {el['role']}: {el['title']} ({el['x']},{el['y']})")

# Click a button / 点击按钮
eye.click_element("Safari", "Downloads")

# Type text / 输入文字
eye.type_text("hello world")

# Get the full picture / 获取完整屏幕状态
screen = eye.get_screen_map()
for w in screen["windows"]:
    print(f"  {w['app']}: {w['title']} {w['width']}x{w['height']}")
```

## Use as MCP Server / 作为 MCP 服务器

Works with Claude Code, Cursor, Claude Desktop, and any MCP-compatible client.

兼容 Claude Code、Cursor、Claude Desktop 以及所有 MCP 客户端。

```bash
pip install "orax-eye[mcp]"
python -m orax_eye
```

### Claude Desktop / Cursor config:

```json
{
  "mcpServers": {
    "orax-eye": {
      "command": "python3",
      "args": ["-m", "orax_eye.mcp_server"]
    }
  }
}
```

### Available MCP Tools / 可用的 MCP 工具

| Tool | Description |
|---|---|
| `check_permission` | Check Accessibility permission status |
| `list_apps` | List all running GUI apps |
| `activate_app` | Bring an app to the foreground |
| `scan_app` | Read an app's full UI tree |
| `find_elements` | Search for specific UI elements |
| `click_element` | Find and click an element |
| `type_text` | Type text at cursor position |
| `press_key` | Press special keys (return, tab, etc.) |
| `set_value` | Set a text field's value directly |
| `focus_element` | Focus an element (for text input) |
| `get_screen_map` | Get complete screen state |
| `key_combo` | Press keyboard shortcuts (Cmd+C, Cmd+V, etc.) |
| `scroll` | Scroll at a screen position |
| `right_click` | Right-click to open context menu |
| `double_click` | Double-click at coordinates |
| `get_clipboard` | Read clipboard content |
| `set_clipboard` | Write to clipboard |
| `get_focused_app` | Get the currently focused app |

## Permissions / 权限设置

ORAX Eye requires macOS Accessibility permission.

ORAX Eye 需要 macOS 辅助功能权限。

1. Open **System Settings > Privacy & Security > Accessibility**
2. Click **"+"** and add your terminal app (Terminal, iTerm2, VS Code, Cursor)
3. Toggle the switch **ON**

打开 **系统设置 > 隐私与安全 > 辅助功能**，点 **"+"** 添加你的终端应用并打开开关。

## How It Works / 工作原理

macOS exposes every UI element through the [Accessibility API](https://developer.apple.com/documentation/accessibility) — originally built for VoiceOver screen reader. Every button, text field, menu item, and label is in a tree structure with:

- **Role** — what it is (button, text field, menu)
- **Title** — display text
- **Position** — exact x, y coordinates
- **Actions** — what you can do (click, press, focus)

ORAX Eye reads this tree directly from the OS. No screenshots, no pixels, no vision models. Just structured data with exact coordinates.

macOS 通过[辅助功能 API](https://developer.apple.com/documentation/accessibility) 暴露了每个 UI 元素 — 这是为 VoiceOver 屏幕阅读器开发的。每个按钮、文本框、菜单项都在一个树形结构中，包含角色、标题、精确坐标和可用操作。ORAX Eye 直接从操作系统读取这棵树，不截屏，不用视觉模型。

## API Reference

### Discovery

- `check_permission()` — Check Accessibility permission
- `list_apps()` — List running GUI apps
- `get_screen_map()` — Full screen state with all windows

### Reading

- `scan_app(app_name, max_depth=3, max_elements=200)` — Scan UI tree
- `find_elements(app_name, query, role, identifier)` — Find matching elements
- `find_element(app_name, query)` — Find first match

### Actions

- `click(x, y)` — Click at coordinates
- `click_element(app_name, query)` — Find and click
- `right_click(x, y)` — Right-click (context menu)
- `double_click(x, y)` — Double-click
- `scroll(x, y, direction, amount)` — Scroll at position
- `type_text(text)` — Type text (Unicode/CJK supported)
- `press_key(key)` — Press special key
- `key_combo(*keys)` — Keyboard shortcut (e.g. `key_combo("cmd", "c")`)
- `set_value(app_name, query, value)` — Set text field value
- `focus_element(app_name, query)` — Focus an element
- `activate_app(app_name)` — Bring app to foreground
- `get_clipboard()` — Read clipboard
- `set_clipboard(text)` — Write clipboard
- `get_focused_app()` — Get frontmost app

## Roadmap

- ✅ macOS (Accessibility API)
- 🔜 Android (Accessibility Service via ADB)
- 🔜 Windows (UI Automation)
- 🔜 Linux (AT-SPI)

## Requirements / 系统要求

- macOS 13+ (Ventura or later)
- Python 3.10+

## Contact

- GitHub: [@oraxhq](https://github.com/oraxhq)
- X: [@oraxhq](https://x.com/oraxhq)

## License

MIT
