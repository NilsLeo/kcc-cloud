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

3. **Install frontend dependencies**
   ```bash
   cd app/frontend && pnpm install && cd ../..
   ```
   This is required because the dev setup mounts your local code into the container.

4. **Start the development environment**
   ```bash
   docker compose up
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8060

All development is done inside Docker containers with hot-reload enabled. Code changes are automatically detected and the services will restart as needed.

4. **Add KindleGen**: Download the Linux version from [archive.org/details/kindlegen](https://archive.org/details/kindlegen), extract it, and place in `./volumes/kindlegen/`:
   ```bash
   mkdir -p ./volumes/kindlegen
   # Copy kindlegen binary here
   chmod +x ./volumes/kindlegen/kindlegen
   ```
   The docker-compose.yml automatically mounts this directory.

### Accessing Container Shells

For interactive development or debugging, you can access a shell inside any container:

```bash
# Backend shell
docker exec -it kcc-cloud-backend sh

# Frontend shell
docker exec -it kcc-cloud-frontend-dev sh
```

## Code Style & Tests

Ensure all CI checks pass before submitting a pull request. This includes code formatting, linting, type checking, and tests for both backend and frontend.

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
   - Add tests for your changes

3. **Ensure all CI checks pass**
   - All code formatting, linting, type checking, and tests must pass
   - Push to your fork and open a pull request
   - The CI pipeline will validate your changes

4. **Commit using Conventional Commits**
   ```bash
   git commit -m "feat: your feature description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feat/your-feature-name
   ```

Thank you for contributing to KCC Cloud!
