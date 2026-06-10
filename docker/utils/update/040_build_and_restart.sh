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

# Build reader (non-critical — warn but don't fail)
echo "Building reader image..."
if ! $COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build reader; then
    echo ""
    echo "WARNING: Reader build failed. The API will still start."
    echo "To retry: $COMPOSE_CMD -p $LENNY_COMPOSE_PROJECT build --no-cache reader"
    echo ""
fi

# Build admin (non-critical — warn but don't fail)
echo "Building admin image..."
if ! $COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build admin; then
    echo ""
    echo "WARNING: Admin build failed. The API will still start."
    echo "To retry: $COMPOSE_CMD -p $LENNY_COMPOSE_PROJECT build --no-cache admin"
    echo ""
fi

# Prune dangling images (old untagged builds). Safe: never touches named volumes,
# running containers, or BuildKit cache mounts (pnpm_store etc.).
# Builder cache capped at 2 GB — preserves pnpm/pip layer caches that make
# future builds fast while preventing unbounded disk growth.
echo "Pruning dangling images and capping build cache..."
docker image prune -f || true
docker builder prune -f --reserved-space=2gb || true

# Restart all services
$COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" up -d
