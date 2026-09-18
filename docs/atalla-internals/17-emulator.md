# 17 — Emulator / simulation interfaces

**There is no emulator, simulator, or hardware model in this repository.** Verified by directory survey
(ch. 01): nothing under `ppci/` or the repo root executes Atalla instructions. The README says the
emulator's *build file* performs packetization and that `-S` output should be fed to it.

What exists that touches the emulator boundary:

| Artifact | Role | Notes |
|----------|------|-------|
| `-S` assembly text | the documented hand-off format | `.section data/code`, `global`, `type`, `.align 5`, labels, one instruction per line in `Syntax` form; identity moves removed by the peephole; no packet markers |
| `.elf` (`ET_REL`, `e_machine 0x270F`) | linked binary | sections `data` (`sh_addr 0x80000`) and `code` (`sh_addr` = `0x1000` rounded up to a multiple of 5), no program headers; a loader must use section headers |
| `disassemble.py` | reference decoder | independent opcode table; its `offset` column is a file offset, symbols are printed as `sec_off + st_value - 4` |
| `instruction_latency.py` | latency model stub | 7 entries |
| `AtallaArch.gdb_registers` (`arch.py:213`) | GDB register list (`x0..x33`, `PC`) | `gdb_pc` is commented out; no debug driver for Atalla exists |
| `scpad_fp_start = 2000000` | the address the compiler assumes for the top of scratchpad memory | must agree with the emulator's scratchpad size; nothing in the repo asserts this |

Assumptions the generated code makes about the machine (each **Unknown** whether the hardware agrees):

1. `x0` reads as zero (`sub_s a, x0, a`, `jal x0, …`, `sqrt_bf d, a, x0`, `stbf_s d, a, x0`).
2. `v0` is a zero vector (`add_vv d, s, v0, m0` is used as a move; `lw_vi v0, …` writes it!).
   Note `pattern_loadweights` (`vector_instructions.py:622-625`) emits `lw_vi v0, vsrc, 0, m0` — if
   that instruction writes `v0`, every later vector move is corrupted.
3. `m0` means “all lanes enabled”.
4. Branch/jump immediates are relative to the branch's own address in units of 5 bytes (ch. 14).
5. `lui_s rd, imm25` computes `imm25 << 7`; `addi_s` sign-extends a 12-bit immediate.
6. `lw_s/sw_s` move 32 bits; there are no byte/half loads (patterns for `i8/i16/u8/u16` memory ops are
   commented out at `instructions.py:809-878`; `bf16` locals are stored with `sw_s` — see ch. 21 §bf16).
7. `jal rd, off` writes the return address (5 bytes past?) into `rd`; `jalr x0, x1, 0` returns.
8. Scratchpad stack grows downward from `2000000`; vector slots are 64 bytes and addressed by
   `vreg_ld/st v, base, 1, 31, 3`.
9. Instruction packets: none produced; the emulator must accept a linear stream or packetize itself.
