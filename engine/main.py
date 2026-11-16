import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Add project roots to sys.path so engine and ai-engine modules resolve cleanly
ROOT_DIR = Path(__file__).resolve().parents[1]
AI_ENGINE_DIR = ROOT_DIR / "ai-engine"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(AI_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_DIR))

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("engine.main")

app = FastAPI(title="Border-AI Engine Runtime", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "ai-engine", "time": time.time()}


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
        "cuda": cuda,
        "device": device,
    }


def _verify_token_if_needed(token: Optional[str], camera_id: str):
    jwks_url = os.getenv("JWKS_URL")
    if not jwks_url or not token:
        return
    try:
        import json
        import urllib.request
        from engine.security.stream_auth import verify_stream_token
        req = urllib.request.Request(jwks_url, headers={"User-Agent": "ai-engine"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            jwks = json.loads(resp.read().decode("utf-8"))
        verify_stream_token(token, camera_id, jwks)
    except Exception as e:
        logger.warning("Stream token verification failed for %s: %s", camera_id, e)
        raise HTTPException(status_code=403, detail="Invalid stream token")


BOUNDARY = "frame"


def generate_mjpeg_stream(camera_id: str):
    import cv2
    import numpy as np
    while True:
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        text = f"BORDER-AI | {camera_id} | {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        cv2.putText(img, text, (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)
        _, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        data = jpeg.tobytes()
        yield (b"--" + BOUNDARY.encode() + b"\r\nContent-Type: image/jpeg\r\n"
               b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n")
        time.sleep(0.1)


@app.get("/cam/{camera_id}.mjpg")
@app.get("/cam/{camera_id}")
@app.get("/stream/{camera_id}")
def stream_camera(camera_id: str, token: Optional[str] = Query(None)):
    clean_id = camera_id.replace(".mjpg", "")
    _verify_token_if_needed(token, clean_id)
    return StreamingResponse(
        generate_mjpeg_stream(clean_id),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
    )


def main():
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info("Starting Border-AI Engine service on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
