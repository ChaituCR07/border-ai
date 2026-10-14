import argparse
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.anpr.plate_format import DIGIT_TO_LETTER, LETTER_TO_DIGIT  # noqa: E402
from app.watchlist.config import WatchlistConfig  # noqa: E402
from app.watchlist.matcher import decide_status, lookup_in_repo, score_for  # noqa: E402
from app.watchlist.repo import InMemoryWatchlistRepo  # noqa: E402

LETTERS = "ABCDEFGHJKLMNPRSTUVWXYZ"


def random_plate(rng):
    return (rng.choice(["KA", "MH", "TN", "DL", "AP"]) + f"{rng.randint(1, 99):02d}"
            + "".join(rng.choice(LETTERS) for _ in range(2)) + f"{rng.randint(1, 9999):04d}")


def lookalike(p, rng):
    idx = [i for i, c in enumerate(p) if c in DIGIT_TO_LETTER or c in LETTER_TO_DIGIT]
    i = rng.choice(idx)
    c = p[i]
    swap = DIGIT_TO_LETTER.get(c) or LETTER_TO_DIGIT.get(c)
    return p[:i] + swap + p[i + 1:]


def plain_substitution(p, rng):
    i = rng.randrange(len(p))
    pool = "0123456789" if p[i].isdigit() else LETTERS
    c = rng.choice([x for x in pool if x != p[i]])
    return p[:i] + c + p[i + 1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listed", type=int, default=200)
    ap.add_argument("--unlisted", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--near-max", type=float, default=1.0)
    ap.add_argument("--near-can-alert", action="store_true")
    ap.add_argument("--alert-min-conf", type=float, default=0.70)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    cfg = WatchlistConfig(near_max_distance=args.near_max, near_can_alert=args.near_can_alert,
                          alert_min_confidence=args.alert_min_conf)
    repo = InMemoryWatchlistRepo()
    listed = set()
    while len(listed) < args.listed:
        listed.add(random_plate(rng))
    for p in listed:
        repo.add("VEHICLE", p, "n", "HIGH")
    listed = sorted(listed)

    cases = []                                                        # (label, plate read, should_match)
    for p in listed:
        cases += [("listed: exact read", p, True),
                  ("listed: look-alike OCR slip", lookalike(p, rng), True),
                  ("listed: plain 1-char OCR error", plain_substitution(p, rng), True)]
    unlisted = set()
    while len(unlisted) < args.unlisted:
        q = random_plate(rng)
        if q not in listed:
            unlisted.add(q)
    cases += [("unlisted: random plate", q, False) for q in sorted(unlisted)]
    cases += [("unlisted: 1 char from a listed plate (look-alike pair)", lookalike(p, rng), False)
              for p in listed[:50]]                                   # a different real plate that happens to look similar

    results = {}
    for label, read, should in cases:
        for conf in (0.95, 0.75, 0.55):
            m = lookup_in_repo(repo, read, cfg)
            status = None
            if m is not None:
                status = decide_status(m, conf, score_for(conf, m.quality), cfg)
            results.setdefault((label, conf), Counter())[status or "none"] += 1

    print(f"{'case':<56}{'conf':>6}{'alert':>8}{'review':>8}{'none':>8}")
    for (label, conf), c in sorted(results.items()):
        print(f"{label:<56}{conf:>6}{c['alert']:>8}{c['review']:>8}{c['none']:>8}")
    print("\nRead this as: for the 'unlisted' rows, every alert or review is a FALSE alarm; "
          "for the 'listed' rows, 'none' is a MISSED hit.")


if __name__ == "__main__":
    main()
