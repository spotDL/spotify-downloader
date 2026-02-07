# SpotDL Development Makefile
# Common commands for development and deployment

.PHONY: help dev dev-cli cli console up down logs build migrate migrate-create test lint clean

# Default target
help:
	@echo "SpotDL Development Commands"
	@echo ""
	@echo "Docker Services:"
	@echo "  make dev              - Start development environment (docker compose up)"
	@echo "  make up               - Start services in background"
	@echo "  make down             - Stop all services"
	@echo "  make logs             - Show logs from all services"
	@echo "  make build            - Rebuild Docker images"
	@echo ""
	@echo "CLI Development:"
	@echo "  make dev-cli          - Run CLI in dev mode with Textual devtools"
	@echo "  make cli              - Run CLI normally"
	@echo "  make console          - Start Textual console (run in separate terminal)"
	@echo ""
	@echo "Database:"
	@echo "  make migrate          - Apply all pending migrations"
	@echo "  make migrate-create   - Create a new migration (autogenerate)"
	@echo "                          Usage: make migrate-create MSG='add user roles'"
	@echo "  make migrate-history  - Show migration history"
	@echo "  make migrate-downgrade - Downgrade one migration"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-backend     - Run backend tests"
	@echo "  make test-frontend    - Run frontend tests"
	@echo "  make lint             - Run linters"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove build artifacts"
	@echo "  make clean-db         - Remove database (WARNING: destructive)"

# Docker Development
dev:
	docker compose up

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# CLI Development
dev-cli:
	cd cli && uv run --with textual-dev textual run --dev src/spotdl_cli/__main__.py

cli:
	cd cli && uv run spotdl

console:
	@echo "Starting Textual console..."
	@echo "Make sure to run 'make dev-cli' in another terminal first!"
	cd cli && uv run --with textual-dev textual console

# Database migrations
# Migrations are auto-applied on startup, but these commands allow manual control

migrate:
	docker compose exec api alembic upgrade head

migrate-create:
ifndef MSG
	$(error MSG is required. Usage: make migrate-create MSG='description of changes')
endif
	docker compose exec api alembic revision --autogenerate -m "$(MSG)"
	@echo ""
	@echo "Migration created. Please review the generated file in backend/alembic/versions/"
	@echo "Run 'make migrate' to apply it."

migrate-history:
	docker compose exec api alembic history

migrate-downgrade:
	docker compose exec api alembic downgrade -1

migrate-current:
	docker compose exec api alembic current

# Testing
test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test

lint:
	cd backend && uv run ruff check src
	cd frontend && npm run lint

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true

clean-db:
	@echo "WARNING: This will delete the database!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose down -v
	@echo "Database volume removed."
