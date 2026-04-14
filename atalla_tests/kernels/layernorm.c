#define CFG_BASE   0x3C
#define EPS_ADDR   20
#define INV_N2_ADDR 24
#define MASK_ALL   0xF

int main() {
    int cfg = CFG_BASE;
    int IN_GMEM;
    int SCPAD_BASE;
    asm("lw_s %0, 0(%1)" : "=r"(IN_GMEM)    : "r"(cfg));
    asm("lw_s %0, 4(%1)" : "=r"(SCPAD_BASE)  : "r"(cfg));

    int eps_addr = EPS_ADDR;
    int inv_addr = INV_N2_ADDR;

    int sp = 0;
    int mask_val = MASK_ALL;
    int sdma_ctl;
    asm("li_s %0, 133169183" : "=r"(sdma_ctl));

    scpad_load(sp, IN_GMEM, sdma_ctl);

    int row0 = 0; int row1 = 1; int row2 = 2; int row3 = 3;
    vec r0 = vector_load(0, row0, 31, 0);
    vec r1 = vector_load(0, row1, 31, 0);
    vec r2 = vector_load(0, row2, 31, 0);
    vec r3 = vector_load(0, row3, 31, 0);

    /* sum_rows vs sum_sq must be different C variables; reusing `acc` made IR tie
       variance masked-add merge_base to the pre-mean row sum (wrong variance). */
    vec s0 = vec_op_masked("RSUM", r0, 0.0, mask_val);
    vec s1 = vec_op_masked("RSUM", r1, 0.0, mask_val);
    vec s2 = vec_op_masked("RSUM", r2, 0.0, mask_val);
    vec s3 = vec_op_masked("RSUM", r3, 0.0, mask_val);
    vec sum_rows = vec_op_masked("+", vec_op_masked("+", s0, s1, mask_val), vec_op_masked("+", s2, s3, mask_val), mask_val);

    float inv_mean;
    asm("lw_s %0, 0(%1)" : "=r"(inv_mean) : "r"(inv_addr));
    vec mean = vec_op_masked("*", sum_rows, inv_mean, mask_val);

    vec c0 = vec_op_masked("-", r0, mean, mask_val);
    vec c1 = vec_op_masked("-", r1, mean, mask_val);
    vec c2 = vec_op_masked("-", r2, mean, mask_val);
    vec c3 = vec_op_masked("-", r3, mean, mask_val);

    vec q0 = vec_op_masked("*", c0, c0, mask_val);
    vec q1 = vec_op_masked("*", c1, c1, mask_val);
    vec q2 = vec_op_masked("*", c2, c2, mask_val);
    vec q3 = vec_op_masked("*", c3, c3, mask_val);
    vec t0 = vec_op_masked("RSUM", q0, 0.0, mask_val);
    vec t1 = vec_op_masked("RSUM", q1, 0.0, mask_val);
    vec t2 = vec_op_masked("RSUM", q2, 0.0, mask_val);
    vec t3 = vec_op_masked("RSUM", q3, 0.0, mask_val);
    vec sum_sq = vec_op_masked("+", vec_op_masked("+", t0, t1, mask_val), vec_op_masked("+", t2, t3, mask_val), mask_val);

    float inv_var;
    asm("lw_s %0, 0(%1)" : "=r"(inv_var) : "r"(inv_addr));
    vec variance = vec_op_masked("*", sum_sq, inv_var, mask_val);

    float eps_den;
    asm("lw_s %0, 0(%1)" : "=r"(eps_den) : "r"(eps_addr));
    vec denom_seed = vec_op_masked("+", variance, eps_den, mask_val);
    float var_eps = denom_seed[0];
    float denom_f = sqrt(var_eps);
    float one = 1.0;
    float inv_denom = one / denom_f;

    vec out = vec_op_masked("*", c0, inv_denom, mask_val);
    vector_store(out, 0, row0, 31, 0);
    out = vec_op_masked("*", c1, inv_denom, mask_val);
    vector_store(out, 0, row1, 31, 0);
    out = vec_op_masked("*", c2, inv_denom, mask_val);
    vector_store(out, 0, row2, 31, 0);
    out = vec_op_masked("*", c3, inv_denom, mask_val);
    vector_store(out, 0, row3, 31, 0);

    scpad_store(sp, IN_GMEM, sdma_ctl);

    asm("halt");
    return 0;
}
