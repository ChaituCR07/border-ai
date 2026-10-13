import re
from dataclasses import dataclass
from typing import List, Optional

INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ", "HP", "HR",
    "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "OR",
    "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"}

DIGIT_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "4": "A", "5": "S", "6": "G", "7": "T", "8": "B"}
LETTER_TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2",
                   "A": "4", "S": "5", "G": "6", "T": "7", "B": "8"}

# (district digits, series letters), most common first. KA01AB1234 is (2, 2).
LAYOUTS = [(2, 2), (2, 1), (2, 3), (1, 2), (1, 1), (1, 3)]
LEVEL_RANK = {"invalid": 0, "loose": 1, "strict": 2}


def clean_text(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


@dataclass
class IndianCandidate:
    text: str
    subs: int            # characters changed by the correction
    state_ok: bool       # the state code exists


@dataclass
class FormatCheck:
    text: str
    level: str           # strict | loose | invalid
    subs: int = 0


def _fit(window: str, d: int, s: int) -> Optional[IndianCandidate]:
    kinds = "L" * 2 + "D" * d + "L" * s + "D" * 4
    if len(window) != len(kinds):
        return None
    # District 0 is invalid for single digit district
    if d == 1 and window[2] == "0":
        return None
    out, subs = [], 0
    series_start = 2 + d
    series_end = series_start + s
    for i, (ch, kind) in enumerate(zip(window, kinds)):
        if kind == "L":
            if ch.isalpha():
                # In Indian vehicle series, I, O, Q are disallowed by RTO rules
                if series_start <= i < series_end and ch in ("I", "O", "Q"):
                    return None
                out.append(ch)
            elif ch in DIGIT_TO_LETTER:
                sub_ch = DIGIT_TO_LETTER[ch]
                if series_start <= i < series_end and sub_ch in ("I", "O", "Q"):
                    return None
                out.append(sub_ch)
                subs += 1
            else:
                return None
        else:
            if ch.isdigit():
                out.append(ch)
            elif ch in LETTER_TO_DIGIT:
                out.append(LETTER_TO_DIGIT[ch])
                subs += 1
            else:
                return None
    text = "".join(out)
    return IndianCandidate(text, subs, text[:2] in INDIAN_STATE_CODES)


def correct_indian(t: str) -> Optional[IndianCandidate]:
    """Best Indian-format reading inside the cleaned text t, or None."""
    if len(t) > 16:
        return None
    best, best_key = None, None
    for start in range(len(t)):
        for end in range(start + 8, min(len(t), start + 11) + 1):
            for pref, (d, s) in enumerate(LAYOUTS):
                cand = _fit(t[start:end], d, s)
                if cand is None:
                    continue
                end_discarded = len(t) - end
                discarded = start + end_discarded
                # Unknown state code is only allowed if it matches the text without discarded noise
                if not cand.state_ok and discarded > 1:
                    continue
                # Discarding trailing digits is penalized more heavily than prefix (e.g. IND)
                cost = cand.subs + end_discarded * 2 + start
                key = (0 if cand.state_ok else 1, cost, cand.subs, pref)
                if best_key is None or key < best_key:
                    best, best_key = cand, key
    return best


class PlateFormats:
    """Applies the configured formats. strict = Indian format with a real state code;
    loose = Indian shape with an unknown state code, or the generic format; invalid = neither."""

    def __init__(self, names: List[str]):
        self.names = list(names)

    def check(self, raw: str) -> FormatCheck:
        t = clean_text(raw)
        if "indian" in self.names:
            cand = correct_indian(t)
            if cand is not None:
                return FormatCheck(cand.text, "strict" if cand.state_ok else "loose", cand.subs)
        if "generic" in self.names and re.fullmatch(r"[A-Z0-9]{5,10}", t):
            return FormatCheck(t, "loose", 0)
        return FormatCheck(t, "invalid", 0)
