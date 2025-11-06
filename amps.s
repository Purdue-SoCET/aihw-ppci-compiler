
C builder
---------

Welcome to the C building report for sample.c
module main functions: 1, blocks: 2, instructions: 102
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<2:2> alloca = alloc 2 bytes aligned at 2;
    ptr alloca_addr = &alloca;
    blob<2:2> alloca_65 = alloc 2 bytes aligned at 2;
    ptr alloca_addr_66 = &alloca_65;
    blob<30:2> alloca_67 = alloc 30 bytes aligned at 2;
    ptr alloca_addr_68 = &alloca_67;
    blob<30:2> alloca_69 = alloc 30 bytes aligned at 2;
    ptr alloca_addr_70 = &alloca_69;
    blob<4:4> alloca_71 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_72 = &alloca_71;
    jmp main_block1;
  }

  main_block1: {
    f16 num = 1.1;
    store num, alloca_addr;
    ptr num_0 = 2;
    ptr tmp = alloca_addr + num_0;
    f16 num_1 = 2.2;
    store num_1, alloca_addr_66;
    ptr num_2 = 2;
    ptr tmp_3 = alloca_addr_66 + num_2;
    f16 num_4 = 1.1;
    store num_4, alloca_addr_68;
    ptr num_5 = 2;
    ptr tmp_6 = alloca_addr_68 + num_5;
    f16 num_7 = 1.2;
    store num_7, tmp_6;
    ptr num_8 = 2;
    ptr tmp_9 = tmp_6 + num_8;
    f16 num_10 = 1.3;
    store num_10, tmp_9;
    ptr num_11 = 2;
    ptr tmp_12 = tmp_9 + num_11;
    f16 num_13 = 1.4;
    store num_13, tmp_12;
    ptr num_14 = 2;
    ptr tmp_15 = tmp_12 + num_14;
    f16 num_16 = 1.5;
    store num_16, tmp_15;
    ptr num_17 = 2;
    ptr tmp_18 = tmp_15 + num_17;
    f16 num_19 = 1.6;
    store num_19, tmp_18;
    ptr num_20 = 2;
    ptr tmp_21 = tmp_18 + num_20;
    f16 num_22 = 1.7;
    store num_22, tmp_21;
    ptr num_23 = 2;
    ptr tmp_24 = tmp_21 + num_23;
    f16 num_25 = 1.8;
    store num_25, tmp_24;
    ptr num_26 = 2;
    ptr tmp_27 = tmp_24 + num_26;
    f16 num_28 = 1.9;
    store num_28, tmp_27;
    ptr num_29 = 2;
    ptr tmp_30 = tmp_27 + num_29;
    f16 num_31 = 2.0;
    store num_31, tmp_30;
    ptr num_32 = 2;
    ptr tmp_33 = tmp_30 + num_32;
    f16 num_34 = 1.1;
    store num_34, alloca_addr_70;
    ptr num_35 = 2;
    ptr tmp_36 = alloca_addr_70 + num_35;
    f16 num_37 = 1.2;
    store num_37, tmp_36;
    ptr num_38 = 2;
    ptr tmp_39 = tmp_36 + num_38;
    f16 num_40 = 1.3;
    store num_40, tmp_39;
    ptr num_41 = 2;
    ptr tmp_42 = tmp_39 + num_41;
    f16 num_43 = 1.4;
    store num_43, tmp_42;
    ptr num_44 = 2;
    ptr tmp_45 = tmp_42 + num_44;
    f16 num_46 = 1.5;
    store num_46, tmp_45;
    ptr num_47 = 2;
    ptr tmp_48 = tmp_45 + num_47;
    f16 num_49 = 1.6;
    store num_49, tmp_48;
    ptr num_50 = 2;
    ptr tmp_51 = tmp_48 + num_50;
    f16 num_52 = 1.7;
    store num_52, tmp_51;
    ptr num_53 = 2;
    ptr tmp_54 = tmp_51 + num_53;
    f16 num_55 = 1.8;
    store num_55, tmp_54;
    ptr num_56 = 2;
    ptr tmp_57 = tmp_54 + num_56;
    f16 num_58 = 1.9;
    store num_58, tmp_57;
    ptr num_59 = 2;
    ptr tmp_60 = tmp_57 + num_59;
    f16 num_61 = 2.0;
    store num_61, tmp_60;
    ptr num_62 = 2;
    ptr tmp_63 = tmp_60 + num_62;
    gemm ptr alloca_addr_72 = &alloca_71, ptr alloca_addr_68 = &alloca_67, ptr alloca_addr_70 = &alloca_69;
    i32 num_64 = 0;
    return num_64;
  }

}
==========================
module main before optimization:
module main functions: 1, blocks: 2, instructions: 102
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<2:2> alloca = alloc 2 bytes aligned at 2;
    ptr alloca_addr = &alloca;
    blob<2:2> alloca_65 = alloc 2 bytes aligned at 2;
    ptr alloca_addr_66 = &alloca_65;
    blob<30:2> alloca_67 = alloc 30 bytes aligned at 2;
    ptr alloca_addr_68 = &alloca_67;
    blob<30:2> alloca_69 = alloc 30 bytes aligned at 2;
    ptr alloca_addr_70 = &alloca_69;
    blob<4:4> alloca_71 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_72 = &alloca_71;
    jmp main_block1;
  }

  main_block1: {
    f16 num = 1.1;
    store num, alloca_addr;
    ptr num_0 = 2;
    ptr tmp = alloca_addr + num_0;
    f16 num_1 = 2.2;
    store num_1, alloca_addr_66;
    ptr num_2 = 2;
    ptr tmp_3 = alloca_addr_66 + num_2;
    f16 num_4 = 1.1;
    store num_4, alloca_addr_68;
    ptr num_5 = 2;
    ptr tmp_6 = alloca_addr_68 + num_5;
    f16 num_7 = 1.2;
    store num_7, tmp_6;
    ptr num_8 = 2;
    ptr tmp_9 = tmp_6 + num_8;
    f16 num_10 = 1.3;
    store num_10, tmp_9;
    ptr num_11 = 2;
    ptr tmp_12 = tmp_9 + num_11;
    f16 num_13 = 1.4;
    store num_13, tmp_12;
    ptr num_14 = 2;
    ptr tmp_15 = tmp_12 + num_14;
    f16 num_16 = 1.5;
    store num_16, tmp_15;
    ptr num_17 = 2;
    ptr tmp_18 = tmp_15 + num_17;
    f16 num_19 = 1.6;
    store num_19, tmp_18;
    ptr num_20 = 2;
    ptr tmp_21 = tmp_18 + num_20;
    f16 num_22 = 1.7;
    store num_22, tmp_21;
    ptr num_23 = 2;
    ptr tmp_24 = tmp_21 + num_23;
    f16 num_25 = 1.8;
    store num_25, tmp_24;
    ptr num_26 = 2;
    ptr tmp_27 = tmp_24 + num_26;
    f16 num_28 = 1.9;
    store num_28, tmp_27;
    ptr num_29 = 2;
    ptr tmp_30 = tmp_27 + num_29;
    f16 num_31 = 2.0;
    store num_31, tmp_30;
    ptr num_32 = 2;
    ptr tmp_33 = tmp_30 + num_32;
    f16 num_34 = 1.1;
    store num_34, alloca_addr_70;
    ptr num_35 = 2;
    ptr tmp_36 = alloca_addr_70 + num_35;
    f16 num_37 = 1.2;
    store num_37, tmp_36;
    ptr num_38 = 2;
    ptr tmp_39 = tmp_36 + num_38;
    f16 num_40 = 1.3;
    store num_40, tmp_39;
    ptr num_41 = 2;
    ptr tmp_42 = tmp_39 + num_41;
    f16 num_43 = 1.4;
    store num_43, tmp_42;
    ptr num_44 = 2;
    ptr tmp_45 = tmp_42 + num_44;
    f16 num_46 = 1.5;
    store num_46, tmp_45;
    ptr num_47 = 2;
    ptr tmp_48 = tmp_45 + num_47;
    f16 num_49 = 1.6;
    store num_49, tmp_48;
    ptr num_50 = 2;
    ptr tmp_51 = tmp_48 + num_50;
    f16 num_52 = 1.7;
    store num_52, tmp_51;
    ptr num_53 = 2;
    ptr tmp_54 = tmp_51 + num_53;
    f16 num_55 = 1.8;
    store num_55, tmp_54;
    ptr num_56 = 2;
    ptr tmp_57 = tmp_54 + num_56;
    f16 num_58 = 1.9;
    store num_58, tmp_57;
    ptr num_59 = 2;
    ptr tmp_60 = tmp_57 + num_59;
    f16 num_61 = 2.0;
    store num_61, tmp_60;
    ptr num_62 = 2;
    ptr tmp_63 = tmp_60 + num_62;
    gemm ptr alloca_addr_72 = &alloca_71, ptr alloca_addr_68 = &alloca_67, ptr alloca_addr_70 = &alloca_69;
    i32 num_64 = 0;
    return num_64;
  }

}
==========================

