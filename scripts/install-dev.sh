#!/usr/bin/env bash
# install-dev.sh — set up the Chimera dev environment
set -euo pipefail

echo "==> Checking tool availability..."
command -v uv   >/dev/null 2>&1 || { echo "ERROR: uv not found. Install from https://docs.astral.sh/uv/"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "ERROR: pnpm not found. Run: corepack enable"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: node not found."; exit 1; }

echo "==> Installing Python workspace (uv sync)..."
uv sync --all-packages --all-extras

echo "==> Installing Node root devDeps (pnpm install)..."
pnpm install

echo "==> Installing Studio deps..."
pnpm -C apps/studio install

echo "==> Setting up Husky git hooks..."
npx husky

echo "==> Installing invariant-reviewer agent (Claude local)..."
AGENTS_DIR="${HOME}/.claude/agents"
TEMPLATE="$(pwd)/tools/claude/agents/invariant-reviewer.md"
if [ -f "$TEMPLATE" ]; then
    mkdir -p "$AGENTS_DIR"
    cp "$TEMPLATE" "$AGENTS_DIR/invariant-reviewer.md"
    echo "  Installed: $AGENTS_DIR/invariant-reviewer.md"
else
    echo "  WARNING: tools/claude/agents/invariant-reviewer.md not found — skipping"
fi

echo ""
echo "==> Dev environment ready!"
echo "    uv run pytest              — run tests + invariant gates"
echo "    uv run lint-imports        — check architecture boundaries"
echo "    pnpm -C apps/studio test   — run Studio tests"
