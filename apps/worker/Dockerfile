FROM node:20-alpine AS builder
WORKDIR /app
RUN apk add --no-cache openssl
RUN npm i -g pnpm
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml tsconfig.json .npmrc ./
COPY packages/ packages/
COPY apps/worker/ apps/worker/
COPY worker-kcc/proto/ worker-kcc/proto/
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @mgc/core build
RUN pnpm --filter @mgc/conversion-sdk build
RUN pnpm --filter @mgc/queue build
RUN pnpm --filter @mgc/events build
RUN pnpm --filter @mgc/db build
RUN pnpm --filter @mgc/db run db:generate
RUN pnpm --filter @mgc/worker build

FROM node:20-alpine
WORKDIR /app
RUN apk add --no-cache openssl
RUN npm i -g pnpm
COPY --from=builder /app/node_modules ./node_modules
# Preserve apps/worker/dist depth so grpc-client proto path (../../../../worker-kcc) resolves correctly
COPY --from=builder /app/apps/worker/dist ./apps/worker/dist
COPY --from=builder /app/packages ./packages
COPY apps/worker/package.json ./apps/worker/package.json
COPY --from=builder /app/worker-kcc/proto/ ./worker-kcc/proto/
ENV NODE_ENV=production
CMD ["node", "apps/worker/dist/main"]
