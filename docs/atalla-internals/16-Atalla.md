# 16 — The Atalla backend, end to end

This chapter is the single place that lists every Atalla-specific mechanism and where generic PPCI
hands over to it. Details of each stage are in chapters 09–15.

## 16.1 Registration and selection

* `ppci/arch/atalla/__init__.py` exports `AtallaArch`; `ppci/arch/target_list.py:18-21` puts it first in
  `target_classes`; `target_class_map["atalla"]`; `create_arch("atalla")` (lru-cached).
* Selected by `-m atalla` (`atalla_cc` passes it always). `AtallaArch.name = "atalla"` is also used as a
  string key in: `elf/writer.py:37,98`, `irdag.py:524,556` (inline-asm vector outputs), and the broken
  `api.py:271`.

## 16.2 Types and register classes (`arch.py:223-245`, `registers.py`, `vector_registers.py`, `mask_registers.py`)

See ch. 05 §1/§6 and ch. 11 §1. Key facts: `i32`/`u32`/`ptr`/`bf16`/small ints share the scalar class;
`vec` = `v1..v31`; `mask` = `m1..m15`; `v0` and `m0` are reserved constants used by patterns
(`v0` as the add-zero source in moves, `m0` as “no mask”); `x32`/`x33` are the scratchpad stack/frame
pointers and never allocated.

## 16.3 Instruction definitions

* Scalar (`instructions.py`): R-type `add/sub/mul/div/mod/or/and/xor/sll/srl/sra_s`, bf16 R-type
  `add/sub/mul/rcp/slt/sqrt_bf`, `stbf_s` (int→bf16), `bfts_s` (bf16→int); I-type `addi…srai_s`;
  branches `beq/bne/blt/bge/bgt/ble_s`; memory `lw_s`, `sw_s`; `li_s`, `lui_s`; `jal`, `jalr`; `halt`, `nop`;
  pseudo `Align`, `Section`; relocatable `Luil`, `Addil`.
* Vector/mask/DMA (`vector_instructions.py`): `add/sub/mul/gemm_vv`, `add/sub/mul_vs`, `expi/lw/rsum/rmin/rmax_vi`,
  `mgt/mlt/meq/mneq_mvv`, `mgt/mlt/meq/mneq_mvs`, `vreg_ld`, `vreg_st`, `mv_stm`, `mv_mts`, `vmov_vts`,
  `scpad_ld`, `scpad_st`. Commented-out: `div_vv`, `and/or/xor_vv`, `addi/subi/muli/divi_vi`, `sqrti_vi`,
  `not_vi`, `shift_vi`, `div_vs`, `shift_vs`.
* Every class carries `patterns` (bit layout) and `syntax` (assembly text). The assembler grammar and the
  `-S` printer are both derived from `syntax`, so `-S` output is re-assemblable by `AtallaAssembler`.

## 16.4 Where each IR construct becomes Atalla code (map)

