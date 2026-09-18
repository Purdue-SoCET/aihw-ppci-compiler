# 14 — Symbols, addresses and relocations

## 14.1 Where symbols are born

`BinaryOutputStream.do_emit` (`ppci/binutils/outstream.py:98-150`): after encoding an item at
`address = section.size`, `for symbol_name in item.symbols(): …` creates (or resolves) a `Symbol`. Only
`Label.symbols()` returns something (`generic_instructions.py:142-143`). Binding is `"global"` if a
`Global(name)` item was seen earlier (`_globals`), else `"local"`; type is `"func"` if `SetSymbolType(name,
"func")` was seen, else `"object"`. Hence: function names → global func symbols; block labels
(`main_block0`, `main_epilog`) → local object symbols; global variables → global object symbols in `data`.

Symbol ids are assigned in order of first mention (`_new_symbol`, `:186-196`); an undefined symbol is
created on first *reference* (`_get_symbol`) with `value=None`, and filled in when its label is emitted
(`:121-129`).

## 14.2 Where relocations are born

Each Atalla instruction that references a symbol keeps the **symbol name string** in an operand and
overrides `relocations()`:

| Instruction | Operand holding the name | Relocation class | `name` string in the object file |
|-------------|-------------------------|------------------|-------------------|
| `beq_s/bne_s/blt_s/bge_s/bgt_s/ble_s` (`BranchBase`, `instructions.py:145-154`) | `imm10: str` | `AtallaBR_Imm10_Relocation` | `BR_i10` |
| `jal` (`:291-303`) | `imm25: str` | `AtallaMI_JAL_Imm25_Relocation` | `MI_jal_i25` |
| `Luil` (`lui_s rd, label`, `:393-406`) | `label` | `AtallaMI_Abs_Imm25_Relocation` | `MI_abs_i25` |
| `Addil` (`addi_s rd, rs1, label`, `:409-424`) | `label` | `AtallaI_Abs_Imm7_Relocation` | `abs_imm7` |
| `Adrl` (`:362-377`) | `imm12` | `AtallaI_JALR_Imm12_Relocation` (`I_i12`) | unused (no pattern emits `Adrl`; its `encode` uses 64-bit bit ranges and would fail) |
| `Dcd2` (data pointer initialiser) | `v` | `U32DataRelocation` (`absaddr32`, `data_instructions.py:111-119`) | only from `generate_global` for pointer initialisers |

The `encode()` of these classes writes opcode and register fields only and leaves the immediate zero;
`BinaryOutputStream` records `RelocationEntry(reloc.name, symbol_id, section, address + reloc.offset, addend)`
with `offset = 0` (relocation covers the whole 5-byte instruction from its start).

Verified object contents for `forloop.c`: 5 relocations (`MI_jal_i25` ×4, `BR_i10` ×1) at offsets
`0x41, 0x4b, 0x50, 0x6e, 0x78`; symbols `main`(0x0), `main_block0`(0x28), `main_block2`(0x46), … .
Note `main_block0` is at 0x28 = 40 = 8 prologue instructions × 5; the first byte of the section is
`main` at 0x0 — `Align(5)` at offset 0 pads nothing.

## 14.3 Address representation

* Inside an object: `Symbol.value` = offset within `Symbol.section`; `Section.address = 0`.
* After `Linker.layout_sections` (`linker.py:309-375`): `section.address` = memory location from the
  `.mmap`, **rounded up to the section alignment** (`while current_address % section.alignment != 0:
  current_address += 1`, `:320-321`). The code section has alignment 5 (from `Align(5)`), and
  `0x1000 % 5 == 1`, so **code is placed at `0x1004`**, data at `0x80000`. Verified from the linked
  `forloop.elf` section headers: `code addr=0x1004 off=0x37 size=0x9b align=5`, `data addr=0x80000`.
  `get_symbol_id_value` (`objectfile.py:275-285`) = `symbol.value + section.address` is what every
  relocation sees, so `main` = `0x1004`, `main_block2` = `0x1004 + 0x46`, etc. The disassembler's
  "offset" column is a *file* offset and its symbol table prints `sec_off + st_value - 4`
  (`disassemble.py:401`), which happens to re-align these numbers with the file offsets; it is not an address.
* `Image` objects group sections per `MEMORY` block; `Image.data` would pad gaps, but images are only
  written for `ET_EXEC` (ch. 02), so they do not affect the produced file.

## 14.4 Applying relocations (`Linker._do_relocation`, `linker.py:623-648`)

```python
sym_value   = symbol.value + dst.get_section(symbol.section).address
reloc_value = section.address + relocation.offset          # address of the instruction being patched
rcls  = arch.isa.relocation_map[relocation.reloc_type]      # by name string
reloc = rcls(None, offset=relocation.offset, addend=relocation.addend)
data  = section.data[off : off + reloc.size()]              # size() = token.Info.size//8 = 5
data  = reloc.apply(sym_value, data, reloc_value)
section.data[off:off+5] = data
```

