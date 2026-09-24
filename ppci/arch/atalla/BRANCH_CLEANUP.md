# Atalla branch cleanup and pc-relative relocation checks

This covers two related changes to the Atalla backend:

1. **Branch cleanup peephole.** It removes jumps that are redundant once the
   block order is fixed. Code is in `AtallaArch._branch_cleanup`
   (`ppci/arch/atalla/arch.py:497`).
2. **Signed range check on pc-relative relocations.** It stops far branches
   and jumps from silently encoding as backward jumps. Code is in
   `pc_rel_offset` (`ppci/arch/atalla/relocations.py:9`).

It also lists what can go wrong with each change, with the file and line to
look at.

---

## 1. What the peephole does

Instruction selection emits every block exit as an explicit jump, because it
selects one tree at a time and does not know which block comes next:

- `JMP` becomes `jal x0, L`: `pattern_jmp`, `ppci/arch/atalla/instructions.py:446`
- `CJMP` becomes `bxx a, b, yes` followed by `jal x0, no`: `pattern_cjmpi`,
  `ppci/arch/atalla/instructions.py:597`

After register allocation the order is final, so two rewrites are safe:

```
jal x0, L          ->    L:                 (jump to the very next label)
L:

bxx a, b, L1       ->    b!xx a, b, L2      (invert, drop the jal)
jal x0, L2               L1:
L1:
```

Each file in `atalla_tests` loses 1 to 6 instructions. `forloop.c` goes
from 39 to 36 instructions, and its loop header becomes a single
`bge_s x11, x9, main_block4`.

### Where it runs

```
CodeGenerator.generate_function                     ppci/codegen/codegen.py:143
├─ select_and_schedule (instruction selection)      ppci/codegen/codegen.py:177
├─ register_allocator.alloc_frame                   ppci/codegen/codegen.py:182
│    builds FlowGraph + liveness from frame.instructions (last time this happens)
├─ frame.instructions = arch.peephole(frame)        ppci/codegen/codegen.py:187
│    └─ AtallaArch.peephole                         ppci/arch/atalla/arch.py:455
│         ├─ identity-copy removal (existing)
│         └─ self._branch_cleanup(...)              ppci/arch/atalla/arch.py:489
│              └─ AtallaArch._branch_cleanup        ppci/arch/atalla/arch.py:497
│                   helpers: _INVERTED_BRANCH       ppci/arch/atalla/arch.py:755
│                            MAX_INVERTED_BRANCH_DISTANCE  arch.py:766
│                            _emits_code            ppci/arch/atalla/arch.py:769
│                            _is_jump               ppci/arch/atalla/arch.py:776
│                            _is_label              ppci/arch/atalla/arch.py:781
└─ emit_frame_to_stream                             ppci/codegen/codegen.py:242
     writes frame.instructions in list order: list order == final layout
```

---

## 2. What the relocation fix does

The hardware sign-extends the branch `imm10` and the `jal` `imm25`
(`disassemble.py:170`, `disassemble.py:193`). The old code called
`wrap_negative(offset, bits)` (`ppci/utils/bitfun.py:147`), which accepts
offsets up to `2**bits - 1`. A branch 512 to 1023 instructions forward
therefore encoded without error and **jumped backward**:

| offset (instructions) | before           | after      |
|-----------------------|------------------|------------|
| `imm10` +511          | ok               | ok         |
| `imm10` +512          | lands at −512    | link error |
| `imm10` +600          | lands at −424    | link error |
| `imm25` +2^24         | lands at −2^24   | link error |

`pc_rel_offset` (`relocations.py:9`) checks
`-2**(bits-1) <= offset < 2**(bits-1)`. Both `AtallaBR_Imm10_Relocation.calc`
(`relocations.py:31`) and `AtallaMI_JAL_Imm25_Relocation.calc`
(`relocations.py:50`) now call it.

`test_relocations.py:77` now also recognizes `bge_s` and `ble_s`. Before this
change, inverted branches would have been skipped by its control-flow check.

---

## 3. Things that can go wrong

### 3.1 Moving the peephole before register allocation, or re-running liveness after it

