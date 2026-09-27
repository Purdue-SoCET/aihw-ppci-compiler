#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_TEST = "scalar_sum_loop.c"
EXPECT_X10_RE = re.compile(r"EXPECT_X10:\s*([+-]?(?:0x[0-9A-Fa-f]+|\d+))")


def run_and_log(cmd: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    log_path.write_text(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {proc.returncode}: {' '.join(cmd)}\n"
            f"See {log_path}"
        )


def parse_x10(sreg_path: Path) -> int:
    text = sreg_path.read_text()
    match = re.search(r"x10:\s+0x([0-9A-Fa-f]{8})", text)
    if not match:
        raise RuntimeError(f"Could not find x10 in {sreg_path}")
    return int(match.group(1), 16)


def parse_expected_x10_from_source(test_path: Path) -> int:
    text = test_path.read_text()
    match = EXPECT_X10_RE.search(text)
    if not match:
        raise RuntimeError(
            f"Could not find EXPECT_X10 in {test_path}. "
            "Add a comment like 'EXPECT_X10: 50' or pass --expect-x10."
        )
    return int(match.group(1), 0)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    ap = argparse.ArgumentParser(
        description="Compile a scalar validation C test, run build_compiler, then run functional_sim."
    )
    ap.add_argument(
        "--test",
        type=Path,
        default=script_dir / DEFAULT_TEST,
        help="Path to the C test file to validate",
    )
    ap.add_argument(
        "--expect-x10",
        type=lambda value: int(value, 0),
        default=None,
        help="Expected final value in x10; if omitted, read EXPECT_X10 from the C file comment",
    )
    args = ap.parse_args()

    test_path = args.test.resolve()
    if not test_path.exists():
        raise FileNotFoundError(f"Test file not found: {test_path}")

    out_dir = script_dir / "out" / test_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    asm_path = out_dir / f"{test_path.stem}.s"
    image_path = out_dir / f"{test_path.stem}.in"
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

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    run_and_log(
        [
            sys.executable,
            "-m",
            "ppci.cli.atalla_cc",
            "--machine",
            "atalla",
            "-S",
            str(test_path),
            "-o",
            str(asm_path),
        ],
        cwd=repo_root,
        env=env,
        log_path=compile_log,
    )

    run_and_log(
        [
            sys.executable,
            str(repo_root / "functional_sim" / "build_compiler.py"),
            "-i",
            str(asm_path),
            "-o",
            str(image_path),
        ],
        cwd=repo_root,
        env=env,
        log_path=build_log,
    )

    run_and_log(
        [
            sys.executable,
            "-m",
            "functional_sim.run",
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
        cwd=repo_root,
        env=env,
        log_path=run_log,
    )

    expected_x10 = args.expect_x10
    if expected_x10 is None:
        expected_x10 = parse_expected_x10_from_source(test_path)

    observed_x10 = parse_x10(output_sregs)
    if observed_x10 != expected_x10:
        raise RuntimeError(
            f"x10 mismatch for {test_path.name}: expected {expected_x10} "
            f"(0x{expected_x10:08X}), observed {observed_x10} "
            f"(0x{observed_x10:08X}). See {output_sregs}"
        )

    print(f"Validation passed for {test_path.name}")
    print(f"Expected x10: {expected_x10} (0x{expected_x10:08X})")
    print(f"Observed x10: {observed_x10} (0x{observed_x10:08X})")
    print(f"Artifacts: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
