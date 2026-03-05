from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import build_softmax as base
from instruction_latency import latency

IMM_RE = re.compile(r"^[+-]?(?:0x[0-9a-fA-F]+|0b[01]+|\d+)$")
REG_RE = re.compile(r"^\$?[xv](\d+)$", re.IGNORECASE)
MASK_RE = re.compile(r"^\$?m(\d+)$", re.IGNORECASE)
MEM_RE = re.compile(
    r"^([+-]?(?:0x[0-9a-fA-F]+|0b[01]+|\d+))\(\s*(\$?[xv]\d+)\s*\)$",
    re.IGNORECASE,
)

IGNORED_DIRECTIVE_PREFIXES = (
    ".section",
    ".align",
    "global",
    "type",
)

MNEMONIC_ALIASES = {
    "beq": "beq.s",
    "bne": "bne.s",
    "blt": "blt.s",
    "bge": "bge.s",
    "bgt": "bgt.s",
    "ble": "ble.s",
    "lw": "lw.s",
    "sw": "sw.s",
    "lhw": "lhw.s",
    "shw": "shw.s",
    "li": "li.s",
    "lui": "lui.s",
    "addi": "addi.s",
    "subi": "subi.s",
    "muli": "muli.s",
    "divi": "divi.s",
    "modi": "modi.s",
    "ori": "ori.s",
    "andi": "andi.s",
    "xori": "xori.s",
    "slli": "slli.s",
    "srli": "srli.s",
    "srai": "srai.s",
    "slti": "slti.s",
    "sltui": "sltui.s",
    "nop": "nop.s",
    "halt": "halt.s",
    "barrier": "barrier.s",
}


@dataclass
class AsmInstr:
    mnemonic: str
    ops: list[str]
    comment: str
    labels: list[str] = field(default_factory=list)


def strip_comment(line: str) -> tuple[str, str]:
    if "#" in line:
        code, cmt = line.split("#", 1)
        return code.rstrip(), cmt.strip()
    return line.rstrip(), ""


def is_ignored_directive(code: str) -> bool:
    lowered = code.lower()
    return any(lowered.startswith(prefix) for prefix in IGNORED_DIRECTIVE_PREFIXES)


def normalize_mnemonic(mnemonic: str) -> str:
    m = mnemonic.strip().lower().replace("_", ".")
    return MNEMONIC_ALIASES.get(m, m)


def normalize_operand(op: str) -> str:
    s = op.strip()

    mem_m = MEM_RE.match(s)
    if mem_m:
        off = mem_m.group(1)
        base_reg = normalize_operand(mem_m.group(2))
        return f"{off}({base_reg})"

    reg_m = REG_RE.match(s)
    if reg_m:
        return f"${int(reg_m.group(1))}"

    mask_m = MASK_RE.match(s)
    if mask_m:
        return str(int(mask_m.group(1)))

    return s


def normalize_instruction(code: str) -> tuple[str, list[str]]:
    mnemonic, ops = base.split_mnemonic_operands(code)
    if not mnemonic:
        return "", []
    return normalize_mnemonic(mnemonic), [normalize_operand(op) for op in ops]


def _check_signed_25bit(value: int) -> None:
    lo = -(1 << 24)
    hi = (1 << 24) - 1
    if value < lo or value > hi:
        raise ValueError(f"jal offset {value} out of signed 25-bit range [{lo}, {hi}]")


def asm_to_instr_dict(
    mnemonic: str,
    ops: list[str],
    *,
    labels: dict[str, int] | None = None,
    pc: int | None = None,
) -> dict:
    # Compiler output sometimes omits VV sac; default to 0.
    if mnemonic in {"add.vv", "sub.vv", "mul.vv", "div.vv", "and.vv", "or.vv", "xor.vv", "gemm.vv"} and len(ops) == 4:
        return base.asm_to_instr_dict(mnemonic, [ops[0], ops[1], ops[2], ops[3], "0"], labels=labels, pc=pc)

    # base assembler resolves labels for BR, but not for JAL immediates.
    if mnemonic == "jal" and len(ops) in (1, 2):
        if len(ops) == 1:
            rd = 0
            target = ops[0]
        else:
            rd = base.parse_reg(ops[0])
            target = ops[1]

        if labels is not None and target in labels:
            if pc is None:
                raise ValueError("Internal error: missing PC for label-based jal")
            imm = labels[target] - pc
        elif IMM_RE.match(target):
            imm = base.parse_int(target)
        else:
            raise ValueError(f"Unknown jal label: {target!r}")

        _check_signed_25bit(imm)
        opcode, instr_type = base.INVERT_OPCODES["jal"]
        return {
            "opcode": opcode,
            "type": instr_type,
            "rd": rd,
            "imm25": imm,
        }

    return base.asm_to_instr_dict(mnemonic, ops, labels=labels, pc=pc)


def parse_program(in_data: str) -> tuple[list[AsmInstr], dict[str, int]]:
    stop_markers = {"data mem", ".data"}
    instructions: list[AsmInstr] = []
    labels: dict[str, int] = {}
    pending_labels: list[str] = []

    for raw in in_data.splitlines():
        code, cmt = strip_comment(raw)
        code = code.strip()
        if not code:
            continue

        line_labels, code = base.parse_leading_labels(code)
        if line_labels:
            pending_labels.extend(line_labels)

        if not code:
            continue

        lowered = code.lower()
        if lowered in stop_markers:
            break

        if code.startswith(".") or is_ignored_directive(code):
            continue

        mnemonic, ops = normalize_instruction(code)
        if not mnemonic:
            continue

        idx = len(instructions)
        if pending_labels:
            for label in pending_labels:
                if label in labels:
                    raise ValueError(f"Duplicate label: {label}")
                labels[label] = idx

        comment = cmt if cmt else mnemonic
        instructions.append(AsmInstr(mnemonic=mnemonic, ops=ops, comment=comment, labels=list(pending_labels)))
        pending_labels.clear()

    return instructions, labels


