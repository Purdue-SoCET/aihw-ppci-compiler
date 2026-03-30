#!/usr/bin/env python3
"""Compile AtallaC .c files to .s (compiler output) and .in (functional sim input).

Usage:
    python compile_and_convert.py <file.c>              # produces file.s and file.in
    python compile_and_convert.py <file.c> --s-only     # produces file.s only
    python compile_and_convert.py <file.c> --show-emu   # also print emulator asm

Pipeline: .c -> atalla_cc -> .s -> asm_converter -> build.assemble_file -> .in
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
COMPILER_ROOT = SCRIPT_DIR.parent
FUNC_SIM = COMPILER_ROOT.parent / "atalla-models" / "functional_sim"
ASM_CONVERTER = COMPILER_ROOT.parent / "atalla-models" / "atalla-graph" / "codegen" / "asm_converter.py"

sys.path.insert(0, str(FUNC_SIM))
sys.path.insert(0, str(ASM_CONVERTER.parent))


def compile_c(c_path: Path, s_path: Path) -> str:
    """Run atalla_cc on a .c file, return the .s text."""
    env = {**os.environ, "PYTHONPATH": str(COMPILER_ROOT)}
    cmd = [sys.executable, str(COMPILER_ROOT / "atalla_cc"),
           str(c_path), "-S", "-o", str(s_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(f"Compile failed:\n{r.stderr[-3000:]}", file=sys.stderr)
        sys.exit(1)
    return s_path.read_text()


def convert_to_emu_asm(compiler_asm: str) -> str:
    """Convert compiler .s output to emulator-compatible assembly text."""
    from asm_converter import convert
    return convert(compiler_asm)


def assemble_to_in(emu_asm: str) -> str:
    """Assemble emulator asm text into .in hex format (no data section)."""
    from build import assemble_file, emit_test_format, render_testfile
    instrs = assemble_file(emu_asm)
    instr_hex = emit_test_format(instrs)
    return render_testfile(instr_hex, "")


def main():
    parser = argparse.ArgumentParser(description="Compile AtallaC to .s and .in")
    parser.add_argument("cfile", help="Input .c file")
    parser.add_argument("--s-only", action="store_true", help="Only produce .s")
    parser.add_argument("--show-emu", action="store_true", help="Print emulator asm")
    args = parser.parse_args()

    c_path = Path(args.cfile).resolve()
    stem = c_path.stem
    out_dir = c_path.parent

    s_path = out_dir / f"{stem}.s"
    in_path = out_dir / f"{stem}.in"

    print(f"[1/3] Compiling {c_path.name} -> {s_path.name}")
    compiler_asm = compile_c(c_path, s_path)
    print(f"      wrote {s_path}")

    if args.s_only:
        return

    print(f"[2/3] Converting to emulator assembly")
    emu_asm = convert_to_emu_asm(compiler_asm)
    if args.show_emu:
        print("--- emulator asm ---")
        print(emu_asm)
        print("--- end ---")

    print(f"[3/3] Assembling to .in format -> {in_path.name}")
    try:
        in_text = assemble_to_in(emu_asm)
        in_path.write_text(in_text)
        print(f"      wrote {in_path}")
    except Exception as e:
        print(f"      assembly to .in failed: {e}", file=sys.stderr)
        emu_path = out_dir / f"{stem}.emu.s"
        emu_path.write_text(emu_asm)
        print(f"      saved emulator asm to {emu_path} for debugging")


if __name__ == "__main__":
    main()
