COMPOSE = docker compose -f docker/docker-compose.yml
RUN     = uv run --env-file .env

.PHONY: test up down logs ps db-init psql bucket upload enqueue backfill tokenize dashboard dashboard-dev list cat download

test:
	uv run pytest

db-init:
	$(COMPOSE) run --rm celery python -c "from paperlm.db import init_db; init_db(); print('Initialized database schema.')"

psql:
	$(COMPOSE) exec postgres psql -U paperlm

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f celery

bucket:
	$(RUN) python scripts/create_bucket.py

upload:
	$(RUN) python scripts/upload_papers.py $(PAPERS)

enqueue:
	$(COMPOSE) run --rm celery python -m paperlm.enqueue

backfill:
	$(COMPOSE) run --rm celery python -m paperlm.backfill

tokenize:
	$(COMPOSE) run --rm celery python -m paperlm.tokenize_enqueue $(SELECTION)

dashboard:
	$(COMPOSE) up --build -d dashboard

dashboard-dev:
	uv run --group dashboard --env-file .env gunicorn -b 0.0.0.0:8050 paperlm.dashboard.app:server

list:
	$(RUN) python scripts/list_bucket.py $(FOLDER)

cat:
	$(RUN) python scripts/cat_object.py $(KEY)

download:
	$(RUN) python scripts/download_extracted.py $(OUT)