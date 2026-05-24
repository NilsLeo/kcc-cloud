# Contributing

## Development setup

Requirements: Node 20, pnpm 9, Python 3.11, Docker

```bash
git clone https://github.com/NilsLeo/kcc-cloud.git
cd kcc-cloud
pnpm install
```

### Run the full stack locally

The easiest way is the single container:

```bash
docker build -f infra/docker/Dockerfile -t kcc-cloud-dev .
docker run -p 8090:80 -v kcc-cloud-dev-data:/data kcc-cloud-dev
```

### Run services individually (faster iteration)

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — KCC gRPC server
cd worker-kcc
python server.py

# Terminal 3 — API
pnpm --filter @mgc/api dev

# Terminal 4 — Worker
pnpm --filter @mgc/worker dev

# Terminal 5 — Frontend
pnpm --filter @mgc/frontend dev
```

### Build all packages

```bash
pnpm build
```

## Project structure

```
apps/
  api/       NestJS REST API
  worker/    BullMQ job processor
  frontend/  Vue 3 frontend
packages/
  core/           Domain interfaces and entities
  conversion-sdk/ Job types, ETA predictor
  db/             Prisma schema + SQLite repository
  queue/          BullMQ queue definitions
  events/         EventEmitter2 local event bus
  auth-core/      NoOpAuthProvider
  storage/        IStorageProvider interface
  telemetry/      Pino structured logger
worker-kcc/       Python gRPC server wrapping KCC
infra/
  docker/         Dockerfile, nginx.conf, supervisord.conf, entrypoint.sh
```

## Pull requests

- Keep PRs focused — one feature or fix per PR
- Run `pnpm build` before opening a PR; the CI will fail otherwise
- For new features, open an issue first to discuss the approach

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md).
