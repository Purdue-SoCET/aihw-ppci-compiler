#!/usr/bin/env python3
"""
Packetization checker for final code listings.

Two input formats are supported:
1) Hex + assembly lines (amps.s style):   <10-hex-digits><spaces><mnemonic operands>
2) Plain assembly output (e.g., f.out from -O2): just mnemonics and operands.

The tool:
- Prompts for the file to check.
- Uses the last contiguous block of hex+asm lines when present; otherwise uses all
  plain assembly instructions (labels/directives are skipped).
- Treats every 4 instructions as one packet and validates:
    * exactly 4 instructions per packet,
    * at most one memory instruction (load/store),
    * no RAW, WAR, or WAW register hazards within the packet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Set


HEX_LINE_RE = re.compile(r"^\s*([0-9A-Fa-f]{10})\s+(.*\S)\s*$")
REGISTER_RE = re.compile(r"x\d+")

# Heuristic mnemonic buckets (suffixes like _s are stripped).
LOAD_MNEMONICS = {
    "lw",
    "ld",
    "lb",
    "lbu",
    "lh",
    "lhu",
    "lwu",
    "ldu",
}
STORE_MNEMONICS = {
    "sw",
    "sd",
    "sb",
    "sh",
    "st",
}
BRANCH_MNEMONICS = {
    "beq",
    "bne",
    "bge",
    "bgt",
    "blt",
    "ble",
}
JUMP_MNEMONICS = {
    "jal",
    "jalr",
}


@dataclass
class EncodedInstr:
    line_no: int
    hex_code: str
    asm: str
    mnemonic: str
    is_memory: bool
    reads: Set[str]
    writes: Set[str]


def strip_suffix(mnemonic: str) -> str:
    """Remove common suffix separators like '_' or '.' to get the base mnemonic."""
    base = mnemonic.split(".", 1)[0]
    base = base.split("_", 1)[0]
    return base.lower()


def split_operands(operand_text: str) -> List[str]:
    return [op.strip() for op in operand_text.split(",") if op.strip()]


def regs_in(text: str) -> Set[str]:
    return set(REGISTER_RE.findall(text))


def analyze_instruction(asm: str) -> tuple[str, bool, Set[str], Set[str]]:
    """
    Parse the assembly portion to extract mnemonic, memory flag, read and write sets.
    Rules are heuristic but align with the simple RISC-style seen in amps.s.
    """
    asm_body = asm.split("#", 1)[0].strip()  # drop comments if present
    if not asm_body:
        return "", False, set(), set()

    parts = asm_body.split(None, 1)
    mnemonic = parts[0]
    operands_text = parts[1] if len(parts) > 1 else ""

    base = strip_suffix(mnemonic)
    operands = split_operands(operands_text)

    is_load = base in LOAD_MNEMONICS
    is_store = base in STORE_MNEMONICS
    is_memory = is_load or is_store or "(" in operands_text

    reads: Set[str] = set()
    writes: Set[str] = set()

    if base == "nop":
        return mnemonic, False, reads, writes

    operand_regs = [regs_in(op) for op in operands]

    if is_store:
        for regs in operand_regs:
            reads |= regs
        return mnemonic, is_memory, {r for r in reads if r != "x0"}, set()

    if is_load:
        dest_regs = operand_regs[0] if operand_regs else set()
        for regs in operand_regs[1:]:
            reads |= regs
        writes = {r for r in dest_regs if r != "x0"}
        reads = {r for r in reads if r != "x0"}
        return mnemonic, is_memory, reads, writes

    if base in BRANCH_MNEMONICS or base.startswith("b"):
        for regs in operand_regs:
            reads |= regs
        return mnemonic, False, {r for r in reads if r != "x0"}, set()

    if base in JUMP_MNEMONICS:
        dest_regs = operand_regs[0] if operand_regs else set()
        writes = set()
        if dest_regs:
            dest = next(iter(dest_regs))
            if dest != "x0":
                writes.add(dest)
        for regs in operand_regs[1:]:
            reads |= regs
        return mnemonic, False, {r for r in reads if r != "x0"}, writes

    # generic ALU-style instruction: dest first, rest are sources
    dest_regs = operand_regs[0] if operand_regs else set()
    if dest_regs:
        dest = next(iter(dest_regs))
        if dest != "x0":
            writes.add(dest)
    for regs in operand_regs[1:]:
        reads |= regs

    reads = {r for r in reads if r != "x0"}
    writes = {w for w in writes if w != "x0"}
    return mnemonic, is_memory, reads, writes


def extract_blocks(lines: Sequence[str]) -> List[List[EncodedInstr]]:
    """
    Find contiguous blocks of hex+assembly lines. Each block ends when a
    non-matching line appears. Only the last block is relevant for final code.
    """
    blocks: List[List[EncodedInstr]] = []
    current: List[EncodedInstr] = []

    for idx, line in enumerate(lines, start=1):
        match = HEX_LINE_RE.match(line)
        if match:
            mnemonic, is_mem, reads, writes = analyze_instruction(match.group(2))
            current.append(
                EncodedInstr(
                    line_no=idx,
                    hex_code=match.group(1),
                    asm=match.group(2),
                    mnemonic=mnemonic,
                    is_memory=is_mem,
                    reads=reads,
                    writes=writes,
                )
            )
        elif current:
            blocks.append(current)
            current = []

    if current:
        blocks.append(current)

    return blocks


def extract_plain_instructions(lines: Sequence[str]) -> List[EncodedInstr]:
    """Extract instructions from plain assembly listings (no hex prefixes)."""
    instrs: List[EncodedInstr] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("."):
            continue  # directives
        if stripped.endswith(":"):
            continue  # labels
        mnemonic, is_mem, reads, writes = analyze_instruction(stripped)
        if not mnemonic:
            continue
        instrs.append(
            EncodedInstr(
                line_no=idx,
                hex_code="",
                asm=stripped,
                mnemonic=mnemonic,
                is_memory=is_mem,
                reads=reads,
                writes=writes,
            )
        )
    return instrs


def check_packets(instrs: Sequence[EncodedInstr]) -> List[str]:
    issues: List[str] = []

    if not instrs:
        issues.append("No instructions found in the selected file.")
        return issues

    total = len(instrs)
    if total % 4 != 0:
        issues.append(
            f"Instruction count {total} is not divisible by 4; last packet is incomplete."
        )

    for packet_idx, start in enumerate(range(0, total, 4), start=1):
        packet = instrs[start : start + 4]
        if len(packet) < 4:
            issues.append(
                f"Packet {packet_idx} has only {len(packet)} instruction(s); expected 4."
            )
            break

        mem_count = 0
        writes_so_far: dict[str, EncodedInstr] = {}
        reads_so_far: dict[str, EncodedInstr] = {}

        for inst in packet:
            if inst.is_memory:
                mem_count += 1

            # RAW: current reads a reg written earlier in packet
            raw_regs = inst.reads & set(writes_so_far.keys())
            for reg in sorted(raw_regs):
                writer = writes_so_far[reg]
                issues.append(
                    f"Packet {packet_idx}: RAW hazard on {reg} "
                    f"(writer line {writer.line_no}: '{writer.asm}' "
                    f"-> reader line {inst.line_no}: '{inst.asm}')."
                )

            # WAW: current writes a reg already written
            waw_regs = inst.writes & set(writes_so_far.keys())
            for reg in sorted(waw_regs):
                writer = writes_so_far[reg]
                issues.append(
                    f"Packet {packet_idx}: WAW hazard on {reg} "
                    f"(first write line {writer.line_no}, second line {inst.line_no})."
                )

            # WAR: current writes a reg that an earlier instruction read
            war_regs = inst.writes & set(reads_so_far.keys())
            for reg in sorted(war_regs):
                reader = reads_so_far[reg]
                issues.append(
                    f"Packet {packet_idx}: WAR hazard on {reg} "
                    f"(read line {reader.line_no}, write line {inst.line_no})."
                )

            for reg in inst.writes:
                writes_so_far[reg] = inst
            for reg in inst.reads:
                if reg not in reads_so_far:
                    reads_so_far[reg] = inst

        if mem_count > 1:
            lines = ", ".join(str(i.line_no) for i in packet if i.is_memory)
            issues.append(
                f"Packet {packet_idx}: {mem_count} memory instructions (lines {lines}); maximum is 1."
            )

    return issues


def main() -> None:
    file_input = input("Assembly file to check: ").strip()
    if not file_input:
        print("No file provided. Exiting.")
        return

    path = Path(file_input)
    if not path.is_file():
        print(f"File not found: {path}")
        return

    lines = path.read_text().splitlines()
    blocks = extract_blocks(lines)

    if blocks:
        target_block = blocks[-1]
        print(
            f"Using last hex-encoded block starting at line {target_block[0].line_no} "
            f"with {len(target_block)} instruction(s)."
        )
    else:
        target_block = extract_plain_instructions(lines)
        if not target_block:
            print("No instructions found in the file.")
            return
        print(
            f"Using plain assembly listing with {len(target_block)} instruction(s) "
            f"starting at line {target_block[0].line_no}."
        )

    issues = check_packets(target_block)

    if issues:
        print(f"Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"- {issue}")
    else:
        packets = len(target_block) // 4
        print(f"All packets valid: {packets} packet(s), {len(target_block)} instruction(s).")


if __name__ == "__main__":
    main()
