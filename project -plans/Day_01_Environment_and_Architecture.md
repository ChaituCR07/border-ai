# Day 1: Environment and Architecture

**Project:** AI-Based Intelligent Video Analytics Platform for Border Surveillance (`border-ai`)
**Week 1 goal:** Video → Detection → Tracking → Zone/Line Analysis → Annotated Video
**Day 1 goal:** Every service starts, every dependency is reachable, the folder structure is final, and the repo is under version control, so from Day 2 onward you only write features.

> Timebox: one day. Do not build features today. No ingestion, no YOLO, no auth, no database schema beyond connectivity. If something is not on this list, it is not a Day 1 task.

---

## 1. Suggested Time Plan

| Block | Task | Est. time |
|---|---|---|
| 1 | Prerequisites check, GitHub repo, clone | 30 min |
| 2 | Folder structure, `.gitignore`, branches | 45 min |
| 3 | Docker: PostgreSQL + Redis | 45 min |
| 4 | Python environment + FastAPI skeleton | 90 min |
| 5 | Node.js + TypeScript backend skeleton | 60 min |
| 6 | React frontend skeleton | 45 min |
| 7 | Configs, `.env`, Dockerfiles | 45 min |
| 8 | Architecture docs + README | 45 min |
| 9 | Full verification + first commits | 30 min |

---

## 2. Prerequisites Checklist

Install and verify each item before starting.

| Tool | Version | Verify with |
|---|---|---|
| Git | any recent | `git --version` |
| Python | 3.10 or 3.11 (3.11 recommended) | `python --version` |
| Node.js | 20 LTS or newer | `node --version` |
| npm | comes with Node | `npm --version` |
| Docker Desktop / Docker Engine | recent | `docker --version` and `docker compose version` |
| NVIDIA driver (if you have a GPU) | recent | `nvidia-smi` |
| VS Code (or your IDE) | any | n/a |
| GitHub account + SSH key or PAT | n/a | `ssh -T git@github.com` |

**GPU note:** you only need the NVIDIA driver on the host today. CUDA-enabled PyTorch is installed in the Python environment (Section 7). Do not try to get GPU access inside Docker today (see Challenges).

**Windows users:** use WSL2 (Ubuntu) for the repo and Python work if possible. Keep the repo inside the WSL filesystem (`~/border-ai`), not under `/mnt/c/...`, for much better file performance.

---

## 3. Task 1: Create the GitHub Repository

1. Create a new **private** repository named `border-ai` on GitHub (you can make it public when the portfolio is ready).
2. Initialize with a README, a Python-style `.gitignore` will be replaced later by our own, and choose a license (MIT is fine for a portfolio).
3. Clone locally:

```bash
git clone git@github.com:<your-username>/border-ai.git
cd border-ai
```