`Relocation.apply` default (`encoding.py:631-643`): `token = self.token.from_data(data)`;
`setattr(token, self.field, self.calc(sym_value, reloc_value))`; return `token.encode()`.
`AtallaBR_Imm10_Relocation`, `AtallaMI_Abs_Imm25_Relocation`, `AtallaI_Abs_Imm7_Relocation` override
`apply` to do exactly the same thing explicitly.

| Relocation | `calc` (`relocations.py`) | Meaning |
|-----------|------|---------|
| `BR_i10` (`:8-25`) | `wrap_negative((sym - reloc) // 5, 10)` written to `AtallaBRToken.imm10` (= bits 31..39 ‖ bit 14) | PC-relative in **instructions**, relative to the **branch instruction's own address** (no +1). `wrap_negative` two's-complements into 10 bits. `//` is floor division; since both addresses are multiples of 5 within the section this is exact. |
| `MI_jal_i25` (`:27-34`) | `wrap_negative((sym - reloc) // 5, 25)` into `imm25` (bits 15..39) | same convention, 25-bit |
| `MI_abs_i25` (`:37-49`) | `(sym >> 7) & 0x1FFFFFF` into `imm25` | upper 25 bits of a 32-bit absolute address; pairs with `lui_s` semantics `rd = imm25 << 7` (consistent with `pattern_const_i32_large`, `instructions.py:545-551`) |
| `abs_imm7` (`:52-64`) | `sym & 0x7F` into `imm12` | low 7 bits, added by `addi_s` |
| `I_i12` (`:67-72`) | `sym & 0xFFF` | unused |

Verified numerically (ch. 21): `blt_s` at `0x82` → `main_block3` at `0x8C`: `calc = 2`, bytes
`25 00 86 84 00`; `jal x0, main_block2` at `0xA5` → `0x7D`: `calc = -8` → `wrap_negative` → `0x1FFFFF8`,
bytes `2D 00 FC FF FF`; `lui_s x9, g` with `g` at `0x80000` → `imm25 = 4096`, bytes `B0 04 00 08 00`.

Because the branch offset is relative to the branch itself, `jal x0, next_label` where the label is the
very next instruction encodes `offset = 1` (see `jal x0, main_epilog` → `# offset=1` in the disassembly).
Whether the hardware interprets the offset relative to the branch address or to PC+5 is **Unknown** from
this repo; the disassembler (`disassemble.py:172-175`) assumes “relative to the branch”. If the ISA is
PC+5-relative, every branch is off by one instruction. The commented-out alternative `calc` at
`relocations.py:16-19` shows the authors considered exactly this.

## 14.5 The global-variable mis-lowering (verified)

`pattern_label1` (`instructions.py:718-725`):
```python
context.emit(Luil(d, ln))      # lui_s d, <label>   (MI_abs_i25)
context.emit(Addil(d, d, ln))  # addi_s d, d, <label>  (abs_imm7)
context.emit(Lws(d, 0, d))     # lw_s d, 0(d)        ← loads the variable's CONTENT
return d                       # …but the tree wanted the ADDRESS
```
Upstream RISC-V (`ppci/arch/riscv/instructions.py:944-951`) does the same three instructions but with
`ln = context.frame.add_constant(tree.value)`: the address is stored in the **literal pool** and the `lw`
loads the address from the pool. The Atalla port replaced the pool label with the symbol itself
(`dcd(str)` raises `NotImplementedError` for Atalla, `instructions.py:322-328`) and kept the `lw_s`.
Result: `g = g + 1` compiles to `lui/addi/lw/lw ... lui/addi/lw/sw` — reading `*(*(&g))` and storing
to address `*(&g)`. Every global-variable access is wrong. `test_relocations.py`'s “GLOBAL ADDRESS TEST”
happens to also be broken (ch. 18) so it does not catch this.

## 14.6 ELF relocation numbers

`AtallaArch.get_reloc_type` (`arch.py:642-671`) maps names → `BR_i10:1, MI_jal_i25:2, MI_abs_i25:3, M_i12:4,
I_i12:5, abs_imm7:6` for the `.relacode` table written by `write_rela_table` (`elf/writer.py:347-395`,
`r_info = (r_sym << 8) + r_type`). `M_i12` has no relocation class; `absaddr32` (from `Dcd2`) has no number
→ `NotImplementedError` if a global pointer initialiser is ever linked to ELF (Inferred). These numbers are
arbitrary (“For now, we use arbitrary numbers”) and the entries are stale because relocations were already
applied.
