.PHONY: up down build seed logs backend frontend

# Start everything with Docker Compose
up:
	docker-compose up --build

# Start in background
up-d:
	docker-compose up --build -d

# Stop everything
down:
	docker-compose down

# Run DB migrations
migrate:
	docker-compose exec backend alembic upgrade head

# Seed the database
seed:
	docker-compose exec backend python -m app.seed

# View logs
logs:
	docker-compose logs -f

backend-logs:
	docker-compose logs -f backend

# Local development (no Docker)
dev-backend:
	cd backend && pip install -r requirements.txt && \
	alembic upgrade head && python -m app.seed && \
	uvicorn app.main:app --reload --port 8001

dev-frontend:
	cd frontend && npm install && npm run dev

# Run both locally (requires two terminals)
dev:
	@echo "Run 'make dev-backend' in one terminal and 'make dev-frontend' in another"
	@echo "Or use 'make up' for Docker Compose"
