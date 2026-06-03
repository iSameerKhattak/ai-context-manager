.PHONY: dev build lint clean test help

help:
	@echo "ContextClaw — Development Commands"
	@echo "─────────────────────────────────"
	@echo "make dev        Start all services (web + api)"
	@echo "make build      Build all packages"
	@echo "make lint       Lint all packages"
	@echo "make typecheck  Run TypeScript type checking"
	@echo "make test       Run all tests"
	@echo "make clean      Clean build artifacts"
	@echo "make format     Format all code"
	@echo "make db/migrate Run database migrations"
	@echo "make dev/web    Start web app only"
	@echo "make dev/api    Start API services only"

dev:
	pnpm dev

build:
	pnpm build

lint:
	pnpm lint

typecheck:
	pnpm typecheck

test:
	pnpm test

clean:
	pnpm clean

format:
	pnpm format

db/migrate:
	cd services/api-gateway && alembic upgrade head

dev/web:
	cd apps/web && pnpm dev

dev/api:
	cd services/api-gateway && uvicorn app.main:app --reload --port 8000
