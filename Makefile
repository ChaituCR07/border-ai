.PHONY: up down reset check smoke scenarios chaos reconcile conformance soak report

up:
	bash scripts/stack_up.sh

down:
	docker compose -f docker-compose.infra.yml down
	bash scripts/kill_stragglers.sh

reset:
	bash scripts/reset_state.sh

check:
	bash scripts/check_all.sh

smoke:
	python3 scripts/smoke_e2e.py

scenarios:
	python3 tests/integration/harness/run_scenarios.py

chaos:
	python3 scripts/chaos/inject_fault.py

reconcile:
	python3 scripts/reconcile.py --strict

conformance:
	python3 scripts/conformance/scan.py

soak:
	python3 scripts/soak.py --minutes 20

report:
	bash scripts/report/week_stats.sh

ai:
	cd ai-engine && uvicorn app.main:app --reload --port 8000

backend:
	cd backend && npm run dev

frontend:
	cd frontend && npm run dev
