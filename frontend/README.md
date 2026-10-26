# Border-AI Command Center Dashboard (Frontend)

The **Border-AI Command Center** is a real-time, dark-theme operational web application designed for border security command centers and control rooms. Built with React 19, TypeScript, Vite, TanStack Query, and Tailwind CSS.

---

## 1. Quick Start

### Prerequisites
- Node.js >= 20.x
- npm >= 10.x

### Install Dependencies
```bash
cd frontend
npm install
```

### Run with Live Backend & Streams
Ensure the Day 15 REST API (`localhost:4000`) and the Day 7 FrameHub MJPEG server (`localhost:8001`) are running:
```bash
npm run dev
```
Navigate to `http://localhost:5173`.

### Run in Standalone Mock Mode (MSW)
To develop or preview the dashboard without running PostgreSQL, Redis, or the AI pipeline:
```bash
VITE_MOCK_API=true npm run dev
```
The dashboard will load using MSW mock handlers and realistic test fixtures.

---

## 2. Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Launch Vite development server with proxy to API backend |
| `npm run build` | Compile TypeScript and bundle production assets with Vite |
| `npm run preview` | Preview production build locally |
| `npm run test` | Run Vitest unit, component, and hook test suites |
| `npm run typecheck` | Strict TypeScript verification (`tsc -b --noEmit`) |
| `npm run gen:api` | Regenerate TypeScript API types from `../docs/api/openapi.json` |

---

## 3. Architecture & Data Flow

- **Server State & Polling:** Managed by TanStack Query with exponential backoff and `keepPreviousData` to eliminate visual flicker.
- **Connection Safety:** Enforces ADR 0018 with a hard ceiling of at most 4 simultaneous MJPEG video streams (1x1 or 2x2 grid) to protect browser HTTP/1.1 connection pools.
- **Tab Inactivity Detection:** MJPEG streams and polling automatically suspend when the tab is hidden or minimized via `useDocumentVisible`.
- **API Drift Detection:** Generated types in `src/api/schema.d.ts` are verified in CI against `docs/api/openapi.json`.
- **Day 17 Real-Time Seam:** `useOpenAlerts` exposes a unified `LiveAlerts` interface, enabling a drop-in transition from HTTP polling to WebSocket live events on Day 17.

---

## 4. Keyboard Shortcuts

| Key | Action |
|---|---|
| `1` – `9` | Select active camera stream |
| `G` / `g` | Toggle video layout between 1×1 single stream and 2×2 grid |
| `U` / `u` | Toggle global timestamp display between UTC and Local time |
| `Esc` | Close evidence snapshot drawer |

---

## 5. Architecture Decision Records (ADRs)

- [ADR 0017 — Frontend Stack and Data Layer](../docs/decisions/0017-frontend-stack-and-data-layer.md)
- [ADR 0018 — Live Video Delivery Constraints](../docs/decisions/0018-live-video-delivery-constraints.md)
- [ADR 0019 — Operational UI Principles](../docs/decisions/0019-operational-ui-principles.md)
