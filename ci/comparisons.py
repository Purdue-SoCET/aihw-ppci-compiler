"""Baseline comparison and regression tracking renderers."""
from __future__ import annotations

try:
    from ci.formatters import (
        STATUS_LABEL,
        fmt_diff,
        fmt_diff_pct,
        fmt_int,
        fmt_pct,
        fmt_spills,
    )
    from ci.metrics import perf_value, stack_value
except ImportError:
    from formatters import (
        STATUS_LABEL,
        fmt_diff,
        fmt_diff_pct,
        fmt_int,
        fmt_pct,
        fmt_spills,
    )
    from metrics import perf_value, stack_value


def render_baseline_comparison(
    current: list[dict],
    baseline: list[dict],
    current_git: dict | None = None,
    baseline_git: dict | None = None,
    baseline_title: str = "Previous Commit",
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
        f"## 2. Commit Delta & Improvements (vs {baseline_title})",
        "",
    ]

    base_desc = []
    if b_g.get("commit") or b_g.get("branch"):
        br = f"`{b_g['branch']}` @ " if b_g.get("branch") else ""
        msg = f" (*{b_g['message']}*)" if b_g.get("message") else ""
        base_desc.append(f"**Baseline:** {br}`{b_g.get('commit', '')}`{msg}")
    if c_g.get("commit") or c_g.get("branch"):
        br = f"`{c_g['branch']}` @ " if c_g.get("branch") else ""
        msg = f" (*{c_g['message']}*)" if c_g.get("message") else ""
        base_desc.append(f"**Current:** {br}`{c_g.get('commit', '')}`{msg}")

    if base_desc:
        lines.append("Comparing compilation and performance metrics against baseline:")
        for d in base_desc:
            lines.append(f"- {d}")
        lines.append("")
    else:
        lines += [
            f"Comparison of compilation and performance metrics against {baseline_title}.",
            "",
        ]

    lines += [
        "| Kernel | Status (Prev -> Now) | Cycles (Prev -> Now) | Cycle Delta | Scalar Mem (Stack) | Mem Delta | Vector Mem (Scpad) | VMem Delta | VLIW Density | Ops Retired | Ops Delta | Stack Spills |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    total_curr_cycles = 0
    total_base_cycles = 0
    total_curr_ops = 0
    total_base_ops = 0
    total_curr_mem = 0
    total_base_mem = 0
    total_curr_vec_mem = 0
    total_base_vec_mem = 0
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

        c_vm = perf_value(r, "dyn_retired_vector_mem")
        b_vm = perf_value(base, "dyn_retired_vector_mem")

        c_spills = stack_value(r, "loop_spills")
        b_spills = stack_value(base, "loop_spills")

        status_str = f"{STATUS_LABEL.get(base.get('status', 'n/a'), base.get('status', 'n/a'))} -> {STATUS_LABEL.get(r['status'], r['status'])}"

        cycle_str = f"{fmt_int(b_pk)} -> {fmt_int(c_pk)}"
        cycle_delta = fmt_diff(c_pk, b_pk)

        ops_str = f"{fmt_int(b_ops)} -> {fmt_int(c_ops)}"
        ops_delta = fmt_diff(c_ops, b_ops, unit=" ops")

        den_str = f"{fmt_pct(b_den)} -> {fmt_pct(c_den)} ({fmt_diff_pct(c_den, b_den)})"

        mem_str = f"{fmt_int(b_sm)} -> {fmt_int(c_sm)}"
        mem_delta = fmt_diff(c_sm, b_sm, unit=" ops")

        vmem_str = f"{fmt_int(b_vm)} -> {fmt_int(c_vm)}"
        vmem_delta = fmt_diff(c_vm, b_vm, unit=" ops")

        spill_str = f"{fmt_spills(b_spills)} -> {fmt_spills(c_spills)}"

        lines.append(
            f"| `{test}` | {status_str} | {cycle_str} | {cycle_delta} | {mem_str} | {mem_delta} | {vmem_str} | {vmem_delta} | {den_str} | {ops_str} | {ops_delta} | {spill_str} |"
        )

        if c_pk is not None and b_pk is not None:
            total_curr_cycles += c_pk
            total_base_cycles += b_pk
            count_compared += 1
            diff_cyc = c_pk - b_pk
            pct_cyc = (diff_cyc / b_pk * 100.0) if b_pk != 0 else 0
            if diff_cyc < 0:
                improved_count += 1
            elif diff_cyc > 0:
                if abs(pct_cyc) <= 1.0 or abs(diff_cyc) <= 2:
                    pass
                else:
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

        if c_vm is not None and b_vm is not None:
            total_curr_vec_mem += c_vm
            total_base_vec_mem += b_vm

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
            f"- **Kernels Faster:** {improved_count} | **Kernels Regressed:** {regressed_count} | **Parity / Unchanged:** {count_compared - improved_count - regressed_count}",
            f"- **Total Suite Cycles:** {fmt_int(total_base_cycles)} -> {fmt_int(total_curr_cycles)} ({fmt_diff(total_curr_cycles, total_base_cycles)})",
            f"- **Total Instructions Retired:** {fmt_int(total_base_ops)} -> {fmt_int(total_curr_ops)} ({fmt_diff(total_curr_ops, total_base_ops, unit=' ops')})",
            f"- **Mean VLIW Slot Density:** {den_summary}",
            f"- **Total Dynamic Scalar Memory (Stack):** {fmt_int(total_base_mem)} -> {fmt_int(total_curr_mem)} ({fmt_diff(total_curr_mem, total_base_mem, unit=' ops')})",
            f"- **Total Dynamic Vector Memory (Scratchpad):** {fmt_int(total_base_vec_mem)} -> {fmt_int(total_curr_vec_mem)} ({fmt_diff(total_curr_vec_mem, total_base_vec_mem, unit=' ops')})",
            f"- **Total Stack Loop Spills:** {fmt_int(total_base_spills)} -> {fmt_int(total_curr_spills)} ({fmt_diff(total_curr_spills, total_base_spills, unit=' spills')})",
        ]

    return lines


