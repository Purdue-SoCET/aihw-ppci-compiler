#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SEMANTIC_EXPECTED = {
    "bftest": {
        "sreg": {10: 0, 1: 24},
        "mreg": {},
    },
    "intrinsictest": {
        "sreg": {10: 0, 12: 3, 13: 6, 1: 24},
        "mreg": {1: 10},
    },
    "masktest": {
        "sreg": {10: 0, 1: 24},
        "mreg": {},
    },
    "sample": {
        "sreg": {10: 0, 1: 24},
        "mreg": {1: 10},
    },
    "vi_instr": {
        "sreg": {10: 0, 1: 24},
        "mreg": {},
    },
    "vs_instr": {
        "sreg": {10: 0, 11: 5, 1: 24},
        "mreg": {},
    },
    "vv_instr": {
        "sreg": {10: 0, 1: 24},
        "mreg": {1: 5},
    },
}


SNAPSHOT_EXPECTED = {
    "bftest": {
        "sregs": "721ac6114b4d4adf",
        "mregs": "cc7ff2d7a0e6d723",
        "mem": "5686839a9a7f0e93",
        "vregs": "17a4eccb2a2241d8",
        "sc0": "5314a7402f9768e5",
        "sc1": "5314a7402f9768e5",
    },
    "intrinsictest": {
        "sregs": "1aeda8bddad969af",
        "mregs": "d4a916eab8fd2c3d",
        "mem": "bf0ac57a1998c7ad",
        "vregs": "17a4eccb2a2241d8",
        "sc0": "4bb35cedd60e74e5",
        "sc1": "5314a7402f9768e5",
    },
    "masktest": {
        "sregs": "721ac6114b4d4adf",
        "mregs": "cc7ff2d7a0e6d723",
        "mem": "5d2cc16a95fe8da6",
        "vregs": "17a4eccb2a2241d8",
        "sc0": "ec91b31a36a50c40",
        "sc1": "5314a7402f9768e5",
    },
    "sample": {
        "sregs": "721ac6114b4d4adf",
        "mregs": "d4a916eab8fd2c3d",
        "mem": "4a7152b161dad7d7",
        "vregs": "bab26916d124b4ca",
        "sc0": "ec91b31a36a50c40",
        "sc1": "5314a7402f9768e5",
    },
    "vi_instr": {
        "sregs": "721ac6114b4d4adf",
        "mregs": "cc7ff2d7a0e6d723",
        "mem": "151480862bb6a224",
        "vregs": "17a4eccb2a2241d8",
        "sc0": "4bb35cedd60e74e5",
        "sc1": "5314a7402f9768e5",
    },
    "vs_instr": {
        "sregs": "de067fc3298a89e1",
        "mregs": "cc7ff2d7a0e6d723",
        "mem": "3fb29829c9bd2756",
        "vregs": "17a4eccb2a2241d8",
        "sc0": "4bb35cedd60e74e5",
        "sc1": "5314a7402f9768e5",
    },
    "vv_instr": {
        "sregs": "721ac6114b4d4adf",
        "mregs": "b3475c2da15928bd",
        "mem": "93f321e736e9400f",
        "vregs": "17a4eccb2a2241d8",
        "sc0": "4bb35cedd60e74e5",
        "sc1": "5314a7402f9768e5",
    },
}


REG_LINE_RE = re.compile(r"x\s*(\d+)\s*:\s*0x([0-9A-Fa-f]{8})")


class StepFailure(Exception):
    def __init__(self, step_name: str, returncode: int, log_file: Path):
        self.step_name = step_name
        self.returncode = returncode
        self.log_file = log_file
        super().__init__(f"{step_name} failed with exit code {returncode}")


def short_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def parse_reg_file(path: Path) -> dict[int, int]:
    regs: dict[int, int] = {}
    text = path.read_text()
    for match in REG_LINE_RE.finditer(text):
        reg = int(match.group(1))
        value = int(match.group(2), 16)
        regs[reg] = value
    return regs


def fmt_u32(value: int | None) -> str:
    if value is None:
        return "<missing>"
    return f"0x{(value & 0xFFFFFFFF):08X}"


def run_step(step_name: str, cmd: list[str], log_path: Path) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log_path.write_text(
        f"$ {subprocess.list2cmdline(cmd)}\n"
        f"\n[stdout]\n{proc.stdout}"
        f"\n[stderr]\n{proc.stderr}"
    )
    if proc.returncode != 0:
        raise StepFailure(step_name, proc.returncode, log_path)


def run_case(
    *,
    case_name: str,
    source_file: Path,
    work_dir: Path,
    build_compiler: Path,
    run_py: Path,
) -> tuple[bool, list[str]]:
    case_dir = work_dir / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    asm_file = case_dir / f"{case_name}.out"
    compiled_file = case_dir / f"{case_name}_compiled.in"
    output_files = {
        "mem": case_dir / f"{case_name}_output_mem.out",
        "sregs": case_dir / f"{case_name}_output_sregs.out",
        "vregs": case_dir / f"{case_name}_output_vregs.out",
        "mregs": case_dir / f"{case_name}_output_mregs.out",
        "sc0": case_dir / f"{case_name}_output_scpad0.out",
        "sc1": case_dir / f"{case_name}_output_scpad1.out",
    }

    try:
        run_step(
            "compile_c_to_out",
            [
                sys.executable,
                "-m",
                "ppci",
                "atalla_cc",
                str(source_file),
                "-m",
                "atalla",
                "-O2",
                "-S",
                "-o",
                str(asm_file),
            ],
            case_dir / "step_compile.log",
        )
        run_step(
            "build_compiler",
            [
                sys.executable,
                str(build_compiler),
                "-i",
                str(asm_file),
                "-o",
                str(compiled_file),
            ],
            case_dir / "step_build.log",
        )
        run_step(
            "emulator",
            [
                sys.executable,
                str(run_py),
                "--input_file",
                str(compiled_file),
                "--output_mem_file",
                str(output_files["mem"]),
                "--output_sreg_file",
                str(output_files["sregs"]),
                "--output_vreg_file",
                str(output_files["vregs"]),
                "--output_mreg_file",
                str(output_files["mregs"]),
                "--output_scpad_file0",
                str(output_files["sc0"]),
                "--output_scpad_file1",
                str(output_files["sc1"]),
            ],
            case_dir / "step_emulator.log",
        )
    except StepFailure as err:
        return False, [
            f"step `{err.step_name}` failed with exit code {err.returncode}",
            f"see log: {err.log_file}",
        ]

    errors: list[str] = []

    sregs = parse_reg_file(output_files["sregs"])
    mregs = parse_reg_file(output_files["mregs"])

    semantic = SEMANTIC_EXPECTED[case_name]
    for reg, expected_value in semantic["sreg"].items():
        actual_value = sregs.get(reg)
        if actual_value != expected_value:
            errors.append(
                f"sreg[x{reg}] expected {fmt_u32(expected_value)} got {fmt_u32(actual_value)}"
            )
    for reg, expected_value in semantic["mreg"].items():
        actual_value = mregs.get(reg)
        if actual_value != expected_value:
            errors.append(
                f"mreg[x{reg}] expected {fmt_u32(expected_value)} got {fmt_u32(actual_value)}"
            )

    snapshot_actual = {name: short_hash(path) for name, path in output_files.items()}
    snapshot_expected = SNAPSHOT_EXPECTED[case_name]
    for name, expected_hash in snapshot_expected.items():
        actual_hash = snapshot_actual[name]
        if actual_hash != expected_hash:
            errors.append(
                f"snapshot[{name}] expected {expected_hash} got {actual_hash}"
            )

    return len(errors) == 0, errors


def discover_cases(tests_dir: Path) -> list[str]:
    cases = []
    for path in sorted(tests_dir.glob("*.c")):
        if "instructtest" in path.name:
            continue
        cases.append(path.stem)
    return cases


def resolve_selected_cases(all_cases: list[str], requested_cases: list[str] | None) -> list[str]:
    if not requested_cases:
        return all_cases

    requested = []
    unknown = []
    for name in requested_cases:
        normalized = Path(name).stem
        if normalized not in all_cases:
            unknown.append(name)
        elif normalized not in requested:
            requested.append(normalized)

    if unknown:
        raise ValueError(
            "Unknown case(s): "
            + ", ".join(unknown)
            + ". Available cases: "
            + ", ".join(all_cases)
        )

    return requested


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Atalla assembly generation + emulator outputs for atalla_tests (except instructtest)."
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Case name to run (repeatable), e.g. --case bftest",
    )
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep per-case artifact directory even on success.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    tests_dir = repo_root / "atalla_tests"
    emulator_dir = repo_root / "emulator copy 2"
    build_compiler = emulator_dir / "build_compiler.py"
    run_py = emulator_dir / "run.py"

    all_cases = discover_cases(tests_dir)
    selected_cases = resolve_selected_cases(all_cases, args.case)

    work_dir = Path(tempfile.mkdtemp(prefix="verify_atalla_tests_"))
    print(f"[INFO] artifact directory: {work_dir}")
    print(f"[INFO] running {len(selected_cases)} case(s): {', '.join(selected_cases)}")

    failed_cases: list[tuple[str, list[str]]] = []

    for case_name in selected_cases:
        source_file = tests_dir / f"{case_name}.c"
        ok, errors = run_case(
            case_name=case_name,
            source_file=source_file,
            work_dir=work_dir,
            build_compiler=build_compiler,
            run_py=run_py,
        )
        if ok:
            print(f"[PASS] {case_name}")
        else:
            print(f"[FAIL] {case_name}")
            failed_cases.append((case_name, errors))

    if failed_cases:
        print("\n[SUMMARY] failures detected:")
        for case_name, errors in failed_cases:
            print(f"- {case_name}")
            for err in errors:
                print(f"  - {err}")
        print(f"\n[INFO] kept artifacts at: {work_dir}")
        return 1

    print("\n[SUMMARY] all selected cases passed")
    if args.keep_artifacts:
        print(f"[INFO] kept artifacts at: {work_dir}")
    else:
        shutil.rmtree(work_dir, ignore_errors=True)
        print("[INFO] removed artifact directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
