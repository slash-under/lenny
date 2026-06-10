FROM node:20-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

WORKDIR /app
RUN apt-get update && apt-get install -y git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN corepack enable

# Pin lenny-app to a specific commit (default branch: main).
# To upgrade the admin frontend: replace LENNY_APP_REF with a newer commit SHA.
# Changing this value invalidates the build cache from this line onward —
# deterministic on both BuildKit and the classic builder — so `make update`
# re-clones and checks out the new commit. No floating HEAD = no surprise drift.
ARG LENNY_APP_REF=e8435c3d6f16e9749bf25832e6c14f6da4c4ae0a

RUN git clone https://github.com/ArchiveLabs/lenny-app . && \
    git checkout "$LENNY_APP_REF"

# Install all workspace deps (no cache mount — fully clean install)
RUN pnpm install --frozen-lockfile

# Build only the web app
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN pnpm turbo run build --filter=web

EXPOSE 4000

WORKDIR /app/apps/web
ENV PORT=4000
CMD ["pnpm", "start"]
