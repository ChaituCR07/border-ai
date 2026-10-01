# ADR 0001: Local Development Architecture and Environment Strategy

## Context
Running real-time computer vision models (YOLO, tracking, OpenCV) inside Docker during active local development introduces significant friction with GPU passthrough, display rendering, and package re-installation delays across different host operating systems.

## Decision
- **Core Infrastructure (PostgreSQL 16 & Redis 7)** will run inside lightweight Docker containers managed by `docker-compose.yml`.
- **Application Services (AI Engine, Backend, Frontend)** will run natively on the host workstation inside a shared Python virtual environment and local Node.js environments during Weeks 1 and 2.
- Full containerization of all microservices into a unified Docker Compose network will take place in Weeks 3–4 for production packaging and final demonstrations.

## Consequences
- Fast iterative code reloads without container rebuild delays.
- Native access to host hardware acceleration and camera devices.
- Consistent database and Redis state via volume mounts.