def render_dual_baseline_comparison(
    current: list[dict],
    macro_baseline: list[dict],
    micro_baseline: list[dict],
    current_git: dict | None = None,
    macro_git: dict | None = None,
    micro_git: dict | None = None,
) -> list[str]:
    lines = [
        "",
        "---",
        "",
        "## 2. Benchmark Comparison (vs atalla-arch & vs Last Commit)",
        "",
    ]

    c_g = current_git or {}
    mac_g = macro_git or {}
    mic_g = micro_git or {}

    lines.append("Comparing compilation and performance metrics against macro and micro baselines:")
    mac_br = mac_g.get("branch") or "atalla-arch"
    mac_sha = f" @ `{mac_g['commit']}`" if mac_g.get("commit") else ""
    mac_msg = f" (*{mac_g['message']}*)" if mac_g.get("message") else ""
    lines.append(f"- **Macro Baseline (`atalla-arch`):** `{mac_br}`{mac_sha}{mac_msg}")
    if mic_g.get("commit") or mic_g.get("branch"):
        br = f"`{mic_g['branch']}` @ " if mic_g.get("branch") else ""
        msg = f" (*{mic_g['message']}*)" if mic_g.get("message") else ""
        lines.append(f"- **Micro Baseline (Last Commit):** {br}`{mic_g.get('commit', '')}`{msg}")
    if c_g.get("commit") or c_g.get("branch"):
        br = f"`{c_g['branch']}` @ " if c_g.get("branch") else ""
        msg = f" (*{c_g['message']}*)" if c_g.get("message") else ""
        lines.append(f"- **Current:** {br}`{c_g.get('commit', '')}`{msg}")
    lines.append("")

    lines += [
        "| Kernel | Status | Cycles (Arch / Prev / Now) | vs atalla-arch | vs Last Commit | Scalar Mem (Arch -> Now) | Vector Mem (Arch -> Now) | VLIW Density (Arch -> Now) | Ops Retired (Arch -> Now) | Spills (Arch -> Now) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    macro_map = {r["test"]: r for r in macro_baseline}
    micro_map = {r["test"]: r for r in micro_baseline}

    total_curr_cycles = 0
    total_macro_cycles = 0
    total_micro_cycles = 0
    total_curr_ops = 0
    total_macro_ops = 0
    total_micro_ops = 0
    total_curr_mem = 0
    total_macro_mem = 0
    total_micro_mem = 0
    total_curr_vec_mem = 0
    total_macro_vec_mem = 0
    total_micro_vec_mem = 0
    total_curr_spills = 0
    total_macro_spills = 0
    total_micro_spills = 0
    macro_densities = []
    micro_densities = []
    curr_densities = []

    macro_compared = 0
    macro_improved = 0
    macro_regressed = 0

    micro_compared = 0
    micro_improved = 0
    micro_regressed = 0

    for r in current:
        test = r["test"]
        mac_r = macro_map.get(test)
        mic_r = micro_map.get(test)

        c_pk = perf_value(r, "packets_executed")
        mac_pk = perf_value(mac_r, "packets_executed") if mac_r else None
        mic_pk = perf_value(mic_r, "packets_executed") if mic_r else None

        c_ops = perf_value(r, "instructions_executed")
        mac_ops = perf_value(mac_r, "instructions_executed") if mac_r else None
        mic_ops = perf_value(mic_r, "instructions_executed") if mic_r else None

        c_den = perf_value(r, "packet_slot_utilization_executed_pct")
        mac_den = perf_value(mac_r, "packet_slot_utilization_executed_pct") if mac_r else None
        mic_den = perf_value(mic_r, "packet_slot_utilization_executed_pct") if mic_r else None

        c_sm = perf_value(r, "dyn_retired_scalar_mem")
        mac_sm = perf_value(mac_r, "dyn_retired_scalar_mem") if mac_r else None
        mic_sm = perf_value(mic_r, "dyn_retired_scalar_mem") if mic_r else None

        c_vm = perf_value(r, "dyn_retired_vector_mem")
        mac_vm = perf_value(mac_r, "dyn_retired_vector_mem") if mac_r else None
        mic_vm = perf_value(mic_r, "dyn_retired_vector_mem") if mic_r else None

        c_spills = stack_value(r, "loop_spills")
        mac_spills = stack_value(mac_r, "loop_spills") if mac_r else None
        mic_spills = stack_value(mic_r, "loop_spills") if mic_r else None

        status_str = STATUS_LABEL.get(r.get("status", "n/a"), r.get("status", "n/a"))
        cycle_col = f"{fmt_int(mac_pk)} / {fmt_int(mic_pk)} / {fmt_int(c_pk)}"
        macro_diff_str = fmt_diff(c_pk, mac_pk) if mac_pk is not None else "-"
        micro_diff_str = fmt_diff(c_pk, mic_pk) if mic_pk is not None else "-"

        if mac_sm is not None and c_sm is not None:
            sm_col = f"{fmt_int(mac_sm)} -> {fmt_int(c_sm)} ({fmt_diff(c_sm, mac_sm, unit=' ops')})"
        else:
            sm_col = fmt_int(c_sm)

        if mac_vm is not None and c_vm is not None:
            vm_col = f"{fmt_int(mac_vm)} -> {fmt_int(c_vm)} ({fmt_diff(c_vm, mac_vm, unit=' ops')})"
        else:
            vm_col = fmt_int(c_vm)

        if mac_den is not None and c_den is not None:
            den_col = f"{fmt_pct(mac_den)} -> {fmt_pct(c_den)} ({fmt_diff_pct(c_den, mac_den)})"
        else:
            den_col = fmt_pct(c_den)

        if mac_ops is not None and c_ops is not None:
            ops_col = f"{fmt_int(mac_ops)} -> {fmt_int(c_ops)} ({fmt_diff(c_ops, mac_ops, unit=' ops')})"
        else:
            ops_col = fmt_int(c_ops)

        if mac_spills is not None and c_spills is not None:
            spill_col = f"{fmt_spills(mac_spills)} -> {fmt_spills(c_spills)}"
        else:
            spill_col = fmt_spills(c_spills)

        lines.append(
            f"| `{test}` | {status_str} | {cycle_col} | {macro_diff_str} | {micro_diff_str} | {sm_col} | {vm_col} | {den_col} | {ops_col} | {spill_col} |"
        )

        if c_pk is not None and mac_pk is not None:
            total_curr_cycles += c_pk
            total_macro_cycles += mac_pk
            macro_compared += 1
            diff_m = c_pk - mac_pk
            pct_m = (diff_m / mac_pk * 100.0) if mac_pk != 0 else 0
            if diff_m < 0:
                macro_improved += 1
            elif diff_m > 0:
                if abs(pct_m) <= 1.0 or abs(diff_m) <= 2:
                    pass
                else:
                    macro_regressed += 1

        if mac_r:
            mac_ops = perf_value(mac_r, "instructions_executed")
            if mac_ops is not None:
                total_macro_ops += mac_ops
            mac_sm = perf_value(mac_r, "dyn_retired_scalar_mem")
            if mac_sm is not None:
                total_macro_mem += mac_sm
            mac_vm = perf_value(mac_r, "dyn_retired_vector_mem")
            if mac_vm is not None:
                total_macro_vec_mem += mac_vm
            mac_spills = stack_value(mac_r, "loop_spills")
            if mac_spills is not None:
                total_macro_spills += mac_spills
            mac_den = perf_value(mac_r, "packet_slot_utilization_executed_pct")
            if mac_den is not None:
                macro_densities.append(mac_den)

        if c_pk is not None and mic_pk is not None:
            total_micro_cycles += mic_pk
            micro_compared += 1
            diff_mi = c_pk - mic_pk
            pct_mi = (diff_mi / mic_pk * 100.0) if mic_pk != 0 else 0
            if diff_mi < 0:
                micro_improved += 1
            elif diff_mi > 0:
                if abs(pct_mi) <= 1.0 or abs(diff_mi) <= 2:
                    pass
                else:
                    micro_regressed += 1

        if mic_r:
            mic_ops = perf_value(mic_r, "instructions_executed")
            if mic_ops is not None:
                total_micro_ops += mic_ops
            mic_sm = perf_value(mic_r, "dyn_retired_scalar_mem")
            if mic_sm is not None:
                total_micro_mem += mic_sm
            mic_vm = perf_value(mic_r, "dyn_retired_vector_mem")
            if mic_vm is not None:
                total_micro_vec_mem += mic_vm
            mic_spills = stack_value(mic_r, "loop_spills")
            if mic_spills is not None:
                total_micro_spills += mic_spills
            mic_den = perf_value(mic_r, "packet_slot_utilization_executed_pct")
            if mic_den is not None:
                micro_densities.append(mic_den)

        if c_ops is not None:
            total_curr_ops += c_ops
        if c_sm is not None:
            total_curr_mem += c_sm
        if c_vm is not None:
            total_curr_vec_mem += c_vm
        if c_spills is not None:
            total_curr_spills += c_spills
        if c_den is not None:
            curr_densities.append(c_den)

    avg_curr_den = (sum(curr_densities) / len(curr_densities)) if curr_densities else None

    if macro_compared > 0:
        avg_mac_den = (sum(macro_densities) / len(macro_densities)) if macro_densities else None
        mac_den_summary = f"{fmt_pct(avg_mac_den)} -> {fmt_pct(avg_curr_den)} ({fmt_diff_pct(avg_curr_den, avg_mac_den)})" if avg_mac_den else "n/a"
        lines += [
            "",
            "### Summary vs atalla-arch (Macro Baseline):",
            f"- **Kernels Faster:** {macro_improved} | **Kernels Regressed:** {macro_regressed} | **Parity / Unchanged:** {macro_compared - macro_improved - macro_regressed}",
            f"- **Total Suite Cycles:** {fmt_int(total_macro_cycles)} -> {fmt_int(total_curr_cycles)} ({fmt_diff(total_curr_cycles, total_macro_cycles)})",
            f"- **Total Instructions Retired:** {fmt_int(total_macro_ops)} -> {fmt_int(total_curr_ops)} ({fmt_diff(total_curr_ops, total_macro_ops, unit=' ops')})",
            f"- **Mean VLIW Slot Density:** {mac_den_summary}",
            f"- **Total Dynamic Scalar Memory (Stack):** {fmt_int(total_macro_mem)} -> {fmt_int(total_curr_mem)} ({fmt_diff(total_curr_mem, total_macro_mem, unit=' ops')})",
            f"- **Total Dynamic Vector Memory (Scratchpad):** {fmt_int(total_macro_vec_mem)} -> {fmt_int(total_curr_vec_mem)} ({fmt_diff(total_curr_vec_mem, total_macro_vec_mem, unit=' ops')})",
            f"- **Total Stack Loop Spills:** {fmt_int(total_macro_spills)} -> {fmt_int(total_curr_spills)} ({fmt_diff(total_curr_spills, total_macro_spills, unit=' spills')})",
        ]

    if micro_compared > 0:
        avg_mic_den = (sum(micro_densities) / len(micro_densities)) if micro_densities else None
        mic_den_summary = f"{fmt_pct(avg_mic_den)} -> {fmt_pct(avg_curr_den)} ({fmt_diff_pct(avg_curr_den, avg_mic_den)})" if avg_mic_den else "n/a"
        lines += [
            "",
            "### Summary vs Last Commit (Micro Baseline):",
            f"- **Kernels Faster:** {micro_improved} | **Kernels Regressed:** {micro_regressed} | **Parity / Unchanged:** {micro_compared - micro_improved - micro_regressed}",
            f"- **Total Suite Cycles:** {fmt_int(total_micro_cycles)} -> {fmt_int(total_curr_cycles)} ({fmt_diff(total_curr_cycles, total_micro_cycles)})",
            f"- **Total Instructions Retired:** {fmt_int(total_micro_ops)} -> {fmt_int(total_curr_ops)} ({fmt_diff(total_curr_ops, total_micro_ops, unit=' ops')})",
            f"- **Mean VLIW Slot Density:** {mic_den_summary}",
            f"- **Total Dynamic Scalar Memory (Stack):** {fmt_int(total_micro_mem)} -> {fmt_int(total_curr_mem)} ({fmt_diff(total_curr_mem, total_micro_mem, unit=' ops')})",
            f"- **Total Dynamic Vector Memory (Scratchpad):** {fmt_int(total_micro_vec_mem)} -> {fmt_int(total_curr_vec_mem)} ({fmt_diff(total_curr_vec_mem, total_micro_vec_mem, unit=' ops')})",
            f"- **Total Stack Loop Spills:** {fmt_int(total_micro_spills)} -> {fmt_int(total_curr_spills)} ({fmt_diff(total_curr_spills, total_micro_spills, unit=' spills')})",
        ]

    return lines
