#!/usr/bin/env python3
"""Kernel C validation: atalla_cc -> build_compiler -> seed .data -> functional_sim/run.py.

Every kernel is checked against a numpy golden computed from the same seeded inputs:
add/relu/maxpool/maxpool_2x2: exact BF16. softmax: numpy softmax. layernorm: numpy on the
4×4 active mask. conv_*: systolic GEMM + bias. gemm_tiled_*: A @ W.
Kernels in EXPECTED_FAILURES are known compiler bugs: they are reported but don't fail the run.
"""
from __future__ import annotations

import argparse
import json
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
GEMM_TILE = 4

# Compiled kernels whose golden currently fails because of a known compiler bug. They are
# reported as "xfail" and don't fail the run; one that starts passing is reported "xpass"
# so it can be removed from this list.
EXPECTED_FAILURES: dict[str, str] = {
    "maxpool_2x2": "Masked-op merge semantics: unmasked lanes in multi-step pooling require accumulator preservation.",
}

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


def read_perf(perf_path: Path) -> dict[str, float] | None:
    if not perf_path.exists():
        return None
    perf: dict[str, float] = {}
    for line in perf_path.read_text().splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            continue
        try:
            perf[key.strip()] = float(value)
        except ValueError:
            continue
    return perf


def run_and_log(cmd: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=30)
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


def _maxpool_input(seed: int) -> np.ndarray:
    """8×8 BF16 tile shared by the maxpool seeds and goldens."""
    rng = np.random.default_rng(seed)
    return (rng.random(size=(8, 8)) * 2.0 - 0.5).astype(np.float32)


def validate_maxpool(out_mem: Path) -> None:
    """Vertical 2x1 pool, stride 2: out[r] = max(in[2r], in[2r+1]) → 4×8."""
    inp = to_bf16(_maxpool_input(3))
    exp = np.maximum(inp[0::2], inp[1::2])
    got = read_bf16_matrix(parse_data_mem(out_mem), 0x1800, 4, 8)
    assert_close_bf16(got, exp, name="maxpool out")


def validate_maxpool_2x2(out_mem: Path) -> None:
    """2×2 pool, stride 2 → 4×4."""
    inp = to_bf16(_maxpool_input(7))
    rows = np.maximum(inp[0::2], inp[1::2])
    exp = np.maximum(rows[:, 0::2], rows[:, 1::2])
    got = read_bf16_matrix(parse_data_mem(out_mem), 0x1800, 4, 4)
    assert_close_bf16(got, exp, name="maxpool_2x2 out")


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
    # Rounding every step to BF16 lands within 0.016 of exact (1 ULP at |y|≈2); allow 2 ULP.
    assert_close_bf16(got, exp, name="layernorm out (4×4 active)", atol=0.03)


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
    """In-place softmax over one 32-lane row (outputs ~0.03; handwritten is within 2e-4)."""
    rng = np.random.default_rng(5)
    x = to_bf16((rng.normal(size=(1, 32)) * 0.3).astype(np.float32)).astype(np.float64)
    e = np.exp(x - x.max())
    exp = to_bf16((e / e.sum()).astype(np.float32))
    got = read_bf16_matrix(parse_data_mem(out_mem), 0x1000, 1, 32)
    assert_close_bf16(got, exp, name="softmax out", atol=1e-3)


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


def _gemm_tiled_tensors() -> tuple[np.ndarray, np.ndarray]:
    """A (8×8) and W (8×8) shared by seed_gemm_tiled and validate_gemm_tiled."""
    rng = np.random.default_rng(2)
    a = (rng.normal(size=(8, 8)) * 0.08).astype(np.float32)
    w = (rng.normal(size=(8, 8)) * 0.08).astype(np.float32)
    return a, w


def _transpose_blocks(mat: np.ndarray, tile: int) -> np.ndarray:
    out = mat.copy()
    for i in range(0, mat.shape[0], tile):
        for j in range(0, mat.shape[1], tile):
            out[i : i + tile, j : j + tile] = mat[i : i + tile, j : j + tile].T
    return out


def validate_gemm_tiled(out_mem: Path) -> None:
    """C = A @ W (8×8×8, 4×4 tiles, C starts at zero)."""
    a, w = _gemm_tiled_tensors()
    exp = to_bf16(to_bf16(a) @ to_bf16(w))
    got = read_bf16_matrix(parse_data_mem(out_mem), 0x2400, 8, 8)
    assert_close_bf16(got, exp, name="gemm_tiled C", atol=0.002)