Code generation
---------------

Target: atalla-arch

Log for global function i32 main()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

==========================
global function i32 main() {
  main_block0: {
    blob<2:2> alloca = alloc 2 bytes aligned at 2;
    ptr alloca_addr = &alloca;
    blob<2:2> alloca_65 = alloc 2 bytes aligned at 2;
    ptr alloca_addr_66 = &alloca_65;
    blob<30:2> alloca_67 = alloc 30 bytes aligned at 2;
    ptr alloca_addr_68 = &alloca_67;
    blob<30:2> alloca_69 = alloc 30 bytes aligned at 2;
    ptr alloca_addr_70 = &alloca_69;
    blob<4:4> alloca_71 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_72 = &alloca_71;
    jmp main_block1;
  }

  main_block1: {
    f16 num = 1.1;
    store num, alloca_addr;
    ptr num_0 = 2;
    ptr tmp = alloca_addr + num_0;
    f16 num_1 = 2.2;
    store num_1, alloca_addr_66;
    ptr num_2 = 2;
    ptr tmp_3 = alloca_addr_66 + num_2;
    f16 num_4 = 1.1;
    store num_4, alloca_addr_68;
    ptr num_5 = 2;
    ptr tmp_6 = alloca_addr_68 + num_5;
    f16 num_7 = 1.2;
    store num_7, tmp_6;
    ptr num_8 = 2;
    ptr tmp_9 = tmp_6 + num_8;
    f16 num_10 = 1.3;
    store num_10, tmp_9;
    ptr num_11 = 2;
    ptr tmp_12 = tmp_9 + num_11;
    f16 num_13 = 1.4;
    store num_13, tmp_12;
    ptr num_14 = 2;
    ptr tmp_15 = tmp_12 + num_14;
    f16 num_16 = 1.5;
    store num_16, tmp_15;
    ptr num_17 = 2;
    ptr tmp_18 = tmp_15 + num_17;
    f16 num_19 = 1.6;
    store num_19, tmp_18;
    ptr num_20 = 2;
    ptr tmp_21 = tmp_18 + num_20;
    f16 num_22 = 1.7;
    store num_22, tmp_21;
    ptr num_23 = 2;
    ptr tmp_24 = tmp_21 + num_23;
    f16 num_25 = 1.8;
    store num_25, tmp_24;
    ptr num_26 = 2;
    ptr tmp_27 = tmp_24 + num_26;
    f16 num_28 = 1.9;
    store num_28, tmp_27;
    ptr num_29 = 2;
    ptr tmp_30 = tmp_27 + num_29;
    f16 num_31 = 2.0;
    store num_31, tmp_30;
    ptr num_32 = 2;
    ptr tmp_33 = tmp_30 + num_32;
    f16 num_34 = 1.1;
    store num_34, alloca_addr_70;
    ptr num_35 = 2;
    ptr tmp_36 = alloca_addr_70 + num_35;
    f16 num_37 = 1.2;
    store num_37, tmp_36;
    ptr num_38 = 2;
    ptr tmp_39 = tmp_36 + num_38;
    f16 num_40 = 1.3;
    store num_40, tmp_39;
    ptr num_41 = 2;
    ptr tmp_42 = tmp_39 + num_41;
    f16 num_43 = 1.4;
    store num_43, tmp_42;
    ptr num_44 = 2;
    ptr tmp_45 = tmp_42 + num_44;
    f16 num_46 = 1.5;
    store num_46, tmp_45;
    ptr num_47 = 2;
    ptr tmp_48 = tmp_45 + num_47;
    f16 num_49 = 1.6;
    store num_49, tmp_48;
    ptr num_50 = 2;
    ptr tmp_51 = tmp_48 + num_50;
    f16 num_52 = 1.7;
    store num_52, tmp_51;
    ptr num_53 = 2;
    ptr tmp_54 = tmp_51 + num_53;
    f16 num_55 = 1.8;
    store num_55, tmp_54;
    ptr num_56 = 2;
    ptr tmp_57 = tmp_54 + num_56;
    f16 num_58 = 1.9;
    store num_58, tmp_57;
    ptr num_59 = 2;
    ptr tmp_60 = tmp_57 + num_59;
    f16 num_61 = 2.0;
    store num_61, tmp_60;
    ptr num_62 = 2;
    ptr tmp_63 = tmp_60 + num_62;
    gemm ptr alloca_addr_72 = &alloca_71, ptr alloca_addr_68 = &alloca_67, ptr alloca_addr_70 = &alloca_69;
    i32 num_64 = 0;
    return num_64;
  }

}
==========================
Selection trees:
  main_block0:
  JMP[main_block1:]
  main_block1:
  STRF16(FPRELU32[Stack[2 bytes at -2]], CONSTF16[1.1])
  STRF16(FPRELU32[Stack[2 bytes at -4]], CONSTF16[2.2])
  STRF16(FPRELU32[Stack[30 bytes at -34]], CONSTF16[1.1])
  MOVU32[vreg4tmp_6](ADDU32(FPRELU32[Stack[30 bytes at -34]], CONSTU32[2]))
  STRF16(REGU32[vreg4tmp_6], CONSTF16[1.2])
  MOVU32[vreg5tmp_9](ADDU32(REGU32[vreg4tmp_6], CONSTU32[2]))
  STRF16(REGU32[vreg5tmp_9], CONSTF16[1.3])
  MOVU32[vreg6tmp_12](ADDU32(REGU32[vreg5tmp_9], CONSTU32[2]))
  STRF16(REGU32[vreg6tmp_12], CONSTF16[1.4])
  MOVU32[vreg7tmp_15](ADDU32(REGU32[vreg6tmp_12], CONSTU32[2]))
  STRF16(REGU32[vreg7tmp_15], CONSTF16[1.5])
  MOVU32[vreg8tmp_18](ADDU32(REGU32[vreg7tmp_15], CONSTU32[2]))
  STRF16(REGU32[vreg8tmp_18], CONSTF16[1.6])
  MOVU32[vreg9tmp_21](ADDU32(REGU32[vreg8tmp_18], CONSTU32[2]))
  STRF16(REGU32[vreg9tmp_21], CONSTF16[1.7])
  MOVU32[vreg10tmp_24](ADDU32(REGU32[vreg9tmp_21], CONSTU32[2]))
  STRF16(REGU32[vreg10tmp_24], CONSTF16[1.8])
  MOVU32[vreg11tmp_27](ADDU32(REGU32[vreg10tmp_24], CONSTU32[2]))
  STRF16(REGU32[vreg11tmp_27], CONSTF16[1.9])
  MOVU32[vreg12tmp_30](ADDU32(REGU32[vreg11tmp_27], CONSTU32[2]))
  STRF16(REGU32[vreg12tmp_30], CONSTF16[2.0])
  STRF16(FPRELU32[Stack[30 bytes at -64]], CONSTF16[1.1])
  MOVU32[vreg13tmp_36](ADDU32(FPRELU32[Stack[30 bytes at -64]], CONSTU32[2]))
  STRF16(REGU32[vreg13tmp_36], CONSTF16[1.2])
  MOVU32[vreg14tmp_39](ADDU32(REGU32[vreg13tmp_36], CONSTU32[2]))
  STRF16(REGU32[vreg14tmp_39], CONSTF16[1.3])
  MOVU32[vreg15tmp_42](ADDU32(REGU32[vreg14tmp_39], CONSTU32[2]))
  STRF16(REGU32[vreg15tmp_42], CONSTF16[1.4])
  MOVU32[vreg16tmp_45](ADDU32(REGU32[vreg15tmp_42], CONSTU32[2]))
  STRF16(REGU32[vreg16tmp_45], CONSTF16[1.5])
  MOVU32[vreg17tmp_48](ADDU32(REGU32[vreg16tmp_45], CONSTU32[2]))
  STRF16(REGU32[vreg17tmp_48], CONSTF16[1.6])
  MOVU32[vreg18tmp_51](ADDU32(REGU32[vreg17tmp_48], CONSTU32[2]))
  STRF16(REGU32[vreg18tmp_51], CONSTF16[1.7])
  MOVU32[vreg19tmp_54](ADDU32(REGU32[vreg18tmp_51], CONSTU32[2]))
  STRF16(REGU32[vreg19tmp_54], CONSTF16[1.8])
  MOVU32[vreg20tmp_57](ADDU32(REGU32[vreg19tmp_54], CONSTU32[2]))
  STRF16(REGU32[vreg20tmp_57], CONSTF16[1.9])
  MOVU32[vreg21tmp_60](ADDU32(REGU32[vreg20tmp_57], CONSTU32[2]))
  STRF16(REGU32[vreg21tmp_60], CONSTF16[2.0])
  MOVU32[vreg1](FPRELU32[Stack[4 bytes at -68]])
  MOVU32[vreg2](FPRELU32[Stack[30 bytes at -34]])
  MOVU32[vreg3](FPRELU32[Stack[30 bytes at -64]])
  MOVU32[vreg1](REGU32[vreg1])
  MOVU32[vreg2](REGU32[vreg2])
  MOVU32[vreg3](REGU32[vreg3])
  GEMMVV(REGU32[vreg1], REGU32[vreg2], REGU32[vreg3])
  MOVI32[vreg0retval](CONSTI32[0])
  JMP[main_epilog:]
  main_epilog:
