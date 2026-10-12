from statistics import mean
from typing import Dict, List

from app.anpr.types import PlateRecord


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def char_accuracy(pred: str, truth: str) -> float:
    """1 - (edit distance / length of the true plate), floored at 0."""
    if not truth:
        return 0.0
    return max(0.0, 1.0 - levenshtein(pred, truth) / len(truth))


def evaluate_records(records: List[PlateRecord], truth: List[dict], slack_s: float = 1.0) -> Dict:
    """Match each true plate (with its visibility window in video seconds) to the closest
    recognized vehicle whose track overlaps that window."""
    used, rows = set(), []
    for t in sorted(truth, key=lambda x: x["first_s"]):
        cands = [r for r in records
                 if r.last_seen >= t["first_s"] - slack_s and r.first_seen <= t["last_s"] + slack_s]
        pool = [r for r in cands if id(r) not in used] or cands
        if not pool:
            rows.append({"truth": t["plate"], "pred": None, "exact": False, "char_acc": 0.0,
                         "confidence": None, "single_read_acc": None})
            continue
        best = min(pool, key=lambda r: (levenshtein(r.plate, t["plate"]), -r.confidence))
        used.add(id(best))
        reads = [txt for txt, _ in best.read_log]
        rows.append({
            "truth": t["plate"], "pred": best.plate, "exact": best.plate == t["plate"],
            "char_acc": char_accuracy(best.plate, t["plate"]), "confidence": best.confidence,
            "single_read_acc": (sum(x == t["plate"] for x in reads) / len(reads)) if reads else None})

    extras = [r for r in records if id(r) not in used]
    n = len(truth)
    right = [r["confidence"] for r in rows if r["exact"]]
    wrong = [r["confidence"] for r in rows if r["pred"] is not None and not r["exact"]]
    singles = [r["single_read_acc"] for r in rows if r["single_read_acc"] is not None]
    return {
        "n_truth": n,
        "exact": sum(r["exact"] for r in rows),
        "plate_accuracy": (sum(r["exact"] for r in rows) / n) if n else 0.0,
        "mean_char_accuracy": mean(r["char_acc"] for r in rows) if rows else 0.0,
        "missed": sum(r["pred"] is None for r in rows),
        "extras": len(extras),
        "mean_conf_when_correct": mean(right) if right else None,
        "mean_conf_when_wrong": mean(wrong) if wrong else None,
        "mean_single_read_accuracy": mean(singles) if singles else None,
        "rows": rows,
    }


def format_report(rep: Dict) -> str:
    out = [f"{'truth':<12}{'predicted':<12}{'exact':>6}{'char acc':>10}{'conf':>7}{'single-read acc':>17}"]
    for r in rep["rows"]:
        conf = f"{r['confidence']:.2f}" if r["confidence"] is not None else "-"
        sra = f"{r['single_read_acc']:.2f}" if r["single_read_acc"] is not None else "-"
        out.append(f"{r['truth']:<12}{str(r['pred']):<12}{str(r['exact']):>6}"
                   f"{r['char_acc']:>10.2f}{conf:>7}{sra:>17}")
    out.append("")
    out.append(f"plate-level accuracy : {rep['plate_accuracy']:.1%}  ({rep['exact']}/{rep['n_truth']})")
    out.append(f"character accuracy   : {rep['mean_char_accuracy']:.1%}")
    out.append(f"missed vehicles      : {rep['missed']}   extra (unmatched) records: {rep['extras']}")
    if rep["mean_single_read_accuracy"] is not None:
        out.append(f"single-read accuracy : {rep['mean_single_read_accuracy']:.1%}  "
                   f"(vs consensus {rep['plate_accuracy']:.1%})")
    if rep["mean_conf_when_correct"] is not None:
        wrong = rep["mean_conf_when_wrong"]
        out.append(f"mean confidence      : correct {rep['mean_conf_when_correct']:.2f}"
                   f" | wrong {('%.2f' % wrong) if wrong is not None else '-'}")
    return "\n".join(out)
