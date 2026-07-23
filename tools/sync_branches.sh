#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "ERROR: run branch sync from main (current: $CURRENT_BRANCH)" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree is not clean. Commit or discard changes before syncing." >&2
  git status --short
  exit 1
fi

make review

git push origin main

for branch in dev sit; do
  git checkout "$branch"
  git merge --ff-only main
  git push origin "$branch"
done

git checkout main
