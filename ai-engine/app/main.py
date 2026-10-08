import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import detect, stream
from app.detection.detector import Detector

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pipeline = getattr(app.state, "pipeline", None)
    # Started by run_pipeline.py --serve: reuse its detector. Otherwise load one for /detect.
    app.state.detector = pipeline.detector if pipeline else Detector.from_config()
    yield
    app.state.detector = None


app = FastAPI(title="Border AI - AI Engine", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect.router)
app.include_router(stream.router)


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
        "model_loaded": getattr(app.state, "detector", None) is not None,
    }
