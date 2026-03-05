.section code

entry:
    jal $x0, main

give_5:
    addi.s $x2, $x2, -16
    sw.s $x1, 4($x2)
    sw.s $x8, 0($x2)
    addi.s $x8, $x2, 8
    addi.s $x2, $x2, -16
give_5_block0:
    li.s $x9, 5
    addi.s $x9, $x9, 0
    jal $x0, give_5_epilog
give_5_epilog:
    addi.s $x10, $x9, 0
    addi.s $x2, $x2, 16
    lw.s $x1, 4($x2)
    lw.s $x8, 0($x2)
    addi.s $x2, $x2, 16
    jalr $x0, $x1, 0

main:
    addi.s $x2, $x2, -16
    sw.s $x1, 4($x2)
    sw.s $x8, 0($x2)
    addi.s $x8, $x2, 8
    addi.s $x2, $x2, -16
main_block0:
    li.s $x9, 43981
    addi.s $x9, $x9, 0
    vreg.ld $v1, $x9, 8, 2, 5, 9, 3
    addi.s $x9, $x33, -64
    vreg.st $v1, $x9, 8, 2, 5, 9, 3
    li.s $x9, 57005
    addi.s $x9, $x9, 0
    vreg.ld $v1, $x9, 8, 2, 5, 9, 3
    addi.s $x9, $x33, -128
    vreg.st $v1, $x9, 8, 2, 5, 9, 3
    addi.s $x9, $x33, -64
    vreg.ld $v1, $x9, 8, 2, 5, 9, 3
    addi.vi $v2, $v1, 0, m0
    addi.s $x9, $x33, -128
    vreg.ld $v1, $x9, 8, 2, 5, 9, 3
    addi.vi $v3, $v1, 0, m0
    jal $x1, give_5
    addi.s $x11, $x10, 0
    li.s $x10, 16563
    li.s $x9, 16673
    div.bf $x9, $x10, $x9
    addi.s $x9, $x9, 0
    addi.s $x11, $x11, 0
    add.vs $v1, $v2, $x9, m0
    mul.vs $v2, $v1, $x9, m0
    sub.vs $v1, $v3, $x9, m0
    div.vs $v1, $v1, $x9, m0
    add.vv $v1, $v2, $v1, m0
    stbf.s $x9, $x11, $x0
    mul.vs $v1, $v1, $x9, m0
    addi.vi $v1, $v1, 0, m0
    li.s $x9, 43690
    addi.s $x9, $x9, 0
    vreg.st $v1, $x9, 8, 2, 5, 9, 3
    li.s $x9, 0
    addi.s $x9, $x9, 0
    jal $x0, main_epilog
main_epilog:
    addi.s $x10, $x9, 0
    addi.s $x2, $x2, 16
    lw.s $x1, 4($x2)
    lw.s $x8, 0($x2)
    addi.s $x2, $x2, 16
    halt.s
