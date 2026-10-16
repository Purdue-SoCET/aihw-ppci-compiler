"""Metric extraction, schema loading, and CSV export utilities."""
from __future__ import annotations

import csv
import json
from pathlib import Path

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