- **Where:** `ppci/codegen/flowgraph.py:62-80`, `ppci/codegen/codegen.py:182-187`
- **Why:** `FlowGraph` only adds edges from `ins.jumps`. It never adds an
  implicit fall-through edge. That is why `pattern_cjmpi` emits the extra
  `jal` and lists it in the branch's `jumps`. After the cleanup, a block that
  falls through has no edge to the next block.
- **Today:** safe. The last `FlowGraph` is built inside `alloc_frame`, before
  the peephole runs.
- **Breaks if:** someone moves `arch.peephole` above `alloc_frame`, or adds a
  pass after the peephole that rebuilds liveness from `frame.instructions`
  (for example, a post-RA scheduler that uses `FlowGraph`). Liveness would be
  wrong across the removed jumps, and that means miscompiles.
- **Partial mitigation:** an inverted branch lists both targets in `jumps`,
  the taken label and the fall-through label (`arch.py:551`). A removed
  `jal x0, L` has no such fix.

### 3.2 Re-enabling the `buckets_by_block` emission path

- **Where:** `ppci/codegen/codegen.py:197`, `ppci/arch/atalla/arch.py:491`,
  `ppci/codegen/instructionselector.py:470` (commented out)
- **Why:** if `frame.buckets_by_block` is set, code is emitted from the
  buckets, not from `frame.instructions`. The peephole mirrors deletions into
  the buckets but not replacements. On an inversion, the old `bxx` and the
  `jal` are both in `removed` and get filtered out of the buckets, and the new
  `b!xx` is never inserted. **The branch disappears entirely.**
- **Today:** safe. `_build_buckets_from_sgraph` is never called, so
  `buckets_by_block` is never set.
- **If re-enabled:** either skip `_branch_cleanup` when `buckets_by_block` is
  set, or replace the instruction inside the buckets in place.

### 3.3 Inverted branch out of range after VLIW padding

- **Where:** `MAX_INVERTED_BRANCH_DISTANCE` (`arch.py:766`), the distance test
  (`arch.py:545`), `pc_rel_offset` (`relocations.py:9`)
- **Why:** inversion moves the far target, often the loop exit, from `jal`
  (±16M instructions) onto the conditional branch (−512..511). The guard
  allows at most 128 real instructions between the branch and its new target.
  That leaves 4x headroom for NOP padding from a packetizer: the one on
  `origin/atalla-shaunak` (`_pack_flat_vliw`), or the emulator's text-based
  `vliw_packetizer.py`.
- **Breaks if:** a packetizer pads more than about 4x, or the constant is
  raised. With the relocation fix this is a loud **link error**
  ("target is N instructions away"), not a miscompile. The fix is to lower the
  constant or have the packetizer relax the branch back into `bxx` + `jal`.
- **Also note:** the branch that was already there, `bxx ..., yes` from
  `pattern_cjmpi`, has no distance guard at all. It relies on `yes` being
  the next block. It gets the same link error if that assumption fails.
- **Test:** `atalla_tests/bigloop_guard.c` (header exit about 196
  instructions away, so it must *not* be inverted) and
  `atalla_tests/bigloop_inverted.c` (under 128, so it must be inverted).

### 3.4 Distance counting assumptions

- **Where:** `arch.py:521-529`, `_emits_code` at `arch.py:769`
- **Why:** distance counts every non-label, non-virtual item as one 5-byte
  word, and labels as zero.
  - Inline assembly has unknown size, so any function containing
    `InlineAssembly` gets no inversions (`arch.py:517`).
  - If other multi-word or pseudo items (`Align`, data directives) ever land
    inside a function body, the count will be low. The relocation check will
    still catch real overflows at link time.
- **Epilogue:** the prologue and epilogue are emitted outside
  `frame.instructions` (`codegen.py:256`, `arch.gen_epilogue`), and so is the
  literal pool (`arch.py:453`, `arch.py:683`). `main_epilog:` is the last
  label in the list, so jumps to it are measured correctly.

### 3.5 Pattern coverage

- **Where:** `_is_jump` (`arch.py:776`), `_INVERTED_BRANCH` (`arch.py:755`)
- `_is_jump` requires `rd is R0` and a string label target. Calls
  (`jal x1, fn`) and returns (`jalr`) are never touched.
