#!/usr/bin/env python3
"""
Jing (4/7/26) back-of-envelope vs measured functional-sim metrics.

  - Analytical: 32x32 feature map, 2x2 stride-2 maxpool -> 16x16 outputs;
    ~6 scalar-ish ops per 2x2 window => 16*16*6 = 1536 (order-of-magnitude).
  - Measured: read ``kernel_metrics.csv`` (from atalla/functional_sim
    ``collect_kernel_metrics.py``) for rows ``maxpool*`` and ``gemm*``.

Usage:
  python3 benchmark_jing_pool_vs_gemm.py
  python3 benchmark_jing_pool_vs_gemm.py --csv /path/to/kernel_metrics.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def jing_model(tile_h: int, tile_w: int, ops_per_window: float = 6.0) -> dict[str, float]:
    oh = tile_h // 2
    ow = tile_w // 2
    windows = oh * ow
    return {
        "out_h": float(oh),
        "out_w": float(ow),
        "windows": float(windows),
        "cycles_est": windows * ops_per_window,
    }


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick_rows(rows: list[dict[str, str]], prefix: str) -> list[dict[str, str]]:
    return [r for r in rows if r.get("Kernel", "").lower().startswith(prefix.lower())]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="kernel_metrics.csv from collect_kernel_metrics.py (optional)",
    )
    ap.add_argument("--tile", type=int, default=32, help="Square tile side for Jing model (default 32)")
    args = ap.parse_args()

    j = jing_model(args.tile, args.tile)
    print("Jing analytical (tile={}x{}, {} ops/window):".format(args.tile, args.tile, 6))
    print("  output cells: {} x {} = {:.0f}".format(int(j["out_h"]), int(j["out_w"]), j["windows"]))
    print("  rough op count: {:.0f} windows * 6 ≈ {:.0f}".format(j["windows"], j["cycles_est"]))
    print("  (not cycles — treat as instruction/operation proxy; compare to GEMM tile cost separately.)")

    csv_path = args.csv
    if csv_path is None:
        # Prefer sibling functional_sim checkout under workspace parent
        guess = SCRIPT_DIR.parent.parent.parent.parent / "atalla" / "functional_sim" / "out" / "kernel_metrics.csv"
        if guess.is_file():
            csv_path = guess

    if csv_path is None or not csv_path.is_file():
        print("\nNo CSV provided or found; skip measured ratios.")
        return 0

    rows = load_csv(csv_path)
    pool = pick_rows(rows, "maxpool")
    gemm = pick_rows(rows, "gemm")

    def col(r: dict[str, str], name: str) -> str | None:
        for k in r:
            if k.strip().lower() == name.lower():
                return r[k]
        return None

    def parse_int(r: dict[str, str], *names: str) -> int | None:
        for n in names:
            v = col(r, n)
            if v is None or v == "":
                continue
            try:
                return int(float(v.replace(",", "")))
            except ValueError:
                continue
        return None

    print("\nFrom CSV: {}".format(csv_path))
    if pool:
        print("  maxpool rows: {}".format(", ".join(col(r, "Kernel") or "?" for r in pool)))
    if gemm:
        print("  gemm rows: {}".format(", ".join(col(r, "Kernel") or "?" for r in gemm[:5])))
        if len(gemm) > 5:
            print("    ... (+{} more)".format(len(gemm) - 5))

    # Ops executed (dynamic) column name in collect_kernel_metrics CSV
    for label, subset in ("maxpool", pool), ("gemm", gemm):
        if not subset:
            continue
        ops = []
        for r in subset:
            o = parse_int(r, "Ops executed (dynamic)", "Ops executed", "instructions_executed")
            if o is not None:
                ops.append(o)
        if ops:
            print("  {}: Ops executed (dynamic) min/median/max = {}, {}, {}".format(
                label, min(ops), sorted(ops)[len(ops) // 2], max(ops),
            ))

    if pool and gemm:
        po = parse_int(pool[0], "Ops executed (dynamic)", "Ops executed")
        go = parse_int(gemm[0], "Ops executed (dynamic)", "Ops executed")
        if po and go and go > 0:
            print("\nRatio first maxpool / first gemm row (ops executed): {:.3f}x".format(po / go))

    return 0


if __name__ == "__main__":
    sys.exit(main())
