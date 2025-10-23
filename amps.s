
C builder
---------

Welcome to the C building report for sample.c
module main functions: 1, blocks: 5, instructions: 32
==========================
module main;

global variable z (4 bytes aligned at 4)

global function i32 main() {
  main_block0: {
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_13 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_14 = &alloca_13;
    blob<4:4> alloca_15 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_16 = &alloca_15;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 10;
    store num, alloca_addr;
    ptr num_0 = 4;
    ptr tmp = alloca_addr + num_0;
    i32 num_1 = 20;
    store num_1, alloca_addr_14;
    ptr num_2 = 4;
    ptr tmp_3 = alloca_addr_14 + num_2;
    i32 tmp_load = load z;
    store tmp_load, alloca_addr_16;
    ptr num_4 = 4;
    ptr tmp_5 = alloca_addr_16 + num_4;
    i32 tmp_load_6 = load alloca_addr;
    i32 tmp_load_7 = load alloca_addr_14;
    i32 tmp_8 = tmp_load_6 + tmp_load_7;
    i32 num_9 = 30;
    cjmp tmp_8 > num_9 ? main_block2 : main_block3;
  }

  main_block2: {
    i32 num_10 = 1;
    jmp main_block4;
  }

  main_block3: {
    i32 num_11 = 2;
    jmp main_block4;
  }

  main_block4: {
    i32 phi = phi main_block2: num_10, main_block3: num_11;
    store phi, alloca_addr_16;
    i32 num_12 = 0;
    return num_12;
  }

}
==========================
module main before optimization:
module main functions: 1, blocks: 5, instructions: 32
==========================
module main;

global variable z (4 bytes aligned at 4)

global function i32 main() {
  main_block0: {
    blob<4:4> alloca = alloc 4 bytes aligned at 4;
    ptr alloca_addr = &alloca;
    blob<4:4> alloca_13 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_14 = &alloca_13;
    blob<4:4> alloca_15 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_16 = &alloca_15;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 10;
    store num, alloca_addr;
    ptr num_0 = 4;
    ptr tmp = alloca_addr + num_0;
    i32 num_1 = 20;
    store num_1, alloca_addr_14;
    ptr num_2 = 4;
    ptr tmp_3 = alloca_addr_14 + num_2;
    i32 tmp_load = load z;
    store tmp_load, alloca_addr_16;
    ptr num_4 = 4;
    ptr tmp_5 = alloca_addr_16 + num_4;
    i32 tmp_load_6 = load alloca_addr;
    i32 tmp_load_7 = load alloca_addr_14;
    i32 tmp_8 = tmp_load_6 + tmp_load_7;
    i32 num_9 = 30;
    cjmp tmp_8 > num_9 ? main_block2 : main_block3;
  }

  main_block2: {
    i32 num_10 = 1;
    jmp main_block4;
  }

  main_block3: {
    i32 num_11 = 2;
    jmp main_block4;
  }

  main_block4: {
    i32 phi = phi main_block2: num_10, main_block3: num_11;
    store phi, alloca_addr_16;
    i32 num_12 = 0;
    return num_12;
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
    blob<4:4> alloca_13 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_14 = &alloca_13;
    blob<4:4> alloca_15 = alloc 4 bytes aligned at 4;
    ptr alloca_addr_16 = &alloca_15;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 10;
    store num, alloca_addr;
    ptr num_0 = 4;
    ptr tmp = alloca_addr + num_0;
    i32 num_1 = 20;
    store num_1, alloca_addr_14;
    ptr num_2 = 4;
    ptr tmp_3 = alloca_addr_14 + num_2;
    i32 tmp_load = load z;
    store tmp_load, alloca_addr_16;
    ptr num_4 = 4;
    ptr tmp_5 = alloca_addr_16 + num_4;
    i32 tmp_load_6 = load alloca_addr;
    i32 tmp_load_7 = load alloca_addr_14;
    i32 tmp_8 = tmp_load_6 + tmp_load_7;
    i32 num_9 = 30;
    cjmp tmp_8 > num_9 ? main_block2 : main_block3;
  }

  main_block2: {
    i32 num_10 = 1;
    jmp main_block4;
  }

  main_block3: {
    i32 num_11 = 2;
    jmp main_block4;
  }

  main_block4: {
    i32 phi = phi main_block2: num_10, main_block3: num_11;
    store phi, alloca_addr_16;
    i32 num_12 = 0;
    return num_12;
  }

}
==========================
Selection trees:
  main_block0:
  JMP[main_block1:]
  main_block1:
  STRI32(FPRELU32[Stack[4 bytes at -4]], CONSTI32[10])
  STRI32(FPRELU32[Stack[4 bytes at -8]], CONSTI32[20])
  MOVI32[vreg4tmp_load](LDRI32(LABEL[z]))
  STRI32(FPRELU32[Stack[4 bytes at -12]], REGI32[vreg4tmp_load])
  MOVI32[vreg5tmp_load_6](LDRI32(FPRELU32[Stack[4 bytes at -4]]))
  MOVI32[vreg6tmp_load_7](LDRI32(FPRELU32[Stack[4 bytes at -8]]))
  CJMPI32[('>', main_block2:, main_block3:)](ADDI32(REGI32[vreg5tmp_load_6], REGI32[vreg6tmp_load_7]), CONSTI32[30])
  main_block2:
  MOVI32[vreg2](CONSTI32[1])
  MOVI32[vreg0phi](REGI32[vreg2])
  JMP[main_block4:]
  main_block3:
  MOVI32[vreg3](CONSTI32[2])
  MOVI32[vreg0phi](REGI32[vreg3])
  JMP[main_block4:]
  main_block4:
  MOVI32[vreg0phi](REGI32[vreg0phi])
  STRI32(FPRELU32[Stack[4 bytes at -12]], REGI32[vreg0phi])
  MOVI32[vreg1retval](CONSTI32[0])
  JMP[main_epilog:]
  main_epilog:
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
$ li_s vreg7, 10
$ sw_s vreg7, -4(x8)
$ li_s vreg8, 20
$ sw_s vreg8, -8(x8)
$ lw_s vreg9, main_literal_0
$ lw_s vreg10, 0(vreg9)
$ addi_s vreg4tmp_load, vreg10, 0
$ sw_s vreg4tmp_load, -12(x8)
$ lw_s vreg11, -4(x8)
$ addi_s vreg5tmp_load_6, vreg11, 0
$ lw_s vreg12, -8(x8)
$ addi_s vreg6tmp_load_7, vreg12, 0
$ add_s vreg13, vreg5tmp_load_6, vreg6tmp_load_7
$ li_s vreg14, 30
$ bgt_s vreg13, vreg14, main_block2
$ jal x0, main_block3
$ main_block2:
$ li_s vreg15, 1
$ addi_s vreg2, vreg15, 0
$ addi_s vreg0phi, vreg2, 0
$ jal x0, main_block4
$ main_block3:
$ li_s vreg16, 2
$ addi_s vreg3, vreg16, 0
$ addi_s vreg0phi, vreg3, 0
$ jal x0, main_block4
$ main_block4:
$ addi_s vreg0phi, vreg0phi, 0
$ sw_s vreg0phi, -12(x8)
$ li_s vreg17, 0
$ addi_s vreg1retval, vreg17, 0
$ jal x0, main_epilog
$ main_epilog:
$ addi_s x10, vreg1retval, 0
$ VUseDef
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
