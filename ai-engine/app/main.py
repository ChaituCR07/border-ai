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
