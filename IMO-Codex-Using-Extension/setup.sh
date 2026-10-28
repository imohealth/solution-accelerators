#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Convert Git Bash paths (/d/Users/...) to Windows paths (D:/Users/...) for Python
WIN_SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)
MCP_JSON="$SCRIPT_DIR/.mcp.json"
WIN_MCP_JSON="$WIN_SCRIPT_DIR/.mcp.json"
CODEX_CONFIG="$HOME/.codex/config.toml"
BASHRC="$HOME/.bashrc"

echo "============================================"
echo "  IMO Health Codex Plugin — Setup"
echo "============================================"
echo ""

# Check prerequisites
if ! command -v codex &> /dev/null; then
    echo "ERROR: 'codex' CLI not found. Install it first."
    exit 1
fi

if [ ! -f "$MCP_JSON" ]; then
    echo "ERROR: .mcp.json not found in $SCRIPT_DIR"
    exit 1
fi

# Read server name and URL dynamically from .mcp.json (use Windows path for Python)
SERVER_NAME=$(python -c "import json; d=json.load(open('$WIN_MCP_JSON')); print(list(d['mcpServers'].keys())[0])")
SERVER_URL=$(python -c "import json; d=json.load(open('$WIN_MCP_JSON')); print(list(d['mcpServers'].values())[0]['url'])")

echo "Detected MCP server:"
echo "  Name: $SERVER_NAME"
echo "  URL:  $SERVER_URL"
echo ""

# Step 1 — Register marketplace
echo "[1/4] Registering marketplace..."
codex plugin marketplace add "$SCRIPT_DIR"
echo "  Done."
echo ""

# Step 2 — Install plugin
echo "[2/4] Installing plugin..."
codex plugin add imo-health-clinical-intelligence@imo-health-codex-marketplace
echo "  Done."
echo ""

# Step 3 — Prompt for credentials
echo "[3/4] Setting up credentials..."
echo ""
read -p "  Enter your IMO Client ID: " CLIENT_ID
read -p "  Enter your IMO Client Secret: " CLIENT_SECRET
echo ""

if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "ERROR: Both Client ID and Client Secret are required."
    exit 1
fi

# Save to bashrc (skip if already present)
if grep -q "IMO_CLIENT_ID" "$BASHRC" 2>/dev/null; then
    echo "  Credentials already in $BASHRC — skipping."
else
    echo "" >> "$BASHRC"
    echo "# IMO Health MCP credentials" >> "$BASHRC"
    echo "export IMO_CLIENT_ID=\"$CLIENT_ID\"" >> "$BASHRC"
    echo "export MCP_CLIENT_SECRET=\"$CLIENT_SECRET\"" >> "$BASHRC"
    echo "  Credentials saved to $BASHRC"
fi

# Export for current session
export IMO_CLIENT_ID="$CLIENT_ID"
export MCP_CLIENT_SECRET="$CLIENT_SECRET"
echo ""

# Step 4 — Add MCP server to config.toml
echo "[4/4] Adding MCP server to Codex config..."

# Create config directory if needed
mkdir -p "$(dirname "$CODEX_CONFIG")"

# Check if server already exists in config
if grep -q "\[mcp_servers\.$SERVER_NAME\]" "$CODEX_CONFIG" 2>/dev/null; then
    echo "  Server '$SERVER_NAME' already in $CODEX_CONFIG — skipping."
else
    echo "" >> "$CODEX_CONFIG"
    echo "[mcp_servers.$SERVER_NAME]" >> "$CODEX_CONFIG"
    echo "enabled = true" >> "$CODEX_CONFIG"
    echo "url = \"$SERVER_URL\"" >> "$CODEX_CONFIG"
    echo "  Server '$SERVER_NAME' added to $CODEX_CONFIG"
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "    1. Run 'codex'"
echo "    2. Type /mcp to verify: $SERVER_NAME: connected (19 tools)"
echo "    3. Type: /mcp login <MCP Server Name>"
echo "    4. Try: \"Normalize chest pain\""
echo ""