4. Set your identity if not already set:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
```

**Deliverable:** empty repo cloned locally.

---

## 4. Task 2: Create the Project Structure

### 4.1 Final folder structure

```text
border-ai/
│
├── ai-engine/                     # Python: detection, tracking, analytics
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI entry point
│   │   ├── config.py              # loads .env + configs/
│   │   ├── api/                   # FastAPI routes (health, detect, stream)
│   │   ├── detection/             # detector.py, classes.py
│   │   ├── tracking/              # tracker.py, track_store.py
│   │   ├── analytics/             # zones.py, lines.py, loitering.py, events.py
│   │   ├── pipeline/              # pipeline.py, visualizer.py
│   │   ├── schemas/               # Pydantic models: Detection, Track, Event
│   │   ├── utils/                 # geometry, timing, logging
│   │   ├── anpr/                  # (Week 2, empty for now)
│   │   ├── identity/              # (Week 2: face / Re-ID)
│   │   └── rules/                 # (Week 2: rule engine + threat scoring)
│   ├── models/                    # YOLO weights (gitignored)
│   ├── scripts/                   # benchmark.py, draw_zones.py, run_pipeline.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── video-ingestion/               # Python: camera and stream handling
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── sources/               # base.py, file_source.py, rtsp_source.py
│   │   ├── camera_manager.py
│   │   ├── frame.py               # Frame dataclass (camera_id, frame_id, ts)
│   │   └── onvif/                 # (stub, stretch goal)
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── backend/                       # Node.js + TypeScript
│   ├── src/
│   │   ├── index.ts
│   │   ├── config/
│   │   ├── routes/
│   │   ├── controllers/
│   │   ├── services/
│   │   ├── db/                    # connection, queries
│   │   ├── streams/               # Redis Streams consumers (Week 2-3)
│   │   ├── websocket/
│   │   ├── middleware/            # auth, error handling (Week 3)
│   │   └── types/
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
│
├── frontend/                      # React + TypeScript (Vite)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/              # API + WebSocket clients
│   │   ├── store/
│   │   └── types/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── database/
│   ├── migrations/
│   ├── seeds/                     # sample watchlist, cameras
│   └── schema.sql
│
├── configs/
│   ├── cameras.json               # camera id, name, source, target FPS
│   ├── zones/
│   │   └── CAM_001.json           # polygons + lines per camera
│   ├── rules.json                 # (Week 2) scoring weights + thresholds
│   └── app.yaml                   # model, confidence, tracker settings
│
├── datasets/                      # gitignored except README
│   ├── videos/                    # test CCTV clips
│   ├── plates/                    # (Week 2)
│   └── faces/                     # (Week 2)
│
├── outputs/                       # gitignored
│   ├── annotated/                 # annotated MP4s
│   ├── events/                    # JSON-lines event logs
│   └── snapshots/                 # (Week 2)
│
├── docker/
│   ├── nginx/                     # (Week 3-4)
│   └── postgres/
│       └── init.sql
│
├── tests/                         # cross-service integration tests
├── docs/
│   ├── architecture.md
│   ├── decisions/                 # short notes on why you chose X
│   ├── benchmarks.md              # record FPS / ms numbers here
│   └── images/
│
├── scripts/                       # setup.sh, run_local.sh
├── docker-compose.yml
├── .env.example
├── .env                           # gitignored
├── .gitignore
├── .gitattributes
├── Makefile                       # optional shortcuts
└── README.md
```

### 4.2 Create it with one script (Linux / macOS / WSL / Git Bash)

Save as `scripts/setup.sh` (or run directly from the repo root):

```bash
#!/usr/bin/env bash
set -e

# --- ai-engine ---
mkdir -p ai-engine/app/{api,detection,tracking,analytics,pipeline,schemas,utils,anpr,identity,rules}
mkdir -p ai-engine/{models,scripts,tests}
touch ai-engine/app/__init__.py
for d in api detection tracking analytics pipeline schemas utils anpr identity rules; do
  touch ai-engine/app/$d/__init__.py
done
touch ai-engine/app/main.py ai-engine/app/config.py
touch ai-engine/requirements.txt ai-engine/Dockerfile
touch ai-engine/models/.gitkeep ai-engine/scripts/.gitkeep ai-engine/tests/.gitkeep

# --- video-ingestion ---
mkdir -p video-ingestion/ingestion/{sources,onvif} video-ingestion/tests
touch video-ingestion/ingestion/__init__.py
touch video-ingestion/ingestion/sources/__init__.py
touch video-ingestion/ingestion/{camera_manager.py,frame.py}
touch video-ingestion/ingestion/onvif/.gitkeep video-ingestion/tests/.gitkeep
touch video-ingestion/requirements.txt video-ingestion/Dockerfile

# --- backend (package.json/tsconfig created in Task 6) ---
mkdir -p backend/src/{config,routes,controllers,services,db,streams,websocket,middleware,types}
for d in config routes controllers services db streams websocket middleware types; do
  touch backend/src/$d/.gitkeep
done

# --- frontend (created by Vite in Task 7, so only make the parent) ---
mkdir -p frontend

# --- database ---
mkdir -p database/{migrations,seeds}
touch database/schema.sql database/migrations/.gitkeep database/seeds/.gitkeep

# --- configs ---
mkdir -p configs/zones
touch configs/zones/.gitkeep

# --- datasets / outputs ---
mkdir -p datasets/{videos,plates,faces}
touch datasets/videos/.gitkeep datasets/plates/.gitkeep datasets/faces/.gitkeep
mkdir -p outputs/{annotated,events,snapshots}
touch outputs/annotated/.gitkeep outputs/events/.gitkeep outputs/snapshots/.gitkeep

