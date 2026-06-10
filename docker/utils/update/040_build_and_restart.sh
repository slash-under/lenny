#!/usr/bin/env bash
set -euo pipefail

# Rebuild custom images and restart containers
# Alembic migrations run automatically on API container startup via migrate.sh

cd "$LENNY_ROOT"

# Build API (critical — must succeed)
# No --pull: reuse locally cached base images (python:3.12 etc.) to avoid
# re-downloading hundreds of MB on every update. Run `make rebuild` for a
# fully fresh pull when you explicitly want the latest base.
echo "Building API image..."
$COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build api

# Build reader and admin in parallel (non-critical — warn but don't fail)
echo "Building reader and admin images..."
reader_failed=0
admin_failed=0

$COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build reader admin || {
    # Re-run individually to get specific failure info
    if ! $COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build reader 2>/dev/null; then
        reader_failed=1
    fi
    if ! $COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build admin 2>/dev/null; then
        admin_failed=1
    fi
}

if [ "$reader_failed" -eq 1 ]; then
    echo ""
    echo "WARNING: Reader build failed. The API will still start."
    echo "The reader may use a cached image or be unavailable."
    echo "To retry: $COMPOSE_CMD -p $LENNY_COMPOSE_PROJECT build --no-cache reader"
    echo ""
fi
if [ "$admin_failed" -eq 1 ]; then
    echo ""
    echo "WARNING: Admin (lenny-app) build failed. The API will still start."
    echo "The admin UI may use a cached image or be unavailable."
    echo "To retry: $COMPOSE_CMD -p $LENNY_COMPOSE_PROJECT build --no-cache admin"
    echo ""
fi

# Prune dangling images (old untagged builds). Safe: never touches named volumes,
# running containers, or BuildKit cache mounts (pnpm_store etc.).
# Builder cache capped at 2 GB — preserves pnpm/pip layer caches that make
# future builds fast while preventing unbounded disk growth.
echo "Pruning dangling images and capping build cache..."
docker image prune -f || true
docker builder prune -f --keep-storage=2gb || true

# Restart all services
$COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" up -d
