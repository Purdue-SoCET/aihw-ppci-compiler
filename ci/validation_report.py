#!/usr/bin/env python3
"""Render validation results (``--json`` output of the two runners) as Markdown.

Writes the report to ``--out`` and, when running in GitHub Actions, appends it to
the job summary. This script only reports; the runners' exit codes are the gate.
Also optionally exports a comprehensive kernel metrics CSV (matching
``functional_sim/collect_kernel_metrics.py``) via ``--csv``.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

STATUS_LABEL = {
    "pass": "PASS",
    "fail": "FAIL",
    "xfail": "KNOWN BUG",  # fails its golden because of a listed compiler bug
    "xpass": "FIXED?",  # listed as a known bug but passes now
}

# Mirror functional_sim/collect_kernel_metrics.py retired buckets
_RETIRED_BUCKET_NAMES: tuple[str, ...] = (
    "branch_control",
    "sdma",
    "scalar_mem",
    "scalar_alu",
    "vector_mem",
    "vector_alu",
    "gemm_systolic",
    "move_convert",
)

CSV_FIELDS = [
    "Kernel",
    "FLOPs (total)",
    "FLOPs matmul",
    "Static slots filled (non-NOP)",
    "Bytes Loaded",
    "Bytes Loaded SP0",
    "Bytes Loaded SP1",
    "Bytes Written",
    "Bytes Stored SP0",
    "Bytes Stored SP1",
    "Static packet rows",
    "Slots",
    "Packet Slot Util. %",
    "Packets executed",
    "Ops executed (dynamic)",
    *[f"dyn_retired_{n}" for n in _RETIRED_BUCKET_NAMES],
    *[f"pct_dyn_retired_{n}" for n in _RETIRED_BUCKET_NAMES],
    "Arithmetic Intensity",
    "AI (load+store)",
]


def get_local_git_info() -> dict[str, str]:
    info = {"commit": "", "branch": "", "message": ""}
    try:
        import subprocess
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        msg = subprocess.check_output(
            ["git", "log", "-1", "--format=%s"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        info = {"commit": commit, "branch": branch, "message": msg}
    except Exception:
        pass
    return info


def load_payload(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {"git": {}, "results": []}
    try:
        content = json.loads(path.read_text())
        if isinstance(content, dict):
            return {
                "git": content.get("git", {}),
                "results": content.get("results", []),
            }
        elif isinstance(content, list):
            return {"git": {}, "results": content}
    except Exception:
        pass
    return {"git": {}, "results": []}


def load(path: Path | None) -> list[dict]:
    return load_payload(path)["results"]


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
    tag = "[IMPROVED]" if is_better else "[REGRESSED]"

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


def render_baseline_comparison(
    current: list[dict],
    baseline: list[dict],
    current_git: dict | None = None,
    baseline_git: dict | None = None,
) -> list[str]:
    if not baseline:
        return []

    base_map = {r["test"]: r for r in baseline}
    c_g = current_git or {}
    b_g = baseline_git or {}

    lines = [
        "",
        "---",
        "",
        "## 2. Commit Delta & Improvements (vs Previous Commit)",
        "",
    ]

    base_desc = []
    if b_g.get("commit"):
        br = f"`{b_g['branch']}` @ " if b_g.get("branch") else ""
        msg = f" (*{b_g['message']}*)" if b_g.get("message") else ""
        base_desc.append(f"**Baseline:** {br}`{b_g['commit']}`{msg}")
    if c_g.get("commit"):
        br = f"`{c_g['branch']}` @ " if c_g.get("branch") else ""
        msg = f" (*{c_g['message']}*)" if c_g.get("message") else ""
        base_desc.append(f"**Current:** {br}`{c_g['commit']}`{msg}")

    if base_desc:
        lines.append("Comparing compilation and performance metrics against baseline:")
        for d in base_desc:
            lines.append(f"- {d}")
        lines.append("")
    else:
        lines += [
            "Comparison of compilation and performance metrics against the previous commit or baseline branch.",
            "",
        ]

    lines += [
        "| Kernel | Status (Prev -> Now) | Cycles (Prev -> Now) | Cycle Delta | Ops Retired (Prev -> Now) | Ops Delta | VLIW Density (Prev -> Now) | Scalar Mem (Prev -> Now) | Mem Delta | Stack Spills (Prev -> Now) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    total_curr_cycles = 0
    total_base_cycles = 0
    total_curr_ops = 0
    total_base_ops = 0
    total_curr_mem = 0
    total_base_mem = 0
    total_curr_spills = 0
    total_base_spills = 0
    curr_densities = []
    base_densities = []
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

        c_ops = perf_value(r, "instructions_executed")
        b_ops = perf_value(base, "instructions_executed")

        c_den = perf_value(r, "packet_slot_utilization_executed_pct")
        b_den = perf_value(base, "packet_slot_utilization_executed_pct")

        c_sm = perf_value(r, "dyn_retired_scalar_mem")
        b_sm = perf_value(base, "dyn_retired_scalar_mem")

        c_spills = stack_value(r, "loop_spills")
        b_spills = stack_value(base, "loop_spills")

        status_str = f"{STATUS_LABEL.get(base.get('status', 'n/a'), base.get('status', 'n/a'))} -> {STATUS_LABEL.get(r['status'], r['status'])}"

        cycle_str = f"{fmt_int(b_pk)} -> {fmt_int(c_pk)}"
        cycle_delta = fmt_diff(c_pk, b_pk)

        ops_str = f"{fmt_int(b_ops)} -> {fmt_int(c_ops)}"
        ops_delta = fmt_diff(c_ops, b_ops, unit=" ops")

        den_str = f"{fmt_pct(b_den)} -> {fmt_pct(c_den)}"

        mem_str = f"{fmt_int(b_sm)} -> {fmt_int(c_sm)}"
        mem_delta = fmt_diff(c_sm, b_sm, unit=" ops")

        spill_str = f"{fmt_spills(b_spills)} -> {fmt_spills(c_spills)}"

        lines.append(
            f"| `{test}` | {status_str} | {cycle_str} | {cycle_delta} | {ops_str} | {ops_delta} | {den_str} | {mem_str} | {mem_delta} | {spill_str} |"
        )

        if c_pk is not None and b_pk is not None:
            total_curr_cycles += c_pk
            total_base_cycles += b_pk
            count_compared += 1
            if c_pk < b_pk:
                improved_count += 1
            elif c_pk > b_pk:
                regressed_count += 1

        if c_ops is not None and b_ops is not None:
            total_curr_ops += c_ops
            total_base_ops += b_ops

        if c_den is not None and b_den is not None:
            curr_densities.append(c_den)
            base_densities.append(b_den)

        if c_sm is not None and b_sm is not None:
            total_curr_mem += c_sm
            total_base_mem += b_sm

        if c_spills is not None and b_spills is not None:
            total_curr_spills += c_spills
            total_base_spills += b_spills

    if count_compared > 0:
        avg_base_den = (sum(base_densities) / len(base_densities)) if base_densities else None
        avg_curr_den = (sum(curr_densities) / len(curr_densities)) if curr_densities else None
        den_summary = f"{fmt_pct(avg_base_den)} -> {fmt_pct(avg_curr_den)} ({fmt_diff_pct(avg_curr_den, avg_base_den)})" if avg_base_den else "n/a"

        lines += [
            "",
            "### Summary of Changes Across Suite:",
            f"- **Kernels Faster:** {improved_count} | **Kernels Regressed:** {regressed_count} | **Unchanged:** {count_compared - improved_count - regressed_count}",
            f"- **Total Suite Cycles:** {fmt_int(total_base_cycles)} -> {fmt_int(total_curr_cycles)} ({fmt_diff(total_curr_cycles, total_base_cycles)})",
            f"- **Total Instructions Retired:** {fmt_int(total_base_ops)} -> {fmt_int(total_curr_ops)} ({fmt_diff(total_curr_ops, total_base_ops, unit=' ops')})",
            f"- **Mean VLIW Slot Density:** {den_summary}",
            f"- **Total Dynamic Scalar Memory:** {fmt_int(total_base_mem)} -> {fmt_int(total_curr_mem)} ({fmt_diff(total_curr_mem, total_base_mem, unit=' ops')})",
            f"- **Total Stack Loop Spills:** {fmt_int(total_base_spills)} -> {fmt_int(total_curr_spills)} ({fmt_diff(total_curr_spills, total_base_spills, unit=' spills')})",
        ]

    return lines


def render(
    unit: list[dict],
    kernel: list[dict],
    baseline: list[dict] | None = None,
    current_git: dict | None = None,
    baseline_git: dict | None = None,
) -> str:
    lines: list[str] = ["# Compiler Validation & Performance Report", ""]

    local_git = get_local_git_info()
    c_g = current_git or {}
    c_ref = c_g.get("branch") or os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or local_git.get("branch")
    c_sha = c_g.get("commit") or os.environ.get("GITHUB_SHA", "")[:8] or local_git.get("commit")
    c_msg = c_g.get("message") or local_git.get("message")

    b_g = baseline_git or {}
    b_ref = b_g.get("branch") or os.environ.get("GITHUB_BASE_REF")
    b_sha = b_g.get("commit")
    b_msg = b_g.get("message")

    header_parts = []
    if c_ref or c_sha:
        desc = f"**Current:** `{c_ref}` @ `{c_sha}`" if c_ref and c_sha else f"**Current:** `{c_ref or c_sha}`"
        if c_msg:
            desc += f" (*{c_msg}*)"
        header_parts.append(desc)
    if b_ref or b_sha:
        desc = f"**Baseline:** `{b_ref}` @ `{b_sha}`" if b_ref and b_sha else f"**Baseline:** `{b_ref or b_sha}`"
        if b_msg:
            desc += f" (*{b_msg}*)"
        header_parts.append(desc)

    if header_parts:
        lines += [" | ".join(header_parts), ""]

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
        lines += render_baseline_comparison(kernel, baseline, current_git=c_g, baseline_git=b_g)

    sec_num = 3 if baseline else 2

    lines += [
        "",
        "---",
        "",
        f"## {sec_num}. Compute, Bandwidth & Roofline Analysis",
        "",
        "Metrics aligned with ``functional_sim/collect_kernel_metrics.py``:",
        "- **AI (Load):** $\\text{FLOPs}_{\\text{total}} / \\text{Bytes Loaded}$ (DMA read bytes only).",
        "- **AI (Load+Store):** $\\text{FLOPs}_{\\text{total}} / (\\text{Bytes Loaded} + \\text{Bytes Written})$ (full DRAM traffic roofline).",
        "- **SP0 / SP1:** Scratchpad bank breakdown (SP0≈activations, SP1≈weights/bias).",
        "",
        "| Kernel | Total FLOPs | Matmul FLOPs | Bytes Loaded (SP0 / SP1) | Bytes Written (SP0 / SP1) | AI (Load) | AI (Load+Store) | SDMA Ops |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in kernel:
        flops_tot = perf_value(r, "flops_total")
        flops_mm = perf_value(r, "flops_matmul")
        b_ld = perf_value(r, "bytes_loaded")
        b_ld_sp0 = perf_value(r, "bytes_loaded_sp0")
        b_ld_sp1 = perf_value(r, "bytes_loaded_sp1")
        b_wr = perf_value(r, "bytes_written")
        b_wr_sp0 = perf_value(r, "bytes_stored_sp0")
        b_wr_sp1 = perf_value(r, "bytes_stored_sp1")
        ai_ld = perf_value(r, "arithmetic_intensity_loads") or perf_value(r, "arithmetic_intensity")
        ai_ls = perf_value(r, "arithmetic_intensity_load_store")
        sdma = perf_value(r, "dyn_retired_sdma")

        ld_str = f"{fmt_int(b_ld)} B ({fmt_int(b_ld_sp0)} / {fmt_int(b_ld_sp1)})"
        wr_str = f"{fmt_int(b_wr)} B ({fmt_int(b_wr_sp0)} / {fmt_int(b_wr_sp1)})"

        lines.append(
            f"| `{r['test']}` | {fmt_int(flops_tot)} | {fmt_int(flops_mm)} | {ld_str} | {wr_str} | {fmt_float(ai_ld, 1)} | {fmt_float(ai_ls, 1)} | {fmt_int(sdma)} |"
        )

    sec_num += 1
    lines += [
        "",
        "---",
        "",
        f"## {sec_num}. Static Code Size & VLIW Packing Density",
        "",
        "Static image dimensions and instruction-level parallelism metrics:",
        "- **Static packet rows:** Number of 4-slot VLIW bundle rows scheduled in static memory.",
        "- **Static slots filled:** Non-NOP operations packed across static packet rows.",
        "- **Packets executed:** Dynamic packet fetch count (loop iterations and jumps scale this count).",
        "",
        "| Kernel | Static Rows | Slots (Filled / Total) | Static Slot Util % | Packets Executed | Dynamic Ops Retired | Dynamic Slot Util % |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in kernel:
        st_rows = perf_value(r, "packets_static_total")
        st_filled = perf_value(r, "packet_slots_filled")
        st_slots = perf_value(r, "packet_slots_total")
        st_util = perf_value(r, "packet_slot_utilization_pct")
        pk_exec = perf_value(r, "packets_executed")
        ops_exec = perf_value(r, "instructions_executed")
        dyn_util = perf_value(r, "packet_slot_utilization_executed_pct")

        slots_str = f"{fmt_int(st_filled)} / {fmt_int(st_slots)}"

        lines.append(
            f"| `{r['test']}` | {fmt_int(st_rows)} | {slots_str} | {fmt_pct(st_util)} | {fmt_int(pk_exec)} | {fmt_int(ops_exec)} | {fmt_pct(dyn_util)} |"
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
        pk = perf_value(r, "packets_executed")
        tot = perf_value(r, "instructions_executed")
        lines.append(
            f"| `{r['test']}` | {STATUS_LABEL[r['status']]} | {fmt_int(pk)} | {fmt_int(tot)} |"
        )

    known_bugs = [r for r in unit + kernel if r.get("known_bug")]
    if known_bugs:
        sec_num += 1
        lines += [
            "",
            "---",
            "",
            f"## {sec_num}. Known Compiler Bugs",
            "",
            "| Kernel | Status | Root Cause / Note |",
            "|---|---|---|",
        ]
        for r in known_bugs:
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


def export_csv(kernel: list[dict], csv_path: Path) -> None:
    """Export complete kernel metrics table matching collect_kernel_metrics.py."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_FIELDS)
        for r in kernel:
            p = r.get("perf") or {}
            dyn_tot = p.get("instructions_executed") or 0.0
            row = [
                r["test"],
                int(p.get("flops_total", 0)),
                int(p.get("flops_matmul", 0)),
                int(p.get("packet_slots_filled", 0)),
                int(p.get("bytes_loaded", 0)),
                int(p.get("bytes_loaded_sp0", 0)),
                int(p.get("bytes_loaded_sp1", 0)),
                int(p.get("bytes_written", 0)),
                int(p.get("bytes_stored_sp0", 0)),
                int(p.get("bytes_stored_sp1", 0)),
                int(p.get("packets_static_total", 0)),
                int(p.get("packet_slots_total", 0)),
                round(p.get("packet_slot_utilization_pct", 0.0), 2),
                int(p.get("packets_executed", 0)),
                int(dyn_tot),
            ]
            for n in _RETIRED_BUCKET_NAMES:
                row.append(int(p.get(f"dyn_retired_{n}", 0)))
            for n in _RETIRED_BUCKET_NAMES:
                val = p.get(f"dyn_retired_{n}", 0)
                pct = (val / dyn_tot * 100.0) if dyn_tot > 0 else 0.0
                row.append(round(pct, 2))
            ai_ld = p.get("arithmetic_intensity_loads", p.get("arithmetic_intensity", 0.0))
            ai_ls = p.get("arithmetic_intensity_load_store", 0.0)
            row.append(round(ai_ld, 2))
            row.append(round(ai_ls, 2))
            writer.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unit", type=Path, help="JSON from test_validation/run_all_validation.py")
    ap.add_argument(
        "--kernel", type=Path, help="JSON from test_validation_kernels/run_kernel_validation.py"
    )
    ap.add_argument(
        "--baseline", type=Path, help="Optional previous JSON to compare against for deltas/improvements"
    )
    ap.add_argument("--csv", type=Path, help="Optional path to output collect_kernel_metrics.py CSV")
    ap.add_argument("--out", type=Path, required=True, help="Markdown report path")
    args = ap.parse_args()

    baseline_path = args.baseline
    if baseline_path is None:
        default_baseline = Path("validation_results/previous.json")
        if default_baseline.exists():
            baseline_path = default_baseline

    baseline_payload = load_payload(baseline_path) if baseline_path else {"git": {}, "results": []}
    kernel_payload = load_payload(args.kernel)

    report = render(
        unit=load(args.unit),
        kernel=kernel_payload["results"],
        baseline=baseline_payload["results"] if baseline_path else None,
        current_git=kernel_payload.get("git"),
        baseline_git=baseline_payload.get("git"),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)

    if args.csv:
        export_csv(kernel_payload["results"], args.csv)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
