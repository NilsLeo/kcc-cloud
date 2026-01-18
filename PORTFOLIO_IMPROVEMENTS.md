# Portfolio Improvements for MangaConverter FOSS

> **Purpose**: This document provides actionable improvements to maximize this project's impact as a pinned GitHub portfolio project for prospective employers.

**Date**: January 16, 2025
**Project**: MangaConverter FOSS - Self-hosted manga/comic converter
**Tech Stack**: Next.js, Flask, Celery, Redis, Docker
**Lines of Code**: ~24,000 (backend) + 108 TypeScript files (frontend)

---

## Executive Summary

### Current Strengths ✅
- **Full-stack architecture**: Modern React/Next.js frontend + Flask backend + distributed task processing
- **Real-time features**: WebSocket implementation with Redis pub/sub
- **Docker orchestration**: Multi-container deployment with proper service separation
- **Clean README**: Well-documented setup, architecture diagrams, configuration
- **CI/CD started**: GitHub Actions for Docker Hub publishing
- **Privacy-conscious**: Removed analytics, stateless design (good for FOSS narrative)

### Critical Gaps 🚨
1. **No testing suite** - Major red flag for employers
2. **Missing LICENSE file** - Legal/professional concern
3. **No screenshots/demo** - Hard to understand what it does
4. **Hardcoded values** - Configuration anti-patterns
5. **No data retention policy** - Files stored indefinitely
6. **No code quality tools** - No linting, formatting, type checking
7. **Incomplete CI/CD** - Only Docker publish, no testing/linting
8. **Poor error handling patterns** - Bare `except Exception:` throughout

---

## 🔴 CRITICAL ISSUES (Must Fix Before Sharing)

### 1. No Testing Suite - DEALBREAKER

**Impact**: "This candidate doesn't know how to test production code"

**Current State**:
- ❌ No `test_*.py` files in backend
- ❌ No `*.test.ts` or `*.spec.ts` files in frontend
- ❌ No `pytest`, `jest`, or `vitest` configuration
- ❌ No test coverage reports

**What Employers Expect**:
- **Minimum**: 30-40% code coverage (shows you understand testing)
- **Good**: 60-70% coverage (shows professional practices)
- **Excellent**: 80%+ with integration tests

**Recommended Fix Priority**:

#### Phase 1: Backend Unit Tests (2-3 hours)
```python
# tests/test_file_validation.py
def test_allowed_file_extensions():
    assert allowed_file('test.cbz') == True
    assert allowed_file('test.exe') == False

# tests/test_conversion_job.py
def test_job_creation():
    job = ConversionJob(id="test", status=JobStatus.QUEUED)
    assert job.status == JobStatus.QUEUED

# tests/test_storage.py
def test_upload_file():
    # Test local storage upload functionality
    pass
```

**Tools to add**:
```bash
# requirements-dev.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-flask==1.3.0
```

**Configuration**:
```ini
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "--cov=app --cov-report=html --cov-report=term"
```

#### Phase 2: Frontend Tests (2-3 hours)
```typescript
// __tests__/components/file-uploader.test.tsx
import { render, screen } from '@testing-library/react'
import { FileUploader } from '@/components/file-uploader'

describe('FileUploader', () => {
  it('renders upload button', () => {
    render(<FileUploader />)
    expect(screen.getByText(/upload/i)).toBeInTheDocument()
  })
})
```

**Tools**:
```json
// package.json
{
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.1.4",
    "vitest": "^1.0.0"
  }
}
```

#### Phase 3: Integration Tests (Optional, 3-4 hours)
```python
# tests/integration/test_conversion_workflow.py
def test_full_conversion_workflow(client):
    # 1. Upload file
    response = client.post('/jobs', data={'file': test_file})
    job_id = response.json['job_id']

    # 2. Check status
    response = client.get(f'/status/{job_id}')
    assert response.json['status'] == 'QUEUED'

    # 3. Wait for completion (with timeout)
    # 4. Download result
```

**Impact on Portfolio**:
- Shows you understand TDD/BDD
- Demonstrates production readiness
- Proves you can work in teams (tests = documentation)
- **Estimated time**: 6-10 hours for 40% coverage

### 4. Hardcoded Configuration Values

**Impact**: "This candidate doesn't understand environment-based configuration"

**Issues Found**:

#### Backend (`app/backend/app/app.py:30`)
```python
# ❌ BAD: Hardcoded wildcard CORS
socketio = SocketIO(
    cors_allowed_origins="*",  # Should be from env var
)
```

**Fix**:
```python
# ✅ GOOD: Environment-based CORS
socketio_cors = os.getenv('SOCKETIO_CORS_ORIGINS', '*')
socketio = SocketIO(
    cors_allowed_origins=socketio_cors,
)
```

#### Frontend (`app/frontend/app/layout.tsx:80`)
```typescript
// ❌ BAD: Hardcoded domain
alternates: {
  canonical: "https://mangaconverter.com",
}
```

**Fix**:
```typescript
// ✅ GOOD: Environment variable
const CANONICAL_URL = process.env.NEXT_PUBLIC_CANONICAL_URL || 'http://localhost:3000'

alternates: {
  canonical: CANONICAL_URL,
}
```

