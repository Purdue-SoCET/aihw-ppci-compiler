#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent
EMULATOR_DIR = REPO_ROOT / "emulator"
if str(EMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(EMULATOR_DIR))

from instruction_latency import latency as LATENCY_MAP  # type: ignore  # noqa: E402
from src.components.decode import decode_instruction  # type: ignore  # noqa: E402


REQUIRED_PACKET_WIDTH = 4
TAIL_LINES = 40

MEMORY_MNEMONICS = {
    "lw.s",
    "sw.s",
    "lhw.s",
    "shw.s",
    "vreg.ld",
    "vreg.st",
    "scpad.ld",
    "scpad.st",
}

MEMORY_STORE_MNEMONICS = {"sw.s", "shw.s", "vreg.st", "scpad.st"}
VECTOR_TYPES = {"VV", "VI", "VS", "VM", "VTS", "MVV", "MVS"}


@dataclass
class PacketLine:
    packet_idx: int
    line_no: int
    addr: int
    words: list[str]
    comment: str


@dataclass
class DecodedInstruction:
    packet_idx: int
    packet_addr: int
    slot_idx: int
    raw_word: str
    mnemonic: str
    instr_type: str
    reads: set[str]
    writes: set[str]
    latency: int
    is_memory: bool
    is_vector: bool
    mem_key: tuple | None


@dataclass
class StepResult:
    name: str
    command: list[str]
    return_code: int | None
    stdout: str
    stderr: str
    skipped: bool = False
    note: str = ""

    @property
    def passed(self) -> bool:
        return (not self.skipped) and self.return_code == 0


def resolve_asm_path(asm_arg: str) -> Path:
    candidate = Path(asm_arg)
    if candidate.is_absolute() and candidate.is_file():
        return candidate

    direct = (REPO_ROOT / candidate).resolve()
    if direct.is_file():
        return direct

    raise FileNotFoundError(f"Assembly file not found: {asm_arg}")


def resolve_report_path(report_arg: str | None, asm_arg: str, out_dir: Path) -> Path:
    if report_arg:
        p = Path(report_arg)
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()
    return (out_dir / f"{Path(asm_arg).stem}_verify_report.txt").resolve()


def resolve_compiled_path(compiled_arg: str | None, asm_path: Path, out_dir: Path) -> Path:
    if compiled_arg:
        p = Path(compiled_arg)
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()
    return (out_dir / f"{asm_path.stem}_compiled.in").resolve()


def run_step(name: str, command: list[str], cwd: Path, timeout_s: int = 300) -> StepResult:
    try:
        cp = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        return StepResult(
            name=name,
            command=command,
            return_code=cp.returncode,
            stdout=cp.stdout or "",
            stderr=cp.stderr or "",
        )
    except subprocess.TimeoutExpired as exc:
        return StepResult(
            name=name,
            command=command,
            return_code=124,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
            note=f"Timed out after {timeout_s} seconds.",
        )


def _to_int(decoded: dict, key: str) -> int | None:
    value = decoded.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _reg_scalar(reg: int | None) -> str | None:
    return f"s{reg}" if reg is not None else None


def _reg_vector(reg: int | None) -> str | None:
    return f"v{reg}" if reg is not None else None


def _reg_mask(reg: int | None) -> str | None:
    return f"m{reg}" if reg is not None else None


def _latency_for(mnemonic: str) -> int:
    m = mnemonic.lower()
    base = m.split(".", 1)[0]
    for key in (m, base):
        if key in LATENCY_MAP:
            try:
                return max(1, int(LATENCY_MAP[key]))
            except (TypeError, ValueError):
                pass
    return 1


