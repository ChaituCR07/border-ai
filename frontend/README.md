# Tactical Command & Investigation Dashboard (`frontend`)

The **Frontend** is a React + TypeScript application bundled with Vite. It serves as the primary tactical operations interface for security personnel, providing real-time multi-camera monitoring, interactive restricted zone visualization, live alert notifications over WebSockets, and historical incident investigation.

---

## 1. Directory Structure

```text
frontend/
├── src/
│   ├── main.tsx               # React application DOM root & bootstrap
│   ├── App.tsx                # Main console shell & healthcheck monitor
│   ├── App.css                # Primary application styling & layout
│   ├── index.css              # Global design tokens and reset styles
│   ├── components/            # Reusable UI widgets (CameraGrid, AlertCard, ThreatGauge)
│   ├── pages/                 # Full view layouts (LiveCommand, Investigation, CameraConfig)
│   ├── hooks/                 # Custom React hooks (useWebSocket, useCameraFeed)
│   ├── services/              # REST API clients and WebSocket event subscribers
│   ├── store/                 # Client-side state management (active camera, alerts)
│   └── types/                 # TypeScript interfaces for UI models
├── public/                    # Static assets (favicons, SVG icons)
├── package.json               # Node.js dependencies (React, Vite, TypeScript)
├── tsconfig.json              # TypeScript compilation rules
├── vite.config.ts             # Vite bundler configuration & dev server options
└── Dockerfile                 # Multi-stage build producing static Nginx image
```

---

## 2. Core Technologies

- **React 18 / 19**: Component-based UI library.
- **TypeScript**: Static typing for data contracts, WebSocket messages, and state.
- **Vite**: Modern front-end tooling offering sub-second Hot Module Replacement (HMR).
- **WebSockets (`ws`)**: Real-time push connection receiving live alerts from the backend.
- **Modern Responsive CSS**: High-contrast, dark-mode optimized layout for 24/7 security control room environments.

---

## 3. How to Use & Run

### Installation
```bash
cd frontend
npm install
```

### Development Server
Start the local Vite dev server with hot reload on port 5173:
```bash
npm run dev
```
Or from the project root:
```bash
make frontend
```
Navigate to [http://localhost:5173](http://localhost:5173) in your browser.

### Production Build
Type-check and generate production-ready static assets in `dist/`:
```bash
npm run build
```

To preview the production build locally:
```bash
npm run preview
```

---

## 4. Current Features (Day 1 & 2)
- **Live Infrastructure Health Monitor**: Checks connectivity against both AI Engine (`:8000/health`) and Backend (`:4000/health`) directly from the browser to verify CORS and network routing.
- **Telemetry Shell**: Ready to render live video canvas tiles and WebSocket alert feeds (Weeks 2–3).
