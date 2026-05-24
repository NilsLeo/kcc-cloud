# kcc-cloud

Convert CBZ, CBR, PDF, and EPUB files into perfectly-sized e-reader files for Kindle, Kobo, reMarkable, and 30+ other devices. Right-to-left support for manga, auto-cropping, panel splitting.

Self-hosted in a single Docker container.

## Quick start

```bash
docker run -d \
  -p 8090:80 \
  -v kcc-cloud-data:/data \
  --restart unless-stopped \
  --name kcc-cloud \
  ghcr.io/nilsleo/kcc-cloud:latest
```

Open `http://localhost:8090`.

## Docker Compose

```yaml
services:
  kcc-cloud:
    image: ghcr.io/nilsleo/kcc-cloud:latest
    ports:
      - "8090:80"
    volumes:
      - kcc-cloud-data:/data
    restart: unless-stopped
    environment:
      ADMIN_PASSWORD: changeme   # optional, protects /api/admin/*

volumes:
  kcc-cloud-data:
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `3000` | Internal API port (nginx proxies from 80) |
| `DATABASE_URL` | `file:/data/mgc.db` | SQLite path — keep inside the volume |
| `REDIS_URL` | `redis://localhost:6379` | Redis (bundled, change only if using external) |
| `STORAGE_PATH` | `/data/files` | Where input/output files are stored |
| `ADMIN_PASSWORD` | _(unset)_ | Password for `/api/admin/*` endpoints. If unset, admin routes are disabled. |

## Volume layout

```
/data/
├── mgc.db            # SQLite database (jobs, conversion history)
└── files/
    ├── input/        # Uploaded files (deleted immediately after conversion)
    └── output/       # Converted files (deleted 24 h after first download)
```

## Upgrading

```bash
docker pull ghcr.io/nilsleo/kcc-cloud:latest
docker stop kcc-cloud && docker rm kcc-cloud
# re-run the docker run command above
```

Or with Compose:

```bash
docker compose pull && docker compose up -d
```

Prisma migrations run automatically on startup — no manual migration step needed.

## Checking logs

```bash
# All services (supervisor)
docker exec kcc-cloud supervisorctl status

# API logs
docker exec kcc-cloud tail -f /var/log/mgc/api.log

# Worker logs
docker exec kcc-cloud tail -f /var/log/mgc/worker.log

# KCC gRPC server logs
docker exec kcc-cloud tail -f /var/log/mgc/kcc-grpc.log

# nginx logs
docker exec kcc-cloud tail -f /var/log/nginx/access.log
docker exec kcc-cloud tail -f /var/log/nginx/error.log

# Redis
docker exec kcc-cloud redis-cli -u redis://localhost:6379 ping
```

## Supported input formats

CBZ, CBR, ZIP, RAR, 7Z, PDF, EPUB

## Supported output formats / devices

30+ device profiles including:
- Kindle (all generations), Kindle Scribe
- Kobo Clara, Libra, Sage, Elipsa
- reMarkable 2
- Boox devices
- Custom resolution

## Building from source

Requirements: Node 20, pnpm 9, Python 3.11, Docker

```bash
git clone https://github.com/NilsLeo/kcc-cloud.git
cd kcc-cloud
docker build -f infra/docker/Dockerfile -t kcc-cloud .
docker run -p 8090:80 -v kcc-cloud-data:/data kcc-cloud
```

Or run services individually for development:

```bash
pnpm install
pnpm build
# See CONTRIBUTING.md for the full dev setup
```

## Architecture

Single Docker container running five services via supervisord:

- **nginx** — reverse proxy, serves the Vue frontend on port 80
- **redis** — job state and pub/sub progress events
- **kcc-grpc** — Python gRPC server wrapping [KCC](https://github.com/ciromattia/kcc)
- **api** — NestJS REST API (port 3000)
- **worker** — NestJS BullMQ processor (three tiers: small/medium/large jobs)

All state lives in the `/data` volume — the container itself is stateless.

## License

MIT — see [LICENSE](LICENSE).

## Support the project

If kcc-cloud saves you time, consider [sponsoring on GitHub](https://github.com/sponsors/NilsLeo).
