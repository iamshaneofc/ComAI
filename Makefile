# Makefile — Developer shortcuts
#
# Full stack: Postgres + Redis + API + Celery worker.
# - Docker: make up  (see docker-compose.yml)
# - Manual (if Docker is unavailable): start Postgres & Redis locally, set .env,
#     then in two terminals:  make dev    and   make worker

.PHONY: dev worker beat test lint format migrate seed up down logs check-local run-local

## Verify Postgres + Redis TCP ports (no Docker)
check-local:
	python scripts/check_local_services.py

## Migrate then start API + Celery as PowerShell background jobs (Windows; needs Postgres + Redis)
run-local:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local.ps1

## Run FastAPI dev server (same as: uvicorn app.main:app --reload)
dev:
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Run Celery worker (broker/backend from .env — default redis://localhost:6379/...)
worker:
	python -m celery -A app.core.celery_app worker --loglevel=info

## Run Celery beat scheduler
beat:
	python -m celery -A app.core.celery_app beat --loglevel=info

## Run all tests with coverage
test:
	pytest tests/ --cov=app --cov-report=term-missing -v

## Lint with ruff + type check with mypy
lint:
	ruff check app/ tests/
	mypy app/

## Format code with black + ruff fix
format:
	black app/ tests/
	ruff check --fix app/ tests/

## Run Alembic migrations
migrate:
	alembic upgrade head

## Create new migration (usage: make migration msg="add_products_table")
migration:
	alembic revision --autogenerate -m "$(msg)"

## Seed database with test data
seed:
	python scripts/seed_database.py

## Start Postgres, Redis, API, Celery worker (Docker Compose v2)
up:
	docker compose up -d --build

## Stop all services
down:
	docker compose down

## View API container logs (service name: backend)
logs:
	docker compose logs -f backend
