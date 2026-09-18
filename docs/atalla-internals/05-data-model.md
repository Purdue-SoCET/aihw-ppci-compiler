# 05 — Data model and data lifecycle

## The lifecycle at a glance

```
C token/AST node (ppci/lang/atalla_c/nodes/*)           owned by CParser/CSemantics; consumed once by CCodeGenerator
  ↓ gen_expr / gen_stmt
ir.Instruction / ir.Value in ir.Block in ir.SubRoutine in ir.Module   owned by the Module; mutated by opt passes
  ↓ SelectionGraphBuilder (per function)
SGNode (op name + ir type) with SGValue edges (DATA/CONTROL)          owned by SelectionGraph; read-only afterwards
  ↓ DagSplitter
utils.tree.Tree (name like "ADDI32", value, children, state)         transient; consumed by TreeSelector
  ↓ @isa.pattern functions
arch.encoding.Instruction subclasses with Register operands           owned by Frame.instructions; mutated by RA (colors) and peephole
  ↓ emit_frame_to_stream / BinaryOutputStream
bytes in objectfile.Section + Symbol + RelocationEntry                 owned by ObjectFile
  ↓ Linker
merged Section (address assigned, bytes patched) + Image              owned by output ObjectFile
  ↓ ElfWriter
ELF section bytes on disk
```

## 1. IR types (`ppci/ir.py:20-165`)

`Typ` → `BasicTyp(name, bits)` (interned by `(name,bits)`, `:59-77`) → `IntegerTyp` (`Signed`/`Unsigned`),
`FloatingPointTyp`, **`VectorTyp`**, **`MaskTyp`**; `PointerTyp` (`ptr`, no size); `BlobDataTyp(size, alignment)`
(interned, used for structs and for every `Alloc`).

| Atalla type | Definition | Size in `ArchInfo` (`atalla/arch.py:223-243`) | Register class |
|-------------|-----------|-----|-----|
| `ir.bf16` | `FloatingPointTyp("bf16", 16)` (`:158`) | 2 B / align 2 | `reg` (scalar `x` register) |
| `ir.vec` | `VectorTyp("vec", 512)` (`:159`; `bits=32*16`, so `size=64`) | 64 B / align 64 | `vecreg` |
| `ir.mask` | `MaskTyp("mask", 32)` (`:160`) | 4 B / align 4 | `maskreg` |
| `"ptr"`, `ir.ptr` | → `ir.u32` | 4 B | `reg` |
| `"int"`, `"long"` | → `ir.i32` | 4 B | `reg` |
| `"float"` | → `ir.bf16` | | |

`ir.value_types` (`:162`) lists `vec`, `bf16`, `mask` first; `all_types = value_types + [ptr]`.
`i64`, `u64`, `f32`, `f64` exist as IR types but have **no** Atalla `TypeInfo` and no register class;
using them (e.g. `long long`) would fail in `ArchInfo.get_type_info` / `get_reg_class`. (Inferred.)

## 2. IR program structure (`ppci/ir.py`)

* `Module(name, debug_db)`: `externals`, `_functions`, `_variables`; `display()` prints via `irutils.print_module`.
* `GlobalValue(Value)` → `Variable(name, binding, amount, alignment, value)`, `SubRoutine` → `Function(return_ty)` / `Procedure`,
  `External*`.
* `SubRoutine` (`:354`): `blocks`, `entry`, `arguments` (`Parameter`s), `defined_names`/`make_unique_name`
  (this is where names like `tmp_14_75` come from), `delete_unreachable`, `calc_reachable_blocks`.
