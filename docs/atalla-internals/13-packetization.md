# 13 — Packetization / VLIW bundling

## 13.1 Executed path: none

No packet or bundle data structure is ever populated when running `atalla_cc`. Verified:

1. `api.ir_to_stream` (`api.py:271-272`):
   ```python
   if march == "atalla":                      # march is an AtallaArch object → always False
       output_stream = vliw_packetizer(output_stream, latency)
   ```
   Even if it were true, `vliw_packetizer(asm_str, latency_map)` expects a **string of assembly**, not a
   stream, and the return value is assigned to a local that is never used.
2. `CodeGenerator.generate_function` (`codegen.py:197-200`): `if hasattr(frame, "buckets_by_block") and
   frame.buckets_by_block:` → the attribute is never set (its producer call is commented out at
   `instructionselector.py:469-470`) → `emit_frame_to_stream` (linear) is used.
3. The README states: “Packetization is currently handled by the emulator's build file.” The emulator is
   not in this repository (ch. 17).

## 13.2 The three dormant packetizers

| Where | Input | Algorithm | Status |
|-------|-------|-----------|--------|
| `vliw_packetizer.py` (repo root, `vliw_packetizer()` `:186-240`) | assembly **text** | per basic block (split at labels and control ops), `build_dependency_graph` computes ready cycles from RAW on `x` registers, a single-LSU rule, and store→load on `(base, imm)` keys; `greedy_pack` fills 4-wide packets, one memory op per packet, control op alone, pads with `"nop"` strings | dead (see 13.1); only knows `x` registers, ignores `v`/`m` registers entirely (`parse_instruction` regex `x\d+`) |
| `InstructionSelector1.select._build_buckets_from_sgraph` (`instructionselector.py:411-465`) + `CodeGenerator._emit_packets_from_buckets` (`codegen.py:308-344`) | `sgraph.levels_by_block` (DAG depth layers) and `context.node_to_insts` (instructions attributed to DAG nodes via the `tree_owner` map from `dagsplit.py`) | groups the instructions of all nodes at the same DAG depth, chunks by 4, pads with `arch.make_nop()` (`Nop`, opcode `0b0110001`); emitter then emits prologue, per-block label, chunks, epilogue | dead; would also be wrong: it packs *pre-allocation* attributions after allocation without checking register hazards, drops `RegisterUseDef`, and `_emit_packets_from_buckets` never emits the `gen_function_enter` moves |
| `CodeGenerator._pack_flat_vliw` on branch `origin/atalla-shaunak` (not in this tree) | post-RA flat frame | list scheduler with 10 FU classes, RAW/WAW/WAR/memory deps, latency table from an expanded `instruction_latency.py`; enabled by a `-p` flag | **not merged**; the remote branch `origin/atalla-shaunak` is present in this clone (verified with `git branch -r`); see the memory note in ch. 22 for the merge hazards |

## 13.3 What a packet would need (facts available in this tree)

* Instruction width is fixed at 5 bytes (`ATALLA_INSN_ALIGNMENT = 5`, `relocations.py:6`); the code section
  is aligned to 5 (`Align(5)` in every prologue). Relocations divide byte distances by 5, so *any*
  padding inserted between instructions (NOPs) must itself be 5-byte instructions (`Nop` is).
* There is **no packet header, slot bit, or parallel-bit in any token layout** (`tokens.py`) — the
  40-bit formats have no field left for bundle delimiting. How the hardware groups instructions into
  packets is **Unknown** from this repository. The dead code assumes “4 consecutive instructions = 1
  packet, pad with NOPs”.
* Functional-unit constraints, issue widths, and vector latencies are Unknown here
  (`instruction_latency.py` has only `addi, add, sub, mul(3), or, lw(3), sw`).
