# 02 — Entry points

## 1. `./atalla_cc` (repo root, Python script)

`parse_args()` (`atalla_cc:22-96`): `sources+`, `-S`, `-c`, `-o`, `-m` (default `atalla`),
`-O` (default `2`), `--super-verbose`, `--dis`, `--test-reloc`, `--verbose`, `--cc-flag` (repeatable,
forwarded to each compile), `--ld-flag` (repeatable).

`main()` (`:174-186`):

```
if -S:   compile_to_asm()            # one `python -m ppci atalla_cc ... -S -o x.s` per source
else:    compile_to_objects()        # one `... -c -o x.o` per source (x.o placed NEXT TO the source)
         if not -c: link_objects()   # `python -m ppci ld x.o ... -o out.elf -L atalla_layout.mmap`
run_post_steps()                     # --dis: dump_elf.py + disassemble.py (both hard-code output.elf in CWD)
                                     # --test-reloc: test_relocations.py (needs disassembly.txt + atalla_layout.mmap in CWD)
```

Verified facts that matter:
* `compiler_base()` (`:100-112`) always passes `-m <arch> -O<level>`; `--super-verbose` is forwarded
  but **no ppci parser defines it** (grep of `ppci/cli` finds nothing) → argparse error if used. (Inferred: not executed.)
* Object files are written beside the sources (`source_to_output`, `:19-20`), e.g. `atalla_tests/sample.o`.
* `link_objects()` (`:141-165`) adds `-L <repo>/atalla_layout.mmap` unless a `--ld-flag` already
  supplies `-L`/`--layout`.
* `PYTHON = sys.executable` — the same interpreter that runs the script.
* The script does `subprocess.run(check=True)`; any failure aborts with the child's exit code.

## 2. `python -m ppci <subcommand>` (`ppci/__main__.py`)

`main()` maps `ld` → `link` (`aliases`), imports `ppci.cli.<subcommand>` and calls its `main`
or the function named like the subcommand. Two subcommands matter: `atalla_cc` and `link`.

**Import-time side effects (Verified):**
* `ppci/arch/target_list.py:37` — `print(target_classes[0])` prints
  `<class 'ppci.arch.atalla.arch.AtallaArch'>` to stdout every time any CLI runs.
* `ppci/api.py:56-57` — `from vliw_packetizer import vliw_packetizer`, `from instruction_latency import latency`.
  These modules live at the **repo root**. `python -m ppci` from the repo root works because `''`/CWD is
  on `sys.path`. The package metadata (`pyproject.toml`) only ships `ppci`, so an installed copy would
  fail to import `ppci.api`. (Inferred: not executed from an installed copy.)
* `ppci/codegen/print_dag.py:12` — `import pydot` at import (pulled in by `instructionselector.py:68`).
  Without `pydot` the compiler does not start.

## 3. `ppci.cli.atalla_cc.atalla_cc(args)` (`ppci/cli/atalla_cc.py:47-86`)

Parser parents: `base_parser` (`--log`, `--report`, `--html-report`, `--text-report`, `-v`, `--pudb`),
`march_parser` (`-m`, `--mtune`), `compile_parser` (`-o`, `-g`, `-S`, `--ir`, `--wasm`, `--pycode`,
`-O {0,1,2,s}`, `--instrument-functions`), `coptions_parser` (C options from `ppci/lang/c/options.py`,
i.e. the *generic* C options module, not the atalla_c one — `:10`).

Flow:
1. `LogSetup(args)` (`ppci/cli/base.py:145`) attaches a root logger at `args.log` level; `-v` forces DEBUG;
   `--html-report f` creates `HtmlReportGenerator`, else `DummyReportGenerator`. `--pudb` installs a
   post-mortem `sys.excepthook`.
2. `march = get_arch_from_args(args)` → `create_arch("atalla", options=())`
   (`ppci/arch/target_list.py:44-51`, `lru_cache`d → **one `AtallaArch` instance per process**).
