from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import config

app = FastAPI(title="Border AI - AI Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
