
C builder
---------

Welcome to the C building report for sample.c
module main functions: 1, blocks: 2, instructions: 15
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<2:2> alloca = alloc 2 bytes aligned at 2;
    ptr alloca_addr = &alloca;
    blob<2:2> alloca_5 = alloc 2 bytes aligned at 2;
    ptr alloca_addr_6 = &alloca_5;
    jmp main_block1;
  }

  main_block1: {
    f16 num = 1.1;
    store num, alloca_addr;
    ptr num_0 = 2;
    ptr tmp = alloca_addr + num_0;
    f16 num_1 = 2.2;
    store num_1, alloca_addr_6;
    ptr num_2 = 2;
    ptr tmp_3 = alloca_addr_6 + num_2;
    i32 num_4 = 0;
    return num_4;
  }

}
==========================
module main before optimization:
module main functions: 1, blocks: 2, instructions: 15
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<2:2> alloca = alloc 2 bytes aligned at 2;
    ptr alloca_addr = &alloca;
    blob<2:2> alloca_5 = alloc 2 bytes aligned at 2;
    ptr alloca_addr_6 = &alloca_5;
    jmp main_block1;
  }

  main_block1: {
    f16 num = 1.1;
    store num, alloca_addr;
    ptr num_0 = 2;
    ptr tmp = alloca_addr + num_0;
    f16 num_1 = 2.2;
    store num_1, alloca_addr_6;
    ptr num_2 = 2;
    ptr tmp_3 = alloca_addr_6 + num_2;
    i32 num_4 = 0;
    return num_4;
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
    blob<2:2> alloca_5 = alloc 2 bytes aligned at 2;
    ptr alloca_addr_6 = &alloca_5;
    jmp main_block1;
  }

  main_block1: {
    f16 num = 1.1;
    store num, alloca_addr;
    ptr num_0 = 2;
    ptr tmp = alloca_addr + num_0;
    f16 num_1 = 2.2;
    store num_1, alloca_addr_6;
    ptr num_2 = 2;
    ptr tmp_3 = alloca_addr_6 + num_2;
    i32 num_4 = 0;
    return num_4;
  }

}
==========================
Selection trees:
  main_block0:
  JMP[main_block1:]
  main_block1:
  STRF16(FPRELU32[Stack[2 bytes at -2]], CONSTF16[1.1])
  STRF16(FPRELU32[Stack[2 bytes at -4]], CONSTF16[2.2])
  MOVI32[vreg0retval](CONSTI32[0])
  JMP[main_epilog:]
  main_epilog:
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
$ li_s vreg1, 1066192077
$ sw_s vreg1, -2(x8)
$ li_s vreg2, 1074580685
$ sw_s vreg2, -4(x8)
$ li_s vreg3, 0
$ addi_s vreg0retval, vreg3, 0
$ jal x0, main_epilog
$ main_epilog:
$ addi_s x10, vreg0retval, 0
$ VUseDef
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
