.PHONY: up down logs rebuild-backend rebuild-frontend dev

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

rebuild-backend:
	docker compose build backend && docker compose up -d backend

rebuild-frontend:
	docker compose build frontend && docker compose up -d frontend

dev:
	docker compose up -d redis
	@echo Redis 已启动。本地开发请分别运行 backend / frontend（见 README）。
