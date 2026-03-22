#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

echo -e "${BLUE}=== ORAX Eye Installer ===${NC}"
echo "See and control any macOS app through the Accessibility API."
echo ""

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: ORAX Eye requires macOS${NC}"
    exit 1
fi

# Find Python 3.10+
PYTHON=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo -e "${RED}Error: Python 3.10+ required. Install: brew install python@3.12${NC}"
    exit 1
fi
echo -e "${GREEN}Python: $PYTHON ($($PYTHON --version))${NC}"

# Install
echo ""
echo -e "${BLUE}Installing orax-eye...${NC}"
$PYTHON -m pip install --upgrade "orax-eye[mcp]"

# Verify
echo ""
$PYTHON -c "from orax_eye import OraxEye; print('  Import: OK')"

# Check Accessibility permission
echo ""
PERM=$($PYTHON -c "
from ApplicationServices import AXIsProcessTrusted
print('granted' if AXIsProcessTrusted() else 'denied')
" 2>/dev/null || echo "error")

if [[ "$PERM" == "granted" ]]; then
    echo -e "${GREEN}Accessibility permission: GRANTED${NC}"
else
    echo -e "${YELLOW}Accessibility permission: NOT GRANTED${NC}"
    echo ""
    echo "  Grant access in:"
    echo "  System Settings > Privacy & Security > Accessibility"
    echo "  Add your terminal app (Terminal, iTerm2, VS Code, Cursor)"
    echo ""
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
fi

# Claude Desktop config hint
echo ""
echo -e "${BLUE}MCP Server config:${NC}"
echo ""
echo "  Add to claude_desktop_config.json or .claude/settings.json:"
echo ""
echo '  "mcpServers": {'
echo '    "orax-eye": {'
echo '      "command": "'"$PYTHON"'",'
echo '      "args": ["-m", "orax_eye.mcp_server"]'
echo '    }'
echo '  }'

echo ""
echo -e "${GREEN}=== Done! ===${NC}"
echo ""
echo "  Quick test:  $PYTHON -c \"from orax_eye import OraxEye; e = OraxEye(); print(e.list_apps())\""
echo "  MCP server:  $PYTHON -m orax_eye.mcp_server"
echo ""