# --- docker / tests / docs / scripts ---
mkdir -p docker/{nginx,postgres} tests docs/{decisions,images} scripts
touch docker/nginx/.gitkeep docker/postgres/init.sql tests/.gitkeep
touch docs/architecture.md docs/benchmarks.md docs/decisions/.gitkeep docs/images/.gitkeep

echo "Structure created."
```

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**PowerShell alternative (no WSL):** create the same folders with `New-Item -ItemType Directory -Force -Path <path>` for each directory, and `New-Item -ItemType File -Force -Path <path>` for each `.gitkeep` / placeholder file. The bash version above is the reference.

### 4.3 Rules for the structure

- Empty folders do not exist in Git, so every folder you want kept has a `.gitkeep`.
- Do not fill Week 2 folders (`anpr/`, `identity/`, `rules/`) with code today.
- Use `pathlib` and a `BASE_DIR` from config everywhere. No hardcoded absolute paths.

**Deliverable:** full tree exists locally.

---

## 5. Task 3: Git Branches

```text
main                 # stable, tagged milestones only
develop              # integration branch (daily work merges here)
feature/detection
feature/anpr
feature/dashboard
feature/rules
```

Commands:

```bash
git checkout -b develop
git push -u origin develop

git checkout -b feature/detection develop
git push -u origin feature/detection
git checkout develop

git checkout -b feature/anpr develop
git push -u origin feature/anpr
git checkout develop

git checkout -b feature/dashboard develop
git push -u origin feature/dashboard
git checkout develop

git checkout -b feature/rules develop
git push -u origin feature/rules
git checkout develop
```

**Workflow to follow all four weeks**

1. Do the day's work on the relevant `feature/*` branch.
2. Merge into `develop` at the end of each day (or milestone).
3. Merge `develop` into `main` only at weekly milestones and tag them (`v0.1-week1`, `v0.2-week2`, and so on).
4. Optional: in GitHub settings, protect `main` (require PRs) even as a solo developer. It keeps the portfolio history clean.

**Commit message convention (suggested):** `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`. For example, `chore: add docker-compose with postgres and redis`.

**Note:** Day 1 work itself (structure, configs, skeletons) is committed directly to `develop`.

---

## 6. Task 4: Repo Hygiene Files

### 6.1 `.gitignore`

```text
# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
dist/
build/
*.log

# Environment
.env
.env.local

# Models and data (never commit these)
ai-engine/models/*
!ai-engine/models/.gitkeep
datasets/*
!datasets/README.md
!datasets/*/.gitkeep
outputs/*
!outputs/.gitkeep
!outputs/*/.gitkeep
*.mp4
*.avi
*.mkv
*.pt
*.onnx
*.engine
*.pth

# Docker volumes / local data
pgdata/
redisdata/

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

### 6.2 `.gitattributes`

```text
* text=auto
*.sh text eol=lf
*.py text eol=lf
*.ts text eol=lf
*.md text eol=lf
```

This prevents Windows/Linux line-ending problems, especially for shell scripts run inside Docker.

### 6.3 `datasets/README.md`

Create a short file explaining that datasets and videos are not committed. List where each test clip came from and its license or permission status. This supports the privacy note in your plan (use only authorized or permitted footage).

### 6.4 `.env.example` (commit this)  and `.env` (do not commit)

```env
# --- General ---
APP_ENV=development
LOG_LEVEL=INFO

# --- PostgreSQL ---
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=borderai
POSTGRES_USER=borderai
POSTGRES_PASSWORD=change_me

# --- Redis ---
REDIS_HOST=localhost
REDIS_PORT=6379

# --- Services ---
AI_ENGINE_PORT=8000
BACKEND_PORT=4000
FRONTEND_PORT=5173

# --- AI ---
YOLO_MODEL=yolov8n.pt
DETECTION_CONFIDENCE=0.4
DEVICE=auto
```

Then create your local copy and change the password:

```bash
cp .env.example .env
```

**Deliverable:** repo hygiene files in place; no secrets committed.

---

## 7. Task 5: Python Environment and FastAPI (AI Engine)

### 7.1 Virtual environment

One virtual environment at the repo root, shared by `ai-engine` and `video-ingestion` during development. Each service keeps its own `requirements.txt` so Docker builds stay independent later.