* `Block` (`:546`): `instructions`, `references` (jumps that target it), `phis`, `successors` (from the
  terminator's `targets`), `predecessors`, `is_closed`.
* `Instruction` (`:709`): `_var_map` + `uses` maintained by the `value_use(name)` property factory (`:682`)
  which calls `add_use/del_use` so `Value.used_by` is always consistent. `LocalValue(Value, Instruction)`.
* Relevant node classes: `Alloc(name, amount, alignment)` (type `BlobDataTyp`), `AddressOf(src)`, `Load`,
  `Store`, `Binop(a, op, b)`, `Unop`, `Cast`, `Const`, `Phi(inputs: {block: value})`, `FunctionCall`,
  `ProcedureCall`, `Jump`, `CJump(a, cond, b, lab_yes, lab_no)`, `Return`, `Exit`, `InlineAsm`, `CopyBlob`,
  and the Atalla nodes in `:1395-1627` (fields: `Gemm(arg1,arg2,mask)`, `VecOpMasked(op,arg1,arg2,mask)`,
  `VecIndex(arg1,index)`, `MakeMask(op,arg1,arg2,mask)`, `LoadWeights(arg)`, `ScpadLoad/ScpadStore(x,y,z)`,
  `VectorLoad(addr,arg2,arg3,arg4)`, `VectorStore(vec,addr,arg2,arg3,arg4)`, `SqrtBf(a)`).
  Constructors type-check operands (e.g. `VecOpMasked` requires `mask.ty` to be `MaskTyp` or `IntegerTyp`
  and at least one vector operand; `VectorLoad` requires integer operands).

Invariants the verifier enforces (`ppci/irutils/verify.py:39-187`): entry is `blocks[0]`; all blocks reachable;
every block ends in exactly one terminator; phi inputs match predecessors; each use dominates; `Binop`
operand types equal the result type **except** for `VectorTyp` results where only one operand must be `vec`
(`:131-137`). This relaxation exists for `vec * float` (the frontend leaves the `float` operand
alone, so the IR `Binop` has operands `vec` and `bf16`). For `vec - int` the frontend inserts an
`ImplicitCast` int→vec first (`semantics.py:1313`), so the IR sees `vec - vec`.

## 3. Selection graph (`ppci/codegen/selectiongraph.py`)

* `SGNode(op: Operation)`: `name` (an `Operation(op, ty)` whose `str` is e.g. `ADDI32`, `ADDVEC`, `LABEL`,
  `CALL`), `value` (payload: constant, vreg, `StackLocation`, `Label`, tuple for CJMP/CALL/ASM), `inputs`
  (list of `SGValue`), `outputs`, `group` (the `ir.Block`).
* `SGValue(name, kind ∈ {DATA, CONTROL, MEMORY}, node)`: `users`, `vreg` (assigned by `DagSplitter.check_vreg`
  or pre-set for REG nodes), `wants_vreg` (False for CONST, FPREL/SCPADREL, MVSTM, asm REG outputs, params
  on stack).
* `SGNode.volatile` = has any non-DATA input/output = is on the control chain. Chained nodes: ENTRY, EXIT,
  every LDR/STR/CALL/JMP/CJMP/MOV/ASM/VLOAD/VSTORE/LOADWEIGHTS/SCPADLD/SCPADST/MOVB, argument REG/FPREL nodes.
  **Not** chained: arithmetic, casts, CONST, LABEL, GEMM, MGT…, VECIDX, MVSTM, UND.
* Lifetime: one `SelectionGraph` per function; `function_info.value_map: ir.Value → SGValue`.

## 4. Trees (`ppci/utils/tree.py:11-52`)

`Tree(name, *children, value)` with a `state: State` slot filled by `burm_label` (`ppci/codegen/treematcher.py:1-26`:
`labels: {nonterminal: (cost, rule_nr)}`). Node names are exactly the SGNode `Operation` strings plus
`REG<ty>`/`MOV<ty>` wrappers inserted by the splitter. Trees are the *only* thing patterns see.

## 5. Machine instructions (`ppci/arch/encoding.py`)

* `Operand(name, cls, read, write)` (`:9`) — a `property` whose backing field is `_<name>`; `read/write`
  flags drive `used_registers`/`defined_registers` (`:339-361`). Setter asserts `isinstance(value, cls)`.
* `Constructor.__init__(*args, **kwargs)` (`:136-158`): positional args are matched to the operands in
  `Syntax` order; kwargs set arbitrary attributes (`jumps=`, `clobbers=`). `Instruction.__init__` adds
  `jumps=[]`, `ismove=False`, `clobbers=[]`, `extra_uses/defs`, then applies kwargs (`assert hasattr`).
* `InsMeta` (`:269`) registers every class with a class attribute `isa` into that `Isa.instructions`.
* `Instruction.encode()` (`:417`): `get_tokens()` instantiates the class `tokens`, `set_all_patterns`
  writes each `patterns` entry (`FixedPattern`/`VariablePattern`) into the token via
  `TokenSequence.set_field`, returns `tokens.encode()` bytes (little-endian, 5 bytes per token).
* `relocations()` (`:443`): from `gen_relocations()` (base) — but every Atalla class that needs a relocation
  overrides `relocations()` directly (`BranchBase`, `Jal`, `Luil`, `Addil`, `Adrl`), yielding e.g.
  `AtallaBR_Imm10_Relocation(self.imm10)` where `imm10` is the **label name string**.
* Per-instance dynamic attributes set by patterns: `fprel`, `scpadfprel`, `spadrel` (booleans read by
  `AtallaArch.peephole`), `is_nop` (dead packetizer).

Atalla instruction classes are generated by factories (`make_r`, `make_i`, `make_br`, `make_m_load/store`,
`make_mi`, `make_nop`, `make_vv/vs/vi/vm/vmv/vms/stm/mts/sdma/vts`) via `type(name, (Base,), members)`.
Class names: R-type `Adds` = `"add_s".title()+"R"` = `Add_SR`; I-type `addi_s_ins`; etc. The Python
binding names (`Adds`, `Addis`, …) are what the patterns use.

## 6. Registers (`ppci/arch/registers.py`, `atalla/*registers.py`)

* `Register(name, num=None, aliases, aka)`: physical when `num` given (`_color = num`), virtual when
  `num is None` (`_color = None` until `set_color`). `is_colored`, `color`, `num` (asserts colored for
  virtuals), `get_real()` → singleton via `from_num(color)`.
* Virtual registers are created **only** by `Frame.new_reg(cls, twain)` (`ppci/arch/stack.py:159-164`):
  names `vreg<N><twain>` from a per-frame generator, so numbering restarts at 0 for every function.
* `AtallaRegister.from_num` (`atalla/registers.py:14`) is **not** a `@classmethod`; it only works when called
  on an instance (`self.from_num(color)` inside `get_real`). `AtallaRegister.from_num(9)` raises
  `TypeError` (verified). `AtallaVectorRegister.from_num`/`AtallaMaskRegister.from_num` are proper classmethods.
* `AtallaRegister.__repr__` returns the physical name once colored (`x9`), else the vreg name — this is why
  `.s` output never shows vreg names.
* `bitsize`: `AtallaRegister` 32, `AtallaVectorRegister` 512, `AtallaMaskRegister` 32 → spill slot size
  (`registerallocator.py:707`).
* `SCPADSP.aka = "scpadsp"` is a **string, not a tuple** (`:66-67`); `make_register_rule_function` iterates
  `register.aka` → adds one-letter assembler aliases `s`,`c`,`p`,`a`,`d`… for `x32`/`x33`. (Verified by reading;
  harmless unless someone writes `s` in inline asm.)

## 7. Frame (`ppci/arch/stack.py:42-186`)

Fields: `name`, `instructions`, `used_regs`, `out_calls` (bytes of outgoing stack args per call),
`temps` (vreg name generator), `stacksize`/`alignment` (normal stack, FP-relative, grows to negative
offsets), **`scpad_stacksize`/`scpad_alignment`** (scratchpad stack), `constants` (literal pool
`(label, value)`), `debug_db`, and attributes attached later: `ig` (interference graph), `cfg`
(not set by this allocator — `live_ranges()` would fail), `node_to_insts`, `tree_owner`, `buckets_by_block` (never set).

`alloc(size, alignment)` (`:98`): grows `stacksize`, rounds to alignment, returns `StackLocation(-stacksize, size, NORMAL)`.
`scpad_alloc(size, alignment)` (`:77`): same on `scpad_stacksize`, **raises unless `size == 64`**, returns
`StackLocation(offset, 64, SCPAD)`.

## 8. Object-file model (`ppci/binutils/objectfile.py`)

`ObjectFile(arch)`: `sections` (`Section(name)`: `address`, `alignment` default 4, `data: bytearray`),
`symbols` (`Symbol(id, name, binding, value, section, typ, size)`), `relocations`
(`RelocationEntry(reloc_type: str, symbol_id, section, offset, addend)`), `images` (`Image(name, address)`
+ sections), `entry_symbol_id`. Serialised as JSON with hex strings.

## 9. Where each structure is mutated

| Structure | Created by | Mutated by | Consumed by |
|-----------|-----------|-----------|-------------|
| AST | `CParser`/`CSemantics` | `CSemantics.coerce` wraps nodes in `ImplicitCast` | `CCodeGenerator` |
| `ir.Module` | `CCodeGenerator.gen_code` | opt passes, `split_block` in codegen | `SelectionGraphBuilder` |
| `SelectionGraph` | `SelectionGraphBuilder.build` | `DagSplitter.assign_vregs` (sets `SGValue.vreg`) | `DagSplitter.make_trees`, `group_nodes_by_depth` |
| `Tree` forest | `DagSplitter` | `TreeSelector.burm_label` (sets `state`) | `TreeSelector.apply_rules` |
| `Frame.instructions` | pattern functions via `InstructionContext.emit` | RA (`replace_register`, insertions, `set_color`), `AtallaArch.peephole` (filters, `imm12 +=`) | `emit_frame_to_stream` |
| `Register._color` | `Frame.new_reg` (None) | `GraphColoringRegisterAllocator.apply_colors` | `Instruction.encode`, `__repr__` |
| `Section.data` | `BinaryOutputStream` | `Linker` (padding, relocation patching) | `ElfWriter` |
| `Symbol.value` | `BinaryOutputStream._new_symbol` | `Linker.inject_object` (offset shift) | `get_symbol_id_value`, ELF symtab |
