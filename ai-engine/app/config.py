from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]      # border-ai/
load_dotenv(BASE_DIR / ".env")

CONFIG_DIR = Path(
    os.getenv("CONFIG_DIR")
    or ("/configs" if Path("/configs/app.yaml").exists() else ("/app/configs.default" if Path("/app/configs.default/app.yaml").exists() else BASE_DIR / "configs"))
)
OUTPUT_DIR = Path(
    os.getenv("OUTPUT_DIR")
    or ("/data/journal" if Path("/data/journal").exists() else BASE_DIR / "outputs")
)
DATASET_DIR = BASE_DIR / "datasets"
MODEL_DIR = Path(
    os.getenv("MODELS_DIR")
    or ("/models" if Path("/models").exists() else BASE_DIR / "ai-engine" / "models")
)


def load_app_config() -> dict:
    with open(CONFIG_DIR / "app.yaml", "r") as f:
        return yaml.safe_load(f)


AI_ENGINE_PORT = int(os.getenv("AI_ENGINE_PORT", 8000))
APP_ENV = os.getenv("APP_ENV", "development")
