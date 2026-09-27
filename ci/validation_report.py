#!/usr/bin/env python3
"""Render validation results (``--json`` output of the two runners) as Markdown.

Writes the report to ``--out`` and, when running in GitHub Actions, appends it to
the job summary. This script only reports; the runners' exit codes are the gate.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

STATUS_LABEL = {"pass": "PASS", "fail": "FAIL", "unchecked": "UNCHECKED"}


def load(path: Path | None) -> list[dict]:
    if path is None or not path.exists():
        return []
    return json.loads(path.read_text())["results"]


def perf_value(result: dict | None, key: str) -> float | None:
    if not result or not result.get("perf"):
        return None
    return result["perf"].get(key)


def fmt_int(value: float | None) -> str:
    return "n/a" if value is None else f"{int(value):,}"


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0f}%"


def fmt_ratio(compiled: float | None, handwritten: float | None) -> str:
    if not compiled or not handwritten:
        return "n/a"
    return f"{compiled / handwritten:.2f}x"


def counts(results: list[dict]) -> str:
    parts = []
    for status in ("pass", "unchecked", "fail"):
        n = sum(1 for r in results if r["status"] == status)
        if n:
            parts.append(f"{n} {status}")
    return ", ".join(parts) or "no results"


def first_line(text: str | None) -> str:
    return (text or "").strip().splitlines()[0] if text else ""


def render(unit: list[dict], kernel: list[dict]) -> str:
    lines: list[str] = ["# Compiler validation", ""]
    ref = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME")
    sha = os.environ.get("GITHUB_SHA", "")[:8]
    if ref or sha:
        lines += [f"Branch `{ref}` at `{sha}`", ""]

    failed = [r for r in unit + kernel if r["status"] == "fail"]
    verdict = "**Accuracy gate: FAILED**" if failed else "**Accuracy gate: PASSED**"
    lines += [
        verdict,
        "",
        f"- Unit tests: {counts(unit)}",
        f"- Kernels (compiled): {counts(kernel)}",
        f"- Kernels (handwritten, informational): "
        f"{counts([r['handwritten'] for r in kernel if 'handwritten' in r])}",
        "",
        "## Kernels: compiled vs handwritten",
        "",
        "Both versions run on the same seeded memory image and are checked by the same "
        "golden. Packet ratio = compiled / handwritten packets executed (lower is better "
        "for the compiler). `UNCHECKED` means the kernel ran but has no numeric golden yet.",
        "",
        "| Kernel | Compiled | Handwritten | Packets executed (C / HW) | Ratio "
        "| Instructions (C / HW) | Slot util (C / HW) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in kernel:
        hw = r.get("handwritten")
        hw_status = STATUS_LABEL[hw["status"]] if hw else "n/a"
        c_pk = perf_value(r, "packets_executed")
        h_pk = perf_value(hw, "packets_executed")
        # Efficiency is only comparable when both versions are verified correct.
        both_pass = r["status"] == "pass" and hw is not None and hw["status"] == "pass"
        ratio = fmt_ratio(c_pk, h_pk) if both_pass else "n/a"
        lines.append(
            f"| `{r['test']}` | {STATUS_LABEL[r['status']]} | {hw_status} "
            f"| {fmt_int(c_pk)} / {fmt_int(h_pk)} | {ratio} "
            f"| {fmt_int(perf_value(r, 'instructions_executed'))} / "
            f"{fmt_int(perf_value(hw, 'instructions_executed'))} "
            f"| {fmt_pct(perf_value(r, 'packet_slot_utilization_executed_pct'))} / "
            f"{fmt_pct(perf_value(hw, 'packet_slot_utilization_executed_pct'))} |"
        )

    lines += [
        "",
        "## Unit tests",
        "",
        "| Test | Status | Packets executed | Instructions |",
        "|---|---|---|---|",
    ]
    for r in unit:
        lines.append(
            f"| `{r['test']}` | {STATUS_LABEL[r['status']]} "
            f"| {fmt_int(perf_value(r, 'packets_executed'))} "
            f"| {fmt_int(perf_value(r, 'instructions_executed'))} |"
        )

    problems = [(r["test"], "compiled", r["error"]) for r in unit + kernel if r["error"]]
    problems += [
        (r["test"], "handwritten", r["handwritten"]["error"])
        for r in kernel
        if r.get("handwritten", {}).get("error")
    ]
    if problems:
        lines += ["", "## Errors", ""]
        for test, kind, error in problems:
            lines += [
                f"<details><summary><code>{test}</code> ({kind}): {first_line(error)}</summary>",
                "",
                "```",
                error.strip(),
                "```",
                "</details>",
            ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unit", type=Path, help="JSON from test_validation/run_all_validation.py")
    ap.add_argument(
        "--kernel", type=Path, help="JSON from test_validation_kernels/run_kernel_validation.py"
    )
    ap.add_argument("--out", type=Path, required=True, help="Markdown report path")
    args = ap.parse_args()

    report = render(load(args.unit), load(args.kernel))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