```bash
cd border-ai
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 7.2 Install PyTorch first (GPU or CPU)

Get the exact command from https://pytorch.org for your OS and CUDA version. Example for CUDA 12.1:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

CPU-only machines: install the default CPU build instead.

Verify:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

### 7.3 `ai-engine/requirements.txt`

```text
ultralytics
opencv-python
numpy
fastapi
uvicorn[standard]
pydantic
python-dotenv
pyyaml
shapely
pytest
```

### 7.4 `video-ingestion/requirements.txt`

```text
opencv-python
numpy
python-dotenv
pyyaml
```

Install both:

```bash
pip install -r ai-engine/requirements.txt -r video-ingestion/requirements.txt
```

After everything works, pin exact versions:

```bash
pip freeze > requirements.lock.txt
```

### 7.5 `ai-engine/app/config.py`

```python
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]      # border-ai/
load_dotenv(BASE_DIR / ".env")

CONFIG_DIR = BASE_DIR / "configs"
OUTPUT_DIR = BASE_DIR / "outputs"
DATASET_DIR = BASE_DIR / "datasets"
MODEL_DIR = BASE_DIR / "ai-engine" / "models"


def load_app_config() -> dict:
    with open(CONFIG_DIR / "app.yaml", "r") as f:
        return yaml.safe_load(f)


AI_ENGINE_PORT = int(os.getenv("AI_ENGINE_PORT", 8000))
APP_ENV = os.getenv("APP_ENV", "development")
```

### 7.6 `ai-engine/app/main.py`

```python
from fastapi import FastAPI
from app import config

app = FastAPI(title="Border AI - AI Engine", version="0.1.0")


@app.get("/health")
def health():
    try:
        import torch
        cuda = torch.cuda.is_available()
        device = torch.cuda.get_device_name(0) if cuda else "cpu"
    except Exception:
        cuda, device = False, "unavailable"

    return {
        "service": "ai-engine",
        "status": "ok",
        "env": config.APP_ENV,
        "cuda": cuda,
        "device": device,
    }
```

### 7.7 Run and test

```bash
cd ai-engine
uvicorn app.main:app --reload --port 8000
```

```bash
curl http://localhost:8000/health
```

Open http://localhost:8000/docs to see the auto-generated Swagger UI.

### 7.8 Confirm YOLO can load (do not build the detector today)

```bash
python -c "from ultralytics import YOLO; m = YOLO('yolov8n.pt'); print('YOLO OK')"
```

This downloads the small pretrained weights and proves the install works. Move the downloaded `yolov8n.pt` into `ai-engine/models/` (it is gitignored).

**Features delivered:** FastAPI running with a health endpoint that reports GPU status.

---

## 8. Task 6: Node.js + TypeScript Backend

```bash
cd backend
npm init -y
npm install express cors dotenv pg ioredis
npm install -D typescript ts-node-dev @types/node @types/express @types/cors @types/pg
npx tsc --init
```

### 8.1 `backend/tsconfig.json` (key settings)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "rootDir": "./src",
    "outDir": "./dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"]
}
```

### 8.2 `backend/package.json` scripts

```json
"scripts": {
  "dev": "ts-node-dev --respawn --transpile-only src/index.ts",
  "build": "tsc",
  "start": "node dist/index.js"
}
```

### 8.3 `backend/src/index.ts`

```ts
import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import path from "path";
import { Pool } from "pg";
import Redis from "ioredis";

dotenv.config({ path: path.resolve(__dirname, "../../.env") });

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({
  host: process.env.POSTGRES_HOST,
  port: Number(process.env.POSTGRES_PORT),
  database: process.env.POSTGRES_DB,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
});

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: Number(process.env.REDIS_PORT),
  lazyConnect: true,
  maxRetriesPerRequest: 1,
});

app.get("/health", async (_req, res) => {
  const status = { service: "backend", postgres: "down", redis: "down" };

  try {
    await pool.query("SELECT 1");
    status.postgres = "up";
  } catch {}

  try {
    if (redis.status === "wait") await redis.connect();
    await redis.ping();
    status.redis = "up";
  } catch {}

  const ok = status.postgres === "up" && status.redis === "up";
  res.status(ok ? 200 : 503).json(status);
});

const port = Number(process.env.BACKEND_PORT) || 4000;
app.listen(port, () => console.log(`Backend listening on ${port}`));
```

### 8.4 Run and test

```bash
npm run dev
curl http://localhost:4000/health
```