def _extract_metadata(decoded: dict, mnemonic: str, instr_type: str) -> tuple[set[str], set[str], tuple | None]:
    reads: set[str] = set()
    writes: set[str] = set()
    mem_key = None

    def add_read(reg: str | None) -> None:
        if reg is not None:
            reads.add(reg)

    def add_write(reg: str | None) -> None:
        if reg is not None:
            writes.add(reg)

    m = mnemonic.lower()
    t = instr_type

    if t == "R":
        add_read(_reg_scalar(_to_int(decoded, "rs1")))
        add_read(_reg_scalar(_to_int(decoded, "rs2")))
        add_write(_reg_scalar(_to_int(decoded, "rd")))

    elif t == "I":
        add_read(_reg_scalar(_to_int(decoded, "rs1")))
        add_write(_reg_scalar(_to_int(decoded, "rd")))

    elif t == "BR":
        rs1 = _to_int(decoded, "rs1")
        add_read(_reg_scalar(rs1))
        add_read(_reg_scalar(_to_int(decoded, "rs2")))
        add_write(_reg_scalar(rs1))

    elif t == "M":
        rd = _to_int(decoded, "rd")
        rs1 = _to_int(decoded, "rs1")
        imm = _to_int(decoded, "imm")
        add_read(_reg_scalar(rs1))
        mem_key = ("scalar_mem", rs1, imm)
        if m in {"sw.s", "shw.s"}:
            add_read(_reg_scalar(rd))
        else:
            add_write(_reg_scalar(rd))

    elif t == "MI":
        rd = _to_int(decoded, "rd")
        if m == "jal":
            if rd not in (None, 0):
                add_write(_reg_scalar(rd))
        elif m in {"li.s", "lui.s"}:
            add_write(_reg_scalar(rd))

    elif t == "VV":
        add_read(_reg_vector(_to_int(decoded, "vs1")))
        add_read(_reg_vector(_to_int(decoded, "vs2")))
        add_read(_reg_mask(_to_int(decoded, "mask")))
        add_write(_reg_vector(_to_int(decoded, "vd")))

    elif t == "VS":
        add_read(_reg_vector(_to_int(decoded, "vs1")))
        add_read(_reg_scalar(_to_int(decoded, "rs1")))
        add_read(_reg_mask(_to_int(decoded, "mask")))
        add_write(_reg_vector(_to_int(decoded, "vd")))

    elif t == "VI":
        add_read(_reg_vector(_to_int(decoded, "vs1")))
        if m != "lw.vi":
            add_read(_reg_mask(_to_int(decoded, "mask")))
            add_write(_reg_vector(_to_int(decoded, "vd")))

    elif t == "VM":
        vd = _to_int(decoded, "vd")
        rs1 = _to_int(decoded, "rs1")
        sid = _to_int(decoded, "sid")
        num_cols = _to_int(decoded, "num_cols")
        num_rows = _to_int(decoded, "num_rows")
        rc = _to_int(decoded, "rc")
        rc_id = _to_int(decoded, "rc_id")
        mem_key = ("vreg_mem", sid, rs1, num_cols, num_rows, rc, rc_id)

        add_read(_reg_scalar(rs1))
        if m == "vreg.st":
            add_read(_reg_vector(vd))
        else:
            add_write(_reg_vector(vd))

    elif t == "SDMA":
        rs1_rd1 = _to_int(decoded, "rs1/rd1")
        rs2 = _to_int(decoded, "rs2")
        sid = _to_int(decoded, "sid")
        num_cols = _to_int(decoded, "num_cols")
        num_rows = _to_int(decoded, "num_rows")
        add_read(_reg_scalar(rs1_rd1))
        add_read(_reg_scalar(rs2))
        mem_key = ("scpad_mem", sid, rs1_rd1, rs2, num_cols, num_rows)

    elif t == "MTS":
        add_read(_reg_mask(_to_int(decoded, "vms")))
        add_write(_reg_scalar(_to_int(decoded, "rd")))

    elif t == "STM":
        add_read(_reg_scalar(_to_int(decoded, "rs1")))
        add_write(_reg_mask(_to_int(decoded, "vmd")))

    elif t == "VTS":
        add_read(_reg_vector(_to_int(decoded, "vs1")))
        add_write(_reg_scalar(_to_int(decoded, "rd")))

    elif t == "MVV":
        add_read(_reg_vector(_to_int(decoded, "vs1")))
        add_read(_reg_vector(_to_int(decoded, "vs2")))
        add_read(_reg_mask(_to_int(decoded, "mask")))
        add_write(_reg_mask(_to_int(decoded, "vmd")))

    elif t == "MVS":
        add_read(_reg_vector(_to_int(decoded, "vs1")))
        add_read(_reg_scalar(_to_int(decoded, "rs1")))
        add_read(_reg_mask(_to_int(decoded, "mask")))
        add_write(_reg_mask(_to_int(decoded, "vmd")))

    return reads, writes, mem_key