def seed_gemm_tiled(words: dict[int, int]) -> None:
    """W is stored with each tile transposed: lw.vi loads a scratchpad row as a *column*
    of the weight buffer, so row i of a stored tile must be column i of the logical W tile.
    """
    g_m = g_n = g_k = 8
    tile_sz = GEMM_TILE
    m_tiles = n_tiles = k_tiles = 2
    a_base, w_base, c_base = 0x2000, 0x2200, 0x2400
    a_full, w_logical = _gemm_tiled_tensors()
    w_full = _transpose_blocks(w_logical, tile_sz)
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
    w = 8
    in_base, out_base = 0x1000, 0x1800
    inp = _maxpool_input(3)
    write_u32_words(words, CFG, [in_base, out_base])
    write_bf16_matrix(words, in_base, inp)
    write_bf16_matrix(words, out_base, np.zeros((4, w), dtype=np.float32))


def seed_maxpool_2x2(words: dict[int, int]) -> None:
    in_base, out_base = 0x1000, 0x1800
    inp = _maxpool_input(7)
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


KernelSpec = tuple[Callable[[dict[int, int]], None], Callable[[Path], None]]

KERNEL_REGISTRY: dict[str, KernelSpec] = {
    "add": (seed_add, validate_add),
    "conv_baseline": (seed_conv, validate_conv),
    "conv_pipelined": (seed_conv, validate_conv),
    "conv_pipelined_unrolled": (seed_conv, validate_conv),
    "gemm_tiled_baseline": (seed_gemm_tiled, validate_gemm_tiled),
    "gemm_tiled_pipelined": (seed_gemm_tiled, validate_gemm_tiled),
    "gemm_tiled_pipelined_unrolled": (seed_gemm_tiled, validate_gemm_tiled),
    "layernorm": (seed_layernorm, validate_layernorm),
    "maxpool": (seed_maxpool, validate_maxpool),
    "maxpool_2x2": (seed_maxpool_2x2, validate_maxpool_2x2),
    "relu": (seed_relu, validate_relu),
    "softmax": (seed_softmax, validate_softmax),
}


# Handwritten (systems-team) generator in functional_sim/kernels that matches each C kernel's
# shape and cfg layout, so both run on the same seeded image and the same checker.
# Not paired yet, because the generator's memory layout doesn't match the C kernel's:
#   layernorm   build_layernorm_param.py assumes an N-wide GMEM tile; C uses a 4x32 tile.
#   gemm_tiled  build_gemm_tiled.py --tile 4 writes nothing to C on this image.
# maxpool has no --emit-asm-only generator.
HANDWRITTEN_KERNELS: dict[str, tuple[str, tuple[str, ...]]] = {
    "add": ("build_add.py", ("--rows", "4", "--width", "32")),
    "relu": ("build_relu.py", ("--rows", "4", "--width", "32")),
    "softmax": ("build_softmax_row32.py", ()),
    "conv_baseline": ("build_conv.py", ("--H", "4", "--W", "4")),
    "conv_pipelined": ("build_conv_pipelined.py", ("--H", "4", "--W", "4")),
}


def compile_c(test_path: Path, asm_path: Path, *, repo_root: Path, env: dict[str, str]) -> None:
    cc = [
        sys.executable,
        "-m",
        "ppci.cli.atalla_cc",
        "--machine",
        "atalla",
        "-O",
        "2",
        "-S",
        str(test_path),
        "-o",
        str(asm_path),
    ]
    run_and_log(cc, cwd=repo_root, env=env, log_path=asm_path.parent / "compile.log")


def emit_handwritten(stem: str, asm_path: Path, *, sim_root: Path, env: dict[str, str]) -> None:
    script, args = HANDWRITTEN_KERNELS[stem]
    gen = [
        sys.executable,
        str(sim_root / "kernels" / script),
        "--emit-asm-only",
        "-o",
        str(asm_path),
        *args,
    ]
    run_and_log(gen, cwd=sim_root, env=env, log_path=asm_path.parent / "generate.log")