Expected once Docker (Task 8) is running:

```json
{"service":"backend","postgres":"up","redis":"up"}
```

**Features delivered:** TypeScript backend with a health endpoint that verifies PostgreSQL and Redis connectivity.

---

## 9. Task 7: React + TypeScript Frontend

```bash
cd border-ai
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

If Vite complains that `frontend/` is not empty, delete the placeholder files inside it first (or run the scaffold in a temp folder and move the contents in).

Open http://localhost:5173 and confirm the default page loads.

### Small connectivity check (optional, 10 minutes)

Replace the body of `src/App.tsx` with a component that calls `http://localhost:4000/health` and `http://localhost:8000/health` and shows the status of each service. This proves CORS and ports are correct before Week 3. Keep it plain; do not style it.

**Features delivered:** React + TypeScript app running on port 5173.

---

## 10. Task 8: Docker (PostgreSQL + Redis)

### 10.1 `docker-compose.yml` (repo root)

```yaml
services:
  postgres:
    image: postgres:16
    container_name: borderai-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7
    container_name: borderai-redis
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redisdata:/data
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
  redisdata:
```

### 10.2 `docker/postgres/init.sql`

```sql
-- Day 1: connectivity only.
-- The real schema (cameras, events, watchlist, snapshots) is designed in Week 2.
SELECT 1;
```

### 10.3 Start and verify

```bash
docker compose up -d
docker compose ps
```

Both containers should show `healthy`.

```bash
docker exec -it borderai-postgres psql -U borderai -d borderai -c "SELECT 1;"
docker exec -it borderai-redis redis-cli ping
```

Expected: a result row of `1`, and `PONG`.

### 10.4 Stopping and resetting

```bash
docker compose down          # stop, keep data
docker compose down -v       # stop AND delete data volumes (full reset)
```

### 10.5 Dockerfile skeletons (create now, refine in Week 3-4)

These are placeholders so the structure is complete. You will not run them today.

`ai-engine/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`backend/Dockerfile`

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

`frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

**Local development decision:** run PostgreSQL and Redis in Docker, and run the Python, Node, and React services directly on the host this week. This avoids GPU-in-Docker problems while you iterate. Full containerization of all services happens in Week 3-4. Record this in `docs/decisions/`.

**Features delivered:** PostgreSQL and Redis running with persistent volumes and healthchecks.

---

## 11. Task 9: Config Files

### 11.1 `configs/app.yaml`

```yaml
model:
  name: yolov8n.pt
  device: auto            # auto | cpu | cuda:0
  confidence: 0.4
  iou: 0.5
  image_size: 640
  classes: [person, bicycle, car, motorcycle, bus, truck]

tracker:
  type: bytetrack
  track_thresh: 0.5
  match_thresh: 0.8
  track_buffer: 30

video:
  target_fps: 15
  resize_width: 1280
```

### 11.2 `configs/cameras.json`

```json
{
  "cameras": [
    {
      "camera_id": "CAM_001",
      "name": "North Gate",
      "source_type": "file",
      "source": "datasets/videos/sample_01.mp4",
      "target_fps": 15,
      "enabled": true
    }
  ]
}
```

Later entries will use `"source_type": "rtsp"` and an `rtsp://...` URL. Do not commit real camera credentials; keep them in `.env`.

### 11.3 `configs/zones/CAM_001.json` (sample, coordinates normalized 0-1)

```json
{
  "camera_id": "CAM_001",
  "zones": [
    {
      "name": "Restricted Zone",
      "type": "restricted",
      "polygon": [[0.1, 0.2], [0.6, 0.2], [0.6, 0.8], [0.1, 0.8]]
    }
  ],
  "lines": [
    {
      "name": "Entry Line",
      "p1": [0.0, 0.5],
      "p2": [1.0, 0.5],
      "positive_direction": "IN"
    }
  ]
}
```

Normalized coordinates survive resolution changes between cameras and videos.

**Features delivered:** camera, model, and zone config schemas agreed before any code depends on them.

---

## 12. Task 10: Initial Architecture Documentation

### 12.1 `docs/architecture.md` should contain

1. **Overview:** one paragraph on what the platform does.
2. **Pipeline diagram** (copy from your plan):