**Add to `.env.example`**:
```bash
# CORS Configuration
SOCKETIO_CORS_ORIGINS=http://localhost:3000,http://localhost
ALLOWED_ORIGINS=http://localhost:3000,http://localhost

# Frontend URLs
NEXT_PUBLIC_CANONICAL_URL=http://localhost:3000
```

**Why it matters**:
- Shows understanding of 12-factor app methodology
- Demonstrates deployment flexibility (dev/staging/prod)
- Critical for cloud-native applications

---

## 🟡 HIGH PRIORITY IMPROVEMENTS

### 5. Code Quality Tools Missing

**Impact**: "Does this candidate write maintainable code?"

**Current State**:
- ❌ No Python linting (Black, Flake8, mypy)
- ❌ No TypeScript linting configured
- ❌ No pre-commit hooks
- ❌ No code formatting enforcement

**Recommended Setup** (1-2 hours):

#### Backend Python
```bash
# requirements-dev.txt
black==23.12.1
flake8==7.0.0
mypy==1.8.0
isort==5.13.2
```

**Configuration**:
```ini
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Start lenient
```

**Add to `.flake8`**:
```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,node_modules
```

#### Frontend TypeScript
```json
// package.json
{
  "scripts": {
    "lint": "next lint",
    "format": "prettier --write .",
    "type-check": "tsc --noEmit"
  },
  "devDependencies": {
    "prettier": "^3.1.0",
    "eslint-config-prettier": "^9.1.0"
  }
}
```

**Add `.prettierrc`**:
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

#### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

**Why it matters**:
- Shows you care about code quality
- Proves you can work in team environments
- Demonstrates knowledge of modern tooling

---

### 6. Expand CI/CD Pipeline

**Impact**: "Does this candidate know DevOps practices?"

**Current State**:
- ✅ Has Docker Hub publish workflow
- ❌ No automated testing in CI
- ❌ No linting checks
- ❌ No type checking
- ❌ No build verification

**Recommended Fix**:

Create `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd app/backend
          pip install -r requirements.txt -r requirements-dev.txt

      - name: Run Black
        run: cd app/backend && black --check .

      - name: Run Flake8
        run: cd app/backend && flake8 .

      - name: Run tests
        run: cd app/backend && pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./app/backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Install dependencies
        run: cd app/frontend && pnpm install

      - name: Run linter
        run: cd app/frontend && pnpm lint

      - name: Type check
        run: cd app/frontend && pnpm type-check

      - name: Run tests
        run: cd app/frontend && pnpm test

      - name: Build
        run: cd app/frontend && pnpm build

  docker-build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Test Docker Compose
        run: docker compose -f docker-compose.yml config
```

**Add badges to README**:
```markdown
[![CI](https://github.com/yourusername/mgc-foss/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/mgc-foss/actions/workflows/ci.yml)
[![Code Coverage](https://codecov.io/gh/yourusername/mgc-foss/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/mgc-foss)
```

**Why it matters**:
- Shows modern DevOps knowledge
- Demonstrates automated quality gates
- Proves you understand CI/CD pipelines
- Green badges look professional on GitHub

---

### 7. Improve Error Handling

**Impact**: "Will this candidate write fragile production code?"

**Issues Found**:

#### Bare Exception Catching
```python
# app/backend/app/utils/redis_job_store.py (multiple locations)
except Exception:  # ❌ Too broad, masks bugs
    pass
```

**Better Pattern**:
```python
except (RedisError, ConnectionError) as e:  # ✅ Specific exceptions
    logger.error(f"Redis connection failed: {e}")
    # Fallback to database
```

#### Missing Error Responses
```python
# app/backend/app/utils/routes.py:145
except Exception as e:
    return jsonify({"error": str(e)}), 500  # ❌ Leaks implementation details
```

**Better Pattern**:
```python
except FileNotFoundError:
    return jsonify({"error": "File not found"}), 404
except ValueError as e:
    logger.error(f"Validation error: {e}")
    return jsonify({"error": "Invalid input"}), 400
except Exception as e:
    logger.exception(f"Unexpected error: {e}")  # Log full traceback
    return jsonify({"error": "Internal server error"}), 500
```

**Recommended Improvements**:
1. Create custom exception classes
2. Use specific exception types
3. Add structured logging
4. Implement error monitoring (optional: Sentry)

**Why it matters**:
- Shows defensive programming skills
- Demonstrates debugging experience
- Critical for production systems

---

## 🟢 NICE-TO-HAVE IMPROVEMENTS

### 8. Add Contributing Guidelines

**Create `CONTRIBUTING.md`**:
```markdown
# Contributing to MangaConverter FOSS

## Development Setup

1. Clone the repository
2. Install dependencies
3. Run tests

## Code Style

- Python: Black + Flake8
- TypeScript: Prettier + ESLint
- Run `pre-commit install` before committing

## Testing

All PRs must include tests and maintain >70% coverage.

## Commit Messages

Follow conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
```


