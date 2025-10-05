
C builder
---------

Welcome to the C building report for instructtest.c
module main functions: 1, blocks: 7, instructions: 90
==========================
module main;

global function i32 instruct_tests(i32 a, i32 b) {
  instruct_tests_block0: {
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_55 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_56 = &alloca_55;
    blob<4:4> alloca_57 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_58 = &alloca_57;
    blob<4:4> alloca_59 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_60 = &alloca_59;
    blob<4:4> alloca_61 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_62 = &alloca_61;
    blob<8:4> alloca_63 = alloc 8 bytes aligned at 4;
    ptr alloca_addr_64 = &alloca_63;
    blob<4:4> alloca_65 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_66 = &alloca_65;
    jmp instruct_tests_block1;
  }

  instruct_tests_block1: {
    store a, alloca_addr;
    store b, alloca_addr_56;
    i32 num = 0;
    store num, alloca_addr_58;
    ptr num_0 = 4;
    ptr tmp = alloca_addr_58 + num_0;
    i32 tmp_load = load alloca_addr;
    i32 num_1 = 4;
    i32 tmp_2 = tmp_load + num_1;
    store tmp_2, alloca_addr_60;
    ptr num_3 = 4;
    ptr tmp_4 = alloca_addr_60 + num_3;
    i32 tmp_load_5 = load alloca_addr_56;
    i32 num_6 = 255;
    i32 tmp_7 = tmp_load_5 & num_6;
    store tmp_7, alloca_addr_62;
    ptr num_8 = 4;
    ptr tmp_9 = alloca_addr_62 + num_8;
    i32 tmp_load_10 = load alloca_addr_60;
    i32 tmp_load_11 = load alloca_addr_62;
    i32 tmp_12 = tmp_load_10 ^ tmp_load_11;
    i32 tmp_load_13 = load alloca_addr_58;
    i32 tmp_14 = tmp_load_13 ^ tmp_12;
    store tmp_14, alloca_addr_58;
    i32 num_15 = 0;
    ptr typecast = cast num_15;
    ptr num_16 = 4;
    ptr tmp_17 = typecast * num_16;
    ptr tmp_18 = alloca_addr_64 + tmp_17;
    i32 tmp_load_19 = load alloca_addr_58;
    store tmp_load_19, tmp_18;
    i32 num_20 = 1;
    ptr typecast_21 = cast num_20;
    ptr num_22 = 4;
    ptr tmp_23 = typecast_21 * num_22;
    ptr tmp_24 = alloca_addr_64 + tmp_23;
    i32 num_25 = 0;
    ptr typecast_26 = cast num_25;
    ptr num_27 = 4;
    ptr tmp_28 = typecast_26 * num_27;
    ptr tmp_29 = alloca_addr_64 + tmp_28;
    i32 tmp_load_30 = load tmp_29;
    i32 num_31 = 1;
    i32 tmp_32 = tmp_load_30 + num_31;
    store tmp_32, tmp_24;
    i32 num_33 = 1;
    ptr typecast_34 = cast num_33;
    ptr num_35 = 4;
    ptr tmp_36 = typecast_34 * num_35;
    ptr tmp_37 = alloca_addr_64 + tmp_36;
    i32 tmp_load_38 = load tmp_37;
    store tmp_load_38, alloca_addr_66;
    ptr num_39 = 4;
    ptr tmp_40 = alloca_addr_66 + num_39;
    i32 tmp_load_41 = load alloca_addr_66;
    i32 tmp_load_42 = load alloca_addr_60;
    cjmp tmp_load_41 >= tmp_load_42 ? instruct_tests_block3 : instruct_tests_block4;
  }

  instruct_tests_block2: {
    i32 tmp_load_51 = load alloca_addr_58;
    i32 tmp_load_52 = load alloca_addr_66;
    i32 tmp_53 = tmp_load_51 + tmp_load_52;
    return tmp_53;
  }

  instruct_tests_block3: {
    i32 num_43 = 2;
    i32 tmp_load_44 = load alloca_addr_66;
    i32 tmp_45 = tmp_load_44 - num_43;
    store tmp_45, alloca_addr_66;
    jmp instruct_tests_block2;
  }

  instruct_tests_block4: {
    i32 tmp_load_46 = load alloca_addr_66;
    i32 tmp_load_47 = load alloca_addr_60;
    cjmp tmp_load_46 == tmp_load_47 ? instruct_tests_block6 : instruct_tests_block5;
  }

  instruct_tests_block5: {
    jmp instruct_tests_block2;
  }

  instruct_tests_block6: {
    i32 num_48 = 3;
    i32 tmp_load_49 = load alloca_addr_66;
    i32 tmp_50 = tmp_load_49 + num_48;
    store tmp_50, alloca_addr_66;
    jmp instruct_tests_block5;
  }

}
==========================
module main before optimization:
module main functions: 1, blocks: 7, instructions: 90
==========================
module main;