- Only the six signed branches are inverted: `blt`/`bge`, `bgt`/`ble`,
  `beq`/`bne`. If unsigned branches are added (the patterns are commented out
  at `instructions.py:606`), add their pairs to `_INVERTED_BRANCH`. Until
  then, unknown branch types are left alone, which is safe.
- The rewrite requires the exact shape `bxx L1; jal x0, L2; L1:`, ignoring
  `RegisterUseDef` and other virtual instructions in between. Any other
  layout is left unchanged.

### 3.6 Debug info on replaced branches

- **Where:** `arch.py:552` (new instruction), `ppci/codegen/dagsplit.py:113`
  (where debug locations get attached)
- The inverted branch is a new `Instruction` object and has no entry in
  `debug_db`. With `-g`, that one branch loses its source-line mapping.
  Nothing else is affected.

### 3.7 Builds that used to link may now fail

- **Where:** `relocations.py:9-23`
- Any program with a branch 512 to 1023 instructions forward, or a jump
  ≥2^24 instructions forward, used to link and then jump to the wrong place.
  It now fails at link time. Those builds were already broken.
- **Not changed:** `pc_rel_offset` still uses floor division by
  `ATALLA_INSN_ALIGNMENT` (`relocations.py:17`). If a target is ever not a
  multiple of 5 bytes from the branch, it rounds silently.
  `AtallaI_JALR_Imm12_Relocation` (`relocations.py:83`) and
  `AtallaI_Abs_Imm7_Relocation` (`relocations.py:68`) mask bits instead of
  range-checking. That is intentional for `lui` + `addi` address pairs, and
  they were not touched.

### 3.8 Comparing compiler output before and after a change

- **Where:** `topological_sort_modified`, `ppci/codegen/dagsplit.py:150`
  and `:181`
- The tree order comes from iterating a plain `set` of DAG nodes, which
  follows object `id()`. Output is identical from run to run, but **any code
  change**, even one that runs after register allocation, can shift memory
  layout and change the register allocation.
- Observed: `bigloop_guard.c` compiled to 339 instructions on `HEAD` and 341
  with `_branch_cleanup` present but returning immediately. A/B comparisons
  should use a no-op baseline of the new code, not `HEAD`.

---

## 4. How it was tested

Everything was built in a scratch directory: `HEAD` exported with
`git archive` as the baseline, and a copy with only the changed files as
the new build. Each file in `atalla_tests` was compiled with `-O2` to `.s`
and `.o`, linked with `atalla_layout.mmap`, disassembled with
`dump_elf.py` / `disassemble.py`, and checked with `test_relocations.py`.

- Every file that compiled before still compiles, links, and passes the
  control-flow check. `testptr.c` and `vs_instr.c` fail before and after,
  for unrelated reasons.
- Compared against a no-op baseline (see 3.8), **the only lines that
  change in any output are `jal x0` / `b*_s` lines.**
- Inversions were checked by hand in `instructtest4.c`:
  `bgt_s`→`ble_s`, `blt_s`→`bge_s`, `beq_s`→`bne_s`, each targeting the
  old `jal`'s label and falling through to the old branch target.

| file            | instructions before → after |
|-----------------|-----------------------------|
| forloop         | 39 → 36                     |
| instructtest3   | 82 → 79                     |
| instructtest4   | 116 → 110                   |
| sample          | 136 → 133                   |
| intrinsictest   | 91 → 89                     |
| bigloop_guard   | 341 → 340 (vs no-op)        |

### Regression test

```
PYTHONPATH=. python3 atalla_tests/test_branch_cleanup.py
```

Run it from the repo root: it compiles with `python -m ppci`, which picks up
the `ppci` in the current directory. It checks:

- the `imm10` and `imm25` boundary offsets (round-trip just inside the
  range, rejection just outside);
- that `bigloop_inverted.c` has a single `bge_s` loop header;
- that `bigloop_guard.c` keeps `blt_s` + `jal`;
- that no `jal x0, L` is directly followed by `L:`.

On the old code it reports 6 failures. With these changes it reports 0.
