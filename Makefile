PYTHON ?= /Library/Frameworks/Python.framework/Versions/3.13/bin/python3

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

.PHONY: test-fp-logic test-fp-system fp-guard fp-exposure test-fp

test-fp-logic:
	PYTHONPATH=. $(PYTHON) tests/test_fp_stats.py
	PYTHONPATH=. $(PYTHON) tests/test_oracle.py
	PYTHONPATH=. $(PYTHON) tests/fp/logic/test_zone_properties.py
	PYTHONPATH=. $(PYTHON) tests/fp/logic/test_line_properties.py
	PYTHONPATH=. $(PYTHON) tests/fp/logic/test_fps_invariance.py
	PYTHONPATH=. $(PYTHON) tests/fp/logic/test_alert_scoring.py
	PYTHONPATH=. $(PYTHON) tests/fp/logic/test_mutations.py

test-fp-system:
	PYTHONPATH=. $(PYTHON) tests/fp/system/test_system_fp.py

fp-guard:
	PYTHONPATH=. $(PYTHON) tests/fp/fp_guard.py

fp-exposure:
	PYTHONPATH=. $(PYTHON) tests/test_exposure_ledger.py
	PYTHONPATH=. $(PYTHON) tests/test_exposure_and_clustering.py

test-fp: test-fp-logic test-fp-system fp-guard fp-exposure
	PYTHONPATH=. $(PYTHON) tests/fp/test_watchlist_fp.py
	PYTHONPATH=. $(PYTHON) tests/test_oracle_vs_system.py
	PYTHONPATH=. $(PYTHON) tests/test_stress_augmentation.py
	$(PYTHON) scripts/report/check_claims.py
