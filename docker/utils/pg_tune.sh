#!/bin/sh
# Auto-tune Postgres settings based on available system RAM.
# Runs inside the postgres container before starting the server.
# Nothing to configure — calculates everything from detected RAM.

total_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
total_mb=$((total_kb / 1024))

# shared_buffers = 25% of RAM, capped at 512 MB
shared_mb=$((total_mb / 4))
[ "$shared_mb" -gt 512 ] && shared_mb=512

# effective_cache_size = 75% of RAM
cache_mb=$((total_mb * 3 / 4))

# work_mem: small — Lenny is not query-heavy
work_mb=4

# max_connections: (workers × 2) + 10 headroom, minimum 20
workers=${LENNY_WORKERS:-2}
connections=$(( workers * 2 + 10 ))
[ "$connections" -lt 20 ] && connections=20

exec docker-entrypoint.sh postgres \
    -c shared_buffers="${shared_mb}MB" \
    -c effective_cache_size="${cache_mb}MB" \
    -c work_mem="${work_mb}MB" \
    -c max_connections="$connections"
