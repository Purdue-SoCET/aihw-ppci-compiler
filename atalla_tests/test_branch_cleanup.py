"""Checks for the Atalla branch cleanup peephole and pc-relative relocations.

Run from the repo root:

    PYTHONPATH=. python3 atalla_tests/test_branch_cleanup.py

1. Relocation range: offsets just inside the signed imm10 / imm25 range
   encode to the same value the hardware decodes (sign extended, as in
   disassemble.py); offsets just outside are rejected instead of wrapping
   to a backward jump.
2. bigloop_inverted.c: the loop header branch is inverted (bge_s to the
   exit, no jal after it).
3. bigloop_guard.c: the loop exit is too far for an inverted imm10 branch,
   so the header keeps blt_s + jal.
4. No "jal x0, L" is directly followed by "L:" in any output.
"""

import os
import re
import subprocess
import sys
import tempfile

from ppci.arch.atalla.relocations import (
    ATALLA_INSN_ALIGNMENT,
    AtallaBR_Imm10_Relocation,
    AtallaMI_JAL_Imm25_Relocation,
)
from ppci.utils.bitfun import sign_extend

HERE = os.path.dirname(os.path.abspath(__file__))
failures = []


def check(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


def test_relocation_range():
    for cls, bits in (
        (AtallaBR_Imm10_Relocation, 10),
        (AtallaMI_JAL_Imm25_Relocation, 25),
    ):
        reloc = cls("sym")
        half = 1 << (bits - 1)
        for words in (-half, half - 1):
            enc = reloc.calc(1000 + words * ATALLA_INSN_ALIGNMENT, 1000)
            check(
                sign_extend(enc, bits) == words,
                f"{cls.name}: offset {words} round-trips",
            )
        for words in (half, -half - 1):
            try:
                reloc.calc(1000 + words * ATALLA_INSN_ALIGNMENT, 1000)
                check(False, f"{cls.name}: offset {words} rejected")
            except ValueError:
                check(True, f"{cls.name}: offset {words} rejected")


def compile_asm(name):
    """Compile with the same command atalla_cc uses and return the .s text."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.s")
        cmd = [sys.executable, "-m", "ppci", "atalla_cc", "-m", "atalla"]
        cmd += ["-O2", os.path.join(HERE, name), "-S", "-o", out]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(out) as f:
            return f.read()


def header_branches(asm):
    """Return the instruction lines of main_block2 (the loop header)."""
    block = asm.split("main_block2:")[1].split("main_block3:")[0]
    return [ln.strip() for ln in block.splitlines() if ln.strip()]


def no_jump_to_next_label(name, asm):
    lines = [ln.strip() for ln in asm.splitlines() if ln.strip()]
    for a, b in zip(lines, lines[1:]):
        m = re.match(r"jal x0, (\S+)$", a)
        if m and b == m.group(1) + ":":
            check(False, f"{name}: '{a}' is followed by its own label")
            return
    check(True, f"{name}: no jal to the next label")


def test_loops():
    asm = compile_asm("bigloop_inverted.c")
    hdr = header_branches(asm)
    check(
        any(ln.startswith("bge_s") and "main_block4" in ln for ln in hdr)
        and not any(ln.startswith("jal") for ln in hdr),
        "bigloop_inverted.c: header is a single bge_s to the exit",
    )
    no_jump_to_next_label("bigloop_inverted.c", asm)

    asm = compile_asm("bigloop_guard.c")
    hdr = header_branches(asm)
    check(
        any(ln.startswith("blt_s") and "main_block3" in ln for ln in hdr)
        and any(ln == "jal x0, main_block4" for ln in hdr),
        "bigloop_guard.c: far exit keeps blt_s + jal (not inverted)",
    )
    no_jump_to_next_label("bigloop_guard.c", asm)

    no_jump_to_next_label("forloop.c", compile_asm("forloop.c"))


if __name__ == "__main__":
    test_relocation_range()
    test_loops()
    print(f"\n{len(failures)} failure(s)")
    sys.exit(1 if failures else 0)