global function i32 instruct_tests(i32 a, i32 b) {
  instruct_tests_block0: {
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_55 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_56 = &alloca_55;
    blob<4:4> alloca_57 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_58 = &alloca_57;
    blob<4:4> alloca_59 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_60 = &alloca_59;
    blob<4:4> alloca_61 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_62 = &alloca_61;
    blob<8:4> alloca_63 = alloc 8 bytes aligned at 4;
    ptr alloca_addr_64 = &alloca_63;
    blob<4:4> alloca_65 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_66 = &alloca_65;
    jmp instruct_tests_block1;
  }

  instruct_tests_block1: {
    store a, alloca_addr;
    store b, alloca_addr_56;
    i32 num = 0;
    store num, alloca_addr_58;
    ptr num_0 = 4;
    ptr tmp = alloca_addr_58 + num_0;
    i32 tmp_load = load alloca_addr;
    i32 num_1 = 4;
    i32 tmp_2 = tmp_load + num_1;
    store tmp_2, alloca_addr_60;
    ptr num_3 = 4;
    ptr tmp_4 = alloca_addr_60 + num_3;
    i32 tmp_load_5 = load alloca_addr_56;
    i32 num_6 = 255;
    i32 tmp_7 = tmp_load_5 & num_6;
    store tmp_7, alloca_addr_62;
    ptr num_8 = 4;
    ptr tmp_9 = alloca_addr_62 + num_8;
    i32 tmp_load_10 = load alloca_addr_60;
    i32 tmp_load_11 = load alloca_addr_62;
    i32 tmp_12 = tmp_load_10 ^ tmp_load_11;
    i32 tmp_load_13 = load alloca_addr_58;
    i32 tmp_14 = tmp_load_13 ^ tmp_12;
    store tmp_14, alloca_addr_58;
    i32 num_15 = 0;
    ptr typecast = cast num_15;
    ptr num_16 = 4;
    ptr tmp_17 = typecast * num_16;
    ptr tmp_18 = alloca_addr_64 + tmp_17;
    i32 tmp_load_19 = load alloca_addr_58;
    store tmp_load_19, tmp_18;
    i32 num_20 = 1;
    ptr typecast_21 = cast num_20;
    ptr num_22 = 4;
    ptr tmp_23 = typecast_21 * num_22;
    ptr tmp_24 = alloca_addr_64 + tmp_23;
    i32 num_25 = 0;
    ptr typecast_26 = cast num_25;
    ptr num_27 = 4;
    ptr tmp_28 = typecast_26 * num_27;
    ptr tmp_29 = alloca_addr_64 + tmp_28;
    i32 tmp_load_30 = load tmp_29;
    i32 num_31 = 1;
    i32 tmp_32 = tmp_load_30 + num_31;
    store tmp_32, tmp_24;
    i32 num_33 = 1;
    ptr typecast_34 = cast num_33;
    ptr num_35 = 4;
    ptr tmp_36 = typecast_34 * num_35;
    ptr tmp_37 = alloca_addr_64 + tmp_36;
    i32 tmp_load_38 = load tmp_37;
    store tmp_load_38, alloca_addr_66;
    ptr num_39 = 4;
    ptr tmp_40 = alloca_addr_66 + num_39;
    i32 tmp_load_41 = load alloca_addr_66;
    i32 tmp_load_42 = load alloca_addr_60;
    cjmp tmp_load_41 >= tmp_load_42 ? instruct_tests_block3 : instruct_tests_block4;
  }

  instruct_tests_block2: {
    i32 tmp_load_51 = load alloca_addr_58;
    i32 tmp_load_52 = load alloca_addr_66;
    i32 tmp_53 = tmp_load_51 + tmp_load_52;
    return tmp_53;
  }

  instruct_tests_block3: {
    i32 num_43 = 2;
    i32 tmp_load_44 = load alloca_addr_66;
    i32 tmp_45 = tmp_load_44 - num_43;
    store tmp_45, alloca_addr_66;
    jmp instruct_tests_block2;
  }

  instruct_tests_block4: {
    i32 tmp_load_46 = load alloca_addr_66;
    i32 tmp_load_47 = load alloca_addr_60;
    cjmp tmp_load_46 == tmp_load_47 ? instruct_tests_block6 : instruct_tests_block5;
  }

  instruct_tests_block5: {
    jmp instruct_tests_block2;
  }

  instruct_tests_block6: {
    i32 num_48 = 3;
    i32 tmp_load_49 = load alloca_addr_66;
    i32 tmp_50 = tmp_load_49 + num_48;
    store tmp_50, alloca_addr_66;
    jmp instruct_tests_block5;
  }

}
==========================

