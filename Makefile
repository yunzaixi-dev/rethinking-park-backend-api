# Makefile for Rethinking Park Backend API

.PHONY: help install install-dev install-prod clean test test-unit test-integration test-e2e lint format type-check security-check pre-commit run dev build docker-build docker-run docs

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install base dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  install-prod     Install production dependencies"
	@echo "  clean            Clean up temporary files and caches"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  lint             Run all linting checks (flake8, pylint)"
	@echo "  lint-flake8      Run flake8 linting only"
	@echo "  lint-pylint      Run pylint linting only"
	@echo "  format           Format code with black and isort"
	@echo "  format-check     Check code formatting without making changes"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security-check   Run security checks with bandit"
	@echo "  quality-check    Run all quality checks (lint, type-check, security)"
	@echo "  pre-commit       Run pre-commit hooks"
	@echo "  run              Run the application in development mode"
	@echo "  dev              Run the application with auto-reload"
	@echo "  build            Build the application"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run Docker container"
	@echo "  docs             Generate documentation"

# Installation targets
install:
	pip install -r requirements/base.txt

install-dev:
	pip install -r requirements/dev.txt
	pre-commit install

install-prod:
	pip install -r requirements/prod.txt

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "bandit-report.json" -delete

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v

test-cov:
	pytest --cov=app --cov=services --cov=models --cov-report=html --cov-report=term

# Code quality
lint: lint-flake8 lint-pylint

lint-flake8:
	flake8 app services models tests

lint-pylint:
	pylint app services models

format:
	black app services models tests
	isort app services models tests

format-check:
	black --check app services models tests
	isort --check-only app services models tests

type-check:
	mypy app services models

security-check:
	bandit -r app services models -f json -o bandit-report.json

quality-check: lint type-check security-check format-check
	@echo "All quality checks completed!"

pre-commit:
	pre-commit run --all-files

# Development
run:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Build
build:
	python -m build

# Docker
docker-build:
	docker build -t rethinking-park-api .

docker-run:
	docker run -p 8000:8000 rethinking-park-api

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

# Documentation
docs:
	mkdocs serve

docs-build:
	mkdocs build

# Database
db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-revision:
	alembic revision --autogenerate -m "$(msg)"

# Deployment
deploy-staging:
	@echo "Deploying to staging..."
	# Add staging deployment commands here

deploy-prod:
	@echo "Deploying to production..."
	# Add production deployment commands here