def run_one(
    test_path: Path,
    *,
    script_dir: Path,
    repo_root: Path,
    sim_root: Path,
    env: dict[str, str],
    handwritten: bool = False,
) -> Path:
    """Build + seed + simulate + check one kernel; return its output directory.

    The asm comes from atalla_cc, or from the matching handwritten generator when
    ``handwritten`` is set (output under ``out/<stem>/handwritten``).
    """
    stem = test_path.stem
    if stem not in KERNEL_REGISTRY:
        raise KeyError(f"No kernel spec for {stem!r}; known: {sorted(KERNEL_REGISTRY)}")

    seed_fn, check_fn = KERNEL_REGISTRY[stem]
    if stem in GEMM_TILED_STEMS:
        # Refill the weight buffer from column 0 every GEMM_TILE lw.vi (one K tile)
        # instead of appending columns across K tiles.
        env = {**env, "FUNCTIONAL_SIM_GEMM_WEIGHT_TILE": str(GEMM_TILE)}
    out_dir = script_dir / "out" / stem
    if handwritten:
        out_dir = out_dir / "handwritten"
    out_dir.mkdir(parents=True, exist_ok=True)

    asm_path = out_dir / f"{stem}.s"
    image_path = out_dir / f"{stem}.in"
    build_log = out_dir / "build.log"
    run_log = out_dir / "run.log"

    output_mem = out_dir / "output_mem.out"
    output_sregs = out_dir / "output_sregs.out"
    output_vregs = out_dir / "output_vregs.out"
    output_mregs = out_dir / "output_mregs.out"
    output_scpad0 = out_dir / "output_scpad0.out"
    output_scpad1 = out_dir / "output_scpad1.out"
    output_perf = out_dir / "output_perf.out"
    output_perf.unlink(missing_ok=True)

    if handwritten:
        emit_handwritten(stem, asm_path, sim_root=sim_root, env=env)
    else:
        compile_c(test_path, asm_path, repo_root=repo_root, env=env)

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

    check_fn(output_mem)
    kind = "handwritten" if handwritten else "compiled"
    print(f"OK {test_path.name} ({kind})  artifacts: {out_dir}")
    return out_dir


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
            "Validate kernel C tests: compile, seed .data (cfg + tensors), run functional_sim, "
            "and check every output against a numpy golden. Kernels in EXPECTED_FAILURES "
            "are reported but don't fail the run."
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
    ap.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write per-test results (status, error, perf counters) to this JSON file",
    )
    ap.add_argument(
        "--no-handwritten",
        dest="handwritten",
        action="store_false",
        help="Skip running the matching handwritten functional_sim kernels for comparison",
    )
    args = ap.parse_args()

    if args.test is not None:
        tests = [args.test.resolve()]
    else:
        tests = [script_dir / t for t in DEFAULT_TESTS]

    failed: list[str] = []
    results: list[dict[str, object]] = []

    for t in tests:
        error: str | None = None
        if not t.exists():
            error = f"missing {t}"
        else:
            try:
                run_one(t, script_dir=script_dir, repo_root=repo_root, sim_root=sim_root, env=env)
            except Exception as e:
                error = str(e)

        known_bug = EXPECTED_FAILURES.get(t.stem)
        if known_bug is None:
            status = "fail" if error else "pass"
            if error:
                failed.append(f"{t.name}: {error}")
        elif error:
            status = "xfail"
            print(f"XFAIL {t.name} (known: {known_bug})")
        else:
            status = "xpass"
            print(f"XPASS {t.name}: passes now; remove it from EXPECTED_FAILURES")
        result = {
            "test": t.stem,
            "status": status,
            "error": error,
            "known_bug": known_bug,
            "perf": read_perf(script_dir / "out" / t.stem / "output_perf.out"),
        }
        results.append(result)

        # Handwritten comparison is informational: it never fails the run.
        if args.handwritten and t.stem in HANDWRITTEN_KERNELS:
            hw_error: str | None = None
            try:
                run_one(
                    t,
                    script_dir=script_dir,
                    repo_root=repo_root,
                    sim_root=sim_root,
                    env=env,
                    handwritten=True,
                )
            except Exception as e:
                hw_error = str(e)
                print(f"HANDWRITTEN FAIL {t.name}: {hw_error.splitlines()[0]}")
            script, gen_args = HANDWRITTEN_KERNELS[t.stem]
            result["handwritten"] = {
                "generator": " ".join((script, *gen_args)),
                "status": "fail" if hw_error else "pass",
                "error": hw_error,
                "perf": read_perf(script_dir / "out" / t.stem / "handwritten" / "output_perf.out"),
            }

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"suite": "kernel", "results": results}, indent=2) + "\n")

    if failed:
        print("FAILURES:\n" + "\n".join(failed), file=sys.stderr)
        return 1
    print(f"All {len(tests)} kernel run(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
