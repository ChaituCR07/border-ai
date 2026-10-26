# ADR 0017 — Frontend Stack and Data Layer Architecture

## Status
Accepted

## Context
The Border AI Video Intelligence Platform requires an operational real-time command dashboard ("Command Center") capable of running continuously in border control rooms. The frontend needs to interface with the Node/Fastify REST API (`:4000`), the multi-camera MJPEG streaming service (`:8001`), and must be engineered to smoothly transition from polling to WebSocket live alerts (Day 17) without refactoring UI components.

## Decision
1. **Core Framework & Build Tooling:**
   - **Vite + React + TypeScript (Strict Mode):** Fast HMR, minimal build overhead, and rigorous type safety (`strict: true`, `noUncheckedIndexedAccess: true`).
   - **Tailwind CSS + CSS Design Tokens:** Styling governed by centralized tokens (`tokens.css`) defining severity hues, dark control-room palettes, borders, and reduced-motion constraints.

2. **Server State & Data Fetching:**
   - **TanStack Query (React Query v5):** Used exclusively for server state. Manages polling, request deduplication, cache invalidation, stale states (`keepPreviousData`), and optimistic updates with automatic rollback.
   - UI components never invoke `fetch` directly; all queries and mutations reside in feature-scoped custom hooks (`useCameras`, `useThreatSummary`, `useOpenAlerts`, `useAcknowledge`, `useRecentEvents`).

3. **API Contract Enforcement:**
   - Generated TypeScript contracts via `openapi-typescript` derived directly from `docs/api/openapi.json`.
   - `openapi-fetch` provides compile-time route and parameter checking against backend endpoints. CI enforces `git diff --exit-code src/api/schema.d.ts` to block undocumented API drift.

4. **UI State Management:**
   - **Zustand (Micro-Store):** Encapsulates ephemeral UI state: `selectedCameraId`, `videoLayout` (`1x1` | `2x2`), `tzMode` (`UTC` | `LOCAL`), `severityFilter`, and `cameraSearchQuery`.
   - Select properties (`videoLayout`, `tzMode`, `selectedCameraOnly`) are persisted in `localStorage` via Zustand middleware.

5. **Day 17 Real-Time Seam (`useOpenAlerts`):**
   - Live alerts are accessed exclusively through a unified contract:
     ```ts
     export interface LiveAlerts {
       alerts: AlertResource[];
       counts: Record<Severity, number>;
       transport: 'polling' | 'websocket';
       isStale: boolean;
       lastUpdated: number | null;
     }
     ```
   - On Day 17, the internal implementation will switch to WebSocket push plus REST catch-up without changing a single line of component code.

## Consequences
- Single source of truth across backend contracts and frontend consumers.
- No direct coupling between visual UI widgets and network transports.
- Complete offline/test development capability enabled by MSW fixtures.
