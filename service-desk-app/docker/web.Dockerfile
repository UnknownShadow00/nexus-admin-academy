FROM node:22-alpine AS base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable && corepack prepare pnpm@10.15.1 --activate
WORKDIR /app

FROM base AS dependencies

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/api/package.json apps/api/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/shared/package.json packages/shared/package.json
COPY packages/simulation-engine/package.json packages/simulation-engine/package.json
COPY packages/ui/package.json packages/ui/package.json

RUN pnpm install --frozen-lockfile

FROM base AS production-dependencies

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/api/package.json apps/api/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/shared/package.json packages/shared/package.json
COPY packages/simulation-engine/package.json packages/simulation-engine/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY --from=dependencies /pnpm/store /pnpm/store

RUN pnpm install --prod --offline --frozen-lockfile

FROM dependencies AS builder

ARG NEXUS_INTEGRATION=""
ARG NEXT_PUBLIC_NEXUS_INTEGRATION=""
ARG SERVICE_DESK_BASE_PATH=""

ENV NEXUS_INTEGRATION="$NEXUS_INTEGRATION"
ENV NEXT_PUBLIC_BASE_PATH="$SERVICE_DESK_BASE_PATH"
ENV NEXT_PUBLIC_NEXUS_INTEGRATION="$NEXT_PUBLIC_NEXUS_INTEGRATION"
ENV SERVICE_DESK_BASE_PATH="$SERVICE_DESK_BASE_PATH"

COPY . .

RUN pnpm --filter @service-desk/web... build

FROM base AS runner

ENV NODE_ENV="production"
ENV NEXT_TELEMETRY_DISABLED="1"
ENV JWT_ALGORITHM=""
ENV NEXUS_ADMIN_CHECK_URL=""
ENV NEXUS_INTEGRATION=""
ENV NEXT_PUBLIC_BASE_PATH=""
ENV NEXT_PUBLIC_NEXUS_INTEGRATION=""
ENV SERVICE_DESK_BASE_PATH=""

COPY --from=production-dependencies --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/package.json /app/pnpm-workspace.yaml ./
COPY --from=production-dependencies --chown=node:node /app/apps/web/node_modules ./apps/web/node_modules
COPY --from=builder --chown=node:node /app/apps/web/package.json ./apps/web/package.json
COPY --from=builder --chown=node:node /app/apps/web/next.config.mjs ./apps/web/next.config.mjs
COPY --from=builder --chown=node:node /app/apps/web/.next ./apps/web/.next
COPY --from=builder --chown=node:node /app/packages/shared/package.json ./packages/shared/package.json
COPY --from=builder --chown=node:node /app/packages/shared/src ./packages/shared/src
COPY --from=builder --chown=node:node /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder --chown=node:node /app/packages/simulation-engine/package.json ./packages/simulation-engine/package.json
COPY --from=builder --chown=node:node /app/packages/simulation-engine/src ./packages/simulation-engine/src
COPY --from=builder --chown=node:node /app/packages/simulation-engine/dist ./packages/simulation-engine/dist
COPY --from=builder --chown=node:node /app/packages/ui/package.json ./packages/ui/package.json
COPY --from=builder --chown=node:node /app/packages/ui/src ./packages/ui/src
COPY --from=builder --chown=node:node /app/packages/ui/dist ./packages/ui/dist

USER node
WORKDIR /app/apps/web

EXPOSE 3000

CMD ["node_modules/.bin/next", "start", "-p", "3000"]
