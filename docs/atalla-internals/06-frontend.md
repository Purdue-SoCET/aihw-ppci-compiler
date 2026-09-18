# 06 — Frontend (`ppci/lang/atalla_c/`)

The package is a fork of `ppci/lang/c/`. The pipeline is unchanged; the Atalla work is in the type
system, the parser's intrinsic keywords, semantic checks, and IR generation for the intrinsics.

## 6.1 Pipeline inside the frontend (verified: `builder.py:23-74`)

```
CBuilder.build(src, filename)
  CContext(coptions, arch_info)          # type sizes/alignments, enum values, constant evaluation
  _parse():
    CPreProcessor(coptions).process_file(src, filename) → token list (macros, #include, …)
    CSemantics(context)                  # builds AST nodes, does type checking & coercion
    CParser(coptions, semantics)         # recursive-descent parser; calls semantics.on_* callbacks
    prepare_for_parsing(tokens, parser.keywords)   # turns identifiers that are keywords into keyword tokens
    parser.parse(tokens) → CompilationUnit
  CCodeGenerator(context).gen_code(compile_unit) → ir.Module
```

There is no separate “AST → typed AST” pass: typing happens inside the semantic callbacks while parsing.

## 6.2 Types

* `nodes/types.py:383-420` `BasicType` ids: `VOID, CHAR, UCHAR, SHORT, USHORT, INT, UINT, LONG, ULONG,
  LONGLONG, ULONGLONG, FLOAT, VA_LIST, VECTOR("vec"), MASK("mask")`. `DOUBLE`/`LONGDOUBLE` are commented out.
  `is_vector()` helper at `:83`.
* `scope.py:45-50`: the keywords `float`, `vec`, `mask` map to those ids (`RootScope`).
* `context.py:34-62` `type_size_map`: `VECTOR: (arch_info.get_size("vec"), get_alignment("vec"))` = (64, 64);
  `FLOAT: (2, 2)` hard-coded; `MASK` is **absent** from `type_size_map` (Inferred: `sizeof(mask)` or a
  `mask` local would raise `KeyError`; no test uses a `mask` variable).
* `codegenerator.py:38-62` `ir_type_map`: `FLOAT → ir.bf16`, `VECTOR → ir.vec`, `MASK → ir.mask`,
  `INT/UINT → i32/u32`, `LONG → i32`, `LONGLONG → i64` (no backend support). `get_ir_type` (`:1736`) maps
  pointers/arrays/functions → `ir.ptr`, structs/unions → `BlobDataTyp`.
* Type ranking for binary operators (`semantics.py:1420-1437`): `VECTOR = 100 > FLOAT = 90 > … > INT = 50`.
  So `vec op scalar` has result type `vec`.
* `coerce` (`semantics.py:1290-1345`): `float → vec` **no cast, no error** (`:1311-1312`); `int → vec`
  inserts `ImplicitCast` (`:1313-1314`); otherwise C rules. Consequence: `v * 3.6` keeps a `float` (bf16)
  operand; `v -= give_5()` produces `Cast(i32→vec)`, which the backend lowers with `stbf_s` into a **scalar**
  register (ch. 10). `ensure_integer` (`:1380`) also accepts vectors — so `make_mask(op, v1, v2, <vec>)`
  is not rejected by this check.

## 6.3 Lexing floats and the `float` literal path

`lexer.py:381-389 lex_float` emits token `FLOAT` for `digits.digits[e±digits]`. `parser.py:1122` →
`semantics.on_float` (`:763-768`) → `utils.float_num` (`:101-109`) → Python `float`, type `float` →
`NumericLiteral(value, float_type)`. In IR: `ir.Const(3.6, bf16)`. There is no suffix handling (`3.6f` is
not lexed as one token; Unknown behaviour).

## 6.4 Intrinsics: parsing

`parser.py:93-101` adds `gemm, vec_op_masked, make_mask, load_weights, scpad_load, scpad_store,
vector_load, vector_store, sqrt` to the keyword list, so they are **keywords, not identifiers** —
a user cannot declare a function named `sqrt`, and `#include <math.h>` would conflict (Inferred).

`parse_primary_expression` (`:1182-1320`) handles each: `consume(keyword)`, `(`, parse comma-separated
`parse_assignment_expression()`s (for `vec_op_masked`/`make_mask` a bare `STRING` token is taken as the
operator name, `:1201-1204`, `:1217-1220`), check the argument count (`error` otherwise), call the
matching `semantics.on_*`, `consume(")")`.

Argument count contract: `gemm` 3, `vec_op_masked` 4, `make_mask` 4, `load_weights` 1, `scpad_load` 3,
`scpad_store` 3, `vector_load` 4, `vector_store` 5, `sqrt` 1.

## 6.5 Intrinsics: semantics (`semantics.py:992-1083`)

