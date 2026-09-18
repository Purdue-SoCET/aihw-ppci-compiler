# 15 — Encoding

## 15.1 Tokens (`ppci/arch/token.py`, `ppci/arch/atalla/tokens.py`)

All Atalla tokens are `size = 40` bits, little-endian (`Token.Info.endianness = LITTLE`, `pack` writes
byte `i` = bits `8i..8i+7`, `token.py:181-190`). A field is a `bit_range(b, e)` property over
`Token.bit_value`; `__setitem__` (`:142-166`) rejects values ≥ 2ⁿ and wraps negatives into two's
complement. `bit_concat` (`:64-81`) stitches partial fields (used only for `imm10`).

| Token | opcode | fields |
|-------|--------|--------|
| `AtallaRToken` | 0..7 | `rd` 7..15, `rs1` 15..23, `rs2` 23..31 (31..40 unused) |
| `AtallaIToken` / `AtallaMToken` | 0..7 | `rd` 7..15, `rs1` 15..23, `imm12` 23..35 |
| `AtallaBRToken` | 0..7 | `incr_imm7` 7..14, `rs1_rd` 15..23, `rs2` 23..31, `imm10` = bits 31..40 (high 9) ‖ bit 14 (low 1) |
| `AtallaMIToken` | 0..7 | `rd` 7..15, `imm25` 15..40 |
| `AtallaSToken` | 0..7 | — |
| `AtallaVVToken` | 0..7 | `vd` 7..15, `vs1` 15..23, `vs2` 23..31, `mask_reg` 31..35 |
| `AtallaVSToken` | 0..7 | `vd`, `vs1`, `rs1` 23..31, `mask_reg` 31..35 |
| `AtallaVIToken` | 0..7 | `vd`, `vs1`, `imm8` 23..31, `mask_reg` 31..35 |
| `AtallaVMemToken` | 0..7 | `vd` 7..15, `rs1` 15..23, `rs2` 23..31, `num_cols` 31..36, `sid` 36..38 |
| `AtallaSDMAToken` | 0..7 | `rs1_rd1` 7..15, `rs2` 15..23, `rs3` 23..31 |
| `AtallaMTSToken` | 0..7 | `rd` 7..15, `vms` 15..19 |
| `AtallaSTMToken` | 0..7 | `vmd` 7..11, `rs1` 15..23 |
| `AtallaVTSToken` | 0..7 | `rd` 7..15, `vs1` 15..23, `imm8` 23..31 |
| `AtallaVMVToken` | 0..7 | `vmd` 7..11, `vs1` 15..23, `vs2` 23..31, `mask_reg` 31..35 |
| `AtallaVMSToken` | 0..7 | `vmd` 7..11, `vs1` 15..23, `rs1` 23..31, `mask_reg` 31..35 |

Register fields are 8 bits wide (room for `x0..x33`), mask fields 4 bits (`m0..m15`).

## 15.2 From `Instruction` to bytes

Generic path (`encoding.py:417-425`): `get_tokens()` → `set_all_patterns(tokens)` → for each
`(field, value)` in the class `patterns` dict: `FixedPattern` (opcode) or `VariablePattern` (an `Operand`;
`get_value` returns `Register.num` for registers, the int otherwise) → `TokenSequence.set_field`
finds the first token having that attribute → `tokens.encode()`.

Overridden `encode()`s write fields by explicit slices and leave relocatable immediates at 0:
`BranchBase` (`instructions.py:149-154`), `Jal` (`:296-300`, opcode hard-coded `0b0101101`), `Jalr`
(`:311-316`, `0b0101110`, **ignores `imm12`** — `jalr x0, x1, 0` always encodes offset 0), `Luil`, `Addil`.

`Register.num` on a virtual register asserts `is_colored` — encoding before allocation is impossible.

## 15.3 Worked encodings (produced by calling `.encode()` directly; verified)

