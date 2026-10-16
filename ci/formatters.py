"""Formatting and text generation utilities for validation reports."""
from __future__ import annotations

STATUS_LABEL = {
    "pass": "PASS",
    "fail": "FAIL",
    "xfail": "KNOWN BUG",  # fails its golden because of a listed compiler bug
    "xpass": "FIXED?",  # listed as a known bug but passes now
}


def fmt_int(value: float | None) -> str:
    return "-" if value is None else f"{int(value):,}"


def fmt_pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}%"


def fmt_float(value: float | None, precision: int = 1) -> str:
    return "-" if value is None else f"{value:.{precision}f}"


def fmt_diff(current: float | None, baseline: float | None, unit: str = "", invert: bool = False) -> str:
    """Format difference between current and baseline integer counts.
    By default (invert=False), lower is better (e.g. cycles, memory ops, spills).
    When invert=True, higher is better (e.g. slot density, throughput).
    """
    if current is None or baseline is None:
        return "-"
    diff = current - baseline
    if diff == 0:
        return "0 (unchanged)"

    pct = (diff / baseline) * 100 if baseline != 0 else 0
    sign = "+" if diff > 0 else ""

    is_better = (diff < 0) if not invert else (diff > 0)
    if is_better:
        tag = "[IMPROVED]"
    elif abs(pct) <= 1.0 or abs(diff) <= 2:
        tag = "parity (within noise)"
    else:
        tag = "[REGRESSED]"

    if abs(pct) >= 0.1:
        return f"{sign}{int(diff):,}{unit} ({sign}{pct:.1f}%) {tag}"
    else:
        return f"{sign}{int(diff):,}{unit} {tag}"


def fmt_diff_pct(current: float | None, baseline: float | None, invert: bool = True) -> str:
    """Format difference between percentage values (e.g. VLIW density).
    Default invert=True (higher density is better).
    """
    if current is None or baseline is None:
        return "-"
    diff = current - baseline
    if abs(diff) < 0.05:
        return "0.0% (unchanged)"

    sign = "+" if diff > 0 else ""
    is_better = (diff > 0) if invert else (diff < 0)
    tag = "[IMPROVED]" if is_better else "[REGRESSED]"
    return f"{sign}{diff:.1f}% {tag}"


def fmt_ratio(compiled: float | None, handwritten: float | None) -> str:
    if not compiled or not handwritten:
        return "n/a"
    ratio = compiled / handwritten
    if ratio < 0.95:
        pct_faster = (1.0 - ratio) * 100
        return f"**{ratio:.2f}x** *(-{pct_faster:.0f}%)*"
    elif ratio <= 1.05:
        return f"**{ratio:.2f}x** *(parity)*"
    else:
        pct_slower = (ratio - 1.0) * 100
        return f"{ratio:.2f}x *(+{pct_slower:.0f}%)*"


def fmt_spills(spills: int | None) -> str:
    if spills is None:
        return "-"
    if spills == 0:
        return "0"
    return f"**{spills}**"


def counts(results: list[dict]) -> str:
    if not results:
        return "not run"
    parts = []
    for status in ("pass", "fail", "xfail", "xpass"):
        n = sum(1 for r in results if r["status"] == status)
        if n:
            parts.append(f"{n} {status}")
    return ", ".join(parts) or "not run"


def first_line(text: str | None) -> str:
    return (text or "").strip().splitlines()[0] if text else ""
