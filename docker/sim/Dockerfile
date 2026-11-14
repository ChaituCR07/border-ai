# syntax=docker/dockerfile:1.7
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -M -s /usr/sbin/nologin app

WORKDIR /app

COPY --chown=10001:10001 docker/sim/supervisor.py ./supervisor.py
COPY --chown=10001:10001 scripts/sim/cctv_sim.py ./cctv_sim.py

USER 10001:10001

CMD ["python", "supervisor.py", "--scenario", "demo"]
