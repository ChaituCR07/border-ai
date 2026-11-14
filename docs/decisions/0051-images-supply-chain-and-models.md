# ADR 0051: Container Images, Supply Chain Integrity, and Model Distribution

## Status
Accepted

## Context
Deploying enterprise surveillance software requires rigorous container supply chain hygiene. Container images must be non-root, minimal in size, free of development artifacts, reproducible across builds, and protected against unverified third-party model weights or dependencies.

## Decision

1. **Multi-Stage Container Builds:**
   - **Backend:** Node.js 22 Bookworm slim base. Dependencies installed via `npm ci` in builder stage; TypeScript compiled to `/dist`; production runtime excludes devDependencies, compilers, and test suites. Runs as unprivileged UID/GID `10001:10001`.
   - **Frontend:** Multi-stage build compiling React 19/Vite assets, packaged into `nginxinc/nginx-unprivileged:1.27-alpine` runtime. Static assets served with immutable cache headers and SPA routing fallbacks.
   - **AI Engine & Sink:** Shared Python 3.11 slim image with separate entrypoints. Virtual environment isolated in `/opt/venv`. Runs as unprivileged UID/GID `10001:10001` with explicit `read_only: true` root filesystem and memory-mapped caches in tmpfs.

2. **Supply Chain & Digest Pinning:**
   - Base images are strictly pinned by cryptographic digest (`image@sha256:...`) to eliminate upstream drift and tag mutability.
   - Dependency lockfiles (`package-lock.json`, requirements locks with SHA-256 hashes) are mandatory.
   - Comprehensive `.dockerignore` prevents accidental inclusion of local secrets, git histories, raw datasets, video footage, and build artifacts.

3. **Model Weight Lifecycle & Verification:**
   - Model weights (YOLOv8, PaddleOCR, YuNet) are **NOT** baked directly into container layers.
   - A dedicated `model-init` container verifies all required weights against a cryptographic manifest (`configs/models.lock.json`) containing model names, paths, sources, licenses, and SHA-256 digests.
   - Tampered or corrupted model files fail closed, halting engine initialization before video processing begins.
   - Air-gapped/offline installations mount pre-verified weights into the named `models` volume.

## Consequences

- Runtime images remain lean, hardened, and free of unnecessary tools or package manager caches.
- No dynamic code or model downloads occur silently inside live production containers.
- Model licensing (AGPL-3.0 for Ultralytics weights, Apache-2.0 for OCR) is explicitly tracked and auditable.
