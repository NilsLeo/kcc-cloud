# MangaConverter — Architecture

## Repository

| Repo | Visibility | Purpose |
|------|-----------|---------|
| `mangaconverter` | Private | All development — both editions |
| `mangaconverter-community` | Public | Self-hosted release. CI subtree export on tag. |

---

## Monorepo: pnpm workspaces

```
mangaconverter/
│
├── apps/
│   ├── api/                    NestJS monolith
│   │   ├── ConversionModule    job submission, SSE, queue routing
│   │   ├── UserModule          users, credits, subscriptions  [→ user-service extraction point]
│   │   ├── AuthModule          guards, Clerk middleware, /webhooks/clerk
│   │   ├── BillingModule       Stripe credits + subscriptions, /webhooks/stripe  [saas only]
│   │   └── AdminModule         admin endpoints, protected by ADMIN_PASSWORD
│   ├── worker/                 NestJS BullMQ processor + KCC gRPC client
│   └── frontend/               Vue 3 + Tailwind → Vercel
│
├── packages/
│   ├── @mgc/core               [internal]  entities, DTOs, interfaces
│   ├── @mgc/storage            [internal]  IStorageProvider → S3 / local fs
│   ├── @mgc/queue              [internal]  BullMQ definitions
│   ├── @mgc/events             [internal]  IEventBus → RedisStreams / EventEmitter2
│   ├── @mgc/auth-core          [internal]  IAuthProvider → ClerkAdapter (saas) / NoOpAdapter (self-hosted)
│   ├── @mgc/db                 [internal]  Prisma schemas + two generated clients
│   ├── @mgc/telemetry          [internal]  OpenTelemetry → Datadog (saas) / stdout (self-hosted)
│   ├── @mgc/ui                 [→ npm]     shared Vue components built on shadcn-vue
│   └── @mgc/conversion-sdk     [→ npm]     KCC job types, ETA predictor
│
├── worker-kcc/                 Python KCC gRPC server  [→ own repo candidate]
│
├── tools/
│   └── train_eta_model.py      reads Postgres → trains XGBoost → exports ONNX to @mgc/conversion-sdk/models/
│
└── infra/
    ├── helm/
    ├── k8s/
    └── docker-compose/
        └── docker-compose.yml  self-hosted: api + worker + redis + postgres + minio
```

Legend: **[internal]** = never published · **[→ npm]** = publish when mature · **[→ own repo]** = extract when stable

---

## Edition Switching

`main.ts` reads `MGC_EDITION` once to select the AppModule. No other code branches on edition.

| Module | SaaS | Self-hosted |
|--------|------|-------------|
| Auth | Clerk | None (optional `ADMIN_PASSWORD` gate) |
| User | Clerk users, credit ledger, subscriptions | No user concept |
| Events | Redis Streams | EventEmitter2 |
| Storage | Cloudflare R2 | Local filesystem |
| Billing | Stripe | Not imported |
| Telemetry | Datadog | stdout |

---

## Hosting

| Component | Hosting |
|-----------|---------|
| `frontend` | Vercel — static SPA, PR preview deploys |
| `api` | Railway — auto-deploy from `main` |
| `worker` + KCC sidecar | Hetzner k8s — KEDA autoscaling, tiered node pools |
| Redis | Upstash (reachable from Railway + k8s) |
| Postgres | Neon — built-in PgBouncer, branching, EU region |
| Storage | Cloudflare R2 |

API CORS allowlists the production Vercel domain and `*.vercel.app` for PR previews.

---

## Self-Hosted Deployment

One container, one command:

```
docker run -p 3000:3000 -v ./data:/data ghcr.io/nilsleo/mangaconverter
```

Runs four processes via supervisord: `api`, `worker`, `worker-kcc`, and an embedded `redis-server`. All state written to the `/data` volume. SQLite. Files stored under `/data/files`.

`MGC_INIT=true` on first run runs migrations and seeds initial config.

---

## Worker Pod — Sidecar (SaaS)

Each worker pod: **NestJS BullMQ processor** + **Python KCC gRPC server** sharing localhost over `localhost:50051`. The gRPC proto lives in `worker-kcc/`.

### KCC_WORKERS

`KCC_WORKERS` caps the process pool size for all three parallel phases inside KCC:

| Phase | Pool controlled |
|-------|----------------|
| MuPDF page extraction (`mupdf_pdf_process_pages_parallel`) | `Pool(processes=KCC_WORKERS)` |
| Image processing (`imgDirectoryProcessing`) | `Pool(processes=KCC_WORKERS)` |
| MOBI packaging (`makeMOBI`) | `Pool(min(4, KCC_WORKERS))` |

Default `cpu_count()` if unset. NestJS worker passes the correct value per tier via `ConvertRequest.kcc_workers` — always set explicitly.

**Dockerfile:** requires `libc6-i386` + `lib32stdc++6` (kindlegen is 32-bit). Download kindlegen from archive.org to `/opt/kcc/kindlegen/kindlegen` at build time.

Queue tiers routed at submission by file size:

| Queue | File size | KCC_WORKERS | Memory limit | KEDA trigger |
|-------|-----------|-------------|--------------|--------------|
| `conversion:small`  | < 100 MB   | 1 | 1.5 GB | 1 replica / 4 queued |
| `conversion:medium` | 100–500 MB | 2 | 3 GB   | 1 replica / 2 queued |
| `conversion:large`  | > 500 MB   | 2 | 5.5 GB | 1 replica / 1 queued |

