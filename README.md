# MangaConverter FOSS

Self-hosted manga and comic converter for e-readers. Convert your CBZ, CBR, PDF files to EPUB/MOBI formats optimized for Kindle, Kobo, and other e-readers.

## Features

- **Multiple Device Profiles**: Kindle, Kobo, reMarkable, and more
- **Advanced Options**: Cropping, rotation, image processing, quality settings
- **Real-time Processing**: WebSocket updates for job status
- **Local Storage**: All files stored on your server, no cloud dependencies
- **No Authentication Required**: Simple, privacy-focused design
- **Docker-based**: Easy deployment with Docker Compose

## Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd mgc-foss

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d
```

Open http://localhost:3000 in your browser.

## Architecture

The application consists of 4 main services:

- **Frontend**: Next.js web interface (port 3000)
- **Backend**: Flask API server (port 8060)
- **Celery Workers**: Background job processing
- **Redis**: Message broker and cache

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Browser   │─────▶│   Frontend  │─────▶│   Backend   │
│             │      │  (Next.js)  │      │   (Flask)   │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                   │
                                          ┌────────▼────────┐
                                          │      Redis      │
                                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │ Celery Workers  │
                                          │  (KCC Conv.)    │
                                          └─────────────────┘
```

## Storage

All files are stored locally in the `conversion-data` Docker volume:

- **Uploads**: `/data/uploads/{job_id}/`
- **Outputs**: `/data/outputs/{job_id}/`
- **Database**: `/data/jobs.db` (SQLite)

To backup your data:

```bash
docker run --rm -v mgc-foss_conversion-data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz -C /data .
```

To restore:

```bash
docker run --rm -v mgc-foss_conversion-data:/data -v $(pwd):/backup alpine tar xzf /backup/data-backup.tar.gz -C /data
```

## Configuration

See `.env.example` for all available configuration options. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `PUID` | User ID for file permissions | 1000 |
| `PGID` | Group ID for file permissions | 1000 |
| `GUNICORN_WORKERS` | Backend worker processes | 4 |
| `CELERY_CONCURRENCY` | Jobs per worker container | 2 |
| `NEXT_PUBLIC_API_URL` | Backend API URL | http://localhost:8060 |
| `NEXT_PUBLIC_MAX_FILES` | Max files per upload | 10 |

### Scaling Workers

To process more jobs in parallel, scale the celery-worker service:

```bash
# Scale to 5 worker containers with 2 concurrent jobs each = 10 parallel jobs
docker compose up -d --scale celery-worker=5
```

Or adjust concurrency per container:

```bash
# Set CELERY_CONCURRENCY=4 in .env for 4 jobs per container
```

## Development

For development with hot-reload:

```bash
# Use the dev compose file
docker compose -f docker-compose.dev.yml up

# Frontend will be available at localhost:3000 with hot reload
# Backend logs visible in terminal
```

## Technology Stack

**Frontend:**
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS + Radix UI
- Socket.IO (real-time updates)

**Backend:**
- Flask + Gunicorn
- Celery + Redis
- SQLAlchemy + SQLite
- Flask-SocketIO

**Conversion Engine:**
- [Kindle Comic Converter (KCC)](https://github.com/ciromattia/kcc)
- ImageMagick
- Poppler (PDF processing)

## Credits

This project is built on top of:

- **Kindle Comic Converter (KCC)** by Ciro Mattia Gonano, Paweł Jastrzębski, Darodi, and contributors
- Original web interface concept by the MangaConverter team

## License

ISC License - See LICENSE file for details.

KCC is licensed under ISC License © 2012-2025 Ciro Mattia Gonano and contributors.
