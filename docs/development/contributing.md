# Contributing Guide

Thank you for your interest in contributing to SpotDL! This guide covers how to set up your development environment, code style requirements, testing, and the pull request process.

## Development Setup

### Prerequisites

- Python 3.13+
- Node.js 22+
- pnpm (for frontend)
- uv (for Python projects)
- Docker (optional, for integration testing)
- Git

### Clone the Repository

```bash
git clone https://github.com/spotDL/spotify-downloader.git
cd spotify-downloader
```

### Install Dependencies

Using the Makefile:

```bash
make install-dev
```

Or manually:

```bash
# Backend
cd backend && uv sync --dev

# Core library
cd ../core && uv sync --dev

# CLI
cd ../cli && uv sync --dev

# Frontend
cd ../frontend && pnpm install
```

### Start Development Servers

```bash
# All services with Docker
make dev

# Backend only
make dev-backend

# Frontend only
make dev-frontend

# CLI development mode
make dev-cli
```

## Project Structure

```
spotify-downloader/
+-- backend/           # FastAPI backend
|   +-- src/spotdl/   # Backend source
|   +-- tests/        # Backend tests
|   +-- pyproject.toml
|
+-- cli/              # Textual CLI
|   +-- src/spotdl_cli/
|   +-- tests/
|   +-- pyproject.toml
|
+-- core/             # Shared library
|   +-- src/spotdl_core/
|   +-- tests/
|   +-- pyproject.toml
|
+-- frontend/         # React frontend
|   +-- src/
|   +-- __tests__/
|   +-- package.json
|
+-- nginx/            # Nginx configuration
+-- docs/             # Documentation
+-- docker-compose.yml
+-- Makefile
```

## Code Style

### Python

We use Ruff for linting and formatting:

```bash
# Check formatting
cd backend && uv run ruff format --check src tests

# Format code
cd backend && uv run ruff format src tests

# Lint
cd backend && uv run ruff check src tests

# Type checking
cd backend && uv run mypy src
```

#### Python Style Guidelines

- Line length: 100 characters
- Use type hints for all function signatures
- Use docstrings for public functions and classes
- Follow PEP 8 naming conventions
- Use `from __future__ import annotations` for modern typing

Example:

```python
"""Module docstring explaining purpose."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

def calculate_score(
    name: str,
    artists: Sequence[str],
    duration: int,
) -> float:
    """
    Calculate match score for a song.

    Args:
        name: Song title.
        artists: List of artist names.
        duration: Duration in seconds.

    Returns:
        Match score between 0 and 100.
    """
    # Implementation
    return 0.0
```

### TypeScript/JavaScript

We use ESLint and Prettier:

```bash
cd frontend

# Lint
pnpm lint

# Type check
pnpm type-check
```

#### TypeScript Style Guidelines

- Use TypeScript strict mode
- Prefer functional components with hooks
- Use explicit return types for functions
- Use `interface` for object shapes
- Use `type` for unions and complex types

Example:

```typescript
interface Song {
  id: string;
  title: string;
  artists: string[];
  duration: number;
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}
```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=spotdl --cov-report=html

# Run specific test file
uv run pytest tests/test_matching.py

# Run specific test
uv run pytest tests/test_matching.py::test_score_calculation

# Run with verbose output
uv run pytest -v

# Run excluding slow tests
uv run pytest -m "not slow"
```

#### Writing Backend Tests

```python
# tests/test_example.py
import pytest
from spotdl.core.matching import calculate_score

class TestCalculateScore:
    """Tests for calculate_score function."""

    def test_exact_match(self) -> None:
        """Exact matches should score 100."""
        score = calculate_score(
            source_name="Test Song",
            target_name="Test Song",
            source_artists=["Artist"],
            target_artists=["Artist"],
            source_duration=180,
            target_duration=180,
        )
        assert score == 100.0

    def test_no_match(self) -> None:
        """Completely different songs should score low."""
        score = calculate_score(
            source_name="Song A",
            target_name="Song B",
            source_artists=["Artist X"],
            target_artists=["Artist Y"],
            source_duration=180,
            target_duration=300,
        )
        assert score < 50.0

    @pytest.mark.slow
    def test_with_api_call(self) -> None:
        """Tests that make real API calls."""
        # This test is marked slow
        pass
```

#### Using VCR for API Tests

Record and replay HTTP interactions:

```python
import pytest

@pytest.mark.vcr
def test_spotify_fetch(spotify_provider) -> None:
    """Test fetching from Spotify API."""
    song = spotify_provider.get_song("spotify:track:4u7EnebtmKWzUH433cf5Qv")
    assert song.name == "Bohemian Rhapsody"
```

### CLI Tests

```bash
cd cli

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=spotdl_cli
```

### Frontend Tests

```bash
cd frontend

# Run tests
pnpm test

# Run with coverage
pnpm test:coverage

# Run in watch mode
pnpm test --watch
```

#### Writing Frontend Tests

```typescript
// __tests__/SongCard.test.tsx
import { render, screen } from '@testing-library/react';
import { SongCard } from '../src/components/SongCard';

describe('SongCard', () => {
  it('displays song title', () => {
    render(<SongCard title="Test Song" artist="Test Artist" />);
    expect(screen.getByText('Test Song')).toBeInTheDocument();
  });
});
```

### End-to-End Tests

```bash
cd frontend
pnpm e2e
```

### Integration Tests

Run the full stack with Docker:

```bash
docker compose up -d
# Run integration tests against the stack
```

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/fixes

### 2. Make Your Changes

- Write code following the style guidelines
- Add tests for new functionality
- Update documentation if needed
- Keep commits focused and atomic

### 3. Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Examples:

```
feat(matching): add ISRC-based matching algorithm

Implements ISRC comparison for improved match accuracy.
ISRC matches are weighted higher than name-based matches.

Closes #123
```

```
fix(cli): handle network timeout gracefully

Previously, network timeouts caused the CLI to crash.
Now displays a user-friendly error message.
```

### 4. Run Pre-Commit Checks

```bash
# Format and lint
make format
make lint

# Type check
make typecheck

# Run tests
make test
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

### PR Requirements

- [ ] All tests pass
- [ ] Code is formatted and linted
- [ ] Type checking passes
- [ ] Documentation updated (if applicable)
- [ ] Changelog entry added (for user-facing changes)
- [ ] PR description explains the changes

### Code Review

- Address reviewer feedback
- Keep discussions focused and professional
- Request re-review after making changes

## Development Tips

### Debugging Backend

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message: %s", variable)
```

### Debugging CLI

```bash
# Run with Textual debug console
cd cli && uv run textual run --dev src/spotdl_cli/app.py
```

### Debugging Frontend

Use React DevTools and browser developer tools.

```typescript
// Console debugging
console.log('State:', state);

// React Query DevTools
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
```

### Database Migrations

```bash
cd backend

# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1
```

### Adding a New Provider

1. Create provider class in `core/src/spotdl_core/providers/`
2. Implement required interface (SourceProvider, TargetProvider, or MetadataProvider)
3. Add tests with VCR cassettes
4. Export in `__init__.py`
5. Document supported features

### Common Tasks

```bash
# Clean build artifacts
make clean

# Rebuild everything
make clean && make install-dev

# Update dependencies
cd backend && uv lock --upgrade
cd frontend && pnpm update
```

## Getting Help

- Check existing issues and discussions
- Ask in the Discord community
- Open an issue for bugs or feature requests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## See Also

- [Architecture Overview](./architecture.md)
- [Configuration Reference](../getting-started/configuration.md)
- [Self-Hosting Guide](../guides/self-hosting.md)
