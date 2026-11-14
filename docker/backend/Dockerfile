# syntax=docker/dockerfile:1.7
# Stage 1: Dependencies
FROM node:22-bookworm-slim AS deps
WORKDIR /app

COPY backend/package.json backend/package-lock.json ./
COPY shared/protocol /shared/protocol

RUN --mount=type=cache,target=/root/.npm npm ci

# Stage 2: Compilation & Build
FROM deps AS build
COPY backend/ ./
RUN npm run build && npm prune --omit=dev

# Stage 3: Production Hardened Runtime
FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production \
    TZ=UTC

# Create unprivileged user (UID/GID 10001)
RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -M -s /usr/sbin/nologin app

WORKDIR /app

# Copy production artifacts with unprivileged ownership
COPY --from=build --chown=10001:10001 /app/node_modules ./node_modules
COPY --from=build --chown=10001:10001 /app/dist ./dist
COPY --from=build --chown=10001:10001 /app/package.json ./package.json
COPY --chown=10001:10001 database/migrations ./database/migrations

USER 10001:10001
EXPOSE 4000

HEALTHCHECK --interval=10s --timeout=3s --retries=6 --start-period=20s \
  CMD ["node", "-e", "fetch('http://127.0.0.1:4000/api/health').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]

CMD ["node", "dist/server.js"]
