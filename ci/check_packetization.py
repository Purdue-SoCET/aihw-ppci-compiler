"""Compare compiler packets with an intentionally repeated legacy scheduling pass."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "functional_sim"))
import build_compiler as builder


def compare(path):
    source = path.read_text()
    instructions, labels, packets = builder.parse_packetized_program(source)
    # Keep the test focused on scheduling; no peephole or instruction expansion.
    padded, padded_labels = builder.parse_program(source)
    _, repeated = builder.schedule_program(padded, padded_labels)
    return {
        "kernel": path.stem,
        "instructions_non_nop": len(instructions),
        "compiler_packets": len(packets),
        "compiler_nop_packets": sum(not packet for packet in packets),
        "compiler_slots": 4 * len(packets),
        "legacy_scheduler_input_including_nops": len(padded),
        "packets_after_legacy_rescheduling": len(repeated),
        "non_nop_instructions_after_rescheduling": sum(
            padded[idx].mnemonic not in builder.NOP_MNEMONICS
            for packet in repeated for idx in packet
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assembly", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps([compare(path) for path in args.assembly], indent=2))


if __name__ == "__main__":
    main()
