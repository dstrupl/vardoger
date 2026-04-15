#!/usr/bin/env bash
#
# Install vardoger MCP server into Cursor.
#
# This script:
#   1. Ensures the Python venv is set up
#   2. Adds a "vardoger" entry to ~/.cursor/mcp.json
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
MCP_CONFIG="$HOME/.cursor/mcp.json"

echo "vardoger: installing Cursor MCP server..."

# Step 1: ensure venv
if [ ! -f "$VENV_PYTHON" ]; then
    echo "  Setting up Python venv..."
    (cd "$REPO_ROOT" && uv sync)
fi

# Step 2: add to mcp.json
if [ ! -f "$MCP_CONFIG" ]; then
    echo '{"mcpServers":{}}' > "$MCP_CONFIG"
fi

# Use Python to safely merge into the JSON config
"$VENV_PYTHON" -c "
import json, sys

config_path = '$MCP_CONFIG'
venv_python = '$VENV_PYTHON'

with open(config_path) as f:
    config = json.load(f)

servers = config.setdefault('mcpServers', {})
servers['vardoger'] = {
    'command': venv_python,
    'args': ['-m', 'vardoger.mcp_server'],
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f'  Added vardoger to {config_path}')
"

echo "vardoger: Cursor MCP server installed. Restart Cursor to activate."
