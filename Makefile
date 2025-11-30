# OK Computer v3 - Development Makefile

.PHONY: help dev-setup test lint format build deploy clean

help: ## Show this help message
	echo "OK Computer v3 - Mission Control System"
	echo "======================================"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

dev-setup: ## Setup development environment
	@echo "🚀 Setting up OK Computer v3 development environment..."
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install -r requirements-dev.txt
	docker-compose up -d postgres redis-cluster jaeger
	@echo "✅ Development environment ready!"

test: ## Run all tests
	@echo "🧪 Running tests..."
	pytest tests/ -v --cov=services --cov-report=html
	@echo "✅ Tests completed!"

lint: ## Run linting
	@echo "🔍 Running linters..."
	ruff check services/ tests/
	mypy services/
	@echo "✅ Linting completed!"

format: ## Format code
	@echo "🎨 Formatting code..."
	black services/ tests/
	ruff format services/ tests/
	@echo "✅ Code formatted!"

build: ## Build all Docker images
	@echo "🐳 Building Docker images..."
	docker-compose build
	@echo "✅ Images built!"

deploy-local: ## Deploy locally with Docker Compose
	@echo "🚀 Deploying OK Computer v3 locally..."
	docker-compose up -d
	@echo "✅ Local deployment complete!"
	@echo "📊 Grafana: http://localhost:3000 (admin/okcomputer)"
	@echo "🔍 Jaeger: http://localhost:16686"
	@echo "🎯 API: http://localhost:8000"

deploy-k8s: ## Deploy to Kubernetes
	@echo "☸️ Deploying to Kubernetes..."
	kubectl create namespace okc-production || true
	helm install okc-observability ./helm/observability -n okc-production
	helm install okc-cache ./helm/cache -n okc-production
	helm install okc-orchestrator ./helm/orchestrator -n okc-production
	@echo "✅ Kubernetes deployment complete!"

smoke-test: ## Run smoke test
	@echo "🧪 Running smoke test..."
	./scripts/smoke-test.sh
	@echo "✅ Smoke test passed!"

clean: ## Clean up containers and volumes
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete!"

install-tools: ## Install required development tools
	@echo "🔧 Installing development tools..."
	pip install black ruff mypy pytest pytest-cov pytest-asyncio
	@echo "✅ Tools installed!"

logs: ## Show logs from all services
	docker-compose logs -f

status: ## Show status of all services
	docker-compose ps
