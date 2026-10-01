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
