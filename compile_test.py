#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

# RUN python3 compile_test.py vv_instr.c 
# Look at emulator/out folder for output files. The .in file is what was generated from the build file. 

REPO_ROOT = Path(__file__).resolve().parent
TEST_DIR_CANDIDATES = ("atalla_tests", "atalla_test")


def run_cmd(cmd: list[str], cwd: Path) -> None:
    print(f"[RUN] {shlex.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def resolve_source_path(source_arg: str) -> Path:
    provided = Path(source_arg)

    if provided.is_absolute() and provided.is_file():
        return provided

    direct = (REPO_ROOT / provided).resolve()
    if direct.is_file():
        return direct

    for test_dir in TEST_DIR_CANDIDATES:
        base = REPO_ROOT / test_dir
        candidate = (base / source_arg).resolve()
        if candidate.is_file():
            return candidate

        if Path(source_arg).suffix == "":
            with_ext = (base / f"{source_arg}.c").resolve()
            if with_ext.is_file():
                return with_ext

    raise FileNotFoundError(
        f"Could not find source '{source_arg}'. "
        f"Checked direct path and {', '.join(TEST_DIR_CANDIDATES)}."
    )


def rel_or_abs(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compile an Atalla C test, build emulator input, and run the emulator."
    )
    ap.add_argument(
        "source",
        help="Test source file (e.g. vv_instr.c). If not found directly, search under atalla_tests/.",
    )
    ap.add_argument(
        "--packet-length",
        type=int,
        default=4,
        help="Packet length passed to emulator/run.py (default: 4).",
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Enable emulator debug mode.",
    )
    ap.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip running verify_emulator_packets.py after emulator run.",
    )
    ap.add_argument(
        "--verify-smoke-run",
        action="store_true",
        help=(
            "Run verifier with its own emulator smoke run. "
            "By default verifier uses --skip-smoke-run since compile_test.py already runs emulator."
        ),
    )
    args = ap.parse_args()

    src_path = resolve_source_path(args.source)
    test_name = src_path.stem

    asm_out = REPO_ROOT / f"{test_name}.out"
    emulator_out_dir = REPO_ROOT / "emulator" / "out"
    emulator_out_dir.mkdir(parents=True, exist_ok=True)
    compiled_in = emulator_out_dir / f"{test_name}_compiled.in"

    mem_out = emulator_out_dir / f"{test_name}_output_mem.out"
    sreg_out = emulator_out_dir / f"{test_name}_output_sregs.out"
    vreg_out = emulator_out_dir / f"{test_name}_output_vregs.out"
    mreg_out = emulator_out_dir / f"{test_name}_output_mregs.out"
    scpad0_out = emulator_out_dir / f"{test_name}_output_scpad0.out"
    scpad1_out = emulator_out_dir / f"{test_name}_output_scpad1.out"
    verify_report = emulator_out_dir / f"{test_name}_verify_report.txt"

    src_for_make = rel_or_abs(src_path)
    asm_for_make = rel_or_abs(asm_out)

    try:
        run_cmd(
            [
                "make",
                "atalla-gen-asmfiles",
                f"SRC1={src_for_make}",
                f"OBJ3={asm_for_make}",
            ],
            cwd=REPO_ROOT,
        )

        run_cmd(
            [
                sys.executable,
                str(REPO_ROOT / "emulator" / "build_compiler.py"),
                "--input",
                str(asm_out),
                "--output",
                str(compiled_in),
            ],
            cwd=REPO_ROOT,
        )

        run_emulator_cmd = [
            sys.executable,
            str(REPO_ROOT / "emulator" / "run.py"),
            "--input_file",
            str(compiled_in),
            "--packet_length",
            str(args.packet_length),
            "--output_mem_file",
            str(mem_out),
            "--output_sreg_file",
            str(sreg_out),
            "--output_vreg_file",
            str(vreg_out),
            "--output_mreg_file",
            str(mreg_out),
            "--output_scpad_file0",
            str(scpad0_out),
            "--output_scpad_file1",
            str(scpad1_out),
        ]
        if args.debug:
            run_emulator_cmd.append("--debug")

        run_cmd(run_emulator_cmd, cwd=REPO_ROOT)

        if not args.no_verify:
            run_verify_cmd = [
                sys.executable,
                str(REPO_ROOT / "verify_emulator_packets.py"),
                "--asm",
                str(asm_out),
                "--compiled-in",
                str(compiled_in),
                "--packet-length",
                str(args.packet_length),
                "--report",
                str(verify_report),
            ]
            if not args.verify_smoke_run:
                run_verify_cmd.append("--skip-smoke-run")

            run_cmd(run_verify_cmd, cwd=REPO_ROOT)
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Command failed with exit code {exc.returncode}")
        return exc.returncode

    print("[OK] Pipeline completed.")
    print(f"[OK] Assembly output: {asm_out}")
    print(f"[OK] Emulator input: {compiled_in}")
    print(f"[OK] Emulator outputs: {emulator_out_dir}")
    if args.no_verify:
        print("[OK] Verifier skipped (--no-verify).")
    else:
        print(f"[OK] Verifier report: {verify_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
