#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str]) -> None:
    print("[RUN]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    emulator_dir = repo_root / "emulator copy 2"
    out_dir = emulator_dir / "out"
    input_file = repo_root / "f.out"
    compiled_file = out_dir / "f_compiled.in"

    if not input_file.exists():
        raise FileNotFoundError(f"Missing input file: {input_file}")

    out_dir.mkdir(parents=True, exist_ok=True)

    run_cmd(
        [
            sys.executable,
            str(emulator_dir / "build_compiler.py"),
            "-i",
            str(input_file),
            "-o",
            str(compiled_file),
        ]
    )

    run_cmd(
        [
            sys.executable,
            str(emulator_dir / "run.py"),
            "--input_file",
            str(compiled_file),
            "--output_mem_file",
            str(out_dir / "f_output_mem.out"),
            "--output_sreg_file",
            str(out_dir / "f_output_sregs.out"),
            "--output_vreg_file",
            str(out_dir / "f_output_vregs.out"),
            "--output_mreg_file",
            str(out_dir / "f_output_mregs.out"),
            "--output_scpad_file0",
            str(out_dir / "f_output_scpad0.out"),
            "--output_scpad_file1",
            str(out_dir / "f_output_scpad1.out"),
        ]
    )

    print("[DONE] Built and emulated f.out")


if __name__ == "__main__":
    main()
