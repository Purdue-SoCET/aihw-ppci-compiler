#!/usr/bin/env python3
"""Verify that atalla-graph kernel generators produce C code structurally
matching the reference .c files in this directory.

For each kernel where both a reference .c and a pipeline generator exist,
this script:
  1. Generates C from the pipeline's kernel generator with the reference params
  2. Normalizes both (strip comments, collapse whitespace)
  3. Compares structural elements (same asm instructions, same control flow)

Usage:
    python test_codegen_match.py           # run all
    python test_codegen_match.py relu      # run specific
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
MODELS_ROOT = SCRIPT_DIR.parent.parent.parent     # atalla-models/
GRAPH_DIR = MODELS_ROOT / "atalla-graph"

sys.path.insert(0, str(GRAPH_DIR))


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_c(src: str) -> str:
    """Strip comments, collapse whitespace, normalize to compare structure."""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
    src = re.sub(r'//[^\n]*', '', src)
    src = re.sub(r'#define\s+\w+\s+[^\n]*\n', '', src)
    lines = [l.strip() for l in src.splitlines() if l.strip()]
    return '\n'.join(lines)


def extract_asm_ops(src: str) -> List[str]:
    """Extract ordered list of asm instruction mnemonics from C source."""
    ops = re.findall(r'asm\s*\(\s*"(\w+)', src)
    return ops


def extract_builtins(src: str) -> List[str]:
    """Extract ordered list of builtin calls (vec_op_masked, make_mask, gemm)."""
    calls = re.findall(r'(vec_op_masked|make_mask|gemm)\s*\(', src)
    return calls


def extract_loops(src: str) -> List[str]:
    """Extract while-loop conditions."""
    return re.findall(r'while\s*\(([^)]+)\)', src)


def has_c_call(src: str, name: str) -> bool:
    """True if `name` appears as a function-like call in C source."""
    return bool(re.search(rf"\b{re.escape(name)}\s*\(", src))


# ---------------------------------------------------------------------------
# Kernel match definitions
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    name: str
    asm_match: bool
    builtins_match: bool
    loops_match: bool
    notes: str

    @property
    def passed(self) -> bool:
        return self.asm_match and self.builtins_match and self.loops_match


def _structural_compare(name: str, gen: str, ref: str) -> MatchResult:
    """Generic structural comparison: same asm instruction set, same builtins
    set, same number of loop nesting levels."""
    gen_ops_set = set(extract_asm_ops(gen))
    ref_ops_set = set(extract_asm_ops(ref))
    gen_builtins_set = set(extract_builtins(gen))
    ref_builtins_set = set(extract_builtins(ref))
    gen_loop_count = len(extract_loops(gen))
    ref_loop_count = len(extract_loops(ref))

    asm_ok = gen_ops_set == ref_ops_set
    builtins_ok = gen_builtins_set == ref_builtins_set
    loops_ok = gen_loop_count == ref_loop_count

    notes = []
    if not asm_ok:
        extra_gen = gen_ops_set - ref_ops_set
        extra_ref = ref_ops_set - gen_ops_set
        if extra_gen:
            notes.append(f"gen extra asm: {extra_gen}")
        if extra_ref:
            notes.append(f"ref extra asm: {extra_ref}")
    if not builtins_ok:
        notes.append(f"builtins: gen={gen_builtins_set} ref={ref_builtins_set}")
    if not loops_ok:
        notes.append(f"loops: gen={gen_loop_count} ref={ref_loop_count}")

    return MatchResult(
        name, asm_ok, builtins_ok, loops_ok,
        "; ".join(notes) if notes else "structural match",
    )


def _match_relu() -> MatchResult:
    """ReLU: generator adds an outer tile loop for multi-tile support.
    For 128 elements / 32 width = 4 rows in 1 tile, generator has 2 loops
    (tile + row) while reference has 1 (row only). Accept gen >= ref loops."""
    from kernels.relu import relu_c
    gen = relu_c(total=128, width=32)
    ref = (SCRIPT_DIR / "relu.c").read_text()
    r = _structural_compare("relu", gen, ref)
    gen_lc = len(extract_loops(gen))
    ref_lc = len(extract_loops(ref))
    if not r.loops_match and gen_lc >= ref_lc:
        r.loops_match = True
        r.notes = "structural match (gen has extra tile loop)"
    return r


def _match_softmax() -> MatchResult:
    from kernels.softmax import softmax_c
    gen = softmax_c(length=32)
    ref = (SCRIPT_DIR / "softmax.c").read_text()
    return _structural_compare("softmax", gen, ref)


def _match_maxpool() -> MatchResult:
    from kernels.maxpool import maxpool_c
    gen = maxpool_c(H=8, W=8, C=1, pool=2, stride=2)
    ref = (SCRIPT_DIR / "maxpool.c").read_text()
    return _structural_compare("maxpool", gen, ref)


def _match_gemm() -> MatchResult:
    """GEMM: Reference .c and generator differ in loop order / scratchpad layout.
    Both use C intrinsics (scpad_*, vector_*) for DMA/vreg, not asm("scpad_ld").
    Require shared inline asm for config (lw_s, li_s, halt), matching intrinsics,
    gemm() calls, and three nested tile loops."""
    from kernels.gemm import gemm_c
    gen = gemm_c(M=4, N=4, K=4)
    ref = (SCRIPT_DIR / "gemm_tiled.c").read_text()

    gen_builtins = extract_builtins(gen)
    ref_builtins = extract_builtins(ref)
    builtins_ok = "gemm" in gen_builtins and "gemm" in ref_builtins

    gen_loops = extract_loops(gen)
    ref_loops = extract_loops(ref)
    both_have_3_loops = len(gen_loops) >= 3 and len(ref_loops) >= 3

    gen_asm_set = set(extract_asm_ops(gen))
    ref_asm_set = set(extract_asm_ops(ref))
    shared_asm = gen_asm_set & ref_asm_set
    required_asm = {"lw_s", "li_s", "halt"}
    asm_tokens_ok = required_asm.issubset(shared_asm)

    intrinsic_names = (
        "scpad_load",
        "scpad_store",
        "vector_load",
        "vector_store",
        "load_weights",
    )
    gen_intr = all(has_c_call(gen, n) for n in intrinsic_names)
    ref_intr = all(has_c_call(ref, n) for n in intrinsic_names)
    intrinsics_ok = gen_intr and ref_intr

    asm_ok = asm_tokens_ok and intrinsics_ok

    notes_parts = []
    if not builtins_ok:
        notes_parts.append("missing gemm builtin")
    if not both_have_3_loops:
        notes_parts.append(f"loop count: gen={len(gen_loops)} ref={len(ref_loops)}")
    if not asm_tokens_ok:
        notes_parts.append(f"missing shared asm: {required_asm - shared_asm}")
    if not gen_intr:
        notes_parts.append("gen missing intrinsics")
    if not ref_intr:
        notes_parts.append("ref missing intrinsics")

    return MatchResult(
        "gemm",
        asm_match=asm_ok,
        builtins_match=builtins_ok,
        loops_match=both_have_3_loops,
        notes="; ".join(notes_parts) if notes_parts else "structural match",
    )


# ---------------------------------------------------------------------------
# Registry and main
# ---------------------------------------------------------------------------

KERNEL_MATCHES: Dict[str, Callable] = {
    "relu": _match_relu,
    "softmax": _match_softmax,
    "maxpool": _match_maxpool,
    "gemm": _match_gemm,
}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Test codegen matches reference .c")
    ap.add_argument("kernels", nargs="*", default=list(KERNEL_MATCHES.keys()))
    args = ap.parse_args()

    results: List[MatchResult] = []
    for name in args.kernels:
        if name not in KERNEL_MATCHES:
            print(f"Unknown: {name}. Available: {list(KERNEL_MATCHES.keys())}")
            continue
        print(f"\n{'='*60}")
        print(f"Matching: {name}")
        print(f"{'='*60}")
        try:
            r = KERNEL_MATCHES[name]()
            results.append(r)
            tag = "PASS" if r.passed else "FAIL"
            print(f"  asm_match:      {r.asm_match}")
            print(f"  builtins_match: {r.builtins_match}")
            print(f"  loops_match:    {r.loops_match}")
            print(f"  notes:          {r.notes}")
            print(f"  [{tag}]")
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append(MatchResult(name, False, False, False, str(e)))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(f"  [{tag}] {r.name:12s}  {r.notes}")
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
