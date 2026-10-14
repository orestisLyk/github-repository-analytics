.PHONY: help build up down restart logs ps health test migrate downgrade stamp

help:
	@echo "Available targets:"
	@echo "  build    Build app image"
	@echo "  up       Start stack in detached mode"
	@echo "  down     Stop stack"
	@echo "  restart  Restart stack"
	@echo "  logs     Tail app and db logs"
	@echo "  ps       Show service status"
	@echo "  health   Check API health endpoint"
	@echo "  test     Run pytest locally"
	@echo "  migrate  Apply database migrations to head"
	@echo "  stamp    Mark current schema as migrated to head"
	@echo "  downgrade  Roll back one migration"

build:
	docker compose build

up:
	docker compose up --build -d

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f app postgres

ps:
	docker compose ps

health:
	powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing http://localhost:8000/health | Select-Object -ExpandProperty Content"

test:
	pytest -q

migrate:
	alembic upgrade head

stamp:
	alembic stamp head

downgrade:
	alembic downgrade -1