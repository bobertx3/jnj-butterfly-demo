#!/usr/bin/env bash
# Deploy Next Best Action app: upload source via bundle, then trigger app deploy via CLI
# so the running app picks up the new code.
#
# Usage: ./scripts/deploy-app.sh [prod|dev]
# Optional: set WORKSPACE_APP_SOURCE_PATH to override the app path in the workspace.
#   Default: /Workspace/Users/<current-user>/jnj-butterfly-demo/files/app

set -e

TARGET="${1:-prod}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Workspace path where the bundle uploads the app (same as in databricks.yml root_path + /files/app)
# Override with WORKSPACE_APP_SOURCE_PATH if your workspace path differs.
if [[ -n "$WORKSPACE_APP_SOURCE_PATH" ]]; then
  SOURCE_CODE_PATH="$WORKSPACE_APP_SOURCE_PATH"
else
  # Try to get current user from CLI
  USER_NAME="$(databricks current-user me -o json 2>/dev/null | jq -r '.userName // empty')" || true
  if [[ -z "$USER_NAME" ]]; then
    echo "Set WORKSPACE_APP_SOURCE_PATH to your app path (e.g. /Workspace/Users/you@example.com/jnj-butterfly-demo/files/app)"
    echo "Or run: databricks current-user get  (to use auto path)"
    exit 1
  fi
  SOURCE_CODE_PATH="/Workspace/Users/${USER_NAME}/jnj-butterfly-demo/files/app"
fi

APP_NAME="next-best-action-${TARGET}"

echo "=== 1. Bundle deploy (upload source) ==="
databricks bundle deploy -t "$TARGET"

echo ""
echo "=== 2. App deploy (rebuild and run from ${SOURCE_CODE_PATH}) ==="
databricks apps deploy "$APP_NAME" \
  --source-code-path "$SOURCE_CODE_PATH" \
  --mode SNAPSHOT

echo ""
echo "Done. Open the app in the workspace to use the new version."
