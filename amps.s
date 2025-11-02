
C builder
---------

Welcome to the C building report for sample.c
module main functions: 1, blocks: 2, instructions: 17
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_7 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_8 = &alloca_7;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 1;
    store num, alloca_addr;
    ptr num_0 = 4;
    ptr tmp = alloca_addr + num_0;
    i32 num_1 = 2;
    store num_1, alloca_addr_8;
    ptr num_2 = 4;
    ptr tmp_3 = alloca_addr_8 + num_2;
    i32 tmp_load = load alloca_addr;
    i32 tmp_load_4 = load alloca_addr_8;
    i32 tmp_5 = tmp_load + tmp_load_4;
    return tmp_5;
  }

}
==========================
module main before optimization:
module main functions: 1, blocks: 2, instructions: 17
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_7 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_8 = &alloca_7;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 1;
    store num, alloca_addr;
    ptr num_0 = 4;
    ptr tmp = alloca_addr + num_0;
    i32 num_1 = 2;
    store num_1, alloca_addr_8;
    ptr num_2 = 4;
    ptr tmp_3 = alloca_addr_8 + num_2;
    i32 tmp_load = load alloca_addr;
    i32 tmp_load_4 = load alloca_addr_8;
    i32 tmp_5 = tmp_load + tmp_load_4;
    return tmp_5;
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
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_7 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_8 = &alloca_7;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 1;
    store num, alloca_addr;
    ptr num_0 = 4;
    ptr tmp = alloca_addr + num_0;
    i32 num_1 = 2;
    store num_1, alloca_addr_8;
    ptr num_2 = 4;
    ptr tmp_3 = alloca_addr_8 + num_2;
    i32 tmp_load = load alloca_addr;
    i32 tmp_load_4 = load alloca_addr_8;
    i32 tmp_5 = tmp_load + tmp_load_4;
    return tmp_5;
  }

}
==========================
Selection trees:
  main_block0:
  JMP[main_block1:]
  main_block1:
  STRI32(FPRELU32[Stack[4 bytes at -4]], CONSTI32[1])
  STRI32(FPRELU32[Stack[4 bytes at -8]], CONSTI32[2])
  MOVI32[vreg1tmp_load](LDRI32(FPRELU32[Stack[4 bytes at -4]]))
  MOVI32[vreg2tmp_load_4](LDRI32(FPRELU32[Stack[4 bytes at -8]]))
  MOVI32[vreg0retval](ADDI32(REGI32[vreg1tmp_load], REGI32[vreg2tmp_load_4]))
  JMP[main_epilog:]
  main_epilog:
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
$ li_s vreg3, 1
$ sw_s vreg3, -4(x8)
$ li_s vreg4, 2
$ sw_s vreg4, -8(x8)
$ lw_s vreg5, -4(x8)
$ addi_s vreg1tmp_load, vreg5, 0
$ lw_s vreg6, -8(x8)
$ addi_s vreg2tmp_load_4, vreg6, 0
$ add_s vreg7, vreg1tmp_load, vreg2tmp_load_4
$ addi_s vreg0retval, vreg7, 0
$ jal x0, main_epilog
$ main_epilog:
$ addi_s x10, vreg0retval, 0
$ VUseDef
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
