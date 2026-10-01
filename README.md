# Border AI: AI Video Intelligence Platform

AI-powered video analytics that turns existing CCTV/IP-camera infrastructure into
a real-time surveillance analytics system: detection, tracking, ANPR, behaviour
rules, threat scoring, alerts, and an investigation dashboard.

## Status
Week 1 in progress: computer vision foundation.

## Quick start
1. `cp .env.example .env`
2. `docker compose up -d`
3. `python3 -m venv .venv && source .venv/bin/activate`
4. `pip install -r ai-engine/requirements.txt -r video-ingestion/requirements.txt`
5. `cd ai-engine && uvicorn app.main:app --reload --port 8000`
6. `cd backend && npm install && npm run dev`
7. `cd frontend && npm install && npm run dev`

## Docs
See `docs/architecture.md`

## Performance
To be filled with measured results (see `docs/benchmarks.md`).
