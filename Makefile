# HabitatCanvas Development Makefile

.PHONY: help setup up down logs test clean

help: ## Show this help message
	@echo "HabitatCanvas Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Set up the development environment
	@echo "🚀 Setting up HabitatCanvas development environment..."
	docker-compose up --build -d
	@echo "✅ Development environment is ready!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-backend: ## View backend logs
	docker-compose logs -f backend

test-frontend: ## Run frontend tests
	docker-compose exec frontend npm test

test-backend: ## Run backend tests
	docker-compose exec backend pytest

test: test-frontend test-backend ## Run all tests

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

restart: ## Restart all services
	docker-compose restart

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec db psql -U habitatcanvas -d habitatcanvas