def inject_main_bootstrap(
    instructions: list[AsmInstr], labels: dict[str, int]
) -> tuple[list[AsmInstr], dict[str, int]]:
    # Provide deterministic entry semantics for compiler-generated code:
    # call main and halt when main returns.
    if "main" not in labels:
        return instructions, labels

    bootstrap = [
        AsmInstr(mnemonic="jal", ops=["$1", "main"], comment="bootstrap.call_main"),
        AsmInstr(mnemonic="halt.s", ops=[], comment="bootstrap.halt"),
    ]

    shifted_labels = {name: idx + len(bootstrap) for name, idx in labels.items()}
    return bootstrap + instructions, shifted_labels


def is_control_mnemonic(mnemonic: str) -> bool:
    return mnemonic in {"jal", "jalr"} or mnemonic.startswith("b")


def split_packets_for_control_and_labels(
    packets: list[list[int]], instructions: list[AsmInstr], labels: dict[str, int]
) -> list[list[int]]:
    labeled_indices = set(labels.values())
    out: list[list[int]] = []

    for packet in packets:
        if not packet:
            out.append([])
            continue

        current: list[int] = []
        for idx in packet:
            mnem = instructions[idx].mnemonic

            # Labels must begin a packet so jumps can target packet PCs safely.
            if current and idx in labeled_indices:
                out.append(current)
                current = []

            # Control instructions must start/end packets.
            if current and is_control_mnemonic(mnem):
                out.append(current)
                current = []

            current.append(idx)

            if is_control_mnemonic(mnem):
                out.append(current)
                current = []

        if current:
            out.append(current)

    return out


def schedule_program(instructions: list[AsmInstr], labels: dict[str, int]) -> tuple[list[int], list[list[int]]]:
    # Reuse softmax scheduler but feed mnemonics directly.
    sched_inputs = [(inst.mnemonic, [], [], None) for inst in instructions]
    ready = base.build_dependency_graph(sched_inputs, latency)
    packets = base.greedy_pack(sched_inputs, ready)
    packets = split_packets_for_control_and_labels(packets, instructions, labels)
    return ready, packets


def build_pc_maps(
    packets: list[list[int]], labels: dict[str, int]
) -> tuple[dict[int, int], dict[str, int]]:
    idx_to_pc: dict[int, int] = {}
    for pkt_idx, packet in enumerate(packets):
        pc = pkt_idx * base.INSTR_ADDR_STRIDE
        for idx in packet:
            idx_to_pc[idx] = pc

    label_to_pc: dict[str, int] = {}
    for label, idx in labels.items():
        if idx not in idx_to_pc:
            raise ValueError(f"Label {label!r} points to unscheduled instruction index {idx}")
        label_to_pc[label] = idx_to_pc[idx]

    return idx_to_pc, label_to_pc


def relocate_and_encode(
    instructions: list[AsmInstr], packets: list[list[int]], labels: dict[str, int]
) -> dict[int, str]:
    idx_to_pc, label_to_pc = build_pc_maps(packets, labels)
    encoded: dict[int, str] = {}

    for packet in packets:
        for idx in packet:
            inst = instructions[idx]
            pc = idx_to_pc[idx]
            instr_dict = asm_to_instr_dict(inst.mnemonic, inst.ops, labels=label_to_pc, pc=pc)
            hex48 = base.encode_instruction(instr_dict).upper()
            if len(hex48) != 12:
                raise ValueError(f"encode_instruction returned {hex48!r} (expected 12 hex chars)")
            encoded[idx] = hex48

    return encoded


def emit_packet_format(
    packets: list[list[int]],
    instructions: list[AsmInstr],
    encoded: dict[int, str],
) -> str:
    nop_hex = base.encode_instruction({"opcode": base.INVERT_OPCODES["nop.s"][0]}).upper()
    lines: list[str] = []

    for pkt_idx, packet in enumerate(packets):
        addr = pkt_idx * base.INSTR_ADDR_STRIDE
        words = [encoded[idx] for idx in packet]
        while len(words) < base.REAL_PACKET_SIZE:
            words.append(nop_hex)

        comment = ""
        for idx in packet:
            c = instructions[idx].comment
            if c:
                comment = c
                break

        suffix = f" # {comment}" if comment else ""
        lines.append(f"{addr:08X}: " + " ".join(words) + suffix)

    return "\n".join(lines)


def compile_asm(in_data: str) -> tuple[str, list[int], list[list[int]]]:
    instructions, labels = parse_program(in_data)
    instructions, labels = inject_main_bootstrap(instructions, labels)
    ready, packets = schedule_program(instructions, labels)
    encoded = relocate_and_encode(instructions, packets, labels)
    instr_text = emit_packet_format(packets, instructions, encoded)
    final = base.render_testfile(instr_text, "")
    return final, ready, packets


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", type=Path, default=None, help="Input assembly file")
    ap.add_argument("-o", "--output", type=Path, default=None, help="Output test file")
    args = ap.parse_args()

    if args.input is None:
        raise ValueError("build_compiler.py requires --input")

    asm = args.input.read_text()
    final, ready, packets = compile_asm(asm)

    print("ready:", ready)
    print("packets:", packets)

    if args.output is not None:
        os.makedirs(args.output.parent, exist_ok=True)
        args.output.write_text(final)
    else:
        print(final)


if __name__ == "__main__":
    main()
