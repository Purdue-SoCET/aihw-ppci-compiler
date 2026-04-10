#define TILE_SIZE 4

#define SCPAD_B_ADDR 0        // WEIGHT_SCPAD_ADDR
#define SCPAD_C_ADDR 2048     // OUTPUT_SCPAD_ADDR  
#define SCPAD_A_ADDR 1024     // INPUT_SCPAD_ADDR

#define GMEM_B_ADDR  0x1000   // WEIGHT_GMEM_ADDR
#define GMEM_C_ADDR  0x5000   // OUTPUT_GMEM_ADDR
#define GMEM_A_ADDR  0x2000   // INPUT_GMEM_ADDR

int gemm_4x4(void) {
    int scpad_B = SCPAD_B_ADDR;
    int gmem_B  = GMEM_B_ADDR;

    int scpad_C = SCPAD_C_ADDR;
    int gmem_C  = GMEM_C_ADDR;

    int scpad_A = SCPAD_A_ADDR;
    int gmem_A  = GMEM_A_ADDR;

    // b into scpad
    asm("scpad_ld %0, %1, %2"
        :
        : "r"(scpad_B), "r"(gmem_B), "r"(0));

    // weight load
    vec vB[TILE_SIZE];
    for (int i = 0; i < TILE_SIZE; i++) {
        vB[i] = *(vec*)(scpad_B + i);  

    asm("lw_vi %0, %0, 0, m0"
        :
        : "v"(vB[i]));
    }
    // c into scpad
    asm("scpad_ld %0, %1, %2"
        :
        : "r"(scpad_C), "r"(gmem_C), "r"(0));

    // a into scpad
    asm("scpad_ld %0, %1, %2"
        :
        : "r"(scpad_A), "r"(gmem_A), "r"(1));

    vec vA, vC;

    for (int i = 0; i < TILE_SIZE; i++) {
        vA = *(vec*)(scpad_A + i);      
        vC = *(vec*)(scpad_C + i);     

        vC = gemm(vA, vB[0], TILE_SIZE);

        *(vec*)(scpad_C + i) = vC;      
    }

    // c stored into scpad
    asm("scpad_st %0, %1, %2"
        :
        : "r"(scpad_C), "r"(gmem_C), "r"(0));

    return 0;
}

int main(void) {
    gemm_4x4();
    return 0;
}