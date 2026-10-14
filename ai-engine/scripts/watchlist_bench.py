import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import build_dsn  # noqa: E402
from app.watchlist.config import WatchlistConfig  # noqa: E402
from app.watchlist.matcher import lookup_in_repo  # noqa: E402
from app.watchlist.repo import PostgresWatchlistRepo  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
repo, rng, cfg = PostgresWatchlistRepo(build_dsn()), random.Random(2), WatchlistConfig()
letters = "ABCDEFGHJKLMNPRSTUVWXYZ"
print(f"inserting {N} synthetic entries (this takes a moment) ...")
plates = {f"KA{rng.randint(1, 99):02d}{rng.choice(letters)}{rng.choice(letters)}{rng.randint(1000, 9999)}" for _ in range(N)}
inserted_ids = []
for p in plates:
    try:
        e = repo.add("VEHICLE", p, "bench", "LOW", actor="bench")
        inserted_ids.append(e.watchlist_id)
    except Exception:
        pass
target = sorted(plates)[0]
for label, plate in (("exact hit", target), ("miss (near scan)", "MH12XY4321")):
    times = []
    for _ in range(30):
        t = time.perf_counter()
        lookup_in_repo(repo, plate, cfg)
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    print(f"{label:<18} median {times[len(times) // 2]:.2f} ms   p95 {times[int(len(times) * 0.95)]:.2f} ms")

print("cleaning up benchmark entries...")
with repo.pool.connection() as conn:
    conn.execute("DELETE FROM watchlist WHERE created_by = 'bench'")
    conn.execute("DELETE FROM watchlist_audit WHERE actor = 'bench'")
repo.close()
print("done.")