| IR | Pattern function | Instruction(s) |
|----|------------------|----------------|
| int `+ - * / % & | ^ << >>` | `instructions.py:625-1339` | R-type or I-type (`< 4096` immediates; note the condition is only an upper bound, so a negative constant like `-5` also matches the I-form and is wrapped into 12 bits by the token setter) |
| bf16 `+ - * /`, unary `-`, `sqrt` | `:1440-1481` | `add_bf`, `sub_bf`, `mul_bf`, `rcp_bf`+`mul_bf`, `sub_bf x0`, `sqrt_bf` |
| bf16 compare | `:1498-1513` | call to `float16_*` → **unresolvable** |
| int↔bf16, int→vec | `:1484-1495` | `bfts_s`, `stbf_s` |
| vec `+ - *` (vv), with scalar (vs) | `vector_instructions.py:362-378`, `:552-568` | `add/sub/mul_vv`, `add/sub/mul_vs` |
| `vec_op_masked` EXP/RSUM/RMIN/RMAX | `:493-549` | `expi_vi d, v, 0, m` (constant ignored), `rsum/rmin/rmax_vi d, v, bf16bits, m` |
| `vec_op_masked` with `|`, `<<`, `&`, `>>`, `/`, `^`, `SQRT`, `~` | none | **`Tree … not covered` crash** (the IR accepts them; the DAG produces `ORVEC`, `SHLVEC`, … which have no rule) |
| `gemm` | `:406-410` | `gemm_vv` |
| `make_mask` | `:224-270` | `m{gt,lt,eq,neq}_m{vv,vs}` |
| mask ↔ int | `:212-222` | `mv_mts`, `mv_stm` |
| `v[i]` | `:616-620` | `vmov_vts` (index must be a constant: pattern is `VECIDXBF16(vecreg, CONSTI32)`; a variable index → not covered) |
| `vector_load/store` | `:637-686` | `vreg_ld/st` with immediate `num_cols`, `sid` |
| vec spill / address-taken vec | `:287-323` | `addi_s t, x33, off; li_s c, 1; vreg_ld/st v, t, c, 31, 3` (hard-coded `num_cols=31`, `sid=3`, `rs2=1`) |
| `load_weights` | `:622-625` | `lw_vi v0, v, 0, m0` |
| `scpad_load/store` | `:627-635` | `scpad_ld/st` |
| control flow | `instructions.py:445-449`, `:594-603` | `jal x0`, `b*_s` + `jal x0` |
| calls/returns | `arch.py:489-568` | `jal x1`, `jalr x0, x1, 0` |
| globals | `:718-725` | `lui_s/addi_s` + spurious `lw_s` (bug) |

## 16.5 Scratchpad (`scpad`) model — the most Atalla-specific mechanism

* Two stacks: the ordinary one (`x2`/`x8`, main memory, word loads/stores) and a **scratchpad stack**
  (`x32`/`x33`) for 64-byte vectors. `AtallaArch.scpad_fp_start = 2000000` is written into `x32`/`x33`
  by the prologue of **`main` only** (`arch.py:333-336`); any other entry point starts with garbage in
  `x32`. (Verified.)
* Allocation policy: `SelectionGraphBuilder.do_alloc` (`irdag.py:438-441`) sends any `Alloc` with
  `amount == 64` to `Frame.scpad_alloc`, producing `StackLocation(kind=SCPAD)` and a `SCPADREL<ptr>` node
  (`wants_vreg=False`). Two rule families consume it: `SCPADRELU32` → `reg` (`vector_instructions.py:325-346`,
  `addi_s d, x33, off` marked `spadrel`) for taking the address (`&v_add` in `sample.s` shows
  `addi_s x9, x33, -192`), and `FPRELU32` with `kind == SCPAD` → `reg`/`mem` (`instructions.py:753-778`)
  — note the latter matches the tree name `FPRELU32`, which the DAG never produces for scratchpad slots;
  the `mem` form that *is* used by `LDRVEC/STRVEC(mem)` comes from the spill generator's
  `Tree("FPRELU32", value=slot)` (`registerallocator.py:193-196`) whose slot has `kind=SCPAD`. So
  address-taken vectors go through `SCPADRELU32` and spills through `FPRELU32(kind=SCPAD)`; both end
  at `x33 + off`.
* Register spills of `AtallaVectorRegister` also go to `scpad_alloc` (`registerallocator.py:709-710`).
* `Frame.scpad_alloc` refuses any size other than 64 (`stack.py:80-81`).
* Prologue/epilogue bracket the frame (`x33 = x32; x32 -= size` / `x32 = x33`) and save/restore `x33` on
  the ordinary stack at `8(x2)`.
* Addressing within the frame uses `vreg_ld/st v, base, c, 31, 3` with `c = li_s 1` — the meaning of
  `rs2`, `num_cols = 31`, `sid = 3` for a stack slot is a hardware convention that is **Unknown** here
  (the README describes `sid` as “Scratchpad ID”).
* `ScpadOffsetAddress` (`debuginfo.py:259`) records it for debug info only.

