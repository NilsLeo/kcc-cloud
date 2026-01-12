# FOSS Simplification Gameplan

Complete guide for converting MangaConverter to a simplified FOSS version at `../mgc-foss`.

---

## PHASE 1: Docker Compose Simplification

### Step 1.1 - Simplify docker-compose.yml

Keep only these services:
- `frontend` (production build, not dev)
- `backend` (Flask + Gunicorn)
- `celery-worker` (background jobs)
- `redis` (message broker only)

Remove:
- `postgres` (replace with SQLite)
- `minio` (replace with local volume)
- `frontend-dev` (use prod only)
- `dashboard` (optional, can keep if useful)

- [ ] **Test app**

### Step 1.2 - Add shared volume for local storage

Add to docker-compose.yml:
```yaml
volumes:
  conversion-data:  # Replaces S3
```

Map volume to services that need file access.

- [ ] **Test app**

---

## PHASE 2: Backend Cleanup

### Step 2.1 - Remove database models

In `backend/app/database/models.py`:
- Delete `User` model
- Delete `Session` model
- Keep `ConversionJob` (but switch to SQLite)
- Delete `LogEntry` (or simplify to file logging)

- [ ] **Test app**

### Step 2.2 - Remove auth code

In `backend/app/utils/`:
- Delete `clerk_auth.py`
- Delete `auth.py` (session validation)
- Remove `@require_auth` decorators from `routes.py`
- Remove `X-Session-Key` header handling
- Remove any authentication middleware

- [ ] **Test app**

### Step 2.3 - Replace S3 with local filesystem

In `backend/app/utils/storage/`:
- Delete `s3_storage.py`
- Create `local_storage.py` with methods:
  - `upload_file(file, job_id)` → saves to `/data/uploads/{job_id}/`
  - `get_file(job_id)` → reads from `/data/outputs/{job_id}/`
  - `delete_file(job_id)`
  - `get_download_url(job_id)` → returns `/download/{job_id}`

- [ ] **Test app**

### Step 2.4 - Simplify routes

In `backend/app/utils/routes.py`:
- Remove `/session` routes
- Remove presigned URL logic from `/jobs`
- Change `/jobs` to accept direct file upload
- Add simple `/download/{job_id}` route
- Remove rate limiting decorators
- Remove session/user checks

- [ ] **Test app**

### Step 2.5 - Switch to SQLite

In `backend/app/database/utils.py`:
- Change `DATABASE_URL` to `sqlite:////data/jobs.db`
- Remove connection pooling (not needed for SQLite)
- Update any PostgreSQL-specific queries

- [ ] **Test app**

### Step 2.6 - Simplify tasks.py

In `backend/app/tasks.py`:
- Remove S3 download logic, read from `/data/uploads/`
- Remove S3 upload logic, write to `/data/outputs/`
- Keep KCC conversion logic
- Remove session updates
- Remove user association logic

- [ ] **Test app**

### Step 2.7 - Remove analytics/monitoring

Throughout backend:
- Remove Sentry imports
- Remove `enhanced_logger.py` database logging
- Use simple Python logging to stdout
- Remove any analytics tracking

- [ ] **Test app**

---

## PHASE 3: Frontend Cleanup

### Step 3.1 - Remove Clerk

In `mangaconverter-fe/`:
- `package.json`: remove `@clerk/nextjs`
- `app/layout.tsx`: remove `ClerkProvider`
- Delete `app/sign-in/`
- Delete `app/sign-up/`
- Delete `app/account/`

- [ ] **Test app**

### Step 3.2 - Remove session management

In `mangaconverter-fe/hooks/`:
- Delete `use-session.ts`
- Remove session hooks from components
- Remove session state from contexts

- [ ] **Test app**

### Step 3.3 - Simplify upload flow

In `mangaconverter-fe/lib/`:
- Delete `MultipartUploadClient.ts` (no S3 multipart needed)
- Simplify `uploadFileAndConvert.ts` to:
  1. POST file directly to `/api/upload`
  2. Backend saves to `/data/uploads/`
  3. Start conversion job
  4. Poll for status
  5. Download from `/api/download/{job_id}`

- [ ] **Test app**

### Step 3.4 - Remove account-specific features

In `mangaconverter-fe/components/`:
- Remove user profile components
- Remove conversion history (or make it local-only)
- Simplify navbar (no sign-in button)
- Remove any user-specific UI elements

- [ ] **Test app**

### Step 3.5 - Simplify API routes

In `mangaconverter-fe/app/api/`:
- Remove session management from all routes
- Remove presigned URL logic
- Simplify to direct backend proxying
- Remove authentication checks

- [ ] **Test app**

### Step 3.6 - Remove analytics

Throughout frontend:
- Remove Vercel Analytics
- Remove Sentry
- Remove `bug-report-button.tsx`
- Remove any tracking code

- [ ] **Test app**

---

## PHASE 4: Configuration & Dependencies

### Step 4.1 - Update backend requirements.txt

Remove:
- `boto3`, `botocore` (S3)
- `psycopg2-binary` (PostgreSQL)
- Any Clerk SDK packages
- `sentry-sdk`

Keep:
- `Flask`, `Celery`, `Redis`, `SQLAlchemy`
- `Pillow`, `Pandas`
- `Flask-SocketIO` (if keeping WebSocket) or remove

