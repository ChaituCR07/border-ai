# syntax=docker/dockerfile:1.7
# Stage 1: Build React/Vite SPA bundle
FROM node:22-bookworm-slim AS build
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
COPY shared/protocol /shared/protocol

RUN --mount=type=cache,target=/root/.npm npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Serve via unprivileged Nginx
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null 2>&1 || exit 1
