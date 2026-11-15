# Border-AI Release Asset Inventory (v1.0.0)

This inventory catalogs all required release assets for the Border-AI Video Intelligence Platform v1.0.0 milestone.

---

## 1. Asset Manifest & Verification Status

| Asset Identifier | File Path | Media Type / Format | Source of Truth | Generation Method | Status |
|---|---|---|---|---|---|
| **System Architecture Diagram** | `docs/diagrams/out/architecture.svg` / `.png` | SVG / PNG (1920×1080) | `docs/diagrams/src/architecture.mmd` | `make diagrams` (Mermaid) | Verified |
| **System Flow Diagram** | `docs/diagrams/out/system-flow.svg` / `.png` | SVG / PNG | `docs/diagrams/src/system-flow.mmd` | `make diagrams` (Mermaid) | Verified |
| **Database Schema ERD** | `docs/diagrams/out/database-schema.svg` / `.png` | SVG / PNG | PostgreSQL Migrations `001–008` | `make db-docs` (Prisma/tbls) | Verified |
| **Container Topology Diagram** | `docs/diagrams/out/deployment.svg` / `.png` | SVG / PNG | `docker-compose.yml` (ADR 0050) | `make diagrams` (Mermaid) | Verified |
| **Static API Reference** | `docs/api/index.html` | HTML5 / Redoc | `backend/src/routes/*.ts` | `npm --prefix backend run openapi:generate` | Verified |
| **WebSocket Protocol Spec** | `docs/api/websocket.md` | Markdown + JSON schema | `backend/src/websocket/*.ts` | Hand-crafted protocol spec | Verified |
| **API Example Collection** | `docs/api/examples/` | HTTP / Curl scripts | Fastify Route Controllers | `make api-examples` | Verified |
| **Interface Screenshots** | `docs/media/screenshots/*.png` | PNG (1920×1080) | Live Composed Stack (`make demo`) | `make screenshots` (Playwright) | Verified |
| **Hero Demonstration GIF** | `docs/media/hero.gif` | Animated GIF (15 FPS, <8MB) | Scenario 2 live alert workflow | `ffmpeg` palettegen/paletteuse | Verified |
| **Demonstration Video** | External CDN / YouTube link | MP4 (1080p60, H.264/AAC) | Scripted Walkthrough Scenarios 1–3 | Manual recording + OBS Studio | Ready |
| **Model Performance Table** | `docs/model_eval/` | Markdown table | `evaluation/runs/`, `docs/perf/` | `scripts/docs/render_readme_numbers.py` | Verified |
| **Capability Matrix** | `docs/capabilities.md` | Markdown | Plan specifications & test suites | Single source of truth | Verified |
| **Technical Limitations** | `docs/LIMITATIONS.md` | Markdown | Benchmarks & edge cases | Audited boundary guide | Verified |
| **Responsible Use Policy** | `docs/RESPONSIBLE_USE.md` | Markdown | Legal & ethics review (ADR 0054) | Single source of truth | Verified |
| **ADR Decision Index** | `docs/decisions/README.md` | Markdown index | ADRs `0001` through `0055` | `scripts/docs/gen_adr_index.py` | Verified |
| **Final Project Report** | `docs/reports/final_report.md` | Markdown report | Git history, test suites, LOC stats | `scripts/report/week_stats.sh` | Verified |

---

## 2. Media Privacy & Compliance Sign-Off

All imagery and videos cataloged in this inventory comply with the following constraints:
- **Zero Real Identifiable Faces:** All human subjects originate from licensed synthetic fixtures or consent-cleared test sets.
- **Zero Real License Plates:** All vehicle plates are strictly synthetic look-alikes (`KA01AB1234`, `DL08CD5678`).
- **Zero Hardcoded Secrets:** OCR screening verifies no private keys, passwords, or hostnames appear in visible viewports or address bars.
- **Metadata Cleared:** All EXIF/GPS tags have been stripped via image sanitization tooling.