---

## Job Flow

**Upload:**
1. `POST /jobs/prepare` → validates MIME type + size (max 2 GB; accepted: `application/pdf`, `application/x-cbz`, `application/zip`), extracts page count from PDF using **`pdf-lib`** (pure JS, no native deps), creates job in Redis (status: `UPLOADING`), returns upload URL
   - **SaaS:** returns presigned R2 multipart URLs (client uploads direct to R2, 100 MB per part)
   - **Community:** returns local API upload URL (`POST /jobs/:id/upload`) — no presigned URLs, file streams directly to API and is written to `/data/files/input/{job_id}/`
2. Client uploads file to the returned URL
3. `POST /jobs/:id/finalize` → API checks quota (anonymous: `anon:{visitor_id}:usage` ≤ 3; free: `user:{id}:usage` ≤ 25; pro: skip), runs ETA prediction, enqueues to BullMQ tier
4. Response includes `eta_s` and queue position
5. Client opens SSE to `GET /jobs/:id/progress`

**Progress (SSE):**
1. Worker writes progress to Redis job hash, publishes to Redis pub/sub channel
2. Any API pod subscribed to that channel pipes events into the open SSE response
3. On reconnect, API sends full Redis hash immediately before resuming live events

**Cancellation:**
- Queued: remove from BullMQ, refund credit, write terminal state
- Processing: publish cancel signal → NestJS processor → `Cancel` gRPC to KCC → SIGTERM → cleanup, refund credit

**Terminal state:** worker writes full job record to Postgres, emits domain event, schedules input file cleanup. Redis TTL is 24 hours (download links stay valid).

**Output file naming:** `{original_basename_without_ext}.{format}` lowercased. Example: `My_Manga.PDF` → `my_manga.epub`.

**Data retention (GDPR):** input files deleted immediately after conversion completes. Output files deleted 24 h after first download or 24 h after `COMPLETE` if never downloaded. Job metadata (status, timestamps, sizes) retained in Postgres indefinitely for billing and analytics. No personal data stored on anonymous jobs.

---

## Job State

All live state (status, progress, phase, ETA, file paths) in a Redis hash keyed by job ID. Postgres written only on terminal states.

### Status Definitions

| Status | Terminal | Description |
|--------|----------|-------------|
| `UPLOADING` | | File parts being uploaded direct to storage |
| `QUEUED` | | Upload complete, waiting in BullMQ |
| `PROCESSING` | | Worker has picked up the job, KCC running |
| `COMPLETE` | ✓ | Conversion finished, output file ready |
| `DOWNLOADED` | ✓ | User has downloaded the output file |
| `ERRORED` | ✓ | Conversion failed |
| `CANCELLED` | ✓ | Manually cancelled by user |
| `ABANDONED` | ✓ | Timed out with no activity |

Transitions are timestamped (`queued_at`, `processing_at`, `completed_at`, …) and stored in Postgres on terminal write.

---

## Events

| Stream | Producers | Consumers |
|--------|-----------|-----------|
| `events:job.completed` | worker | billing (finalise usage), notification |
| `events:job.failed` | worker | billing (refund credit), notification |
| `events:credit.depleted` | api | notification |

SaaS uses Redis Streams with consumer groups. Self-hosted uses in-process EventEmitter2.

---

## Database

**SaaS:** Neon Postgres via built-in PgBouncer pooler endpoint (transaction mode).

**Self-hosted:** SQLite.

`@mgc/db` generates two independent Prisma clients — `base` and `saas`. Schemas can diverge: the saas schema adds columns, foreign keys, and tables that don't exist in base.

| | Base (community) | SaaS |
|-|-----------------|------|
| `jobs` | id, status, file paths, timestamps | + user_id |
| `users` | — | id, clerk_id, email, is_pro, stripe_customer_id |
| `subscriptions` | — | user_id, stripe_subscription_id, status, current_period_end |

Business logic uses `@mgc/core` repository interfaces only — never Prisma directly. Migrations run as a k8s init container (saas) or on container start (self-hosted).

---

## Auth

**SaaS:** Clerk — SSO, OAuth, MFA. JWT verified without a DB call. `user.created` webhook provisions the user row in Postgres.

Anonymous users get a **visitor ID** (UUID httpOnly cookie `mgc_visitor`, 30-day TTL) on first visit — purely a Redis key prefix, not a session.

| User type | Can convert | Quota | Job history |
|-----------|-------------|-------|-------------|
| Anonymous | ✓ | 3 lifetime (cookie-scoped) | current session only |
| Free (signed in) | ✓ | 25 / month | persistent |
| Pro (signed in) | ✓ | unlimited | persistent |

After 3 anonymous conversions the API returns `402 signup_required`. The frontend shows a signup prompt at that point — not before. Anonymous job history is not migrated on signup.

**Anonymous user signs up mid-job:** in-flight job continues uninterrupted. Visitor cookie persists as a Redis key alongside the Clerk JWT. Future jobs attributed to Clerk user ID.

Anonymous quota: `anon:{visitor_id}:usage` in Redis, TTL 30 days.

**Self-hosted:** No auth. Assumed to run behind a VPN or reverse proxy. Optional `ADMIN_PASSWORD` env var for a simple password gate.

---

## Billing

SaaS only. Self-hosted is free. Simple monthly subscription — no credit system.

| Plan | Price | Conversions / month |
|------|-------|---------------------|
| Free | — | 25 / month |
| Pro | $9.99 / mo | Unlimited |

**Quota flow:** atomic `INCR user:{id}:usage` at finalize; reject `402` at limit. Pro users skip via `user:{id}:is_pro` flag. Cancelled/errored jobs decrement.

**Stripe integration:**
- Subscription: Stripe Checkout → `checkout.session.completed` webhook → set `user:{id}:is_pro` in Redis + `is_pro=true` in Postgres
- Monthly renewal: `invoice.paid` webhook → reset `user:{id}:usage` counter in Redis
- Cancellation: Stripe Customer Portal → `customer.subscription.deleted` webhook → remove `user:{id}:is_pro` flag, revert to free tier
- All Stripe webhook endpoints excluded from Clerk auth middleware, verified via `stripe-signature` HMAC header

**Free tier monthly reset:** `user:{id}:usage` TTL is `EXPIREAT` end-of-month — key expires naturally. On `INCR`, if key is new also set `EXPIREAT`. No cron job.

**Refunds:** mailto link on each completed job, pre-filled with job ID + filename. Manual via Stripe dashboard.

**Future:** per-job credits ($0.49) once subscription is validated.

**Donations:** static Stripe Payment Link in community README + self-hosted footer.

---

## Observability

**SaaS:** Datadog via OTLP — APM, logs, metrics, BullMQ spans, gRPC calls, frontend RUM. Set `DD_API_KEY` + `DD_SITE`.

**Self-hosted:** JSON logs to stdout only.


---

## Secrets

**SaaS (k8s):** External Secrets Operator syncs from Doppler into k8s Secrets. **Railway API:** env vars set in Railway dashboard. **Self-hosted:** `.env` generated on first run. `.env.example` documents every key.

---

## Technical Reference

### API Contract

**Base path:** `/api/v1` (SaaS) · `/api` (self-hosted)

All errors: `{ "error": "string", "reason": "string" | undefined }`.

**Rate limiting:** `ThrottlerModule` — 10 req/min per IP on `POST /jobs/prepare` only.

| Method | Path | Auth | Request body | Success | Errors |
|--------|------|------|-------------|---------|--------|
| `POST` | `/jobs/prepare` | optional | `{ filename, size_bytes }` | `200 { job_id, upload_url, upload_parts? }` | `400 invalid_file` · `413 file_too_large` · `415 unsupported_type` |
| `POST` | `/jobs/:id/upload` | — | `multipart/form-data` file stream | `204` | `404` · `413` |
| `POST` | `/jobs/:id/finalize` | optional | `{ device, format, options }` | `200 { job_id, eta_s, queue_position }` | `402 signup_required\|upgrade_required` · `404` · `409 already_finalized` |
| `GET` | `/jobs/:id` | optional | — | `200 Job` | `404` |
| `GET` | `/jobs/:id/progress` | optional | SSE | `JobProgressEvent` stream | `404` |
| `DELETE` | `/jobs/:id` | optional | — | `204` | `404` · `409 already_terminal` |
| `GET` | `/jobs` | required | `?page&limit` | `200 { jobs, total }` | `401` |
| `POST` | `/billing/subscribe` | required | — | `200 { checkout_url }` | `401` · `409 already_pro` |
| `POST` | `/billing/portal` | required | — | `200 { portal_url }` | `401` |
| `POST` | `/webhooks/clerk` | HMAC | Clerk event | `200` | — |
| `POST` | `/webhooks/stripe` | HMAC | Stripe event | `200` | — |

**`POST /jobs/finalize` request:**
```json
{
  "device": "KV",
  "format": "mobi",
  "options": { "manga": true, "hq": false, "webtoon": false, "two_panel": false, "upscale": false }
}
```

**Job object:**
```ts
{
  id: string
  status: 'UPLOADING' | 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'DOWNLOADED' | 'ERRORED' | 'CANCELLED' | 'ABANDONED'
  filename: string
  output_filename: string | null   // "{basename}.{format}" lowercase
  format: 'epub' | 'mobi' | 'cbz' | null
  device: string | null
  page_count: number | null
  file_size_bytes: number | null
  output_size_bytes: number | null
  eta_s: number | null
  elapsed_s: number | null
  error_message: string | null
  download_url: string | null      // presigned, valid 24 h after COMPLETE
  created_at: string               // ISO 8601
  completed_at: string | null
}
```

**`JobProgressEvent` (SSE):**
```json
{ "phase": "imgproc", "progress": 67, "status": "PROCESSING", "eta_s": 180, "message": "Processing images..." }
```

---

### Redis Key Reference

| Key | Type | TTL | Owner | Description |
|-----|------|-----|-------|-------------|
| `job:{id}` | Hash | 24 h (set at COMPLETE) | API create · Worker update | All live job state |
| `jobs:{id}:progress` | Pub/Sub channel | — | Worker → API SSE | Live progress fan-out |
| `user:{id}:usage` | String (int) | EXPIREAT end-of-month | API `INCR` · `invoice.paid` reset | Monthly conversion count |
| `user:{id}:is_pro` | String `"1"` | None | BillingModule webhooks | Pro subscription flag |
| `anon:{visitor_id}:usage` | String (int) | 30 days | API `INCR` | Anonymous lifetime usage |
| `bull:{queue}:*` | Various | BullMQ managed | BullMQ internals | Do not touch directly |

