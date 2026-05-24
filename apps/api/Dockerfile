FROM node:20-alpine AS builder
WORKDIR /app
RUN apk add --no-cache openssl
RUN npm i -g pnpm
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml tsconfig.json .npmrc ./
COPY packages/ packages/
COPY apps/api/ apps/api/
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @mgc/core build
RUN pnpm --filter @mgc/conversion-sdk build
RUN pnpm --filter @mgc/queue build
RUN pnpm --filter @mgc/events build
RUN pnpm --filter @mgc/db build
RUN pnpm --filter @mgc/db run db:generate
RUN pnpm --filter @mgc/api build

FROM node:20-alpine
WORKDIR /app
RUN apk add --no-cache openssl
RUN npm i -g pnpm
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/api/dist ./dist
COPY --from=builder /app/packages ./packages
COPY apps/api/package.json ./
RUN mkdir -p /data/files/input /data/files/output
ENV NODE_ENV=production
EXPOSE 3000
CMD sh -c "mkdir -p /data && ./node_modules/.bin/prisma db push --schema packages/db/prisma/base/schema.prisma --skip-generate 2>/dev/null || true && node dist/main"
