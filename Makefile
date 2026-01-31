# SpotDL Makefile
# Provides convenient commands for development and deployment

.PHONY: help install dev test lint format build docker-dev docker-prod clean

# Default target
help:
	@echo "SpotDL Development Commands"
	@echo ""
	@echo "Setup & Install:"
	@echo "  make install      - Install all dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development servers"
	@echo "  make dev-backend  - Start backend only"
	@echo "  make dev-frontend - Start frontend only"
	@echo "  make dev-cli      - Start CLI in dev mode"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests"
	@echo "  make test-frontend- Run frontend tests"
	@echo "  make test-cli     - Run CLI tests"
	@echo "  make coverage     - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make typecheck    - Run type checking"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-dev   - Start development containers"
	@echo "  make docker-prod  - Start production containers"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-push  - Push Docker images"
	@echo "  make docker-stop  - Stop all containers"
	@echo ""
	@echo "Misc:"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make migrate      - Run database migrations"

# =============================================================================
# Setup & Install
# =============================================================================

install:
	cd backend && uv sync
	cd cli && uv sync
	cd core && uv sync
	cd frontend && pnpm install

install-dev:
	cd backend && uv sync --dev
	cd cli && uv sync --dev
	cd core && uv sync --dev
	cd frontend && pnpm install

# =============================================================================
# Development
# =============================================================================

dev:
	docker compose up

dev-backend:
	cd backend && uv run uvicorn spotdl.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && pnpm dev

dev-cli:
	cd cli && uv run python -m spotdl_cli

# =============================================================================
# Testing
# =============================================================================

test: test-backend test-frontend test-cli

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && pnpm test

test-cli:
	cd cli && uv run pytest

test-core:
	cd core && uv run pytest

coverage:
	cd backend && uv run pytest --cov=spotdl --cov-report=html --cov-report=term-missing --cov-fail-under=80
	cd frontend && pnpm test --coverage
	cd cli && uv run pytest --cov=spotdl_cli --cov-report=html --cov-report=term-missing

# =============================================================================
# Code Quality
# =============================================================================

lint:
	cd backend && uv run ruff check src tests
	cd cli && uv run ruff check src tests
	cd frontend && pnpm lint

format:
	cd backend && uv run ruff format src tests
	cd cli && uv run ruff format src tests
	cd frontend && pnpm format

typecheck:
	cd backend && uv run mypy src
	cd cli && uv run mypy src
	cd frontend && pnpm type-check

# =============================================================================
# Docker
# =============================================================================

docker-dev:
	docker compose up -d

docker-prod:
	docker compose -f docker-compose.prod.yml up -d

docker-build:
	docker compose build
	docker compose -f docker-compose.prod.yml build

docker-push:
	docker compose -f docker-compose.prod.yml push

docker-stop:
	docker compose down
	docker compose -f docker-compose.prod.yml down

docker-logs:
	docker compose logs -f

# =============================================================================
# Database
# =============================================================================

migrate:
	cd backend && uv run alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; \
	cd backend && uv run alembic revision --autogenerate -m "$$name"

migrate-rollback:
	cd backend && uv run alembic downgrade -1

# =============================================================================
# Cleanup
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
