# DATABASE CONNECTION AUDIT

## 1. UPLOAD FLOW (routes.py)

### Job Creation (POST /jobs)
**Line ~267-297:** Creates job in Redis → persist_to_db IMMEDIATELY
- ❌ UNNECESSARY: Job is still UPLOADING, nothing needs persistence yet
- ✅ SHOULD BE: Only persist when transitioning to QUEUED

### Complete Part (POST /multipart/complete-part)  
**Line ~2158-2240:** Redis-only ✅
- No DB connection during part uploads

### Finalize Upload (POST /multipart/finalize)
**Line ~2354:** persist_to_db when status → QUEUED ✅
- NECESSARY: Job about to enter Celery queue

**Line ~2411:** persist_to_db on ERROR ✅  
- NECESSARY: Terminal state needs persistence

### Abort Upload (POST /multipart/abort)
**Line ~2682:** persist_to_db when status → CANCELLED ✅
- NECESSARY: Terminal state needs persistence

## 2. JOB MANAGEMENT

### Download Result (GET /jobs/:id/download)
**Line ~381-444:** get_db_session + query + commit
- Query to get job
- Update download_attempts counter
- ⚠️ COULD BE REDIS: Counter doesn't need immediate persistence

### Dismiss Job (POST /jobs/:id/dismiss)
**Line ~438-444:** get_db_session + query + commit
- Set dismissed_at timestamp
- ✅ OK: Terminal action, user wants it saved

### Cancel Job (POST /jobs/:id/cancel)
**Line ~917:** persist_to_db ✅
- Terminal state

## 3. SESSION/AUTH (routes.py)

### Migrate Session (POST /migrate-session)
**Line ~1161-1288:** Multiple DB operations
- Query existing sessions
- Update user_id on sessions
- ⚠️ NEEDED: User linking critical data

### Logout (POST /logout)
**Line ~1345-1385:** DB operations
- Delete user sessions
- ✅ NEEDED: Auth cleanup

### Delete Account (DELETE /user/account)
**Line ~1444-1462:** DB operations  
- Delete all user sessions
- ✅ NEEDED: Account deletion

## 4. ADMIN/ANALYTICS

### ✅ REMOVED: Stats (GET /api/user/stats) - Line ~64-138
- **DELETED** - Unused by frontend
- User stats now only in Streamlit dashboard (direct DB access)

### ✅ REMOVED: Delete User (DELETE /admin/delete-user/<alias>) - Line ~1768-1830
- **DELETED** - Unused by dashboard
- Dashboard performs direct SQL DELETE operations
- User account deletion still available via /api/auth/delete-user

## 5. CELERY WORKER (utils/utils.py)

### process_conversion
**Line ~441, 477, 639:** Multiple db.commit()
- Update job status during processing
- ✅ NEEDED: Progress tracking for long-running jobs

## 6. WEBSOCKET (websocket.py)

### _inject_completed_at
**Line ~36:** DB query for COMPLETE jobs
- Backfill missing completed_at
- ✅ OK: Only for terminal state, rare

### handle_connect  
**Line ~160:** db.commit()
- Update session last_active
- ⚠️ COULD BE REDIS: Activity tracking doesn't need immediate persistence

## 7. LOGGING (db_logger.py)

### DatabaseHandler.flush
**Line ~56:** db.commit()
- Batch insert log entries
- ⚠️ OPTIONAL: Logs could go to file/Redis, DB is nice-to-have

---

## SUMMARY: What Actually Needs DB Persistence

### ✅ ESSENTIAL (Keep as-is)
1. **Status transitions to terminal states** (QUEUED, COMPLETE, ERROR, CANCELLED)
2. **Auth operations** (login, logout, account deletion)
3. **Session migration** (user linking)
4. **Job dismissal** (user-initiated terminal action)

### ⚠️ OPTIMIZE (Move to Redis or cache)
1. **Job creation** - Don't persist until QUEUED
2. **Download counter** - Track in Redis, sync periodically
3. **Session activity** - Track in Redis, sync periodically
4. **Logs** - Buffer longer or use file/Redis

### 🔥 HIGH IMPACT FIXES

#### 1. Remove DB Persist on Job Creation (Line ~267-297)
```python
# CURRENT: Persists immediately when status=UPLOADING
# FIX: Only persist when finalize() transitions to QUEUED
```

