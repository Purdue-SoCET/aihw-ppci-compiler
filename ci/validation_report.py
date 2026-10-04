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

STATUS_LABEL = {
    "pass": "PASS",
    "fail": "FAIL",
    "xfail": "KNOWN BUG",  # fails its golden because of a listed compiler bug
    "xpass": "FIXED?",  # listed as a known bug but passes now
}


def load(path: Path | None) -> list[dict]:
    if path is None or not path.exists():
        return []
    return json.loads(path.read_text())["results"]


def perf_value(result: dict | None, key: str) -> float | None:
    if not result or not result.get("perf"):
        return None
    return result["perf"].get(key)


def stack_value(result: dict | None, key: str) -> int | None:
    if not result or not result.get("stack"):
        return None
    return result["stack"].get(key)


def fmt_int(value: float | None) -> str:
    return "-" if value is None else f"{int(value):,}"


def fmt_pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}%"


def fmt_float(value: float | None, precision: int = 1) -> str:
    return "-" if value is None else f"{value:.{precision}f}"


def fmt_diff(current: float | None, baseline: float | None, unit: str = "", invert: bool = False) -> str:
    """Format difference between current and baseline.
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
    tag = "[IMPROVED]" if is_better else "[REGRESSED]"

    if abs(pct) >= 0.1:
        return f"{sign}{int(diff):,}{unit} ({sign}{pct:.1f}%) {tag}"
    else:
        return f"{sign}{int(diff):,}{unit} {tag}"


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


def render_baseline_comparison(current: list[dict], baseline: list[dict]) -> list[str]:
    if not baseline:
        return []

    base_map = {r["test"]: r for r in baseline}
    lines = [
        "",
        "---",
        "",
        "## 2. Commit Delta & Improvements (vs Previous Commit)",
        "",
        "Comparison of compilation and performance metrics against the previous commit or baseline branch.",
        "",
        "| Kernel | Status (Prev -> Now) | Cycles (Prev -> Now) | Cycle Delta | Scalar Mem (Prev -> Now) | Mem Delta | Stack Spills (Prev -> Now) |",
        "|---|---|---|---|---|---|---|",
    ]

    total_curr_cycles = 0
    total_base_cycles = 0
    total_curr_mem = 0
    total_base_mem = 0
    total_curr_spills = 0
    total_base_spills = 0
    count_compared = 0
    improved_count = 0
    regressed_count = 0

    for r in current:
        test = r["test"]
        base = base_map.get(test)
        if not base:
            continue

        c_pk = perf_value(r, "packets_executed")
        b_pk = perf_value(base, "packets_executed")

        c_sm = perf_value(r, "dyn_retired_scalar_mem")
        b_sm = perf_value(base, "dyn_retired_scalar_mem")

        c_spills = stack_value(r, "loop_spills")
        b_spills = stack_value(base, "loop_spills")

        status_str = f"{STATUS_LABEL.get(base.get('status', 'n/a'), base.get('status', 'n/a'))} -> {STATUS_LABEL.get(r['status'], r['status'])}"

        cycle_str = f"{fmt_int(b_pk)} -> {fmt_int(c_pk)}"
        cycle_delta = fmt_diff(c_pk, b_pk)

        mem_str = f"{fmt_int(b_sm)} -> {fmt_int(c_sm)}"
        mem_delta = fmt_diff(c_sm, b_sm, unit=" ops")

        spill_str = f"{fmt_spills(b_spills)} -> {fmt_spills(c_spills)}"

        lines.append(
            f"| `{test}` | {status_str} | {cycle_str} | {cycle_delta} | {mem_str} | {mem_delta} | {spill_str} |"
        )

        if c_pk is not None and b_pk is not None:
            total_curr_cycles += c_pk
            total_base_cycles += b_pk
            count_compared += 1
            if c_pk < b_pk:
                improved_count += 1
            elif c_pk > b_pk:
                regressed_count += 1

        if c_sm is not None and b_sm is not None:
            total_curr_mem += c_sm
            total_base_mem += b_sm

        if c_spills is not None and b_spills is not None:
            total_curr_spills += c_spills
            total_base_spills += b_spills

    if count_compared > 0:
        lines += [
            "",
            "### Summary of Changes Across Suite:",
            f"- **Kernels Faster:** {improved_count} | **Kernels Regressed:** {regressed_count} | **Unchanged:** {count_compared - improved_count - regressed_count}",
            f"- **Total Suite Cycles:** {fmt_int(total_base_cycles)} -> {fmt_int(total_curr_cycles)} ({fmt_diff(total_curr_cycles, total_base_cycles)})",
            f"- **Total Dynamic Scalar Memory:** {fmt_int(total_base_mem)} -> {fmt_int(total_curr_mem)} ({fmt_diff(total_curr_mem, total_base_mem, unit=' ops')})",
            f"- **Total Stack Loop Spills:** {fmt_int(total_base_spills)} -> {fmt_int(total_curr_spills)} ({fmt_diff(total_curr_spills, total_base_spills, unit=' spills')})",
        ]

    return lines


def render(unit: list[dict], kernel: list[dict], baseline: list[dict] | None = None) -> str:
    lines: list[str] = ["# Compiler Validation & Performance Report", ""]
    ref = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME")
    sha = os.environ.get("GITHUB_SHA", "")[:8]
    if ref or sha:
        lines += [f"**Branch:** `{ref}` | **Commit:** `{sha}`", ""]

    failed = [r for r in unit + kernel if r["status"] == "fail"]
    if not (unit or kernel):
        verdict = "### Accuracy Gate: FAILED (no results found)"
    elif failed:
        verdict = "### Accuracy Gate: FAILED"
    else:
        verdict = "### Accuracy Gate: PASSED"
    lines += [
        verdict,
        "",
        f"- **Unit Tests:** {counts(unit)}",
        f"- **Compiled Kernels:** {counts(kernel)}",
        f"- **Handwritten References:** {counts([r['handwritten'] for r in kernel if 'handwritten' in r])}",
        "",
        "---",
        "",
        "## 1. Executive Performance & VLIW Efficiency",
        "",
        "Every kernel is validated against a NumPy golden model. The handwritten version runs on the identical seeded memory layout. "
        "**Cycles / Packets Ratio** = $\\text{Compiled} / \\text{Handwritten}$ (lower is better; `< 1.00x` indicates the compiled C code outperforms handwritten assembly).",
        "",
        "| Kernel | Compiled | HW Ref | Cycles / Packets (C / HW) | Ratio (Speedup / Overhead) | Slot Density (C / HW) | Scalar Mem Ops (C / HW) | Stack Loop Spills |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in kernel:
        hw = r.get("handwritten")
        hw_status = STATUS_LABEL[hw["status"]] if hw else "n/a"
        c_pk = perf_value(r, "packets_executed")
        h_pk = perf_value(hw, "packets_executed")
        both_pass = r["status"] == "pass" and hw is not None and hw["status"] == "pass"
        ratio = fmt_ratio(c_pk, h_pk) if both_pass else "n/a"

        c_util = perf_value(r, "packet_slot_utilization_executed_pct")
        h_util = perf_value(hw, "packet_slot_utilization_executed_pct")
        slot_util = f"{fmt_pct(c_util)} / {fmt_pct(h_util)}"

        c_sm = perf_value(r, "dyn_retired_scalar_mem")
        h_sm = perf_value(hw, "dyn_retired_scalar_mem")
        sm_ops = f"{fmt_int(c_sm)} / {fmt_int(h_sm)}"

        spills = stack_value(r, "loop_spills")

        lines.append(
            f"| `{r['test']}` | {STATUS_LABEL[r['status']]} | {hw_status} "
            f"| {fmt_int(c_pk)} / {fmt_int(h_pk)} | {ratio} "
            f"| {slot_util} | {sm_ops} | {fmt_spills(spills)} |"
        )

    if baseline:
        lines += render_baseline_comparison(kernel, baseline)

    sec_num = 3 if baseline else 2

    lines += [
        "",
        "---",
        "",
        f"## {sec_num}. Memory Traffic & Bandwidth Analysis",
        "",
        "Monitors dynamic memory traffic (scratchpad / DRAM / scalar register accesses). Zero stack spills and low dynamic scalar memory instructions indicate optimal register allocation without memory thrashing.",
        "",
        "| Kernel | Dyn Scalar Mem | Dyn Vector Mem | SDMA Ops | Data Moved (Bytes) | Arithmetic Intensity (FLOP/B) |",
        "|---|---|---|---|---|---|",
    ]

    for r in kernel:
        sm = perf_value(r, "dyn_retired_scalar_mem")
        vm = perf_value(r, "dyn_retired_vector_mem")
        sdma = perf_value(r, "dyn_retired_sdma")
        bytes_moved = perf_value(r, "bytes_moved")
        ai = perf_value(r, "arithmetic_intensity")

        lines.append(
            f"| `{r['test']}` | {fmt_int(sm)} | {fmt_int(vm)} | {fmt_int(sdma)} "
            f"| {fmt_int(bytes_moved)} B | {fmt_float(ai, 1)} |"
        )

    sec_num += 1
    lines += [
        "",
        "---",
        "",
        "<details>",
        f"<summary><b>{sec_num}. Detailed Dynamic Instruction Breakdown (Click to Expand)</b></summary>",
        "",
        "Dynamic counts of hardware instructions retired by functional unit execution category:",
        "",
        "| Kernel | Total Instr (C / HW) | Scalar ALU (C / HW) | Scalar Mem (C / HW) | Vector ALU (C / HW) | Vector Mem (C / HW) | GEMM Systolic (C / HW) | Branch/Ctrl (C / HW) |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in kernel:
        hw = r.get("handwritten")
        c_tot = perf_value(r, "instructions_executed")
        h_tot = perf_value(hw, "instructions_executed")
        c_salu = perf_value(r, "dyn_retired_scalar_alu")
        h_salu = perf_value(hw, "dyn_retired_scalar_alu")
        c_sm = perf_value(r, "dyn_retired_scalar_mem")
        h_sm = perf_value(hw, "dyn_retired_scalar_mem")
        c_valu = perf_value(r, "dyn_retired_vector_alu")
        h_valu = perf_value(hw, "dyn_retired_vector_alu")
        c_vmem = perf_value(r, "dyn_retired_vector_mem")
        h_vmem = perf_value(hw, "dyn_retired_vector_mem")
        c_gemm = perf_value(r, "dyn_retired_gemm_systolic")
        h_gemm = perf_value(hw, "dyn_retired_gemm_systolic")
        c_br = perf_value(r, "dyn_retired_branch_control")
        h_br = perf_value(hw, "dyn_retired_branch_control")

        lines.append(
            f"| `{r['test']}` | {fmt_int(c_tot)} / {fmt_int(h_tot)} "
            f"| {fmt_int(c_salu)} / {fmt_int(h_salu)} "
            f"| {fmt_int(c_sm)} / {fmt_int(h_sm)} "
            f"| {fmt_int(c_valu)} / {fmt_int(h_valu)} "
            f"| {fmt_int(c_vmem)} / {fmt_int(h_vmem)} "
            f"| {fmt_int(c_gemm)} / {fmt_int(h_gemm)} "
            f"| {fmt_int(c_br)} / {fmt_int(h_br)} |"
        )

    sec_num += 1
    lines += [
        "",
        "</details>",
        "",
        "---",
        "",
        f"## {sec_num}. Unit Feature Tests",
        "",
        "| Test | Status | Packets Executed | Total Instructions |",
        "|---|---|---|---|",
    ]
    for r in unit:
        lines.append(
            f"| `{r['test']}` | {STATUS_LABEL[r['status']]} "
            f"| {fmt_int(perf_value(r, 'packets_executed'))} "
            f"| {fmt_int(perf_value(r, 'instructions_executed'))} |"
        )

    known = [r for r in kernel if r.get("known_bug")]
    if known:
        sec_num += 1
        lines += ["", "---", "", f"## {sec_num}. Known Compiler Bugs", "", "| Kernel | Status | Root Cause / Note |", "|---|---|---|"]
        for r in known:
            lines.append(f"| `{r['test']}` | {STATUS_LABEL[r['status']]} | {r['known_bug']} |")

    problems = [(r["test"], "compiled", r["error"]) for r in unit + kernel if r["error"]]
    problems += [
        (r["test"], "handwritten", r["handwritten"]["error"])
        for r in kernel
        if r.get("handwritten", {}).get("error")
    ]
    if problems:
        sec_num += 1
        lines += ["", "---", "", f"## {sec_num}. Error Diagnostic Traces", ""]
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
    ap.add_argument(
        "--baseline", type=Path, help="Optional previous JSON to compare against for deltas/improvements"
    )
    ap.add_argument("--out", type=Path, required=True, help="Markdown report path")
    args = ap.parse_args()

    baseline_path = args.baseline
    if baseline_path is None:
        default_baseline = Path("validation_results/previous.json")
        if default_baseline.exists():
            baseline_path = default_baseline

    baseline_results = load(baseline_path) if baseline_path else None

    report = render(load(args.unit), load(args.kernel), baseline_results)
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
