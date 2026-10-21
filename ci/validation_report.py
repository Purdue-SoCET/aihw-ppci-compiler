#!/usr/bin/env python3
"""Render validation results (``--json`` output of the two runners) as Markdown.

Writes the report to ``--out`` and, when running in GitHub Actions, appends it to
the job summary. This script only reports; the runners' exit codes are the gate.
Also optionally exports a comprehensive kernel metrics CSV (matching
``functional_sim/collect_kernel_metrics.py``) via ``--csv``.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

try:
    from ci.formatters import (
        STATUS_LABEL,
        counts,
        first_line,
        fmt_diff,
        fmt_diff_pct,
        fmt_float,
        fmt_int,
        fmt_pct,
        fmt_ratio,
        fmt_spills,
    )
    from ci.metrics import (
        CSV_FIELDS,
        _RETIRED_BUCKET_NAMES,
        export_csv,
        get_local_git_info,
        load,
        load_payload,
        perf_value,
        stack_value,
    )
    from ci.comparisons import (
        render_baseline_comparison,
        render_dual_baseline_comparison,
    )
except ImportError:
    from formatters import (
        STATUS_LABEL,
        counts,
        first_line,
        fmt_diff,
        fmt_diff_pct,
        fmt_float,
        fmt_int,
        fmt_pct,
        fmt_ratio,
        fmt_spills,
    )
    from metrics import (
        CSV_FIELDS,
        _RETIRED_BUCKET_NAMES,
        export_csv,
        get_local_git_info,
        load,
        load_payload,
        perf_value,
        stack_value,
    )
    from comparisons import (
        render_baseline_comparison,
        render_dual_baseline_comparison,
    )

# Re-exports for backward compatibility
__all__ = [
    "STATUS_LABEL",
    "CSV_FIELDS",
    "_RETIRED_BUCKET_NAMES",
    "fmt_int",
    "fmt_pct",
    "fmt_float",
    "fmt_diff",
    "fmt_diff_pct",
    "fmt_ratio",
    "fmt_spills",
    "counts",
    "first_line",
    "get_local_git_info",
    "load_payload",
    "load",
    "perf_value",
    "stack_value",
    "export_csv",
    "render_baseline_comparison",
    "render_dual_baseline_comparison",
    "render",
    "main",
]


def render(
    unit: list[dict],
    kernel: list[dict],
    baseline: list[dict] | None = None,
    current_git: dict | None = None,
    baseline_git: dict | None = None,
    macro_baseline: list[dict] | None = None,
    micro_baseline: list[dict] | None = None,
    macro_git: dict | None = None,
    micro_git: dict | None = None,
) -> str:
    lines: list[str] = ["# Compiler Validation & Performance Report", ""]

    local_git = get_local_git_info()
    c_g = current_git or {}
    c_ref = c_g.get("branch") or os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or local_git.get("branch")
    c_sha = c_g.get("commit") or os.environ.get("GITHUB_SHA", "")[:8] or local_git.get("commit")
    c_msg = c_g.get("message") or local_git.get("message")

    header_parts = []
    if c_ref or c_sha:
        desc = f"**Current:** `{c_ref}` @ `{c_sha}`" if c_ref and c_sha else f"**Current:** `{c_ref or c_sha}`"
        if c_msg:
            desc += f" (*{c_msg}*)"
        header_parts.append(desc)

    mac_g = macro_git or {}
    mic_g = micro_git or {}
    b_g = baseline_git or {}

    if macro_baseline:
        m_ref = mac_g.get("branch") or "atalla-arch"
        m_sha = mac_g.get("commit")
        m_msg = mac_g.get("message")
        desc = f"**Macro Baseline:** `{m_ref}` @ `{m_sha}`" if m_sha else f"**Macro Baseline:** `{m_ref}`"
        if m_msg:
            desc += f" (*{m_msg}*)"
        header_parts.append(desc)

    if mic_g.get("commit") or mic_g.get("branch"):
        mi_ref = mic_g.get("branch")
        mi_sha = mic_g.get("commit")
        mi_msg = mic_g.get("message")
        desc = f"**Micro Baseline:** `{mi_ref}` @ `{mi_sha}`" if mi_ref and mi_sha else f"**Micro Baseline:** `{mi_sha or mi_ref}`"
        if mi_msg:
            desc += f" (*{mi_msg}*)"
        header_parts.append(desc)

    if not mac_g and not mic_g and (b_g.get("commit") or b_g.get("branch")):
        b_ref = b_g.get("branch") or os.environ.get("GITHUB_BASE_REF")
        b_sha = b_g.get("commit")
        b_msg = b_g.get("message")
        desc = f"**Baseline:** `{b_ref}` @ `{b_sha}`" if b_ref and b_sha else f"**Baseline:** `{b_ref or b_sha}`"
        if b_msg:
            desc += f" (*{b_msg}*)"
        header_parts.append(desc)

    if header_parts:
        lines += [" | ".join(header_parts), ""]

    failed = [r for r in unit + kernel if r.get("status") == "fail"]
    failed += [
        r["handwritten"]
        for r in kernel
        if r.get("handwritten", {}).get("status") == "fail"
    ]
    missing = [name for name, res in (("unit", unit), ("kernel", kernel)) if not res]
    if missing:
        verdict = (
            f"**Accuracy gate: FAILED** (no {' or '.join(missing)} results; "
            "the suite did not run, see the job log)"
        )
    elif failed:
        verdict = "### Accuracy gate: FAILED"
    else:
        verdict = "### Accuracy gate: PASSED"
    lines += [
        verdict,
        "",
    ]

    total_spills = sum(stack_value(r, "loop_spills") or 0 for r in kernel)
    if total_spills > 0:
        lines += [
            "> [!WARNING]",
            f"> **Stack Spilling Detected:** {total_spills} spill(s) found in core compute loops!",
            "> Core compute loops must maintain zero stack memory traffic.",
            "",
        ]

    eval_macro = macro_baseline if macro_baseline is not None else baseline
    if eval_macro:
        macro_map = {r["test"]: r for r in eval_macro}
        tot_curr = 0
        tot_macro = 0
        for r in kernel:
            base = macro_map.get(r["test"])
            if not base:
                continue
            c_pk = perf_value(r, "packets_executed")
            b_pk = perf_value(base, "packets_executed")
            if c_pk is not None and b_pk is not None:
                tot_curr += c_pk
                tot_macro += b_pk
        if tot_macro > 0:
            diff_cyc = tot_curr - tot_macro
            pct_cyc = (diff_cyc / tot_macro) * 100.0
            if pct_cyc > 3.0:
                ref_name = mac_g.get("branch") or b_g.get("branch") or "atalla-arch"
                lines += [
                    "> [!WARNING]",
                    f"> **Performance Regression Detected:** Total suite cycles regressed by +{pct_cyc:.1f}% ({diff_cyc:+,} cycles) vs {ref_name}!",
                    "",
                ]

    lines += [
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
        both_pass = r.get("status") == "pass" and hw is not None and hw.get("status") == "pass"
        ratio = fmt_ratio(c_pk, h_pk) if both_pass else "n/a"

        c_util = perf_value(r, "packet_slot_utilization_executed_pct")
        h_util = perf_value(hw, "packet_slot_utilization_executed_pct")
        slot_util = f"{fmt_pct(c_util)} / {fmt_pct(h_util)}"

        c_sm = perf_value(r, "dyn_retired_scalar_mem")
        h_sm = perf_value(hw, "dyn_retired_scalar_mem")
        sm_ops = f"{fmt_int(c_sm)} / {fmt_int(h_sm)}"

        spills = stack_value(r, "loop_spills")

        st_label = STATUS_LABEL.get(r.get("status", "n/a"), r.get("status", "n/a"))
        lines.append(
            f"| `{r['test']}` | {st_label} | {hw_status} "
            f"| {fmt_int(c_pk)} / {fmt_int(h_pk)} | {ratio} "
            f"| {slot_util} | {sm_ops} | {fmt_spills(spills)} |"
        )

    has_dual = bool(macro_baseline and micro_baseline)
    has_macro = bool(macro_baseline)
    has_micro = bool(micro_baseline)
    has_baseline = bool(baseline)

    if has_dual:
        lines += render_dual_baseline_comparison(
            kernel,
            macro_baseline=macro_baseline,
            micro_baseline=micro_baseline,
            current_git=c_g,
            macro_git=mac_g,
            micro_git=mic_g,
        )
    elif has_macro:
        lines += render_baseline_comparison(
            kernel, macro_baseline, current_git=c_g, baseline_git=mac_g or b_g, baseline_title="atalla-arch"
        )
    elif has_micro:
        lines += render_baseline_comparison(
            kernel, micro_baseline, current_git=c_g, baseline_git=mic_g or b_g, baseline_title="Last Commit"
        )
    elif has_baseline:
        lines += render_baseline_comparison(
            kernel, baseline, current_git=c_g, baseline_git=b_g
        )

    sec_num = 3 if (has_dual or has_macro or has_micro or has_baseline) else 2

    lines += [
        "",
        "---",
        "",
        "## Static packetization",
        "",
        "Instructions are counted before scheduling, excluding NOPs and directives. "
        "Packet totals include latency stalls and exclude simulator bootstrap packets (main and halt). "
        "These static counts are separate from loop-dependent execution counts above.",
        "Branch-expansion instructions are counted separately from the original instructions; "
        "packet totals include their packets.",
        "",
        "| Kernel | Instructions before packetization (C / HW) | Packets (C / HW) "
        "| All-NOP packets (C / HW) | Branch-expansion instructions (C / HW) |",
        "|---|---|---|---|---|",
    ]
    for result in kernel:
        hw = result.get("handwritten")
        values = [
            f"{fmt_int(perf_value(result, key))} / {fmt_int(perf_value(hw, key))}"
            for key in ("instructions_before_packetization", "packets_before_encoding", "nop_packets",
                        "branch_lowering_instructions")
        ]
        lines.append(f"| `{result['test']}` | " + " | ".join(values) + " |")

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

    macro_map_sec3 = {r["test"]: r for r in eval_macro} if eval_macro else {}
    total_curr_dram = 0
    total_macro_dram = 0
    total_curr_sdma = 0
    total_macro_sdma = 0

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

        base_r = macro_map_sec3.get(r["test"])
        mac_ld = perf_value(base_r, "bytes_loaded") if base_r else None
        mac_wr = perf_value(base_r, "bytes_written") if base_r else None
        mac_sdma = perf_value(base_r, "dyn_retired_sdma") if base_r else None

        if mac_ld is not None and b_ld is not None and mac_ld != b_ld:
            ld_str = f"{fmt_int(mac_ld)} -> {fmt_int(b_ld)} B ({fmt_diff(b_ld, mac_ld, unit=' B')})"
        else:
            ld_str = f"{fmt_int(b_ld)} B ({fmt_int(b_ld_sp0)} / {fmt_int(b_ld_sp1)})"

        if mac_wr is not None and b_wr is not None and mac_wr != b_wr:
            wr_str = f"{fmt_int(mac_wr)} -> {fmt_int(b_wr)} B ({fmt_diff(b_wr, mac_wr, unit=' B')})"
        else:
            wr_str = f"{fmt_int(b_wr)} B ({fmt_int(b_wr_sp0)} / {fmt_int(b_wr_sp1)})"

        if mac_sdma is not None and sdma is not None:
            if mac_sdma != sdma:
                sdma_str = f"{fmt_int(mac_sdma)} -> {fmt_int(sdma)} ({fmt_diff(sdma, mac_sdma, unit=' ops')})"
            else:
                sdma_str = fmt_int(sdma)
        else:
            sdma_str = fmt_int(sdma)

        if b_ld is not None and b_wr is not None:
            total_curr_dram += (b_ld + b_wr)
        if mac_ld is not None and mac_wr is not None:
            total_macro_dram += (mac_ld + mac_wr)
        if sdma is not None:
            total_curr_sdma += sdma
        if mac_sdma is not None:
            total_macro_sdma += mac_sdma

        lines.append(
            f"| `{r['test']}` | {fmt_int(flops_tot)} | {fmt_int(flops_mm)} | {ld_str} | {wr_str} | {fmt_float(ai_ld, 1)} | {fmt_float(ai_ls, 1)} | {sdma_str} |"
        )

    if total_macro_dram > 0:
        ref_title = mac_g.get("branch") or b_g.get("branch") or "atalla-arch"
        lines += [
            "",
            f"### DRAM Traffic & Transfer Summary vs {ref_title}:",
            f"- **Total DRAM Bandwidth (Loaded + Written):** {fmt_int(total_macro_dram)} B -> {fmt_int(total_curr_dram)} B ({fmt_diff(total_curr_dram, total_macro_dram, unit=' B')})",
            f"- **Total SDMA Transfers:** {fmt_int(total_macro_sdma)} -> {fmt_int(total_curr_sdma)} ({fmt_diff(total_curr_sdma, total_macro_sdma, unit=' ops')})",
        ]

    sec_num += 1
    lines += [
        "",
        "---",
        "",
        f"## {sec_num}. Static Code Size & VLIW Image Dimensions",
        "",
        "Static image dimensions and VLIW slot layout in static memory:",
        "- **Static packet rows:** Number of 4-slot VLIW bundle rows scheduled in static memory.",
        "- **Static slots filled:** Non-NOP operations packed across static packet rows.",
        "- **Static slot utilization:** Percentage of non-NOP slots filled in static memory.",
        "",
        "| Kernel | Static Rows | Slots (Filled / Total) | Static Slot Util % |",
        "|---|---|---|---|",
    ]

    for r in kernel:
        st_rows = perf_value(r, "packets_static_total")
        st_filled = perf_value(r, "packet_slots_filled")
        st_slots = perf_value(r, "packet_slots_total")
        st_util = perf_value(r, "packet_slot_utilization_pct")

        slots_str = f"{fmt_int(st_filled)} / {fmt_int(st_slots)}"

        lines.append(
            f"| `{r['test']}` | {fmt_int(st_rows)} | {slots_str} | {fmt_pct(st_util)} |"
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
    ]
    if unit:
        lines += [
            "| Test | Status | Packets Executed | Total Instructions |",
            "|---|---|---|---|",
        ]
        for r in unit:
            pk = perf_value(r, "packets_executed")
            tot = perf_value(r, "instructions_executed")
            lines.append(
                f"| `{r['test']}` | {STATUS_LABEL[r['status']]} | {fmt_int(pk)} | {fmt_int(tot)} |"
            )
    else:
        lines += [
            "*Unit feature tests were not run in this execution (run `./run_test.sh --unit` or `./run_test.sh --all`).*",
        ]

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

    problems = [(r["test"], "compiled", r.get("error")) for r in unit + kernel if r.get("error")]
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
    ap.add_argument(
        "--macro-baseline", type=Path, help="Macro baseline JSON (e.g. atalla-arch)"
    )
    ap.add_argument(
        "--micro-baseline", type=Path, help="Micro baseline JSON (e.g. previous commit)"
    )
    ap.add_argument("--csv", type=Path, help="Optional path to output collect_kernel_metrics.py CSV")
    ap.add_argument("--out", type=Path, required=True, help="Markdown report path")
    args = ap.parse_args()

    unit_path = args.unit
    if unit_path is None:
        default_unit = Path("validation_results/unit.json")
        if default_unit.exists():
            unit_path = default_unit
        elif args.kernel:
            candidate = args.kernel.parent / "unit.json"
            if candidate.exists():
                unit_path = candidate

    macro_path = args.macro_baseline
    micro_path = args.micro_baseline
    baseline_path = args.baseline

    if macro_path is None and micro_path is None and baseline_path is None:
        default_baseline = Path("validation_results/previous.json")
        if default_baseline.exists():
            baseline_path = default_baseline

    macro_payload = load_payload(macro_path) if macro_path else {"git": {}, "results": []}
    micro_payload = load_payload(micro_path) if micro_path else {"git": {}, "results": []}
    baseline_payload = load_payload(baseline_path) if baseline_path else {"git": {}, "results": []}
    kernel_payload = load_payload(args.kernel) if args.kernel else {"git": {}, "results": []}

    report = render(
        unit=load(unit_path),
        kernel=kernel_payload.get("results", []),
        baseline=baseline_payload.get("results") if baseline_path else None,
        current_git=kernel_payload.get("git"),
        baseline_git=baseline_payload.get("git"),
        macro_baseline=macro_payload.get("results") if macro_path else None,
        micro_baseline=micro_payload.get("results") if micro_path else None,
        macro_git=macro_payload.get("git"),
        micro_git=micro_payload.get("git"),
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
