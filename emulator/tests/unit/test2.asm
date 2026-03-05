       .section data
       .section data
       .section code
       global give_5
       type give_5 func
 give_5:
       addi_s x2, x2, -16
       sw_s x1, 4(x2)
       sw_s x8, 0(x2)
       addi_s x8, x2, 8
       addi_s x2, x2, -16
 give_5_block0:
       li_s x9, 5
       addi_s x9, x9, 0
       jal x0, give_5_epilog
 give_5_epilog:
       addi_s x10, x9, 0
       addi_s x2, x2, 16
       lw_s x1, 4(x2)
       lw_s x8, 0(x2)
       addi_s x2, x2, 16
       jalr x0,x1, 0
       .section data
       .section code
       .align 4
       global main
       type main func
 main:
       addi_s x2, x2, -16
       sw_s x1, 4(x2)
       sw_s x8, 0(x2)
       addi_s x8, x2, 8
       addi_s x2, x2, -16
 main_block0:
       li_s x9, 43981
       addi_s x9, x9, 0
       vreg_ld v1, x9, 4, 5, 6, 7, 8
       addi_s x9, x33, -64
       vreg_st v1, x9, 4, 5, 6, 7, 8
       li_s x9, 57005
       addi_s x9, x9, 0
       vreg_ld v1, x9, 4, 5, 6, 7, 8
       addi_s x9, x33, -128
       vreg_st v1, x9, 4, 5, 6, 7, 8
       addi_s x9, x33, -64
       vreg_ld v1, x9, 4, 5, 6, 7, 8
       addi_vi v2, v1, 0, m0
       addi_s x9, x33, -128
       vreg_ld v1, x9, 4, 5, 6, 7, 8
       addi_vi v3, v1, 0, m0
       jal x1, give_5
       addi_s x11, x10, 0
       li_s x10, 16563
       li_s x9, 16673
       div_bf x9, x10, x9
       addi_s x9, x9, 0
       addi_s x11, x11, 0
       add_vs v1, v2, x9, m0
       mul_vs v2, v1, x9, m0
       sub_vs v1, v3, x9, m0
       div_vs v1, v1, x9, m0
       add_vv v1, v2, v1, m0
       stbf_s x9, x11, x0
       mul_vs v1, v1, x9, m0
       addi_vi v1, v1, 0, m0
       li_s x9, 43690
       addi_s x9, x9, 0
       vreg_st v1, x9, 4, 5, 6, 7, 8
       li_s x9, 0
       addi_s x9, x9, 0
       jal x0, main_epilog
 main_epilog:
       addi_s x10, x9, 0
       addi_s x2, x2, 16
       lw_s x1, 4(x2)
       lw_s x8, 0(x2)
       addi_s x2, x2, 16
       jalr x0,x1, 0
       .section data
       .section code
       .align 4
