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

# El agente invariant-reviewer es OPT-IN (P5/M27 · hallazgo N10).
#
# Antes, este script escribía en `~/.claude/agents/` sin preguntar: un
# directorio de configuración PERSONAL del usuario, fuera del repo, tocado por
# un script llamado "install-dev". Un tercero que corre el setup de un
# proyecto no espera que le modifiquen su herramienta. Ahora hay que pedirlo
# —con la bandera o respondiendo el prompt—, y en no-interactivo (CI) se
# SALTA por defecto: sin TTY nadie pudo consentir.
install_agent() {
    local agents_dir="${HOME}/.claude/agents"
    local template="$(pwd)/tools/claude/agents/invariant-reviewer.md"
    if [ ! -f "$template" ]; then
        echo "  WARNING: tools/claude/agents/invariant-reviewer.md not found — skipping"
        return
    fi
    mkdir -p "$agents_dir"
    cp "$template" "$agents_dir/invariant-reviewer.md"
    echo "  Installed: $agents_dir/invariant-reviewer.md"
}

echo "==> Optional: invariant-reviewer agent (writes to ~/.claude/agents/)"
if [ "${INSTALL_CLAUDE_AGENT:-}" = "1" ] || [ "${1:-}" = "--with-claude-agent" ]; then
    install_agent
elif [ ! -t 0 ]; then
    echo "  Skipped (non-interactive). Enable with INSTALL_CLAUDE_AGENT=1"
else
    printf '  Install it into your ~/.claude/agents/? [y/N] '
    read -r respuesta
    case "$respuesta" in
        [yY]*) install_agent ;;
        *) echo "  Skipped — nothing written outside this repo." ;;
    esac
fi

echo ""
echo "==> Dev environment ready!"
echo "    uv run pytest              — run tests + invariant gates"
echo "    uv run lint-imports        — check architecture boundaries"
echo "    pnpm -C apps/studio test   — run Studio tests"