def parse_compiled_packets(compiled_path: Path) -> tuple[list[PacketLine], list[str]]:
    packets: list[PacketLine] = []
    errors: list[str] = []
    in_instr = True

    for line_no, raw_line in enumerate(compiled_path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if line.lower().startswith(".data"):
            in_instr = False
            continue
        if not in_instr:
            continue

        comment = ""
        if "#" in line:
            line, comment = line.split("#", 1)
            line = line.strip()
            comment = comment.strip()

        if not line:
            continue

        if ":" not in line:
            errors.append(f"Line {line_no}: missing ':' separator in instruction line.")
            continue

        addr_str, data_str = line.split(":", 1)
        addr_str = addr_str.strip()
        data_str = data_str.strip()

        try:
            addr = int(addr_str, 16)
        except ValueError:
            errors.append(f"Line {line_no}: invalid address '{addr_str}'.")
            continue

        words = data_str.split()
        if not words:
            errors.append(f"Line {line_no}: no instruction words found for packet at 0x{addr:08X}.")
            continue

        packets.append(
            PacketLine(
                packet_idx=len(packets),
                line_no=line_no,
                addr=addr,
                words=words,
                comment=comment,
            )
        )

    return packets, errors


def decode_packets(packets: Iterable[PacketLine]) -> tuple[list[list[DecodedInstruction]], list[str]]:
    all_decoded: list[list[DecodedInstruction]] = []
    errors: list[str] = []

    for packet in packets:
        packet_decoded: list[DecodedInstruction] = []
        for slot_idx, word in enumerate(packet.words):
            try:
                raw = int(word, 16)
            except ValueError:
                errors.append(
                    f"Line {packet.line_no} packet {packet.packet_idx} addr 0x{packet.addr:08X} "
                    f"slot {slot_idx}: invalid hex word '{word}'."
                )
                continue

            if raw.bit_length() > 48:
                errors.append(
                    f"Line {packet.line_no} packet {packet.packet_idx} addr 0x{packet.addr:08X} "
                    f"slot {slot_idx}: word '{word}' exceeds 48 bits."
                )
                continue

            decoded = decode_instruction(raw)
            mnemonic = str(decoded.get("mnemonic", "unknown")).lower()
            instr_type = str(decoded.get("type", "UNKNOWN")).upper()
            reads, writes, mem_key = _extract_metadata(decoded, mnemonic, instr_type)

            packet_decoded.append(
                DecodedInstruction(
                    packet_idx=packet.packet_idx,
                    packet_addr=packet.addr,
                    slot_idx=slot_idx,
                    raw_word=word,
                    mnemonic=mnemonic,
                    instr_type=instr_type,
                    reads=reads,
                    writes=writes,
                    latency=_latency_for(mnemonic),
                    is_memory=(mnemonic in MEMORY_MNEMONICS),
                    is_vector=(instr_type in VECTOR_TYPES),
                    mem_key=mem_key,
                )
            )

        all_decoded.append(packet_decoded)

    return all_decoded, errors


def _fmt_loc(inst: DecodedInstruction) -> str:
    return (
        f"packet={inst.packet_idx} addr=0x{inst.packet_addr:08X} "
        f"slot={inst.slot_idx} mnemonic={inst.mnemonic}"
    )


def check_intra_packet_hazards(decoded_packets: list[list[DecodedInstruction]]) -> list[str]:
    findings: list[str] = []

    for packet in decoded_packets:
        seen_reads: set[str] = set()
        seen_writes: set[str] = set()
        for inst in packet:
            if inst.mnemonic == "nop.s":
                continue

            for reg in sorted(inst.reads):
                if reg in seen_writes:
                    findings.append(f"{_fmt_loc(inst)} RAW hazard on register '{reg}'.")

            for reg in sorted(inst.writes):
                if reg in seen_reads:
                    findings.append(f"{_fmt_loc(inst)} WAR hazard on register '{reg}'.")
                if reg in seen_writes:
                    findings.append(f"{_fmt_loc(inst)} WAW hazard on register '{reg}'.")

            seen_reads.update(inst.reads)
            seen_writes.update(inst.writes)

    return findings


def check_inter_packet_hazards(decoded_packets: list[list[DecodedInstruction]]) -> list[str]:
    findings: list[str] = []
    reg_ready: dict[str, int] = {}
    store_ready: dict[tuple, int] = {}

    for cycle, packet in enumerate(decoded_packets):
        for inst in packet:
            if inst.mnemonic == "nop.s":
                continue

            for reg in sorted(inst.reads):
                ready_cycle = reg_ready.get(reg, 0)
                if cycle < ready_cycle:
                    findings.append(
                        f"{_fmt_loc(inst)} inter-packet RAW hazard on '{reg}' "
                        f"(consumer cycle={cycle}, producer ready={ready_cycle})."
                    )

            if inst.is_memory and inst.mem_key is not None:
                mem_ready = store_ready.get(inst.mem_key, 0)
                if cycle < mem_ready:
                    findings.append(
                        f"{_fmt_loc(inst)} memory dependency hazard on key={inst.mem_key} "
                        f"(consumer cycle={cycle}, store ready={mem_ready})."
                    )

        for inst in packet:
            if inst.mnemonic == "nop.s":
                continue

            ready_cycle = cycle + inst.latency
            for reg in inst.writes:
                current = reg_ready.get(reg, 0)
                if ready_cycle > current:
                    reg_ready[reg] = ready_cycle

            if inst.is_memory and inst.mem_key is not None and inst.mnemonic in MEMORY_STORE_MNEMONICS:
                current = store_ready.get(inst.mem_key, 0)
                if ready_cycle > current:
                    store_ready[inst.mem_key] = ready_cycle

    return findings


def _tail(text: str, limit: int = TAIL_LINES) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-limit:]) if lines else ""


