#!/usr/bin/env sh
# Scan STAGED changes for secrets before they become a commit.
#
# CI already scans the full history and blocks the merge; this is the fast half,
# so you find it before it is in the log rather than after. A secret that
# reaches a commit has to be rotated even if the commit never leaves your
# machine — the cheap moment is now.
#
# Config resolution:
#   1. `.gitleaks.local.toml` if it exists (git-ignored — your own patterns);
#   2. otherwise `.gitleaks.toml` (versioned, shared with CI).
#
# If gitleaks is not installed:
#   - with a local config present → FAIL. You configured extra patterns, so
#     silently skipping them would be the worst outcome: enforcement you
#     believe in and do not have.
#   - without one → warn and continue. CI still blocks, and a missing dev tool
#     should not stop someone from committing on their first day.
#
# Install: https://github.com/gitleaks/gitleaks#installing

set -eu

ROOT=$(git rev-parse --show-toplevel)
LOCAL_CONFIG="$ROOT/.gitleaks.local.toml"
SHARED_CONFIG="$ROOT/.gitleaks.toml"

if [ -f "$LOCAL_CONFIG" ]; then
  CONFIG="$LOCAL_CONFIG"
  CONFIG_IS_LOCAL=1
else
  CONFIG="$SHARED_CONFIG"
  CONFIG_IS_LOCAL=0
fi

if ! command -v gitleaks >/dev/null 2>&1; then
  if [ "$CONFIG_IS_LOCAL" = "1" ]; then
    echo "pre-commit: .gitleaks.local.toml exists but gitleaks is not installed." >&2
    echo "            Install it, or remove the local config if you no longer want it:" >&2
    echo "            https://github.com/gitleaks/gitleaks#installing" >&2
    exit 1
  fi
  echo "pre-commit: gitleaks not installed — skipping the local secret scan."
  echo "            CI still scans the full history and blocks on findings."
  exit 0
fi

gitleaks git --staged --redact --no-banner --config "$CONFIG" "$ROOT"
