#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs) || true
fi

TOKEN="${Github_api:-${GITHUB_PERSONAL_ACCESS_TOKEN:-${GIT_TOKEN:-${GITHUB_TOKEN:-}}}}"

if [ -z "${TOKEN}" ]; then
  echo "Error: GITHUB_PERSONAL_ACCESS_TOKEN (or GIT_TOKEN) secret is not set in environment or .env" >&2
  exit 1
fi

REPO="github.com/tejasmeet-code/Zenith.git"
REMOTE_URL="https://${TOKEN}@${REPO}"

BRANCH=$(git --no-optional-locks rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

echo "Pushing branch '${BRANCH}' to GitHub repository ${REPO}..."
git push "$REMOTE_URL" "${BRANCH}:${BRANCH}" --force
echo "Successfully pushed to GitHub!"
