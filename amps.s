
C builder
---------

Welcome to the C building report for sample.c
module main functions: 1, blocks: 2, instructions: 5
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<256:256> alloca = alloc 256 bytes aligned at 256;
    ptr alloca_addr = &alloca;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 0;
    return num;
  }

}
==========================
module main before optimization:
module main functions: 1, blocks: 2, instructions: 5
==========================
module main;

global function i32 main() {
  main_block0: {
    blob<256:256> alloca = alloc 256 bytes aligned at 256;
    ptr alloca_addr = &alloca;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 0;
    return num;
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
    blob<256:256> alloca = alloc 256 bytes aligned at 256;
    ptr alloca_addr = &alloca;
    jmp main_block1;
  }

  main_block1: {
    i32 num = 0;
    return num;
  }

}
==========================
Selection trees:
  main_block0:
  JMP[main_block1:]
  main_block1:
  MOVI32[vreg0retval](CONSTI32[0])
  JMP[main_epilog:]
  main_epilog:
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
$ li_s vreg1, 0
$ addi_s vreg0retval, vreg1, 0
$ jal x0, main_epilog
$ main_epilog:
$ addi_s x10, vreg0retval, 0
$ VUseDef
Frame main
$ VUseDef
$ main_block0:
$ jal x0, main_block1
$ main_block1:
