from typing import List, Tuple, Union


def format_ci_cell(val: float, lo: float, hi: float, is_pct: bool = True) -> str:
    """Formats point estimate with [lo, hi] bootstrap confidence interval."""
    if is_pct:
        return f"{val * 100:.1f}% [{lo * 100:.1f}, {hi * 100:.1f}]"
    return f"{val:.3f} [{lo:.3f}, {hi:.3f}]"


def markdown_table(headers: List[str], rows: List[List[Union[str, int, float]]]) -> str:
    """Generates a clean GFM markdown table."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---" if i == 0 else "---:" for i in range(len(headers))]) + " |",
    ]
    for row in rows:
        formatted_row = [str(x) for x in row]
        lines.append("| " + " | ".join(formatted_row) + " |")
    return "\n".join(lines)
