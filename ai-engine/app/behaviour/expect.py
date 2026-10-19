from typing import Dict, List, Tuple


def compare_counts(counts: Dict[str, int], expected: Dict[str, int], tolerance: int = 0) -> Tuple[List[dict], bool]:
    rows, ok = [], True
    for key in sorted(set(counts) | set(expected)):
        exp, got = expected.get(key, 0), counts.get(key, 0)
        passed = abs(got - exp) <= tolerance
        ok &= passed
        rows.append({"key": key, "expected": exp, "got": got, "pass": passed})
    return rows, ok
