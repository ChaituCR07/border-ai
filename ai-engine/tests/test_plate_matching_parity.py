import json
from pathlib import Path
import re
import pytest

CONFUSABLE_FROM = 'OQDIBSZG'
CONFUSABLE_TO = '00018526'
TRANS_TABLE = str.maketrans(CONFUSABLE_FROM, CONFUSABLE_TO)


def plate_norm(s: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', (s or '').upper())


def plate_key(s: str) -> str:
    return plate_norm(s).translate(TRANS_TABLE)


def classify_match(query: str, candidate: str, mode: str = 'lookalike') -> str:
    q_norm = plate_norm(query)
    c_norm = plate_norm(candidate)

    if not q_norm or not c_norm:
        return 'none'

    if mode == 'prefix':
        # Ensure regex metacharacters in query don't behave as wildcards
        if c_norm.startswith(q_norm):
            return 'prefix'
        return 'none'

    if mode == 'contains':
        if q_norm in c_norm:
            return 'partial'
        return 'none'

    # default lookalike mode
    if q_norm == c_norm:
        return 'exact'

    if plate_key(query) == plate_key(candidate):
        return 'lookalike'

    return 'none'


def test_plate_matching_parity_with_fixture():
    fixture_path = Path(__file__).resolve().parents[2] / 'docs' / 'fixtures' / 'plate_matching_cases.json'
    assert fixture_path.exists(), f"Fixture missing at {fixture_path}"

    with open(fixture_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)

    for case in cases:
        q = case['query']
        cand = case['candidate']
        expected = case['expect']
        mode = case.get('mode', 'lookalike')

        actual = classify_match(q, cand, mode=mode)
        assert actual == expected, (
            f"Failed for query='{q}', candidate='{cand}', mode='{mode}': "
            f"expected '{expected}', got '{actual}'"
        )
