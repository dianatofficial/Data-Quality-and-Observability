.PHONY: help install test lint format clean up down seed run-dashboard

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies"
	@echo "  test           Run pytest suite with coverage"
	@echo "  lint           Run flake8 and ruff linters"
	@echo "  format         Format code with black and ruff"
	@echo "  seed           Seed database with test data"
	@echo "  run-dashboard  Start Streamlit observability dashboard"
	@echo "  up             Start Docker Compose services (Postgres, Airflow, Dashboard)"
	@echo "  down           Stop Docker Compose services"
	@echo "  clean          Remove temporary and cache files"

install:
	pip install --upgrade pip
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/ config/ scripts/
	flake8 src/ tests/ config/ scripts/

format:
	black src/ tests/ config/ scripts/
	ruff check --fix src/ tests/ config/ scripts/

seed:
	python scripts/seed_data.py

run-dashboard:
	streamlit run streamlit_app.py --server.port=8501

up:
	docker-compose up -d --build

down:
	docker-compose down -v

clean:
	rm -rf .pytest_cache .coverage htmlcov __pycache__ */__pycache__ */*/__pycache__ local_storage/*.db reports/*.html