def _format_step(step: StepResult) -> list[str]:
    lines: list[str] = [f"- {step.name}"]
    lines.append(f"  command: {shlex.join(step.command)}")
    if step.skipped:
        lines.append("  status: SKIPPED")
        if step.note:
            lines.append(f"  note: {step.note}")
        return lines

    lines.append(f"  status: {'PASS' if step.passed else 'FAIL'}")
    lines.append(f"  return_code: {step.return_code}")
    if step.note:
        lines.append(f"  note: {step.note}")

    stdout_tail = _tail(step.stdout)
    stderr_tail = _tail(step.stderr)
    if stdout_tail:
        lines.append("  stdout_tail:")
        lines.extend([f"    {line}" for line in stdout_tail.splitlines()])
    if stderr_tail:
        lines.append("  stderr_tail:")
        lines.extend([f"    {line}" for line in stderr_tail.splitlines()])
    return lines


def _format_findings(name: str, findings: list[str]) -> list[str]:
    lines = [f"{name}: {len(findings)}"]
    if findings:
        lines.extend([f"  - {entry}" for entry in findings])
    return lines


def render_report(
    asm_path: Path | None,
    compiled_path: Path,
    report_path: Path,
    packet_length: int,
    build_step: StepResult,
    smoke_step: StepResult,
    config_findings: list[str],
    parse_findings: list[str],
    width_findings: list[str],
    vector_findings: list[str],
    memory_findings: list[str],
    intra_findings: list[str],
    inter_findings: list[str],
    total_packets: int,
    total_noop_slots: int,
    packets_with_noops: int,
    overall_pass: bool,
) -> str:
    now = dt.datetime.now().isoformat(timespec="seconds")
    lines: list[str] = []

    lines.append("Packetized Emulator Verification Report")
    lines.append(f"Generated: {now}")
    lines.append(f"ASM file: {asm_path if asm_path is not None else 'N/A'}")
    lines.append(f"Compiled input: {compiled_path}")
    lines.append(f"Report file: {report_path}")
    lines.append(f"Packet length argument: {packet_length}")
    lines.append(f"Required packet width: {REQUIRED_PACKET_WIDTH}")
    lines.append("")

    lines.append("Pipeline Steps")
    lines.extend(_format_step(build_step))
    lines.extend(_format_step(smoke_step))
    lines.append("")

    lines.append("Summary")
    lines.append(f"- Overall result: {'PASS' if overall_pass else 'FAIL'}")
    lines.append(f"- Total packets: {total_packets}")
    lines.append(f"- Total noop slots: {total_noop_slots}")
    lines.append(f"- Packets containing noop(s): {packets_with_noops}")
    lines.append("")

    lines.append("Rule Stats")
    lines.extend(_format_findings("Configuration findings", config_findings))
    lines.extend(_format_findings("Parse findings", parse_findings))
    lines.extend(_format_findings("Packet width violations", width_findings))
    lines.extend(_format_findings("Vector-per-packet violations", vector_findings))
    lines.extend(_format_findings("Memory-per-packet violations", memory_findings))
    lines.extend(_format_findings("Intra-packet hazard violations", intra_findings))
    lines.extend(_format_findings("Inter-packet hazard violations", inter_findings))
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile assembly to emulator packet input, smoke-run emulator, and verify "
            "packet structural/hazard correctness."
        )
    )
    parser.add_argument("--asm", required=True, help="Input assembly file (.s/.asm).")
    parser.add_argument(
        "--compiled-in",
        default=None,
        help="Optional path for generated compiled .in file (default: emulator/out/<stem>_compiled.in).",
    )
    parser.add_argument(
        "--packet-length",
        type=int,
        default=REQUIRED_PACKET_WIDTH,
        help=f"Packet length passed to emulator/run.py (default: {REQUIRED_PACKET_WIDTH}).",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Output text report path (default: emulator/out/<stem>_verify_report.txt).",
    )
    parser.add_argument(
        "--skip-smoke-run",
        action="store_true",
        help="Skip running emulator smoke test.",
    )
    args = parser.parse_args()

    out_dir = (REPO_ROOT / "emulator" / "out").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = resolve_report_path(args.report, args.asm, out_dir)

    config_findings: list[str] = []
    parse_findings: list[str] = []
    width_findings: list[str] = []
    vector_findings: list[str] = []
    memory_findings: list[str] = []
    intra_findings: list[str] = []
    inter_findings: list[str] = []

    if args.packet_length != REQUIRED_PACKET_WIDTH:
        config_findings.append(
            f"Packet length argument is {args.packet_length}, but pass criteria requires {REQUIRED_PACKET_WIDTH}."
        )

    asm_path: Path | None = None
    build_step = StepResult(
        name="build_compiler",
        command=[],
        return_code=None,
        stdout="",
        stderr="",
        skipped=True,
        note="Build step not started.",
    )
    smoke_step = StepResult(
        name="emulator_smoke_run",
        command=[],
        return_code=None,
        stdout="",
        stderr="",
        skipped=True,
        note="Smoke run not started.",
    )

    total_packets = 0
    total_noop_slots = 0
    packets_with_noops = 0

    try:
        asm_path = resolve_asm_path(args.asm)
    except FileNotFoundError as exc:
        config_findings.append(str(exc))
        compiled_path = resolve_compiled_path(args.compiled_in, Path(args.asm), out_dir)
        overall_fail = True
        report_text = render_report(
            asm_path=asm_path,
            compiled_path=compiled_path,
            report_path=report_path,
            packet_length=args.packet_length,
            build_step=build_step,
            smoke_step=smoke_step,
            config_findings=config_findings,
            parse_findings=parse_findings,
            width_findings=width_findings,
            vector_findings=vector_findings,
            memory_findings=memory_findings,
            intra_findings=intra_findings,
            inter_findings=inter_findings,
            total_packets=total_packets,
            total_noop_slots=total_noop_slots,
            packets_with_noops=packets_with_noops,
            overall_pass=(not overall_fail),
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text)
        print(f"[FAIL] Verification failed. Report: {report_path}")
        return 1

    compiled_path = resolve_compiled_path(args.compiled_in, asm_path, out_dir)

    build_cmd = [
        sys.executable,
        str(REPO_ROOT / "emulator" / "build_compiler.py"),
        "--input",
        str(asm_path),
        "--output",
        str(compiled_path),
    ]
    build_step = run_step("build_compiler", build_cmd, REPO_ROOT)

    if build_step.passed:
        if args.skip_smoke_run:
            smoke_step = StepResult(
                name="emulator_smoke_run",
                command=[],
                return_code=None,
                stdout="",
                stderr="",
                skipped=True,
                note="Skipped by --skip-smoke-run.",
            )
        else:
            stem = compiled_path.stem.replace("_compiled", "")
            mem_out = out_dir / f"{stem}_verify_output_mem.out"
            sreg_out = out_dir / f"{stem}_verify_output_sregs.out"
            vreg_out = out_dir / f"{stem}_verify_output_vregs.out"
            mreg_out = out_dir / f"{stem}_verify_output_mregs.out"
            scpad0_out = out_dir / f"{stem}_verify_output_scpad0.out"
            scpad1_out = out_dir / f"{stem}_verify_output_scpad1.out"

            smoke_cmd = [
                sys.executable,
                str(REPO_ROOT / "emulator" / "run.py"),
                "--input_file",
                str(compiled_path),
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
            smoke_step = run_step("emulator_smoke_run", smoke_cmd, REPO_ROOT)
    else:
        smoke_step = StepResult(
            name="emulator_smoke_run",
            command=[],
            return_code=None,
            stdout="",
            stderr="",
            skipped=True,
            note="Skipped because build_compiler step failed.",
        )

    decoded_packets: list[list[DecodedInstruction]] = []
    if build_step.passed and compiled_path.is_file():
        packet_lines, parse_errors = parse_compiled_packets(compiled_path)
        parse_findings.extend(parse_errors)
        decoded_packets, decode_errors = decode_packets(packet_lines)
        parse_findings.extend(decode_errors)

        total_packets = len(packet_lines)

        for packet, decoded in zip(packet_lines, decoded_packets):
            if len(packet.words) != REQUIRED_PACKET_WIDTH:
                width_findings.append(
                    f"packet={packet.packet_idx} addr=0x{packet.addr:08X} "
                    f"has width={len(packet.words)} (expected {REQUIRED_PACKET_WIDTH})."
                )

            vector_count = sum(1 for inst in decoded if inst.mnemonic != "nop.s" and inst.is_vector)
            if vector_count > 1:
                vector_findings.append(
                    f"packet={packet.packet_idx} addr=0x{packet.addr:08X} has {vector_count} vector instructions."
                )

            memory_count = sum(1 for inst in decoded if inst.mnemonic != "nop.s" and inst.is_memory)
            if memory_count > 1:
                memory_findings.append(
                    f"packet={packet.packet_idx} addr=0x{packet.addr:08X} has {memory_count} memory instructions."
                )

            noop_count = sum(1 for inst in decoded if inst.mnemonic == "nop.s")
            total_noop_slots += noop_count
            if noop_count > 0:
                packets_with_noops += 1

        intra_findings.extend(check_intra_packet_hazards(decoded_packets))
        inter_findings.extend(check_inter_packet_hazards(decoded_packets))

    elif build_step.passed:
        parse_findings.append(f"Compiled input file not found: {compiled_path}")

    overall_fail = False
    if not build_step.passed:
        overall_fail = True
    if not smoke_step.skipped and not smoke_step.passed:
        overall_fail = True
    if (
        config_findings
        or parse_findings
        or width_findings
        or vector_findings
        or memory_findings
        or intra_findings
        or inter_findings
    ):
        overall_fail = True

    report_text = render_report(
        asm_path=asm_path,
        compiled_path=compiled_path,
        report_path=report_path,
        packet_length=args.packet_length,
        build_step=build_step,
        smoke_step=smoke_step,
        config_findings=config_findings,
        parse_findings=parse_findings,
        width_findings=width_findings,
        vector_findings=vector_findings,
        memory_findings=memory_findings,
        intra_findings=intra_findings,
        inter_findings=inter_findings,
        total_packets=total_packets,
        total_noop_slots=total_noop_slots,
        packets_with_noops=packets_with_noops,
        overall_pass=(not overall_fail),
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text)

    if overall_fail:
        print(f"[FAIL] Verification failed. Report: {report_path}")
        return 1

    print(f"[PASS] Verification succeeded. Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
