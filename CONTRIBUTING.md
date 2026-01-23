# Contributing to KCC Cloud

Thank you for your interest in contributing to KCC Cloud! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Docker and Docker Compose

### Local Development

1. **Clone the repository**
   ```bash
   git clone git@github.com:NilsLeo/kcc-cloud.git
   cd kcc-cloud
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

3. **Start the development environment**
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8060

All development is done inside Docker containers with hot-reload enabled. Code changes are automatically detected and the services will restart as needed.

### Container Names

The development containers use the following names:
- **Backend**: `kcc-cloud-backend`
- **Frontend**: `kcc-cloud-frontend-dev`
- **Redis**: `kcc-cloud-redis`

### Accessing Container Shells

For interactive development or debugging, you can access a shell inside any container:

```bash
# Backend shell
docker exec -it kcc-cloud-backend sh

# Frontend shell
docker exec -it kcc-cloud-frontend-dev sh
```

### Running Tests

All tests are run inside the Docker containers using `docker exec`.

**Backend**:
```bash
docker exec kcc-cloud-backend pytest --cov=app --cov-report=html
```

**Frontend**:
```bash
docker exec kcc-cloud-frontend-dev pnpm test
```

## Code Style

We enforce consistent code style across the project using automated tools.

### Python (Backend)

- **Formatter**: Black (line length: 100)
- **Linter**: Flake8
- **Import sorting**: isort
- **Type checking**: mypy (lenient mode)

Run all checks inside the backend container:
```bash
docker exec kcc-cloud-backend black .
docker exec kcc-cloud-backend isort .
docker exec kcc-cloud-backend flake8 .
docker exec kcc-cloud-backend mypy .
```

### TypeScript/JavaScript (Frontend)

- **Formatter**: Prettier
- **Linter**: ESLint (Next.js config)
- **Type checking**: TypeScript

Run all checks inside the frontend container:
```bash
docker exec kcc-cloud-frontend-dev pnpm format
docker exec kcc-cloud-frontend-dev pnpm lint
docker exec kcc-cloud-frontend-dev pnpm type-check
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality before commits. Run pre-commit inside the backend container:

```bash
# Install hooks (one-time setup)
docker exec kcc-cloud-backend pre-commit install

# Run manually to check all files
docker exec kcc-cloud-backend pre-commit run --all-files
```

Once installed, pre-commit will automatically run on git commits. If you prefer to run checks manually before committing, use the command above.

## Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>: <description>

[optional body]

[optional footer]
```

### Types

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks
- `perf:` Performance improvements

### Examples

```
feat: add support for WebP image format

fix: resolve race condition in job cancellation

docs: update README with deployment instructions

test: add unit tests for file validation
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Follow the code style guidelines
   - Add tests for your changes

3. **Run all checks inside Docker containers**
   ```bash
   # Backend checks
   docker exec kcc-cloud-backend black --check .
   docker exec kcc-cloud-backend flake8 .
   docker exec kcc-cloud-backend pytest

   # Frontend checks
   docker exec kcc-cloud-frontend-dev pnpm lint
   docker exec kcc-cloud-frontend-dev pnpm type-check
   docker exec kcc-cloud-frontend-dev pnpm test
   docker exec kcc-cloud-frontend-dev pnpm build
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feat/your-feature-name
   ```

6. **Open a Pull Request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure CI checks pass

## Branching & Release Workflow

We use a simple three-branch workflow:

```
feature/* → develop → main (auto-release)
```

### Branch Strategy

- **`feature/*`** - New features and bug fixes
- **`develop`** - Integration and testing branch
- **`main`** - Production releases with automatic versioning

### Release Process

1. **Development** happens on `feature/*` branches → merge to `develop`
   - CI builds Docker image: `nilsleo/kcc-cloud:feature-name`

2. **Integration testing** on `develop` branch
   - Every push builds: `nilsleo/kcc-cloud:develop`

3. **Production release** - merge `develop` → `main`
   - **Automatically**:
     - Increments patch version (e.g., `v1.2.3` → `v1.2.4`)
     - Builds and pushes Docker images:
       - `nilsleo/kcc-cloud:v1.2.4`
       - `nilsleo/kcc-cloud:latest`
       - `nilsleo/kcc-cloud:stable`
     - Creates Git tag `v1.2.4`
     - Creates GitHub Release with auto-generated changelog

### Docker Image Tags

| Branch | Tags | Usage |
|--------|------|-------|
| `feature/*` | `feature-name`, `feature-name-abc1234` | Feature testing |
| `develop` | `develop`, `develop-abc1234` | Integration testing |
| `main` | `v1.2.3`, `latest`, `stable` | Production |

### Versioning

- **Automatic**: Every merge to `main` auto-increments the patch version
- **Format**: Semantic Versioning `vMAJOR.MINOR.PATCH`
- **Sync**: Docker tags and GitHub releases are always in sync (created atomically)

### Creating a Release

```bash
# When ready for production release:
git checkout develop
git pull origin develop

# Create PR: develop → main
# After merge, CI automatically:
# - Runs all tests
# - Increments version
# - Builds and tags Docker images
# - Creates GitHub release
```

## Code Review

All contributions go through code review:

- Reviewers will check code quality, tests, and documentation
- Address feedback promptly and professionally
- Be open to suggestions and improvements

## Questions?

If you have questions or need help:

- Open an issue for discussion
- Check existing documentation
- Reach out to maintainers

Thank you for contributing to KCC Cloud!
