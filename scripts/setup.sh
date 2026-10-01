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
