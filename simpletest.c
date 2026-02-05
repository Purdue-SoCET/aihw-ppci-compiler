int instruct_tests(int a, int b) {
    int r_acc = 0;

    // // R-type: operate purely on registers : add_s, sub_s
    // int r_sum = a + b;
    // int r_diff = a - b;
    // r_acc = r_sum ^ r_diff;

    // I-type: register-immediate arithmetic (addi_s, andi_s)
    int i_adj = a + 4;
    int i_mask = b & 0xFF;
    r_acc ^= i_adj ^ i_mask;

    // // Mem-type: explicit loads/stores through stack memory (lw_s, sw_s)
    // int mem_buf[2];
    // mem_buf[0] = r_acc;
    // mem_buf[1] = mem_buf[0] + 1;
    // int mem_val = mem_buf[1];

    // // BR-type: conditional branch that compares registers (beq_s, blt_s)
    // if (mem_val >= i_adj) {
    //     mem_val -= 2;
    // } else if (mem_val == i_adj) {
    //     mem_val += 3;
    // }

//     // MI-type: load immediate into a register (li_s)
//     int mi_seed = 0x1234;
//     r_acc ^= mi_seed;

    // return r_acc + mem_val;
    return r_acc;
}
