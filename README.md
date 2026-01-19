<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">

<!-- TODO: Replace with actual logo -->
<!-- <img src="docs/logo.svg" width="300" alt="MangaConverter FOSS Logo"> -->
<!-- <br/><br/> -->

# MangaConverter FOSS

**A self-hosted, privacy-focused web application for converting manga and comics to e-reader optimized formats**

<br/>

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-Try_Now-success?style=for-the-badge)](https://www.mangaconverter.com)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg?style=for-the-badge)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/nilsleo/mgc-foss?style=for-the-badge&logo=github)](https://github.com/nilsleo/mgc-foss/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/nilsleo/mgc-foss?style=for-the-badge&logo=github)](https://github.com/nilsleo/mgc-foss/network/members)
[![Downloads](https://img.shields.io/github/downloads/nilsleo/mgc-foss/total?style=for-the-badge&logo=github)](https://github.com/nilsleo/mgc-foss/releases)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

[🌐 Live Demo](https://www.mangaconverter.com) • [Features](#features) • [Quick Start](#quick-start) • [Tech Stack](#tech-stack) • [Documentation](#documentation)

</div>

---

<!-- TABLE OF CONTENTS -->
<details>
  <summary>📑 Table of Contents</summary>
  <ol>
    <li><a href="#overview">Overview</a></li>
    <li><a href="#demo">Demo</a></li>
    <li><a href="#architecture">Architecture</a></li>
    <li><a href="#features">Features</a></li>
    <li><a href="#tech-stack">Tech Stack</a></li>
    <li><a href="#quick-start">Quick Start</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#configuration">Configuration</a></li>
    <li><a href="#monitoring">Monitoring</a></li>
    <li><a href="#backup--restore">Backup & Restore</a></li>
    <li><a href="#troubleshooting">Troubleshooting</a></li>
    <li><a href="#development">Development</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

---

## 📖 Overview

MangaConverter FOSS transforms your manga, comics, and documents into e-reader optimized formats (EPUB, MOBI, PDF, KFX, CBZ) with a modern, responsive web interface. Built for self-hosting with Docker, it provides multi-device access, real-time job monitoring, and parallel processing capabilities.

> **🚀 Try it now:** [www.mangaconverter.com](https://www.mangaconverter.com) — No installation required!

### Built on KCC

This project is powered by **[Kindle Comic Converter (KCC)](https://github.com/ciromattia/kcc)**, an excellent open-source tool by Ciro Mattia Gonano and Paweł Jastrzębski. We're deeply grateful for their work, which forms the conversion engine of this application.

### Why Choose the Web Interface?

While KCC's desktop GUI is fantastic, this web-based alternative offers compelling advantages for modern workflows:

| Benefit | Description |
|---------|-------------|
| **Multi-Device Access** | Access the converter from any device—desktop, tablet, or smartphone—via your browser |
| **Simultaneous Processing** | Celery worker pool enables parallel conversion of multiple files, significantly faster than sequential GUI processing |
| **One-Time Setup** | Deploy once with Docker Compose, then access from anywhere on your network—no repeated installations |
| **Centralized Storage** | All conversions stored on the server, accessible from any device without file transfers |
| **Always Available** | Runs 24/7 as a service, queue jobs anytime without launching a desktop application |
| **Responsive Design** | Optimized UI for mobile, tablet, and desktop—convert manga on your phone while commuting |
| **Real-Time Monitoring** | Live progress updates via WebSocket, monitor conversions from multiple devices simultaneously |
| **Batch Processing** | Upload and queue up to 10 files at once with intelligent queue management |
| **Scalable Infrastructure** | Add more workers with a single command to handle increased load |
| **Privacy-First** | Self-hosted solution—all data stays on your server, no cloud dependencies |
| **Job History** | Persistent database tracks all conversions, redownload files anytime |
| **No Installation Required** | Users just visit a URL, no software installation or updates needed |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🎬 Demo

### 🌐 Live Demo

**Try it now:** **[www.mangaconverter.com](https://www.mangaconverter.com)**

Experience the full application in action! No installation required—just visit the URL and start converting manga and comics to e-reader formats.

> **💡 Tip:** Works great on mobile too! Try uploading a file from your smartphone to see the responsive design in action.

---

### Desktop & Mobile Responsive Design

> **[GIF PLACEHOLDER: Desktop workflow - Upload → Configure → Monitor → Download]**
>
> *Shows full conversion flow on desktop: dragging files, selecting device profile, adjusting options, watching real-time progress, downloading converted file*

> **[GIF PLACEHOLDER: Mobile workflow - Same flow shown on smartphone]**
>
> *Demonstrates responsive design: mobile-optimized file picker, touch-friendly controls, real-time job monitoring on phone*

> **[GIF PLACEHOLDER: Multi-device sync - Desktop upload, phone monitors, tablet downloads]**
>
> *Showcases cross-device access: upload from desktop, monitor progress on phone, download from tablet*

### Screenshots

<details>
<summary>Click to expand screenshots</summary>

> **[SCREENSHOT PLACEHOLDER: Main conversion page - Desktop]**

> **[SCREENSHOT PLACEHOLDER: Advanced options panel]**

> **[SCREENSHOT PLACEHOLDER: Conversion queue with real-time progress]**

> **[SCREENSHOT PLACEHOLDER: Mobile view - Main page]**

> **[SCREENSHOT PLACEHOLDER: Downloads history page]**

</details>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🏗️ Architecture

> **[DIAGRAM PLACEHOLDER: System architecture diagram]**
>
> *High-level overview showing: Browser → Next.js Frontend (Port 3000) → Flask Backend API (Port 8060) → Redis Message Broker → Celery Worker Pool → KCC Conversion Engine → SQLite Database + Local Storage*

**Microservices Architecture:**
- **Frontend**: Next.js 16 with React 19, TypeScript, Tailwind CSS, Radix UI
- **Backend API**: Flask 2.0 with Gunicorn, Socket.IO for WebSocket real-time updates
- **Task Queue**: Celery 5.3 with Redis broker for distributed job processing
- **Database**: SQLite for job metadata and history
- **Storage**: Local filesystem for uploads and converted files
- **Deployment**: Docker Compose orchestration with scalable worker pool

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## ✨ Features

### Core Functionality

- ✅ **Multi-Format Support**
  - **Input**: CBZ, CBR, CB7, PDF, EPUB, ZIP, RAR, 7Z, TAR
  - **Output**: EPUB, MOBI, PDF, KFX, CBZ, MOBI+EPUB

- ✅ **35+ E-Reader Devices**
  - Kindle (K1-K11, Paperwhite, Voyage, Oasis, Scribe)
  - Kobo (19+ models from Mini to Elipsa)
  - reMarkable (1, 2, Paper Pro)
  - Custom dimensions support

- ✅ **Advanced Conversion Options** (25+ parameters)
  - Image processing: upscale, stretch, auto-level, quality
  - Cropping: margin detection, page number removal
  - Borders: black/white detection, forced borders
  - Output: gamma correction, target file size, color modes
  - Manga-specific: RTL reading, two-panel mode, webtoon support
  - Orientation: rotation, spread shift

### User Experience

- ✅ **Real-Time Job Monitoring**
  - Live progress bars with percentage and ETA
  - WebSocket updates—no page refresh needed
  - Queue visualization with job status badges
  - Job cancellation with instant feedback

- ✅ **Dual Mode Interface**
  - **Manga Mode**: Right-to-left optimized, manga options highlighted
  - **Comic Mode**: Left-to-right optimized, general options

- ✅ **Responsive Design**
  - Mobile-first approach, works on 320px+ screens
  - Touch-optimized controls for smartphones/tablets
  - Desktop-optimized layouts with advanced features
  - Dark/light theme support

- ✅ **Batch Processing**
  - Upload up to 10 files simultaneously (configurable)
  - Intelligent queue management
  - Download all converted files individually
  - Persistent job history

### Technical Highlights

- ✅ **Scalable Job Processing**
  - Horizontal scaling: `docker-compose up -d --scale celery-worker=5`
  - Configurable concurrency per worker (default: 2 jobs/worker)
  - Example: 5 workers × 2 concurrency = 10 parallel conversions

- ✅ **Real-Time Communication**
  - Socket.IO WebSocket server with Redis pub/sub
  - Automatic reconnection with exponential backoff
  - Fallback polling for unstable connections

- ✅ **Data Persistence**
  - SQLite database with comprehensive job metadata
  - All uploads/outputs stored locally (no cloud)
  - Job history with download tracking

- ✅ **Production-Ready**
  - Docker Compose deployment (single command)
  - Nginx reverse proxy (production)
  - Gunicorn WSGI server with 4 workers
  - Supervisor process management
  - Health check endpoints

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 16 (React 19, TypeScript 5+)
- **Styling**: Tailwind CSS 3.4, Radix UI components
- **State**: React Hooks, React Hook Form + Zod validation
- **Real-time**: Socket.IO Client 4.7
- **Animation**: Framer Motion 12
- **Testing**: Vitest 1.0, React Testing Library 14
- **Code Quality**: ESLint, Prettier, TypeScript strict mode

### Backend
- **Framework**: Flask 2.0, Gunicorn WSGI
- **Task Queue**: Celery 5.3, Redis 7
- **Database**: SQLAlchemy 1.4, SQLite 3
- **Real-time**: Flask-SocketIO 5.3, Python-SocketIO 5.11
- **Conversion**: KCC (custom module), ImageMagick, PyMuPDF 1.23
- **Testing**: pytest 7.4, pytest-cov, pytest-mock
- **Code Quality**: Black, Flake8, isort, mypy

### DevOps
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions (linting, testing, coverage)
- **Code Quality**: Pre-commit hooks, Codecov integration
- **Monitoring**: Flower (Celery), structured logging

### Built With

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" />
</p>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- 2GB+ RAM available
- 10GB+ disk space for conversions

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nilsleo/mgc-foss.git
   cd mgc-foss
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env if needed (optional for local testing)
   ```

3. **Start the application**
   ```bash
   docker compose up -d
   ```

4. **Access the web interface**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8060

### Scaling Workers

To increase conversion throughput, scale the worker pool:

```bash
# Scale to 5 worker containers (10 parallel jobs with default concurrency=2)
docker compose up -d --scale celery-worker=5

# Adjust concurrency in .env
CELERY_CONCURRENCY=4  # 5 workers × 4 = 20 parallel jobs
```

### Development Setup

For hot-reload development:

```bash
# Install dependencies locally (optional, for IDE support)
cd app/backend && pip install -r requirements.txt -r requirements-dev.txt
cd app/frontend && pnpm install

# Start development environment
docker compose -f docker-compose.dev.yml up
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development instructions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 📱 Usage

### Basic Conversion

1. **Upload Files**: Drag-and-drop or click to browse
2. **Select Device**: Choose from 35+ e-reader profiles (e.g., Kindle Paperwhite, Kobo Clara)
3. **Configure Options** (optional): Expand "Advanced Options" for fine-tuning
4. **Convert**: Click "Convert" button
5. **Monitor**: Watch real-time progress with ETA
6. **Download**: Click download button when complete

### Advanced Options

<details>
<summary>View all 25+ conversion parameters</summary>

**Image Processing**
- Upscale images for higher quality
- Stretch to fill screen (no borders)
- High quality mode (slower, better output)
- Auto-level for contrast adjustment
- Force grayscale or color

**Cropping & Margins**
- Margin detection (4 levels: none to aggressive)
- Page number removal
- Preserve original margins
- Cropping power adjustment

**Borders**
- Black/white border detection
- Force black or white borders
- Border size control

**Output Quality**
- Gamma correction (0.1-2.0)
- Target file size limits
- mozJPEG compression
- Force PNG format

**Manga-Specific**
- Right-to-left reading mode
- Two-panel detection
- Webtoon mode (vertical scroll)
- Spread shift for two-page layouts

**Orientation**
- Rotation (0°, 90°, 180°, 270°)
- Auto-rotation
- Landscape split mode

</details>

### Mobile Usage

MangaConverter FOSS is fully optimized for mobile:

1. Visit the URL on your smartphone/tablet
2. Use native file picker or photo library
3. Touch-optimized controls for all options
4. Monitor conversions on-the-go
5. Download directly to device

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_CONCURRENCY` | 2 | Jobs per worker container |
| `GUNICORN_WORKERS` | 4 | API server processes |
| `NEXT_PUBLIC_MAX_FILES` | 10 | Max simultaneous uploads |
| `NEXT_PUBLIC_MAX_FILE_SIZE` | 1GB | Max single file size |
| `ALLOWED_ORIGINS` | localhost:3000 | CORS allowed origins |

See [.env.example](.env.example) for all 40+ configuration options.

### Performance Tuning

**For high-volume conversions:**
```bash
# .env adjustments
CELERY_CONCURRENCY=4          # More jobs per worker
GUNICORN_WORKERS=8            # More API workers
GUNICORN_TIMEOUT=1200         # Longer timeout for large files

# Scale workers
docker compose up -d --scale celery-worker=10
```

**For low-resource systems:**
```bash
# .env adjustments
CELERY_CONCURRENCY=1          # Single job per worker
GUNICORN_WORKERS=2            # Fewer API workers
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 📊 Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8060/health

# Queue status
curl http://localhost:8060/queue
```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f celery-worker
docker compose logs -f backend
docker compose logs -f frontend
```

### Celery Monitoring (Flower)

Access Flower dashboard (if enabled):
```
http://localhost:5555
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 💾 Backup & Restore

### Backup Conversion Data

```bash
docker run --rm \
  -v mgc-foss_conversion-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/mgc-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore

```bash
docker run --rm \
  -v mgc-foss_conversion-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/mgc-backup-YYYYMMDD.tar.gz -C /data
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🐛 Troubleshooting

### Common Issues

**"Connection refused" errors**
- Check all containers are running: `docker compose ps`
- Restart services: `docker compose restart`

**Conversions stuck in "Processing"**
- Check worker logs: `docker compose logs celery-worker`
- Verify Redis is running: `docker compose ps redis`
- Restart worker: `docker compose restart celery-worker`

**"File too large" errors**
- Increase `NEXT_PUBLIC_MAX_FILE_SIZE` in `.env`
- Increase `GUNICORN_TIMEOUT` for large files

**Slow conversions**
- Scale workers: `docker compose up -d --scale celery-worker=5`
- Increase `CELERY_CONCURRENCY` in `.env`
- Check system resources: `docker stats`

### Support

For bugs or feature requests:
1. Check [existing issues](https://github.com/nilsleo/mgc-foss/issues)
2. Open a new issue with details
3. Include logs and environment info

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 💻 Development

### Project Structure

```
mgc-foss/
├── app/
│   ├── backend/           # Flask API + Celery workers
│   │   ├── app/
│   │   │   ├── app.py     # Flask application
│   │   │   ├── tasks.py   # Celery tasks
│   │   │   ├── routes.py  # API endpoints
│   │   │   ├── models.py  # SQLAlchemy models
│   │   │   └── utils/     # Helper modules
│   │   ├── tests/         # Backend tests
│   │   └── requirements.txt
│   └── frontend/          # Next.js application
│       ├── app/           # Next.js 13+ app directory
│       ├── components/    # React components
│       ├── lib/           # Utilities
│       ├── hooks/         # Custom hooks
│       ├── __tests__/     # Frontend tests
│       └── package.json
├── docker-compose.yml     # Production config
├── docker-compose.dev.yml # Development config
├── .github/workflows/     # CI/CD pipelines
└── README.md
```

### Running Tests

**Backend**:
```bash
cd app/backend
pytest --cov=app --cov-report=html
```

**Frontend**:
```bash
cd app/frontend
pnpm test
pnpm test:coverage
```

### Code Quality

**Backend**:
```bash
cd app/backend
black .                    # Format code
isort .                    # Sort imports
flake8 .                   # Lint
mypy .                     # Type check
```

**Frontend**:
```bash
cd app/frontend
pnpm format                # Format code
pnpm lint                  # Lint
pnpm type-check            # Type check
```

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Manual run
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🗺️ Roadmap

- [ ] User authentication and multi-tenancy
- [ ] Cloud storage integration (S3, MinIO)
- [ ] Batch download as ZIP
- [ ] Conversion presets/templates
- [ ] API rate limiting
- [ ] Enhanced job scheduling
- [ ] Admin dashboard
- [ ] Internationalization (i18n)
- [ ] Email notifications
- [ ] Webhook support

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 📄 License

This project is licensed under the **ISC License** - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses

- **Kindle Comic Converter (KCC)**: ISC License - [GitHub](https://github.com/ciromattia/kcc)
- **ImageMagick**: Apache 2.0 License
- All other dependencies: See respective package licenses

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🙏 Acknowledgments

Special thanks to:
- **[Ciro Mattia Gonano](https://github.com/ciromattia)** and **[Paweł Jastrzębski](https://github.com/darodi)** for creating Kindle Comic Converter
- The open-source community for all the amazing libraries and tools

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- STAR HISTORY - Uncomment when you have some stars! -->
<!--
## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=nilsleo/mgc-foss&type=Date)](https://star-history.com/#nilsleo/mgc-foss&Date)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---
-->

## 📸 Screenshots

<div align="center">

### Desktop Interface

> **[PLACEHOLDER: Desktop main page - light theme]**

> **[PLACEHOLDER: Desktop conversion queue with progress]**

### Mobile Interface

> **[PLACEHOLDER: Mobile main page - dark theme]**

> **[PLACEHOLDER: Mobile advanced options panel]**

</div>

---

<div align="center">

### ⭐ Found this useful?

**[Star this repo](https://github.com/nilsleo/mgc-foss/stargazers)** to help others discover it!

[![GitHub stars](https://img.shields.io/github/stars/nilsleo/mgc-foss?style=social)](https://github.com/nilsleo/mgc-foss/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/nilsleo/mgc-foss?style=social)](https://github.com/nilsleo/mgc-foss/fork)

<br/>

Made with ❤️ for the manga and comic community

<br/>

**[🌐 Try Live Demo](https://www.mangaconverter.com)** •
**[Report Bug](https://github.com/nilsleo/mgc-foss/issues)** •
**[Request Feature](https://github.com/nilsleo/mgc-foss/issues)** •
**[View Roadmap](https://github.com/nilsleo/mgc-foss#-roadmap)**

<br/>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

</div>