```text
CCTV / RTSP / ONVIF
        ↓
Video Ingestion
        ↓
Object Detection (YOLO)
        ↓
Multi-Object Tracking (ByteTrack)
        ↓
ANPR / Identity Intelligence
        ↓
Watchlist Verification
        ↓
Zone & Behaviour Analysis
        ↓
Threat Scoring
        ↓
Cross-Camera Correlation
        ↓
Prioritized Alert
        ↓
Command Dashboard → Investigation Dashboard
```

3. **Component table:**

| Component | Tech | Port | Responsibility |
|---|---|---|---|
| ai-engine | Python, FastAPI, YOLO, ByteTrack | 8000 | Detection, tracking, analytics, events |
| video-ingestion | Python, OpenCV, FFmpeg | n/a (library in Week 1) | Camera/file/RTSP frame input |
| backend | Node.js, TypeScript, Express | 4000 | API, persistence, WebSockets |
| frontend | React, TypeScript, Vite | 5173 | Command dashboard |
| PostgreSQL | postgres:16 | 5432 | Event, watchlist, camera storage |
| Redis | redis:7 | 6379 | Redis Streams event bus |

4. **Design principle:** AI models produce *observations*; the rule engine turns observations into *events*; the scoring engine turns events into a *risk score*. Models never decide "threat" directly.
5. **Planned data flow:** ai-engine → Redis Streams → PostgreSQL + WebSocket → dashboard (built in Weeks 2-3).
6. **Repository layout:** paste the folder tree from Section 4.
7. **Local development approach:** infra in Docker, services on host (with the reason).
8. **Configuration approach:** `.env` for secrets, `configs/` for behavior.
9. **Privacy note:** use only authorized or permitted footage; note that retention and legal compliance belong to the deploying organization.

### 12.2 `docs/benchmarks.md` (create the empty template now)

```markdown
# Benchmarks

| Date | Hardware | Model | Input size | Cameras | ms/frame | FPS | Notes |
|---|---|---|---|---|---|---|---|
```

Fill it from Day 4 onward. Your final README needs measured numbers.

### 12.3 `docs/decisions/0001-local-dev-approach.md`

Two or three lines: infrastructure in Docker, services on host during Weeks 1-2, full Compose in Weeks 3-4, and why (GPU-in-Docker friction, faster iteration).

### 12.4 `README.md` stub

```markdown
# Border AI: AI Video Intelligence Platform

AI-powered video analytics that turns existing CCTV/IP-camera infrastructure into
a real-time surveillance analytics system: detection, tracking, ANPR, behaviour
rules, threat scoring, alerts, and an investigation dashboard.

## Status
Week 1 in progress: computer vision foundation.

## Quick start
1. cp .env.example .env
2. docker compose up -d
3. python -m venv .venv && source .venv/bin/activate
4. pip install -r ai-engine/requirements.txt -r video-ingestion/requirements.txt
5. cd ai-engine && uvicorn app.main:app --reload --port 8000
6. cd backend && npm install && npm run dev
7. cd frontend && npm install && npm run dev

## Docs
See docs/architecture.md

## Performance
To be filled with measured results (see docs/benchmarks.md).
```

**Features delivered:** architecture, benchmark template, decision log, and README in place.

---

## 13. Optional: `Makefile` Shortcuts

```makefile
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
```

(Makefile recipes must be indented with a real tab. On Windows without `make`, skip this.)

---

## 14. Task 11: Verification Checklist (Definition of Done)

Run through every item before committing.

- [ ] `git status` is clean after the first commit and `.env` is not tracked
- [ ] Folder structure matches Section 4.1
- [ ] Branches `main`, `develop`, and all four `feature/*` exist locally and on GitHub
- [ ] `docker compose ps` shows Postgres and Redis as `healthy`
- [ ] `psql SELECT 1` works; `redis-cli ping` returns `PONG`
- [ ] `curl localhost:8000/health` returns ai-engine status with CUDA info
- [ ] `curl localhost:4000/health` returns `postgres: up` and `redis: up`
- [ ] Frontend loads at `localhost:5173`
- [ ] `YOLO('yolov8n.pt')` loads without errors
- [ ] `torch.cuda.is_available()` result is known and recorded (True or False)
- [ ] `configs/app.yaml`, `cameras.json`, and `zones/CAM_001.json` exist
- [ ] `docs/architecture.md`, `docs/benchmarks.md`, and `README.md` exist
- [ ] At least one test video is placed in `datasets/videos/` (and is gitignored)

