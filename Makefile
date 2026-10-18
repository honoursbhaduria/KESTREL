.PHONY: up down migrate test lint format help

help:
	@echo "Available commands:"
	@echo "  make up       - Start all Docker Compose infrastructure (postgres, redis, minio)"
	@echo "  make down     - Stop all Docker Compose services"
	@echo "  make migrate  - Run database migrations with Alembic"
	@echo "  make test     - Run pytest test suite across backend"
	@echo "  make lint     - Run ruff linter and typecheck"
	@echo "  make format   - Run ruff code formatter"

up:
	docker compose up -d postgres redis minio

down:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

test:
	cd backend && uv run pytest -v

lint:
	cd backend && uv run ruff check . && uv run mypy app
	cd frontend && npm run typecheck

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .
