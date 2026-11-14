# syntax=docker/dockerfile:1.7
ARG PY_IMAGE=python:3.11-slim-bookworm

# Stage 1: Build Virtual Environment & Dependencies
FROM ${PY_IMAGE} AS builder
ARG TORCH_VARIANT=cpu

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/opt/venv/bin:$PATH

RUN python -m venv /opt/venv

COPY docker/ai-engine/requirements/${TORCH_VARIANT}.lock /tmp/requirements.lock
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.lock

# Stage 2: Hardened Runtime Container
FROM ${PY_IMAGE} AS runtime
ARG TORCH_VARIANT=cpu

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC \
    PATH=/opt/venv/bin:$PATH \
    OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" \
    HOME=/tmp \
    PADDLE_HOME=/tmp/paddle \
    TORCH_HOME=/tmp/torch \
    YOLO_CONFIG_DIR=/tmp/ultralytics

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user
RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -M -s /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY --chown=10001:10001 ai-engine/ /app/ai-engine/
COPY --chown=10001:10001 engine/ /app/engine/
COPY --chown=10001:10001 configs/ /app/configs.default/
COPY --chmod=755 docker/ai-engine/entrypoint.sh /entrypoint.sh

USER 10001:10001
EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]

HEALTHCHECK --interval=10s --timeout=3s --retries=6 --start-period=60s \
  CMD ["python", "-m", "engine.healthcheck"]

CMD ["python", "-m", "engine.main"]
