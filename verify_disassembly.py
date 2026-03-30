#!/usr/bin/env python3
"""Verify Atalla disassembler output against f.out assembly listing.

Usage:
  python3 verify_disassembly.py --asm f.out --disasm disassembly.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


DISASM_LINE_RE = re.compile(r"^0x[0-9A-Fa-f]+\s+[0-9A-Fa-f ]+\s+(?P<insn>.+)$")
LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$")

IGNORE_DIRECTIVES_PREFIXES = (
    ".section",
    ".align",
    "global",
    "type",
)

# These instructions may differ in final target operand between symbolic f.out and
# numeric disassembler output. We compare everything except the final operand.
IGNORE_LAST_OPERAND_MNEMONICS = {
    "jal",
    "beq_s",
    "bne_s",
    "blt_s",
    "bge_s",
    "bgt_s",
    "ble_s",
}


@dataclass
class InstructionRecord:
    source_line: int
    raw: str
    normalized: str


def normalize_instruction(text: str) -> str:
    text = text.strip()
    if "#" in text:
        text = text.split("#", 1)[0].strip()

    text = text.replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ",", text)
    text = re.sub(r"\s*\(\s*", "(", text)
    text = re.sub(r"\s*\)\s*", ")", text)
    text = text.lower().strip()

    # Normalize accidental double spaces after formatting.
    text = re.sub(r"\s+", " ", text)

    parts = text.split(" ", 1)
    mnemonic = parts[0]
    operands = parts[1] if len(parts) > 1 else ""

    if mnemonic in IGNORE_LAST_OPERAND_MNEMONICS and operands:
        ops = [op.strip() for op in operands.split(",")]
        if len(ops) >= 2:
            # Keep all but last operand (branch/jump target may be label vs address)
            operands = ",".join(ops[:-1])
            return f"{mnemonic} {operands}".strip()

    return text


def parse_f_out(path: str) -> list[InstructionRecord]:
    out: list[InstructionRecord] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            if LABEL_RE.match(line):
                continue
            if any(line.startswith(prefix) for prefix in IGNORE_DIRECTIVES_PREFIXES):
                continue

            normalized = normalize_instruction(line)
            if normalized:
                out.append(InstructionRecord(line_no, line, normalized))
    return out


def parse_disassembly(path: str) -> list[InstructionRecord]:
    out: list[InstructionRecord] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip("\n")
            m = DISASM_LINE_RE.match(line.strip())
            if not m:
                continue
            insn = m.group("insn").strip()
            normalized = normalize_instruction(insn)
            out.append(InstructionRecord(line_no, insn, normalized))
    return out


def compare_sequences(
    expected: list[InstructionRecord], actual: list[InstructionRecord]
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True

    if len(expected) != len(actual):
        ok = False
        messages.append(
            f"Instruction count mismatch: f.out={len(expected)} disassembly={len(actual)}"
        )

    n = min(len(expected), len(actual))
    mismatch_count = 0

    for i in range(n):
        lhs = expected[i]
        rhs = actual[i]
        if lhs.normalized != rhs.normalized:
            ok = False
            mismatch_count += 1
            messages.append(
                f"[{i:03d}] f.out line {lhs.source_line}: '{lhs.raw}' != disasm line {rhs.source_line}: '{rhs.raw}'"
            )

    if mismatch_count:
        messages.append(f"Total mismatches: {mismatch_count}")

    if len(expected) > n:
        ok = False
        messages.append("Extra instructions in f.out not found in disassembly:")
        for rec in expected[n : n + 10]:
            messages.append(f"  f.out line {rec.source_line}: {rec.raw}")
        if len(expected) - n > 10:
            messages.append(f"  ... and {len(expected) - n - 10} more")

    if len(actual) > n:
        ok = False
        messages.append("Extra instructions in disassembly not found in f.out:")
        for rec in actual[n : n + 10]:
            messages.append(f"  disassembly line {rec.source_line}: {rec.raw}")
        if len(actual) - n > 10:
            messages.append(f"  ... and {len(actual) - n - 10} more")

    return ok, messages


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Atalla disassembler output against f.out instruction stream"
    )
    parser.add_argument("--asm", default="f.out", help="Path to assembler listing (default: f.out)")
    parser.add_argument(
        "--disasm",
        default="disassembly.txt",
        help="Path to disassembly output (default: disassembly.txt)",
    )
    args = parser.parse_args()

    expected = parse_f_out(args.asm)
    actual = parse_disassembly(args.disasm)

    ok, messages = compare_sequences(expected, actual)

    print(f"Parsed f.out instructions: {len(expected)}")
    print(f"Parsed disassembly instructions: {len(actual)}")

    if ok:
        print("PASS: disassembler output matches f.out (with branch/jump target normalization)")
        return 0

    print("FAIL: disassembler output does not match f.out")
    for msg in messages:
        print(msg)
    return 1


if __name__ == "__main__":
    sys.exit(main())