```
add_s x9, x11, x12      81 84 05 06 00   opcode=0000001 rd=9 rs1=11 rs2=12
addi_s x2, x2, -16      16 01 01 F8 07   opcode=0010110 rd=2 rs1=2 imm12=0xFF0 (two's complement)
li_s x9, 10             AF 04 05 00 00   opcode=0101111 rd=9 imm25=10
lui_s x32, 15625        30 90 84 1E 00   opcode=0110000 rd=32 imm25=15625
blt_s x12, x9, L        25 00 86 04 00   opcode=0100101 rs1_rd=12 rs2=9 imm10=0 (patched by BR_i10)
  after reloc +2:       25 00 86 84 00   bit 14 = 0 (low bit), bits 31..39 = 1 → imm10 = 0b0000000010
jal x0, L               2D 00 00 00 00   opcode=0101101 rd=0 imm25=0 (patched)
  after reloc -8:       2D 00 FC FF FF
jalr x0, x1, 0          2E 80 00 00 00   opcode=0101110 rd=0 rs1=1
lw_s x1, 4(x2)          A9 00 01 02 00   opcode=0101001 rd=1 rs1=2 imm12=4
sw_s x1, 4(x2)          AA 00 01 02 00   opcode=0101010 rd=1 rs1=2 imm12=4   (rd is the source register)
lui_s x9, g             B0 04 00 00 00   → after MI_abs_i25 (g=0x80000): B0 04 00 08 00 (imm25=4096)
add_vv v3, v1, v0, m0   B3 81 00 00 00   opcode=0110011 vd=3 vs1=1 vs2=0 mask=0
vreg_ld v1, x10, x9,31,1 C4 00 85 84 1F  opcode=1000100 vd=1 rs1=10 rs2=9 num_cols=31 sid=1
mv_stm m1, x9           CA 80 04 00 00   opcode=1001010 vmd=1 rs1=9
gemm_vv v1, v1, v1, m1  B6 80 80 80 00
scpad_ld x11, x10, x9   C6 05 85 04 00   opcode=1000110 rs1_rd1=11 rs2=10 rs3=9
```

Opcode table: scalar `instructions.py:69-93` (R), `:126-136` (I), `:175-180` (BR), `:237-238` (M),
`:269-270` (MI), `:318-319` (`halt`, `nop`); vector `vector_instructions.py:125-172`, mask `:200-201`,
SDMA `:598-599`, `vmov_vts` `:614`. Note `expi_vi` (`0b0110111`) and `gemm_vv` (`0b0110110`) sit next to
`add/sub/mul_vv`; several opcodes were renumbered (“WAS:” comments) — the assembler/disassembler tables
must be kept in sync by hand (`disassemble.py:31-141` is a separate copy).

## 15.4 Data, alignment, sections

* `DByte`, `DZero`, `Dd` (`data_instructions.py`) encode raw bytes; `dcd(int)` → `Dd`.
* `Align(n)` (`ArtificialInstruction`) renders to `Alignment(n)`; `BinaryOutputStream` pads with zero bytes
  until `section.size % n == 0` and raises `section.alignment` (`outstream.py:143-147`). The code section
  ends up with alignment 5 (visible as `"alignment": "0x5"` in the JSON), data with 4.
* `Section("data")`/`Section("code")` render to `SectionInstruction` → `get_section(name, create=True)`.
  `TextOutputStream` prints them as `.section <name>` (`AtallaAsmPrinter`).

## 15.5 ELF file layout (verified from the hexdump in ch. 21)

`ElfFile(bits=32, LITTLE)`; `e_machine = 0x270F`; `e_type = ET_REL`; `e_phnum = 0`. File order:
ELF header (52 bytes) → `data` section bytes (aligned to 4) → `code` section bytes (aligned to 5: `0x34 + …`;
in `forloop.elf` code begins at file offset `0x37`) → `.symtab` (aligned 4) → `.relacode` → `.strtab` →
section headers. Section headers carry `sh_addr` from the layout (`0x80000`, `0x1000`-based) and
`sh_addralign` 4/5. `disassemble.py` reads `.text/text/code` by name (`get_code_bounds`, `:414-441`) and
walks it in 5-byte steps, treating any byte that does not start a known opcode as `PAD`.
