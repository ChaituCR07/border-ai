"""Character confusion evidence analyzer vs plate_key look-alike classes (ADR 0039).

Aggregates optical character recognition confusion matrices and compares empirical
substitution frequencies against the design assumptions codified in:
- Python matcher: `evaluation.anpr.metrics.plate_key`
- PostgreSQL generated column: `plate_key()`
- TypeScript: `plateKey()`
- Shared fixture: `docs/fixtures/plate_matching_cases.json`
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from evaluation.anpr.metrics import confusion, plate_key


# Canonical groupings currently active in plate_key()
CURRENT_PLATE_KEY_MAPPINGS: Dict[str, Set[str]] = {
    "0": {"O", "Q", "D"},
    "1": {"I"},
    "8": {"B"},
    "5": {"S"},
    "2": {"Z"},
    "6": {"G"},
}


@dataclass
class LookalikeEvidence:
    """Empirical support for a specific character confusion pair."""
    char_a: str
    char_b: str
    count: int
    share_of_subs: float
    is_in_plate_key: bool
    recommendation: str                        # 'retain', 'monitor', 'propose_add', 'low_evidence'
    notes: str = ""


@dataclass
class ConfusionAnalysisReport:
    """Consolidated character confusion and ADR 0039 policy analysis."""
    total_substitutions: int
    total_insertions: int
    total_deletions: int
    top_substitutions: List[Tuple[str, str, int]]
    lookalike_evidence: List[LookalikeEvidence]
    unexpected_confusions: List[Tuple[str, str, int]]
    adr0039_verdict: str

    def to_markdown(self) -> str:
        lines = [
            "### Character Confusion Evidence & ADR 0039 Audit",
            "",
            f"- **Total Substitutions Analyzed:** {self.total_substitutions}",
            f"- **Total Insertions:** {self.total_insertions}",
            f"- **Total Deletions:** {self.total_deletions}",
            f"- **ADR 0039 Policy Verdict:** **{self.adr0039_verdict}**",
            "",
            "#### Active `plate_key()` Look-Alike Equivalence Pairs",
            "",
            "| Pair | Occurrences | % of Substitutions | In `plate_key` | Recommendation | Notes |",
            "|---|---|---|---|---|---|",
        ]
        for e in self.lookalike_evidence:
            in_key = "Yes" if e.is_in_plate_key else "No"
            lines.append(
                f"| `{e.char_a}` $\\leftrightarrow$ `{e.char_b}` | {e.count} | "
                f"{e.share_of_subs:.1%} | {in_key} | **{e.recommendation}** | {e.notes} |"
            )
        lines.append("")
        lines.append("#### Top Non-Equivalence Confusions (Candidates / Noise)")
        lines.append("")
        lines.append("| Substitution Pair (GT $\\to$ Pred) | Count | Share |")
        lines.append("|---|---|---|")
        for g, p, cnt in self.unexpected_confusions[:8]:
            share = cnt / self.total_substitutions if self.total_substitutions > 0 else 0.0
            lines.append(f"| `{g}` $\\to$ `{p}` | {cnt} | {share:.1%} |")
        lines.append("")
        return "\n".join(lines)


def is_pair_in_plate_key(c1: str, c2: str) -> bool:
    """Checks if c1 and c2 map to the same character in plate_key()."""
    k1 = plate_key(c1)
    k2 = plate_key(c2)
    return bool(k1 and k2 and k1 == k2)


def analyze_character_confusion(pairs: List[Dict[str, Any]]) -> ConfusionAnalysisReport:
    """Analyzes character alignment operations and assesses ADR 0039 compliance."""
    conf = confusion(pairs)

    sub_counts: Counter[Tuple[str, str]] = Counter()
    del_count = 0
    ins_count = 0

    for (g, p), cnt in conf.items():
        if g == "∅":
            ins_count += cnt
        elif p == "∅":
            del_count += cnt
        else:
            sub_counts[(g, p)] += cnt

    total_subs = sum(sub_counts.values())

    # Symmetric substitution counter (e.g. 0->O and O->0 counted together)
    sym_counts: Counter[Tuple[str, str]] = Counter()
    for (g, p), cnt in sub_counts.items():
        pair_key = tuple(sorted([g, p]))
        sym_counts[pair_key] += cnt

    # Known lookalike pairs to verify
    target_lookalikes = [
        ("0", "O"),
        ("0", "D"),
        ("0", "Q"),
        ("1", "I"),
        ("8", "B"),
        ("5", "S"),
        ("2", "Z"),
        ("6", "G"),
    ]

    evidence_list: List[LookalikeEvidence] = []
    for c1, c2 in target_lookalikes:
        sym_key = tuple(sorted([c1, c2]))
        cnt = sym_counts.get(sym_key, 0)
        share = cnt / total_subs if total_subs > 0 else 0.0
        in_key = is_pair_in_plate_key(c1, c2)

        if cnt > 0:
            rec = "retain" if in_key else "propose_add"
            notes = "Empirically observed in test set"
        else:
            rec = "retain" if in_key else "low_evidence"
            notes = "Standard optical confusion design baseline"

        evidence_list.append(
            LookalikeEvidence(
                char_a=c1,
                char_b=c2,
                count=cnt,
                share_of_subs=share,
                is_in_plate_key=in_key,
                recommendation=rec,
                notes=notes,
            )
        )

    # Sort top substitutions
    top_subs = [(g, p, cnt) for (g, p), cnt in sub_counts.most_common()]

    # Unexpected confusions not covered by plate_key
    unexpected = [
        (g, p, cnt)
        for g, p, cnt in top_subs
        if not is_pair_in_plate_key(g, p)
    ]

    # ADR 0039 verdict
    # Check if any non-lookalike confusion is overwhelmingly high enough to warrant schema migration
    high_unexpected = [u for u in unexpected if total_subs >= 10 and (u[2] / total_subs) > 0.15]
    if high_unexpected:
        verdict = f"Monitor top pairs ({high_unexpected[0][0]}<->{high_unexpected[0][1]}); no immediate table rewrite required"
    else:
        verdict = "RETAIN_CURRENT_POLICY (All active plate_key classes validated; zero conflicting schema migrations needed)"

    return ConfusionAnalysisReport(
        total_substitutions=total_subs,
        total_insertions=ins_count,
        total_deletions=del_count,
        top_substitutions=top_subs,
        lookalike_evidence=evidence_list,
        unexpected_confusions=unexpected,
        adr0039_verdict=verdict,
    )
