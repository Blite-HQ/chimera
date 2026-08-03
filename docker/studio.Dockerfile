# syntax=docker/dockerfile:1
# Imagen del servicio `studio`: nginx sirve el `dist/` de la SPA y
# reverse-proxea /invoke,/runs,/health al `api` (same-origin, SSE-safe).
# Build context = raíz del repo (workspace pnpm completo: root package.json,
# pnpm-lock.yaml, pnpm-workspace.yaml, apps/studio, packages/assurance-ui).
FROM node:22-bookworm-slim AS builder

WORKDIR /app

RUN corepack enable

# Copia el repo completo (respeta .dockerignore: excluye node_modules/dist)
# e instala el workspace pnpm completo antes de construir solo apps/studio.
COPY . .
RUN pnpm install --frozen-lockfile

ARG VITE_API_URL=""
# VITE_GATEWAY_URL murió con la ruta fantasma /invoke (hallazgo 7, 2026-08-08):
# ningún módulo del Studio la lee. La única var del build es VITE_API_URL.
RUN VITE_API_URL=$VITE_API_URL pnpm -C apps/studio run build

FROM nginx:1.27-alpine AS runtime

COPY docker/studio-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/studio/dist /usr/share/nginx/html

EXPOSE 80
