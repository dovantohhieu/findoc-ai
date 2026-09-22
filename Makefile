.PHONY: db-up db-down migrate reindex reindex-full eval

db-up:
	docker compose up -d db

db-down:
	docker compose down

migrate:
	docker compose exec -T db psql -U findoc -d findoc < sql/001_schema.sql

reindex:
	python -m findoc.reindex --source data/processed/docs.jsonl

reindex-full:
	python -m findoc.reindex --source data/processed/docs.jsonl --full

eval:
	python -m findoc.eval.run --queries eval/queries.yaml --k 5 --out reports/week5_eval.md

test:
	pytest -m "not eval" -q

test-eval:
	pytest -m eval -q