Code generation
---------------

Target: atalla-arch

Log for global function i32 instruct_tests(i32 a, i32 b)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

==========================
global function i32 instruct_tests(i32 a, i32 b) {
  instruct_tests_block0: {
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_55 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_56 = &alloca_55;
    blob<4:4> alloca_57 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_58 = &alloca_57;
    blob<4:4> alloca_59 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_60 = &alloca_59;
    blob<4:4> alloca_61 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_62 = &alloca_61;
    blob<8:4> alloca_63 = alloc 8 bytes aligned at 4;
    ptr alloca_addr_64 = &alloca_63;
    blob<4:4> alloca_65 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_66 = &alloca_65;
    jmp instruct_tests_block1;
  }

  instruct_tests_block1: {
    store a, alloca_addr;
    store b, alloca_addr_56;
    i32 num = 0;
    store num, alloca_addr_58;
    ptr num_0 = 4;
    ptr tmp = alloca_addr_58 + num_0;
    i32 tmp_load = load alloca_addr;
    i32 num_1 = 4;
    i32 tmp_2 = tmp_load + num_1;
    store tmp_2, alloca_addr_60;
    ptr num_3 = 4;
    ptr tmp_4 = alloca_addr_60 + num_3;
    i32 tmp_load_5 = load alloca_addr_56;
    i32 num_6 = 255;
    i32 tmp_7 = tmp_load_5 & num_6;
    store tmp_7, alloca_addr_62;
    ptr num_8 = 4;
    ptr tmp_9 = alloca_addr_62 + num_8;
    i32 tmp_load_10 = load alloca_addr_60;
    i32 tmp_load_11 = load alloca_addr_62;
    i32 tmp_12 = tmp_load_10 ^ tmp_load_11;
    i32 tmp_load_13 = load alloca_addr_58;
    i32 tmp_14 = tmp_load_13 ^ tmp_12;
    store tmp_14, alloca_addr_58;
    i32 num_15 = 0;
    ptr typecast = cast num_15;
    ptr num_16 = 4;
    ptr tmp_17 = typecast * num_16;
    ptr tmp_18 = alloca_addr_64 + tmp_17;
    i32 tmp_load_19 = load alloca_addr_58;
    store tmp_load_19, tmp_18;
    i32 num_20 = 1;
    ptr typecast_21 = cast num_20;
    ptr num_22 = 4;
    ptr tmp_23 = typecast_21 * num_22;
    ptr tmp_24 = alloca_addr_64 + tmp_23;
    i32 num_25 = 0;
    ptr typecast_26 = cast num_25;
    ptr num_27 = 4;
    ptr tmp_28 = typecast_26 * num_27;
    ptr tmp_29 = alloca_addr_64 + tmp_28;
    i32 tmp_load_30 = load tmp_29;
    i32 num_31 = 1;
    i32 tmp_32 = tmp_load_30 + num_31;
    store tmp_32, tmp_24;
    i32 num_33 = 1;
    ptr typecast_34 = cast num_33;
    ptr num_35 = 4;
    ptr tmp_36 = typecast_34 * num_35;
    ptr tmp_37 = alloca_addr_64 + tmp_36;
    i32 tmp_load_38 = load tmp_37;
    store tmp_load_38, alloca_addr_66;
    ptr num_39 = 4;
    ptr tmp_40 = alloca_addr_66 + num_39;
    i32 tmp_load_41 = load alloca_addr_66;
    i32 tmp_load_42 = load alloca_addr_60;
    cjmp tmp_load_41 >= tmp_load_42 ? instruct_tests_block3 : instruct_tests_block4;
  }

  instruct_tests_block2: {
    i32 tmp_load_51 = load alloca_addr_58;
    i32 tmp_load_52 = load alloca_addr_66;
    i32 tmp_53 = tmp_load_51 + tmp_load_52;
    return tmp_53;
  }

  instruct_tests_block3: {
    i32 num_43 = 2;
    i32 tmp_load_44 = load alloca_addr_66;
    i32 tmp_45 = tmp_load_44 - num_43;
    store tmp_45, alloca_addr_66;
    jmp instruct_tests_block2;
  }

  instruct_tests_block4: {
    i32 tmp_load_46 = load alloca_addr_66;
    i32 tmp_load_47 = load alloca_addr_60;
    cjmp tmp_load_46 == tmp_load_47 ? instruct_tests_block6 : instruct_tests_block5;
  }

  instruct_tests_block5: {
    jmp instruct_tests_block2;
  }

  instruct_tests_block6: {
    i32 num_48 = 3;
    i32 tmp_load_49 = load alloca_addr_66;
    i32 tmp_50 = tmp_load_49 + num_48;
    store tmp_50, alloca_addr_66;
    jmp instruct_tests_block5;
  }

}
==========================
Selection trees:
  instruct_tests_block0:
  JMP[instruct_tests_block1:]
  instruct_tests_block1:
  STRI32(FPRELU32[Stack[4 bytes at -4]], REGI32[vreg0a])
  STRI32(FPRELU32[Stack[4 bytes at -8]], REGI32[vreg1b])
  STRI32(FPRELU32[Stack[4 bytes at -12]], CONSTI32[0])
  MOVI32[vreg3tmp_load](LDRI32(FPRELU32[Stack[4 bytes at -4]]))
  STRI32(FPRELU32[Stack[4 bytes at -16]], ADDI32(REGI32[vreg3tmp_load], CONSTI32[4]))
  MOVI32[vreg4tmp_load_5](LDRI32(FPRELU32[Stack[4 bytes at -8]]))
  STRI32(FPRELU32[Stack[4 bytes at -20]], ANDI32(REGI32[vreg4tmp_load_5], CONSTI32[255]))
  MOVI32[vreg5tmp_load_10](LDRI32(FPRELU32[Stack[4 bytes at -16]]))
  MOVI32[vreg6tmp_load_11](LDRI32(FPRELU32[Stack[4 bytes at -20]]))
  MOVI32[vreg7tmp_load_13](LDRI32(FPRELU32[Stack[4 bytes at -12]]))
  STRI32(FPRELU32[Stack[4 bytes at -12]], XORI32(REGI32[vreg7tmp_load_13], XORI32(REGI32[vreg5tmp_load_10], REGI32[vreg6tmp_load_11])))
  MOVI32[vreg8tmp_load_19](LDRI32(FPRELU32[Stack[4 bytes at -12]]))
  STRI32(ADDU32(FPRELU32[Stack[8 bytes at -28]], MULU32(CONSTI32[0], CONSTU32[4])), REGI32[vreg8tmp_load_19])
  MOVI32[vreg9tmp_load_30](LDRI32(ADDU32(FPRELU32[Stack[8 bytes at -28]], MULU32(CONSTI32[0], CONSTU32[4]))))
  STRI32(ADDU32(FPRELU32[Stack[8 bytes at -28]], MULU32(CONSTI32[1], CONSTU32[4])), ADDI32(REGI32[vreg9tmp_load_30], CONSTI32[1]))
  MOVI32[vreg10tmp_load_38](LDRI32(ADDU32(FPRELU32[Stack[8 bytes at -28]], MULU32(CONSTI32[1], CONSTU32[4]))))
  STRI32(FPRELU32[Stack[4 bytes at -32]], REGI32[vreg10tmp_load_38])
  MOVI32[vreg11tmp_load_41](LDRI32(FPRELU32[Stack[4 bytes at -32]]))
  MOVI32[vreg12tmp_load_42](LDRI32(FPRELU32[Stack[4 bytes at -16]]))
  CJMPI32[('>=', instruct_tests_block3:, instruct_tests_block4:)](REGI32[vreg11tmp_load_41], REGI32[vreg12tmp_load_42])
  instruct_tests_block2:
  MOVI32[vreg16tmp_load_51](LDRI32(FPRELU32[Stack[4 bytes at -12]]))
  MOVI32[vreg17tmp_load_52](LDRI32(FPRELU32[Stack[4 bytes at -32]]))
  MOVI32[vreg2retval](ADDI32(REGI32[vreg16tmp_load_51], REGI32[vreg17tmp_load_52]))
  JMP[instruct_tests_epilog:]
  instruct_tests_block3:
  MOVI32[vreg13tmp_load_44](LDRI32(FPRELU32[Stack[4 bytes at -32]]))
  STRI32(FPRELU32[Stack[4 bytes at -32]], SUBI32(REGI32[vreg13tmp_load_44], CONSTI32[2]))
  JMP[instruct_tests_block2:]
  instruct_tests_block4:
  MOVI32[vreg14tmp_load_46](LDRI32(FPRELU32[Stack[4 bytes at -32]]))
  MOVI32[vreg15tmp_load_47](LDRI32(FPRELU32[Stack[4 bytes at -16]]))
  CJMPI32[('==', instruct_tests_block6:, instruct_tests_block5:)](REGI32[vreg14tmp_load_46], REGI32[vreg15tmp_load_47])
  instruct_tests_block5:
  JMP[instruct_tests_block2:]
  instruct_tests_block6:
  MOVI32[vreg18tmp_load_49](LDRI32(FPRELU32[Stack[4 bytes at -32]]))
  STRI32(FPRELU32[Stack[4 bytes at -32]], ADDI32(REGI32[vreg18tmp_load_49], CONSTI32[3]))
  JMP[instruct_tests_block5:]
  instruct_tests_epilog:
