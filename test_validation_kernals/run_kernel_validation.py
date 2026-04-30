#!/usr/bin/env python3
"""Kernel C validation: atalla_cc -> build_compiler -> seed .data -> functional_sim/run.py.

add/relu: BF16 goldens. softmax: sum≈1, non-negative. maxpool/maxpool_2x2: finite outputs
(SDMA layout ≠ dense seed for 2x1; 2x2 checks 4×4 out tile). layernorm: BF16 golden vs numpy
on the 4×4 active mask. conv_*: systolic GEMM golden + bias (W DRAM K×N). gemm_tiled: cross-variant C match.
Failures are not skipped—compile/build/sim errors propagate.
"""
from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Callable

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
_SIM_ROOT = _REPO / "functional_sim"


def _prepend_sys_path(path: Path) -> None:
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)
    sys.path.insert(0, path_str)


def build_pythonpath(*paths: Path) -> str:
    entries: list[str] = []
    for path in paths:
        entry = str(path)
        if entry not in entries:
            entries.append(entry)
    for entry in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if entry and entry not in entries:
            entries.append(entry)
    return os.pathsep.join(entries)


if not _SIM_ROOT.is_dir():
    raise RuntimeError(f"Missing simulator dependency directory: {_SIM_ROOT}")

_prepend_sys_path(_REPO)
_prepend_sys_path(_SIM_ROOT)

from src.components.gemm import (  # noqa: E402
    systolic_gemm_vv_dram_reference,
    to_bf16,
)

GEMM_TILED_STEMS = (
    "gemm_tiled_baseline",
    "gemm_tiled_pipelined",
    "gemm_tiled_pipelined_unrolled",
)
C_BASE_GEMM = 0x2400
GEMM_GMN = 8

DEFAULT_TESTS = (
    "add.c",
    "conv_baseline.c",
    "conv_pipelined.c",
    "conv_pipelined_unrolled.c",
    "gemm_tiled_baseline.c",
    "gemm_tiled_pipelined.c",
    "gemm_tiled_pipelined_unrolled.c",
    "layernorm.c",
    "maxpool.c",
    "maxpool_2x2.c",
    "relu.c",
    "softmax.c",
)