- [ ] **Test app**

### Step 4.2 - Update frontend package.json

Remove:
- `@clerk/nextjs`
- `@sentry/nextjs`
- `@vercel/analytics`

Keep:
- `Next.js`, `React`, `TypeScript`
- `Radix UI`, `Tailwind`
- `socket.io-client` (optional)
- `react-hook-form`, `zod`

- [ ] **Test app**

### Step 4.3 - Create .env.example

Create new `.env.example` with:
```bash
# Backend
REDIS_URL=redis://redis:6379/0
DATABASE_URL=sqlite:////data/jobs.db
STORAGE_PATH=/data
FLASK_ENV=production
ALLOWED_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8060
NEXT_PUBLIC_MAX_FILE_SIZE=1073741824
```

- [ ] **Test app**

### Step 4.4 - Update Dockerfiles

In `backend/Dockerfile`:
- Remove AWS CLI
- Keep KCC, ImageMagick, poppler, 7zip
- Remove PostgreSQL client

In `frontend/Dockerfile`:
- Use production build only
- Remove dev dependencies

- [ ] **Test app**

---

## PHASE 5: Simplify Features

### Step 5.1 - Simplify job management

In `backend/`:
- Remove job cancellation (or keep if simple)
- Remove ETA estimation (delete `eta_estimator.py`, `best_model.pkl`)
- Remove rate limiting (delete `rate_limiter.py`)

- [ ] **Test app**

### Step 5.2 - Keep core features

Ensure these still work:
- Device profiles
- Advanced options (cropping, format)
- KCC conversion logic
- Job queue system

- [ ] **Test app**

### Step 5.3 - Optional: Remove WebSocket

If you want to simplify further:
- Remove `Flask-SocketIO` from backend
- Remove `socket.io-client` from frontend
- Use polling only (`useQueuePolling` hook)

- [ ] **Test app**

---

## PHASE 6: File Structure Cleanup

### Step 6.1 - Delete unused backend files

Delete from `backend/app/utils/`:
- `clerk_auth.py`
- `auth.py`
- `enhanced_logger.py`
- `eta_estimator.py`
- `rate_limiter.py`
- `best_model.pkl`
- `celery_events.py` (if removing WebSocket)

Simplify `backend/app/database/`:
- `models.py` to `ConversionJob` only

Delete from `backend/app/utils/storage/`:
- `s3_storage.py`

- [ ] **Test app**

### Step 6.2 - Delete Kubernetes configs

Delete:
- `kubernetes/` directory
- `.github/workflows/` (or simplify to basic Docker build)

- [ ] **Test app**

### Step 6.3 - Clean up frontend

Delete:
- `app/account/`
- `app/sign-in/`, `app/sign-up/`
- `hooks/use-session.ts`
- `lib/MultipartUploadClient.ts`
- `components/bug-report-button.tsx`
- `contexts/` (if session-related)

- [ ] **Test app**

---

## PHASE 7: Testing & Documentation

### Step 7.1 - Update README.md

Create clear, simple README:
```markdown
# MangaConverter FOSS

Self-hosted manga/comic converter.

## Quick Start

```bash
git clone <repo>
cd mgc-foss
cp .env.example .env
docker compose up -d
```

Open http://localhost:3000

## Architecture

- Frontend: Next.js (port 3000)
- Backend: Flask (port 8060)
- Worker: Celery
- Queue: Redis
- Storage: Local filesystem (/data)
```

- [ ] **Test app**

### Step 7.2 - Test complete workflow

Full end-to-end test:
1. Start services: `docker compose up`
2. Upload a test CBZ file
3. Select device profile
4. Convert
5. Download result
6. Check `/data/uploads/` and `/data/outputs/`

- [ ] **Test app**

---

## PHASE 8: Final Simplifications (Optional)

### Step 8.1 - Combine backend + worker

If you want even simpler deployment, merge services:
```yaml
backend:
  command: >
    sh -c "celery -A app.tasks worker --detach &&
           gunicorn app:app -w 2 -b 0.0.0.0:8060"
```

- [ ] **Test app**

### Step 8.2 - Remove SQLite, use Redis only

Store job state in Redis hashes:
- `job:{id}:status`
- `job:{id}:metadata`
- `job:{id}:result_path`

- [ ] **Test app**

---

## Quick Reference: What Gets Removed vs. Kept

### ❌ REMOVE
- PostgreSQL → SQLite
- S3/Minio → Local filesystem
- Clerk → No auth
- Sessions → No tracking
- Rate limiting
- ETA estimation
- Enhanced logging → Simple stdout
- Sentry/Analytics
- Multipart upload
- Account pages
- WebSocket (optional)

### ✅ KEEP
- Docker Compose architecture
- Frontend/Backend/Worker/Redis separation
- KCC conversion core
- Device profiles
- Advanced options
- File upload/download
- Job queue
- UI components (Radix, Tailwind)

---

## Recommended Execution Order

1. **PHASE 1** - Docker Compose infrastructure
2. **PHASE 4** - Dependencies cleanup
3. **PHASE 2** - Backend functionality changes
4. **PHASE 3** - Frontend UI changes
5. **PHASE 6** - File cleanup
6. **PHASE 7** - Testing & documentation
7. **PHASE 5 & 8** - Optional further simplifications
