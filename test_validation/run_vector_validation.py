#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import struct
import subprocess
import sys
from pathlib import Path


DEFAULT_TEST = "vector_add_lane0.c"
EXPECT_X10_RE = re.compile(r"EXPECT_X10:\s*([+-]?(?:0x[0-9A-Fa-f]+|\d+))")
INPUT_BASE_RE = re.compile(r"INPUT_GMEM_BASE:\s*([+-]?(?:0x[0-9A-Fa-f]+|\d+))")
INPUT_LANE0_RE = re.compile(r"INPUT_LANE0:\s*([+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)")
INPUT_OTHER_LANES_RE = re.compile(
    r"INPUT_OTHER_LANES:\s*([+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)"
)


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


def _parse_required(regex: re.Pattern[str], text: str, *, key: str, test_path: Path) -> str:
    match = regex.search(text)
    if not match:
        raise RuntimeError(f"Could not find {key} in {test_path}")
    return match.group(1)


def parse_metadata(test_path: Path) -> tuple[int, int, float, float]:
    text = test_path.read_text()
    expect_x10 = int(_parse_required(EXPECT_X10_RE, text, key="EXPECT_X10", test_path=test_path), 0)
    input_base = int(_parse_required(INPUT_BASE_RE, text, key="INPUT_GMEM_BASE", test_path=test_path), 0)
    input_lane0 = float(_parse_required(INPUT_LANE0_RE, text, key="INPUT_LANE0", test_path=test_path))
    input_other_lanes = float(
        _parse_required(INPUT_OTHER_LANES_RE, text, key="INPUT_OTHER_LANES", test_path=test_path)
    )
    return expect_x10, input_base, input_lane0, input_other_lanes


def bf16_bits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", float(x)))[0] >> 16


def render_bf16_vector_data(base_addr: int, values: list[float]) -> str:
    lines: list[str] = []
    for lane in range(0, len(values), 2):
        low = bf16_bits(values[lane])
        high = bf16_bits(values[lane + 1]) if lane + 1 < len(values) else 0
        word = low | (high << 16)
        addr = base_addr + (lane // 2) * 4
        lines.append(f"{addr:08X}: {word:08X}")
    return "\n".join(lines)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    ap = argparse.ArgumentParser(
        description="Compile a vector validation C test, seed GMEM, run build_compiler, then run functional_sim."
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

    comment_expect_x10, input_base, input_lane0, input_other_lanes = parse_metadata(test_path)
    expected_x10 = args.expect_x10 if args.expect_x10 is not None else comment_expect_x10

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

    input_vector = [input_lane0] + [input_other_lanes] * 31
    data_text = render_bf16_vector_data(input_base, input_vector)
    image_text = image_path.read_text().rstrip()
    image_path.write_text(image_text + "\n" + data_text + "\n")

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
    print(f"Seeded input base: 0x{input_base:08X}")
    print(f"Artifacts: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
