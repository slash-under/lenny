#!/usr/bin/env bash
set -euo pipefail

# Rebuild custom images and restart containers
# Alembic migrations run automatically on API container startup via migrate.sh

cd "$LENNY_ROOT"

# Build API (critical — must succeed)
echo "Building API image..."
$COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build --pull api

# Build reader (non-critical — warn but don't fail the update)
echo "Building reader image..."
if ! $COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build --pull reader; then
    echo ""
    echo "WARNING: Reader build failed. The API will still start."
    echo "The reader may use a cached image or be unavailable."
    echo "To retry the reader build later: $COMPOSE_CMD -p $LENNY_COMPOSE_PROJECT build --no-cache reader"
    echo ""
fi

# Build admin / lenny-app frontend (non-critical — warn but don't fail the update)
# Pulled from its own repo (ArchiveLabs/lenny-app); the Dockerfile's cache-bust
# ensures this picks up the latest frontend on every update.
echo "Building admin (lenny-app) image..."
if ! $COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" build --pull admin; then
    echo ""
    echo "WARNING: Admin (lenny-app) build failed. The API will still start."
    echo "The admin UI may use a cached image or be unavailable."
    echo "To retry the admin build later: $COMPOSE_CMD -p $LENNY_COMPOSE_PROJECT build --no-cache admin"
    echo ""
fi

# Prune stale build cache and dangling images from prior updates.
# Safe: only removes layers/images not referenced by any running container or volume.
# db_data and all other named volumes are never touched by these commands.
echo "Pruning stale build cache and dangling images..."
docker builder prune -f --filter until=24h || true
docker image prune -f || true

# Restart all services
$COMPOSE_CMD -p "$LENNY_COMPOSE_PROJECT" up -d
