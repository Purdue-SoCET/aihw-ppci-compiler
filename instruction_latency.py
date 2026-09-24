# Instruction latencies for the Atalla architecture.
# Keys must match the first token of str(instruction) — i.e. the mnemonic
# as defined in the Syntax(...) constructors in instructions.py /
# vector_instructions.py.
#
# Vector latencies come from "ISA -- Atalla - Updated Instr Latency.csv".
# Scalar latencies are from micro-architecture conventions; div/mod are
# estimated (not in the CSV).

latency = {
    # ── Scalar ALU (Unit 1) ────────────────────────────────────────────────
    "add_s":  1,
    "sub_s":  1,
    "or_s":   1,
    "and_s":  1,
    "xor_s":  1,
    "sll_s":  1,
    "srl_s":  1,
    "sra_s":  1,
    "lui_s":  1,
    "li_s":   1,
    "addi_s": 1,
    "subi_s": 1,
    "ori_s":  1,
    "andi_s": 1,
    "xori_s": 1,
    "slli_s": 1,
    "srli_s": 1,
    "srai_s": 1,

    # ── Scalar Div/Mod (Unit 2) ────────────────────────────────────────────
    "div_s":  20,
    "mod_s":  20,
    "divi_s": 20,
    "modi_s": 20,

    # ── BF16 ↔ int conversions (Unit 2) ───────────────────────────────────
    "bfts_s":  3,
    "stbf_s":  3,
    "rcp_bf":  5,
    "sqrt_bf": 5,

    # ── BF16 arithmetic (Unit 3) ───────────────────────────────────────────
    "add_bf": 5,
    "sub_bf": 5,
    "mul_bf": 4,

    # ── Scalar Mult (Unit 4) ──────────────────────────────────────────────
    "mul_s":  3,
    "muli_s": 3,

    # ── Scalar Ld/St (Unit 5) ─────────────────────────────────────────────
    "lw_s":  3,
    "lhw_s": 3,
    "sw_s":  1,
    "shw_s": 1,

    # ── Control (Unit 1 Ctrl) — branches go alone, latency mostly unused ──
    "beq_s": 1,
    "bne_s": 1,
    "blt_s": 1,
    "bge_s": 1,
    "bgt_s": 1,
    "ble_s": 1,
    "jal":   1,
    "jalr":  1,

    # ── Vector ALU lane ───────────────────────────────────────────────────
    # add/sub: 5 cycles  (CSV: add=5, sub=5)
    "add_vv": 5,
    "sub_vv": 5,
    "add_vs": 5,
    "sub_vs": 5,
    # mul: 4 cycles  (CSV: mul=4)
    "mul_vv": 4,
    "mul_vs": 4,
    # mask compare ops: 5 cycles  (CSV: mgt=mlt=meq=mneq=5)
    "mgt_mvv":  5,
    "mlt_mvv":  5,
    "meq_mvv":  5,
    "mneq_mvv": 5,
    "mgt_mvs":  5,
    "mlt_mvs":  5,
    "meq_mvs":  5,
    "mneq_mvs": 5,
    # reduction ops: 20 cycles  (CSV: rsum=rmin=rmax=20)
    "rsum_vi": 20,
    "rmin_vi": 20,
    "rmax_vi": 20,

    # ── EXP lane ──────────────────────────────────────────────────────────
    "expi_vi": 6,   # CSV: expi=6

    # ── GSAU lane ─────────────────────────────────────────────────────────
    "gemm_vv": 45,  # CSV: 45 cycles (TPU variant)
    "lw_vi":    1,  # CSV: "no dependency" — result available immediately

    # ── VLSU ──────────────────────────────────────────────────────────────
    "vreg_ld": 15,  # CSV: 1+13+1 = 15 (spad latency ~13)
    "vreg_st":  2,  # CSV: 2

    # ── Scpad / SDMA ──────────────────────────────────────────────────────
    "scpad_ld": 13,
    "scpad_st":  2,

    # ── Move / misc ───────────────────────────────────────────────────────
    "vmov_vts": 1,  # CSV: vmov=1
    "mv_mts":   1,  # CSV: mv=1
    "mv_stm":   1,  # CSV: mv=1
}
