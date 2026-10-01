up:
	docker compose up -d

down:
	docker compose down

ai:
	cd ai-engine && uvicorn app.main:app --reload --port 8000

backend:
	cd backend && npm run dev

frontend:
	cd frontend && npm run dev
