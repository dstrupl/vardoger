#!/usr/bin/env bash
#
# Install vardoger locally for all three platforms.
#
# Prerequisites: uv must be installed.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
VARDOGER_CLI="$REPO_ROOT/.venv/bin/vardoger"

echo "================================================"
echo " vardoger local install"
echo "================================================"
echo ""

# ------------------------------------------------------------------
# Step 1: Python venv + package
# ------------------------------------------------------------------
echo "[1/3] Setting up Python environment..."
(cd "$REPO_ROOT" && uv sync)
echo "  venv ready at $REPO_ROOT/.venv"
echo "  CLI available at $VARDOGER_CLI"
echo ""

# Keep the per-platform plugins/*/skills/analyze/SKILL.md files in sync with
# the shared src/vardoger/prompts/analyze_skill_body.md template. CI enforces
# the same check with `--check`.
(cd "$REPO_ROOT" && uv run scripts/render-skills.py)
echo ""

# ------------------------------------------------------------------
# Step 2: Cursor — register MCP server
# ------------------------------------------------------------------
echo "[2/3] Registering Cursor MCP server..."
MCP_CONFIG="$HOME/.cursor/mcp.json"

if [ ! -f "$MCP_CONFIG" ]; then
    mkdir -p "$(dirname "$MCP_CONFIG")"
    echo '{"mcpServers":{}}' > "$MCP_CONFIG"
fi

"$VENV_PYTHON" -c "
import json

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
"
echo "  Added vardoger to $MCP_CONFIG"
echo "  Restart Cursor to activate."
echo ""

# ------------------------------------------------------------------
# Step 3: Claude Code + Codex — print instructions
# ------------------------------------------------------------------
CLAUDE_PLUGIN_DIR="$REPO_ROOT/plugins/claude-code"
CODEX_PLUGIN_DIR="$REPO_ROOT/plugins/codex"

echo "[3/3] Claude Code and Codex setup:"
echo ""
echo "  CLAUDE CODE:"
echo "    Start Claude Code with:"
echo "      claude --plugin-dir $CLAUDE_PLUGIN_DIR"
echo ""
echo "  CODEX:"
echo "    Copy the plugin under ~/.codex/plugins/ so the ./.codex/... path"
echo "    in the marketplace file resolves correctly (Codex resolves source.path"
echo "    relative to the parent of .agents/):"
echo "      mkdir -p ~/.codex/plugins"
echo "      cp -R $CODEX_PLUGIN_DIR ~/.codex/plugins/vardoger"
echo ""
echo "    Then create or edit ~/.agents/plugins/marketplace.json:"
echo "    {"
echo "      \"name\": \"local\","
echo "      \"interface\": { \"displayName\": \"Local Plugins\" },"
echo "      \"plugins\": [{"
echo "        \"name\": \"vardoger\","
echo "        \"source\": { \"source\": \"local\", \"path\": \"./.codex/plugins/vardoger\" },"
echo "        \"policy\": { \"installation\": \"AVAILABLE\", \"authentication\": \"ON_INSTALL\" },"
echo "        \"category\": \"Productivity\""
echo "      }]"
echo "    }"
echo "    Restart Codex, run /plugins, pick the Local Plugins marketplace, and install."
echo ""
echo "================================================"
echo " vardoger installed successfully!"
echo "================================================"
echo ""
echo "Quick test (any platform):"
echo "  $VARDOGER_CLI analyze --platform cursor"
echo "  $VARDOGER_CLI analyze --platform claude-code"
echo "  $VARDOGER_CLI analyze --platform codex"
