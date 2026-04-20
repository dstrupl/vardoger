#!/usr/bin/env bash
#
# Post-release smoke test for the PyPI 0.1.0 publish (Milestone 2 of the
# Phase 4 marketplace release plan).
#
# Runs in a clean pipx venv so we verify the real published wheel, not a
# local checkout. Each `vardoger setup <platform>` is exercised against a
# throwaway $HOME so this script is safe to run repeatedly.
#
# Usage: bash scripts/smoke-test-release.sh [version]
#     version defaults to the latest release on PyPI.

set -euo pipefail

VERSION="${1:-}"

if ! command -v pipx >/dev/null 2>&1; then
    echo "pipx is required: https://pipx.pypa.io/stable/installation/" >&2
    exit 1
fi

TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

echo "================================================"
echo " vardoger smoke test"
echo "================================================"
echo "  temp HOME: $TMP_HOME"
echo ""

INSTALL_TARGET="vardoger"
if [[ -n "$VERSION" ]]; then
    INSTALL_TARGET="vardoger==$VERSION"
fi

echo "[1/6] pipx install $INSTALL_TARGET"
pipx install --force "$INSTALL_TARGET" >/dev/null
echo "  installed"
echo ""

echo "[2/6] vardoger --version"
vardoger --version
echo ""

for platform in cursor claude-code codex openclaw; do
    echo "[setup $platform] HOME=$TMP_HOME vardoger setup $platform"
    HOME="$TMP_HOME" vardoger setup "$platform" >/dev/null
    echo "  ok"
done
echo ""

echo "[6/6] Verify artifacts written under temp HOME"
find "$TMP_HOME" -maxdepth 6 \( -name "mcp.json" -o -name "plugin.json" -o -name "SKILL.md" -o -name "marketplace.json" \) | sort
echo ""

echo "================================================"
echo " smoke test passed"
echo "================================================"
