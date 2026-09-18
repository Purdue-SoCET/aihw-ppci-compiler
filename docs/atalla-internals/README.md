# AtallaC compiler — internal architecture and reference manual

A forensic, source-level description of how this repository compiles AtallaC to Atalla machine code.
Written against branch `atalla-arch-erwin17` at commit `a3371582` (2026-09-18). Every chapter cites
`file:line` and distinguishes *Verified* / *Inferred* / *Unknown*.

| Chapter | Contents |
|---------|----------|
| [00-overview](00-overview.md) | what this is, one-paragraph pipeline, top findings |
| [01-repository-structure](01-repository-structure.md) | what is generic PPCI, what is Atalla, where each stage lives |
| [02-entry-points](02-entry-points.md) | `atalla_cc`, `python -m ppci`, CLI flags, import-time side effects, ELF type |
| [03-compilation-pipeline](03-compilation-pipeline.md) | the actual stage list with inputs/outputs; stages that do not exist |
| [04-call-graph](04-call-graph.md) | expanded call graph for compile, per-function lowering, link; dispatch table |
| [05-data-model](05-data-model.md) | IR types, IR nodes, selection graph, trees, instructions, registers, frame, object file |
| [06-frontend](06-frontend.md) | types, intrinsics parsing/semantics, inline asm, IR generation quirks |
| [07-IR](07-IR.md) | IR reference incl. Atalla nodes, verifier, example |
| [08-optimization](08-optimization.md) | the fixed pass list and its interactions |
| [09-backend](09-backend.md) | codegen driver, frame layout, calling convention, `move`, peephole |
| [10-instruction-selection](10-instruction-selection.md) | DAG build, splitting, BURS matching, representative selections, caveats |
| [11-register-allocation](11-register-allocation.md) | liveness, interference, IRC, why coalescing never runs, spills to scratchpad |
| [12-scheduling](12-scheduling.md) | none exists; what fixes instruction order |
| [13-packetization](13-packetization.md) | three dormant packetizers; what a packet would need |
| [14-relocations](14-relocations.md) | symbols, relocations, link-time patching, the global-variable bug |
| [15-encoding](15-encoding.md) | tokens, bit layouts, worked encodings, ELF layout |
| [16-Atalla](16-Atalla.md) | everything Atalla-specific in one place; generic/Atalla boundary |
| [17-emulator](17-emulator.md) | there is none; hardware assumptions the code makes |
| [18-tests](18-tests.md) | what CI runs, `atalla_tests` as specs, `test_relocations.py`, coverage gaps |
| [19-invariants](19-invariants.md) | 20 invariants with establish/check/depend/break |
| [20-debugging](20-debugging.md) | commands, loggers, breakpoints by question, tracing a value |
| [21-end-to-end-traces](21-end-to-end-traces.md) | real traces: loop, load/store, calls, vectors, constants, intrinsics, bf16, globals, spills |
| [22-unknowns-and-open-questions](22-unknowns-and-open-questions.md) | unknowns, inferences, verified defect list, design questions |

Reproducing the traces: run the commands in chapter 20 §1 from the repository root (the compiler
needs the repo root on `sys.path` and `pydot` installed).
