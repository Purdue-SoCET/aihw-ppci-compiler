# 04 — Call graph

Indentation = calls. `→` = returns/produces. Only behaviour-determining calls are listed.
File paths are relative to the repo root; `atalla/` = `ppci/arch/atalla/`, `cg/` = `ppci/codegen/`.

## A. Compile one source to an object

```
atalla_cc:main()                                                        [atalla_cc:174]
  compile_to_objects() → subprocess: python -m ppci atalla_cc -m atalla -O2 f.c -c -o f.o
    ppci/__main__.py:main() → importlib ppci.cli.atalla_cc → atalla_cc(cmd_args)
      ppci/cli/atalla_cc.py:atalla_cc(args)                             [:47]
        LogSetup(args).__enter__                                        [ppci/cli/base.py:163]
        get_arch_from_args(args) → create_arch("atalla") → AtallaArch() [target_list.py:45; atalla/arch.py:199]
          Isa.__add__(isa, data_isa)                                    [ppci/arch/isa.py:34]
          ArchInfo(type_infos, register_classes) → value_classes, alias [ppci/arch/arch_info.py:37-60]
          AtallaAssembler().gen_asm_parser(isa)                         [ppci/binutils/assembler.py:168]
        api.atalla_c_to_ir(src, march, coptions, reporter)              [ppci/lang/atalla_c/api.py:20]
          CBuilder(march.info, coptions).build(src, filename)           [builder.py:23]
            CContext(coptions, arch_info)                               [context.py:25-90]  type sizes
            _parse(src, filename, context)                              [builder.py:67]
              CPreProcessor(coptions).process_file(src, filename) → tokens
              CSemantics(context); CParser(coptions, semantics)
              prepare_for_parsing(tokens, parser.keywords)
              parser.parse(tokens) → CompilationUnit AST
                … parse_primary_expression: intrinsic keywords          [parser.py:1182-1320]
                  semantics.on_gemm/on_vec_op_masked/on_make_mask/…     [semantics.py:992-1083]
                … on_binop → get_common_type (vec rank 100 > float 90)  [semantics.py:792, 1412]
                … coerce (float→vec: no cast; int→vec: ImplicitCast)     [semantics.py:1290-1345]
            CCodeGenerator(context).gen_code(ast) → ir.Module           [codegenerator.py:77]
              gen_global_variable → ir.Variable                         [:163]
              create_function → Builder.new_function/new_procedure      [:355-403]
              gen_function_def                                          [:406]
                emit_alloca per param/local → ir.Alloc + ir.AddressOf   [:121]
                gen_compound_statement → gen_stmt → gen_expr …          [:503, :996]
                  gen_binop → Builder.emit_binop → ir.Binop             [:1249]
                  gen_call → ir.FunctionCall / ir.ProcedureCall         [:1421]
                  gen_vec_op_masked → Builder.emit_vec_op_masked        [:1586; irutils/builder.py:163]
                  gen_vector_load → ir.VectorLoad                       [:1625]
                  gen_inline_assembly → ir.InlineAsm                    [:806]
                  _load_value → Builder.emit_load; _store_value → ir.Store [:1070, :1098]
                ir_function.delete_unreachable()                        [:502]
        do_compile(ir_modules, march, reporter, args)                   [ppci/cli/compile_base.py:49]
          api.optimize(m, level, reporter)                              [ppci/api.py:195]
            verify_module(m)                                            [ppci/irutils/verify.py:15]
            for p in [Mem2RegPromotor, RemoveAddZeroPass, ConstantFolder, CSE, TailCall,
                      LoadAfterStore, DeleteUnusedInstructions, CleanPass]*3: p.run(m)
              Mem2RegPromotor.on_function → is_alloc_promotable / promote  [ppci/opt/mem2reg.py:218, 12, 144]
            verify_module(m)
          api.ir_to_object(ir_modules, march, reporter, debug)          [ppci/api.py:284]
            ObjectFile(march); BinaryOutputStream(obj); MasterOutputStream([...])
            api.ir_to_stream(m, march, output_stream, reporter, debug, opt)   [:256]
              CodeGenerator(march, reporter, optimize_for="speed")     [cg/codegen.py:41]
                SelectionGraphBuilder(arch)                             [cg/irdag.py:135]
                InstructionSelector1(arch, sgb, reporter, weights)     [cg/instructionselector.py:281]
                  BurgSystem(); add_terminal ×N; add_rule(CALL, ASM, UND*, every arch.isa.pattern)
                GraphColoringRegisterAllocator(arch, selector, reporter) [cg/registerallocator.py:212]
              verify_module(m); m.display()  (stdout print)             [:266-269]
              CodeGenerator.generate(m, output_stream, debug)           [cg/codegen.py:62]
                output_stream.select_section("data"); _mark_global(externals); SetSymbolType
                generate_global(var) per ir.Variable                    [:100]
                output_stream.select_section("code")
                generate_function(fn, output_stream)  ← see B           [:143]
            obj.save(file) → JSON                                       [ppci/binutils/objectfile.py:367]
```

