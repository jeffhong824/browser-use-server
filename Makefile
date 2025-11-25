.PHONY: help docker-build docker-run docker-run-bg docker-stop docker-logs docker-shell test lint clean install

# Default target
help:
	@echo "Browser Use SaaS - Makefile Commands"
	@echo ""
	@echo "  make install          - Install Python dependencies"
	@echo "  make docker-build     - Build Docker image"
	@echo "  make docker-run       - Run container in foreground"
	@echo "  make docker-run-bg    - Run container in background"
	@echo "  make docker-stop      - Stop and remove containers"
	@echo "  make docker-logs      - Show container logs"
	@echo "  make docker-shell     - Open shell in container"
	@echo "  make test             - Run tests"
	@echo "  make lint             - Run linters"
	@echo "  make clean            - Clean temporary files"
	@echo ""

# Install dependencies
install:
	pip install -r requirements.txt

# Docker commands
docker-build:
	docker compose build

docker-run:
	docker compose up

docker-run-bg:
	docker compose up -d
	@echo "✅ Service started in background"
	@echo "📡 API available at http://localhost:$${API_PORT:-8000}"
	@echo "🌐 Web interface: http://localhost:$${API_PORT:-8000}/"
	@echo ""
	@echo "Check logs with: make docker-logs"

docker-stop:
	docker compose down
	@echo "🛑 Service stopped"

docker-logs:
	docker compose logs --tail=100 -f

docker-shell:
	docker compose exec browser-use-api /bin/bash

# Testing
test:
	pytest tests/ -v

# Linting
lint:
	@echo "Running linters..."
	@if command -v black > /dev/null; then black --check src/; fi
	@if command -v ruff > /dev/null; then ruff check src/; fi
	@if command -v mypy > /dev/null; then mypy src/; fi

# Clean temporary files
clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	@echo "🧹 Cleaned temporary files"