3. `coptions = COptions(); coptions.process_args(args)`.
4. `-E` → `api.preprocess`; `--ast` → `create_ast` from the **generic** `ppci.lang.c` (`:9`, so `--ast`
   would parse with the non-Atalla parser; Inferred, not executed); otherwise for each source:
   `api.atalla_c_to_ir(src, march, coptions, reporter)` then `do_compile(ir_modules, march, reporter, args)`.

## 4. `do_compile` (`ppci/cli/compile_base.py:49-90`)

```
for m in ir_modules: api.optimize(m, level=args.O, reporter)
if --ir:  irutils.Writer(file).write(m)                       # textual IR
elif -S:  stream = TextOutputStream(printer=march.asm_printer, f=file)
          for m: api.ir_to_stream(m, march, stream, reporter)  # assembly text
else:     obj = api.ir_to_object(ir_modules, march, reporter, debug=args.g); obj.save(file)  # JSON object
          logger.warning("TODO: Linking with stdlibs")
```

Note `-c` is accepted by the CLI parser but never read (`# TODO: what to do with the -c option?`, `:59`).
Object output is the default whenever `-S`/`--ir` are absent.

## 5. `python -m ppci ld` (`ppci/cli/link.py:55-72`)

`api.link(objs, layout, debug, partial_link=-r, entry, libraries)` → `Linker.link` (ch. 14) →
`create_platform_executable` → `api.objcopy(obj, None, "elf", out)` (`ppci/api.py:561-579`).
`objcopy` picks `elf_type = "executable" if obj.is_executable else "relocatable"`, and
`ObjectFile.is_executable` is `entry_symbol_id is not None` (`ppci/binutils/objectfile.py:240-245`).
`atalla_layout.mmap` has no `ENTRY(...)` and `atalla_cc` passes no `-e`, so the output is written as
**`ET_REL`** (`e_type = 1`, verified in the hexdump of ch. 21: `0100 0f27` at offset 0x10, and the
`.relacode` section name in the string table). Consequences (verified in `ppci/format/elf/writer.py`):
* `write_images()` (`:131-132`) runs only for `ET_EXEC`/`ET_DYN`, so **no program headers / LOAD
  segments** are written (`e_phnum = 0`). Sections still carry their linked `sh_addr` (`:277`).
* `write_rela_table()` (`:137-138`) writes a `.relacode` section using `AtallaArch.get_reloc_type`
  (`ppci/arch/atalla/arch.py:642-671`) for the type numbers.
* Relocations **were nevertheless applied** in the section bytes because `partial_link=False` made
  `Linker.link` run `do_relocations()` (`ppci/binutils/linker.py:163-164`). The `.relacode` table is
  therefore a stale copy of already-applied relocations.

## 6. Python API entry points (`ppci/api.py`)

* `atalla_c_to_ir(source, march, coptions, reporter)` (`ppci/lang/atalla_c/api.py:20`).
* `optimize(ir_module, level, reporter)` (`:195`).
* `ir_to_stream(ir_module, march, output_stream, reporter, debug, opt)` (`:256`) — creates a fresh
  `CodeGenerator` each call, calls `ir_module.display()` (**prints the whole IR module to stdout**, `:269`),
  then `generate`. Line `271` `if march == "atalla"` compares an `AtallaArch` object with a string → always
  False → the packetizer never runs.
* `ir_to_object(ir_modules, march, reporter, debug, opt, outstream)` (`:284`) — builds
  `MasterOutputStream([BinaryOutputStream(obj), FunctionOutputStream(list.append), outstream?])`.
* `atalla_cc(source, march, ...)` (`:379`) — API convenience; not used by the CLI.
* `link(...)` re-exported from `ppci/binutils/linker.py`.

## 7. Entry points that exist but are not on the Atalla path

`main.py` (obsolete), `ppci/cli/cc.py` (generic C), all other `ppci/cli/*`, `ppci/build` recipes.