Frame instruct_tests
$ VUseDef
$ addi_s vreg0a, x12, 0
$ addi_s vreg1b, x13, 0
$ instruct_tests_block0:
$ jal x0, instruct_tests_block1
$ instruct_tests_block1:
$ sw_s vreg0a, -4(x8)
$ sw_s vreg1b, -8(x8)
$ li_s vreg19, 0
$ sw_s vreg19, -12(x8)
$ lw_s vreg20, -4(x8)
$ addi_s vreg3tmp_load, vreg20, 0
$ addi_s vreg21, vreg3tmp_load, 4
$ sw_s vreg21, -16(x8)
$ lw_s vreg22, -8(x8)
$ addi_s vreg4tmp_load_5, vreg22, 0
$ andi_s vreg23, vreg4tmp_load_5, 255
$ sw_s vreg23, -20(x8)
$ lw_s vreg24, -16(x8)
$ addi_s vreg5tmp_load_10, vreg24, 0
$ lw_s vreg25, -20(x8)
$ addi_s vreg6tmp_load_11, vreg25, 0
$ lw_s vreg26, -12(x8)
$ addi_s vreg7tmp_load_13, vreg26, 0
$ xor_s vreg27, vreg5tmp_load_10, vreg6tmp_load_11
$ xor_s vreg28, vreg7tmp_load_13, vreg27
$ sw_s vreg28, -12(x8)
$ lw_s vreg29, -12(x8)
$ addi_s vreg8tmp_load_19, vreg29, 0
$ addi_s vreg30, x8, -28
$ li_s vreg31, 0
$ li_s vreg32, 4
$ mul_s vreg33, vreg31, vreg32
$ add_s vreg34, vreg30, vreg33
$ sw_s vreg8tmp_load_19, 0(vreg34)
$ addi_s vreg35, x8, -28
$ li_s vreg36, 0
$ li_s vreg37, 4
$ mul_s vreg38, vreg36, vreg37
$ add_s vreg39, vreg35, vreg38
$ lw_s vreg40, 0(vreg39)
$ addi_s vreg9tmp_load_30, vreg40, 0
$ addi_s vreg41, x8, -28
$ li_s vreg42, 1
$ li_s vreg43, 4
$ mul_s vreg44, vreg42, vreg43
$ add_s vreg45, vreg41, vreg44
$ addi_s vreg46, vreg9tmp_load_30, 1
$ sw_s vreg46, 0(vreg45)
$ addi_s vreg47, x8, -28
$ li_s vreg48, 1
$ li_s vreg49, 4
$ mul_s vreg50, vreg48, vreg49
$ add_s vreg51, vreg47, vreg50
$ lw_s vreg52, 0(vreg51)
$ addi_s vreg10tmp_load_38, vreg52, 0
$ sw_s vreg10tmp_load_38, -32(x8)
$ lw_s vreg53, -32(x8)
$ addi_s vreg11tmp_load_41, vreg53, 0
$ lw_s vreg54, -16(x8)
$ addi_s vreg12tmp_load_42, vreg54, 0
$ bge_s vreg11tmp_load_41, vreg12tmp_load_42, instruct_tests_block3
$ jal x0, instruct_tests_block4
$ instruct_tests_block2:
$ lw_s vreg55, -12(x8)
$ addi_s vreg16tmp_load_51, vreg55, 0
$ lw_s vreg56, -32(x8)
$ addi_s vreg17tmp_load_52, vreg56, 0
$ add_s vreg57, vreg16tmp_load_51, vreg17tmp_load_52
$ addi_s vreg2retval, vreg57, 0
$ jal x0, instruct_tests_epilog
$ instruct_tests_block3:
$ lw_s vreg58, -32(x8)
$ addi_s vreg13tmp_load_44, vreg58, 0
$ li_s vreg59, 2
$ sub_s vreg60, vreg13tmp_load_44, vreg59
$ sw_s vreg60, -32(x8)
$ jal x0, instruct_tests_block2
$ instruct_tests_block4:
$ lw_s vreg61, -32(x8)
$ addi_s vreg14tmp_load_46, vreg61, 0
$ lw_s vreg62, -16(x8)
$ addi_s vreg15tmp_load_47, vreg62, 0
$ beq_s vreg14tmp_load_46, vreg15tmp_load_47, instruct_tests_block6
$ jal x0, instruct_tests_block5
$ instruct_tests_block5:
$ jal x0, instruct_tests_block2
$ instruct_tests_block6:
$ lw_s vreg63, -32(x8)
$ addi_s vreg18tmp_load_49, vreg63, 0
$ addi_s vreg64, vreg18tmp_load_49, 3
$ sw_s vreg64, -32(x8)
$ jal x0, instruct_tests_block5
$ instruct_tests_epilog:
$ addi_s x10, vreg2retval, 0
$ VUseDef
Frame instruct_tests
$ VUseDef