**`job:{id}` hash fields:** `status`, `phase`, `progress`, `eta_s`, `kcc_workers`, `input_path`, `output_path`, `queued_at`, `processing_at`, `completed_at`, `error_message`.

---

### Prisma Schemas

**Base** — `packages/@mgc/db/prisma/base/schema.prisma`:
```prisma
datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}
generator client {
  provider = "prisma-client-js"
  output   = "../../node_modules/.prisma/base-client"
}
model Job {
  id                String    @id @default(cuid())
  status            String    @default("UPLOADING")
  filename          String
  output_filename   String?
  format            String?
  device            String?
  page_count        Int?
  file_size_bytes   BigInt?
  output_size_bytes BigInt?
  eta_s             Float?
  elapsed_s         Float?
  error_message     String?
  input_path        String?
  output_path       String?
  queued_at         DateTime?
  processing_at     DateTime?
  completed_at      DateTime?
  created_at        DateTime  @default(now())
  updated_at        DateTime  @updatedAt
}
```

**SaaS** — `packages/@mgc/db/prisma/saas/schema.prisma`:
```prisma
datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DATABASE_DIRECT_URL")
}
generator client {
  provider = "prisma-client-js"
  output   = "../../node_modules/.prisma/saas-client"
}
model Job {
  id                String    @id @default(cuid())
  status            String    @default("UPLOADING")
  filename          String
  output_filename   String?
  format            String?
  device            String?
  page_count        Int?
  file_size_bytes   BigInt?
  output_size_bytes BigInt?
  eta_s             Float?
  elapsed_s         Float?
  error_message     String?
  input_path        String?
  output_path       String?
  queued_at         DateTime?
  processing_at     DateTime?
  completed_at      DateTime?
  created_at        DateTime  @default(now())
  updated_at        DateTime  @updatedAt
  user_id           String?
  user              User?     @relation(fields: [user_id], references: [id])
}
model User {
  id                 String        @id @default(cuid())
  clerk_id           String        @unique
  email              String        @unique
  is_pro             Boolean       @default(false)
  stripe_customer_id String?
  created_at         DateTime      @default(now())
  updated_at         DateTime      @updatedAt
  jobs               Job[]
  subscription       Subscription?
}
model Subscription {
  id                     String   @id @default(cuid())
  user_id                String   @unique
  stripe_subscription_id String   @unique
  status                 String
  current_period_end     DateTime
  created_at             DateTime @default(now())
  updated_at             DateTime @updatedAt
  user                   User     @relation(fields: [user_id], references: [id])
}
```

---

### gRPC Proto

`worker-kcc/proto/conversion.proto`:
```protobuf
syntax = "proto3";
package conversion;

service Converter {
  rpc Convert(ConvertRequest) returns (stream ProgressEvent);
  rpc Cancel(CancelRequest)   returns (CancelResponse);
}

message ConvertRequest {
  string job_id      = 1;
  string input_path  = 2;
  string output_dir  = 3;
  string format      = 4;   // "epub" | "mobi" | "cbz"
  string device      = 5;
  int32  kcc_workers = 6;
  bool   manga       = 7;
  bool   hq          = 8;
  bool   webtoon     = 9;
  bool   two_panel   = 10;
  bool   upscale     = 11;
}

message ProgressEvent {
  string job_id      = 1;
  string phase       = 2;   // "mupdf" | "imgproc" | "epub" | "mobi" | "complete" | "error" | "cancelled"
  int32  progress    = 3;   // 0–100
  string status      = 4;
  string message     = 5;
  string output_path = 6;   // populated on phase="complete"
}

message CancelRequest {
  string job_id = 1;
}

message CancelResponse {
  bool   success = 1;
  string message = 2;
}
```

---

### Environment Variables

**`apps/api`:**

| Variable | Editions | Default | Description |
|----------|----------|---------|-------------|
| `MGC_EDITION` | all | — | `community` \| `saas` |
| `PORT` | all | `3000` | HTTP listen port |
| `DATABASE_URL` | all | — | SQLite path or Neon pooler URL |
| `DATABASE_DIRECT_URL` | saas | — | Neon direct URL (migrations) |
| `REDIS_URL` | all | — | Redis or Upstash URL |
| `ADMIN_PASSWORD` | all | — | Optional AdminModule gate |
| `STORAGE_PATH` | community | `/data/files` | Local file storage root |
| `CLERK_SECRET_KEY` | saas | — | |
| `CLERK_WEBHOOK_SECRET` | saas | — | |
| `STRIPE_SECRET_KEY` | saas | — | |
| `STRIPE_WEBHOOK_SECRET` | saas | — | |
| `STRIPE_PRO_PRICE_ID` | saas | — | |
| `R2_ACCOUNT_ID` | saas | — | |
| `R2_ACCESS_KEY_ID` | saas | — | |
| `R2_SECRET_ACCESS_KEY` | saas | — | |
| `R2_BUCKET` | saas | `mangaconverter` | |
| `DD_API_KEY` | saas | — | |
| `DD_SITE` | saas | `datadoghq.eu` | |
| `THROTTLE_TTL` | all | `60` | ThrottlerModule window (s) |
| `THROTTLE_LIMIT` | all | `10` | Max requests per window |