## 16.6 DMA / SDMA

`scpad_ld`/`scpad_st` (`AtallaSDMAToken`: `rs1_rd1`, `rs2`, `rs3`) are exposed one-to-one as the
`scpad_load(x, y, z)`/`scpad_store` intrinsics and lowered with no interpretation of the operands
(`SCPADLD(reg, reg, reg)`). The README documents `rs3` as packed metadata `[31:30]=scratchpad id,
[29:25]=rows, [24:20]=cols, [19:0]=cols in full matrix`. The compiler does not check or pack anything;
the `rs1_rd1` operand is declared `read=True, write=True` (`vector_instructions.py:584`), so the
allocator treats the first argument's register as **clobbered by the instruction** (it is a def) — the
C variable passed as `x` is not updated, because the value was moved into a fresh vreg first. Whether
the hardware writes back to `rs1_rd1` is Unknown.

## 16.7 Immediates and constants

* `li_s` carries a 25-bit signed immediate (`CONSTI32` rule requires `-2²⁵ ≤ v < 2²⁵`, `CONSTU32` `< 2²⁵`).
* `lui_s` + `addi_s` for unsigned constants ≥ 2²⁵ (upper 25 bits `>>7`, low 7 bits). **Signed** constants
  ≥ 2²⁵ crash (`Tree not covered`); negative constants < −2²⁵ likewise (Inferred).
* I-type immediates: patterns check `< 4096` only (no lower bound) — `addi_s d, a, -3000` would fail in
  `Token.__setitem__` (`value {v} cannot be fit`) only for `v ≥ 4096`; negatives wrap silently. `-2048…-1`
  are fine; `-4096` would wrap to `0` incorrectly (Inferred).
* bf16 constants: `_f32_to_f16_bits` (`ppci/wasm/execution/runtime.py:165-172`) = top 16 bits of the
  IEEE-754 single (truncation, no rounding) → bfloat16 bits loaded with `li_s`.

## 16.8 Symbol handling and the assembler

* `AtallaAssembler` (`arch.py:172-193`) extends `BaseAssembler` with a literal pool API; `gen_asm_parser`
  derives grammar rules from every instruction `Syntax`, including register names and `aka` aliases.
  Used for inline `asm()` templates only (`codegen.py:346-371`) — `atalla_cc` has no `.s` → `.o` mode
  (`python -m ppci asm -m atalla` exists generically but is unverified for Atalla).
* `AtallaAsmPrinter` prints `.section name` for `SectionInstruction` and `nop` for `Nop`; otherwise `str(ins)`.

## 16.9 ELF

`ElfMachine.ATALLA = 0x270F` (9999). ELF class 32, little-endian, `ET_REL`, no program headers
(ch. 02, ch. 15). Code section `sh_addralign = 5`.

## 16.10 Generic PPCI ends / Atalla begins — the boundary list

| Generic | Boundary | Atalla |
|---------|----------|--------|
| `ppci/lang/atalla_c` is a private copy | — | everything in it is Atalla-owned |
| `ir.py` core classes | `:157-165`, `:1395-1627` | new types/nodes |
| `SelectionGraphBuilder` generic handlers | `irdag.py:224-351` (`do_gemm`…), `:438-446` (`scpad_alloc`), `:524,556` | Atalla handlers |
| `DagSplitter`, `TreeSelector`, `BurgSystem` | `arch.isa.patterns` | pattern functions in `atalla/*instructions.py` |
| `GraphColoringRegisterAllocator` | `registers.py` classes; `registerallocator.py:186-187,709-712` | class lists; VEC spill hack |
| `CodeGenerator.generate_function` | `arch.gen_*`, `arch.peephole` | `AtallaArch` methods |
| `BinaryOutputStream`/`Linker` | `Instruction.encode`, `relocations()`, `isa.relocation_map` | Atalla tokens/relocations |
| `ElfWriter` | `arch.name`, `arch.get_reloc_type` | table in `arch.py:649-656` |
