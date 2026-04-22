# Makefile — Developer shortcuts

.PHONY: dev worker beat test lint format migrate seed

## Run FastAPI dev server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Run Celery worker
worker:
	celery -A app.workers.celery_app worker --loglevel=info

## Run Celery beat scheduler
beat:
	celery -A app.workers.celery_app beat --loglevel=info

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

## Start all services with docker-compose
up:
	docker-compose up -d

## Stop all services
down:
	docker-compose down

## View logs
logs:
	docker-compose logs -f api
