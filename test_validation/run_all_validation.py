#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import struct
import subprocess
import sys
from pathlib import Path


EXPECT_X10_RE = re.compile(r"EXPECT_X10:\s*([+-]?(?:0x[0-9A-Fa-f]+|\d+))")
INPUT_BASE_RE = re.compile(r"INPUT_GMEM_BASE:\s*([+-]?(?:0x[0-9A-Fa-f]+|\d+))")
INPUT_LANE0_RE = re.compile(r"INPUT_LANE0:\s*([+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)")
INPUT_OTHER_LANES_RE = re.compile(
    r"INPUT_OTHER_LANES:\s*([+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)"
)


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


def parse_required(regex: re.Pattern[str], text: str, *, key: str, test_path: Path) -> str:
    match = regex.search(text)
    if not match:
        raise RuntimeError(f"Could not find {key} in {test_path}")
    return match.group(1)


def is_vector_test(source_text: str) -> bool:
    return "INPUT_GMEM_BASE:" in source_text


def parse_test_metadata(test_path: Path) -> tuple[int, int | None, float | None, float | None]:
    text = test_path.read_text()
    expected_x10 = int(parse_required(EXPECT_X10_RE, text, key="EXPECT_X10", test_path=test_path), 0)

    if not is_vector_test(text):
        return expected_x10, None, None, None

    input_base = int(parse_required(INPUT_BASE_RE, text, key="INPUT_GMEM_BASE", test_path=test_path), 0)
    input_lane0 = float(parse_required(INPUT_LANE0_RE, text, key="INPUT_LANE0", test_path=test_path))
    input_other_lanes = float(
        parse_required(INPUT_OTHER_LANES_RE, text, key="INPUT_OTHER_LANES", test_path=test_path)
    )
    return expected_x10, input_base, input_lane0, input_other_lanes


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


def seed_vector_input(image_path: Path, *, input_base: int, input_lane0: float, input_other_lanes: float) -> None:
    input_vector = [input_lane0] + [input_other_lanes] * 31
    data_text = render_bf16_vector_data(input_base, input_vector)
    image_text = image_path.read_text().rstrip()
    image_path.write_text(image_text + "\n" + data_text + "\n")


def validate_test(test_path: Path, *, repo_root: Path, sim_root: Path, out_root: Path) -> Path:
    expected_x10, input_base, input_lane0, input_other_lanes = parse_test_metadata(test_path)
    out_dir = out_root / test_path.stem
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
    env["PYTHONPATH"] = build_pythonpath(sim_root, repo_root)

    run_and_log(
        [
            sys.executable,
            "-m",
            "ppci.cli.atalla_cc",
            "--machine",
            "atalla",
            "-S",
            "-p",
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
            str(sim_root / "build_compiler.py"),
            "-i",
            str(asm_path),
            "-o",
            str(image_path),
        ],
        cwd=sim_root,
        env=env,
        log_path=build_log,
    )

    if input_base is not None and input_lane0 is not None and input_other_lanes is not None:
        seed_vector_input(
            image_path,
            input_base=input_base,
            input_lane0=input_lane0,
            input_other_lanes=input_other_lanes,
        )

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

    observed_x10 = parse_x10(output_sregs)
    if observed_x10 != expected_x10:
        raise RuntimeError(
            f"x10 mismatch for {test_path.name}: expected {expected_x10} "
            f"(0x{expected_x10:08X}), observed {observed_x10} "
            f"(0x{observed_x10:08X}). See {output_sregs}"
        )

    return out_dir


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    sim_root = repo_root / "functional_sim"
    out_root = script_dir / "out"

    if not sim_root.is_dir():
        raise RuntimeError(f"Missing simulator dependency directory: {sim_root}")

    ap = argparse.ArgumentParser(
        description=(
            "Compile validation C tests, optionally seed vector GMEM input, run the "
            "functional simulator, and verify the final x10 result."
        )
    )
    ap.add_argument(
        "--match",
        default="*.c",
        help="Glob used to select validation C files (default: *.c)",
    )
    args = ap.parse_args()

    tests = sorted(
        path for path in script_dir.glob(args.match) if path.is_file() and path.suffix == ".c"
    )
    if not tests:
        raise RuntimeError(f"No validation tests matched {args.match!r} in {script_dir}")

    failures: list[tuple[Path, str]] = []
    for test_path in tests:
        try:
            out_dir = validate_test(
                test_path.resolve(),
                repo_root=repo_root,
                sim_root=sim_root,
                out_root=out_root,
            )
            print(f"PASS {test_path.name} -> {out_dir}")
        except Exception as exc:
            failures.append((test_path, str(exc)))
            print(f"FAIL {test_path.name}")

    if failures:
        print()
        for test_path, message in failures:
            print(f"--- {test_path.name} ---")
            print(message)
            print()
        return 1

    print()
    print(f"Validated {len(tests)} tests successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