## B. `CodeGenerator.generate_function` (per IR function) — the core

```
generate_function(ir_function, output_stream)                           [cg/codegen.py:143]
  split_block(...) while len(block) > 200                               [:156-165]
  _mark_global; output_stream.emit(SetSymbolType(name,"func"))
  frame = arch.new_frame(name, fn) → Frame(name, fp_location=TOP)       [ppci/arch/arch.py:24; stack.py:50]
  select_and_schedule(fn, frame) → instruction_selector.select(fn, frame)   [:225 → instructionselector.py:370]
    function_info = FunctionInfo(frame)                                 [cg/irdag.py:70]
    prepare_function_info(arch, function_info, fn)                      [cg/irdag.py:24]
      Label(fn.name+"_epilog"); label_map[block] = Label(block.name)
      phi_map[phi] = frame.new_reg(arch.get_reg_class(ty=phi.ty), twain=phi.name)
      arch.determine_arg_locations(arg_types) → [R12..R17 | StackLocation]   [atalla/arch.py:570]
      arg_vregs[i] = frame.new_reg(value_classes[ty], twain=name) | StackLocation
      rv_vreg = frame.new_reg(cls, "retval")
    sgraph = dag_builder.build(fn, function_info, frame.debug_db)      [cg/irdag.py:140]
      LABEL nodes for module variables/functions/externals
      ENTRY token; REG/FPREL nodes for arguments (chained)
      for block in depth_first_order(fn): block_to_sgraph(block)        [:190]
        ENTRY node; for ins: (if terminator: copy_phis_of_successors); f_map[type(ins)](self, ins)
          do_binop → SGNode(op+ty)                                       [:596]
          do_load/do_store → LDR/STR chained                             [:479, :488]
          do_c_jump → CJMP(value=(cond, yes, no)) chained                [:407]
          do_return → MOV(rv_vreg) + JMP(epilog) chained                 [:392]
          do_function_call → _prep_call_arguments (MOV into fresh vregs) → CALL(value=(target,args,rv)) → REG(ret_val) [:701]
          do_alloc → frame.alloc | frame.scpad_alloc → FPREL | SCPADREL  [:434]
          do_vec_op_masked → prepare_mask → SGNode(ADD/SUB/…VEC)         [:267]
          do_vector_load → VLOAD chained; do_vector_store → VSTORE       [:318, :337]
          do_inline_asm → MOV inputs; ASM node; STR outputs              [:500]
          do_phi → REG(phi vreg)                                          [:720]
        block_tails[block] = current token node; EXIT node
      sgraph.check()
    print("===== Selection DAG …"); sgraph.levels_by_block = group_nodes_by_depth(sgraph)   [:383-387]
    forest = dag_splitter.split_into_trees(sgraph, fn, function_info, debug_db)   [cg/dagsplit.py:26]
      assign_vregs → check_vreg: vreg for multi-use / volatile / cross-block outputs   [:58-78]
      per block: Label, then make_trees(nodes, tail) → topological_sort_modified → Tree objects, MOV wrappers [:86-134]
      epilog Label
    context = InstructionContext(frame, arch)                           [instructionselector.py:150]
    arch.gen_function_enter(args) → RegisterUseDef(defs=argregs); move(arg_vreg, R12..) | Lws(fprel)   [atalla/arch.py:539]
    munch_trees(context, forest)                                        [:489]
      print(tree) per tree
      Label → context.emit(label)  |  Tree → gen_tree → TreeSelector.gen(context, tree)   [:196]
        sys.check_tree_defined(tree); burm_label(tree) (bottom-up DP over rules)   [:206]
        apply_rules(context, tree, "stm")                                [:245]
          rule_f(context, tree, *kid_results)  ← the @isa.pattern function in atalla/instructions.py / vector_instructions.py
            context.new_reg(cls) → frame.new_reg; context.emit(Ins) → frame.emit; print("[emit] mapped …")
    arch.gen_function_exit(rv) → move(R10, rv_vreg); RegisterUseDef(uses={R10})   [atalla/arch.py:562]
  reporter.dump_frame(frame)
  register_allocator.alloc_frame(frame)                                 [cg/registerallocator.py:233]
    loop:
      init_data(frame)                                                  [:306]
        FlowGraph(frame.instructions) (leaders from ins.jumps)          [cg/flowgraph.py:51]
        cfg.calculate_liveness()  (fixpoint; per-instruction live_in/out)   [:107]
        frame.ig = InterferenceGraph(); calculate_interference(cfg)     [cg/interferencegraph.py:51]
        moves = [i for i in instructions if i.ismove]  → [] for Atalla
        worklists: precolored / spill / freeze / simplify (is_colorable = pq-test)   [:349-360]
      while: simplify | coalesc | freeze | select_spill                 [:249-262]
      spilled = assign_colors()                                         [:751]
      if spilled: rewrite_program(node) → frame.alloc | frame.scpad_alloc; MiniGen.gen_load/gen_store via TreeSelector   [:700]
    remove_redundant_moves(); apply_colors() → reg.set_color(...); frame.used_regs   [:787, :792]
  frame.instructions = arch.peephole(frame)                             [atalla/arch.py:448]
  peep_hole_stream = PeepHoleStream(MasterOutputStream([FunctionOutputStream, output_stream]))
  emit_frame_to_stream(frame, peep_hole_stream)                         [cg/codegen.py:242]
    emit_all(arch.gen_prologue(frame))                                  [atalla/arch.py:318]
    for ins: RegisterUseDef→skip | ArtificialInstruction→emit | InlineAssembly→_generate_inline_assembly | else assert colored; emit
      _generate_inline_assembly: replace %i by str(reg.get_real()); assembler.assemble(text, ostream)   [:346]
    emit_all(arch.gen_epilogue(frame)) (incl. litpool)                  [atalla/arch.py:390]
  peep_hole_stream.flush()
  arch.gen_function_exit((return_ty, None)) → RegisterUseDef → stuck in PeepHoleStream window (dropped)   [:204-210]
  reporter.dump_instructions(instruction_list, arch)
```

