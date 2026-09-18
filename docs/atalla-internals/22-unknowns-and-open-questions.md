# 22 — Unknowns, inferences, and open questions

## Unknown (hardware/ISA facts the repository does not pin down)

| Question | Why it matters | Where to look / how to resolve |
|----------|----------------|-------------------------------|
| Is the branch/jal immediate relative to the branch address or to PC+5? | `BR_i10`/`MI_jal_i25.calc` use the branch address; a commented alternative uses PC+5 (`relocations.py:16-19`) | ISA spec / emulator; `test_relocations.py` cannot tell (it mirrors the compiler's convention) |
| `lui_s` semantics (`imm25 << 7`?) and `addi_s` sign extension width | constant materialisation and global addressing (`>> 7`, `& 0x7F`) | ISA spec |
| Do `x0`, `v0` read as zero; does `m0` mean all-lanes? | moves (`add_vv … v0, m0`), negation, `jal x0` | ISA spec; note `lw_vi v0, …` from `load_weights` **writes v0** if it is a real register |
| Meaning of `vreg_ld/st` operands `rs2`, `num_cols`, `sid` for a stack slot (`1`, `31`, `3`) | scratchpad spill/local correctness | hardware docs; `vector_instructions.py:287-323` hard-codes them |
| Is `2000000` a valid scratchpad top address? | `AtallaArch.scpad_fp_start` | emulator memory map |
| Does `scpad_ld/st` write back `rs1_rd1`? | operand declared read+write; C semantics ignore it | ISA spec |
| How are VLIW packets delimited? | no bits in any token; no packetizer runs | emulator build file (outside repo) |
| Vector/functional-unit latencies | `instruction_latency.py` has 7 scalar entries | branch `origin/atalla-shaunak` has an expanded table (not merged) |
| Does the emulator load `ET_REL` files by section headers? | output has no program headers | emulator loader |
| bf16 rounding: hardware vs compiler's truncation (`_f32_to_f16_bits`) | constant values | ISA spec |
| `jalr` offset field (always 0 in encode) | indirect calls | ISA spec |

## Inferred (not executed in this investigation)

* `vec` arguments/returns by value crash in `arch.move` (operand class assertion).
* `mask`-typed locals crash in `CContext.type_size_map` (`MASK` missing).
* `--ast` uses the generic C parser (`cli/atalla_cc.py:9`) and would reject `vec`.
* An installed (`pip install .`) copy fails on `import vliw_packetizer`.
* `Dcd2`/`absaddr32` relocations (global pointer initialisers) raise in `get_reloc_type` when writing ELF.
* `--super-verbose` in `atalla_cc` is rejected by the inner parser.
* Signed constants below −2²⁵ are not covered.
* `vec_op_masked` with `|`, `&`, `^`, `<<`, `>>`, `/`, `SQRT`, `~` reaches the selector with no rule → crash.
* Vector element with a non-constant index (`v[i]`) → not covered.
* `ConstantFolder` folds bf16 constants as Python floats (`cast` returns the value unchanged for
  `FloatingPointTyp`) — `5.0/6.7` was **not** folded in `bftest.c` because `/` folding goes through
  `enhance`/integer helpers; not traced further.

## Verified defects (summary; details in the chapters cited)

1. Global variable access double-dereferences (ch. 14.5).
2. Register coalescing disabled by `ismove` (ch. 11.4).
3. Caller/callee-save sets leave `x9, x11, x18–x27` unprotected across calls (ch. 09.4).
4. Signed `int` constants ≥ 2²⁵ crash (ch. 10.4).
5. bf16 comparisons link-fail (`float16_*`) (ch. 10.4).
6. `load_weights` emits `lw_vi v0, …` while `v0` is assumed zero elsewhere (ch. 17).
7. `test_relocations.py` global test is broken (ch. 18.3).
8. `round_up(0) == 16` and the always-empty callee-save block waste 16 bytes and 2 instructions per frame (ch. 09.3).
9. `api.py:271` dead packetizer hook; `print()` calls in the hot path (ch. 02, 20).
10. 2-byte `float` locals stored with 4-byte `sw_s` (ch. 21.7).
11. `gen_Atalla_memcpy` copies words at byte offsets (ch. 09.4).
12. Scratchpad routing keyed on `amount == 64` catches any 64-byte local (ch. 06.7).
13. `dump_elf.py` hard-codes offsets and a 6-byte stride (ch. 01).

## Open design questions

* Where should packetization live? All three attempts pack post-RA; the allocator's lowest-register-first
  policy and the uncoalesced copies create false dependencies that any bundle former must serialise.
  Fixing `ismove` (finding 2) is a prerequisite for meaningful ILP measurements.
* Should `LABEL` produce an address in a register (drop the `lw_s`) or should a literal pool be reintroduced
  (`dcd` for symbols is `NotImplementedError` today)?
* The ABI needs a decision on callee-saved registers before any non-trivial program is trusted.
* `ET_REL` vs `ET_EXEC`: adding `ENTRY(main)` to `atalla_layout.mmap` would produce an executable with
  program headers (and `write_images` would then emit `code`/`data` `LOAD` segments) — untested.
