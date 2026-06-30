#!/usr/bin/env bash
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
