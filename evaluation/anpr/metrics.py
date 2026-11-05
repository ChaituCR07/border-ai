"""Core ANPR evaluation metrics, alignment, CER, exact matching, and confusion analysis."""
from collections import Counter
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

CONFUSABLE_FROM = "OQDIBSZG"
CONFUSABLE_TO = "00018526"
TRANS_TABLE = str.maketrans(CONFUSABLE_FROM, CONFUSABLE_TO)


def plate_norm(s: Optional[str]) -> str:
    """Normalizes plate string: uppercase and strip all non-alphanumeric characters."""
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def plate_key(s: Optional[str]) -> str:
    """Computes look-alike equivalence key with character substitutions."""
    return plate_norm(s).translate(TRANS_TABLE)


def align(gt: str, pred: str) -> Tuple[int, List[Tuple[str, str, str]]]:
    """Computes Levenshtein edit distance and deterministic alignment operations.

    Operations returned: List of (op_type, gt_char, pred_char)
    where op_type is in {"match", "sub", "del", "ins"}.
    Tie-breaking prefers diagonal moves (match/substitution) over insertions/deletions.
    """
    n, m = len(gt), len(pred)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if gt[i - 1] == pred[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,        # deletion from gt
                dp[i][j - 1] + 1,        # insertion into pred
                dp[i - 1][j - 1] + cost,  # match or substitution
            )

    i, j = n, m
    ops: List[Tuple[str, str, str]] = []

    # Backtrack path with deterministic tie-breaking (prefer diagonal move)
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0 if gt[i - 1] == pred[j - 1] else 1):
            op = "match" if gt[i - 1] == pred[j - 1] else "sub"
            ops.append((op, gt[i - 1], pred[j - 1]))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("del", gt[i - 1], ""))
            i -= 1
        else:
            ops.append(("ins", "", pred[j - 1]))
            j -= 1

    return dp[n][m], ops[::-1]


def score_pair(
    gt: str,
    pred: Optional[str],
    plate_key_fn: Callable[[Optional[str]], str] = plate_key,
) -> Dict[str, Any]:
    """Scores a single GT plate vs predicted plate pair."""
    g = plate_norm(gt)
    p = plate_norm(pred)

    if not g:
        raise ValueError("Ground truth plate cannot be empty after normalization")

    if not p:
        # Non-emitted prediction: all characters count as deletions
        dist = len(g)
        ops = [("del", char, "") for char in g]
        return {
            "exact": False,
            "near_miss": False,
            "lookalike_equiv": False,
            "edit_distance": dist,
            "gt_len": len(g),
            "ops": ops,
            "emitted": False,
            "gt": g,
            "pred": "",
        }

    dist, ops = align(g, p)
    is_exact = (g == p)
    is_near_miss = (dist == 1)
    is_lookalike = is_exact or (plate_key_fn(g) == plate_key_fn(p))

    return {
        "exact": is_exact,
        "near_miss": is_near_miss,
        "lookalike_equiv": is_lookalike,
        "edit_distance": dist,
        "gt_len": len(g),
        "ops": ops,
        "emitted": True,
        "gt": g,
        "pred": p,
    }


def corpus_metrics(pairs: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregates corpus-level metrics with micro-averaged character accuracy."""
    if not pairs:
        return {
            "char_accuracy": 0.0,
            "plate_exact": 0.0,
            "near_miss": 0.0,
            "lookalike_equiv": 0.0,
            "read_rate": 0.0,
            "accuracy_among_emitted": 0.0,
        }

    total_chars = sum(x["gt_len"] for x in pairs)
    total_errors = sum(x["edit_distance"] for x in pairs)
    n = len(pairs)

    char_accuracy = max(0.0, 1.0 - (total_errors / total_chars)) if total_chars > 0 else 0.0
    plate_exact = sum(1 for x in pairs if x["exact"]) / n
    near_miss = sum(1 for x in pairs if x["near_miss"]) / n
    lookalike_equiv = sum(1 for x in pairs if x["lookalike_equiv"]) / n
    read_rate = sum(1 for x in pairs if x["emitted"]) / n

    emitted_pairs = [x for x in pairs if x["emitted"]]
    acc_emitted = (
        sum(1 for x in emitted_pairs if x["exact"]) / len(emitted_pairs)
        if emitted_pairs
        else 0.0
    )

    return {
        "char_accuracy": char_accuracy,
        "plate_exact": plate_exact,
        "near_miss": near_miss,
        "lookalike_equiv": lookalike_equiv,
        "read_rate": read_rate,
        "accuracy_among_emitted": acc_emitted,
    }


def confusion(pairs: List[Dict[str, Any]]) -> Counter:
    """Builds a frequency counter of (gt_char, pred_char) errors."""
    c: Counter = Counter()
    for x in pairs:
        for op, g, p in x.get("ops", []):
            if op in ("sub", "del", "ins"):
                gt_c = g if g else "∅"
                pred_c = p if p else "∅"
                c[(gt_c, pred_c)] += 1
    return c