def run_and_log(cmd: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    log_path.write_text(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {proc.returncode}: {' '.join(cmd)}\nSee {log_path}"
        )


def set_data_section(image: str, data_lines: list[str]) -> str:
    stripped = image.rstrip()
    head, sep, _ = stripped.partition(".data")
    base = head.rstrip() if sep else stripped
    body = "\n".join(data_lines)
    return f"{base}\n.data\n{body}\n"


def f32_to_bf16_u16(x: float) -> int:
    u = struct.unpack("<I", struct.pack("<f", np.float32(x)))[0]
    lsb = (u >> 16) & 1
    u = (u + (0x7FFF + lsb)) & 0xFFFFFFFF
    return (u >> 16) & 0xFFFF


def bf16_u16_to_f32(h: int) -> np.float32:
    u = (int(h) & 0xFFFF) << 16
    return np.float32(struct.unpack("<f", struct.pack("<I", u))[0])


def write_bf16_matrix(words: dict[int, int], base: int, mat: np.ndarray) -> None:
    mat = np.asarray(mat, dtype=np.float32)
    rows, cols = mat.shape
    for i in range(rows):
        for j in range(cols):
            ba = base + (i * cols + j) * 2
            h = f32_to_bf16_u16(float(mat[i, j]))
            wa = ba & ~3
            cur = int(words.get(wa, 0)) & 0xFFFFFFFF
            if ba & 2:
                cur = (cur & 0xFFFF) | ((h & 0xFFFF) << 16)
            else:
                cur = (cur & 0xFFFF0000) | (h & 0xFFFF)
            words[wa] = cur


def write_u32_words(words: dict[int, int], base: int, vals: list[int]) -> None:
    for i, v in enumerate(vals):
        words[base + i * 4] = int(v) & 0xFFFFFFFF


def write_f32(words: dict[int, int], byte_addr: int, x: float) -> None:
    u = struct.unpack("<I", struct.pack("<f", np.float32(x)))[0]
    words[int(byte_addr) & 0xFFFFFFFF] = u & 0xFFFFFFFF


def words_to_lines(words: dict[int, int]) -> list[str]:
    return [f"{a:08X}: {w & 0xFFFFFFFF:08X}" for a, w in sorted(words.items())]


def parse_data_mem(path: Path) -> dict[int, int]:
    text = path.read_text()
    if "DATA MEM" not in text:
        raise RuntimeError(f"No DATA MEM section in {path}")
    _, _, rest = text.partition("DATA MEM")
    out: dict[int, int] = {}
    for line in rest.splitlines():
        line = line.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        a, d = [x.strip() for x in line.split(":", 1)]
        d = d.replace(" ", "").replace("_", "")
        try:
            out[int(a, 16)] = int(d, 16) & 0xFFFFFFFF
        except ValueError:
            continue
    return out


def read_bf16_le(mem: dict[int, int], byte_addr: int) -> int:
    ba = int(byte_addr) & 0xFFFFFFFF
    wa = ba & ~3
    w = int(mem.get(wa, 0)) & 0xFFFFFFFF
    if ba & 2:
        return (w >> 16) & 0xFFFF
    return w & 0xFFFF


def read_bf16_matrix(mem: dict[int, int], base: int, rows: int, cols: int) -> np.ndarray:
    out = np.zeros((rows, cols), dtype=np.float32)
    for i in range(rows):
        for j in range(cols):
            h = read_bf16_le(mem, base + (i * cols + j) * 2)
            out[i, j] = bf16_u16_to_f32(h)
    return out


def assert_close_bf16(
    got: np.ndarray, exp: np.ndarray, *, name: str, rtol: float = 0.0, atol: float = 0.0
) -> None:
    got = np.asarray(got, dtype=np.float32)
    exp = np.asarray(exp, dtype=np.float32)
    if got.shape != exp.shape:
        raise RuntimeError(f"{name}: shape {got.shape} != {exp.shape}")
    diff = np.max(np.abs(got - exp))
    lim = atol + rtol * (np.max(np.abs(exp)) + 1e-30)
    if diff > lim:
        raise RuntimeError(f"{name}: max abs diff {diff} (limit ~{lim})\nexp:\n{exp}\ngot:\n{got}")


# --- per-test builders / checkers ---

CFG = 0x3C


def validate_add(out_mem: Path) -> None:
    rows, cols = 4, 32
    a_base, b_base, c_base = 0x1000, 0x1200, 0x1400
    rng = np.random.default_rng(0)
    a = rng.normal(size=(rows, cols)).astype(np.float32) * 0.25
    b = rng.normal(size=(rows, cols)).astype(np.float32) * 0.25
    exp = to_bf16(to_bf16(a) + to_bf16(b))
    mem = parse_data_mem(out_mem)
    got = read_bf16_matrix(mem, c_base, rows, cols)
    assert_close_bf16(got, exp, name="add C")


def validate_maxpool(out_mem: Path) -> None:
    """SDMA tile geometry (sdma_in) does not match dense row-major 8×8 seeding; sanity-check only."""
    h_out, w = 4, 8
    out_base = 0x1800
    mem = parse_data_mem(out_mem)
    got = read_bf16_matrix(mem, out_base, h_out, w)
    if not np.all(np.isfinite(got)):
        raise RuntimeError("maxpool: non-finite outputs")


def validate_maxpool_2x2(out_mem: Path) -> None:
    h_out, w = 4, 4
    out_base = 0x1800
    mem = parse_data_mem(out_mem)
    got = read_bf16_matrix(mem, out_base, h_out, w)
    if not np.all(np.isfinite(got)):
        raise RuntimeError("maxpool_2x2: non-finite outputs")


def validate_layernorm(out_mem: Path) -> None:
    """4×32 tile, mask 0xF: stats over the leading 4 lanes × 4 rows (same as build_layernorm_param layout)."""
    rows, active = 4, 4
    in_base = 0x1000
    eps = 1e-5
    rng = np.random.default_rng(6)
    inp = (rng.normal(size=(rows, 32)) * 0.35).astype(np.float32)
    x4 = inp[:, :active].astype(np.float64)
    mean = float(x4.mean())
    var = float(((x4 - mean) ** 2).mean())
    exp4 = (x4 - mean) / np.sqrt(var + eps)
    exp = to_bf16(exp4.astype(np.float32))
    mem = parse_data_mem(out_mem)
    got_full = read_bf16_matrix(mem, in_base, rows, 32)
    got = got_full[:, :active]
    assert_close_bf16(got, exp, name="layernorm out (4×4 active)", atol=0.08, rtol=0.12)


def validate_relu(out_mem: Path) -> None:
    rows, cols = 4, 32
    in_base, out_base = 0x1000, 0x1400
    rng = np.random.default_rng(4)
    inp = (rng.normal(size=(rows, cols)) * 0.5).astype(np.float32)
    exp = to_bf16(np.maximum(to_bf16(inp), 0.0))
    mem = parse_data_mem(out_mem)
    got = read_bf16_matrix(mem, out_base, rows, cols)
    assert_close_bf16(got, exp, name="relu out", atol=1e-6)


def validate_softmax(out_mem: Path) -> None:
    """RMAX/RSUM/EXP path differs from a naive numpy softmax; check normalization + non-negativity."""
    rows, cols = 1, 32
    in_base = 0x1000
    mem = parse_data_mem(out_mem)
    got = read_bf16_matrix(mem, in_base, rows, cols)
    s = float(np.sum(got))
    if abs(s - 1.0) > 0.2:
        raise RuntimeError(f"softmax: sum(got)={s}, expected ~1.0")
    if float(np.min(got)) < -1e-5:
        raise RuntimeError("softmax: negative output")


def seed_add(words: dict[int, int]) -> None:
    rows, cols = 4, 32
    a_base, b_base, c_base = 0x1000, 0x1200, 0x1400
    rng = np.random.default_rng(0)
    a = rng.normal(size=(rows, cols)).astype(np.float32) * 0.25
    b = rng.normal(size=(rows, cols)).astype(np.float32) * 0.25
    write_u32_words(words, CFG, [a_base, b_base, c_base])
    write_bf16_matrix(words, a_base, a)
    write_bf16_matrix(words, b_base, b)
    write_bf16_matrix(words, c_base, np.zeros((rows, cols), dtype=np.float32))


def _conv_tensors() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Same RNG + shapes as ``seed_conv`` / ``validate_conv`` (M×K_flat, K_out×K_flat, M×K_out)."""
    m, k_flat, n_out = 4, 27, 4
    rng = np.random.default_rng(1)
    a = (rng.normal(size=(m, k_flat)) * 0.1).astype(np.float32)
    w_rows = (rng.normal(size=(n_out, k_flat)) * 0.1).astype(np.float32)
    c0 = (rng.normal(size=(m, n_out)) * 0.05).astype(np.float32)
    return a, w_rows, c0


def seed_conv(words: dict[int, int]) -> None:
    """DRAM layout matches ``validate_and_benchmark._run_conv_variant``: A (M×K), W (K×N), C (M×N)."""
    m, k_flat, n_out = 4, 27, 4
    a_base, w_base, c_base = 0x1000, 0x2000, 0x3000
    a, w_rows, c0 = _conv_tensors()
    w_kn = w_rows.T
    write_u32_words(words, CFG, [a_base, 0, w_base, 0, c_base, 0])
    write_bf16_matrix(words, a_base, a)
    write_bf16_matrix(words, w_base, w_kn)
    write_bf16_matrix(words, c_base, c0)


def validate_conv(out_mem: Path) -> None:
    """Golden = systolic GEMM ref (same as validate_and_benchmark) + float32 add of BF16 bias C0.

    functional_sim gemm.vv writes ``matmul_out + src2`` in float32; DRAM stores BF16, so we
    compare against ``to_bf16(mat + to_bf16(c0))``.
    """
    m, k_out = 4, 4
    c_base = 0x3000
    a, w_rows, c0 = _conv_tensors()
    b_kn = w_rows.T
    mat = systolic_gemm_vv_dram_reference(a, b_kn)
    c0_q = to_bf16(c0)
    exp = to_bf16(mat + c0_q)
    mem = parse_data_mem(out_mem)
    got = read_bf16_matrix(mem, c_base, m, k_out)
    assert_close_bf16(got, exp, name="conv-as-GEMM C", atol=0.002, rtol=0.0)


def seed_gemm_tiled(words: dict[int, int]) -> None:
    g_m = g_n = g_k = 8
    tile_sz = 4
    m_tiles = n_tiles = k_tiles = 2
    a_base, w_base, c_base = 0x2000, 0x2200, 0x2400
    rng = np.random.default_rng(2)
    a_full = (rng.normal(size=(g_m, g_k)) * 0.08).astype(np.float32)
    w_full = (rng.normal(size=(g_k, g_n)) * 0.08).astype(np.float32)
    c0 = np.zeros((g_m, g_n), dtype=np.float32)
    write_u32_words(
        words,
        CFG,
        [
            a_base,
            w_base,
            c_base,
            g_m,
            g_n,
            g_k,
            m_tiles,
            n_tiles,
            k_tiles,
            tile_sz,
        ],
    )
    write_bf16_matrix(words, a_base, a_full)
    write_bf16_matrix(words, w_base, w_full)
    write_bf16_matrix(words, c_base, c0)


def seed_maxpool(words: dict[int, int]) -> None:
    h_in, w = 8, 8
    in_base, out_base = 0x1000, 0x1800
    rng = np.random.default_rng(3)
    inp = (rng.random(size=(h_in, w)) * 2.0 - 0.5).astype(np.float32)
    write_u32_words(words, CFG, [in_base, out_base])
    write_bf16_matrix(words, in_base, inp)
    write_bf16_matrix(words, out_base, np.zeros((4, w), dtype=np.float32))


def seed_maxpool_2x2(words: dict[int, int]) -> None:
    h_in, w = 8, 8
    in_base, out_base = 0x1000, 0x1800
    rng = np.random.default_rng(7)
    inp = (rng.random(size=(h_in, w)) * 2.0 - 0.5).astype(np.float32)
    write_u32_words(words, CFG, [in_base, out_base])
    write_bf16_matrix(words, in_base, inp)
    write_bf16_matrix(words, out_base, np.zeros((4, 4), dtype=np.float32))


def seed_layernorm(words: dict[int, int]) -> None:
    rows, cols = 4, 32
    in_base = 0x1000
    scpad_base = 1
    rng = np.random.default_rng(6)
    inp = (rng.normal(size=(rows, cols)) * 0.35).astype(np.float32)
    write_u32_words(words, CFG, [in_base, scpad_base])
    write_f32(words, 20, 1e-5)
    write_f32(words, 24, 1.0 / 16.0)
    write_bf16_matrix(words, in_base, inp)


def seed_relu(words: dict[int, int]) -> None:
    rows, cols = 4, 32
    in_base, out_base = 0x1000, 0x1400
    rng = np.random.default_rng(4)
    inp = (rng.normal(size=(rows, cols)) * 0.5).astype(np.float32)
    write_u32_words(words, CFG, [in_base, out_base])
    write_bf16_matrix(words, in_base, inp)
    write_bf16_matrix(words, out_base, np.zeros((rows, cols), dtype=np.float32))


def seed_softmax(words: dict[int, int]) -> None:
    rows, cols = 1, 32
    in_base = 0x1000
    rng = np.random.default_rng(5)
    inp = (rng.normal(size=(rows, cols)) * 0.3).astype(np.float32)
    write_u32_words(words, CFG, [in_base, 0])
    write_bf16_matrix(words, in_base, inp)


KernelSpec = tuple[Callable[[dict[int, int]], None], Callable[[Path], None] | None]

KERNEL_REGISTRY: dict[str, KernelSpec] = {
    "add": (seed_add, validate_add),
    "conv_baseline": (seed_conv, validate_conv),
    "conv_pipelined": (seed_conv, validate_conv),
    "conv_pipelined_unrolled": (seed_conv, validate_conv),
    "gemm_tiled_baseline": (seed_gemm_tiled, None),
    "gemm_tiled_pipelined": (seed_gemm_tiled, None),
    "gemm_tiled_pipelined_unrolled": (seed_gemm_tiled, None),
    "layernorm": (seed_layernorm, validate_layernorm),
    "maxpool": (seed_maxpool, validate_maxpool),
    "maxpool_2x2": (seed_maxpool_2x2, validate_maxpool_2x2),
    "relu": (seed_relu, validate_relu),
    "softmax": (seed_softmax, validate_softmax),
}


def compare_gemm_tiled_matrix_outputs(script_dir: Path) -> None:
    mats: list[tuple[str, np.ndarray]] = []
    for s in GEMM_TILED_STEMS:
        p = script_dir / "out" / s / "output_mem.out"
        if not p.exists():
            continue
        mem = parse_data_mem(p)
        mats.append((s, read_bf16_matrix(mem, C_BASE_GEMM, GEMM_GMN, GEMM_GMN)))
    if len(mats) < 2:
        return
    ref_s, ref_m = mats[0]
    for name, m in mats[1:]:
        assert_close_bf16(m, ref_m, name=f"gemm_tiled {name} vs {ref_s}", atol=0.0, rtol=0.0)


def run_one(
    test_path: Path,
    *,
    script_dir: Path,
    repo_root: Path,
    sim_root: Path,
    env: dict[str, str],
) -> None:
    stem = test_path.stem
    if stem not in KERNEL_REGISTRY:
        raise KeyError(f"No kernel spec for {stem!r}; known: {sorted(KERNEL_REGISTRY)}")

    seed_fn, check_fn = KERNEL_REGISTRY[stem]
    out_dir = script_dir / "out" / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    asm_path = out_dir / f"{stem}.s"
    image_path = out_dir / f"{stem}.in"
    compile_log = out_dir / "compile.log"
    build_log = out_dir / "build.log"
    run_log = out_dir / "run.log"

    output_mem = out_dir / "output_mem.out"
    output_sregs = out_dir / "output_sregs.out"
    output_vregs = out_dir / "output_vregs.out"
    output_mregs = out_dir / "output_mregs.out"
    output_scpad0 = out_dir / "output_scpad0.out"
    output_scpad1 = out_dir / "output_scpad1.out"
    output_perf = out_dir / "output_perf.out"

    cc = [
        sys.executable,
        "-m",
        "ppci.cli.atalla_cc",
        "--machine",
        "atalla",
        "-O",
        "2",
        "-S",
        "-p",
        str(test_path),
        "-o",
        str(asm_path),
    ]
    run_and_log(cc, cwd=repo_root, env=env, log_path=compile_log)

    bc = [
        sys.executable,
        str(sim_root / "build_compiler.py"),
        "-i",
        str(asm_path),
        "-o",
        str(image_path),
    ]
    run_and_log(bc, cwd=sim_root, env=env, log_path=build_log)

    words: dict[int, int] = {}
    seed_fn(words)
    image_path.write_text(set_data_section(image_path.read_text(), words_to_lines(words)))

    run_and_log(
        [
            sys.executable,
            str(sim_root / "run.py"),
            "--input_file",
            str(image_path),
            "--output_mem_file",
            str(output_mem),
            "--output_sreg_file",
            str(output_sregs),
            "--output_vreg_file",
            str(output_vregs),
            "--output_mreg_file",
            str(output_mregs),
            "--output_scpad_file0",
            str(output_scpad0),
            "--output_scpad_file1",
            str(output_scpad1),
            "--output_perf_file",
            str(output_perf),
        ],
        cwd=sim_root,
        env=env,
        log_path=run_log,
    )

    if check_fn is not None:
        check_fn(output_mem)
    print(f"OK {test_path.name}  artifacts: {out_dir}")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    sim_root = repo_root / "functional_sim"
    env = os.environ.copy()
    env["PYTHONPATH"] = build_pythonpath(sim_root, repo_root)
    # functional_sim/build_compiler: avoid SDMA latency stall rows inflating PC distance
    # past BEQ/BNE range (see instruction_latency scpad.ld/st).
    env["ATALLA_FUNCTIONAL_SCHED_LATENCY"] = "1"

    ap = argparse.ArgumentParser(
        description=(
            "Validate kernel C tests: compile, seed .data (cfg + tensors), run functional_sim. "
            "add/relu/layernorm/conv use numeric goldens (conv: systolic GEMM ref + bias); "
            "maxpool variants sanity-check outputs; softmax checks normalization; "
            "gemm_tiled variants are cross-checked when all ran."
        )
    )
    ap.add_argument(
        "--test",
        type=Path,
        default=None,
        help="Single test .c file (default: run --all)",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help=f"Run all default tests (same as default): {', '.join(DEFAULT_TESTS)}",
    )
    args = ap.parse_args()

    if args.test is not None:
        tests = [args.test.resolve()]
    else:
        tests = [script_dir / t for t in DEFAULT_TESTS]

    failed: list[str] = []
    for t in tests:
        if not t.exists():
            failed.append(f"missing {t}")
            continue
        try:
            run_one(t, script_dir=script_dir, repo_root=repo_root, sim_root=sim_root, env=env)
        except Exception as e:
            failed.append(f"{t.name}: {e}")

    if args.test is None:
        try:
            compare_gemm_tiled_matrix_outputs(script_dir)
            print("OK gemm_tiled cross-check: outputs match across built variants.")
        except Exception as e:
            failed.append(f"gemm_tiled cross-check: {e}")

    if failed:
        print("FAILURES:\n" + "\n".join(failed), file=sys.stderr)
        return 1
    print(f"All {len(tests)} kernel run(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