Every `output_stream.emit(ins)` above fans out (`MasterOutputStream.do_emit`) to
`BinaryOutputStream.do_emit` (encode + symbols + relocations) and/or `TextOutputStream.do_emit`.

## C. Link

```
python -m ppci ld a.o b.o -o out.elf -L atalla_layout.mmap
  ppci/cli/link.py:link(args)                                           [:55]
    api.link(objs, layout, debug, partial_link=False, entry=None, libraries=[])   [ppci/binutils/linker.py:20]
      get_object(f) → ObjectFile.load → deserialize (get_arch("atalla"))   [objectfile.py:26, 449]
      get_layout(file) → Layout.load → LayoutLoader (lexer+LR parser)  [layout.py:7, 251]
      Linker(march).link(objects, layout, ...)                          [linker.py:100]
        merge_objects → inject_object per object                        [:193, :199]
          per section: align output section to input alignment; append data; record offset
          per symbol: merge_global_symbol | inject_symbol (id remap)
          per relocation: RelocationEntry with shifted offset & remapped symbol id
        layout_sections(layout): section.address = mem.location (aligned); Image per MEMORY   [:309]
        check_undefined_symbols                                          [:416]
        do_relaxations (no-op: can_shrink False)                         [:426]
        do_relocations → _do_relocation per entry                        [:615, :623]
          sym_value = dst.get_symbol_id_value(id) = symbol.value + section.address
          reloc_value = section.address + entry.offset
          rcls = arch.isa.relocation_map[entry.reloc_type]; reloc = rcls(None, offset, addend)
          data = section.data[off:off+5]; data = reloc.apply(sym_value, data, reloc_value); write back
    create_platform_executable → api.objcopy(obj, None, "elf", out) → write_elf(obj, f, "relocatable")   [link.py:75; api.py:561; elf/writer.py:23]
      ElfWriter.export_object: write_sections, write_symbol_table, write_rela_table, write_string_table, section headers, header
```

## D. Dynamic dispatch points (where the “generic” call lands in Atalla code)

| Generic call site | Resolves to |
|-------------------|-------------|
| `arch.new_frame` | `MachineArchitecture.new_frame` (generic) → `Frame` |
| `arch.determine_arg_locations` | `AtallaArch.determine_arg_locations` (`atalla/arch.py:570`) |
| `arch.gen_function_enter/exit/call/prologue/epilogue` | `AtallaArch.*` |
| `arch.move(dst, src)` | `AtallaArch.move` (`:303`) — `Addis(dst,src,0)` or `AddVv(dst,src,V0,M0)` |
| `arch.peephole` | `AtallaArch.peephole` (only backend defining one; guarded by `hasattr`) |
| `arch.isa.patterns` | union of `@isa.pattern` decorators in `atalla/instructions.py` and `atalla/vector_instructions.py` (216 patterns, 106 instruction classes — counted at runtime) |
| `arch.isa.relocation_map[name]` | `AtallaBR_Imm10_Relocation`, `AtallaMI_JAL_Imm25_Relocation`, `AtallaMI_Abs_Imm25_Relocation`, `AtallaI_JALR_Imm12_Relocation`, `AtallaI_Abs_Imm7_Relocation`, plus `absaddr16/32/64` from `data_isa` |
| `arch.get_reloc_type` (ELF writer) | `AtallaArch.get_reloc_type` (`:642`) |
| `arch.asm_printer` | `AtallaAsmPrinter` |
| `arch.assembler` | `AtallaAssembler` |
| `arch.make_nop` | `AtallaArch.make_nop` → `Nop()` (opcode `0b0110001`) — only used by dead packetizers |
| `f_map[type(ir_instruction)]` in `SelectionGraphBuilder` | `do_<snake_case_of_class>` methods registered by the `@make_map` decorator (`cg/irdag.py:113-125`) — e.g. `ir.VecOpMasked` → `do_vec_op_masked` |
| `Instruction.encode` | `Constructor.set_patterns` via the class `patterns` dict, unless the class overrides `encode` (`BranchBase`, `Jal`, `Jalr`, `Luil`, `Addil`, `Adrl`) |