---

## 15. First Commits

```bash
git checkout develop
git add .
git status                      # confirm no .env, no videos, no weights
git commit -m "chore: initial project structure, configs, and service skeletons"
git push origin develop
```

Suggested split if you prefer smaller commits:

1. `chore: add project structure and gitignore`
2. `chore: add docker-compose with postgres and redis`
3. `feat: add fastapi ai-engine skeleton with health endpoint`
4. `feat: add typescript backend skeleton with health endpoint`
5. `feat: add react frontend skeleton`
6. `docs: add architecture, README, and benchmark template`

---

## 16. Features Delivered by End of Day 1

- One-command infrastructure start (`docker compose up -d`)
- FastAPI AI engine with `/health` (reports GPU availability)
- Node/TypeScript backend with `/health` (checks PostgreSQL and Redis)
- React + TypeScript frontend running
- Final folder structure, Git branching model, and `.gitignore` rules
- Shared configuration conventions (`.env` plus `configs/`)
- Architecture documentation and benchmark template

---

## 17. Challenges and How to Handle Them

| Challenge | Why it happens | What to do |
|---|---|---|
| GPU inside Docker fails | Needs NVIDIA Container Toolkit and matching CUDA/driver versions | Do not attempt today. Run the AI engine on the host; containerize in Week 3-4 |
| PyTorch installs CPU-only by accident | Default `pip install torch` may pick the CPU build | Install PyTorch first using the command from pytorch.org, then install the rest |
| Python / Node version conflicts | Different system versions, especially on Windows | Use Python 3.11 in a venv and Node 20 LTS. Pin versions after it works |
| Port already in use (5432, 6379, 8000, 4000, 5173) | Existing local Postgres or Redis installs | Change the port in `.env` and `docker-compose.yml`, or stop the local service |
| Backend cannot connect to Postgres | Wrong host or `.env` path, or the container is still starting | Wait for `healthy`, check `POSTGRES_HOST=localhost`, and confirm the `dotenv` path |
| Vite refuses a non-empty folder | `frontend/` already has `.gitkeep` or placeholders | Remove placeholders or scaffold elsewhere and move the files |
| Line-ending issues (CRLF vs LF) | Windows editors and Git | Use `.gitattributes` (Section 6.2) and set `git config core.autocrlf input` |
| Windows file performance / path errors | Repo under `/mnt/c` in WSL, or hardcoded paths | Keep the repo in the WSL home directory and use `pathlib` + `BASE_DIR` |
| Large files accidentally committed | Videos and `.pt` files added with `git add .` | `.gitignore` is set before the first commit; always check `git status` first |
| Empty folders missing on GitHub | Git does not track empty directories | `.gitkeep` files (already in the setup script) |
| Over-engineering Day 1 | Temptation to add auth, migrations, CI, Kubernetes | Follow the "do not do today" list below |
| Secrets committed by mistake | `.env` not ignored early enough | `.gitignore` first, `.env.example` only in Git. If a secret leaks, rotate it |

### Do NOT do today

- Ingestion code (Day 2)
- YOLO detector class (Days 3-4)
- Tracking (Day 5)
- Zone logic (Day 6)
- Database schema design or migrations (Week 2)
- Authentication, RBAC, or JWT (Week 3-4)
- CI/CD pipelines
- Nginx, Prometheus, or Grafana (later)
- Styling the frontend

---

## 18. Preparing for Day 2

Before you stop for the day:

1. Put **3-5 test videos** into `datasets/videos/`: one person walking, one with vehicles, one night or low-light clip, one crowded or occluded scene. Use only footage you are permitted to use, and note the source and license in `datasets/README.md`.
2. Note the resolution and FPS of each clip (you can check with `ffprobe` or OpenCV).
3. Set up a local RTSP simulator for Day 2 if you can: MediaMTX (a single binary or Docker image) plus FFmpeg looping a video file into it. This lets you test RTSP without a physical camera.
4. Write down anything that did not go smoothly today in `docs/decisions/` so it is not forgotten.

**Day 2 goal:** `VideoSource` abstraction (file + RTSP), `CameraManager`, and three cameras running at once with a frame ID, timestamp, and FPS overlay.
