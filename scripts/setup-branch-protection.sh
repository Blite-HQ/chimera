#!/usr/bin/env bash
# =============================================================================
# SUPERSEDED (2026-07-15) — no correr esto para Blite-HQ/Chimera.
#
# La protección de main para Blite-HQ/Chimera ahora se define como un GitHub
# REPOSITORY RULESET, no con la API clásica de branch-protection que usa este
# script (PUT /repos/{owner}/{repo}/branches/main/protection, abajo). El
# ruleset se crea con:
#     gh api repos/Blite-HQ/Chimera/rulesets -X POST --input -   (ver el plan)
#
# Por qué: los rulesets son el reemplazo moderno y apilable de la protección
# clásica. Expresan las mismas garantías — status checks requeridos, review
# con CODEOWNERS, historia lineal, sin force-push, sin borrado de branch, y
# (con bypass list vacía) aplican también a admins — más restricción de
# método de merge, y pueden convivir con otros rulesets.
#
# NOTA: tanto la protección clásica como los rulesets están inertes en este
# repo hasta que la org Blite-HQ se actualice de GitHub Free a GitHub Team.
# Hasta entonces cualquier llamada devuelve 403 "Upgrade to GitHub Pro or
# make this repository public".
#
# Este archivo se mantiene funcional a propósito: la lógica de la API clásica
# sigue siendo reusable para otros repos/orgs en planes donde los rulesets no
# están disponibles.
# =============================================================================
# setup-branch-protection.sh — configure main branch protection on GitHub.
# Requires: gh auth login (authenticated gh CLI)
set -euo pipefail

REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")}"
if [ -z "$REPO" ]; then
    echo "ERROR: Could not determine repo. Run: export GH_REPO=owner/repo"
    exit 1
fi

echo "==> Applying branch protection to ${REPO}/main ..."
gh api "repos/${REPO}/branches/main/protection" \
    --method PUT \
    --header "Accept: application/vnd.github+json" \
    --field "required_status_checks[strict]=true" \
    --field "required_status_checks[contexts][]=Python" \
    --field "required_status_checks[contexts][]=Web (Studio)" \
    --field "required_status_checks[contexts][]=Commit messages" \
    --field "required_status_checks[contexts][]=Security" \
    --field "required_status_checks[contexts][]=Docs" \
    --field "enforce_admins=true" \
    --field "required_pull_request_reviews[required_approving_review_count]=1" \
    --field "required_pull_request_reviews[require_code_owner_reviews]=true" \
    --field "required_pull_request_reviews[dismiss_stale_reviews]=true" \
    --field "restrictions=null" \
    --field "required_linear_history=true" \
    --field "allow_force_pushes=false" \
    --field "allow_deletions=false"

echo "==> Branch protection set on ${REPO}:main"
echo "    Required checks: Python, Web, Commits, Security, Docs"
echo "    PR required + 1 CODEOWNERS review + linear history"