#### 2. Batch Session Activity Updates (websocket.py:160)
```python
# CURRENT: db.commit() on every WebSocket connect
# FIX: Update last_active in Redis, sync to DB every 5 minutes
```

#### 3. ✅ COMPLETED: Removed Unused Admin Endpoints
```python
# DELETED: /api/user/stats (line 64-138) - unused by frontend
# DELETED: /admin/delete-user/<alias> (line 1768-1830) - dashboard uses direct SQL
# Streamlit dashboard queries DB directly with built-in 5-minute cache
```

---

## CONCISE LIST: Every DB Connection Point

### routes.py
- ✅ **REMOVED** Line 64-138: `/api/user/stats` - Unused, deleted
- Line 267: `get_db_session()` - Job creation (remove persist)
- Line 381: `get_db_session()` - Download job (move counter to Redis)
- Line 438: `get_db_session()` - Dismiss job (keep)
- Line 475: `get_db_session()` - Mark abandoned (keep)
- Line 605: `get_db_session()` - Mark abandoned fallback (keep)
- Line 658: `get_db_session()` - Get presigned URL (keep)
- Line 714: `get_db_session()` - Get presigned URL fallback (keep)
- Line 829: `get_db_session()` - Delete result (keep)
- Line 917: `persist_to_db()` - Cancel job (keep)
- Line 941: `get_db_session()` - Finalize single-part (keep)
- Line 1002: `get_db_session()` - Abort single-part (keep)
- Line 1074: `get_db_session()` - Job creation legacy (keep for now)
- Line 1161: `get_db_session()` - Migrate session (keep)
- Line 1345: `get_db_session()` - Logout (keep)
- Line 1444: `get_db_session()` - Delete account (keep)
- Line 1498: `get_db_session()` - Get job by ID (keep)
- Line 1600: `get_db_session()` - Get job by ID fallback (keep)
- Line 1626: `get_db_session()` - Get logs (keep)
- Line 1655: `get_db_session()` - Admin logs (keep)
- ✅ **REMOVED** Line 1768-1830: `/admin/delete-user/<alias>` - Unused, deleted
- Line 2099: `get_db_session()` - Initiate multipart (keep)
- Line 2354: `persist_to_db()` - Finalize multipart (keep)
- Line 2411: `persist_to_db()` - Finalize error (keep)
- Line 2489: `get_db_session()` - Abort multipart (keep)
- Line 2530: `get_db_session()` - Get parts (keep)
- Line 2682: `persist_to_db()` - Abort cancel (keep)
- Line 2837: `get_db_session()` - Cleanup old jobs (keep)
- Line 2845: `get_db_session()` - Cleanup inner loop (keep)
- Line 2976: `get_db_session()` - User jobs (keep)

### websocket.py
- Line 36: `get_db_session()` - Inject completed_at (keep)
- Line 160: `db.commit()` - Session activity (move to Redis)

### utils/utils.py (Celery worker)
- Line 441: `db.commit()` - Update job status (keep)
- Line 477: `db.commit()` - Update job status (keep)
- Line 639: `db.commit()` - Update job status (keep)

### db_logger.py
- Line 56: `db.commit()` - Flush logs (keep or buffer longer)

### redis_job_store.py
- Line 331: `db.commit()` - persist_to_db implementation (keep)

### auth.py
- Line 105: `db.commit()` - Save user (keep)

### job_status.py
- Line 77: `db.commit()` - Update status (keep)
- Line 141: `db.commit()` - Update status (keep)

### database/utils.py
- Multiple commits for DB schema/migrations (keep)

---

## RECOMMENDED PRIORITY FIXES

### 🔴 CRITICAL (Do first)
1. ✅ **DONE:** Remove DB from `handle_upload_progress` (websocket.py:414)
2. **TODO:** Remove `persist_to_db` from job creation (routes.py:~297)

### 🟡 HIGH IMPACT (Do next)
3. Move session `last_active` to Redis (websocket.py:160)
4. ✅ **DONE:** Remove unused admin endpoints
5. Move `download_attempts` counter to Redis (routes.py:381)

### 🟢 NICE TO HAVE
6. Buffer DB logs longer (db_logger.py:56)
