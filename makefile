COMPOSE = docker compose -f docker/docker-compose.yml
RUN     = uv run --env-file .env

.PHONY: test up down logs ps bucket upload enqueue list cat download

test:
	uv run pytest

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

list:
	$(RUN) python scripts/list_bucket.py $(FOLDER)

cat:
	$(RUN) python scripts/cat_object.py $(KEY)

download:
	$(RUN) python scripts/download_extracted.py $(OUT)