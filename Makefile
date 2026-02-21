.PHONY: install test lint run clean

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run ruff check .
	poetry run mypy .

run:
	poetry run python run_pipeline.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +