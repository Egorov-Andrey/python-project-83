PORT ?= 8000

install:
	uv sync

dev:
    uv run flask --debug --app page_analyzer:app run

start: 
	uv run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

build:
	./build.sh

migrate:
	@if [ -n "$$DATABASE_URL" ]; then \
		psql -a -d "$$DATABASE_URL" -f database.sql; \
	else \
		echo "DATABASE_URL not set"; \
		exit 1; \
	fi

render-start:
	@echo "Running migrations..."
	psql -a -d "$$DATABASE_URL" -f database.sql || true
	gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