| Intrinsic | Node (`nodes/expressions.py`) | Result type | Checks |
|-----------|-------------------------------|-------------|--------|
| `gemm(a,b,mask)` | `Gemm(arg1,arg2,mask)` (`:179`) | `vec` | none |
| `vec_op_masked(op,a,b,mask)` | `VecOpMasked(op,…)` (`:188`) | `vec` | none here; the **IR constructor** validates `op ∈ VecOpMasked.op` and operand kinds (`ppci/ir.py:1416-1442`) |
| `make_mask(op,a,b,mask)` | `MakeMask` (`:198`) | `mask` | validated in `ir.MakeMask` (`op ∈ {">","<","==","!="}`) |
| `load_weights(v)` | `LoadWeights` (`:209`) | `void` | `is_vector(v.typ)` |
| `scpad_load/store(x,y,z)` | `ScpadLoad/ScpadStore` | `void` | `ensure_integer` ×3 |
| `vector_load(addr,rows,cols,sid)` | `VectorLoad(addr,arg2,arg3,arg4)` | `vec` | integer ×4; `arg3`, `arg4` must be constant expressions (`ensure_constant`, `:1038-1039`) |
| `vector_store(v,addr,rows,cols,sid)` | `VectorStore` | `void` | vector first; integers; `arg3`,`arg4` constant |
| `sqrt(x)` | `Sqrt` | `float` | `x.typ.is_float` |
| `v[i]` on a `vec` | `VecIndex(base,index)` (`on_array_index`, `:1102-1103`) | `float` | index coerced to int; base must be an lvalue |

Note the README documents `vector_load(addr, num_rows, num_cols, sid)`; the code names the operands
`addr, arg2, arg3, arg4` and the backend feeds `arg2` to `rs2`, `arg3` to `num_cols`, `arg4` to `sid`
(ch. 10). There is no `num_rows` field in the encoding; `arg2` goes into a register.

## 6.6 Inline assembly (`semantics.py:646-700`, `codegenerator.py:806-820`)

Constraints accepted: outputs `=r`, `=v`; inputs `r` (coerced to `long`), `v`. Vector/scalar mismatch is an
error. `gen_inline_assembly` builds `ir.InlineAsm(template, clobbers)`, adds input values (rvalues) and
output *addresses* (lvalues). Down the pipeline (`irdag.py:500-566`) inputs are moved into fresh vregs,
outputs get fresh vregs typed `ir.vec` when the output alloca has `amount == 64` **and `arch.name == "atalla"`**
(`:524`, `:556`), and after the `ASM` node each output vreg is stored back to its address through a `STR`.
The template is assembled at emission time with `%i` replaced by the physical register name
(`codegen.py:346-371`), using the Earley grammar generated from the instruction `Syntax` objects — so
inline asm mnemonics/operand order must match `Syntax` exactly (e.g. `vreg_ld v1, x10, x9, 31, 1`).

## 6.7 IR generation details that shape the backend

* `gen_function_def` (`codegenerator.py:406-503`): entry block holds only `alloc`/`AddressOf`
  (`_allocs`, emitted at `:498-500`) plus a jump to `block1`. Parameters are stored into their allocas
  (`:440-447`) → after mem2reg they become SSA values named after the parameter.
* Locals: `emit_alloca` (`:121-142`) → `ir.Alloc("alloca", size, alignment)` + `ir.AddressOf`. For `vec`
  the size is 64 → the backend keys **on `amount == 64`** to pick the scratchpad stack (ch. 09). Any
  64-byte struct or `int[16]` local would be mis-routed to the scratchpad stack as well (Verified by
  reading `irdag.py:438-441`; not executed).
* `gen_return` (`:785-803`): `Return(value)` then **opens a new block**; if the function ends with `return`,
  that block is empty and unclosed, so `:483-494` warns "Function does not return a value" and appends
  `return 0`; the block is unreachable and deleted at `:502`. This warning is therefore **always** printed
  for normal functions and is not an error.
* Comparisons produce `gen_condition_to_integer` (`:973-994`): yes/no blocks and a `Phi` of constants 1/0.
  `if` uses `gen_condition` → `CJump` directly.
* Function calls (`:1421-1481`): struct returns pass a hidden pointer (`return_value_address`).
  Blob (struct) arguments are passed by value as `BlobDataTyp` → backend `StackLocation`/memcpy path.
* Global variables: `gen_global_variable` → `ir.Variable(name, binding, size, alignment, value=tuple of bytes/labels)`.

## 6.8 What the frontend does *not* do

No `double`, no `long long` backend support, no `switch` on vectors, no vector element assignment
(`v[i] = x` — `VecIndex` is not an lvalue; Inferred), no `mask` arithmetic. `float` is 16-bit bf16 with
no `f` suffix and no `double` promotion.
