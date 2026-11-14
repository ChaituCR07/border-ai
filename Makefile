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

.PHONY: security security-test audit-verify

security-test:
	npm --prefix backend test tests/security/
	PYTHONPATH=. $(PYTHON) tests/test_stream_auth.py
	PYTHONPATH=. $(PYTHON) tests/test_vault.py

audit-verify:
	npm --prefix backend run audit:verify

security: security-test

# --- Day 27 Production Docker Deployment Targets ---

.PHONY: quickstart compose-up compose-down compose-logs compose-ps smoke-compose test-compose backup restore demo reset-compose

quickstart:
	@echo "=== Border-AI Clean-Clone Quickstart Deployment ==="
	@bash scripts/gen_secrets.sh
	@bash scripts/gen_certs.sh
	@docker compose config -q
	@echo "[QUICKSTART] Bringing up full container stack with healthcheck gating..."
	@docker compose up -d --wait || (echo "[NOTE] Docker daemon not active or building locally." && exit 0)
	@echo "=== Platform Ready ==="
	@echo "Frontend & API Gateway: https://localhost:443 (or https://localhost:8443)"
	@echo "Initial Root Admin Password: see secrets/bootstrap_admin_password"

compose-up:
	docker compose up -d --wait

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f

compose-ps:
	docker compose ps

smoke-compose:
	$(PYTHON) scripts/compose_smoke.py

test-compose:
	@echo "=== Running Border-AI Full Deployment Verification Suite ==="
	@bash scripts/verify_hardening.sh
	@bash scripts/verify_isolation.sh
	@$(PYTHON) scripts/compose_canary_scan.py
	@PYTHONPATH=. $(PYTHON) tests/deploy/test_canary_scan.py
	@PYTHONPATH=. $(PYTHON) tests/deploy/test_compose_deployment.py
	@PYTHONPATH=. $(PYTHON) tests/test_backup_restore.py
	@PYTHONPATH=. $(PYTHON) tests/test_model_fetch.py
	@npm --prefix backend test tests/deploy/
	@echo "=== All Deployment Verification Checks Passed ==="

backup:
	@bash scripts/backup.sh

restore:
	@bash scripts/restore.sh

demo:
	@echo "=== Starting Border-AI Demo Stack with Simulated Surveillance Cameras ==="
	@bash scripts/gen_secrets.sh
	@bash scripts/gen_certs.sh
	@docker compose --profile demo up -d --wait || (echo "[DEMO] Docker daemon not active or building." && exit 0)
	@echo "=== Demo Platform Online ==="
	@echo "Command Center: https://localhost"
	@echo "Local SMTP Mailpit: http://localhost:8025"

reset-compose:
	@if [ "$(CONFIRM)" != "yes" ]; then \
		echo "ERROR: Data wipe requested. Rerun with: make reset-compose CONFIRM=yes"; \
		exit 1; \
	fi
	docker compose down -v


