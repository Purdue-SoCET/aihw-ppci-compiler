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
    float epsilon;
    asm("lw_s %0, 0(%1)" : "=r"(epsilon) : "r"(eps_addr));

    int inv_addr = INV_N2_ADDR;
    float inv_n2;
    asm("lw_s %0, 0(%1)" : "=r"(inv_n2) : "r"(inv_addr));

    int sp = 0;
    int mask_val = MASK_ALL;
    int ncols = 1;
    int sdma_ctl;
    asm("li_s %0, 133169183" : "=r"(sdma_ctl));

    scpad_load(sp, IN_GMEM, sdma_ctl);

    int row0 = 0; int row1 = 1; int row2 = 2; int row3 = 3;
    vec r0 = vector_load(row0, ncols, 31, 0);
    vec r1 = vector_load(row1, ncols, 31, 0);
    vec r2 = vector_load(row2, ncols, 31, 0);
    vec r3 = vector_load(row3, ncols, 31, 0);

    vec acc = vec_op_masked("RSUM", r0, 0.0, mask_val);
    vec tmp = vec_op_masked("RSUM", r1, 0.0, mask_val);
    acc = vec_op_masked("+", acc, tmp, mask_val);
    tmp = vec_op_masked("RSUM", r2, 0.0, mask_val);
    acc = vec_op_masked("+", acc, tmp, mask_val);
    tmp = vec_op_masked("RSUM", r3, 0.0, mask_val);
    acc = vec_op_masked("+", acc, tmp, mask_val);
    vec mean = vec_op_masked("*", acc, inv_n2, mask_val);

    vec c0 = vec_op_masked("-", r0, mean, mask_val);
    vec c1 = vec_op_masked("-", r1, mean, mask_val);
    vec c2 = vec_op_masked("-", r2, mean, mask_val);
    vec c3 = vec_op_masked("-", r3, mean, mask_val);

    tmp = vec_op_masked("*", c0, c0, mask_val);
    acc = vec_op_masked("RSUM", tmp, 0.0, mask_val);
    tmp = vec_op_masked("*", c1, c1, mask_val);
    tmp = vec_op_masked("RSUM", tmp, 0.0, mask_val);
    acc = vec_op_masked("+", acc, tmp, mask_val);
    tmp = vec_op_masked("*", c2, c2, mask_val);
    tmp = vec_op_masked("RSUM", tmp, 0.0, mask_val);
    acc = vec_op_masked("+", acc, tmp, mask_val);
    tmp = vec_op_masked("*", c3, c3, mask_val);
    tmp = vec_op_masked("RSUM", tmp, 0.0, mask_val);
    acc = vec_op_masked("+", acc, tmp, mask_val);
    vec variance = vec_op_masked("*", acc, inv_n2, mask_val);

    vec denom_seed = vec_op_masked("+", variance, epsilon, mask_val);
    float var_eps = denom_seed[0];
    float denom_f = sqrt(var_eps);
    float one = 1.0;
    float inv_denom = one / denom_f;

    vec out = vec_op_masked("*", c0, inv_denom, mask_val);
    vector_store(out, row0, ncols, 31, 0);
    out = vec_op_masked("*", c1, inv_denom, mask_val);
    vector_store(out, row1, ncols, 31, 0);
    out = vec_op_masked("*", c2, inv_denom, mask_val);
    vector_store(out, row2, ncols, 31, 0);
    out = vec_op_masked("*", c3, inv_denom, mask_val);
    vector_store(out, row3, ncols, 31, 0);

    scpad_store(sp, IN_GMEM, sdma_ctl);

    asm("halt");
    return 0;
}
