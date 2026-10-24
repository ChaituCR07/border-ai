import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-ingestion"))

from app import config  # noqa: E402
from app.db.events_repo import PostgresEventRepository  # noqa: E402
from app.db.seed import camera_row  # noqa: E402
from app.watchlist.dsn import build_dsn  # noqa: E402
from ingestion.camera_manager import load_camera_configs  # noqa: E402


def main():
    repo = PostgresEventRepository(build_dsn())
    for cfg in load_camera_configs(config.CONFIG_DIR / "cameras.json"):
        row = camera_row(cfg)
        repo.upsert_camera(**row)
        print(f"{row['camera_id']:<10}{row['status']:<10}{row['rtsp_url'] or '(file source)'}")
    repo.close()


if __name__ == "__main__":
    main()