**`apps/worker`:**

| Variable | Editions | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | all | — | Same as API |
| `DATABASE_URL` | all | — | Same as API |
| `KCC_GRPC_ADDR` | all | `localhost:50051` | KCC sidecar gRPC address |
| `STORAGE_PATH` | community | `/data/files` | Must match API value |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` | saas | — | |

**`worker-kcc`:**

| Variable | Default | Description |
|----------|---------|-------------|
| `GRPC_PORT` | `50051` | gRPC listen port |
| `KCC_WORKERS` | `cpu_count()` | Default pool size — overridden per-job via `ConvertRequest.kcc_workers` |
| `KINDLEGEN_PATH` | `/opt/kcc/kindlegen/kindlegen` | Path to 32-bit kindlegen binary |

---

## CI/CD

GitHub Actions on push to `main`:
1. Build packages, run tests
2. Build and push Docker images to GHCR (tagged by commit SHA)
3. SaaS: `helm upgrade`, Prisma init container runs migrations before API pods start
4. Self-hosted: image tags published to release notes
5. Vercel deploys frontend automatically via GitHub integration. PR previews per branch.

---

## Frontend UI

### Pages

**`/` — Converter**
Single-purpose page, the whole product. No navigation clutter.

- **Header** — sticky, minimal. Logo + wordmark left. Theme toggle + Sign In ghost button (anonymous) or user avatar dropdown (authenticated, links to History and Account) right.
- **Hero** — centered mode toggle (MANGA / COMIC) as two pills — switches title font and accent colour. Single h1 below ("Manga Converter" / "Comic Converter"), one-line subtitle. Nothing else above the fold except the upload zone.
- **Upload zone** — large centered card, dashed border, mode-specific icon (scales on hover/drag, pulses on drag-over). "Drop your file here or click to browse." Single file, PDF or CBZ.
- **Configuration drawer** — shadcn-vue Sheet sliding in from the right immediately after file drop, before conversion starts. Contains: device selector (grouped dropdown — Kindle, Kobo, reMarkable, Other), output format (Auto / EPUB / MOBI / CBZ), Advanced accordion (collapsed by default) with manga mode, HQ, webtoon, two-panel, upscale toggles. Sticky "Convert" button at bottom — closes drawer and starts conversion.
- **Progress view** — replaces upload zone after conversion starts. Three-stage timeline (horizontal desktop, vertical mobile): Upload → Converting → Done. Active stage pulses. Converting stage shows live ETA countdown ticking client-side every second + upload speed during upload stage. On completion, timeline collapses to a large Download button with output filename and file size. "Convert another" link below resets the page.
- **Anonymous nudge** — slim non-blocking info banner below progress view after job completes. "Sign up to keep your files for longer and track your history." Dismiss button. Anonymous users only.
- **Quota wall** — Modal (not a redirect) triggered by `402` response. Anonymous: "You've used your 3 free conversions — sign up for 25/month free." Free tier at limit: "You've hit your monthly limit — upgrade to Pro for unlimited." Both embed Clerk SignIn/SignUp + inline pricing comparison. Dismissible for anonymous only.

---

**`/pricing`**
Three shadcn-vue Cards side by side: Free / Pro / Self-hosted. Free and Self-hosted outlined, Pro highlighted with "Most popular" badge. Feature checklist rows, single CTA per card. Linked from quota wall modal and header.

---

**`/history`** *(authenticated only)*
Full-width table: filename, device, format, status badge, elapsed time, date, download button (active within 24h TTL, greyed after). Row expands inline to show file size, page count, ETA vs actual. "Request refund" mailto link per row. Anonymous visitors redirected to signin modal.

---

**`/account`** *(authenticated only)*
Two stacked cards: account info (email, Clerk-managed) + subscription status (plan, renewal date, Upgrade or Manage Subscription button via Stripe). Below: red-bordered Danger Zone card with Delete Account.

---

### Component map

| Component | Type | Description |
|-----------|------|-------------|
| `FileDropzone` | custom | Drag-and-drop upload zone, mode-aware icon, drag animations |
| `TimelineProgress` | custom | Three-stage SSE-driven progress, live ETA countdown, upload speed |
| `StatusBadge` | custom | Colour-coded job status pill |
| `DeviceSelect` | custom | Grouped device dropdown (Kindle / Kobo / reMarkable / Other) |
| `QuotaWallModal` | custom | 402 handler modal with embedded Clerk + pricing |
| `ConversionDrawer` | custom | Right-side Sheet for conversion options |
| All primitives | shadcn-vue | Card, Sheet, Dialog, Button, Badge, Progress, Accordion, Select, Input, Separator, DropdownMenu, Avatar |

### Key interaction rules

- No page reloads — all state transitions via Pinia stores
- SSE consumed by `useJobProgress(jobId)` composable driving timeline and ETA reactively
- Dark mode default, light toggle, persisted to localStorage
- Mobile: upload zone and timeline stack vertically, ConversionDrawer becomes a bottom Sheet on small screens
- Quota wall is always a modal — never a redirect that loses the user's current file

---

## ETA Predictor

Predicted at `POST /jobs/finalize` using submit-time features. Runs in TypeScript via `onnxruntime-node` in `@mgc/conversion-sdk`.

### Features

| Feature | Source |
|---------|--------|
| `file_size_mb` | upload metadata |
| `page_count` | extracted from PDF during prepare step |
| `mb_per_page` | derived (`file_size_mb / page_count`) |
| `output_format` | user input (EPUB / MOBI) |
| `device_profile` | user input (Kindle device) |
| `kcc_workers` | determined by queue tier |

### Model

XGBoost regressor on `elapsed_seconds = completed_at − processing_at`. Exported to ONNX via `onnxmltools`, stored at `packages/@mgc/conversion-sdk/models/eta_v{n}.onnx` (~100 KB, committed).

**Cold start:** bootstrap model ships with the package; replaced once ≥ 100 real jobs accumulate.

**Retraining:** `tools/train_eta_model.py` → new ONNX committed, weekly CI schedule.

**Fallback:** formula-based estimate if ONNX fails to load.

### Important calibration note

For MOBI output, KCC's `makeBook` timer wraps the entire pipeline (MuPDF + imgproc + kindlegen). Do not add preprocessing time separately — it is already included. EPUB has no `makeBook` phase; predict `mupdf + imgproc` only.

---

## Service Extraction Roadmap

| Trigger | Action |
|---------|--------|
| Auth/user queries bottleneck API | `UserModule` → standalone NestJS service, HTTP REST behind `IUserService` |
| Billing logic warrants isolation | `BillingModule` → standalone service, same pattern |
| Event volume > 1M/day | Swap `RedisStreamAdapter` → `KafkaAdapter` in `EventModule` |
| Component library has external consumers | Publish `@mgc/ui` to npm |

---

## Build Roadmap

Community edition first; SaaS slots in behind existing interfaces. **Complete rewrite** — reference repos below are for inspiration only, not copy-paste.

| Repo | What to reference |
|------|------------------|
| `~/Development/mgc/mangaconverter` | Job status machine, Celery task structure, `backend/app/utils/`, k8s manifests in `kubernetes/` |
| `~/Development/mgc/mangaconverter-fe` | UI/UX patterns, component structure (Next.js — translate to Vue 3) |
| `~/Development/mgc-comparison/kcc-memory-efficient` | `KCC_WORKERS` patch, kindlegen Dockerfile, benchmark data |
| `~/Development/mgc-comparison/eta_predict.py` | ETA formula calibration constants and corrected MOBI formula |
| `~/Development/REWRITE.md` | Adapter pattern rationale and variation point analysis |

---

### Phase 0 — Project structure + shared contracts
> Interfaces only. Nothing in `apps/` imports a concrete class.

- [ ] Init pnpm workspace with `apps/`, `packages/`, `worker-kcc/`, `tools/`, `infra/` dirs
- [ ] Configure root `tsconfig.json`, ESLint, Prettier across workspace
- [ ] GitHub Actions CI: install → build (no tests yet — testing is Phase 10)
- [ ] `@mgc/core` — define all domain entities (`Job`, `User`) and **every interface**: `IJobRepository`, `IStorageProvider`, `IEventBus`, `IAuthProvider`, `IEtaPredictor`. No implementations yet — interfaces only.
- [ ] `@mgc/conversion-sdk` — job type definitions, `JobStatus` enum, `ConversionTier` enum
- [ ] `@mgc/queue` — BullMQ queue definitions and typed job payloads for all three tiers
- [ ] `@mgc/db` — base Prisma schema (jobs, files, conversion_profiles), generate base client, first migration
- [ ] `@mgc/events` — `IEventBus` with `emit()` + `subscribe()`, `EventEmitter2LocalAdapter`
- [ ] `@mgc/storage` — `IStorageProvider` interface only
- [ ] `@mgc/auth-core` — `IAuthProvider` interface, `NoOpAuthProvider` (passes all requests)
- [ ] `@mgc/telemetry` — Pino structured logger, stdout transport, wire into NestJS logger
- [ ] Verify: `pnpm build` passes across all packages with zero cross-package concrete imports

---

### Phase 1 — KCC gRPC server

- [ ] Define gRPC proto in `worker-kcc/` — `ConvertRequest` (includes `kcc_workers: int`), `ProgressEvent`, `ConvertResponse`, `CancelRequest`
- [ ] Wrap existing KCC Python logic in a thin gRPC server (`grpc.aio`) implementing `Convert` (streaming) and `Cancel`
- [ ] `ConvertRequest.kcc_workers` is written to `KCC_WORKERS` env before spawning KCC — controls all three internal pool sizes (`mupdf`, `imgproc`, `makeMOBI`)
- [ ] `Convert` emits `ProgressEvent` for each KCC phase: `mupdf`, `imgproc`, `epub`, `mobi`
- [ ] Graceful `Cancel`: send SIGTERM to KCC subprocess, clean up temp files, stream final `ProgressEvent` with `status: CANCELLED`
- [ ] Dockerfile: add `dpkg --add-architecture i386`, `libc6-i386`, `lib32stdc++6` (kindlegen is a 32-bit binary); download kindlegen from archive.org to `/opt/kcc/kindlegen/kindlegen` at build time
- [ ] Build `worker-kcc` Docker image, run end-to-end: send a PDF with `kcc_workers=1`, verify streamed progress and output file
- [ ] Verify `kcc_workers=2` produces faster output on a multi-page PDF
- [ ] Unit tests for cancel and error paths

---

### Phase 2 — Worker

- [ ] `apps/worker` NestJS app — BullMQ processors for `conversion:small`, `conversion:medium`, `conversion:large`, each with `concurrency: 1` (one job per pod; KEDA adds pods for parallelism)
- [ ] gRPC client to `localhost:50051` — calls `Convert`, streams `ProgressEvent` back
- [ ] On each `ProgressEvent`: write progress fields to Redis job hash + publish to `jobs:{id}:progress` pub/sub channel
- [ ] On `COMPLETE`: call `IJobRepository.saveTerminal()`, emit `events:job.completed` via `IEventBus`, schedule input file cleanup
- [ ] On `ERRORED` / `CANCELLED`: same terminal write path, emit corresponding event
- [ ] BullMQ stalled-job detection configured (heartbeat + `stalledInterval`)
- [ ] Worker Docker image builds cleanly alongside `worker-kcc` sidecar image

---

### Phase 3 — Community API

- [ ] `apps/api` NestJS monolith, `MGC_EDITION=community` AppModule wiring:
  - `NoOpAuthProvider` → `IAuthProvider`
  - Local filesystem adapter → `IStorageProvider`
  - `EventEmitter2LocalAdapter` → `IEventBus`
  - Base Prisma `JobRepository` → `IJobRepository`
- [ ] `IStorageProvider` local filesystem adapter: `putObject`, `getPresignedUploadUrl`, `getPresignedDownloadUrl`, `deleteObject`
- [ ] `ConversionModule`:
  - `POST /jobs/prepare` — extract page count from PDF, create job in Redis (`UPLOADING`), return local upload URL
  - `POST /jobs/:id/finalize` — move file to storage, run `IEtaPredictor`, enqueue to correct BullMQ tier, return `eta_s` + queue position
  - `GET /jobs/:id` — read from Redis (live) or Postgres (terminal)
  - `GET /jobs/:id/progress` — SSE endpoint, subscribe to Redis pub/sub, flush current Redis hash on connect
  - `DELETE /jobs/:id` — cancel (BullMQ remove if queued, or publish cancel signal if processing)
  - `GET /jobs` — job history from Postgres
- [ ] `AdminModule` — admin endpoints behind `AdminGuard` (password from `ADMIN_PASSWORD`)
- [ ] `@mgc/conversion-sdk` — formula-based `EtaPredictor` implementing `IEtaPredictor` (MOBI: `makeBook` total only; EPUB: `mupdf + imgproc`)
- [ ] SQLite support confirmed in base Prisma schema
- [ ] Build single community Docker image: supervisord running `api` + `worker` + `worker-kcc` + `redis-server`, all state in `/data`
- [ ] `MGC_INIT=true` first-run: migrate, seed config
- [ ] End-to-end: `docker run` → upload PDF → convert → SSE progress → download ✓

---

### Phase 4 — Community frontend

- [ ] Bootstrap `apps/frontend` — Vite + Vue 3 + Tailwind + Vue Router + Pinia
- [ ] Install shadcn-vue, configure theme tokens (colour, radius, font) in `tailwind.config.ts`
- [ ] `@mgc/ui` — wrap and extend shadcn-vue components needed across apps: FileDropzone, StatusChip, ProgressBar (not in shadcn-vue core)
- [ ] Upload flow: drag-and-drop or file picker → prepare → chunked multipart → finalize
- [ ] Progress view: SSE-driven, phase label (`Extracting pages`, `Processing images`, `Building EPUB`), progress bar, live ETA countdown
- [ ] Result view: download button, file size, elapsed time
- [ ] Job history: list of past jobs with status, file name, elapsed time, re-download link (within 24h TTL)
- [ ] Error states: upload failed, conversion failed, abandoned — clear messaging and retry option
- [ ] Responsive layout — works on mobile (users uploading from tablet)
- [ ] Donations nudge — passive Stripe Payment Link in footer ("Support the project")
- [ ] `vercel.json` SPA rewrite, deploy to Vercel
- [ ] Self-hosted: static build served by nginx in the single Docker image

---

### Phase 5 — Community release

- [ ] Create `mangaconverter-community` public GitHub repo
- [ ] CI: on version tag, `git subtree push` to community repo — strips `BillingModule`, `ClerkAdapter`, `R2Adapter`, saas Prisma schema, all SaaS-only code
- [ ] Verify community repo builds and runs cleanly from scratch with no private deps
- [ ] Write self-hosted setup guide (README): one-command install, volume layout, `ADMIN_PASSWORD`, upgrading
- [ ] GitHub issue templates, contributing guide, MIT licence
- [ ] Publish first release with changelog
- [ ] Publish `@mgc/ui` to npm if stable enough

---

### Phase 6 — SaaS edition (auth + billing)

- [ ] Set up Clerk project, configure OAuth + email providers
- [ ] `ClerkAdapter` implementing `IAuthProvider` — JWT verification, `userId` extraction
- [ ] Visitor ID middleware — assign UUID as httpOnly `mgc_visitor` cookie on first request (30-day TTL), attach to request context alongside any Clerk JWT. No session store — UUID is only a Redis key.
- [ ] `AuthModule` — `ClerkAuthGuard` for authenticated routes, `POST /webhooks/clerk`: `user.created` → provision user row in Postgres
- [ ] `@mgc/db` — saas Prisma schema: `users`, `credits_ledger`, `subscriptions`; extend `jobs` with `user_id`, `credits_used`
- [ ] Saas Prisma repository implementations (user-scoped `JobRepository`, `CreditRepository`)
- [ ] `R2StorageAdapter` implementing `IStorageProvider` — presigned multipart upload + download
- [ ] `BillingModule`:
  - Anonymous quota: `INCR anon:{visitor_id}:usage` (TTL 30 days), reject `402` with `reason: signup_required` after 3
  - Free quota: `INCR user:{id}:usage`, reject `402` with `reason: upgrade_required` after 25
  - Pro users bypass both checks via `user:{id}:is_pro` flag in Redis
  - Decrement counter on `CANCELLED` and `ERRORED`
  - `POST /billing/subscribe` — Stripe Checkout Session (Pro subscription)
  - `POST /billing/portal` — Stripe Customer Portal (cancel/manage)
  - `POST /webhooks/stripe` — `checkout.session.completed` (set pro flag), `invoice.paid` (reset usage counter), `customer.subscription.deleted` (remove pro flag)
- [ ] "Request refund" mailto link on each completed job — pre-fills job ID, file name, prompt for issue description
- [ ] `MGC_EDITION=saas` AppModule — swap in `ClerkAdapter`, `R2StorageAdapter`, `RedisStreamAdapter`, saas repositories, `BillingModule`
- [ ] Frontend: anonymous users can upload and convert with no prompt — signup wall only appears on `402 signup_required` response
- [ ] Frontend: Clerk `<SignIn>` / `<SignUp>` modal triggered by `402`, not by page load
- [ ] Frontend: credit balance display, top-up flow, subscription page
- [ ] Frontend: feature-gated routes rendered only when API returns billing flags
- [ ] End-to-end SaaS test: sign up → 3 free jobs → credit depleted → top up → convert again ✓

---

### Phase 7 — SaaS infrastructure
- [ ] Set up Hetzner k8s cluster, label nodes `worker-tier=small/medium/large`
- [ ] Set up Upstash Redis, verify reachability from Railway and k8s
- [ ] Deploy `apps/worker` + `worker-kcc` sidecar as k8s Deployments
- [ ] Apply KEDA `ScaledObjects` for all three queue tiers
- [ ] Deploy `apps/api` to Railway, configure all env vars
- [ ] Set up Doppler, import all secrets
- [ ] Install External Secrets Operator, wire Doppler → k8s Secrets
- [ ] Helm chart for worker + sidecar, Prisma init container for migrations
- [ ] CI: `helm upgrade` on push to `main`, Docker build skipped on frontend-only changes
- [ ] Neon branch per feature branch strategy, deleted on PR merge
- [ ] `RedisStreamAdapter` with consumer groups wired for saas event bus

---

### Phase 8 — Observability + hardening
- [ ] Set up Datadog account, `DD_API_KEY` in Doppler
- [ ] `@mgc/telemetry` — OpenTelemetry OTLP exporter to Datadog Agent, replace stdout transport in saas
- [ ] Instrument BullMQ job spans, gRPC calls, SSE connection lifecycle
- [ ] Frontend: Datadog RUM + session replay
- [ ] Datadog dashboards: job throughput, queue depth per tier, credit spend, error rate, p95 conversion time
- [ ] Alerts: queue depth spike, error rate > 1%, worker pod OOM, p95 latency regression
- [ ] Neon daily `pg_dump` CronJob → R2 backup bucket
- [ ] Load test: 100 concurrent jobs across all three tiers, verify KEDA scaling behaviour

---

### Phase 9 — ETA model (ML)
> Start only after ≥ 100 real production jobs.

- [ ] Confirm `page_count`, `file_size_mb`, `output_format`, `device_profile`, `elapsed_seconds` stored on every completed job
- [ ] Collect ≥ 100 completed jobs
- [ ] `tools/train_eta_model.py` — read Postgres, engineer features (`mb_per_page`, encoded categoricals), train XGBoost, evaluate MAE vs formula baseline
- [ ] Export to `packages/@mgc/conversion-sdk/models/eta_v1.onnx` via `onnxmltools`
- [ ] `EtaPredictor` in `@mgc/conversion-sdk` — load ONNX via `onnxruntime-node` at startup, fall back to formula on load failure
- [ ] Wire into `POST /jobs/finalize`
- [ ] Commit model, add weekly CI retrain schedule

---

### Phase 10 — Testing & CI hardening
> After Phase 5 ships. Don't write tests speculatively.

- [ ] Unit tests: `@mgc/core` domain logic, `EtaPredictor` formula, queue routing thresholds — **Vitest**
- [ ] Integration tests: `ConversionModule` endpoints against real SQLite + Redis (no mocks) — **Vitest + Supertest**
- [ ] E2E: upload a real PDF → conversion → download via API — runs against the community Docker image
- [ ] Frontend: happy-path upload flow, quota wall modal, SSE reconnect — **Playwright**
- [ ] GitHub Actions: add test step after build; fail PR on test failure
- [ ] Coverage gate: 70% on `@mgc/core` and `apps/api` — not `apps/frontend` (Playwright covers it)
- [ ] Load test: 100 concurrent jobs, verify KEDA scaling and no job loss — **k6** against staging
